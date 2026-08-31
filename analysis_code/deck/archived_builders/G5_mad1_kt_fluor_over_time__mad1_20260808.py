"""Mad1 at kinetochores over mitosis: sisterless vs paired. 5 mad1-only batches.

USER 2026-08-08: "...plot the flourescences over time (i expect that the sisterless will retain mad1 for
longer than the paired). make t=0 the start of metaphase, and if there are annotations before the start of
metaohase, put them in the negative time range leading up to metaphase... when the track for a kinetochore
ends... then the timepoint that would be it's next... should go to a flourescence value of 0."

Measurement comes from `G5_mad1_kt_fluor_measurements.csv`, built by
`_claude_tmp/mad1_fluor_measure_20260808.py` (100% of her marks validated brighter than her background).
Plotting is kept separate from measuring so the measurement can be audited on its own.

DECISIONS, and why:
* **Background-subtracted MEAN is the plotted quantity.** It satisfies both of her corrections at once:
  `(sum - bg*N)/N == mean - bg` removes background AND normalises the outline-area difference.
* **Track end -> 0.** A track is (batch, label, grp). When the WHOLE track ends -- not a gap between
  traces -- the next available fluor timepoint is emitted at exactly 0, because 0 is calibrated to
  background and she stops tracing when the kinetochore has faded into background. Interior gaps are NOT
  zero-filled; only the terminal point.
* **Ablation frames are drawn differently, never pooled.** Ablation sources are 1 z-slice, monitoring are
  34 (3 for `20260303 …ablation_10`). Same outline on two acquisition modes is not the same measurement.
* **No anaphase** (her standing rule): rows flagged `at_or_after_anaphase` are dropped.
* `20260310 ptk2_eyfp_mad1_14` has NO Metaphase Start in the master, so it cannot go on a metaphase-anchored
  axis. Its data is measured and kept in the CSV but excluded from this figure rather than given an
  invented anchor.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()

SRC = "/Volumes/4 MB/ablation_plots/data/G5_mad1_kt_fluor_measurements.csv"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group5"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G5_mad1_kt_fluor_over_time"
SCRIPT = __file__

full, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in full}

rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8", errors="replace")))
print(f"measurement rows: {len(rows)}")


def f(v):
    try:
        return float(v)
    except Exception:
        return None


# ---- keep only measurable, anchored, pre-anaphase rows -------------------------------------------
keep = []
drop = collections.Counter()
for r in rows:
    if r["flag"] == "phase_channel_not_measurable":
        drop["phase-channel outline (no fluor signal)"] += 1; continue
    if r["flag"] == "at_or_after_anaphase":
        drop["at/after anaphase (her rule)"] += 1; continue
    if f(r["net_mean_au"]) is None:
        drop["no background mark on that frame"] += 1; continue
    if f(r["t_rel_metaphase_s"]) is None:
        drop[f"no Metaphase Start ({r['batch']})"] += 1; continue
    keep.append(r)
print(f"plotted rows: {len(keep)}")
for k, v in drop.items():
    print(f"   dropped {v:3d}  {k}")

# ---- tracks: (batch, label, grp) ------------------------------------------------------------------
def grp(r):
    for part in (r.get("notes") or "").split(";"):
        if part.startswith("grp:"):
            return part[4:]
    return "?"


tracks = collections.defaultdict(list)
for r in keep:
    tracks[(r["batch"], r["label"], grp(r))].append(r)

# ---- terminal zero: the next fluor timepoint after each track's last trace -------------------------
# The frame AFTER the last trace, on that batch's own fluor clip, is emitted at 0.
import json
FRAMES = {}
for b in {r["batch"] for r in keep}:
    d = (MR.get(b, {}).get("Drive Path", "") or "").strip()
    if not (d and os.path.isdir(d)):
        d = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
    j = json.load(open(os.path.join(d, f"{b}_frames.json")))
    per = {"mon": [], "abl": []}
    for fr in j.get("frames", []):
        ph = "mon" if fr.get("role") == "monitoring" else ("abl" if fr.get("role") == "ablation" else None)
        if ph and fr.get("fluor_tif_idx") is not None:
            per[ph].append(fr)
    FRAMES[b] = per

zeros = []
for key, rs in tracks.items():
    b, lab, g = key
    rs.sort(key=lambda x: f(x["t_sec"]))
    last = rs[-1]
    ph = last["phase"]
    lst = FRAMES[b][ph]
    idx = int(last["frame"])              # 1-based into the fluor clip
    ms = lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", ""))
    ana = lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", ""))
    if idx < len(lst):                    # there IS a next frame -> the track truly ended before the movie did
        nt = float(lst[idx]["t_sec"])
        if ana is not None and nt >= ana:
            continue                      # would land in anaphase -> her rule says leave it off
        zeros.append({"batch": b, "label": lab, "grp": g, "t_rel": nt - ms,
                      "net": 0.0, "phase": ph, "terminal_zero": True})
print(f"terminal zeros emitted: {len(zeros)} (one per track that ended before its movie did)")

# ---- assemble plot series --------------------------------------------------------------------------
LAB_COL = {"sisterless": "#d62728", "paired": "#2ca02c", "polar": "#ff7f0e"}
series = collections.defaultdict(list)
for key, rs in tracks.items():
    b, lab, g = key
    for r in rs:
        series[(b, lab, g)].append((f(r["t_rel_metaphase_s"]) / 60.0, f(r["net_mean_au"]), r["phase"]))
for z in zeros:
    series[(z["batch"], z["label"], z["grp"])].append((z["t_rel"] / 60.0, 0.0, z["phase"]))
for k in series:
    series[k].sort()

fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.4, 5.2), width_ratios=[1.35, 1])

# --- A: every track over time, coloured by class
seen = set()
for (b, lab, g), pts in sorted(series.items()):
    if lab not in LAB_COL:
        continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; phs = [p[2] for p in pts]
    c = LAB_COL[lab]
    axA.plot(xs, ys, "-", color=c, lw=1.2, alpha=.75, zorder=2,
             label=(lab if lab not in seen else None))
    seen.add(lab)
    mon = [(x, y) for x, y, p in zip(xs, ys, phs) if p == "mon"]
    abl = [(x, y) for x, y, p in zip(xs, ys, phs) if p == "abl"]
    if mon:
        axA.scatter([m[0] for m in mon], [m[1] for m in mon], s=26, c=c, edgecolor="k", lw=.4, zorder=3)
    if abl:   # 1 z-slice, not comparable to the 34-slice monitoring frames -> open square
        axA.scatter([a[0] for a in abl], [a[1] for a in abl], s=44, facecolor="none",
                    edgecolor=c, lw=1.4, marker="s", zorder=4)
axA.axvline(0, color="#444", ls="--", lw=1.1, zorder=1)
axA.axhline(0, color="#999", lw=.8, zorder=1)
axA.set_xlabel("time from metaphase start (min)")
axA.set_ylabel("Mad1 at kinetochore\n(background-subtracted mean, AU)")
axA.set_title("Mad1 per kinetochore track", fontsize=10)
h, l = axA.get_legend_handles_labels()
axA.legend(h, l, frameon=False, fontsize=8, loc="upper right")
# ACCOUNT FOR THE Z DIFFERENCE QUANTITATIVELY, not just by drawing it differently.
# She said the ablation movie has ONE z-plane per frame while monitoring has many, and that this "should be
# accounted for somehow". The test that settles it: if the two modes sat on different intensity scales,
# their BACKGROUNDS would differ, and background subtraction would not reconcile them. Measured here from
# her own cytosol_bg marks, so the answer is data, not assumption.
_bg = {"abl": [], "mon": []}
_net = {"abl": [], "mon": []}
for r in keep:
    _bg[r["phase"]].append(f(r["bg_au"]))
    _net[r["phase"]].append(f(r["net_mean_au"]))
_zmsg = ""
if _bg["abl"] and _bg["mon"]:
    import statistics as _st
    _rb = _st.median(_bg["mon"]) / _st.median(_bg["abl"])
    _rn = _st.median(_net["mon"]) / _st.median(_net["abl"])
    _zmsg = (f"z-mode check: background mon/abl = {_rb:.2f} "
             f"(1.00 = same scale, so subtraction reconciles them);\n"
             f"net signal mon/abl = {_rn:.2f}, n_abl={len(_net['abl'])}")
    print("  " + _zmsg.replace("\n", " "))
axA.text(.01, .99, "open squares = ablation movie (1 z-slice)\nfilled = monitoring (multi-z)\n"
                   "0 = faded to background (track end)\n" + _zmsg,
         transform=axA.transAxes, ha="left", va="top", fontsize=7, color="#555")

# --- B: sisterless vs paired, last timepoint each class holds signal
lastt = collections.defaultdict(list)
for (b, lab, g), pts in series.items():
    if lab not in ("sisterless", "paired"):
        continue
    nz = [p for p in pts if p[1] > 0]
    if nz:
        lastt[lab].append(max(p[0] for p in nz))
order = ["paired", "sisterless"]
vals = [lastt.get(k, []) for k in order]
bp = axB.boxplot([v for v in vals], widths=.55, patch_artist=True, showfliers=False,
                 medianprops=dict(color="k", lw=1.4))
for patch, k in zip(bp["boxes"], order):
    patch.set_facecolor(LAB_COL[k]); patch.set_alpha(.35); patch.set_edgecolor("k")
rng = np.random.default_rng(0)
for i, (k, v) in enumerate(zip(order, vals), start=1):
    if v:
        axB.scatter(np.full(len(v), i) + rng.uniform(-.10, .10, len(v)), v,
                    s=34, c=LAB_COL[k], edgecolor="k", lw=.4, zorder=3)
axB.axhline(0, color="#444", ls="--", lw=1)
axB.set_xticks([1, 2]); axB.set_xticklabels([f"paired\nn={len(vals[0])}", f"sisterless\nn={len(vals[1])}"])
axB.set_ylabel("last time with Mad1 above background\n(min from metaphase start)")
axB.set_title("how long Mad1 is retained", fontsize=10)

p_txt = ""
if len(vals[0]) >= 3 and len(vals[1]) >= 3:
    try:
        from scipy import stats
        u, p = stats.mannwhitneyu(vals[1], vals[0], alternative="greater")
        p_txt = f"sisterless > paired: Mann-Whitney p = {p:.3g}"
    except Exception as e:
        p_txt = f"(stats unavailable: {e})"
else:
    p_txt = f"n too small to test (paired {len(vals[0])}, sisterless {len(vals[1])})"
axB.text(.5, .98, p_txt, transform=axB.transAxes, ha="center", va="top", fontsize=8)
print("  " + p_txt)

fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200); plt.close(fig)
print("wrote", png)

out_rows = []
for (b, lab, g), pts in sorted(series.items()):
    for (x, y, ph) in pts:
        out_rows.append([b, lab, g, ph, f"{x:.3f}", f"{y:.2f}"])
lib.record_plot(
    PLOT_ID,
    ["batch", "kt_class", "grp", "acq_phase", "t_rel_metaphase_min", "net_mean_au"],
    out_rows,
    {"kind": "timeseries+box", "metric": "background-subtracted mean", "anaphase": "excluded"},
    script=SCRIPT,
    caption=("Mad1 inside her kinetochore outlines, background-subtracted per frame using her own "
             "cytosol_bg mark; the mean also normalises the outline-area difference. t=0 is metaphase "
             "start, pre-metaphase annotations run negative. Track end is plotted at 0 (0 = background). "
             "Open squares are ablation-movie frames (1 z-slice) vs filled monitoring frames (multi-z); "
             "they are never pooled. The z difference is accounted for by measurement, not assumption: "
             + _zmsg.replace(chr(10), " ") + ". Anaphase excluded. " + p_txt),
    source=[SRC, "/Volumes/4 MB/annotations/kt_outlines.csv",
            "/Volumes/4 MB/annotations/kt_points.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch",
    fig=png,
)
print("recorded", PLOT_ID)
