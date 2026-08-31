#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_lagging_bar.
Rebuilds ONLY this figure from data/G4_lagging_bar.csv
(cohort,fraction_yes,N,n_yes,n_no,fisher_p_vs_unmod). Ported from
group4_polar_lagging.py::bar('Lagging Chromosomes',...). Imports ONLY lib for styling.
Fisher p vs unmodified + overall chi-square are RECOMPUTED here (full precision) from the
n_yes/n_no counts in the CSV, so the plot never shows the round(.,5)->0.0 artifact stored in
the fisher_p_vs_unmod column. Honors $KTFIG_OUT (scratch override); default = real group4/ path.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as _st
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
# 2026-08-18: reads the ALL-COHORT companion, not its own output. group4_polar_lagging.py used to write
# plot_id "G4_lagging_bar" itself and clobbered this file's figure on every re-run (NOTES §8); it now
# writes G4_lagging_bar_allcohorts and this script is the sole owner of "G4_lagging_bar".
_ALL = "/Volumes/4 MB/ablation_plots/data/G4_lagging_bar_allcohorts.csv"
DATA = _ALL if os.path.exists(_ALL) else "/Volumes/4 MB/ablation_plots/data/G4_lagging_bar.csv"
SCRIPT = __file__
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
# USER 2026-08-16: "for that sideways bar plot, remove the 2-sisterless samples from it." ORDER drives the
# bars, the between-cohort chi-square and the pairwise Fisher set, so dropping the cohort here removes it
# from all three. Each Fisher test is cohort-vs-unModified, so the remaining p-values are unaffected; the
# chi-square legitimately changes, since it tests across the cohorts actually shown.
# 🔴 HER 2026-08-20, board-5 item 7: *"plot the bars in the order of unmovified, off-target, 1 sisterless,
# and 3 sisterless from left to right"*. Order comes from the canonical table so it cannot drift from the
# canonical NAMES; the 2-Sister removal above still applies (it is simply not in this list).
import sys as _sys
_sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import canon_labels as _CL
ORDER = _CL.sort_groups(["unModified", "1-Sister", "3-Sister", "Off-Target/Control"])

# USER 2026-08-16: "i want something on that plot to show the idea that triple cells congress chromosomes
# until on average they enter anaphase with less than 1 polar, similar to single sisterless."
# NOT recomputed here: these are the re-derived values from NOTES §14 2026-08-14, from HER behaviour
# determinations, capped at each cell's "# Sisterless KTs". The superseded "no cell enters anaphase with
# more than one polar KT" claim came from _POLAR_AT_ANA (36 of 66 cells, structurally cannot report >1)
# and must never be requoted. Collagen triples stay excluded, as in the published cohort.
POLAR_AT_ANA = {"1-Sister": (0.67, 36), "3-Sister": (0.82, 22)}

frac = {}; Ns = {}; cnt = {}
with open(DATA) as f:
    for row in csv.DictReader(f):
        k = row["cohort"].strip()
        ny = int(row["n_yes"]); no = int(row["n_no"])
        frac[k] = ny / (ny + no); Ns[k] = ny + no; cnt[k] = (ny, no)

present = [k for k in ORDER if k in cnt]

def _stars(p): return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"

# overall between-cohort chi-square (recomputed from counts)
overall_txt = ""
if len(present) >= 2:
    table = np.array([[cnt[k][0], cnt[k][1]] for k in present], float)
    chi2, p_all, dof, exp = _st.chi2_contingency(table)
    low = bool((exp < 5).any())
    overall_txt = f"Between-cohort χ²={chi2:.2f}, df={dof}, p={p_all:.3g}" + \
                  ("  (some expected<5 -> see Fisher pairwise)" if low else "")

# pairwise Fisher vs unmodified (recomputed, full precision)
pw = {}
if "unModified" in cnt:
    uy, un = cnt["unModified"]
    for k in present:
        if k == "unModified": continue
        ky, kn = cnt[k]
        _, pw[k] = _st.fisher_exact([[uy, un], [ky, kn]])

fig, ax = plt.subplots(figsize=(8, 5.2))
for i, k in enumerate(ORDER):
    if k not in frac: continue
    ax.bar(i, frac[k], color=lib.PALETTE[k], alpha=.85, width=.7)
    lab = f"{frac[k]*100:.0f}%\nN={Ns[k]}"
    if k in POLAR_AT_ANA:            # rides with the bar, so it can never land on the rotated tick labels
        lab += f"\n{POLAR_AT_ANA[k][0]:.2f} polar KT/cell at ana"
    if k in pw:
        pk = pw[k]
        lab += f"\nvs unmod {_stars(pk)}\n" + (f"p={pk:.2g}" if pk >= 1e-4 else f"p<1e-4")
    ax.text(i, frac[k] + .02, lab, ha="center", va="bottom", fontsize=7.5)
if overall_txt: ax.text(.012, .845, overall_txt, transform=ax.transAxes, ha="left", va="top", fontsize=8, color="#222")
ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER], rotation=25, ha="right", fontsize=8.5)
ax.set_ylabel("Fraction with Lagging = Yes"); ax.set_ylim(0, 1.32)
# Summary sits OUTSIDE the axes so it cannot collide with the chi-square line inside them (her separate
# complaint: "text overlapping with items on the plot"). ASCII arrow: the "->" glyph was rendering as a
# missing-character box in this font.
if all(k in POLAR_AT_ANA for k in ("1-Sister", "3-Sister")):
    ax.text(0.012, 0.995,
            "Polar KTs per cell at anaphase: single 0.67 vs triple 0.82 (MW p=0.92, indistinguishable) - both BELOW 1:\n"
            "triples congress most of their sisterless KTs and reach anaphase with about the same absolute\n"
            "polar burden as singles (as a fraction of their own sisterless KTs: 0.67 -> 0.27)",
            transform=ax.transAxes, ha="left", va="top", fontsize=7.4, color="#222",
            bbox=dict(fc="#f6f6f6", ec="#bbb", lw=.6, alpha=.95))
ax.set_title("Lagging chromosomes by cohort (normalized to N)", loc="left", fontweight="bold", fontsize=11, pad=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_lagging_bar.png", bbox_inches="tight"); plt.close()

# 2026-08-17: RE-RECORD the data so the figure and its provenance agree. `group4_polar_lagging.bar()`
# writes this plot's CSV with EVERY cohort; this 1:1 builder then re-renders the PNG with the 2026-08-16
# ORDER (2-Sister removed). Until now only the PICTURE lost the cohort — the recorded CSV still listed it,
# so a provenance audit would have reported a cohort the figure does not show. Caught by the item-by-item
# verification, not by looking at the plot, which is exactly the class of error a visual check misses.
_rows = [[k, round(frac[k], 5), Ns[k], cnt[k][0], cnt[k][1],
          # full precision: round(p, 5) turned 3-Sister's true p=4.47e-09 into a recorded 0.0,
          # which is wrong in the provenance record even though the figure itself prints "p<1e-4".
          float(pw[k]) if k in pw else ""]
         for k in ORDER if k in cnt]
lib.record_plot("G4_lagging_bar",
                ["cohort", "fraction_yes", "N", "n_yes", "n_no", "fisher_p_vs_unmod"], _rows,
                {"type": "bar (fraction Yes)", "normalize": "within cohort",
                 "cohorts_shown": ORDER,
                 "dropped": "2-Sister (user 2026-08-16)",
                 "annotation": "polar KTs per cell at anaphase (NOTES 2026-08-14): 1-sis 0.67 n=36, "
                               "3-sis 0.82 n=22, MW p=0.92",
                 "overall": overall_txt},
                SCRIPT, "Lagging chromosomes by cohort (2-sisterless removed; polar-at-anaphase annotated)")
print("G4_lagging_bar ->", f"{OUT}/G4_lagging_bar.png", {k: (round(frac[k], 3), Ns[k]) for k in present},
      "| overall:", overall_txt, "| fisher:", {k: round(pw[k], 6) for k in pw})
