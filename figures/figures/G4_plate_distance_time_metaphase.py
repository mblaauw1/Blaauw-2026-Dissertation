#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_plate_distance_time_metaphase.
Rebuilds ONLY this figure from data/G4_plate_distance_time_metaphase.csv
(batch,t_min_from_meta,plate_dist_um). Ported from group4_movement.py (O5 metaphase-onset
companion). Imports ONLY lib for styling. Honors $KTFIG_OUT.

FLAGGED LIMITATION: the source builder colours each per-cell line by its COHORT (b2 from master)
and draws per-cohort median trends + cohort-average anaphase dashed lines. The frozen CSV for this
figure carries NO cohort column and no anaphase caps, so a faithful CSV-only rebuild cannot recover
cohort colouring/anaphase markers. This script therefore draws the per-cell distance-vs-time-from-
metaphase lines (one colour per cell) plus an OVERALL binned-median trend. See the QA log.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_plate_distance_time_metaphase.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

series = defaultdict(list)
with open(DATA) as f:
    for row in csv.DictReader(f):
        series[row["batch"]].append((float(row["t_min_from_meta"]), float(row["plate_dist_um"])))

fig, ax = plt.subplots(figsize=(9, 5.2))
cmap = plt.cm.tab20
allpts = []
for i, (b, s) in enumerate(sorted(series.items())):
    s = sorted(s)
    ax.plot([p[0] for p in s], [p[1] for p in s], color=cmap(i % 20), alpha=.6, lw=1.0, marker="o", ms=2)
    allpts.extend(s)
# overall binned-median trend (bin width 4 min)
a = np.array(sorted(allpts))
if len(a):
    gx = []; gy = []
    for lo in np.arange(0, a[:, 0].max() + 4, 4):
        m = (a[:, 0] >= lo) & (a[:, 0] < lo + 4)
        if m.sum() >= 3: gx.append(lo + 2); gy.append(np.median(a[m, 1]))
    if len(gx) >= 2: ax.plot(gx, gy, color="#111", lw=3, zorder=5, label="overall median trend")
ax.axvline(0, color="#333", ls=":", lw=.9)
ax.set_xlabel("Time since metaphase onset (min; 0 = Metaphase Start)")
ax.set_ylabel("KT distance to metaphase plate (µm)")
ax.legend(fontsize=8)
ncells = len(series)
ax.set_title(f"KT distance to metaphase plate — from METAPHASE ONSET (O5 companion; N={ncells} cells)",
             loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time_metaphase.png", bbox_inches="tight"); plt.close()
print(f"G4_plate_distance_time_metaphase -> {OUT}/G4_plate_distance_time_metaphase.png : {ncells} cells, {len(allpts)} points")
