#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_velocity_vs_distance.
Rebuilds ONLY this figure from data/G4_velocity_vs_distance.csv (dist_um,velocity_um_per_min).
Ported from group4_movement.py (the "velocity vs distance-from-plate" block, ~L488-502).
Imports ONLY shared styling/labels from lib. $KTFIG_OUT overrides the output dir (scratch verify);
default = the real group4/ path. Emits PNG (+ editable SVG into OUT/illustrator/) only under OUT."""
import os, sys, csv
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_velocity_vs_distance.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
# inline journal rcParams (parity with lib.apply_style, WITHOUT its savefig wrapper that writes SVG/PDF to
# fixed drive paths — keeps scratch verification side-effect-free).
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 300, "figure.facecolor": "white",
    "savefig.facecolor": "white", "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 12,
    "axes.linewidth": 1.0, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"})

# ---- load this figure's own CSV (already outlier-filtered at build time: |v|<=40 µm/min) ----
vd = []
with open(DATA) as f:
    for row in csv.DictReader(f):
        try: vd.append((float(row["dist_um"]), float(row["velocity_um_per_min"])))
        except (ValueError, KeyError): pass

fig, ax = plt.subplots(figsize=(7, 5))
if vd:
    _d = [p[0] for p in vd]; _v = [p[1] for p in vd]
    ax.scatter(_d, _v, s=14, color="#2166ac", alpha=.5, edgecolor="none")
    ax.axhline(0, color="#999", lw=.8, ls=":")
    if len(_d) >= 5:
        _m, _b = np.polyfit(_d, _v, 1)
        _xr = np.linspace(min(_d), max(_d), 20)
        ax.plot(_xr, _m*_xr + _b, "--", color="#b30000", lw=1.6, label=f"trend (slope {_m:.2f})")
        ax.legend(fontsize=8)
# ITEM 10 sign convention: v = d(distance-to-plate)/dt -> + = away from plate (toward pole), - = toward plate
ax.set_xlabel("Distance to metaphase plate (µm)")
ax.set_ylabel("Velocity vs plate (µm/min; + = toward pole, − = toward plate)")
ax.set_title(f"Polar/sisterless-KT velocity vs distance from plate (N={len(vd)} steps)",
             loc="left", fontweight="bold", fontsize=10.5)
plt.tight_layout()
png = f"{OUT}/G4_velocity_vs_distance.png"; plt.savefig(png, bbox_inches="tight")
_ad = os.path.join(OUT, "illustrator"); os.makedirs(_ad, exist_ok=True)
plt.savefig(os.path.join(_ad, "G4_velocity_vs_distance.svg"), bbox_inches="tight")
plt.close()
print(f"G4_velocity_vs_distance -> {png}  (N={len(vd)} steps)")
