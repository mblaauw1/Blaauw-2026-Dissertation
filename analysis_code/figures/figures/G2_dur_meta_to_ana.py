# 2026-08-16 (NOTES §1 rule 30): the off-target colour #d6604d is a RED and sat against the
# 1-Sister GREEN in every cohort figure. lib.PALETTE moved it to teal #00a0b0, but these builders
# HARD-CODED the hex and so bypassed the palette entirely — found by a pixel audit of the rendered
# figures, not by reading the code. Hard-coded copies replaced; use lib.PALETTE, never a literal.
#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G2_dur_meta_to_ana.
Rebuilds ONLY this figure from data/G2_dur_meta_to_ana.csv (cohort,duration_min).
Ported from group2_build.py::dur_violin(mdur,"Metaphase to Anaphase",...) — the standalone (_own)
variant: jittered points, shaded violin body, solid median / dashed mean, per-cohort N/mean/med text,
Kruskal-Wallis omnibus + pairwise Mann-Whitney vs unmodified in the title. Imports ONLY lib.
Output dir honors $KTFIG_OUT (scratch); default = the real group2/ path.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats as _st
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G2_dur_meta_to_ana.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group2"); os.makedirs(OUT, exist_ok=True)
TITLE = "Metaphase to Anaphase"

ORDER = ["unmodified", "1-Sisterless", "2-Sisterless", "3-Sisterless", "all off-target"]
COL = {"unmodified": "#6e6e6e", "1-Sisterless": lib.PALETTE["1-Sister"],
       "2-Sisterless": lib.PALETTE["2-Sister"], "3-Sisterless": lib.PALETTE["3-Sister"],
       "all off-target": "#00a0b0"}

_cd = {}
with open(DATA) as f:
    for row in csv.DictReader(f):
        _cd.setdefault(row["cohort"].strip(), []).append(float(row["duration_min"]))
cohorts = [c for c in ORDER if c in _cd]

fig, ax = plt.subplots(figsize=(8.5, 5))
for i, lab in enumerate(cohorts):
    d = _cd[lab]; col = COL[lab]
    if len(d) >= 2:
        for b in ax.violinplot([d], positions=[i], widths=0.8, showextrema=False)['bodies']:
            b.set_facecolor(col); b.set_alpha(.3); b.set_edgecolor(col)
    ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .22, d,
               s=14, color=col, alpha=.8, edgecolor="white", lw=.3, zorder=3)
    ax.hlines(np.median(d), i - .34, i + .34, color=col, lw=2.2)
    ax.hlines(np.mean(d), i - .28, i + .28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax.text(i, max(d) + (max(d) * .03 + .5),
            f"N={len(d)}\nmean {lib.mmss(np.mean(d))}\nmed {lib.mmss(np.median(d))}", ha="center", va="bottom", fontsize=6.5)

ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], color="#444", lw=1.4, ls=(0, (2, 1.5)), label="mean")],
          loc="upper left", bbox_to_anchor=(1.005, 1.0), borderaxespad=0, fontsize=7)
ax.set_xticks(range(len(cohorts))); ax.set_xticklabels(cohorts, rotation=20, ha="right", fontsize=9)
ax.set_ylabel(TITLE + " (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_ylim(top=ax.get_ylim()[1] * 1.18)

# stats: Kruskal-Wallis omnibus + pairwise Mann-Whitney vs unmodified
_grps = [v for v in (_cd[c] for c in cohorts) if len(v) >= 2]; _stat = ""
if len(_grps) >= 2:
    try:
        _h, _p = _st.kruskal(*_grps); _stat = f"Kruskal–Wallis p={_p:.2g}"
    except Exception: pass
    _base = _cd.get("unmodified")
    if _base and len(_base) >= 2:
        _pw = []
        for lab in cohorts:
            v = _cd[lab]
            if lab == "unmodified" or len(v) < 2: continue
            try:
                _u, _pp = _st.mannwhitneyu(_base, v, alternative="two-sided")
                _pw.append(f"{lab.split(chr(10))[0]} {('*' if _pp < 0.05 else 'ns')}({_pp:.2g})")
            except Exception: pass
        if _pw: _stat += "  |  vs unmodified: " + ", ".join(_pw)
ax.set_title(TITLE + ("\n" + _stat if _stat else ""), loc="left", fontweight="bold", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G2_dur_meta_to_ana.png", bbox_inches="tight"); plt.close()
print("G2_dur_meta_to_ana ->", OUT, {c: len(_cd[c]) for c in cohorts})
