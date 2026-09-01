#!/usr/bin/env python3
"""Standalone rebuild of ONE figure: G1_violin2_sisterless_1234_journal_zoom.

Outlier-trimmed '_zoom' COMPANION of G1_violin2_sisterless_1234_journal (metaphase duration
by cohort, journal-standard bodies). Reads the BASE csv
data/G1_violin2_sisterless_1234_journal.csv, finds the extreme metaphase-duration points with
the shared robust IQR fence (lib.zoom_trim), draws the bulk with the y-axis fit to it, and pins
trimmed points as hollow markers at the top edge (the missing-point convention). COMPANION-ONLY
readability trim — it does NOT propagate to the base violin or any other figure.
Ported from make_zoom_companions.py (generic 'strip' family), pinned to this id; the journal
bodies (scale='width', width=0.8, cut=0) come from lib.journal_violin. Honors $KTFIG_OUT.
"""
import os, csv, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

FIG = "/Volumes/4 MB/ablation_figures_20260625"
DATA_DIR = "/Volumes/4 MB/ablation_plots/data"
BASE = f"{DATA_DIR}/G1_violin2_sisterless_1234_journal.csv"
ID = "G1_violin2_sisterless_1234_journal"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group1"); os.makedirs(OUT, exist_ok=True)
CSV_OUT = OUT if os.environ.get("KTFIG_OUT") else DATA_DIR   # scratch keeps _zoom.csv out of the real data dir

with open(BASE) as f:
    r = csv.reader(f); hdr = next(r); rows = [row for row in r if row]
gi = hdr.index("cohort"); yi = hdr.index("metaphase_duration_min")
yvals = np.array([float(row[yi]) if row[yi] not in ("", "nan") else np.nan for row in rows])
groups = [row[gi] for row in rows]

trim = lib.zoom_trim(yvals)
assert trim["distorting"], "expected distorting outliers for this companion"
om = trim["out_mask"]; keep = ~om; hi = trim["hi"]; lo = trim["lo"]

fig, ax = plt.subplots(figsize=(8.5, 5.2))
gnames = list(dict.fromkeys(groups))                      # order-of-appearance = violin order
gpos = {g: i for i, g in enumerate(gnames)}
rng = np.random.default_rng(0)
for g in gnames:
    gm = np.array([gg == g for gg in groups])
    c = lib.PALETTE.get(g, "#4477aa")
    lib.journal_violin(ax, list(yvals[gm & keep]), gpos[g], c, alpha=0.30, lw=1.0)   # body of the KEPT bulk
    xk = gpos[g] + rng.uniform(-.15, .15, int(gm.sum())); yk = yvals[gm]; ok = om[gm]
    ax.scatter(xk[~ok], yk[~ok], s=16, alpha=.55, color=c, edgecolors="none")
    for xx in xk[ok]:
        ax.plot(xx, hi, marker="o", mfc="none", mec=c, ms=6, mew=1.1, zorder=6)
    vv = yvals[gm & keep]
    if vv.size:
        ax.hlines(np.median(vv), gpos[g] - .28, gpos[g] + .28, color="#111", lw=2, zorder=7)
ax.set_xticks(range(len(gnames)))
ax.set_xticklabels([lib.lbl(g) for g in gnames], rotation=25, ha="right", fontsize=8)
ax.set_ylim(lo, hi); ax.set_ylabel("metaphase_duration_min")
n_out = int(om.sum())
ax.set_title(f"{ID}_zoom — outlier-trimmed zoom companion  "
             f"(y-axis fit to bulk; {n_out} outlier pt(s) removed → hollow markers at top)",
             loc="left", fontweight="bold", fontsize=9.5)
ax.text(0.995, 0.02, f"v2 zoom: {n_out} pts > {trim['fence_hi']:.3g} trimmed  |  "
        f"old y-max {trim['vmax']:.3g} → new {hi:.3g}", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=7, color="#555")
fig.tight_layout(); fig.savefig(f"{OUT}/{ID}_zoom.png", bbox_inches="tight"); plt.close(fig)

with open(f"{CSV_OUT}/{ID}_zoom.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr + ["zoom_outlier_removed"])
    for row, o in zip(rows, om):
        w.writerow(row + ["1" if o else "0"])
print(f"wrote {OUT}/{ID}_zoom.png  ({n_out} outliers trimmed, hi={hi:.3g})")
