# 2026-08-16 (NOTES §1 rule 30): the off-target colour #d6604d is a RED and sat against the
# 1-Sister GREEN in every cohort figure. lib.PALETTE moved it to teal #00a0b0, but these builders
# HARD-CODED the hex and so bypassed the palette entirely — found by a pixel audit of the rendered
# figures, not by reading the code. Hard-coded copies replaced; use lib.PALETTE, never a literal.
#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_zm_by_target.
Rebuilds ONLY this figure from data/G4_zm_by_target.csv (group,batch,metaphase_duration_min).
Ported from group4_drug.py::zm_by_group(). Imports ONLY lib for styling. Honors $KTFIG_OUT.
NOTE: this 3-ZM-group plot is disabled in the deck manifest (ITEM 11 — the 103-min off-target
sample is meaningless in isolation; the full comparison lives in G4_zm_full); it is rebuilt here
as an on-disk figure per the 1:1:1 index. Includes the 103-min off-target sample (NOT dropped here).
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats as _st
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_zm_by_target.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

order = [("ZM on-target", "#1b7837"), ("ZM off-target", "#00a0b0"), ("ZM unmodified", "#6e6e6e")]
vals = {lab: [] for lab, _ in order}
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["group"].strip()
        if g in vals: vals[g].append(float(row["metaphase_duration_min"]))

fig, ax = plt.subplots(figsize=(7.6, 5.4))
for i, (lab, col) in enumerate(order):
    d = vals[lab]
    if not d: continue
    lib.journal_violin(ax, d, i, col, width=.7, alpha=.3)
    ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .18, d, s=18, color=col, alpha=.8, edgecolor="white", lw=.3, zorder=3)
    ax.hlines(np.median(d), i - .3, i + .3, color=col, lw=2.6, zorder=4)
    ax.hlines(np.mean(d), i - .24, i + .24, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=4)
    ax.text(i, max(d) + 1, f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
labs = [lab for lab, _ in order]
_stars = lambda p: "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
_ymax = max((max(v) for v in vals.values() if v), default=1); _yr = _ymax * 0.06; _top = _ymax
for k, (a, b) in enumerate([(0, 1), (1, 2), (0, 2)]):
    da, db = vals[labs[a]], vals[labs[b]]
    if len(da) >= 2 and len(db) >= 2:
        _u, _p = _st.mannwhitneyu(da, db, alternative="two-sided"); yy = _ymax + _yr * (1.6 + k * 2.1)
        ax.plot([a, a, b, b], [yy, yy + _yr * .3, yy + _yr * .3, yy], color="#333", lw=1.0, clip_on=False)
        ax.text((a + b) / 2, yy + _yr * .34, f"{labs[a].split()[-1]} vs {labs[b].split()[-1]}: {_stars(_p)} p={_p:.2g}", ha="center", va="bottom", fontsize=6.3); _top = max(_top, yy + _yr)
ax.set_ylim(top=_top + _yr * 1.5); ax.set_xticks(range(3)); ax.set_xticklabels(labs, fontsize=9)
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.6, label="median"),
                   Line2D([0], [0], color="#444", lw=1.3, ls=(0, (2, 1.5)), label="mean")], loc="upper right", fontsize=7.5)
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("ZM (2µM) — metaphase duration by target group\n(includes the 103-min off-target sample — real, per dish/pos table)", loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_zm_by_target.png", bbox_inches="tight"); plt.close()
print("G4_zm_by_target ->", f"{OUT}/G4_zm_by_target.png", {lab: len(vals[lab]) for lab, _ in order})
