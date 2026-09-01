#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_exhaustion_violin.
Rebuilds ONLY this figure from data/G4_exhaustion_violin.csv (batch,group,minutes,
in_metaphase_at_start,censored). Ported from group4_exhaustion_violin.py::build_exhaustion(False).
Imports ONLY shared styling helpers from lib. Output dir honors $KTFIG_OUT (scratch override);
default = the real group4/ path.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_exhaustion_violin.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

# ---- load this figure's own CSV -----------------------------------------------------------------
# group column values: 1-sisterless / 2-sisterless / 3-sisterless / colcemid / nocodazole
order = ["1-sisterless", "2-sisterless", "3-sisterless", "colcemid", "nocodazole"]
G = {g: [] for g in order}                     # g -> list of (minutes, in_metaphase_at_start, censored)
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["group"].strip()
        if g not in G:  # be tolerant of case
            g = g.lower()
        if g not in G:
            continue
        G[g].append((float(row["minutes"]), int(row["in_metaphase_at_start"]), int(row["censored"])))

XLAB = {"1-sisterless": "1-Sisterless", "2-sisterless": "2-Sisterless", "3-sisterless": "3-Sisterless",
        "colcemid": "colcemid\n(exhaustion)", "nocodazole": "nocodazole\n(exhaustion)"}
PAL = {"1-sisterless": lib.PALETTE["1-Sister"], "2-sisterless": lib.PALETTE["2-Sister"],
       "3-sisterless": lib.PALETTE["3-Sister"], "colcemid": "#b35806", "nocodazole": "#2166ac"}
IMS_COLOR = "#d62728"   # in-metaphase-at-start (red)

fig, ax = plt.subplots(figsize=(10, 7.4))
for i, g in enumerate(order):
    vals = [v[0] for v in G[g]]
    if len(vals) >= 2:
        for bd in ax.violinplot([vals], positions=[i], widths=.8, showextrema=False)['bodies']:
            bd.set_facecolor(PAL[g]); bd.set_alpha(.25); bd.set_edgecolor(PAL[g])
    for (val, ims, cens) in G[g]:
        col = IMS_COLOR if ims else '#9a9a9a'
        ax.scatter(i + (np.random.RandomState(int(val * 7) % 99).rand() - .5) * .28, val, s=26,
                   facecolor=("none" if cens else col), edgecolor=col, lw=1.1, alpha=.85, zorder=3,
                   marker=("^" if cens else "o"))
    if vals:
        ax.hlines(np.median(vals), i - .32, i + .32, color=PAL[g], lw=2.6, zorder=4)
        ax.hlines(np.mean(vals), i - .28, i + .28, color=PAL[g], lw=1.4, ls=(0, (2, 1.5)), zorder=4)
        ax.text(i, max(vals) + 3, f"x̄ {lib.mmss(np.mean(vals))}\nmed {lib.mmss(np.median(vals))}\nN={len(vals)}",
                ha="center", va="bottom", fontsize=7.5)
ax.set_xticks(range(len(order))); ax.set_xticklabels([XLAB[g] for g in order])
ax.set_ylabel("Time in mitosis (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("Metaphase duration (sisterless) vs\nmitotic-exhaustion controls (colcemid, nocodazole)",
             loc="left", fontweight="bold", fontsize=10)
ax.legend(handles=[Line2D([0], [0], marker='o', color='w', markerfacecolor=IMS_COLOR, markeredgecolor=IMS_COLOR, label='in metaphase at start of imaging', ms=8),
                   Line2D([0], [0], marker='o', color='w', markerfacecolor='#888', markeredgecolor='#888', label='not (NEBD captured)', ms=8),
                   Line2D([0], [0], marker='^', color='w', markerfacecolor='none', markeredgecolor=IMS_COLOR, label='in metaphase + right-censored (red triangle)', ms=8),
                   Line2D([0], [0], marker='^', color='w', markerfacecolor='none', markeredgecolor='#888', label='not-captured + right-censored', ms=8),
                   Line2D([0], [0], color='#555', lw=2.6, label='median'),
                   Line2D([0], [0], color='#555', lw=1.4, ls=(0, (2, 1.5)), label='mean')],
          fontsize=7.5, loc="upper left")

# ---- pairwise significance ON the plot (Mann-Whitney U, adjacent pairs) --------------------------
def _stars(p): return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
_gv = {g: [v[0] for v in G[g]] for g in order}
def _mwu(gi, gj):
    a, b = _gv[order[gi]], _gv[order[gj]]
    return stats.mannwhitneyu(a, b, alternative="two-sided").pvalue if (len(a) >= 3 and len(b) >= 3) else None
_ymaxall = max((max(v) for v in _gv.values() if v), default=1); _dh = _ymaxall * 0.045
_pairs = [(0, 1), (1, 2), (2, 3), (3, 4)]
_ytops = []
for k, (gi, gj) in enumerate(_pairs):
    p = _mwu(gi, gj)
    if p is None: continue
    base = max(max(_gv[order[gi]]), max(_gv[order[gj]]))
    y = base + _dh * 2 + k * _dh * 1.5
    ax.plot([gi, gi, gj, gj], [y, y + _dh * .35, y + _dh * .35, y], color="#333", lw=1.0, clip_on=False)
    ax.text((gi + gj) / 2, y + _dh * .42, f"{_stars(p)} p={p:.2g}", ha="center", va="bottom", fontsize=7.2)
    _ytops.append(y + _dh)
if _ytops: ax.set_ylim(top=max(_ytops) + _dh * 2)

_para = ("How to read this plot:  Each point is one cell's time in mitosis.  The sisterless groups (1/2/3-Sisterless) "
         "are metaphase-to-anaphase durations after laser-ablating that many kinetochores' sister KTs.  The two "
         "EXHAUSTION CONTROLS are cells arrested by spindle poisons — colcemid (microtubule depolymerizer) and "
         "nocodazole — which hold an unsatisfiable spindle-assembly checkpoint until the arrest 'exhausts' (slippage); "
         "they set the ceiling for how long these cells can stay in mitosis.\n"
         "RED points = the cell was already in metaphase when imaging started, so its true mitotic entry (NEBD) was not "
         "captured and its plotted duration is a LOWER BOUND.  GREY points = NEBD was captured.  OPEN TRIANGLES = "
         "right-censored: the cell had not exited mitosis by the end of the movie, so its value is a minimum.  Solid bar = "
         "median, dashed bar = mean.  Brackets = Mann–Whitney U (ns / * <.05 / ** <.01 / *** <.001); the full 5×5 "
         "pairwise grid is in G4_exhaustion_statgrid.")
fig.text(0.02, 0.015, _para, ha="left", va="bottom", fontsize=7.4, wrap=True, color="#222")
plt.tight_layout(rect=[0, 0.20, 1, 1])
plt.savefig(f"{OUT}/G4_exhaustion_violin.png", bbox_inches="tight"); plt.close()
print("G4_exhaustion_violin ->", f"{OUT}/G4_exhaustion_violin.png", {g: len(G[g]) for g in order})
