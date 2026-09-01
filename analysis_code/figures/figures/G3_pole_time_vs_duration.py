#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G3_pole_time_vs_duration.
Rebuilds ONLY this figure from data/G3_pole_time_vs_duration.csv
(batch,n_sisterless,chromosome,pole_time_min,mitotic_duration_min).
Ported from group3_pole_time.py. One point PER KINETOCHORE (no averaging).
Imports ONLY shared styling helpers from lib. Output dir honors $KTFIG_OUT
(scratch override); default = the real group3/ path.
All source-level exclusions (Mad1 / REVIEW_EXCLUDE / double-chromosome /
plate-join-before-metaphase D13) are already baked into the CSV.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.ticker import FuncFormatter
from scipy import stats
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G3_pole_time_vs_duration.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group3"); os.makedirs(OUT, exist_ok=True)

PAL = {"1": lib.PALETTE["1-Sister"], "2": lib.PALETTE["2-Sister"], "3": lib.PALETTE["3-Sister"]}

xs = []; ys = []; cs = []
with open(DATA) as f:
    for row in csv.DictReader(f):
        p = float(row["pole_time_min"])
        if p < 0:   # D13 guard (already applied in CSV; belt-and-suspenders)
            continue
        xs.append(p); ys.append(float(row["mitotic_duration_min"])); cs.append(row["n_sisterless"].strip())
xs = np.array(xs); ys = np.array(ys); cs = np.array(cs)

fig, ax = plt.subplots(figsize=(8, 5.6))
for n in "123":
    m = cs == n
    if m.any():
        ax.scatter(xs[m], ys[m], s=34, color=PAL[n], alpha=.85, edgecolor="white", lw=.4,
                   label=f"{n}-sisterless (n={m.sum()} KTs)")
rho = p = None
if len(xs) >= 5:
    rho, p = stats.spearmanr(xs, ys)   # S40: NO all-data black-dashed trend; keep per-group
for n in "123":
    mm = cs == n
    if mm.sum() >= 4:
        m, b0 = np.polyfit(xs[mm], ys[mm], 1); xr = np.linspace(xs[mm].min(), xs[mm].max(), 20)
        ax.plot(xr, m * xr + b0, color=PAL[n], lw=1.5)
ax.set_xlabel("Time at pole before congression (min after metaphase)")
ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(fontsize=8)
ax.set_title("Time-at-pole-before-congression vs metaphase duration (per kinetochore)"
             + (f"  ·  Spearman rho={rho:.2f}, p={p:.2g}" if rho is not None else ""),
             loc="left", fontweight="bold", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_pole_time_vs_duration.png", bbox_inches="tight"); plt.close()
print("G3_pole_time_vs_duration ->", f"{OUT}/G3_pole_time_vs_duration.png",
      {n: int((cs == n).sum()) for n in "123"}, "Spearman", (round(rho, 3), float(f"{p:.2g}")) if rho is not None else None)
