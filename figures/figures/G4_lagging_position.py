#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G4_lagging_position.
Rebuilds ONLY this figure from data/G4_lagging_position.csv
(batch,along_axis_frac,across_axis_frac,radial_frac,frame_gap,t_since_ana_min).
Ported from group4_lagging_shape.py (I9 lagging-position block). Imports ONLY lib for styling.

NOTE (flagged): the source builder also draws faint per-KT connector polylines, which require the
raw pixel (x,y) of each point — those are NOT in this figure's CSV, so the connectors are omitted
here. All quantitative content (the along-axis histogram + the normalized-frame scatter shaded by
time-since-anaphase) is fully reproduced from the CSV. Honors $KTFIG_OUT.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as _mc
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G4_lagging_position.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)

A1 = []; A2 = []; RAD = []; T = []; batches = set()
scx = []; scy = []; sct = []; scx_nt = []; scy_nt = []
with open(DATA) as f:
    for row in csv.DictReader(f):
        a1 = float(row["along_axis_frac"]); a2 = float(row["across_axis_frac"])
        rad = float(row["radial_frac"]); batches.add(row["batch"])
        A1.append(a1); A2.append(a2); RAD.append(rad)
        ts = row["t_since_ana_min"].strip()
        if ts not in ("", "nan"):
            sct.append(float(ts)); scx.append(a1); scy.append(a2)
        else:
            scx_nt.append(a1); scy_nt.append(a2)
A1 = np.array(A1); A2 = np.array(A2); RAD = np.array(RAD)
npts = len(A1); ncells = len(batches)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(13, 5.4))
# LEFT: histogram of along-division-axis fractional position (0 = cell middle)
axL.hist(A1, bins=np.linspace(-1, 1, 21), color="#762a83", alpha=.8)
axL.axvline(0, color="#333", ls=":", lw=1)
axL.axvline(np.median(A1), color="#b30000", ls="--", lw=1.6,
            label=f"median |pos|={np.median(np.abs(A1)):.2f}\nmedian pos={np.median(A1):+.2f}")
axL.set_xlabel("Position along cell division axis (0 = cell middle, ±1 = cell ends)")
axL.set_ylabel("lagging-KT measurements"); axL.set_xlim(-1, 1); axL.legend(fontsize=8)
axL.set_title("Lagging KT sits near the cell middle (division-axis position)", loc="left", fontweight="bold", fontsize=10)
# RIGHT: normalized cell-frame scatter shaded by time since anaphase (dark=earlier, light=later)
th = np.linspace(0, 2 * np.pi, 100); axR.plot(np.cos(th), np.sin(th), color="#aaa", lw=1.2, ls="--")
axR.text(0, 1.02, "cell boundary", color="#999", fontsize=7.5, ha="center", va="bottom")
if sct:
    norm = _mc.Normalize(vmin=float(np.min(sct)), vmax=float(np.max(sct)))
    sc = axR.scatter(scx, scy, c=sct, cmap=plt.cm.viridis, norm=norm, s=26, alpha=.85, edgecolor="white", lw=.3, zorder=3)
    cb = fig.colorbar(sc, ax=axR, fraction=0.046, pad=0.04)
    cb.set_label("Time since anaphase onset (min)  —  dark = earlier, light = later", fontsize=8)
if scx_nt:
    axR.scatter(scx_nt, scy_nt, facecolor="none", edgecolor="#bbb", s=26, lw=.6, zorder=2, label="no anaphase time")
    axR.legend(fontsize=7, loc="upper right")
axR.plot(0, 0, "+", color="k", ms=12, mew=2); axR.set_aspect("equal")
axR.set_xlabel("along division axis (frac)"); axR.set_ylabel("across short axis (frac)")
axR.set_xlim(-1.3, 1.3); axR.set_ylim(-1.3, 1.3)
axR.set_title("Lagging-KT position in the normalized cell frame (shaded by time after anaphase)", loc="left", fontweight="bold", fontsize=10)
fig.suptitle(f"Lagging-kinetochore POSITION relative to cell outline — {npts} points, {ncells} cells "
             f"(median radial {np.median(RAD):.2f} of cell radius; near-middle if small)", x=.01, ha="left", fontweight="bold", fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_lagging_position.png", bbox_inches="tight"); plt.close()
print(f"G4_lagging_position -> {OUT}/G4_lagging_position.png : {npts} points, {ncells} cells; "
      f"median |along|={np.median(np.abs(A1)):.2f}, median radial={np.median(RAD):.2f}")
