#!/usr/bin/env python3
"""Dedicated 1:1:1 builder for G3_chromo_length.
Rebuilds ONLY this figure from data/G3_chromo_length.csv (batch,length_um,duration_min,phase).
Ported from group3_build.py (section 4). Scatter of chromosome length vs metaphase duration,
color = ablation phase, marker = sisterless group; per-phase + overall trend lines; N box
(phase × sisterless). Imports ONLY lib (styling + master lookup for sisterless marker shape).
Output dir honors $KTFIG_OUT (scratch override); default = the real group3/ path.
Source-level exclusions (Mad1 / REVIEW_EXCLUDE / double-chromosome / L>30µm) are baked into the CSV.
"""
import os, sys, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA = "/Volumes/4 MB/ablation_plots/data/G3_chromo_length.csv"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group3"); os.makedirs(OUT, exist_ok=True)

PCOL = {"Prophase": "#1b7837", "Prometaphase": "#2166ac", "Metaphase": "#762a83", "": "#999", None: "#999"}
SISMARK = {"1": "o", "2": "s", "3": "^"}   # marker by sisterless count

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def sis(b): return mr.get(b, {}).get("# Sisterless KTs", "")

recC = []   # [batch, length_um, duration_min, phase]
with open(DATA) as f:
    for row in csv.DictReader(f):
        recC.append([row["batch"], float(row["length_um"]), float(row["duration_min"]), row["phase"].strip()])
CX = [r[1] for r in recC]; CY = [r[2] for r in recC]

def _pxs_text(records):
    from collections import Counter as _Cn
    cnt = _Cn()
    for r in records:
        s = sis(r[0])
        if s in "123": cnt[(r[3], s)] += 1
    lines = ["N (phase × sisterless):"]
    for ph in ["Prophase", "Prometaphase", "Metaphase"]:
        parts = [f"{s}-sis {cnt[(ph, s)]}" for s in "123" if cnt[(ph, s)]]
        if parts: lines.append(f"  {ph}: " + ", ".join(parts))
    return "\n".join(lines)

fig, ax = plt.subplots(figsize=(7.4, 5.2))
for r in recC:
    mk = SISMARK.get(sis(r[0]), "o")
    ax.scatter(r[1], r[2], s=30, color=PCOL.get(r[3], "#999"), alpha=.8, edgecolor="white", lw=.3, marker=mk)
for _ph in ["Prophase", "Prometaphase", "Metaphase"]:
    _xx = [r[1] for r in recC if r[3] == _ph]; _yy = [r[2] for r in recC if r[3] == _ph]
    if len(_xx) >= 3:
        _m, _b = np.polyfit(_xx, _yy, 1); _xr = np.linspace(min(_xx), max(_xx), 20)
        ax.plot(_xr, _m * _xr + _b, "--", color=PCOL[_ph], lw=1.8)
if len(CX) >= 3:
    _m, _b = np.polyfit(CX, CY, 1); _xr = np.linspace(min(CX), max(CX), 20); ax.plot(_xr, _m * _xr + _b, "-", color="#222", lw=1.8)
ax.set_xlabel("chromosome length (µm)"); ax.set_ylabel("Metaphase duration, metaphase to anaphase (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(handles=[Line2D([0], [0], marker='o', color='w', markerfacecolor=PCOL[p], label=p) for p in ["Prophase", "Prometaphase", "Metaphase"]]
          + [Line2D([0], [0], color="#222", ls="-", lw=1.8, label="overall trend"),
             Line2D([0], [0], color="#888", ls="--", lw=1.8, label="per-phase trend")]
          + [Line2D([0], [0], marker=SISMARK[s], color='w', markerfacecolor='#888', markeredgecolor='#888', label=lib.lbl(f'{s}-Sister')) for s in "123"],
          fontsize=7, ncol=2)
ax.text(.99, .02, _pxs_text(recC), transform=ax.transAxes, ha="right", va="bottom", fontsize=6.4, color="#333",
        bbox=dict(fc="#f8f8f8", ec="#ccc", lw=.6, alpha=.92))
ax.set_title("Chromosome length vs metaphase duration (color = phase)", loc="left", fontweight="bold", fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_chromo_length.png", bbox_inches="tight"); plt.close()
print("G3_chromo_length ->", f"{OUT}/G3_chromo_length.png", "N=", len(recC),
      {p: sum(1 for r in recC if r[3] == p) for p in ["Prophase", "Prometaphase", "Metaphase"]})
