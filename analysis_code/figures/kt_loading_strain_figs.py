#!/usr/bin/env python3
"""WITHDRAWN 2026-08-05 — this builder no longer emits anything.

It produced `G6load_strain_over_metaphase` and `G6load_strain_by_state` on the LOADING axis (sister-pair
axis where a sister existed, else windowed displacement). That axis was withdrawn the same day: using a
different axis definition for paired kinetochores than for polar ones made polar-vs-paired a comparison
between two definitions rather than between two states. Her instruction was to use ONE axis for every
kinetochore — the per-frame plate normal — which is what `spindle_strain` already is.

Replacements, both live and placed:
    G6load_strain_over_metaphase  ->  G6tenM_strain_over_time      (META board)
    G6load_strain_by_state        ->  G6tenM_strain_by_state       (NEW_FIGURES, "NEW 2026-08-05" grid)

The figure files were deleted once those replacements were confirmed on a board. This script is kept as
the record of what was tried and why it was dropped, but it EXITS IMMEDIATELY so a full rebuild cannot
resurrect the retired figures. The original body is preserved below the exit.
"""
import sys
print(__doc__.strip().splitlines()[0])
sys.exit(0)

# ---------------------------------------------------------------------------------------------------
# ORIGINAL BODY BELOW — retained for provenance only, never executed.
# ---------------------------------------------------------------------------------------------------

import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib

lib.apply_style()
ROOT = "/Volumes/4 MB"
SRC = f"{ROOT}/annotations/KT_LOADING_AXIS_20260805.csv"
OUT = f"{ROOT}/ablation_figures_20260625/group6_tension"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

MR = {r["Batch Name"]: r for r in lib.load_master()[0]}
NS = {b: (r.get("# Sisterless KTs") or "").strip() for b, r in MR.items()}
def psec(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); v = lib.parse_time(s.lstrip("-"))
    return None if v is None else (-v if neg else v)

rows = [r for r in csv.DictReader(open(SRC))
        if r["in_window"] == "1" and r["outlier"] == "0" and r["load_ratio"] not in ("", None)]
print(f"usable rows: {len(rows)}  (outliers and out-of-window rows excluded, not deleted)")

# normalized metaphase progress per row
recs = []
for r in rows:
    b = r["batch"]; m = psec((MR.get(b, {}) or {}).get("Metaphase Start (s)", ""))
    a = psec((MR.get(b, {}) or {}).get("Anaphase Onset (s)", ""))
    if m is None or a is None or a <= m: continue
    ns = NS.get(b, "")
    if ns not in ("1", "3"): continue
    recs.append((r["label"], ns, (float(r["t_sec"]) - m) / (a - m), float(r["load_ratio"]), b, r["track_id"]))
print(f"rows in 1/3-sisterless cells with a usable window: {len(recs)}")

GROUPS = [("polar", "1", "#e6820e", "-", "o"), ("polar", "3", "#8a4b00", "--", "s"),
          ("paired", "1", "#3b6fb6", "-", "o"), ("paired", "3", "#14385f", "--", "s")]

# ---- FIG 1: load_ratio over normalized metaphase, four series -----------------------------------
fig, ax = plt.subplots(figsize=(9.0, 5.4)); stats_out = {}
for lab, ns, col, ls, mk in GROUPS:
    S = [(f, v) for l, n, f, v, _b, _t in recs if l == lab and n == ns]
    if len(S) < 12: continue
    x = np.array([p[0] for p in S]); y = np.array([p[1] for p in S])
    ax.scatter(x, y, s=4, color=col, alpha=0.10, lw=0)
    bins = np.linspace(0, 1, 11); idx = np.digitize(x, bins)
    bx, bm, blo, bhi = [], [], [], []
    for bi in range(1, len(bins)):
        sel = y[idx == bi]
        if len(sel) >= 4:
            bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
            blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
    if bx:
        ax.plot(bx, bm, ls=ls, marker=mk, color=col, lw=2.2, ms=3.6)
        ax.fill_between(bx, blo, bhi, color=col, alpha=0.10)
    rho, p = st.spearmanr(x, y)
    ncell = len({b for l, n, _f, _v, b, _t in recs if l == lab and n == ns})
    stats_out[f"{ns}-sis {lab}"] = {"n_points": len(x), "n_cells": ncell,
                                    "median": round(float(np.median(y)), 4),
                                    "rho_vs_progress": round(float(rho), 3), "p": float(p)}
    ax.plot([], [], color=col, ls=ls, marker=mk, ms=3.6, lw=2.2,
            label=f"{ns}-sis {lab} (n={len(x)}, {ncell} cells): med={np.median(y):.2f}, rho={rho:+.2f}, p={p:.1g}")
ax.axhline(1.0, color="#888", ls=":", lw=1.0)
ax.set_xlabel("fraction of metaphase (0 = metaphase onset, 1 = that cell's anaphase onset)")
ax.set_ylabel("extent along loading axis / extent across it")
ax.set_title("Kinetochore strain along its LOADING axis, over metaphase\n"
             "loading axis = sister-pair axis where available, else windowed displacement "
             "(6.5° and 12° from the plate normal; the outline long axis was 58.5°)",
             loc="left", fontweight="bold", fontsize=9.5)
ax.legend(fontsize=6.8, loc="best")
fig.tight_layout(); fig.savefig(f"{OUT}/G6load_strain_over_metaphase.png", dpi=200, bbox_inches="tight"); plt.close(fig)
lib.record_plot("G6load_strain_over_metaphase",
                ["label", "n_sisterless", "frac_meta_to_ana", "load_ratio", "batch", "track_id"],
                [[l, n, round(f, 4), round(v, 4), b, t] for l, n, f, v, b, t in recs], stats_out,
                SCRIPT, "Kinetochore strain along the loading axis over metaphase", source=[SRC], key_column="batch")

# ---- FIG 2: polar vs paired, single vs triple ----------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(6.6, 5.0)); pos = 0; xt, xl = [], []; s2 = {}
for lab, ns, col, ls, mk in GROUPS:
    v = [x[3] for x in recs if x[0] == lab and x[1] == ns]
    if len(v) < 5: continue
    lib.journal_violin(ax2, v, pos, col, alpha=0.30, lw=1.0)
    ax2.scatter(np.full(len(v), pos) + (np.random.RandomState(pos).rand(len(v))-.5)*0.22, v,
                s=lib.VIOLIN_DOT_S, color=col, alpha=lib.VIOLIN_DOT_ALPHA_DENSE, edgecolor="none")
    ax2.hlines(np.median(v), pos-0.32, pos+0.32, color=col, lw=2.2)
    ax2.hlines(np.mean(v), pos-0.26, pos+0.26, color=col, lw=1.3, ls=(0, (2, 1.5)))
    ax2.scatter([pos], [np.mean(v)], marker="D", s=28, facecolor="white", edgecolor=col, lw=1.2, zorder=5)
    ax2.text(pos, max(v), f"med {np.median(v):.2f}\n{len(v)}", ha="center", va="bottom", fontsize=7)
    xt.append(pos); xl.append(f"{ns}-sis\n{lab}"); s2[f"{ns}-sis {lab}"] = len(v); pos += 1
ax2.axhline(1.0, color="#888", ls=":", lw=1.0)
ax2.set_xticks(xt); ax2.set_xticklabels(xl, fontsize=8.5)
ax2.set_ylabel("extent along loading axis / extent across it")
ax2.set_title("Kinetochore strain along the loading axis (metaphase only)", loc="left", fontweight="bold", fontsize=10)
fig2.tight_layout(); fig2.savefig(f"{OUT}/G6load_strain_by_state.png", dpi=200, bbox_inches="tight"); plt.close(fig2)
lib.record_plot("G6load_strain_by_state", ["label", "n_sisterless", "load_ratio", "batch"],
                [[l, n, round(v, 4), b] for l, n, _f, v, b, _t in recs], s2,
                SCRIPT, "Kinetochore strain along the loading axis by state", source=[SRC], key_column="batch")

for k, v in sorted(stats_out.items()): print(f"  {k:16s} {v}")
print(f"-> {OUT}/G6load_strain_over_metaphase.png  and  G6load_strain_by_state.png")
