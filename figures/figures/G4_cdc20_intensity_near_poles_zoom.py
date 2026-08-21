#!/usr/bin/env python3
"""Standalone zoom companion for G4_cdc20_intensity_near_poles.

Reads data/G4_cdc20_intensity_near_poles_zoom.csv (pre-flagged with zoom_outlier_removed column).
Plots kept points as filled markers; removed outliers as hollow markers pinned at the top axis edge.
Family: strip (1-D distribution by location group).
"""
import os, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data"
N = 4   # group number -> group4/
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group{N}")
os.makedirs(OUT, exist_ok=True)

lib.apply_style()

ID = "G4_cdc20_intensity_near_poles_zoom"
YCOL = "intensity_sum_bgsub"
GCOL = "location"

# --- load zoom CSV ---
zoom_csv = f"{DATA}/G4_cdc20_intensity_near_poles_zoom.csv"
with open(zoom_csv, newline="") as f:
    rows = list(csv.DictReader(f))

yvals  = np.array([float(r[YCOL]) for r in rows])
groups = [r[GCOL] for r in rows]
om     = np.array([r.get("zoom_outlier_removed", "0") == "1" for r in rows], dtype=bool)
keep   = ~om

# --- recompute fence for axis limits (matches zoom_trim k=3) ---
v = yvals[np.isfinite(yvals)]
q1, q3 = np.percentile(v, [25, 75]); iqr = q3 - q1
fence_hi = q3 + 3.0 * iqr; fence_lo = q1 - 3.0 * iqr
bulk = v[(v <= fence_hi) & (v >= fence_lo)]
bmin, bmax = float(bulk.min()), float(bulk.max())
span = bmax - bmin; pad = 0.06
lo = 0.0   # data is floored at 0 (intensity >= 0)
hi = bmax + pad * span

n_out = int(om.sum())
n_kept = int(keep.sum())

# --- draw strip plot ---
gnames = list(dict.fromkeys(groups))
gpos = {g: i for i, g in enumerate(gnames)}
rng = np.random.default_rng(0)

fig, ax = plt.subplots(figsize=(8.5, 5.2))

for g in gnames:
    gm = np.array([gg == g for gg in groups])
    c = lib.PALETTE.get(g, "#4477aa")
    xk = gpos[g] + rng.uniform(-0.15, 0.15, gm.sum())
    yk = yvals[gm]; ok = om[gm]
    ax.scatter(xk[~ok], yk[~ok], s=16, alpha=0.55, color=c, edgecolors="none")
    for xx in xk[ok]:
        ax.plot(xx, hi, marker="o", mfc="none", mec=c, ms=6, mew=1.1, zorder=6)
    vv = yvals[gm & keep]
    if vv.size:
        ax.hlines(np.median(vv), gpos[g] - 0.28, gpos[g] + 0.28, color="#111", lw=2, zorder=7)

ax.set_xticks(range(len(gnames)))
ax.set_xticklabels([lib.lbl(g) for g in gnames], rotation=25, ha="right", fontsize=8)
ax.set_ylim(lo, hi)
ax.set_ylabel("eYFP-Cdc20 intensity (Σ in r=9 disk, bg-subtracted)")   # was the raw column name "intensity_sum_bgsub"
ax.set_title(
    f"{ID} — outlier-trimmed zoom companion  "
    f"(y-axis fit to bulk; {n_out} outlier pt(s) removed -> hollow markers at top)",
    loc="left", fontweight="bold", fontsize=9.5,
)
ax.text(
    0.995, 0.02,
    f"v2 zoom: {n_out} pts > {fence_hi:.3g} trimmed  |  "
    f"old y-max {float(v.max()):.3g} -> new {hi:.3g}",
    transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#555",
)

fig.tight_layout()
out_png = f"{OUT}/{ID}.png"
fig.savefig(out_png, bbox_inches="tight")
plt.close(fig)
print(f"[{ID}] N kept={n_kept} removed={n_out} -> {out_png}")
