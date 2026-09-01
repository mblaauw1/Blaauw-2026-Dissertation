#!/usr/bin/env python3
"""Standalone 1:1:1 rebuild of ONE figure: G2_dur_meta_to_ana_journal_zoom.

Outlier-trimmed '_zoom' COMPANION of G2_dur_meta_to_ana_journal (metaphase->anaphase duration by cohort).
Reads the BASE csv data/G2_dur_meta_to_ana_journal.csv, finds the extreme duration points with the shared
robust IQR fence (lib.zoom_trim), draws the bulk with the y-axis fit to it; trimmed points become hollow
markers pinned at the top edge. COMPANION-ONLY readability trim. Imports ONLY lib. Honors KTFIG_OUT.
"""
import os, csv, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ID = "G2_dur_meta_to_ana_journal_zoom"
BASE = "G2_dur_meta_to_ana_journal"
DATA = "/Volumes/4 MB/ablation_plots/data"
YCOL = "duration_min"; GCOL = "cohort"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group2"
os.makedirs(OUT, exist_ok=True)
CSV_OUT = OUT if os.environ.get("KTFIG_OUT") else DATA
lib.apply_style()

def load(pid):
    with open(f"{DATA}/{pid}.csv") as f:
        r = csv.reader(f); hdr = next(r); rows = [row for row in r if row]
    return hdr, rows

hdr, rows = load(BASE)
yi = hdr.index(YCOL); gi = hdr.index(GCOL)
yvals = np.array([float(r[yi]) if r[yi] not in ("", "nan") else np.nan for r in rows])
groups = [r[gi] for r in rows]
trim = lib.zoom_trim(yvals)
assert trim["distorting"], "expected distorting outliers for this companion"
om = trim["out_mask"]; keep = ~om; hi = trim["hi"]; lo = trim["lo"]

fig, ax = plt.subplots(figsize=(8.5, 5.2))
gnames = list(dict.fromkeys(groups))
gpos = {g: i for i, g in enumerate(gnames)}
rng = np.random.default_rng(0)
for g in gnames:
    gm = np.array([gg == g for gg in groups])
    xk = gpos[g] + rng.uniform(-.15, .15, int(gm.sum()))
    yk = yvals[gm]; ok = om[gm]
    c = lib.PALETTE.get(g, "#4477aa")
    ax.scatter(xk[~ok], yk[~ok], s=16, alpha=.55, color=c, edgecolors="none")
    for xx in xk[ok]:
        ax.plot(xx, hi, marker="o", mfc="none", mec=c, ms=6, mew=1.1, zorder=6)
    vv = yvals[gm & keep]
    if vv.size: ax.hlines(np.median(vv), gpos[g]-.28, gpos[g]+.28, color="#111", lw=2, zorder=7)
ax.set_xticks(range(len(gnames)))
ax.set_xticklabels([lib.lbl(g) for g in gnames], rotation=25, ha="right", fontsize=8)
ax.set_ylim(lo, hi); ax.set_ylabel(YCOL)
n_out = int(om.sum())
ax.set_title(f"{BASE} — outlier-trimmed zoom companion  "
             f"(y-axis fit to bulk; {n_out} outlier pt(s) removed → hollow markers at top)",
             loc="left", fontweight="bold", fontsize=9.5)
ax.text(0.995, 0.02, f"v2 zoom: {n_out} pts > {trim['fence_hi']:.3g} trimmed  |  "
        f"old y-max {trim['vmax']:.3g} → new {hi:.3g}", transform=ax.transAxes,
        ha="right", va="bottom", fontsize=7, color="#555")
fig.tight_layout(); fig.savefig(f"{OUT}/{ID}.png", bbox_inches="tight"); plt.close(fig)

with open(f"{CSV_OUT}/{ID}.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr + ["zoom_outlier_removed"])
    for row, o in zip(rows, om): w.writerow(row + ["1" if o else "0"])
print(f"wrote {OUT}/{ID}.png  ({n_out} outliers trimmed, hi={hi:.3g})")
