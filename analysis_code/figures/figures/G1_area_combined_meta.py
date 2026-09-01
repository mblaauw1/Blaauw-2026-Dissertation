#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_area_combined_meta.
Cell cross-sectional area over metaphase, ALL groups combined, referenced to each cell's own
metaphase onset (x=0) and clipped at anaphase (mode='meta'). Light = per-cell traces,
bold = per-group binned-mean trend, dashed vertical = per-group MEAN time to anaphase.
Rebuilds ONLY this figure from data/G1_area_combined_meta.csv (batch,cohort,t_min,value) —
the exact plotted per-cell trace points. Ported from group1_roundness.py::combined(mode='meta').

NB the CSV stores the plotted trace points but NOT each cell's anaphase-x; the per-group mean-time
dashed line is reconstructed as the mean over cells of that cell's last plotted t_min (traces are
clipped at anaphase, so the last point ≈ anaphase-x). Trend uses the same binned-mean-to-mean logic
as the builder. Imports ONLY lib. Honors $KTFIG_OUT.
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from collections import defaultdict
from scipy import stats
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_area_combined_meta.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)
YLABEL = "Cross-sectional area (um^2)"; TITLENOUN = "Cell cross-sectional area"

FAM = [("1-Sisterless", ["1-Sister"]), ("2-Sisterless", ["2-Sister"]), ("3-Sisterless", ["3-Sister"]),
       ("off-target (1/2/3)", ["1-Sister Controls", "2-Sister Controls", "3-Sister Controls"]),
       ("unmodified", ["unModified"])]

# per-cell traces from the CSV
cells = defaultdict(list)                                  # batch -> [(t_min,value)]
cell_coh = {}
with open(DATA) as f:
    for row in csv.DictReader(f):
        b = row["batch"]; cell_coh[b] = row["cohort"]
        cells[b].append((float(row["t_min"]), float(row["value"])))

def trend_to_mean(pts, md, nb=8, minpts=3, start=0.0):
    if md is None or md <= start: return [], []
    a = np.array(sorted(pts)); t = a[:, 0]; y = a[:, 1]
    bins = np.linspace(start, md, nb); idx = np.digitize(t, bins); bx = []; by = []
    for k in range(1, len(bins)):
        m = idx == k
        if m.sum() >= minpts: bx.append(float(t[m].mean())); by.append(float(y[m].mean()))
    if bx and bx[-1] < md - 1e-6:
        mlast = (t >= bins[-2]) & (t <= md + 1e-6)
        by.append(float(y[mlast].mean()) if mlast.sum() >= 1 else by[-1]); bx.append(md)
    return bx, by

fig, ax = plt.subplots(figsize=(9.6, 5.6))
_grpcell = {}; _label_q = []
for title, keys in FAM:
    col = lib.PALETTE[keys[0]]; pa = []; _cm = []; anaxs = []
    for b, tr in cells.items():
        if cell_coh[b] not in keys: continue
        pts = sorted(tr)
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=col, alpha=.12, lw=.7, zorder=1)
        pa.extend(pts); _cm.append(np.median([q[1] for q in pts]))
        anaxs.append(max(q[0] for q in pts))              # reconstructed anaphase-x = last plotted t_min
    _grpcell[title] = _cm
    md = float(np.mean(anaxs)) if anaxs else None
    if pa and md and len(pa) >= 5:
        bx, by = trend_to_mean(pa, md)
        if len(bx) >= 2:
            ax.plot(bx, by, color=col, lw=2.8, marker="o", ms=4, zorder=3, label=f"{title} (N={len(_cm)})")
        ax.axvline(md, color=col, ls=(0, (2, 1.5)), lw=1.2)
        _label_q.append((md, col, lib.mmss(md)))
ax.set_ylim(bottom=0); ax.set_xlim(left=0); ytop = ax.get_ylim()[1]

# horizontal, right-offset, vertically-staggered MM:SS mean-time labels (RA2 collision avoidance)
_label_q.sort(key=lambda z: z[0])
_xr = ax.get_xlim()[1] - ax.get_xlim()[0]; _DX = _xr * 0.008; _WX = _xr * 0.075
_tiers = [ytop * 0.985, ytop * 0.905, ytop * 0.825, ytop * 0.745, ytop * 0.665]
_lastx = -1e9; _ti = 0
for _md, _col, _s in _label_q:
    _ti = min(_ti + 1, len(_tiers) - 1) if _md - _lastx < _WX else 0
    ax.text(_md + _DX, _tiers[_ti], _s, rotation=0, fontsize=6.5, color=_col, ha="left", va="top", zorder=7,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=_col, lw=0.6, alpha=0.9))
    _lastx = _md
ax.set_xlabel("Time from metaphase onset (min)"); ax.set_ylabel(YLABEL)
_hh, _ll = ax.get_legend_handles_labels()
_hh.append(Line2D([0], [0], color="#555", ls=(0, (2, 1.5)), lw=1.2)); _ll.append("mean time to anaphase")
ax.legend(_hh, _ll, fontsize=7, ncol=2)
_kg = [v for v in _grpcell.values() if len(v) >= 2]; _kw = ""
if len(_kg) >= 2:
    try:
        _h, _p = stats.kruskal(*_kg); _kw = f"Kruskal-Wallis (per-cell median {TITLENOUN.lower()}) p={_p:.2g}"
    except Exception: pass
ax.set_title(f"{TITLENOUN} — all groups combined (light=cells, bold=group trend) "
             f"(metaphase onset → anaphase)" + ("\n" + _kw if _kw else ""),
             loc="left", fontweight="bold", fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_area_combined_meta.png", bbox_inches="tight"); plt.close()
print("G1_area_combined_meta ->", f"{OUT}/G1_area_combined_meta.png",
      {t: len([b for b in cells if cell_coh[b] in k]) for t, k in FAM})
