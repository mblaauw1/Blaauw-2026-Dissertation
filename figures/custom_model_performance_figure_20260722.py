"""custom_model_performance_figure_20260722.py — render the held-out performance of the structured model.

Reads `_scratch/model_structured_results.json`, written by custom_model_structured_20260722.py, and draws
the two tasks side by side with their baselines and controls. The point of the figure is the COMPARISON:
a model is only interesting if it beats the single-feature baseline, and only believable if the
shuffled-label control sits at chance.

WHAT IS PLOTTED
  left  — plate vs polar (per chromosome), AUC, bar at the median over 200 held-out repeats,
          whisker = 10th-90th percentile across repeats
  right — metaphase duration (per cell), R2, same convention
  The single-feature baseline (chromosome length / summed length) is drawn in a contrasting colour, and
  the shuffled-label control is drawn last so it is obvious where chance lies.

PROTOCOL (shown on the figure so it travels with the PNG into the deck)
  30% of EACH sisterless group held out, split BY CELL, 200 repeats, all feature selection INSIDE the
  training fold, cohort taken from G1_violin2_mitotic_duration (on-target only).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import json
import numpy as np
import matplotlib.pyplot as plt
import lib

lib.apply_style()
OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"
SCRIPT = __file__
RES = "/Volumes/4 MB/_scratch/model_structured_results.json"

d = json.load(open(RES))
nrep = d.get("n_repeats", "?")
A = (d.get("classification") or {}).get("res", {})
B = (d.get("regression") or {}).get("res", {})

# Keep the informative rows; drop the variants that collapsed under the wider feature pool so the figure
# does not imply they are usable (they are reported in the run log instead).
A_ORDER = ["structured", "structured + lagging", "structured (forest)", "length only", "shuffled control"]
B_ORDER = ["structured (ridge)", "structured (forest)", "sum_len only", "predict-mean", "shuffled control"]
NICE = {"structured": "structured model", "structured (ridge)": "structured model",
        "structured (forest)": "structured (random forest)", "structured + lagging": "structured + lagging flag",
        "length only": "chromosome length ALONE", "sum_len only": "summed length ALONE",
        "predict-mean": "predict the mean", "shuffled control": "shuffled labels (chance)"}


def panel(ax, res, order, key, lo, hi, title, xlabel, chance):
    names, med, e_lo, e_hi, cols = [], [], [], [], []
    for k in order:
        v = res.get(k)
        if not v:
            continue
        m = v.get(key)
        if m is None:
            continue
        names.append(NICE.get(k, k)); med.append(m)
        e_lo.append(m - v.get(lo, m)); e_hi.append(v.get(hi, m) - m)
        cols.append("#999999" if "shuffled" in k or "predict-mean" == k
                    else ("#e08214" if "ALONE" in NICE.get(k, k) else "#762a83"))
    y = np.arange(len(names))[::-1]
    ax.barh(y, med, color=cols, edgecolor="#222", lw=.6, height=.62, zorder=3)
    ax.errorbar(med, y, xerr=[e_lo, e_hi], fmt="none", ecolor="#333", elinewidth=1.1,
                capsize=3, zorder=4)
    ax.axvline(chance, color="#c33", ls="--", lw=1.2, zorder=2)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel(xlabel); ax.set_title(title, fontsize=11)
    for yy, m in zip(y, med):
        ax.text(m + (0.012 if m >= chance else -0.012), yy, f"{m:.3f}",
                va="center", ha="left" if m >= chance else "right", fontsize=8)
    ax.grid(axis="x", alpha=.25, zorder=0)


fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.5))
panel(axes[0], A, A_ORDER, "AUC_median", "p10", "p90",
      f"Plate vs polar  ({(d.get('classification') or {}).get('n_chrom','?')} chromosomes, "
      f"{(d.get('classification') or {}).get('n_cells','?')} cells)",
      "held-out AUC   (0.5 = chance)", 0.5)
axes[0].set_xlim(0.35, 0.78)
panel(axes[1], B, B_ORDER, "R2_median", "p10", "p90",
      f"Metaphase duration  ({(d.get('regression') or {}).get('n','?')} cells)",
      "held-out R²   (0 = predicting the mean)", 0.0)
axes[1].set_xlim(-0.65, 0.62)
fig.suptitle("Held-out performance of the structured model", fontsize=13, y=1.005)
fig.text(0.5, -0.045,
         f"30% of EACH sisterless group held out · split BY CELL · {nrep} repeats · feature selection "
         f"INSIDE each training fold\ncohort taken from G1_violin2_mitotic_duration (on-target only) · "
         f"whiskers = 10th–90th percentile across repeats",
         ha="center", fontsize=8, color="#444")
fig.tight_layout()

rows = []
for task, res, key, lo, hi in (("plate_vs_polar", A, "AUC_median", "p10", "p90"),
                               ("metaphase_duration", B, "R2_median", "p10", "p90")):
    for k, v in res.items():
        rows.append([task, k, v.get(key), v.get(lo), v.get(hi), v.get("MAE", "")])
lib.record_plot("G3_model_structured_performance",
                ["task", "model", "score_median", "p10", "p90", "MAE_min"], rows,
                {"protocol": f"30% held out per sisterless group, split by cell, {nrep} repeats",
                 "selection": "block-level, inside training fold only",
                 "cohort": "G1_violin2_mitotic_duration membership, on-target cohorts",
                 "metrics": "AUC (classification), R2 (regression)"},
                SCRIPT, caption="Held-out performance of the structured model vs single-feature baselines",
                key_column="task")
fig.savefig(f"{OUT3}/G3_model_structured_performance.png", dpi=200, bbox_inches="tight")
print(f"saved {OUT3}/G3_model_structured_performance.png")
