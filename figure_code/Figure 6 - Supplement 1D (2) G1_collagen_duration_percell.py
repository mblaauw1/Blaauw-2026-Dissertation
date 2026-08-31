#!/usr/bin/env python3
"""Accompanying FIGURES for the collagen / triple-ablation duration table.

USER 2026-08-19 (to-do list 0819 1pm), all-figures item 17:
    "What is the table on artboard 2 and copied below? Move to supplemental, and also make accompanying
     figure(s) for its data and place on supplemental"

WHAT THE TABLE IS (answered on the figure itself, so the answer travels with it):
    `G1_collagen_duration_table` on META_FIGURES_20260814 artboard 2. It is a METAPHASE-DURATION comparison
    between cells plated on COLLAGEN and the triple-ablation cells, listing each collagen cell by name plus
    the fastest and slowest quartiles of the triple-ablation cells. Collagen is a plating SUBSTRATE, not a
    drug (feedback_collagen_not_a_drug_exclusion), so those cells sit inside the normal cohorts and this
    table exists to show whether the substrate moved metaphase duration.

TWO FIGURES, because the table carries two separable things:
    p1  the DISTRIBUTIONS — every collagen cell and every triple-ablation cell as one point per cell, with
        the group median, so the reader sees the spread the table's mean/SD summarises.
    p2  the QUARTILE CONTRAST the table's second and third columns are about — the fastest and slowest
        triple-ablation quartiles against the collagen cells, cell by cell.

Both are single-axes figures: her item 16 forbids combination figures that can only be moved as one piece.
"""
import collections
import csv
import os
import sys

import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

lib.apply_style()
ROOT = "/Volumes/4 MB"
SRC = f"{ROOT}/ablation_plots/data/G1_collagen_duration_table.csv"
OUT = f"{ROOT}/ablation_figures_20260625/group1"
SCRIPT = __file__

COL = {"collagen": lib.PALETTE.get("Collagen (2/3-sis on-target)", "#e69f00"),
       "triple_fastest_quartile": "#0072B2",
       "triple_slowest_quartile": "#56194d"}
NICE = {"collagen": "collagen (2/3-sis on-target)",
        "triple_fastest_quartile": "triple ablation — fastest 25%",
        "triple_slowest_quartile": "triple ablation — slowest 25%"}


def load():
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(SRC, newline="", encoding="utf-8", errors="replace")):
        try:
            per[r["section"]].append((r["batch"], float(r["metaphase_duration_min"])))
        except Exception:
            continue
    return per


def p1(per):
    """Distributions: one point per cell, group median marked."""
    order = ["collagen", "triple_fastest_quartile", "triple_slowest_quartile"]
    order = [k for k in order if per.get(k)]
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    rows = []
    for i, k in enumerate(order):
        v = [d for _, d in per[k]]
        jit = (np.random.default_rng(7 + i).random(len(v)) - 0.5) * 0.26
        ax.scatter(np.full(len(v), i) + jit, v, s=42, color=COL[k], alpha=.85,
                   edgecolor="w", lw=.6, zorder=3)
        med = float(np.median(v))
        ax.hlines(med, i - .30, i + .30, color=COL[k], lw=4.0, zorder=4)
        ax.annotate(f"median {med:.1f} min\nn={len(v)}", xy=(i, 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -46), textcoords="offset points", ha="center", va="top",
                    fontsize=8, color="#444")
        for b, d in per[k]:
            rows.append([k, b, round(d, 3)])
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([NICE[k] for k in order], fontsize=9)
    ax.set_xlim(-0.6, len(order) - 0.4)
    ax.set_ylabel("Metaphase duration (min)")
    ax.set_ylim(bottom=0)
    # the table's own comparison, stated as a test rather than left to the eye
    sub = ""
    if per.get("collagen") and per.get("triple_fastest_quartile") and per.get("triple_slowest_quartile"):
        trip = [d for k in ("triple_fastest_quartile", "triple_slowest_quartile") for _, d in per[k]]
        coll = [d for _, d in per["collagen"]]
        try:
            u = stats.mannwhitneyu(coll, trip, alternative="two-sided").pvalue
            sub = f"\ncollagen vs the two triple-ablation quartiles pooled: Mann-Whitney p={u:.3g}"
        except Exception:
            pass
    ax.set_title("Metaphase duration — collagen cells vs triple-ablation quartiles\n"
                 "every cell shown; thick bar = group median" + sub,
                 loc="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G1_collagen_duration_dist.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G1_collagen_duration_dist", ["section", "batch", "metaphase_duration_min"], rows,
                    {"type": "per-cell distribution", "accompanies": "G1_collagen_duration_table",
                     "why": "user 2026-08-19 item 17 -- figures for the artboard-2 table's data"},
                    SCRIPT, "Metaphase duration: collagen cells vs triple-ablation quartiles",
                    source=[SRC], key_column="batch")
    print("wrote G1_collagen_duration_dist.png")


def p2(per):
    """The quartile contrast, cell by cell -- a ranked bar per cell, coloured by section."""
    items = [(k, b, d) for k in ("triple_fastest_quartile", "collagen", "triple_slowest_quartile")
             for b, d in per.get(k, [])]
    if not items:
        print("skip p2: no rows"); return
    items.sort(key=lambda q: q[2])
    fig, ax = plt.subplots(figsize=(8.6, 0.26 * len(items) + 2.0))
    y = np.arange(len(items))
    ax.barh(y, [q[2] for q in items], color=[COL[q[0]] for q in items], height=.72, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels([q[1] for q in items], fontsize=6.4)
    ax.set_xlabel("Metaphase duration (min)")
    ax.invert_yaxis()
    seen = []
    for k in ("triple_fastest_quartile", "collagen", "triple_slowest_quartile"):
        if per.get(k):
            ax.barh([], [], color=COL[k], label=NICE[k]); seen.append(k)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title("Every cell behind the artboard-2 table, ranked by metaphase duration",
                 loc="left", fontweight="bold", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G1_collagen_duration_percell.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G1_collagen_duration_percell", ["section", "batch", "metaphase_duration_min"],
                    [[k, b, round(d, 3)] for k, b, d in items],
                    {"type": "per-cell ranked bars", "accompanies": "G1_collagen_duration_table",
                     "why": "user 2026-08-19 item 17"},
                    SCRIPT, "Every cell behind the collagen/triple duration table, ranked",
                    source=[SRC], key_column="batch")
    print("wrote G1_collagen_duration_percell.png")


if __name__ == "__main__":
    if not os.path.exists(SRC):
        sys.exit(f"missing {SRC}")
    per = load()
    print(f"loaded {sum(len(v) for v in per.values())} cells in {len(per)} sections")
    p1(per)
    p2(per)
