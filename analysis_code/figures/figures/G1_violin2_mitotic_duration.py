#!/usr/bin/env python3
"""Standalone 1:1:1 builder for G1_violin2_mitotic_duration.
Violin 2 — metaphase duration by cohort (with matched controls).
Rebuilds ONLY this figure from data/G1_violin2_mitotic_duration.csv
(batch,cohort,metaphase_duration_min). Ported from g1_violin2.py::make(...) for the
["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls","3-Sister",
"3-Sister Controls","Off-Target/Control"] order, show_uncaptured=False (non-journal original).
Imports ONLY shared styling helpers from lib. Output dir honors $KTFIG_OUT (scratch override);
default = the real group1/ path.
"""
import os, sys, csv
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

ID = "G1_violin2_mitotic_duration"
DATA = f"/Volumes/4 MB/ablation_plots/data/{ID}.csv"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group1"
os.makedirs(OUT, exist_ok=True)

ORDER = ["unModified", "1-Sister", "1-Sister Controls", "2-Sister", "2-Sister Controls",
         "3-Sister", "3-Sister Controls", "Off-Target/Control"]
TITLE = "Violin 2 — metaphase duration by cohort (with matched controls)"
WIDTH = 11.5

# ---- load this figure's own CSV (cohort membership already screened upstream) --------------------
coh = {k: [] for k in ORDER}
with open(DATA) as f:
    for row in csv.DictReader(f):
        k = row["cohort"].strip()
        if k in coh:
            coh[k].append((row["batch"], float(row["metaphase_duration_min"])))

data_v = [[v for _, v in coh[k]] for k in ORDER]
fig, ax = plt.subplots(figsize=(WIDTH, 5.4))
dmax = max((max(d) for d in data_v if d), default=10)
for i, (k, d) in enumerate(zip(ORDER, data_v)):
    if not d:
        continue
    col = lib.PALETTE[k]
    if len(d) >= 2:
        vp = ax.violinplot([d], positions=[i], widths=0.8, showextrema=False)
        for b in vp['bodies']:
            b.set_facecolor(col); b.set_alpha(0.30); b.set_edgecolor(col); b.set_linewidth(1.0)
    jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=14, color=col, alpha=0.8,
               edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.2, zorder=4)
    ax.hlines(mean, i - 0.28, i + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax.scatter([i], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    ax.text(i, max(d) + 1.5, f"x̄ {lib.mmss(mean)}\nmed {lib.mmss(med)}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.5, color="#222")
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels([lib.lbl(k) for k in ORDER], rotation=30, ha="right", fontsize=8.5)
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.set_title(TITLE, loc="left", fontweight="bold")
ax.set_ylim(0, dmax + 12)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                          markerfacecolor="white", markeredgecolor="#444", label="mean")],
          loc="upper right", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/{ID}.png", bbox_inches="tight"); plt.close()
print(ID, "->", f"{OUT}/{ID}.png", {k: len(d) for k, d in zip(ORDER, data_v)})
