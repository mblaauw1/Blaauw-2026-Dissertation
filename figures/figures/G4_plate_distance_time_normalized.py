#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_plate_distance_time_normalized.
Rebuilds ONLY this figure from data/G4_plate_distance_time_normalized.csv
(batch,group,frac_meta_to_ana,dist_to_plate_um). Ported from group4_tracking_dist.py (N5
normalized-time companion). Imports ONLY lib for styling. Honors $KTFIG_OUT.
group column: 'polar' (polar-marked KTs, purple) vs 'plate' (plate-control TrackMate tracks, green).
x = fraction of each cell's metaphase->anaphase window (0 = meta onset, 1 = ana onset).
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_plate_distance_time_normalized.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
PURPLE = ("#4a148c", "#b39ddb"); GREEN = ("#1b5e20", "#a5d6a7")

recN = []  # [batch, group, frac, dist]
with open(DATA) as f:
    for row in csv.DictReader(f):
        recN.append([row["batch"], row["group"].strip(), float(row["frac_meta_to_ana"]), float(row["dist_to_plate_um"])])

pol_cells = sorted({r[0] for r in recN if r[1] == "polar"})
pla_cells = sorted({r[0] for r in recN if r[1] == "plate"})
win_cells = sorted({r[0] for r in recN})

fig, axN = plt.subplots(figsize=(9.5, 5.6)); npol = 0; npla = 0
for b in pol_cells:
    P = sorted((r[2], r[3]) for r in recN if r[1] == "polar" and r[0] == b)
    if len(P) >= 3: axN.plot([p[0] for p in P], [p[1] for p in P], color=PURPLE[1], alpha=.5, lw=1, zorder=1); npol += 1
for b in pla_cells:
    P = sorted((r[2], r[3]) for r in recN if r[1] == "plate" and r[0] == b)
    if len(P) >= 3: axN.plot([p[0] for p in P], [p[1] for p in P], color=GREEN[1], alpha=.55, lw=1, zorder=1); npla += 1

def trendN(grp, col):   # binned MEAN over 0..1 (width 0.1), >=3 pts & >=2 cells per bin
    P = [(r[0], r[2], r[3]) for r in recN if r[1] == grp]
    if len(P) < 5: return
    ts = np.array([p[1] for p in P]); vs = np.array([p[2] for p in P]); bs = [p[0] for p in P]
    bx = []; by = []
    for lo in np.arange(0, 1.0, 0.1):
        m = (ts >= lo) & (ts < lo + 0.1); ncell = len({bs[j] for j in np.where(m)[0]})
        if m.sum() >= 3 and ncell >= 2: bx.append(lo + 0.05); by.append(float(vs[m].mean()))
    if len(bx) >= 2: axN.plot(bx, by, color=col, lw=3, zorder=4)
trendN("polar", PURPLE[0]); trendN("plate", GREEN[0])
axN.axvline(0, color="#333", ls=":", lw=.8); axN.set_xlim(0, 1)
axN.set_xlabel("Mitotic progress (fraction of metaphase to anaphase window)")
axN.set_ylabel("Distance to metaphase plate (µm)")
axN.legend(handles=[Line2D([0], [0], color=PURPLE[0], lw=3, label=f"polar-marked KTs — group mean (N={npol})"),
                    Line2D([0], [0], color=PURPLE[1], lw=1, label="polar-marked (individual cells)"),
                    Line2D([0], [0], color=GREEN[0], lw=3, label=f"plate-control KTs — group mean (N={npla})"),
                    Line2D([0], [0], color=GREEN[1], lw=1, label="plate-control (individual TrackMate tracks)")], fontsize=8)
axN.set_title(f"Distance to metaphase plate vs normalized mitotic progress — polar-marked vs plate-control KTs "
              f"({len(win_cells)} cells with usable meta-to-ana window)", loc="left", fontweight="bold", fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time_normalized.png", bbox_inches="tight"); plt.close()
print(f"G4_plate_distance_time_normalized -> {OUT} : {len(recN)} pts, polar cells {npol}, plate cells {npla}, total cells {len(win_cells)}")
