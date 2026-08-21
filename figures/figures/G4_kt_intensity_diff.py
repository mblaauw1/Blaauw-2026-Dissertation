#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_kt_intensity_diff.
Rebuilds ONLY this figure from data/G4_kt_intensity_diff.csv
(batch,t_min_since_first_abl,polar_au,plate_au,diff_au). Ported from group4_movement.py (section 4c).
Per-cell line of polar − plate eYFP-Cdc20 KT intensity vs time since first ablation, coloured by
cohort, + per-cohort binned-median trend (4-min bins, ≥3 pts & ≥2 cells/bin). Imports ONLY lib
(styling + cohort colours). Output dir honors $KTFIG_OUT (scratch override); default = real group4/.
Exclusions (Mad1 / REVIEW_EXCLUDE / LONG_SAMPLE / unassigned cohort) are baked into the CSV.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.lines import Line2D
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_kt_intensity_diff.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
R = int(os.environ.get("KT_R", "9"))

coh = lib.assign_cohorts(); b2 = {b: k for k, lst in coh.items() for b, _ in lst}

_DT = []   # (batch, t_min, diff_au)
with open(DATA) as f:
    for row in csv.DictReader(f):
        _DT.append((row["batch"], float(row["t_min_since_first_abl"]), float(row["diff_au"])))

figD, axD = plt.subplots(figsize=(9.4, 5.4))
_byD = defaultdict(list); _byGdiff = defaultdict(list); _dcov = set()
for b, tm, dv in _DT:
    _byD[b].append((tm, dv)); _byGdiff[b2.get(b)].append((tm, dv)); _dcov.add(b)
for b, ser in _byD.items():
    ser = sorted(ser)
    if len(ser) >= 2:
        axD.plot([s[0] for s in ser], [s[1] for s in ser], color=lib.PALETTE.get(b2.get(b), "#888"), alpha=.55, lw=1.0, marker="o", ms=2)
    elif len(ser) == 1:
        axD.scatter([ser[0][0]], [ser[0][1]], color=lib.PALETTE.get(b2.get(b), "#888"), s=16)
for g, pp in _byGdiff.items():
    if g is None: continue
    a = np.array(sorted(pp))
    if len(a) < 5: continue
    _cells_in = defaultdict(set)
    for (bb, tm, dv) in _DT:
        if b2.get(bb) == g: _cells_in[int(tm // 4)].add(bb)
    gx = []; gy = []
    for lo in np.arange(np.floor(a[:, 0].min() / 4) * 4, a[:, 0].max() + 4, 4):
        m = (a[:, 0] >= lo) & (a[:, 0] < lo + 4)
        if m.sum() >= 3 and len(_cells_in[int((lo + 2) // 4)]) >= 2:
            gx.append(lo + 2); gy.append(np.median(a[m, 1]))
    if len(gx) >= 2: axD.plot(gx, gy, color=lib.PALETTE.get(g, "#888"), lw=3, zorder=6)
axD.axhline(0, color="#999", ls="--", lw=1); axD.axvline(0, color="#333", ls=":", lw=.9)
axD.set_xlabel("Time since first ablation (min; t=0 = first ablation)")
axD.set_ylabel(f"eYFP intensity: polar − plate KT (Σ r={R} disk, bg-subtracted)")
_gsD = sorted([g for g in _byGdiff if g is not None], key=lambda g: lib.lbl(g))
_ncellD = defaultdict(set)
for b in _dcov: _ncellD[b2.get(b)].add(b)
_hD = [Line2D([0], [0], color=lib.PALETTE.get(g, "#888"), lw=2, label=f"{lib.lbl(g).splitlines()[0]} (N={len(_ncellD.get(g, []))}; bold=cohort median)") for g in _gsD]
if None in _byGdiff: _hD.append(Line2D([0], [0], color="#888", lw=2, label=f"unassigned cohort (N={len(_ncellD.get(None, []))})"))
axD.legend(handles=_hD, fontsize=6.6, ncol=2, loc="upper right")
_medD = np.median([d for *_, d in _DT]) if _DT else float("nan")
axD.set_title(f"Polar − plate kinetochore eYFP-Cdc20 intensity vs time ({len(_dcov)} cells; median diff {_medD:,.0f} a.u.)\n"
              f"MANUAL polar KT vs TrackMate-position PLATE KT, both measured identically (Σ r={R} disk, same-frame cytosol_bg-subtracted); plate KT may differ frame-to-frame; +'ve = polar brighter",
              loc="left", fontweight="bold", fontsize=8.8)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_diff.png", bbox_inches="tight"); plt.close()
print("G4_kt_intensity_diff ->", f"{OUT}/G4_kt_intensity_diff.png", len(_dcov), "cells", len(_DT), "frames",
      "median diff", round(float(_medD), 1))
