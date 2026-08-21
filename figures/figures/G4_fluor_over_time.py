#!/usr/bin/env python3
"""Standalone 1:1 builder for G4_fluor_over_time.
Rebuilds ONLY this figure from data/G4_fluor_over_time.csv (batch,cohort,t_sec,fluor_mean_au).
Ported from group4_fluor.py (b) 'fluorescence over time'. Imports ONLY shared helpers from lib
(styling + master read for the per-cohort anaphase trend cap). Output honors $KTFIG_OUT (default
= real group4/).

The CSV is already the plotted per-cell points (low/2-Sister/LONG_SAMPLE/>HI-cut exclusions applied
at build time, off-target merged into 'Off-Target/Control'). This script renders: faint per-cell
lines, per-cohort binned-median trend (5-min bins, >=3 pts, capped at that cohort's mean anaphase),
'all data' dashed trend, and the across-cohort Kruskal-Wallis on per-cell median fluorescence."""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_fluor_over_time.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

# ---- load this figure's own CSV ----------------------------------------------------------------
bym = defaultdict(list)          # batch -> [(t_sec, fluor)]
bcoh = {}                        # batch -> cohort
grp_pts = defaultdict(list)      # cohort -> [(t_min, fluor)]
grp_n = defaultdict(set)         # cohort -> {batch}
with open(DATA) as f:
    for row in csv.DictReader(f):
        b = row["batch"].strip(); g = row["cohort"].strip()
        try: ts = float(row["t_sec"]); fl = float(row["fluor_mean_au"])
        except Exception: continue
        bym[b].append((ts, fl)); bcoh[b] = g
        grp_pts[g].append((ts / 60.0, fl)); grp_n[g].add(b)

# per-cohort mean anaphase (min from movie start) to cap each trend (from master via lib)
data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
_flcap = defaultdict(list)
for b, g in bcoh.items():
    _an = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    if _an is not None: _flcap[g].append(_an / 60.0)
_flcap = {g: float(np.mean(v)) for g, v in _flcap.items() if v}
_allcap = max(_flcap.values()) if _flcap else None

ORDER_T = ["unModified", "1-Sister", "3-Sister", "4-Sister", "Off-Target/Control"]
def _binmed(P, cap=None):
    P = np.array(sorted(P)); bx = []; by = []
    for lo in np.arange(0, P[:, 0].max() + 5, 5):
        if cap is not None and lo + 2.5 > cap: break
        m = (P[:, 0] >= lo) & (P[:, 0] < lo + 5)
        if m.sum() >= 3: bx.append(lo + 2.5); by.append(np.median(P[m, 1]))
    return bx, by

fig, ax = plt.subplots(figsize=(9, 5.2))
for b, pl in bym.items():
    g = bcoh[b]; pl = sorted(pl)
    ax.plot([p[0] / 60 for p in pl], [p[1] for p in pl], color=lib.PALETTE.get(g, "#999"), alpha=.18, lw=.8, zorder=1)
for g in [x for x in ORDER_T if x in grp_pts] + [x for x in grp_pts if x not in ORDER_T]:
    bx, by = _binmed(grp_pts[g], _flcap.get(g))
    if len(bx) >= 2:
        ax.plot(bx, by, color=lib.PALETTE.get(g, "#888"), lw=2.6, marker="o", ms=4, zorder=3,
                label=f"{lib.lbl(g).replace(chr(10), ' ')} (N={len(grp_n[g])})")
allP = [p for P in grp_pts.values() for p in P]
if len(allP) >= 5:
    abx, aby = _binmed(allP, _allcap); ax.plot(abx, aby, "--", color="#111", lw=2.2, zorder=4, label="all data")

# Kruskal-Wallis across cohorts on per-cell median fluorescence
kw = [[np.median([f for _, f in bym[b]]) for b in grp_n[g]] for g in grp_n]
kw = [v for v in kw if len(v) >= 3]
if len(kw) >= 2:
    H, pk = stats.kruskal(*kw)
    ax.text(.98, .60, f"Kruskal–Wallis across cohorts\n(per-cell median): H={H:.1f}, p={pk:.3g}",
            transform=ax.transAxes, va="top", ha="right", fontsize=8.5, bbox=dict(boxstyle="round", fc="white", ec="#ccc", alpha=.9))
ax.set_xlabel("Time from movie start (min)")
ax.set_ylabel("Cell fluorescence (mean inside manual outline, area-normalized, a.u.)")
ax.set_title("Cell fluorescence over time — per-cohort binned-median trend (trend capped at avg anaphase)",
             loc="left", fontweight="bold", fontsize=10.5)
ax.legend(fontsize=7, ncol=2)
ax.text(.02, .02, "unmodified batches imaged at ≤1 z-stack/min excluded (ITEM 2)", transform=ax.transAxes, va="bottom", fontsize=7, color="#777")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_over_time.png", bbox_inches="tight"); plt.close()
print(f"G4_fluor_over_time -> {OUT}/G4_fluor_over_time.png  cohorts={ {g: len(grp_n[g]) for g in grp_n} }, points={sum(len(v) for v in bym.values())}")
