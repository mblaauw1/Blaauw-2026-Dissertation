#!/usr/bin/env python3
"""METAPHASE-ONSET -> ANAPHASE versions of the "over time, aligned to metaphase onset" family
(artboard 02 / figures 454-470). User 2026-07-27, four requirements:

  1. window = metaphase onset -> anaphase ONLY. Each cell is cut at its OWN anaphase onset, not at the
     cohort median, so no cell contributes frames from a phase it was not in.
  2. LAGGING left out — these are the metaphase-behaviour plots; only polar and paired.
  3. trendlines REFIT on that window (linear fit per state + a binned median/IQR band), never carried over
     from the full-mitosis version.
  4. OUTLIERS DROPPED so the fit and the axes are right: a few very large speeds or vase ratios were
     setting the y-range and dragging every line. Robust MAD rule (lib.robust_keep), pooled across the two
     states so both are cut at the same threshold; every drop is printed.

Figures are written as G6timeMA_<metric> alongside the originals, which are left untouched."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]
COL = {"paired": "#3b6fb6", "polar": "#e6820e"}          # lagging deliberately absent

LM = list(csv.DictReader(open(SRC[0])))
# USER 2026-08-06: prophase ablations are excluded from every plot that has no prophase group.
# This file reads annotation CSVs directly, so the shared gates do not reach it.
LM = [r for r in LM if not lib.is_prophase_ablation(r.get("batch",""))]

# USER 2026-08-05: grafts the kinetochore's LOADING-axis strain, not `spindle_strain`. One axis for every kinetochore
# (paired, polar, lagging alike), so the comparison is like for like; the plate line is already picked
# per FRAME, so a rotating plate is handled. Outlier-flagged rows graft as "" — kept, not plotted.
TEN = {(r["track_id"], r["frame"]): r for r in csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"))}
for r in LM:
    t = TEN.get((r["track_id"], r["frame"]))
    r["distortion"] = (t["spindle_strain"] if (t and t.get("outlier") != "1") else "")
ph = phase_times(sorted({r["batch"] for r in LM}))
for r in LM:
    mt, at = ph.get(r["batch"], (None, None))
    try: tt = float(r["t_sec"])
    except Exception: tt = None
    r["tmeta"] = ((tt - mt) / 60.0) if (mt is not None and tt is not None) else None
    r["ana_min"] = ((at - mt) / 60.0) if (mt is not None and at is not None and at > mt) else None
    # USER 2026-08-05: "first normalize the metaphase axis". Fraction of THIS cell's own metaphase:
    # 0 = metaphase onset, 1 = its own anaphase onset. Cells differ several-fold in metaphase length, so
    # on the raw minute axis a short cell's anaphase lines up with a long cell's mid-metaphase and the
    # binned trend mixes different phases together.
    r["tfrac"] = (r["tmeta"] / r["ana_min"]) if (r["tmeta"] is not None and r["ana_min"]) else None

# THE WINDOW: 0 <= t <= that cell's own anaphase onset, polar/paired only
WIN = [r for r in LM
       if r["label"] in COL and r["tmeta"] is not None and r["ana_min"] is not None
       and 0.0 <= r["tmeta"] <= r["ana_min"]]
NCELL = len({r["batch"] for r in WIN})
print(f"metaphase->anaphase window: {len(WIN)} frames, {NCELL} cells, "
      f"{len({r['track_id'] for r in WIN})} tracks (lagging excluded)")


def num(r, k):
    try: return float(r[k])
    except Exception: return None


def traj(metric, ylabel, title, outname, normalize=False):
    rs_all = [r for r in WIN if num(r, metric) is not None]
    if len(rs_all) < 12:
        print(f"  skip {outname} (n={len(rs_all)})"); return
    keep = lib.robust_keep([num(r, metric) for r in rs_all], verbose_name=f"{outname}/{metric}")
    rs_all = [r for r, k in zip(rs_all, keep) if k]

    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    ylo, yhi, xhi = np.inf, -np.inf, 0.0
    for st_name, colr in COL.items():
        rs = [r for r in rs_all if r["label"] == st_name]
        if len(rs) < 6:
            continue
        _xk = "tfrac" if normalize else "tmeta"
        rs = [r for r in rs if r.get(_xk) is not None]
        if len(rs) < 6: continue
        x = np.array([r[_xk] for r in rs], float); y = np.array([num(r, metric) for r in rs], float)
        ylo = min(ylo, y.min()); yhi = max(yhi, y.max()); xhi = max(xhi, x.max())
        ax.scatter(x, y, s=6, color=colr, alpha=0.16, lw=0)
        # USER 2026-08-10: on the MINUTES axis a group's trend stops at that group's median metaphase
        # duration. (The `normalize` axis is already 0-1 across metaphase->anaphase, so it needs no cap.)
        if not normalize:
            _cap = lib.trend_cap([r["batch"] for r in rs])
            if _cap is not None:
                _k = x <= _cap
                if _k.sum() >= 4:
                    x, y = x[_k], y[_k]; rs = [q for q, kk in zip(rs, _k) if kk]
                    lib.annotate_trend_cap(ax, _cap, color=colr)
        # binned median +/- IQR
        bins = np.linspace(0, 1.0 if normalize else x.max(), 11 if normalize else 10); idx = np.digitize(x, bins)
        bx, bm, blo, bhi = [], [], [], []
        for bi in range(1, len(bins)):
            sel = y[idx == bi]
            if len(sel) >= 4:
                bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
                blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
        if bx:
            ax.plot(bx, bm, "-o", color=colr, lw=2.0, ms=3.2, zorder=3)
            ax.fill_between(bx, blo, bhi, color=colr, alpha=0.13, zorder=1)
        # REFIT the trendline on this window only
        b, a = np.polyfit(x, y, 1); xf = np.linspace(0, 1.0 if normalize else x.max(), 20)
        ax.plot(xf, a + b*xf, "--", color=colr, lw=1.6, zorder=4)
        rho, p = st.spearmanr(x, y)
        ax.plot([], [], color=colr, lw=2.0,
                label=f"{st_name}: slope={b:+.3g}/{'metaphase' if normalize else 'min'}, ρ={rho:+.2f}, p={p:.1g} (n={len(x)})")
    if not np.isfinite(ylo):
        plt.close(fig); print(f"  skip {outname} (no state had enough points)"); return
    pad = (yhi - ylo) * 0.08 or 0.1
    ax.set_ylim(ylo - pad, yhi + pad)          # axes fitted to the TRIMMED data
    ax.set_xlim(-0.02, 1.02) if normalize else ax.set_xlim(-0.5, xhi * 1.02)
    ax.set_xlabel("fraction of metaphase (0 = metaphase onset, 1 = that cell's own anaphase onset)"
                  if normalize else "minutes from metaphase onset (each cell cut at its own anaphase onset)")
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} — metaphase to anaphase ({NCELL} cells)", loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=7.5, loc="best")
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # Record the ACTUAL plotted values (2026-08-03). This was record_plot(["x"], []) - a placeholder that
    # registered the figure with an EMPTY data table, so it could not be checked against its own data and any
    # _zoom companion was built from nothing. Same bug fixed in kt_phase_split.py on 2026-07-29, never
    # propagated here. rs_all is already the trimmed, plotted set.
    try:
        _rows = [[r.get("batch", r.get("cell", "")), r.get("label", ""),
                  round(float(r["tfrac" if normalize else "tmeta"]), 4), round(float(num(r, metric)), 5)]
                 for r in rs_all if r.get("tfrac" if normalize else "tmeta") is not None and num(r, metric) is not None]
        lib.record_plot(outname, ["batch", "label",
                                  "frac_meta_to_ana" if normalize else "t_min_from_meta", metric], _rows,
                        {"family": "time_meta2ana", "metric": metric, "y": ylabel, "n_cells": NCELL},
                        script=__file__, caption=f"{title} (metaphase->anaphase, no lagging)",
                        source=SRC, key_column="batch")
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (outname, _e))
    print("  " + outname)


if __name__ == "__main__":
    METRICS = [
        ("area_um2", "area (µm²)", "Kinetochore area", "G6timeMA_area"),
        ("perimeter_um", "perimeter (µm)", "Kinetochore perimeter", "G6timeMA_perimeter"),
        ("circularity", "circularity", "Kinetochore circularity", "G6timeMA_circularity"),
        ("solidity", "solidity", "Kinetochore solidity", "G6timeMA_solidity"),
        ("convexity", "convexity", "Kinetochore convexity", "G6timeMA_convexity"),
        ("aspect_ratio", "aspect ratio", "Kinetochore stretch (aspect)", "G6timeMA_aspect"),
        ("elongation", "elongation", "Kinetochore elongation", "G6timeMA_elongation"),
        ("major_um", "major axis (µm)", "Kinetochore major-axis", "G6timeMA_major"),
        ("dist_to_plate_um", "distance to plate (µm)", "Kinetochore distance-to-plate", "G6timeMA_dist"),
        ("anisotropy_par_perp", "anisotropy (spindle/cross)", "Stretch anisotropy", "G6timeMA_anisotropy"),
        ("stretch_radial_deg", "stretch angle vs plate (°)", "Stretch direction", "G6timeMA_stretchdir"),
        ("near_far_area_ratio", "near/far area (vase)", "Vase asymmetry", "G6timeMA_vase"),
        ("reflection_asym_perp", "reflection asymmetry", "Reflection asymmetry", "G6timeMA_reflasym"),
        ("R_toward_um", "toward-plate reach (µm)", "Leading-edge reach", "G6timeMA_Rtoward"),
        ("speed_um_s", "speed (µm/s)", "Kinetochore speed", "G6timeMA_speed"),
        ("radial_speed_um_s", "toward-plate velocity (µm/s)", "Radial velocity", "G6timeMA_radialspeed"),
        ("distortion", "distortion along the spindle axis", "Spindle-axis distortion", "G6timeMA_strain"),
    ]
    for m, yl, t, name in METRICS:
        traj(m, yl, t, name, normalize=(name == "G6timeMA_dist"))   # USER 2026-08-05: dist axis normalized
    print(f"done metaphase->anaphase trajectories ({len(METRICS)})")
