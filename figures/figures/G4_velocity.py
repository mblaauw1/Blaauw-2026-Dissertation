#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_velocity.
Rebuilds ONLY this figure from data/G4_velocity.csv (cohort,velocity_um_per_min).
Ported from group4_movement.py (velocity section). Stacked histogram of polar/sisterless-KT
velocity relative to the metaphase plate, coloured by ablation cohort. Sign: + = away from
plate (toward pole), − = toward plate. Imports ONLY lib. Output dir honors $KTFIG_OUT
(scratch override); default = the real group4/ path.
Exclusions (LONG_SAMPLE, OSC glitch batches, |v|>40 µm/min S55 outlier, unassigned cohort)
are already baked into the CSV.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_velocity.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

vel = []   # (cohort, velocity)
with open(DATA) as f:
    for row in csv.DictReader(f):
        vel.append((row["cohort"].strip(), float(row["velocity_um_per_min"])))
_velv = [v for g, v in vel]
_velgs = sorted(set(g for g, _ in vel), key=lambda g: (g == "", g))

fig, ax = plt.subplots(figsize=(6.8, 4.6))
if vel:
    _bins = np.linspace(min(_velv), max(_velv), 25)
    ax.hist([[v for gg, v in vel if gg == g] for g in _velgs], bins=_bins, stacked=True,
            color=[lib.PALETTE.get(g, "#888") for g in _velgs],
            label=[f"{lib.lbl(g).splitlines()[0]} (N={sum(1 for gg, _ in vel if gg == g)})" for g in _velgs], alpha=.9)
    ax.axvline(np.median(_velv), color="#b30000", ls="--", lw=1.5, label=f"median {np.median(_velv):.2f} µm/min")
ax.axvline(0, color="#333", lw=.8, ls=":")
ax.set_xlabel("Velocity relative to plate (µm/min;  + = away from plate / toward pole,  − = toward plate)")
ax.set_ylabel("count")
ax.legend(fontsize=7.5, title="ablation group")
ax.set_title(f"Polar/sisterless-KT velocity relative to metaphase plate, by ablation group (N={len(_velv)} steps)",
             loc="left", fontweight="bold", fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_velocity.png", bbox_inches="tight"); plt.close()
print("G4_velocity ->", f"{OUT}/G4_velocity.png", "N=", len(_velv), "median", round(float(np.median(_velv)), 3),
      {g: sum(1 for gg, _ in vel if gg == g) for g in _velgs})
