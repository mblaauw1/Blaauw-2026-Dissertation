#!/usr/bin/env python3
"""The four KT metrics where the UNIT changes the verdict, plotted with BOTH numbers.

USER 2026-08-10: "make versions of the four plots you mentioned above with both numbers and place these
versions on the new figures file."

The four are the metrics where switching from one-point-per-CELL to one-point-per-KINETOCHORE flips
significance:

    paired  major_um          per-cell p=0.052  ->  per-KT p=0.0013
    paired  dist_to_plate_um  per-cell p=0.515  ->  per-KT p=0.031
    paired  chromo_len_um     per-cell p=0.397  ->  per-KT p=0.042
    polar   area_um2          per-cell p=0.094  ->  per-KT p=0.046

WHY BOTH NUMBERS, AND WHY THAT IS THE POINT OF THESE FIGURES. A p-value moving from 0.51 to 0.03 purely
because the unit was re-labelled is the signature of PSEUDOREPLICATION: several kinetochores from one cell
are not independent observations, so counting each as one inflates n and shrinks p without any new
evidence. The per-KINETOCHORE number is the right one if the kinetochore is the thing that varies (she
marks them separately and treats them separately); the per-CELL number is the conservative one that cannot
be inflated by a cell contributing many kinetochores. Neither is "the" answer on its own, so every figure
here reports both, draws the per-cell medians on top of the per-KT points, and states the number of cells
contributing more than one kinetochore -- which is what drives the gap between the two.

Points are one per KINETOCHORE (track_id), each the median of that kinetochore's frames; a track needs
>= MIN_FRAMES frames to be counted. Cohort = 1- vs 3-sisterless, standard exclusions applied.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
import lib

lib.apply_style()
csv.field_size_limit(10 ** 9)
LM = "/Volumes/4 MB/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group6_tracks"
RELINK = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
os.makedirs(OUT, exist_ok=True); os.makedirs(RELINK, exist_ok=True)
MIN_FRAMES = 3

data, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in data}
DBL = set(lib.double_chromosome_batches()); _ok = {}
def cohort_ok(b):
    if b not in _ok:
        _ok[b] = (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in DBL
    return _ok[b]
def sis(b): return (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()

SPECS = [
    # the original four (verdict flips per-cell -> per-KT)
    ("paired",  "major_um",             "Paired-KT major axis (\u00b5m)",              "G6perkt_paired_major"),
    ("paired",  "dist_to_plate_um",     "Paired-KT distance to plate (\u00b5m)",       "G6perkt_paired_dist_to_plate"),
    ("paired",  "chromo_len_um",        "Chromosome length at paired KT (\u00b5m)",    "G6perkt_paired_chromo_len"),
    ("polar",   "area_um2",             "Polar-KT area (\u00b5m\u00b2)",              "G6perkt_polar_area"),
    # the seven found by the exhaustive scan of every metric x every label (user 2026-08-10: "build all")
    ("paired",  "area_toward_um2",      "Paired-KT area toward the pole (\u00b5m\u00b2)", "G6perkt_paired_area_toward"),
    ("paired",  "anisotropy_par_perp",  "Paired-KT anisotropy (par/perp)",          "G6perkt_paired_anisotropy"),
    ("paired",  "stretch_radial_deg",   "Paired-KT stretch vs radial axis (deg)",   "G6perkt_paired_stretch_radial"),
    ("polar",   "area_away_um2",        "Polar-KT area away from the pole (\u00b5m\u00b2)", "G6perkt_polar_area_away"),
    ("lagging", "reflection_asym_perp", "Lagging-KT reflection asymmetry (perp)",   "G6perkt_lagging_reflasym"),
    ("lagging", "minor_um",             "Lagging-KT minor axis (\u00b5m)",             "G6perkt_lagging_minor"),
    # NOTE: this one flips the OTHER way -- significant per CELL, not per kinetochore. Kept in the set
    # precisely because it shows the unit question is not "per-KT always wins".
    ("polar",   "stretch_radial_deg",   "Polar-KT stretch vs radial axis (deg)",    "G6perkt_polar_stretch_radial"),
]

COL = {"1": "#2a7fff", "3": "#ff5a3c"}
rows_all = []

def collect(label, metric):
    kt = collections.defaultdict(list); cell = collections.defaultdict(list)
    for r in csv.DictReader(open(LM)):
        if (r.get("label") or "") != label: continue
        b = (r.get("batch") or "").strip()
        g = sis(b)
        if g not in ("1", "3") or not cohort_ok(b): continue
        try: v = float(r[metric])
        except Exception: continue
        kt[(b, g, r["track_id"])].append(v)
        cell[(b, g)].append(v)
    return kt, cell

for label, metric, ylab, pid in SPECS:
    kt, cell = collect(label, metric)
    KT = {k: float(np.median(v)) for k, v in kt.items() if len(v) >= MIN_FRAMES}
    CE = {k: float(np.median(v)) for k, v in cell.items() if len(v) >= MIN_FRAMES}
    a = [v for k, v in KT.items() if k[1] == "1"]; c = [v for k, v in KT.items() if k[1] == "3"]
    ac = [v for k, v in CE.items() if k[1] == "1"]; cc = [v for k, v in CE.items() if k[1] == "3"]
    if len(a) < 3 or len(c) < 3:
        print(f"  {pid}: too few ({len(a)}/{len(c)})"); continue
    p_kt = mannwhitneyu(a, c, alternative="two-sided").pvalue
    p_ce = mannwhitneyu(ac, cc, alternative="two-sided").pvalue if len(ac) >= 3 and len(cc) >= 3 else float("nan")
    # how many cells contribute more than one kinetochore -- this is what separates the two numbers
    per_cell_n = collections.Counter((k[0], k[1]) for k in KT)
    multi = sum(1 for v in per_cell_n.values() if v > 1)

    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    for i, (vals, g) in enumerate(((a, "1"), (c, "3"))):
        x = np.random.default_rng(i).normal(i, 0.07, len(vals))
        ax.scatter(x, vals, c=COL[g], s=42, alpha=.70, edgecolor="k", lw=.35, zorder=3,
                   label=None)
        ax.boxplot(vals, positions=[i], widths=.55, showfliers=False)
    # per-CELL medians drawn on top, so the conservative unit is visible, not just quoted
    for i, (vals, g) in enumerate(((ac, "1"), (cc, "3"))):
        xx = np.random.default_rng(10 + i).normal(i, 0.05, len(vals))
        ax.scatter(xx, vals, facecolors="none", edgecolors="k", marker="D", s=58, lw=1.1, zorder=5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"single\nKTs n={len(a)} · cells n={len(ac)}",
                        f"3-sisterless\nKTs n={len(c)} · cells n={len(cc)}"])
    ax.set_ylabel(ylab)
    ax.set_title(f"{label} kinetochores — {metric}\n"
                 f"per KINETOCHORE p={p_kt:.4g}   ·   per CELL p={p_ce:.4g}",
                 fontsize=11)
    ax.grid(alpha=.3, axis="y")
    from matplotlib.lines import Line2D
    ax.legend([Line2D([], [], marker="o", color="none", markerfacecolor="#888", markersize=8),
               Line2D([], [], marker="D", color="none", markeredgecolor="k", markerfacecolor="none", markersize=9)],
              ["one point per KINETOCHORE", "one point per CELL (conservative)"], fontsize=8, loc="best")
    ax.text(0.0, -0.155,
            "Both units are shown because the choice changes the verdict. Counting each kinetochore as an "
            "observation inflates n\nwhen several come from one cell (pseudoreplication) — "
            f"{multi} cells here contribute more than one. The per-cell number\ncannot be inflated that way; "
            "the per-kinetochore number is right only if the kinetochore is what varies.",
            transform=ax.transAxes, fontsize=7, color="#555", va="top", linespacing=1.5)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, pid + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(RELINK, pid + ".pdf"), bbox_inches="tight")
    plt.close(fig)
    print(f"  {pid}: perKT n={len(a)}/{len(c)} p={p_kt:.4g} | perCELL n={len(ac)}/{len(cc)} p={p_ce:.4g} "
          f"| {multi} multi-KT cells")

    rows = ([["kinetochore", k[0], k[2], k[1], round(v, 5)] for k, v in KT.items()] +
            [["cell", k[0], "", k[1], round(v, 5)] for k, v in CE.items()])
    lib.record_plot(pid, ["unit", "cell", "track_id", "n_sisterless", "value"], rows,
                    {"metric": metric, "label": label,
                     "mannwhitney_p_per_kinetochore": p_kt, "mannwhitney_p_per_cell": p_ce,
                     "cells_contributing_more_than_one_KT": multi,
                     "why_both": "unit changes the verdict; per-KT can be pseudoreplicated"},
                    __file__,
                    f"{label} kinetochore {metric}, single vs triple, shown per KINETOCHORE and per CELL",
                    source=[LM], key_column="cell")
    rows_all.append((pid, len(a), len(c), p_kt, len(ac), len(cc), p_ce, multi))

print("\nsummary")
for pid, n1, n3, pk, c1, c3, pc, m in rows_all:
    print(f"  {pid:34s} perKT {n1:3d}/{n3:3d} p={pk:8.4g}   perCELL {c1:3d}/{c3:3d} p={pc:8.4g}   multiKT cells={m}")
