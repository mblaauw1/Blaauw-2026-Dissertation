#!/usr/bin/env python3
"""Phase-split VIOLINS (user 2026-07-23): every per-frame metric split into prometaphase / metaphase /
anaphase, drawn as 3 panels on one page (shared y), each panel comparing states (paired/polar/lagging) with
thorough stats (Kruskal + Holm pairwise MW + Cliff's δ)."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
import lib, kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
PHASES = ["prometaphase", "metaphase", "anaphase"]
STATES = ["paired", "polar", "lagging"]

LM = list(csv.DictReader(open(SRC[0])))
# USER 2026-08-05: was `spindle_strain` from KT_TENSION_20260723 (extent along the PLATE NORMAL over
# extent along the plate). Same measurement, renamed: DISTORTION along the spindle
# axis. One axis for every kinetochore, so polar-vs-paired compares like with like. Rows flagged `outlier` graft as ""
# so they are kept in the source table but never plotted, per her rule.
TEN = {(r["track_id"], r["frame"]): ("" if r.get("outlier") == "1" else r.get("spindle_strain", ""))
       for r in csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"))}
for r in LM:
    r["distortion"] = TEN.get((r["track_id"], r["frame"]), "")
def num(r, k):
    try: return float(r[k])
    except Exception: return None


def phase_split(metric, ylabel, title, outname, fmt="{:.2f}"):
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.8), sharey=True)
    allv = [num(r, metric) for r in LM if num(r, metric) is not None]
    if not allv:
        plt.close(fig); return
    ymax = np.percentile(allv, 99) * 1.15
    for ax, ph in zip(axs, PHASES):
        g = {s: [num(r, metric) for r in LM if r["label"] == s and r["phase"] == ph and num(r, metric) is not None] for s in STATES}
        for i, s in enumerate(STATES):
            d = [v for v in g[s] if v is not None]
            if len(d) < 3:
                if d:
                    ax.scatter(np.full(len(d), i), d, s=10, color=COL[s], alpha=0.5)
                continue
            lib.journal_violin(ax, d, i, COL[s], alpha=0.28, lw=1.0, min_n=3)
            ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[s], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
            ax.hlines(np.median(d), i-0.34, i+0.34, color=COL[s], lw=2.2)
            ax.text(i, ymax*0.99, f"{fmt.format(np.median(d))}\nN={len(d)}", ha="center", va="top", fontsize=6.8)
        ax.set_xticks(range(len(STATES))); ax.set_xticklabels(STATES, fontsize=8.5)
        ax.set_title(ph, fontsize=10, fontweight="bold")
        kt_stats.add_group_stats(ax, g, STATES, loc="upper right", fontsize=6.0)
    axs[0].set_ylabel(ylabel); axs[0].set_ylim(top=ymax)
    fig.suptitle(title + " — split by mitotic phase", fontweight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # Record the ACTUAL plotted values (2026-07-29). This used to be record_plot(["x"], []) - a
    # placeholder that registered the figure with an EMPTY data table. The consequence was invisible
    # until the deck was audited: with no rows there is nothing for the significance scan to test and
    # nothing for family grouping to read, so all 79 G6ph_/G6ppt_/G6poly_ figures on the overflow board
    # carried 0 yellow highlights and n=0 in their titles.
    try:
        _rows = []
        for r in LM:
            v = num(r, metric)
            if v is None:
                continue
            _rows.append([r.get("batch", r.get("cell", "")), r.get("track", ""), r.get("label", ""),
                          r.get("phase", ""), round(float(v), 5)])
        lib.record_plot(outname, ["batch", "track", "label", "phase", metric], _rows,
                        {"family": "phase_split", "metric": metric, "states": list(STATES),
                         "phases": list(PHASES), "y": ylabel},
                        script=__file__, caption=title, source=SRC, key_column="batch")
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (outname, _e))
    print("  " + outname)


if __name__ == "__main__":
    M = [
        ("area_um2", "area (µm²)", "Kinetochore area", "G6ph_area"),
        ("perimeter_um", "perimeter (µm)", "Kinetochore perimeter", "G6ph_perimeter"),
        ("circularity", "circularity", "Kinetochore circularity", "G6ph_circularity"),
        ("solidity", "solidity", "Kinetochore solidity", "G6ph_solidity"),
        ("aspect_ratio", "aspect ratio", "Kinetochore stretch (aspect)", "G6ph_aspect"),
        ("elongation", "elongation", "Kinetochore elongation", "G6ph_elongation"),
        ("major_um", "major axis (µm)", "Kinetochore major-axis", "G6ph_major"),
        ("dist_to_plate_um", "distance to plate (µm)", "Kinetochore distance-to-plate", "G6ph_dist"),
        ("anisotropy_par_perp", "anisotropy (spindle/cross)", "Stretch anisotropy", "G6ph_anisotropy"),
        ("stretch_radial_deg", "stretch angle vs plate (°)", "Stretch direction", "G6ph_stretchdir"),
        ("near_far_area_ratio", "near/far area (vase)", "Vase asymmetry", "G6ph_vase"),
        ("reflection_asym_perp", "reflection asymmetry", "Reflection asymmetry", "G6ph_reflasym"),
        ("distortion", "distortion along the spindle axis", "Spindle-axis distortion", "G6ph_strain"),
        ("speed_um_s", "speed (µm/s)", "Kinetochore speed", "G6ph_speed"),
    ]
    for a in M:
        phase_split(*a)
    print(f"done phase-split ({len(M)})")
