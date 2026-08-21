#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_kt_intensity_polar_vs_plate.
Rebuilds ONLY this figure from data/G4_kt_intensity_polar_vs_plate.csv
(batch,plate_median_au,polar_median_au,n_frames). Ported from group4_movement.py (section 4d).
Per-cell paired dumbbell of MEDIAN polar vs MEDIAN plate eYFP-Cdc20 intensity (both measured
identically: snapped Σ r=9 disk, same-frame cytosol_bg-subtracted, floor 0) + paired Wilcoxon
(polar > plate). Imports ONLY lib (styling + cohort colours). Output dir honors $KTFIG_OUT
(scratch override); default = the real group4/ path.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_kt_intensity_polar_vs_plate.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
R = int(os.environ.get("KT_R", "9"))

coh = lib.assign_cohorts(); b2 = {b: k for k, lst in coh.items() for b, _ in lst}

_pol_c = []; _pla_c = []; _pp_b = []; _nfr = []
with open(DATA) as f:
    for row in csv.DictReader(f):
        # Column names drifted: the recorded CSV now writes plate_signal / polar_signal /
        # n_matched_frames, while this reader still expected plate_median_au / polar_median_au / n_frames,
        # so it died with KeyError on every run. Accept either spelling rather than pin one.
        def _g(r, *names):
            for n in names:
                if n in r and str(r[n]).strip() != "": return r[n]
            raise KeyError(names)
        _pp_b.append(row["batch"])
        _pla_c.append(float(_g(row, "plate_median_au", "plate_signal")))
        _pol_c.append(float(_g(row, "polar_median_au", "polar_signal")))
        _nfr.append(int(float(_g(row, "n_frames", "n_matched_frames"))))

figPP, axPP = plt.subplots(figsize=(6.0, 5.6))
if _pol_c:
    _pol_c = np.array(_pol_c); _pla_c = np.array(_pla_c); _rng = np.random.RandomState(0)
    for mq_, mp_, b in zip(_pla_c, _pol_c, _pp_b):
        axPP.plot([0, 1], [mq_, mp_], color=(lib.PALETTE.get(b2.get(b), "#888") if mp_ > mq_ else "#cccccc"), alpha=.5, lw=1.0, zorder=1)
    axPP.scatter(np.zeros(len(_pla_c)) + (_rng.rand(len(_pla_c)) - .5) * .10, _pla_c, s=26, color="#1b5e20", alpha=.75, zorder=3)
    axPP.scatter(np.ones(len(_pol_c)) + (_rng.rand(len(_pol_c)) - .5) * .10, _pol_c, s=26, color="#762a83", alpha=.75, zorder=3)
    axPP.hlines(np.median(_pla_c), -.2, .2, color="#1b5e20", lw=2.6, zorder=4)
    axPP.hlines(np.median(_pol_c), .8, 1.2, color="#762a83", lw=2.6, zorder=4)
    _fracPP = float(np.mean(_pol_c > _pla_c))
    try:
        from scipy import stats as _stPP
        _W, _pPP = _stPP.wilcoxon(_pol_c, _pla_c, alternative="greater")
        _pwr = f"Wilcoxon (polar>plate, paired per cell) p={_pPP:.2g}"
    except Exception:
        _pwr = "Wilcoxon n/a"
    axPP.set_title(f"eYFP-Cdc20 — polar vs plate KT, paired per cell (N={len(_pol_c)})\n"
                   f"{_pwr}; polar brighter in {_fracPP*100:.0f}% of cells "
                   f"(med polar {np.median(_pol_c):,.0f} vs plate {np.median(_pla_c):,.0f} a.u.)\n"
                   f"MANUAL polar KT vs TrackMate-position plate KT, identical Σ r={R} disk bg-subtracted measurement",
                   loc="left", fontweight="bold", fontsize=8.4)
else:
    axPP.set_title("polar vs plate KT (paired) — no cells", loc="left", fontsize=9)
axPP.set_xticks([0, 1]); axPP.set_xticklabels(["plate KT\n(TrackMate position)", "polar KT\n(manual)"])
axPP.set_ylabel(f"eYFP-Cdc20 intensity (Σ r={R} disk, bg-subtracted)")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_polar_vs_plate.png", bbox_inches="tight"); plt.close()
print("G4_kt_intensity_polar_vs_plate ->", f"{OUT}/G4_kt_intensity_polar_vs_plate.png",
      "N cells", len(_pol_c), "polar>plate frac", round(float(np.mean(_pol_c > _pla_c)), 3) if len(_pol_c) else None)
