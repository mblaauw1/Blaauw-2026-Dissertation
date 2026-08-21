#!/usr/bin/env python3
"""Standalone 1:1:1 builder for G2_kk_distance_percell.
Average KK distance per cell (1/2/3-sisterless) by ablation phase.
Rebuilds ONLY this figure from data/G2_kk_distance_percell.csv
(batch,phase,n_sisterless,avg_kk_um,n_pairs). Ported from group2_kk.py (Plot 2 block).
Imports ONLY shared styling helpers from lib. Output dir honors $KTFIG_OUT.
"""
import os, sys, csv
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as _st
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

ID = "G2_kk_distance_percell"
DATA = f"/Volumes/4 MB/ablation_plots/data/{ID}.csv"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group2"
os.makedirs(OUT, exist_ok=True)

PHASES = ["Prophase", "Prometaphase", "Metaphase"]
PCOL = {"Prophase": "#1b7837", "Prometaphase": "#2166ac", "Metaphase": "#762a83"}
SM = {"1": "o", "2": "s", "3": "^"}   # marker shape by sisterless count

from collections import defaultdict
percell = defaultdict(list)   # phase -> [(avg_kk_um, n_sisterless_str)]
with open(DATA) as f:
    for row in csv.DictReader(f):
        ph = row["phase"].strip()
        if ph in PCOL:
            percell[ph].append((float(row["avg_kk_um"]), row["n_sisterless"].strip()))

fig, ax = plt.subplots(figsize=(6.5, 5))
for i, ph in enumerate(PHASES):
    dd = percell.get(ph, []); d = [v for v, _ in dd]
    if not dd:
        continue
    lib.journal_violin(ax, d, i, PCOL[ph], width=0.45, alpha=.3)
    for (v, sc) in dd:
        ax.scatter(i + (np.random.RandomState(int(v * 97) % 9999).rand() - .5) * .16, v,
                   s=32, color=PCOL[ph], alpha=.85, edgecolor="white", lw=.4, zorder=3,
                   marker=SM.get(sc, "o"))
    ax.hlines(np.median(d), i - .22, i + .22, color=PCOL[ph], lw=2.2)
    ax.hlines(np.mean(d), i - .18, i + .18, color=PCOL[ph], lw=1.4, ls=(0, (2, 1.5)))
    ax.text(i, max(d) + .2, f"x̄ {np.mean(d):.2f}\nmed {np.median(d):.2f}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.5)
ax.set_ylim(top=ax.get_ylim()[1] * 1.18)
_h = [Line2D([0], [0], marker=SM[s], color='w', markerfacecolor='#888', markeredgecolor='#888',
             label=f"{s}-sisterless") for s in "123"]
_h += [Line2D([0], [0], color="#444", lw=2.2, label="median"),
       Line2D([0], [0], color="#444", lw=1.4, ls=(0, (2, 1.5)), label="mean")]
ax.legend(handles=_h, fontsize=8, loc="upper left")
_grp2 = [[v for v, _ in percell[ph]] for ph in PHASES if len(percell.get(ph, [])) >= 2]
if len(_grp2) >= 2:
    _H2, _p2 = _st.kruskal(*_grp2)
    ax.text(.02, .02, f"Kruskal-Wallis across phases: H={_H2:.2f}, p={_p2:.2g}",
            transform=ax.transAxes, fontsize=7.5, va="bottom", ha="left")
ax.set_xticks(range(len(PHASES))); ax.set_xticklabels(PHASES)
ax.set_ylabel("Average KK distance per cell (µm)")
ax.set_title("Average KK distance per cell (1/2/3-sisterless) by phase",
             loc="left", fontweight="bold", fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/{ID}.png", bbox_inches="tight"); plt.close()
print(ID, "->", f"{OUT}/{ID}.png", {ph: len(percell.get(ph, [])) for ph in PHASES})
