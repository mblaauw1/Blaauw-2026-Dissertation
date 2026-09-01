# 2026-08-16 (NOTES §1 rule 30): the off-target colour #d6604d is a RED and sat against the
# 1-Sister GREEN in every cohort figure. lib.PALETTE moved it to teal #00a0b0, but these builders
# HARD-CODED the hex and so bypassed the palette entirely — found by a pixel audit of the rendered
# figures, not by reading the code. Hard-coded copies replaced; use lib.PALETTE, never a literal.
#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_zm_full.
Rebuilds ONLY this figure from data/G4_zm_full.csv (group,metaphase_duration_min).
Ported from group4_drug.py::zm_full(). Imports ONLY lib for styling. Honors $KTFIG_OUT.
5-group violin (Control, 3-sisterless target-ablated, ZM on/off-target, ZM unmodified) with a
pairwise Mann-Whitney U (two-sided) stats grid below (LZ5: no on-plot significance marks).
The >100-min off-target outlier is already dropped from this figure's CSV (matches the builder).
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
DATA = "/Volumes/4 MB/ablation_plots/data/G4_zm_full.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

# CSV group labels (single-line) -> plotted label (with newline) + colour, in fixed order
SPEC = [("Control (Unmodified)", "Control\n(Unmodified)", "#6e6e6e"),
        ("Target-ablated (3-sisterless)", "Target-ablated\n(3-sisterless)", "#1b7837"),
        ("ZM on-target", "ZM\non-target", "#1b5e20"),
        ("ZM off-target", "ZM\noff-target", "#00a0b0"),
        ("ZM unmodified", "ZM\nunmodified", "#b35806")]
byg = {csvlab: [] for csvlab, _, _ in SPEC}
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["group"].strip()
        if g in byg: byg[g].append(float(row["metaphase_duration_min"]))
groups = [(disp, byg[csvlab], col) for csvlab, disp, col in SPEC]

fig, (ax, axT) = plt.subplots(2, 1, figsize=(10, 8.4), gridspec_kw={"height_ratios": [3, 1.5]})
for i, (lab, d, col) in enumerate(groups):
    if not d: continue
    lib.journal_violin(ax, d, i, col, width=.7, alpha=.3)
    ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .18, d, s=16, color=col, alpha=.8, edgecolor="white", lw=.3, zorder=3)
    ax.hlines(np.median(d), i - .3, i + .3, color=col, lw=2.6, zorder=4)
    ax.hlines(np.mean(d), i - .24, i + .24, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=4)
    ax.text(i, max(d) + 1, f"x̄ {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}\nN={len(d)}", ha="center", va="bottom", fontsize=7)
_stars = lambda p: "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
_ymax = max((max(d) for _, d, _ in groups if d), default=1)
ax.set_ylim(top=_ymax * 1.22)
ax.set_xticks(range(len(groups))); ax.set_xticklabels([g[0] for g in groups], fontsize=8)
# pairwise Mann-Whitney (two-sided) across ALL group pairs -> stats grid
_gshort = ["Control", "Target(3-sis)", "ZM on-tgt", "ZM off-tgt", "ZM unmod"]
_ng = len(groups); _pmat = [["" for _ in range(_ng)] for _ in range(_ng)]
for a in range(_ng):
    for b in range(_ng):
        if a == b: _pmat[a][b] = "—"; continue
        _da, _db = groups[a][1], groups[b][1]
        if len(_da) >= 2 and len(_db) >= 2:
            try:
                _u, _p = _st.mannwhitneyu(_da, _db, alternative="two-sided"); _pmat[a][b] = f"{_p:.2g} {_stars(_p)}"
            except Exception: _pmat[a][b] = "n/a"
        else: _pmat[a][b] = "n/a"
axT.axis("off")
_tbl = axT.table(cellText=_pmat, rowLabels=_gshort, colLabels=_gshort, loc="center", cellLoc="center")
_tbl.auto_set_font_size(False); _tbl.set_fontsize(7.5); _tbl.scale(1, 1.5)
axT.set_title("Pairwise metaphase-duration comparison — Mann–Whitney U (two-sided): p-value + significance", fontsize=9, loc="left")
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.6, label="median"),
                   Line2D([0], [0], color="#444", lw=1.3, ls=(0, (2, 1.5)), label="mean")], loc="upper right", fontsize=7.5)
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)"); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("ZM sensitivity — full comparison (Control, 3-sisterless target-ablated, ZM on/off-target, ZM unmodified)", loc="left", fontweight="bold", fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_zm_full.png", bbox_inches="tight"); plt.close()
print("G4_zm_full ->", f"{OUT}/G4_zm_full.png", {g[0].replace(chr(10), ' '): len(g[1]) for g in groups})
