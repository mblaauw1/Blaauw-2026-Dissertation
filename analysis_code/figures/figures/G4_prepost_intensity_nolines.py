#!/usr/bin/env python3
"""Standalone 1:1 builder for G4_prepost_intensity_nolines.
Rebuilds ONLY this figure from data/G4_prepost_intensity_nolines.csv
(batch,kt,pre_over_cytosol,post_over_cytosol). Ported from group4_prepost.py::render(False) — the
'connector lines removed' companion of G4_prepost_intensity. Imports ONLY shared styling from lib.
Output honors $KTFIG_OUT (default = real group4/).

Each row = one KT's own pre value and post value (kt in {targeted,paired}). The CSV is already the
POST-removal filtered/floored data the figure plots (broken-bg, increasing-targeted, near-flat,
sharp-paired removals + floor-at-0 all applied when the CSV was written), so this script does NOT
re-derive: it renders the four columns, medians/means, N labels, and Wilcoxon pre-vs-post."""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from scipy import stats
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_prepost_intensity_nolines.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
R = int(os.environ.get("KT_R", "9"))

# ---- load this figure's own CSV ----------------------------------------------------------------
tgt_pre = []; tgt_post = []; par_pre = []; par_post = []; batches = set()
with open(DATA) as f:
    for row in csv.DictReader(f):
        b = row["batch"].strip(); kt = row["kt"].strip(); batches.add(b)
        pre = float(row["pre_over_cytosol"]); post = float(row["post_over_cytosol"])
        if kt == "targeted": tgt_pre.append(pre); tgt_post.append(post)
        elif kt == "paired": par_pre.append(pre); par_post.append(post)
ncell = len(batches)

TC = "#d62728"; SC = "#1f77b4"
fig, ax = plt.subplots(figsize=(7.4, 5.6))
ax.set_yscale("symlog", linthresh=2000)   # KT intensities span orders of magnitude (bright pre -> ~bg post)

def box(x, vals, col):
    if not vals: return
    ax.scatter([x] * len(vals), vals, color=col, s=10, alpha=.5, zorder=1)
    md_ = np.median(vals); ax.hlines(md_, x - .18, x + .18, color=col, lw=2.5, zorder=3)      # median = solid
    mn_ = np.mean(vals);   ax.hlines(mn_, x - .14, x + .14, color=col, lw=1.2, ls=(0, (2, 1.5)), zorder=3)  # mean = dashed
    _left = (int(round(x)) % 2 == 0)
    ax.text(x - .22 if _left else x + .22, md_, f"med {md_:,.0f}", color=col, fontsize=6.8,
            ha=("right" if _left else "left"), va="center")
box(0, tgt_pre, TC); box(1, tgt_post, TC); box(2, par_pre, SC); box(3, par_post, SC)

ax.legend(handles=[mlines.Line2D([], [], color="#333", lw=2.5, ls="-"),
                   mlines.Line2D([], [], color="#333", lw=1.2, ls=(0, (2, 1.5)))],
          labels=["median", "mean"], fontsize=7, ncol=2, loc="upper center",
          bbox_to_anchor=(0.5, 0.99), framealpha=.9)
# significance pre vs post — targeted AND paired
if tgt_pre:
    w = stats.wilcoxon(tgt_pre, tgt_post).pvalue if len(tgt_pre) > 5 else float('nan')
    ax.text(.5, ax.get_ylim()[1] * .97, f"targeted pre vs post\nWilcoxon p={w:.2g}", ha="center", va="top", fontsize=8, color=TC)
if par_pre and len(par_pre) > 5:
    wp = stats.wilcoxon(par_pre, par_post).pvalue
    ax.text(2.5, ax.get_ylim()[1] * .97, f"paired pre vs post\nWilcoxon p={wp:.2g}", ha="center", va="top", fontsize=8, color=SC)
for x, vals in [(0, tgt_pre), (1, tgt_post), (2, par_pre), (3, par_post)]:
    if vals: ax.text(x, ax.get_ylim()[0], f"N={len(vals)}", ha="center", va="top", fontsize=7, color="#444")
ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["targeted\npre", "targeted\npost", "paired\npre", "paired\npost"])
ax.set_xlim(-0.6, 3.6)
ax.set_ylabel(f"KT eYFP intensity (Σ in r={R} disk, background-subtracted)")
ax.set_title(f"Pre- vs post-ablation KT intensity (N={len(tgt_pre)} ablations, {ncell} cells)\n"
             "paired connector lines removed", loc="left", fontweight="bold", fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_prepost_intensity_nolines.png", bbox_inches="tight"); plt.close()
print(f"G4_prepost_intensity_nolines -> {OUT}/G4_prepost_intensity_nolines.png  targeted N={len(tgt_pre)}, paired N={len(par_pre)}, cells={ncell}")
