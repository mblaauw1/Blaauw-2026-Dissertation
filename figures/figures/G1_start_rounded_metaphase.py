#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_start_rounded_metaphase.
Rebuilds ONLY this figure from data/G1_start_rounded_metaphase.csv
(batch,cohort,start_roundness,mitotic_duration_min — cohort already has the off-target
controls merged into 'Off-Target/Control'). Ported from group1_roundness.py::startround(_meta_round,...).
Imports ONLY shared styling helpers from lib. Output dir honors $KTFIG_OUT (scratch override);
default = the real group1/ path.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from scipy import stats
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_start_rounded_metaphase.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)
XLABEL = "Roundness at metaphase onset (outline nearest metaphase start)"
TITLE = "Does shape at metaphase onset affect metaphase duration?"

_ORDER = ["unModified", "1-Sister", "2-Sister", "3-Sister", "4-Sister", "Off-Target/Control"]
def _okey(g): return _ORDER.index(g) if g in _ORDER else 99

sx, sy, sg, srow = [], [], [], []
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["cohort"].strip()
        r = float(row["start_roundness"]); d = float(row["mitotic_duration_min"])
        sx.append(r); sy.append(d); sg.append(g); srow.append(row["batch"])
sx = np.array(sx); sy = np.array(sy); sg = np.array(sg)

fig, ax = plt.subplots(figsize=(7.8, 5.6))
for r, d, g in zip(sx, sy, sg):
    ax.scatter(r, d, s=26, color=lib.PALETTE.get(g, "#999"), alpha=.8, edgecolor="white", lw=.4)

# cohort legend (dot colour) with per-cohort N
cohan = [Line2D([0], [0], marker="o", ls="", mfc=lib.PALETTE.get(g, "#999"), mec="white", ms=7,
                label=f'{lib.lbl(g).replace(chr(10)," ")} (N={int((sg==g).sum())})')
         for g in sorted(set(sg), key=_okey)]

# overall trend: Spearman + OLS dashed black line
rho = pp = float("nan"); trendan = []
if len(sx) >= 5:
    rho, pp = stats.spearmanr(sx, sy)
    m, bb = np.polyfit(sx, sy, 1); xx = np.linspace(sx.min(), sx.max(), 50)
    ax.plot(xx, m * xx + bb, color="#111", lw=2, ls="--", zorder=5)
    trendan.append(Line2D([0], [0], color="#111", lw=2, ls="--",
                          label=f"all cells (Spearman rho={rho:.2f}, p={pp:.2g})"))
# per-group OLS trend (N>=4)
for g in sorted(set(sg), key=_okey):
    mflag = sg == g
    if mflag.sum() >= 4:
        m, bb = np.polyfit(sx[mflag], sy[mflag], 1); xx = np.linspace(sx[mflag].min(), sx[mflag].max(), 20)
        ax.plot(xx, m * xx + bb, color=lib.PALETTE.get(g, "#999"), lw=1.6, zorder=4)
        trendan.append(Line2D([0], [0], color=lib.PALETTE.get(g, "#999"), lw=1.6,
                              label=f"{lib.lbl(g).replace(chr(10),' ')} trend"))

ax.set_xlabel(XLABEL); ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
leg1 = ax.legend(handles=cohan, fontsize=6, ncol=2, loc="upper right", title="cohort (dot color)", title_fontsize=6.5)
ax.add_artist(leg1)
if trendan: ax.legend(handles=trendan, fontsize=6.5, loc="upper left", title="trend lines", title_fontsize=7)
ax.set_title(TITLE, loc="left", fontweight="bold", fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_start_rounded_metaphase.png", bbox_inches="tight"); plt.close()
print(f"G1_start_rounded_metaphase -> {OUT}  Spearman rho={rho:.3f} p={pp:.3g} (N={len(sx)})")
