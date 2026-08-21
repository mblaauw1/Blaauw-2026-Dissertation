#!/usr/bin/env python3
"""Standalone 1:1 builder for G4_oscillation_tracking.
Rebuilds ONLY this figure from data/G4_oscillation_tracking.csv (group,per_frame_displacement_um).
Ported from group4_tracking_dist.py (S53/I8 oscillation violin: polar-marked vs plate-control vs
unmodified-cell KT displacement per 20s). Imports ONLY shared styling helpers from lib.
Output dir honors $KTFIG_OUT (scratch override); default = the real group4/ path.

Per-step displacement (µm per 20s interval). Violin bodies use lib.journal_violin (cut=0, scale='width')
so the tails are capped flat at the data extremes (2026-07-09 feedback #20: 'violin plot pointed tail').
Unmodified scatter subsampled to 500 (violin/median/mean/N/stats still use the full set)."""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from scipy import stats as _st
from matplotlib.lines import Line2D as _L2
from matplotlib.patches import Patch as _P2
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_oscillation_tracking.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

PURPLE = ("#4a148c", "#b39ddb"); GREEN = ("#1b5e20", "#a5d6a7")
order = ["polar-marked", "plate-control", "unmodified-cell"]
COL = {"polar-marked": PURPLE[0], "plate-control": GREEN[0], "unmodified-cell": lib.PALETTE["unModified"]}
SRC = {"polar-marked": "kt_points", "plate-control": "TrackMate", "unmodified-cell": "TrackMate"}

# ---- load this figure's own CSV ----------------------------------------------------------------
G = {g: [] for g in order}
with open(DATA) as f:
    for row in csv.DictReader(f):
        g = row["group"].strip()
        if g in G:
            try: G[g].append(float(row["per_frame_displacement_um"]))
            except Exception: pass
# builder plot-filter: drop >10 µm/step tracking-jump outliers (polar/plate already <=8 by construction)
G = {g: [v for v in vals if v < 10] for g, vals in G.items()}

fig, ax = plt.subplots(figsize=(7.4, 5.2))
_gvals = []
for i, g in enumerate(order):
    vals = G[g]; col = COL[g]
    _gvals.append((g, vals))
    if len(vals) >= 2:
        lib.journal_violin(ax, vals, i, col, width=.7, alpha=.3)
    if vals:
        _scv = vals if len(vals) <= 500 else list(np.random.RandomState(42).choice(np.array(vals), 500, replace=False))
        ax.scatter(np.full(len(_scv), i) + (np.random.RandomState(i).rand(len(_scv)) - .5) * .2, _scv,
                   s=8, color=col, alpha=.4, zorder=2)
        ax.hlines(np.median(vals), i - .3, i + .3, color=col, lw=2.6, zorder=3)               # median (solid)
        ax.hlines(np.mean(vals), i - .24, i + .24, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=3)  # mean (dashed)
    else:
        ax.text(i, 0, "no data\n(needs TrackMate spots)", ha="center", va="bottom", fontsize=7.5, color="#999")

# N/median labels above the data at a common height (shared top from all groups' 99th pct)
_allv = [v for _, vv in _gvals for v in vv]
if _allv:
    _top = np.percentile(_allv, 99) * 1.06 + 0.4; ax.set_ylim(top=_top * 1.32)
    for i, (_, vals) in enumerate(_gvals):
        if vals:
            _sh = f"\n({min(len(vals), 500)} of {len(vals)} shown)" if len(vals) > 500 else ""
            ax.text(i, _top, f"x̄ {np.mean(vals):.2f}\nmed {np.median(vals):.2f}\nN={len(vals)}{_sh}",
                    ha="center", va="bottom", fontsize=7.5)

# all-pairs Mann-Whitney box (data-x 1.5, axes-y 0.985)
_stat_lines = []
for a in range(len(_gvals)):
    for c in range(a + 1, len(_gvals)):
        (la, va), (lc, vc) = _gvals[a], _gvals[c]
        if len(va) >= 2 and len(vc) >= 2:
            try:
                _pp = _st.mannwhitneyu(va, vc, alternative="two-sided").pvalue
                _stat_lines.append(f"{la} vs {lc}: p={_pp:.2g}")
            except Exception: pass
if _stat_lines:
    ax.text(1.5, 0.985, "Mann–Whitney (all pairs):\n" + "\n".join(_stat_lines),
            transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=6.6,
            bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="#bbb", alpha=.92), zorder=10)

ax.set_xticks([0, 1, 2]); ax.set_xticklabels(order)
ax.set_ylabel("Displacement per 20s interval (µm)")
ax.legend(handles=[_P2(facecolor=PURPLE[0], alpha=.3, edgecolor=PURPLE[0], label=f"polar-marked KTs (kt_points; N={len(G['polar-marked'])} steps)"),
                   _P2(facecolor=GREEN[0], alpha=.3, edgecolor=GREEN[0], label=f"plate-control KTs (TrackMate; N={len(G['plate-control'])} steps)"),
                   _P2(facecolor=lib.PALETTE["unModified"], alpha=.3, edgecolor=lib.PALETTE["unModified"], label=f"unmodified-cell KTs (TrackMate; N={len(G['unmodified-cell'])} steps)"),
                   _L2([0], [0], color="#444", lw=2.6, label="median"),
                   _L2([0], [0], color="#444", lw=1.3, ls=(0, (2, 1.5)), label="mean")],
          fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
ax.set_title("Kinetochore oscillation — displacement per 20s: polar-marked vs plate-control vs unmodified\n"
             "(polar & plate reconciled to G4_oscillation; unmodified scatter subsampled to 500; all-pair Mann–Whitney)",
             loc="left", fontweight="bold", fontsize=9.3)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_oscillation_tracking.png", bbox_inches="tight"); plt.close()
print("G4_oscillation_tracking ->", f"{OUT}/G4_oscillation_tracking.png", {g: len(G[g]) for g in order})
