"""Do metaphase spindles in TRIPLE-sisterless cells behave like PROMETAPHASE spindles in single-sisterless?

USER 2026-08-08: "create additional plot that takes the prometaphase outline data from single sisterless
cells and use the movement calculatios that have been generated for the traces (like k-k distance, speed,
oscilation period an damplitude, etc etc) and plot against the metaphase values for the triple ablations
(prometaphase values for single sisterless means the measurements that are available from before the
metaphase start time. they won't specifically be labeled as prometaphase measurements. the goal of these
plots is to see if metaphase spindles in triple sisterless cells behave more similarly to prometaphase
spindles in single sisterless than metaphase spindles in single sisterless cells."

THREE GROUPS, and the third one is the whole point -- without single-sisterless METAPHASE there is nothing
to say "more similar than" against:
  A  1-sisterless, PROMETAPHASE  = every measurement with t < Metaphase Start (never labelled as such)
  B  1-sisterless, METAPHASE     = [Metaphase Start, Anaphase Onset)      <- the comparison baseline
  C  3-sisterless, METAPHASE     = [Metaphase Start, Anaphase Onset)      <- the question

FOUR METRICS, definitions kept consistent with the existing protocol in `kt_oscillation.py`:
  * k-k distance      -- her sister pairs, from KT_SISTER_KK (built by `kt_sisters.py`, the established
                         pairing protocol; NOT re-derived here)
  * speed             -- frame-to-frame displacement / dt, on her traced coordinates (uncorrected)
  * oscillation period-- Lomb-Scargle (handles the irregular t_sec), 30-600 s, imported from kt_oscillation
  * oscillation amp   -- detrended SD of position along the plate normal, in um

STAGE: speed and oscillation use `cx_px`/`cy_px` from KT_OUTLINE_TRACKS -- HER TRACED coordinates,
uncorrected. The 2026-08-08 common-mode correction is RETIRED (the microscope metadata shows the stage does
not drift during acquisition). Oscillation is additionally measured along her plate normal, which is
insensitive to any rigid shift because both the KT and the plate are her marks in the same frame.

NO ANAPHASE anywhere (her standing rule) -- and note group A is deliberately PRE-metaphase, which is not
anaphase and is therefore allowed.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
import osclib   # validated plate reconstruction (user 2026-08-20, board 8 item 2)
# 2026-08-09: the 2026-08-08 'common mode' stage correction is RETIRED -- the microscope's own
# per-frame XPositionUm/YPositionUm show the stage does not drift during acquisition (1,901 of
# 2,071 source files never move). These plots use HER TRACED coordinates, uncorrected. Measured
# stage offsets, where they exist at all, are available as cx_px_stagecorr in the tracks store.
from kt_oscillation import dominant_period       # same Lomb-Scargle used everywhere else
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group7"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G7_prometa_single_vs_meta_triple"
SCRIPT = __file__

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
_dbl = lib.double_chromosome_batches()
_manual = set(lib.manual_plot_exclusions(PLOT_ID))


def nsis(b):
    v = (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


def usable(b):
    return not (lib.plot_excluded(b) or lib.is_mad1(b) or b in _dbl or b in _manual)


def window(b):
    return (lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", "")),
            lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", "")))


GROUPS = ["1-sis prometaphase", "1-sis metaphase", "3-sis metaphase"]
GC = {"1-sis prometaphase": "#4393c3", "1-sis metaphase": "#2166ac", "3-sis metaphase": "#b2182b"}


def group_of(b, t):
    n = nsis(b); ms, ana = window(b)
    if ms is None or n not in (1, 3):
        return None
    if ana is not None and t >= ana:
        return None                       # NO ANAPHASE
    if n == 1:
        return "1-sis prometaphase" if t < ms else "1-sis metaphase"
    return "3-sis metaphase" if t >= ms else None    # 3-sis prometaphase is not part of the question


# ---------- 1. k-k distance -------------------------------------------------------------------
kk = collections.defaultdict(list)
kk_cell = {}
for r in csv.DictReader(open(A + "KT_SISTER_KK_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    b = r["batch"].strip()
    if not usable(b):
        continue
    try:
        t = float(r["t_sec"]); v = float(r["kk_dist_um"])
    except Exception:
        continue
    g = group_of(b, t)
    if g:
        kk_cell.setdefault((g, b), []).append(v)
# ONE VALUE PER CELL for k-k too -- 589 measurements from 13 cells is not 589 independent facts.
for (_g, _b), _v in kk_cell.items():
    kk[_g].append(float(np.median(_v)))
print("k-k n (CELLS):", {g: len(v) for g, v in kk.items()})

# ---------- 2. plate line, for the normal axis --------------------------------------------------
PLATE = {}
for r in csv.DictReader(open(A + "META_PLATE_NORMALIZED_20260728.csv", newline="", encoding="utf-8",
                             errors="replace")):
    try:
        PLATE[(r["batch"].strip(), int(r["frame"]))] = (float(r["norm_x1"]), float(r["norm_y1"]),
                                                        float(r["norm_x2"]), float(r["norm_y2"]))
    except Exception:
        pass

# ---------- 3. tracks -> speed, oscillation ------------------------------------------------------
TR = collections.defaultdict(list)
for r in csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                             errors="replace")):
    if (r.get("label") or "").strip() != "paired":
        continue                                   # spindle behaviour = the aligned, bioriented population
    b = r["batch"].strip()
    if usable(b):
        TR[(b, r["track_id"])].append(r)

speed, period, amp = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
percell_speed = {}      # (group, batch) -> [per-track medians]; collapsed to one value per cell below
period_cell, amp_cell = {}, {}
for (b, tid), rs in TR.items():
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    try:
        rs.sort(key=lambda x: float(x["t_sec"]))
    except Exception:
        continue
    for g in GROUPS:
        seg = []
        for r in rs:
            try:
                t = float(r["t_sec"])
            except Exception:
                continue
            if group_of(b, t) != g:
                continue
            seg.append((t, float(r["cx_px"]), float(r["cy_px"]), int(r["frame"])))
        if len(seg) < 4:
            continue
        # speed on her traced coordinates (no stage correction — the metadata shows none is needed)
        sp = [np.hypot(c[1] - a[1], c[2] - a[2]) * ps / (c[0] - a[0])
              for a, c in zip(seg, seg[1:]) if c[0] > a[0]]
        if sp:
            # ONE VALUE PER CELL, not per track. 2026-08-09: appending per track is pseudo-replication --
            # a cell with 8 tracks counted 8 times, which is what made the group comparisons look
            # significant (metaphase speed p=0.005 per track -> p=0.059 per cell; anaphase p=4e-06 ->
            # p=0.62). Cells are the independent unit here, so the per-cell median is collected and the
            # group test runs across cells.
            percell_speed.setdefault((g, b), []).append(float(np.median(sp)))
        # position along the plate normal -> oscillation (drift-immune: both are her marks)
        proj = []
        for (t, x, y, fr) in seg:
            pl = PLATE.get((b, fr))
            if pl is not None:
                x1, y1, x2, y2 = pl
                vx, vy = x2 - x1, y2 - y1
                L = np.hypot(vx, vy)
                if L <= 0:
                    continue
                px_, py_ = x1, y1
                nx, ny = -vy / L, vx / L           # unit normal to her plate
            else:
                # USER 2026-08-20 (artboard 8, item 2): "there should definitely be more annotated data that
                # should be in these - the n for all groups on both plots is far too small". Requiring a
                # DRAWN plate on the exact frame is what made it small: the oscillation metrics fell to n=4
                # for 1-sisterless PROMETAPHASE while k-k, which needs no plate, kept n=16 -- and
                # prometaphase is exactly where she had least reason to draw a plate. Where she drew none,
                # the plate is reconstructed from her OWN sister pairs (osclib, validated on 1,045 frames
                # where she DID draw one: 6.9 deg median disagreement). Never overrides a drawn plate.
                # NOT `g`: that is the GROUP key in the enclosing loop, and rebinding it here made
                # `period_cell.setdefault((g, b), [])` try to hash a numpy array. Same class of bug as the
                # `T` shadowing this file already documents at the model-wave block.
                _recon = osclib._reconstructed_plate(b, fr)
                if _recon is None:
                    continue
                (px_, py_), (nx, ny) = _recon
            proj.append((t, ((x - px_) * nx + (y - py_) * ny) * ps))
        if len(proj) >= 6:
            ts = np.array([p[0] for p in proj]); ys = np.array([p[1] for p in proj])
            per, pw = dominant_period(ts, ys)
            if per:
                period_cell.setdefault((g, b), []).append(per)
            det = ys - np.polyval(np.polyfit(ts, ys, 1), ts)     # remove drift toward/away from the plate
            amp_cell.setdefault((g, b), []).append(float(det.std()))

for (_g, _b), _v in percell_speed.items():
    speed[_g].append(float(np.median(_v)))          # one median per CELL
print("speed n (CELLS):", {g: len(v) for g, v in speed.items()})
for (_g,_b),_v in period_cell.items(): period[_g].append(float(np.median(_v)))
for (_g,_b),_v in amp_cell.items():    amp[_g].append(float(np.median(_v)))
print("period n (CELLS):", {g: len(v) for g, v in period.items()})
print("amp n:", {g: len(v) for g, v in amp.items()})

# ---------- figure --------------------------------------------------------------------------------
PANELS = [("k-k distance (um)", kk), ("median speed (um/s)", speed),
          ("oscillation period (s)", period), ("oscillation amplitude (um, SD)", amp)]
fig, axes = plt.subplots(1, 4, figsize=(17.0, 4.9))
stats_lines = []
for ax, (ylab, dat) in zip(axes, PANELS):
    vals = [np.array(dat.get(g, []), float) for g in GROUPS]
    bp = ax.boxplot([v for v in vals], widths=.58, patch_artist=True, showfliers=False,
                    medianprops=dict(color="k", lw=1.4))
    for patch, g in zip(bp["boxes"], GROUPS):
        patch.set_facecolor(GC[g]); patch.set_alpha(.35); patch.set_edgecolor("k")
    rng = np.random.default_rng(0)
    for i, (g, v) in enumerate(zip(GROUPS, vals), start=1):
        if len(v):
            ax.scatter(np.full(len(v), i) + rng.uniform(-.11, .11, len(v)), v,
                       s=16, c=GC[g], edgecolor="k", lw=.3, zorder=3, alpha=.8)
    ax.set_xticks([1, 2, 3])
    ax.set_xticklabels([f"{g.replace(' ', chr(10))}\nn={len(v)}" for g, v in zip(GROUPS, vals)], fontsize=7)
    ax.set_ylabel(ylab, fontsize=9)
    # the actual question: is C closer to A than to B?
    try:
        from scipy import stats as st
        a, b_, c = vals[0], vals[1], vals[2]
        if len(a) >= 3 and len(b_) >= 3 and len(c) >= 3:
            p_ca = st.mannwhitneyu(c, a, alternative="two-sided")[1]
            p_cb = st.mannwhitneyu(c, b_, alternative="two-sided")[1]
            # A "closer to X" label is only meaningful if 3-sis actually differs from the OTHER one.
            # For k-k it differs significantly from BOTH (p=0.013 and p=0.012) and is nearer prometaphase
            # by only 0.30 vs 0.36 um -- calling that "resembles prometaphase" overstates a 0.06 um margin.
            d_a, d_b = abs(np.median(c) - np.median(a)), abs(np.median(c) - np.median(b_))
            closer = "prometaphase" if d_a < d_b else "metaphase"
            if p_ca < .05 and p_cb < .05:
                head = "differs from BOTH\n(nearer %s by %.3g)" % (closer, abs(d_a - d_b))
            elif p_ca >= .05 and p_cb >= .05:
                head = "no difference from\neither (n.s.)"
            else:
                head = "3-sis meta closer to\n1-sis %s" % closer
            ax.set_title(head, fontsize=8.5)
            ax.text(.5, .01, f"vs promet p={p_ca:.2g}\nvs meta p={p_cb:.2g}", transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=7, color="#444")
            stats_lines.append(f"{ylab}: 3-sis-meta median {np.median(c):.3g}; "
                               f"1-sis-promet {np.median(a):.3g} (p={p_ca:.2g}); "
                               f"1-sis-meta {np.median(b_):.3g} (p={p_cb:.2g}); closer to {closer}")
    except Exception as e:
        stats_lines.append(f"{ylab}: stats failed ({e})")

fig.suptitle("Do metaphase spindles in triple-sisterless cells behave like PROMETAPHASE spindles in "
             "single-sisterless cells?", fontsize=11, y=1.01)
fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)
for s in stats_lines:
    print("   " + s)

rows = []
for name, dat in [("kk_dist_um", kk), ("median_speed_um_s", speed),
                  ("oscillation_period_s", period), ("oscillation_amp_um", amp)]:
    for g in GROUPS:
        for v in dat.get(g, []):
            rows.append([name, g, f"{v:.5f}"])
lib.record_plot(
    PLOT_ID, ["metric", "group", "value"], rows,
    {"kind": "4-panel box", "groups": GROUPS, "anaphase": "excluded", "stage_correction": "none (traced coordinates)"},
    script=SCRIPT,
    caption=("Single-sisterless PROMETAPHASE (every measurement before Metaphase Start, which is not "
             "labelled as prometaphase in the data) vs single-sisterless METAPHASE vs triple-sisterless "
             "METAPHASE. Speed and oscillation use her traced track coordinates, uncorrected; oscillation is "
             "measured along her metaphase-plate normal, which is drift-immune. k-k from her sister pairs "
             "via the established kt_sisters protocol. Anaphase excluded. " + " | ".join(stats_lines)),
    source=[A + "KT_SISTER_KK_20260723.csv", A + "KT_OUTLINE_TRACKS_20260723.csv",
            A + "META_PLATE_NORMALIZED_20260728.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column=None, fig=png,
)
print("recorded", PLOT_ID)
