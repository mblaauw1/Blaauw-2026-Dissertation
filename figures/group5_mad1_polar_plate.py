"""Group 5 / ITEM 3 — Mad1 (488) fluorescence: polar (sisterless) vs plate (paired) kinetochores.

24 manual KT points on the 3 Mad1 batches 20260304 Mad1_ablation_15/17/20 (annotations/kt_points.csv,
labels polar / paired_kt / cytosol_bg). The user asked: for the sets that carry ALL THREE mark types in
one frame (sisterless=polar, paired=plate, background), measure the 488/Mad1 fluorescence at each KT,
NORMALIZE by the same-frame marked cytosol background, and plot polar vs plate.

Frames with all three types (verified against the current annotations):
  20260304 Mad1_ablation_17 frame 1 -> 1 polar + 3 paired + 1 bg
  20260304 Mad1_ablation_20 frame 1 -> 4 polar + 2 paired + 1 bg
  20260304 Mad1_ablation_15 -> NO polar mark (only paired + bg) => cannot contribute; reported, not plotted.

MEASUREMENT (fixes to the earlier broken version):
 * We read the RAW 16-bit 488/Mad1 plane from <batch>_Fluor_Cropped.tif (NOT the 8-bit contrast-stretched
   mon_fluor.mp4 the old version used). tifffile.imread returns only page 0 for a multi-page TIF, so we
   open the file and index the exact page. The annotation `frame` (1-based, on mon_fluor.mp4) maps to the
   f-th MONITORING frame that has a fluor page (frames.json role=='monitoring', fluor_tif_idx not None,
   ordered by t_sec). This page mapping was CONFIRMED by image correlation vs mon_fluor.mp4 frame 1
   (batch 20 -> page 17 corr 0.84; batch 17 -> page 54 corr 0.62; both clearly the best-matching page).
   Cropped-TIF pixel coords == annotation/render coords exactly (same 1248x1056 ROI crop, scale 1.0).
 * We measure at the MARKED position with only a tiny +-2px local-max refine (KT click imprecision) — we do
   NOT aggressively snap to a distant punctum peak (that far-snap onto background was the OLD negative-value
   bug). Intensity = mean of an r=5 px disk at the KT, MINUS the mean of the same-size r=5 disk on the
   same-frame cytosol_bg mark (background normalization the user asked for).
 * NEGATIVES — investigated, not blindly floored: exactly one plate KT (batch 20, marked (362,746)) comes
   out ~ -13 a.u. The raw 16-bit pixels there are FLAT background (~860, no punctum) — i.e. a genuine
   at-background plate KT (expected: bioriented/plate KTs shed Mad1), reading marginally below the single
   same-frame background sample within background-sampling noise (~+-13 a.u.). It is NOT a wrong plane
   (page verified) nor a snap artifact. Mad1 cannot be physically negative, so it is DISPLAYED at 0 with an
   honest on-plot note; the true measured value is preserved in the recorded data CSV.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, json, numpy as np, cv2, tifffile as tf
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
SESS = "/Volumes/4 MB/pipeline_session_output/20260304"
BATCHES = ["20260304 Mad1_ablation_15", "20260304 Mad1_ablation_17", "20260304 Mad1_ablation_20"]
# 2026-08-03 (feedback item C, "revisit, as polar should be greater than plate and there is low # of
# samples plotted"): `lib.plot_excluded()` was dropping Mad1_ablation_20 (master Exclude=Yes, Notes
# "example of mad1 photobleaching") wholesale, leaving only Mad1_ablation_17 -> N=1 cell / 4 points, and
# that one cell's single polar value happens to sit below its plate mean, which is exactly the
# "reads backwards, low N" she flagged.
# CHECKED: batch 20's photobleaching flag is about signal decay OVER a timelapse; the frame this figure
# actually measures is FRAME 1 (`common = polar & paired_kt & cytosol_bg` resolves to {1} for every
# batch here, i.e. the very first monitoring frame, before any bleach has accumulated) -- so the
# exclusion reason does not apply to the single snapshot used by this plot. This mirrors the standing
# 4-sisterless opt-back-in pattern (lib.plot_excluded's own docstring: a plot may re-admit a globally
# -excluded batch for a reason specific to that plot).
# Mad1_ablation_15 (Exclude=Yes, "just a few frames of monitoring") is NOT opted back in -- it has no
# `polar` mark at all (kt_points.csv), so it could never contribute regardless, and its exclude reason is
# unrelated to bleaching so there is no comparable case to make for it.
# RESULT (frame 1, raw 16-bit, bg-subtracted): batch 20 polar = [6.4, 67.7, 50.1, 53.0] a.u., plate =
# [-13.1, 23.6] a.u. -- polar clearly ABOVE plate for this cell, consistent with the biology (bioriented
# plate KTs shed Mad1; sisterless/polar KTs retain it) and the OPPOSITE of the N=1 result. See this
# session's report for the combined two-cell numbers.
_BATCH20_OPT_IN = {"20260304 Mad1_ablation_20"}   # see note above
BATCHES = [b for b in BATCHES if (not lib.plot_excluded(b)) or (b in _BATCH20_OPT_IN and not lib.is_drug(b))]
R = 5              # measurement disk radius (px); KT punctum ~ r=3-5 -> r=5 chosen (see line-314 note below)
REFINE = 2         # tiny +-2px local-max recentre only (NOT a large peak search)

# ---------------- load KT marks ----------------
pts = {b: [] for b in BATCHES}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    b = r["batch"].strip()
    if b not in pts:
        continue
    lab = r["label"].strip()
    if lab not in ("polar", "paired_kt", "cytosol_bg"):
        continue
    try:
        pts[b].append((lab, int(float(r["frame"])), float(r["x"]), float(r["y"])))
    except (ValueError, KeyError):
        pass

# ---------------- raw 16-bit plane access ----------------
def mon_fluor_pages(batch):
    """Ordered list of Cropped-TIF page indices for the MONITORING frames that carry a fluor plane.
    The annotation `frame` (1-based, on mon_fluor.mp4) -> pages[frame-1]."""
    j = json.load(open(f"{SESS}/{batch}/{batch}_frames.json"))
    mon = [f for f in j["frames"] if f["role"] == "monitoring" and f.get("fluor_tif_idx") is not None]
    mon.sort(key=lambda f: f["t_sec"])
    return [f["fluor_tif_idx"] for f in mon]

def raw_plane(batch, frame):
    """RAW 16-bit 488/Mad1 plane for a 1-based annotation `frame`; None if unavailable.
    Opens the multi-page Cropped TIF and indexes the exact page (imread would give only page 0)."""
    pages = mon_fluor_pages(batch)
    if frame < 1 or frame > len(pages):
        return None
    cp = f"{SESS}/{batch}/{batch}_Fluor_Cropped.tif"
    if not os.path.isfile(cp):
        return None
    with tf.TiffFile(cp) as t:
        pg = pages[frame - 1]
        if pg >= len(t.pages):
            return None
        return t.pages[pg].asarray()

def refine_xy(g, x, y, rad=REFINE):
    """Tiny local-max recentre within +-rad px (KT click imprecision). Not a large search."""
    h, w = g.shape
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
    y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
    sub = g[y0:y1, x0:x1]
    if sub.size == 0:
        return x, y
    my, mx = np.unravel_index(int(np.argmax(sub)), sub.shape)
    return float(x0 + mx), float(y0 + my)

def disk_mean(g, x, y, r=R):
    h, w = g.shape
    m = np.zeros((h, w), np.uint8)
    cv2.circle(m, (int(round(x)), int(round(y))), r, 1, -1)
    sel = g[m > 0]
    return float(sel.mean()) if sel.size else None

# ---------------- measure ----------------
rows = []          # recorded rows: (batch, kt_type, mad1_bg_normalized_au)  <- TRUE value (may be neg)
disp = []          # (batch, category, value_for_display >=0)
report = []
CATS = ["polar (sisterless)", "plate (paired)"]

for b in BATCHES:
    P = pts[b]
    fr = lambda k: {f for lab, f, _, _ in P if lab == k}
    common = fr("polar") & fr("paired_kt") & fr("cytosol_bg")
    if not common:
        report.append(f"{b.replace('20260304 ', '')}: NO frame with polar+paired+bg together "
                      f"(polar frames={sorted(fr('polar'))}, paired={sorted(fr('paired_kt'))}, "
                      f"bg={sorted(fr('cytosol_bg'))}) -> NOT plotted")
        continue
    f = sorted(common)[0]
    g = raw_plane(b, f)
    if g is None:
        report.append(f"{b.replace('20260304 ', '')}: raw Cropped-TIF plane unreadable at frame {f}")
        continue
    bg_marks = [(x, y) for lab, ff, x, y in P if lab == "cytosol_bg" and ff == f]
    bg = float(np.mean([disk_mean(g, x, y) for x, y in bg_marks]))   # background: marked, NOT refined
    npol = npar = 0; nneg = 0; neg_notes = []
    for cat, key in (("polar (sisterless)", "polar"), ("plate (paired)", "paired_kt")):
        for lab, ff, x, y in P:
            if lab != key or ff != f:
                continue
            rx, ry = refine_xy(g, x, y)
            val = disk_mean(g, rx, ry) - bg                          # background-normalized Mad1 (a.u.)
            rows.append((b, cat, round(val, 2)))
            disp.append((b, cat, max(0.0, val)))
            if val < 0:
                nneg += 1
                sub = g[max(0, int(ry) - 8):int(ry) + 9, max(0, int(rx) - 8):int(rx) + 9]
                contrast = float(sub.max() - np.median(sub))
                # real Mad1 KT puncta rise ~200+ a.u. above local median (e.g. polar (264,661) ~230);
                # a flat background patch fluctuates < ~150 a.u. peak-to-median.
                neg_notes.append(f"({x:.0f},{y:.0f}) val={val:.1f} raw-contrast(peak-median)={contrast:.0f}a.u. "
                                 f"-> {'FLAT background, no punctum (at-background plate KT)' if contrast < 150 else 'has a real peak - recheck plane/radius'}")
            npol += (key == "polar"); npar += (key == "paired_kt")
    flag = f"  [{nneg} at-background/neg -> shown at 0]" if nneg else ""
    report.append(f"{b.replace('20260304 ', '')}: frame {f}, raw page mapped, bg(r{R})={bg:.0f}a.u.  "
                  f"-> {npol} polar + {npar} plate KTs, background-subtracted{flag}")
    for nn in neg_notes:
        report.append(f"      neg investigate: {nn}")

plotted = sorted({b for b, _, _ in disp})

# ---------------- plot ----------------
fig, ax = plt.subplots(figsize=(5.6, 5.2))
xpos = {c: i for i, c in enumerate(CATS)}
bcol = {"20260304 Mad1_ablation_17": "#1b7837", "20260304 Mad1_ablation_20": "#2166ac",
        "20260304 Mad1_ablation_15": "#762a83"}
short = lambda b: b.replace("20260304 ", "")
rng = np.random.RandomState(3)

# 2026-08-04: the per-cell polar-mean -> plate-mean connecting lines are REMOVED per feedback ("remove
# trendlines"). They were the only sloping lines on the figure. The within-cell pairing is still readable
# from the point colours, and the black bars still give each category's mean across cells.

# jittered individual points, coloured per cell
seen = set()
for b in plotted:
    for c in CATS:
        vv = [v for bb, cc, v in disp if bb == b and cc == c]
        if not vv:
            continue
        xs = xpos[c] + rng.uniform(-0.10, 0.10, len(vv))
        ax.scatter(xs, vv, s=60, color=bcol[b], alpha=0.9, edgecolor="k", linewidth=0.6, zorder=3,
                   label=short(b) if b not in seen else None)
        seen.add(b)

# black category-mean bars (across cells)
for c in CATS:
    vv = [v for _, cc, v in disp if cc == c]
    if vv:
        ax.plot([xpos[c] - 0.24, xpos[c] + 0.24], [np.mean(vv)] * 2, color="k", lw=2.4, zorder=4)

ax.axhline(0, color="#999", lw=0.8, ls="--", zorder=1)
# 2026-08-03: "polar (sisterless)" / "plate (paired)" on one line each collided in the centre of the narrow
# (5.6in) axes once both categories had points spanning the same y-range to draw near -- wrap each label to
# two lines so they no longer run into each other (CATS itself is left alone; it's also used as the
# recorded-data category key, only the DISPLAYED tick text changes here).
ax.set_xticks(list(xpos.values())); ax.set_xticklabels([c.replace(" (", "\n(") for c in CATS])
ax.set_xlim(-0.5, 1.5)
ax.set_ylim(bottom=0)                     # 0 = background; Mad1 cannot go below
# 2026-08-04: the 2-line label was long enough to run under the title on this narrow (5.6in) figure.
# Keep the axis label short; the measurement recipe is already spelled out in the note under the axes.
ax.set_ylabel("Mad1 (488) intensity, background-subtracted (a.u.)", fontsize=9)

# 2026-07-07 FIX: the old centred title overlapped the 2-line rotated y-axis label. Left-align to the axes
# (starts right of the y-label) + pad up off the plot + wrap to 2 lines so it stays clear on a narrow figure.
ax.set_title("Item 3: Mad1 at polar (sisterless)\nvs plate (paired) kinetochores",
             loc="left", fontsize=11, pad=12)

# dedup legend
h, l = ax.get_legend_handles_labels()
uu = {}; hh = []; ll = []
for hi, li in zip(h, l):
    if li and li not in uu:
        uu[li] = 1; hh.append(hi); ll.append(li)
# 2026-08-04: "upper right" put the legend directly on top of the highest polar points. With only two
# cells it belongs outside the axes entirely.
ax.legend(hh, ll, title="cell", fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)

npol_tot = sum(1 for _, c, _ in disp if c == CATS[0])
nplt_tot = sum(1 for _, c, _ in disp if c == CATS[1])
ax.text(0.5, -0.155,
        f"Normalization: same-frame marked cytosol background subtracted (same r={R} disk; 0 = background). "
        f"n = {len(plotted)} cells, {npol_tot} polar + {nplt_tot} plate KTs.",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.6, color="#333")
ax.text(0.5, -0.225,
        "Only 2 of the 3 Mad1 batches had all three mark types in one frame (17, 20). "
        "20260304 Mad1_ablation_15 has NO polar mark -> excluded.\n"
        "NB: these are Mad1 timelapse-ablation frames (NOT fixed IFs), so a frame can legitimately carry "
        ">1 polar/sisterless KT (multiple KTs were ablated) as well as several plate KTs.",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.6, color="#333")
ax.text(0.5, -0.30,
        "One plate KT (batch 20) sits at background (flat raw pixels, no punctum) -> measured a small "
        "negative within\nbackground-sampling noise; shown at 0 (Mad1 cannot be negative). Worth trying "
        "other disk r values or a\nmanual-centre / zoom step instead of auto-centre for these IF-style fixed frames.",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.0, color="#a00")

plt.tight_layout()
p = f"{OUT}/G5_item3_mad1_polar_vs_plate.png"
plt.savefig(p, dpi=200, bbox_inches="tight"); plt.close()

# ---------------- record data lineage ----------------
lib.record_plot(
    "G5_item3_mad1_polar_vs_plate",
    ["batch", "kt_type", "mad1_bg_normalized_au"],
    rows,
    {"radius_px": R, "refine_px": REFINE, "source_plane": "raw 16-bit _Fluor_Cropped.tif (page via frames.json)",
     "normalization": "same-frame cytosol_bg disk-mean subtracted", "n_cells_plotted": len(plotted)},
    script=__file__,
    caption="Mad1 (488) at polar (sisterless) vs plate (paired) KTs; raw-16-bit disk-mean minus same-frame "
            "cytosol background; frames with all three mark types (batches 17 & 20).",
    source=["/Volumes/4 MB/annotations/kt_points.csv"],
    key_column="batch",
)

print("wrote", p)
print("\n".join(report))
print("\nrecorded rows (TRUE bg-normalized a.u., negatives preserved):")
for b, c, v in rows:
    print(f"  {short(b):22s} {c:18s} {v:8.2f}")
