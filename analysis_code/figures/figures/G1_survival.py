#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_survival.
KM-style step: fraction of cells NOT yet at anaphase vs time in metaphase, by cohort.
Rebuilds ONLY this figure from data/G1_survival.csv (batch,cohort,mitotic_duration_min).
Ported from group1_build.py (survival block). Imports ONLY shared styling from lib.
Matched off-target partitions (1/2/3-Sister Controls) are drawn dashed; the "all off-target"
and Double-Chromosome curves were removed per 2026-07-06 feedback (absent from the CSV).
Honors $KTFIG_OUT (scratch override); default = the real group1 path.
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_survival.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)

# same cohort order as the builder (unmodified + on-target 1/2/3 + matched off-target partitions)
SURV = ["unModified", "1-Sister", "2-Sister", "3-Sister",
        "1-Sister Controls", "2-Sister Controls", "3-Sister Controls"]
vals = {k: [] for k in SURV}
with open(DATA) as f:
    for row in csv.DictReader(f):
        k = row["cohort"].strip()
        if k in vals:
            vals[k].append(float(row["mitotic_duration_min"]))

fig, ax = plt.subplots(figsize=(8.6, 5.2))
for k in SURV:
    d = sorted(vals[k])
    if len(d) < 3:
        continue
    xs = np.sort(d); ys = 1 - np.arange(1, len(xs) + 1) / len(xs)
    ls = "-" if "Controls" not in k else (0, (4, 1.5))           # off-target partitions dashed
    ax.step(np.concatenate([[0], xs]), np.concatenate([[1], ys]), where="post",
            color=lib.PALETTE[k], lw=2, ls=ls,
            label=f"{lib.lbl(k).replace(chr(10), ' ')} (N={len(xs)})")
ax.set_xlabel("Time in metaphase (min)"); ax.set_ylabel("Fraction not yet at anaphase")
ax.set_title("Survival — time to anaphase by cohort", loc="left", fontweight="bold", fontsize=11)
ax.legend(fontsize=7, ncol=2, loc="upper right"); ax.set_ylim(0, 1.02)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_survival.png", bbox_inches="tight"); plt.close()
print("G1_survival ->", f"{OUT}/G1_survival.png", {k: len(vals[k]) for k in SURV})
