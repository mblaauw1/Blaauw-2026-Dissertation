#!/usr/bin/env python3
"""Polar-KT metrics over time, MARKERS COLOURED BY PHASE with a distinct linear FIT per phase
(user 2026-07-23). x = minutes from metaphase onset (cells aligned). Per phase: colour, fit line over that
phase's own frames, slope (/min) + Spearman reported."""
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
PHCOL = {"prometaphase": "#7a7a7a", "metaphase": "#3b6fb6", "anaphase": "#d1495b"}
PHASES = ["prometaphase", "metaphase", "anaphase"]

LM = [r for r in csv.DictReader(open(SRC[0]))
      if r["label"] == "polar" and not lib.is_prophase_ablation(r["batch"])]   # prophase excluded
# USER 2026-08-05: was `spindle_strain` from KT_TENSION_20260723 (extent along the PLATE NORMAL over
# extent along the plate). Same measurement, renamed: DISTORTION along the spindle
# axis. One axis for every kinetochore, so polar-vs-paired compares like with like. Rows flagged `outlier` graft as ""
# so they are kept in the source table but never plotted, per her rule.
TEN = {(r["track_id"], r["frame"]): ("" if r.get("outlier") == "1" else r.get("spindle_strain", ""))
       for r in csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"))}
for r in LM: r["distortion"] = TEN.get((r["track_id"], r["frame"]), "")
ph = phase_times(sorted({r["batch"] for r in LM}))
for r in LM:
    mt, at = ph.get(r["batch"], (None, None))
    try: tt = float(r["t_sec"])
    except Exception: tt = None
    r["tmeta"] = ((tt - mt) / 60.0) if (mt is not None and tt is not None) else None
_ana = [((at - mt) / 60.0) for mt, at in ph.values() if mt is not None and at is not None and at > mt]
MED_ANA = float(np.median(_ana)) if _ana else None
def num(r, k):
    try: return float(r[k])
    except Exception: return None


def plot(metric, ylabel, title, outname):
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    # USER 2026-07-27: extreme points were setting the y-range and dragging the per-phase fits (e.g. the
    # handful of area>2 um2 frames on G6ppt_area). Trim on the POOLED metric so every phase is cut at the
    # same threshold, then fit each phase on what is left.
    _allrs = [r for r in LM if r["tmeta"] is not None and num(r, metric) is not None]
    _keep = lib.robust_keep([num(r, metric) for r in _allrs], verbose_name=f"{outname}/{metric}")
    _ok = {id(r) for r, kp in zip(_allrs, _keep) if kp}
    for phn in PHASES:
        rs = [r for r in _allrs if r["phase"] == phn and id(r) in _ok]
        if not rs: continue
        x = np.array([r["tmeta"] for r in rs]); y = np.array([num(r, metric) for r in rs])
        ax.scatter(x, y, s=12, color=PHCOL[phn], alpha=0.5, edgecolor="white", lw=0.15)
        lab = f"{phn} (n={len(x)})"
        # USER 2026-08-10: a group's trend stops at THAT group's median metaphase duration.
        _cap = lib.trend_cap([r["batch"] for r in rs])
        if _cap is not None:
            _k = x <= _cap
            if _k.sum() >= 4:
                x, y = x[_k], y[_k]; lib.annotate_trend_cap(ax, _cap, color=PHCOL[phn])
        if len(x) >= 4:
            b, a = np.polyfit(x, y, 1); xf = np.linspace(x.min(), x.max(), 20)
            ax.plot(xf, a + b*xf, "-", color=PHCOL[phn], lw=2.4)
            rho, p = st.spearmanr(x, y)
            lab = f"{phn}: slope={b:+.3f}/min, ρ={rho:+.2f}, p={p:.1g} (n={len(x)})"
        ax.plot([], [], color=PHCOL[phn], lw=2.4, label=lab)
    ax.axvline(0, ls=":", color="#3b6fb6", lw=1.2)
    if MED_ANA is not None: ax.axvline(MED_ANA, ls="--", color="#d1495b", lw=1.0)
    ax.set_xlabel("minutes from metaphase onset (cells aligned)"); ax.set_ylabel(ylabel)
    ax.set_title(f"Polar KT — {title} over time, by phase", loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=7.5, loc="best")
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # Record the plotted points (2026-07-29) - was record_plot(["x"], []), an empty placeholder table.
    # See the note in kt_phase_split.py: an empty table means the significance scan and family grouping
    # have nothing to read, which is why the overflow board had no highlights.
    try:
        _rows = []
        for r in _allrs:
            if id(r) not in _ok:
                continue
            v = num(r, metric)
            if v is None:
                continue
            _rows.append([r.get("batch", r.get("cell", "")), r.get("track", ""), r.get("phase", ""),
                          round(float(r["tmeta"]), 4), round(float(v), 5)])
        lib.record_plot(outname, ["batch", "track", "phase", "t_min_from_meta", metric], _rows,
                        {"family": "polar_phase_time", "metric": metric, "phases": list(PHASES),
                         "x": "minutes from metaphase onset", "y": ylabel,
                         "filter": "lib.robust_keep on the metric"},
                        script=__file__, caption=title, source=SRC, key_column="batch")
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (outname, _e))
    print("  " + outname)


if __name__ == "__main__":
    M = [
        ("area_um2", "area (µm²)", "area", "G6ppt_area"),
        ("dist_to_plate_um", "distance to plate (µm)", "distance-to-plate", "G6ppt_dist"),
        ("aspect_ratio", "aspect ratio", "stretch", "G6ppt_aspect"),
        ("circularity", "circularity", "circularity", "G6ppt_circularity"),
        ("distortion", "distortion along the spindle axis", "spindle-axis distortion", "G6ppt_strain"),
        ("major_um", "major axis (µm)", "major-axis", "G6ppt_major"),
        ("stretch_radial_deg", "stretch angle vs plate (°)", "stretch direction", "G6ppt_stretchdir"),
        ("speed_um_s", "speed (µm/s)", "speed", "G6ppt_speed"),
    ]
    for a in M:
        plot(*a)
    print(f"done polar-phase-time ({len(M)})")
