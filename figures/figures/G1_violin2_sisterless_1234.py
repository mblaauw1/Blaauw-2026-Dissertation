#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_violin2_sisterless_1234 (BASE variant).
Rebuilds ONLY this figure from data/G1_violin2_sisterless_1234.csv
(columns: batch,cohort,metaphase_duration_min). Ported from g1_violin2.py::make(...) — the first
`make(order=[unModified,Off-Target/Control,1-Sister,2-Sister,3-Sister,4-Sister], show_uncaptured=False)`
call (journal=False, statgrid is a SEPARATE figure id and is NOT drawn here). Imports ONLY shared
styling helpers from lib. Output dir honors $KTFIG_OUT (scratch override); default = the real group1 path.

NOTE (journal spacing): the journal-standard version (scale='width', width=0.8, cut=0, points-only N<6 —
the "pointed-tail" feedback fix) is a SEPARATE sibling figure G1_violin2_sisterless_1234_journal; this
BASE figure intentionally keeps the original matplotlib violin body (dual-version, same-artboard design).
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_violin2_sisterless_1234.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)

ORDER = ["unModified", "Off-Target/Control", "1-Sister", "2-Sister", "3-Sister", "4-Sister"]
TITLE = "Violin 2 — metaphase duration by cohort"

# ---- load this figure's own CSV -----------------------------------------------------------------
coh = {k: [] for k in ORDER}
with open(DATA) as f:
    for row in csv.DictReader(f):
        k = row["cohort"].strip()
        if k in coh:
            coh[k].append((row["batch"].strip(), float(row["metaphase_duration_min"])))
data_v = [[v for _, v in coh[k]] for k in ORDER]

fig, ax = plt.subplots(figsize=(9, 5.4))
dmax = max((max(d) for d in data_v if d), default=10)
for i, (k, d) in enumerate(zip(ORDER, data_v)):
    if not d:
        continue
    col = lib.PALETTE[k]
    if len(d) >= 2:                                                     # base variant: standard body
        vp = ax.violinplot([d], positions=[i], widths=0.8, showextrema=False)
        for b in vp['bodies']:
            b.set_facecolor(col); b.set_alpha(0.30); b.set_edgecolor(col); b.set_linewidth(1.0)
    jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=14, color=col, alpha=0.8, edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.2, zorder=4)                    # median (solid bar)
    ax.hlines(mean, i - 0.28, i + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)  # mean (dashed bar)
    ax.scatter([i], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)  # mean marker
    ax.text(i, max(d) + 1.5, f"x̄ {lib.mmss(mean)}\nmed {lib.mmss(med)}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.5, color="#222")

ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER], rotation=30, ha="right", fontsize=8.5)
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.set_title(TITLE, loc="left", fontweight="bold")
ax.set_ylim(0, dmax + 12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                          markerfacecolor="white", markeredgecolor="#444", label="mean")],
          loc="upper right", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_violin2_sisterless_1234.png", bbox_inches="tight"); plt.close()
print("G1_violin2_sisterless_1234 ->", f"{OUT}/G1_violin2_sisterless_1234.png",
      {lib.lbl(k).replace(chr(10), ' '): len(d) for k, d in zip(ORDER, data_v)})
