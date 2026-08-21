#!/usr/bin/env python3
"""Standalone rebuild of ONE figure: G1_start_rounded_vs_duration_zoom.

Outlier-trimmed '_zoom' COMPANION of G1_start_rounded_vs_duration (start-outline roundness vs
metaphase duration, colored by cohort). Reads the BASE csv data/G1_start_rounded_vs_duration.csv,
finds the extreme metaphase-duration points with the shared robust IQR fence (lib.zoom_trim), and
draws the scatter with the y-axis fit to the bulk; trimmed points become hollow markers pinned at
the top edge at their true x (the missing-point convention). COMPANION-ONLY readability trim — it
does NOT propagate to v1 or any other figure.

Ported from make_zoom_companions.py (generic 'scatter' family) but pinned to this id only; the
distorting metric (mitotic_duration_min) and x-metric (start_roundness) are fixed for this figure.
Imports only lib for shared styling/helpers. Honors KTFIG_OUT to redirect output to a scratch dir.
"""
import os, csv
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

ID = "G1_start_rounded_vs_duration"
DATA = "/Volumes/4 MB/ablation_plots/data"
YCOL = "mitotic_duration_min"   # the distorting metric (matches make_zoom_companions selection)
XCOL = "start_roundness"        # the x-metric of the base scatter
GCOL = "cohort"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group1"
os.makedirs(OUT, exist_ok=True)
CSV_OUT = OUT if os.environ.get("KTFIG_OUT") else DATA

lib.apply_style()

def load(pid):
    with open(f"{DATA}/{pid}.csv") as f:
        r = csv.reader(f); hdr = next(r); rows = [row for row in r if row]
    return hdr, rows

hdr, rows = load(ID)
yi, xi, gi = hdr.index(YCOL), hdr.index(XCOL), hdr.index(GCOL)
yvals = np.array([float(r[yi]) if r[yi] not in ("", "nan") else np.nan for r in rows])
xvals = np.array([float(r[xi]) if r[xi] not in ("", "nan") else np.nan for r in rows])
groups = [r[gi] for r in rows]

trim = lib.zoom_trim(yvals)
assert trim["distorting"], "expected distorting outliers for this companion"
om = trim["out_mask"]; keep = ~om; hi = trim["hi"]; lo = trim["lo"]

fig, ax = plt.subplots(figsize=(8.5, 5.2))
c_all = np.array([lib.PALETTE.get(g, "#4477aa") for g in groups], dtype=object)
ax.scatter(xvals[keep], yvals[keep], c=list(c_all[keep]), s=22, alpha=.7, edgecolors="none")
for x, cc in zip(xvals[om], c_all[om]):
    ax.plot(x, hi, marker="o", mfc="none", mec=cc, ms=6, mew=1.1, zorder=6)
ax.set_xlabel(XCOL)
ax.set_ylim(lo, hi); ax.set_ylabel(YCOL)
n_out = int(om.sum())
ax.set_title(f"{ID}_zoom — outlier-trimmed zoom companion  "
             f"(y-axis fit to bulk; {n_out} outlier pt(s) removed → hollow markers at top)",
             loc="left", fontweight="bold", fontsize=9.5)
ax.text(0.995, 0.02, f"v2 zoom: {n_out} pts > {trim['fence_hi']:.3g} trimmed  |  "
        f"old y-max {trim['vmax']:.3g} → new {hi:.3g}", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=7, color="#555")
fig.tight_layout(); fig.savefig(f"{OUT}/{ID}_zoom.png", bbox_inches="tight"); plt.close(fig)

with open(f"{CSV_OUT}/{ID}_zoom.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr + ["zoom_outlier_removed"])
    for row, o in zip(rows, om): w.writerow(row + ["1" if o else "0"])
print(f"wrote {OUT}/{ID}_zoom.png  ({n_out} outliers trimmed, hi={hi:.3g})")
