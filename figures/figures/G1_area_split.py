#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G1_area_split.
Cell cross-sectional area over mitosis, faceted by group (2x3), ablation-referenced
(mode='ablation': x = time from first ablation; unmodified referenced to NEBD). Light = per-cell
traces, bold = per-group binned-mean trend, dashed vertical = per-group MEAN time to anaphase.
Rebuilds ONLY this figure from data/G1_area_split.csv (batch,cohort,t_min,value) — the exact
plotted per-cell trace points. Ported from group1_roundness.py::split_panels(area, mode='ablation').

NB the CSV stores the plotted trace points but NOT each cell's anaphase-x; the per-group mean-time
dashed line is reconstructed as the mean over cells of that cell's last plotted t_min (traces are
clipped at anaphase). Imports ONLY lib. Honors $KTFIG_OUT.
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G1_area_split.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)
YLABEL = "Cross-sectional area (um^2)"; TITLENOUN = "Cell cross-sectional area"

FAM = [("1-Sisterless", ["1-Sister"]), ("2-Sisterless", ["2-Sister"]), ("3-Sisterless", ["3-Sister"]),
       ("off-target (1/2/3)", ["1-Sister Controls", "2-Sister Controls", "3-Sister Controls"]),
       ("unmodified", ["unModified"])]
def xlab(is_un): return "Time from NEBD (min)" if is_un else "Time from first ablation (min)"

cells = defaultdict(list); cell_coh = {}
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

fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=False, sharey=True); af = list(axes.flat)
for i, (title, keys) in enumerate(FAM):
    ax = af[i]; col = lib.PALETTE[keys[0]]; pa = []; anaxs = []; is_un = keys == ["unModified"]; ncell = 0
    for b, tr in cells.items():
        if cell_coh[b] not in keys: continue
        pts = sorted(tr); ncell += 1
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=col, alpha=.2, lw=.8, zorder=1)
        pa.extend(pts); anaxs.append(max(q[0] for q in pts))
    md = float(np.mean(anaxs)) if anaxs else None
    if pa and md and len(pa) >= 5:
        # ablation-mode traces can start slightly <0; start the trend at the group's min plotted x
        start = min(0.0, min(q[0] for q in pa))
        bx, by = trend_to_mean(pa, md, start=start)
        if len(bx) >= 2: ax.plot(bx, by, color=col, lw=2.8, marker="o", ms=4, zorder=3)
        ax.axvline(md, color=col, ls=(0, (2, 1.5)), lw=1.2)
        _dx = (md if md else 1) * 0.02 + 0.2
        ax.text(md + _dx, 0.045, f"mean ana {lib.mmss(md)}", transform=ax.get_xaxis_transform(),
                rotation=0, fontsize=6.5, color=col, ha="left", va="bottom", zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=col, lw=0.6, alpha=0.9))
    ax.set_title(f"{title} (N={ncell})", fontsize=10, color=col)
    ax.set_xlabel(xlab(is_un))
for j in range(len(FAM), len(af)): af[j].axis("off")
for ax in axes[:, 0]: ax.set_ylabel(YLABEL)
fig.suptitle(f"{TITLENOUN} by group — trend ends at group mean time to anaphase",
             x=.01, ha="left", fontweight="bold")
plt.tight_layout(); plt.savefig(f"{OUT}/G1_area_split.png", bbox_inches="tight"); plt.close()
print("G1_area_split ->", f"{OUT}/G1_area_split.png",
      {t: len([b for b in cells if cell_coh[b] in k]) for t, k in FAM})
