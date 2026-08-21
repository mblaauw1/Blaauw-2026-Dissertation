#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_start_rounded_metaphase_statgrid.
Per-group Spearman (rho, p, N) table BEHIND each trend line of the start-rounded-at-metaphase-onset
plot. This is a DERIVED companion of G1_start_rounded_metaphase: it recomputes the per-group
correlation directly from that plot's scatter CSV (data/G1_start_rounded_metaphase.csv), so N per
group is guaranteed identical to the scatter (off-target controls already merged there).
Ported from group1_roundness.py::metaphase_statgrid(). Imports ONLY lib. Honors $KTFIG_OUT.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from scipy import stats
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
BASE = "/Volumes/4 MB/ablation_plots/data/G1_start_rounded_metaphase.csv"   # the scatter this grid summarises
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)
METRIC_DESC = "roundness at metaphase onset"; TITLE_LEAD = "Shape at metaphase onset"

_ORDER = ["unModified", "1-Sister", "2-Sister", "3-Sister", "4-Sister", "Off-Target/Control"]
def _okey(g): return _ORDER.index(g) if g in _ORDER else 99

pts = []   # (cohort, roundness, duration)
with open(BASE) as f:
    for row in csv.DictReader(f):
        pts.append((row["cohort"].strip(), float(row["start_roundness"]), float(row["mitotic_duration_min"])))
groups = sorted(set(p[0] for p in pts), key=_okey)

def sp(sub):
    if len(sub) >= 3:
        return stats.spearmanr([x[1] for x in sub], [x[2] for x in sub])
    return float("nan"), float("nan")

tbl_rows = []
rho, pp = sp(pts); tbl_rows.append(("All cells", len(pts), rho, pp, "#111"))
for g in groups:
    sub = [p for p in pts if p[0] == g]; rho, pp = sp(sub)
    tbl_rows.append((lib.lbl(g).replace(chr(10), " "), len(sub), rho, pp, lib.PALETTE.get(g, "#111")))

fig, ax = plt.subplots(figsize=(7.4, 0.9 + 0.46 * len(tbl_rows))); ax.axis("off")
col_labels = ["group", "N", "Spearman rho", "p-value"]
cellText = [[nm, str(n), (f"{rho:+.2f}" if rho == rho else "n/a"), (f"{pp:.3g}" if pp == pp else "n/a")]
            for nm, n, rho, pp, _ in tbl_rows]
t = ax.table(cellText=cellText, colLabels=col_labels, loc="center", cellLoc="center", colLoc="center")
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.6)
for j in range(len(col_labels)):
    c = t[0, j]; c.set_facecolor("#eee"); c.set_text_props(fontweight="bold")
for i, (nm, n, rho, pp, col) in enumerate(tbl_rows, start=1):
    t[i, 0].set_text_props(color=col, fontweight="bold")
    if pp == pp and pp < 0.05: t[i, 3].set_text_props(fontweight="bold")
ax.set_title(f"{TITLE_LEAD} vs metaphase duration — per-group Spearman correlation\n"
             f"({METRIC_DESC} vs Meta->Ana duration; off-target controls merged)",
             loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_start_rounded_metaphase_statgrid.png", bbox_inches="tight"); plt.close()
print(f"G1_start_rounded_metaphase_statgrid -> {OUT}  {len(tbl_rows)} rows",
      [(nm, n, None if rho != rho else round(rho, 3)) for nm, n, rho, pp, _ in tbl_rows])
