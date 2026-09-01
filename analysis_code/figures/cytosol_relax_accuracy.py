#!/usr/bin/env python3
"""P6: break down the auto-cytosol-background agreement (rel_to_manual_pct) by relax_level.
The pooled offset is median -1.08%; the 6-level relaxation ladder (0=strict, 5=loosest) was never
validated per-level. This shows whether the loose levels (which carry most rows) bias the background."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import lib
lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group5_shape"
os.makedirs(OUT, exist_ok=True)
SRC = ["/Volumes/4 MB/annotations/CYTOSOL_BACKGROUND_MASTER.csv"]
csv.field_size_limit(10 ** 9)

rows = [r for r in csv.DictReader(open(SRC[0]))
        if (r.get("rel_to_manual_pct") or "").strip() not in ("", "nan")]
by = collections.defaultdict(list)
for r in rows:
    try:
        by[int(r["relax_level"])].append(float(r["rel_to_manual_pct"]))
    except Exception:
        pass

levels = sorted(by)
cmap = plt.cm.viridis(np.linspace(0.15, 0.85, len(levels)))
fig, ax = plt.subplots(figsize=(7.8, 5.2))
rows_csv = []
for i, lv in enumerate(levels):
    d = np.asarray(by[lv], float)
    col = cmap[i]
    lib.journal_violin(ax, d, i, col, alpha=0.30, lw=1.0, min_n=6)
    jit = (np.random.RandomState(lv).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=12, color=col, alpha=0.55, edgecolor="white", linewidth=0.2, zorder=3)
    med = float(np.median(d))
    ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.4, zorder=4)
    ax.text(i, 9.0, f"med {med:+.2f}%\nIQR {np.percentile(d,25):+.1f}..{np.percentile(d,75):+.1f}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.5, color="#222")
    for v in d:
        rows_csv.append([lv, v])
ax.axhline(0, ls=":", color="#666", lw=1.2)
# clip the y-axis to the informative band; note the few extreme outliers so nothing is hidden silently
n_below = sum(1 for d in by.values() for v in d if v < -16)
ax.set_ylim(-16, 14)
if n_below:
    ax.text(0.01, 0.01, f"{n_below} trace(s) below −16% off-scale (max −48%)", transform=ax.transAxes,
            fontsize=7, color="#888", va="bottom")
ax.set_xticks(range(len(levels)))
ax.set_xticklabels([f"level {lv}\n{'strict' if lv==0 else 'loose' if lv>=3 else ''}" for lv in levels], fontsize=9)
ax.set_xlabel("cytosol-background relaxation level (0 = strict aperture, 5 = loosest)")
ax.set_ylabel("auto − manual background (% of manual)")
allv = [v for d in by.values() for v in d]
ax.set_title(f"Auto cytosol-background accuracy by relaxation level  (pooled median {np.median(allv):+.2f}%, N={len(allv)})",
             loc="left", fontweight="bold", fontsize=10.5)
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.4, label="median")], loc="upper right", fontsize=8)
fig.tight_layout()
fig.savefig(f"{OUT}/G5shape_cytosol_relax_accuracy.png", dpi=200, bbox_inches="tight")
plt.close(fig)
lib.record_plot("G5shape_cytosol_relax_accuracy", ["relax_level", "rel_to_manual_pct"], rows_csv,
                {"kind": "journal_violin", "metric": "rel_to_manual_pct"}, script=__file__,
                caption="Auto cytosol-background accuracy by relaxation level", source=SRC, key_column="relax_level")
print("wrote G5shape_cytosol_relax_accuracy; per-level medians:",
      {lv: round(float(np.median(by[lv])), 2) for lv in levels})
