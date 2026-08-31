"""Number of SAC-active (Mad1-positive) kinetochores over time, per batch.

USER 2026-08-08: "for the mad1+hec1 samples, detect in each frame w/ the locations marked the number of
kinetochores (hec1 and also the number of kinetochore annotations on that frme) have mad1 signal and are
thus SAC active. its expected to plumet quickly after the first frame or two. then make it into a line plot
over time that plots number of kinetochores with active SAC over time. each batch should get a line (all on
one plot so things can be compared)"

SOURCE: `G5_hec1_mad1_TRUE_quant.csv` -- the corrected readout, where every one of HER marked kinetochore
locations was measured in BOTH channels on the same z-slice, with her own cytosol background. Each mark
therefore yields a paired (hec1, mad1) measurement at one (batch, timepoint, x, y), which is exactly the
per-location test this plot needs. Locations are paired by (batch, t_sec, x_snapped, y_snapped).

"HAS MAD1 SIGNAL" is thresholded on `fold_over_her_bg`, her own background being the calibration. The
threshold is a judgement call, so it is NOT hidden: the main line uses 1.5x background, and a sensitivity
band showing 1.25x and 2.0x is drawn behind it so the conclusion can be seen not to depend on the choice.
Counting is over locations that have a Mad1 measurement; the hec1 measurement at the same spot is what
establishes the location IS a kinetochore.

Both the count and the FRACTION are plotted: batches contribute different numbers of marked kinetochores
per frame, so a raw count alone would confound "SAC switched off" with "she marked fewer spots".
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()

SRC = "/Volumes/4 MB/ablation_plots/data/G5_hec1_mad1_TRUE_quant.csv"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group5"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G5_sac_active_kt_over_time"
SCRIPT = __file__

MAIN_THR = 1.5
BAND = (1.25, 2.0)

rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8", errors="replace")))
print(f"{len(rows)} measurement rows")


def f(v):
    try:
        return float(v)
    except Exception:
        return None


# pair the two channels at each marked LOCATION
loc = collections.defaultdict(dict)
for r in rows:
    k = (r["batch"], r["t_mmss"], f(r["t_sec"]), r["x_snapped"], r["y_snapped"])
    fold = f(r.get("fold_over_her_bg"))
    if fold is not None:
        loc[k][r["channel"]] = fold

print(f"distinct marked locations: {len(loc)}")
both = sum(1 for v in loc.values() if "mad1" in v and "hec1" in v)
print(f"  with BOTH hec1 and mad1 measured: {both}")

# per (batch, timepoint): how many locations, how many Mad1-positive at each threshold
per = collections.defaultdict(lambda: {"n": 0, "hec1": 0, MAIN_THR: 0, BAND[0]: 0, BAND[1]: 0})
for (b, tmm, tsec, x, y), v in loc.items():
    if "mad1" not in v:
        continue
    d = per[(b, tmm, tsec)]
    d["n"] += 1
    if "hec1" in v:
        d["hec1"] += 1
    for thr in (MAIN_THR, BAND[0], BAND[1]):
        if v["mad1"] >= thr:
            d[thr] += 1

batches = sorted({k[0] for k in per})
COL = {"xy2": "#1f77b4", "xy5": "#d62728"}
print(f"batches: {batches}")

fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.6, 5.0))
rows_out, summary = [], []
for b in batches:
    ks = sorted([k for k in per if k[0] == b], key=lambda k: k[2])
    ts = [k[2] / 60.0 for k in ks]
    n = [per[k]["n"] for k in ks]
    pos = [per[k][MAIN_THR] for k in ks]
    lo = [per[k][BAND[0]] for k in ks]
    hi = [per[k][BAND[1]] for k in ks]
    c = COL.get(b, "#666")
    axA.fill_between(ts, hi, lo, color=c, alpha=.16, lw=0, zorder=1)
    axA.plot(ts, pos, "-o", color=c, lw=2, ms=6, zorder=3, label=f"{b} (of {max(n)} marked KTs)")
    frac = [p / m if m else np.nan for p, m in zip(pos, n)]
    fl = [p / m if m else np.nan for p, m in zip(lo, n)]
    fh = [p / m if m else np.nan for p, m in zip(hi, n)]
    axB.fill_between(ts, fh, fl, color=c, alpha=.16, lw=0, zorder=1)
    axB.plot(ts, frac, "-o", color=c, lw=2, ms=6, zorder=3, label=b)
    for k, m, p, l_, h_ in zip(ks, n, pos, lo, hi):
        rows_out.append([b, k[1], f"{k[2]:.2f}", m, per[k]["hec1"], p, l_, h_,
                         f"{p/m:.4f}" if m else ""])
    if pos:
        summary.append(f"{b}: {pos[0]}/{n[0]} SAC-active at {ks[0][1]} -> {pos[-1]}/{n[-1]} at {ks[-1][1]}")

axA.set_xlabel("time (min)")
axA.set_ylabel(f"kinetochores with Mad1 signal\n(SAC-active, >= {MAIN_THR}x background)")
axA.set_title("SAC-active kinetochore count over time", fontsize=10)
axA.legend(frameon=False, fontsize=8)
axA.set_ylim(bottom=0)
axA.text(.98, .97, f"shaded = threshold {BAND[0]}x-{BAND[1]}x", transform=axA.transAxes,
         ha="right", va="top", fontsize=7, color="#555")

axB.set_xlabel("time (min)")
axB.set_ylabel("fraction of marked kinetochores that are SAC-active")
axB.set_title("as a fraction of the kinetochores marked on that frame", fontsize=10)
axB.set_ylim(0, 1.02)
axB.legend(frameon=False, fontsize=8)

fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200); plt.close(fig)
print("wrote", png)
for s in summary:
    print("   " + s)

lib.record_plot(
    PLOT_ID,
    ["batch", "t_mmss", "t_sec", "n_marked_kt", "n_with_hec1",
     f"n_mad1_pos_{MAIN_THR}x", f"n_mad1_pos_{BAND[0]}x", f"n_mad1_pos_{BAND[1]}x", "fraction_sac_active"],
    rows_out,
    {"kind": "line", "threshold_fold": MAIN_THR, "sensitivity_band": list(BAND)},
    script=SCRIPT,
    caption=("Kinetochores scored SAC-active (Mad1 at or above " + str(MAIN_THR) + "x her cytosol "
             "background) at each of her marked locations, per timepoint, one line per batch. Locations "
             "are paired across channels by (batch, time, x, y) from the corrected quantification; the "
             "hec1 measurement at the same spot establishes the location is a kinetochore. Shaded band "
             f"spans thresholds {BAND[0]}x-{BAND[1]}x so the trend can be seen not to depend on the cut. "
             "Right panel normalises by the number of kinetochores marked on that frame. " + " | ".join(summary)),
    source=[SRC, "/Volumes/4 MB/annotations/kt_points.csv"],
    key_column="batch", fig=png,
)
print("recorded", PLOT_ID)
