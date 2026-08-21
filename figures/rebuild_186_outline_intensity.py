#!/usr/bin/env python3
"""Plot 186 (G4_kt_intensity_polar_vs_plate), rebuilt from the TRACED KINETOCHORE OUTLINES.

User 2026-07-28: "update it so it's all manual data from kinetochore outlines instead of the current circle
regions and trackmate data."

What changed vs the old version:
  * plate KT position came from TRACKMATE, polar from a manual mark -> now BOTH sides are her own traced
    kt_outline polygons (label paired = plate-aligned, label polar = sisterless).
  * intensity was a fixed Sigma r=9 DISK around a point -> now it is measured INSIDE the actual outline,
    so it follows the kinetochore's real shape instead of a circle that may clip it or include neighbours.
  * background was a disk-local estimate -> now a PER-FRAME CYTOSOL level (her 2026-07-28 correction), which
    removes the photobleaching/maturation drift that a fixed offset leaves behind.
  * pairs are TIME-MATCHED: only frames where the SAME cell carries both a polar and a paired outline
    contribute, so an early polar is never compared against a late plate KT.
  * out-of-focus frames (POLAR_FOCUS_CHECK suspect=yes) are already excluded from the source table.

Source: annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv (built by polar_fluor_matched.py).
The pre-rebuild figure is kept at _retired_figs/G4_kt_intensity_polar_vs_plate_PRE_OUTLINE_20260728.*
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
SRC = f"{ROOT}/annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv"
OUT = f"{ROOT}/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)

rows = list(csv.DictReader(open(SRC, newline="")))
rows = [r for r in rows if not lib.is_prophase_ablation(r.get("batch",""))]   # prophase excluded (no prophase group)
byf = collections.defaultdict(lambda: {"polar": [], "paired": []})
for r in rows:
    try: sig = float(r["signal"])
    except Exception: continue
    byf[(r["batch"], r["frame"])][r["label"]].append(sig)

# per cell: median over the frames that carry BOTH states
cell = collections.defaultdict(lambda: {"polar": [], "paired": [], "n": 0})
for (b, f), v in byf.items():
    if not v["polar"] or not v["paired"]:
        continue
    cell[b]["polar"].append(float(np.median(v["polar"])))
    cell[b]["paired"].append(float(np.median(v["paired"])))
    cell[b]["n"] += 1
# 2026-08-18: this builder never consulted MANUAL_PLOT_EXCLUSIONS.csv, so `20250401 ptk_yfpcdc20_28`
# -- which she dropped from THIS figure on 2026-07-09 ("polar cell, long/cytokinesis tail") -- came back
# the next time it was rebuilt.  A per-plot exclusion has to live in the builder or it expires silently.
_EXCL = lib.manual_plot_exclusions("G4_kt_intensity_polar_vs_plate")
if _EXCL:
    _back = sorted(b for b in cell if b in _EXCL)
    if _back: print(f"manual exclusions honoured: {_back}")
    for b in _back: cell.pop(b, None)
cells = sorted(cell)
pol = np.array([float(np.median(cell[b]["polar"])) for b in cells])
pla = np.array([float(np.median(cell[b]["paired"])) for b in cells])
nfr = sum(cell[b]["n"] for b in cells)
print(f"{len(cells)} cells, {nfr} time-matched frames")

master, _ = lib.load_master_plots(); M = {r["Batch Name"]: r for r in master}
def coh(b):
    n = (M.get(b, {}).get("# Sisterless KTs") or "").strip()
    return n if n in ("1", "2", "3") else "other"
CCOL = {"1": "#3b6fb6", "2": "#7a5cff", "3": "#d1495b", "other": "#999999"}

fig, ax = plt.subplots(figsize=(6.6, 5.6))
rng = np.random.RandomState(0)
for b, q, p in zip(cells, pla, pol):
    ax.plot([0, 1], [q, p], color=(CCOL[coh(b)] if p > q else "#cccccc"), alpha=0.5, lw=1.0, zorder=1)
ax.scatter(np.zeros(len(pla)) + (rng.rand(len(pla)) - .5) * .10, pla, s=30, color="#1b5e20", alpha=0.8, zorder=3)
ax.scatter(np.ones(len(pol)) + (rng.rand(len(pol)) - .5) * .10, pol, s=30,
           color=[CCOL[coh(b)] for b in cells], alpha=0.85, zorder=3, edgecolor="white", lw=0.4)
ax.hlines(np.median(pla), -0.18, 0.18, color="#1b5e20", lw=2.6, zorder=4)
ax.hlines(np.median(pol), 0.82, 1.18, color="#762a83", lw=2.6, zorder=4)
pw = st.wilcoxon(pol, pla)[1] if len(pol) >= 6 else float("nan")
frac = float(np.mean(pol > pla))
frame_frac = float(np.mean([np.median(v["polar"]) > np.median(v["paired"])
                            for v in byf.values() if v["polar"] and v["paired"]]))
ax.set_xticks([0, 1])
ax.set_xticklabels(["plate-aligned KT\n(traced outline)", "polar KT\n(traced outline)"])
ax.set_ylabel("eYFP-Cdc20 signal inside the outline\n(95th pct − per-frame cytosol)")
ax.set_title(f"eYFP-Cdc20 — polar vs plate-aligned KT, paired per cell (N={len(cells)})\n"
             f"Wilcoxon p={pw:.2g}; polar brighter in {frac*100:.0f}% of cells and "
             f"{frame_frac*100:.0f}% of {nfr} time-matched frames\n"
             f"ALL MANUAL: both sides measured inside her traced kt_outline, per-frame cytosol subtracted",
             loc="left", fontweight="bold", fontsize=8.4)
from matplotlib.lines import Line2D
ax.legend([Line2D([], [], marker="o", ls="", color=CCOL[c]) for c in ("1", "2", "3")],
          [f"{c}-sisterless (n={sum(1 for b in cells if coh(b) == c)})" for c in ("1", "2", "3")],
          fontsize=7.5, loc="best")
fig.tight_layout()
fig.savefig(f"{OUT}/G4_kt_intensity_polar_vs_plate.png", dpi=200, bbox_inches="tight")
plt.close(fig)
rowsPP = [[b, round(q, 2), round(p, 2), cell[b]["n"]] for b, q, p in zip(cells, pla, pol)]
lib.record_plot("G4_kt_intensity_polar_vs_plate",
                ["batch", "plate_signal", "polar_signal", "n_matched_frames"], rowsPP,
                {"family": "kt_intensity"}, script=__file__,
                caption="Polar vs plate-aligned KT eYFP-Cdc20 measured inside the traced outlines "
                        "(all manual; per-frame cytosol subtracted; time-matched)",
                source=[SRC], key_column="batch")
print(f"  G4_kt_intensity_polar_vs_plate  (Wilcoxon p={pw:.3g}, polar brighter in {frac*100:.0f}% of cells)")
