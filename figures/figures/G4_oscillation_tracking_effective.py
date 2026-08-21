#!/usr/bin/env python3
"""Standalone 1:1 builder for G4_oscillation_tracking_effective.
Rebuilds ONLY this figure from data/G4_oscillation_tracking_effective.csv
(group,effective_disp_um_per_20s). Ported from group4_tracking_dist.py (O10 companion:
EFFECTIVE / net-endpoint displacement per ~20s segment for polar-marked vs plate-control vs
unmodified-cell KTs). Companion of G4_oscillation_tracking (that one = per-step / total path).
Imports ONLY shared styling helpers from lib. Output honors $KTFIG_OUT (default = real group4/).

Violin bodies use lib.journal_violin (cut=0, scale='width') so tails cap flat at the data extremes
(2026-07-09 feedback #20)."""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_oscillation_tracking_effective.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

PURPLE = ("#4a148c", "#b39ddb"); GREEN = ("#1b5e20", "#a5d6a7")
order = ["polar-marked", "plate-control", "unmodified-cell"]
COL = {"polar-marked": PURPLE[0], "plate-control": GREEN[0], "unmodified-cell": lib.PALETTE["unModified"]}

# ---- load this figure's own CSV ----------------------------------------------------------------
G = {g: [] for g in order}
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["group"].strip()
        if g in G:
            try: G[g].append(float(row["effective_disp_um_per_20s"]))
            except Exception: pass
# builder plot-filter: <10 µm/segment
G = {g: [v for v in vals if v < 10] for g, vals in G.items()}

fig, ax = plt.subplots(figsize=(7.4, 5.2))
_tops = [np.percentile(vv, 99) for _, vv in G.items() if len(vv) >= 2]
_top = (max(_tops) * 1.06 + 0.4) if _tops else 1.0
for i, g in enumerate(order):
    vals = G[g]; col = COL[g]
    if len(vals) >= 2:
        lib.journal_violin(ax, vals, i, col, width=.7, alpha=.3)
        _scv = vals if len(vals) <= 500 else list(np.random.RandomState(7).choice(np.array(vals), 500, replace=False))
        ax.scatter(np.full(len(_scv), i) + (np.random.RandomState(i).rand(len(_scv)) - .5) * .2, _scv,
                   s=8, color=col, alpha=.4, zorder=2)
        ax.hlines(np.median(vals), i - .3, i + .3, color=col, lw=2.6, zorder=3)
        ax.hlines(np.mean(vals), i - .24, i + .24, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=3)
        ax.text(i, _top, f"x̄ {np.mean(vals):.2f}\nmed {np.median(vals):.2f}\nN={len(vals)}",
                ha="center", va="bottom", fontsize=7.5)
    else:
        ax.text(i, 0, "no data", ha="center", va="bottom", fontsize=7.5, color="#999")
if _tops: ax.set_ylim(top=_top * 1.18)

ax.set_xticks([0, 1, 2]); ax.set_xticklabels(order)
ax.set_ylabel("Effective (net) displacement per 20s interval (µm)")
ax.set_title("Kinetochore oscillation — EFFECTIVE (net endpoint) displacement per 20s (O10 companion to G4_oscillation_tracking)\n"
             "net start→end move per ~20s segment; ignores back-and-forth (vs the per-step/total-path version)",
             loc="left", fontweight="bold", fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_oscillation_tracking_effective.png", bbox_inches="tight"); plt.close()
print("G4_oscillation_tracking_effective ->", f"{OUT}/G4_oscillation_tracking_effective.png", {g: len(G[g]) for g in order})
