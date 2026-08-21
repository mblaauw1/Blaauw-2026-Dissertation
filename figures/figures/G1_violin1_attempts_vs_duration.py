#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_violin1_attempts_vs_duration.
Two-panel scatter: # ablation targets placed vs metaphase duration
(panel A = experimental/on-target 1/2/3-Sister; panel B = off-target controls).
Rebuilds ONLY this figure from data/G1_violin1_attempts_vs_duration.csv
(batch,cohort,n_targets,mitotic_duration_min). The CSV already encodes the builder's
filters (>25 targets excluded, cohort membership = lib.assign_cohorts()); reading it
reproduces exactly the plotted points. Ported from group1_build.py (Violin 1 block).
Imports ONLY shared styling from lib. Honors $KTFIG_OUT (scratch override).
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import linregress
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_violin1_attempts_vs_duration.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)

G = {}                                  # cohort -> (targets[], durations[])
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["cohort"].strip()
        G.setdefault(g, [[], []])
        G[g][0].append(float(row["n_targets"])); G[g][1].append(float(row["mitotic_duration_min"]))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
for ax, (title, groups) in zip(axes, [("Experimental (on-target)", ["1-Sister", "2-Sister", "3-Sister"]),
                                       ("Off-target", ["Off-Target/Control"])]):
    for g in groups:
        if g not in G:
            continue
        xs = np.array(G[g][0], float); ys = np.array(G[g][1], float)
        ax.scatter(xs + np.random.RandomState(1).rand(len(xs)) * 0.3 - 0.15, ys, s=20,
                   color=lib.PALETTE[g], alpha=0.8, edgecolor="white", linewidth=0.3,
                   label=f"{lib.lbl(g).replace(chr(10), chr(32))} (N={len(xs)})")
        if len(xs) >= 3 and np.unique(xs).size >= 2:
            lr = linregress(xs, ys); xln = np.array([xs.min(), xs.max()])
            ax.plot(xln, lr.intercept + lr.slope * xln, color=lib.PALETTE[g], lw=1.7, ls="--", alpha=0.9, zorder=2)
    ax.set_title(title, fontsize=11); ax.set_xlabel("# ablation targets placed"); ax.legend(fontsize=8)
axes[0].set_ylabel("Metaphase duration, metaphase to anaphase (min)")
fig.suptitle("Violin 1 — Ablation attempts vs metaphase duration", x=0.01, ha="left", fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G1_violin1_attempts_vs_duration.png", bbox_inches="tight"); plt.close()
print("G1_violin1_attempts_vs_duration ->", f"{OUT}/G1_violin1_attempts_vs_duration.png",
      {g: len(G[g][0]) for g in G})
