"""Metaphase duration expressed as a DIFFERENCE from the unmodified-cohort MEAN (not absolute time).
Same canonical cohort membership as the main violin (lib.assign_cohorts): unmodified centres at 0 by
construction; every other cohort shows how much longer/shorter its cells sit in metaphase relative to the
unmodified average. Companion to the absolute-time violin (g1_violin2). Writes PNG + editable PDF + CSV."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT = __file__
coh = {k: [(b, v) for b, v in lst if "hec1" not in b.lower()] for k, lst in lib.assign_cohorts().items()}
ORDER = ["unModified", "Off-Target/Control", "1-Sister", "2-Sister", "3-Sister"]

unmod = [v for _, v in coh.get("unModified", [])]
if not unmod:
    raise SystemExit("no unmodified cohort values")
BASE = float(np.mean(unmod))   # the reference: mean metaphase duration of unmodified cells

fig, ax = plt.subplots(figsize=(9, 5.4))
rec = []
for i, k in enumerate(ORDER):
    d0 = [v for _, v in coh.get(k, [])]
    if not d0:
        continue
    d = [v - BASE for v in d0]                       # difference from unmodified mean
    col = lib.PALETTE[k]
    lib.journal_violin(ax, d, i, col, alpha=0.30, lw=1.0)   # scale=width, width=0.8, cut=0, points-only N<6
    jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=14, color=col, alpha=0.8, edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.2, zorder=4)
    ax.hlines(mean, i - 0.28, i + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax.scatter([i], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    sgn = "+" if mean >= 0 else "−"
    ax.text(i, max(d) + 1.2, f"{sgn}{abs(mean):.1f} min\nN={len(d)}", ha="center", va="bottom", fontsize=7.5, color="#222")
    for b, v in zip([b for b, _ in coh.get(k, [])], d):
        rec.append([b, k, round(v, 3)])

ax.axhline(0, color="#444", lw=1.2, ls="-", zorder=2)     # 0 = unmodified mean
ax.text(len(ORDER) - 0.5, 0, "  unmodified mean", va="center", ha="left", fontsize=7.5, color="#444")
ax.set_xticks(range(len(ORDER))); ax.set_xticklabels([lib.lbl(k) for k in ORDER], rotation=30, ha="right", fontsize=8.5)
ax.set_ylabel("Metaphase duration relative to unmodified mean (minutes)")
ax.set_title(f"Metaphase duration as difference from the unmodified mean "
             f"(unmodified mean = {lib.mmss(BASE)} = 0)", loc="left", fontweight="bold", fontsize=10.5)
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                          markerfacecolor="white", markeredgecolor="#444", label="mean")],
          loc="upper left", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/metaphase_duration_delta_from_unmodified.png", bbox_inches="tight"); plt.close()

lib.record_plot("metaphase_duration_delta_from_unmodified", ["batch", "cohort", "delta_min_from_unmod_mean"], rec,
    {"type": "violin+points", "metric": "metaphase duration MINUS unmodified-cohort mean",
     "baseline": f"unmodified mean = {BASE:.3f} min", "annot": "mean(diamond)/median; N per cohort"},
    SCRIPT, "Metaphase duration as difference from the unmodified mean")
print("metaphase_duration_delta_from_unmodified ->", {lib.lbl(k).replace(chr(10), ' '): len([v for _, v in coh.get(k, [])]) for k in ORDER}, "| baseline min=", round(BASE, 2))
