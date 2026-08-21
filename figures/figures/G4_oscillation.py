#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_oscillation.
Rebuilds ONLY this figure from data/G4_oscillation.csv (track,disp_um_per_20s).
Ported from group4_movement.py oscillation block (the violin: polar kinetochore vs
plate KT (tracking), displacement per 20s interval). Imports ONLY shared styling helpers
from lib. Output dir honors $KTFIG_OUT (scratch override); default = the real group4/ path.

NOTE: the source builder colours the polar SCATTER by cohort; the plot's own CSV carries only
(track,value) with no cohort column, so this standalone draws the polar scatter in the single
group colour (matching the violin body). The violin body, median, mean, N and the polar-vs-plate
Mann-Whitney are fully reproduced from the CSV.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_oscillation.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

ORDER = ["polar kinetochore", "plate KT (tracking)"]
COL = {"polar kinetochore": "#762a83", "plate KT (tracking)": "#1b5e20"}
G = {g: [] for g in ORDER}
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["track"].strip()
        if g in G:
            G[g].append(float(row["disp_um_per_20s"]))

fig, ax = plt.subplots(figsize=(7.5, 5))
for i, g in enumerate(ORDER):
    vals = G[g]
    if len(vals) >= 2:
        for bd in ax.violinplot([vals], positions=[i], widths=.7, showextrema=False)['bodies']:
            bd.set_facecolor(COL[g]); bd.set_alpha(.25 if i == 0 else .3); bd.set_edgecolor(COL[g])
    if vals:
        ax.scatter(np.full(len(vals), i) + (np.random.RandomState(i).rand(len(vals)) - .5) * .18,
                   vals, s=11, color=COL[g], alpha=.55, edgecolor="none", zorder=2)
        ax.hlines(np.median(vals), i - .3, i + .3, color=COL[g], lw=2.2, zorder=3)
        ax.hlines(np.mean(vals), i - .24, i + .24, color=COL[g], lw=1.3, ls=(0, (2, 1.5)), zorder=3)
        ax.text(i, np.percentile(vals, 99), f"x̄ {np.mean(vals):.2f}µm\nmed {np.median(vals):.2f}µm\nN={len(vals)}",
                ha="center", va="bottom", fontsize=7.5)

a, b = G["polar kinetochore"], G["plate KT (tracking)"]
if len(a) >= 2 and len(b) >= 2:
    p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
    ax.text(.5, .02, f"polar vs plate: Mann–Whitney p={p:.2g}", transform=ax.transAxes,
            ha="center", fontsize=8, color="#333")

ax.set_xticks([0, 1]); ax.set_xticklabels(["polar kinetochore", "plate KT (tracking)"], fontsize=9.5)
ax.set_ylabel("Displacement per 20s interval (µm)")
ax.legend(handles=[Patch(facecolor=COL["polar kinetochore"], alpha=.25, edgecolor=COL["polar kinetochore"], label=f"polar kinetochore (annotation; N={len(a)} steps)"),
                   Patch(facecolor=COL["plate KT (tracking)"], alpha=.3, edgecolor=COL["plate KT (tracking)"], label=f"plate KT (TrackMate, after metaphase; N={len(b)} steps)"),
                   Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], color="#444", lw=1.3, ls=(0, (2, 1.5)), label="mean")], fontsize=7.5, loc="upper right")
ax.set_title("Kinetochore oscillation — displacement per 20s interval: polar vs plate-aligned (tracking)",
             loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_oscillation.png", bbox_inches="tight"); plt.close()
print("G4_oscillation ->", f"{OUT}/G4_oscillation.png", {g: len(G[g]) for g in ORDER})
