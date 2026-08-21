#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_violin2_sisterless_1234_journal.
Journal-standard variant of Violin 2 (metaphase duration by cohort): uniform-width KDE
bodies (scale='width', width=0.8, cut=0, points-only for N<6 via lib.journal_violin),
jittered points, solid median bar, dashed + diamond mean, N labels, MM:SS y-axis.
show_uncaptured=False (the not-captured / right-censored band was removed per 2026-07-06).
Rebuilds ONLY this figure from data/G1_violin2_sisterless_1234_journal.csv
(batch,cohort,metaphase_duration_min). Ported from g1_violin2.py::make(...,journal=True).
NB: FIGURE_INDEX lists current_builder=make_zoom_companions.py, but the real source is
g1_violin2.py (index provenance error, flagged). Imports ONLY lib. Honors $KTFIG_OUT.
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_violin2_sisterless_1234_journal.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)

ORDER = ["unModified", "Off-Target/Control", "1-Sister", "2-Sister", "3-Sister", "4-Sister"]
coh = {k: [] for k in ORDER}
with open(DATA) as f:
    for row in csv.DictReader(f):
        k = row["cohort"].strip()
        if k in coh:
            coh[k].append(float(row["metaphase_duration_min"]))
data_v = [coh[k] for k in ORDER]

fig, ax = plt.subplots(figsize=(9, 5.4))
dmax = max((max(d) for d in data_v if d), default=10)
for i, (k, d) in enumerate(zip(ORDER, data_v)):
    if not d:
        continue
    col = lib.PALETTE[k]
    lib.journal_violin(ax, d, i, col, alpha=0.30, lw=1.0)     # scale=width, width=0.8, cut=0, points-only N<6
    jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=14, color=col, alpha=0.8, edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.2, zorder=4)                        # median (solid bar)
    ax.hlines(mean, i - 0.28, i + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)      # mean (dashed bar)
    ax.scatter([i], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    ax.text(i, max(d) + 1.5, f"x̄ {lib.mmss(mean)}\nmed {lib.mmss(med)}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.5, color="#222")
ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER], rotation=30, ha="right", fontsize=8.5)
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.set_title("Violin 2 — metaphase duration by cohort", loc="left", fontweight="bold")
ax.set_ylim(0, dmax + 12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                          markerfacecolor="white", markeredgecolor="#444", label="mean")],
          loc="upper right", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_violin2_sisterless_1234_journal.png", bbox_inches="tight"); plt.close()
print("G1_violin2_sisterless_1234_journal ->", f"{OUT}/G1_violin2_sisterless_1234_journal.png",
      {k: len(coh[k]) for k in ORDER})
