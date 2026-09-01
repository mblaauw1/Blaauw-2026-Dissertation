#!/usr/bin/env python3
"""Time-resolved trajectories for (nearly) every per-frame KT measurement (user 2026-07-23: almost
everything is measured frame-by-frame, so every quantity needs a plot with TIME on an axis).

For each metric: median ± IQR band vs MITOTIC PROGRESS (0 = metaphase onset, 1 = anaphase onset), one band
per state (paired / polar / lagging), with the per-state Spearman(progress, metric) reported. Sources:
KT_LANDMARK_ANALYSIS (shape/landmark/motion) + KT_TENSION (spindle strain) + KT_CHROMO_ANALYSIS (chromosome
geometry vs its own t_sec)."""
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
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}

LM = list(csv.DictReader(open(SRC[0])))
LM = [r for r in LM if not lib.is_prophase_ablation(r.get("batch",""))]   # prophase excluded (no prophase group)
# USER 2026-08-05: grafts the kinetochore's LOADING-axis strain, not `spindle_strain`. One axis for every kinetochore
# (paired, polar, lagging alike), so the comparison is like for like; the plate line is already picked
# per FRAME, so a rotating plate is handled. Outlier-flagged rows graft as "" — kept, not plotted.
TEN = {(r["track_id"], r["frame"]): r for r in csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"))}
for r in LM:  # graft loading-axis strain onto landmark rows
    t = TEN.get((r["track_id"], r["frame"]))
    r["distortion"] = (t["spindle_strain"] if (t and t.get("outlier") != "1") else "")
ph = phase_times(sorted({r["batch"] for r in LM}))
# ANCHOR t=0 at METAPHASE ONSET in REAL minutes, so different cells align at the same event and can be
# overlaid/compared (user 2026-07-23). Also stash each cell's own anaphase time (min) for a per-cell marker.
for r in LM:
    mt, at = ph.get(r["batch"], (None, None))
    try: tt = float(r["t_sec"])
    except Exception: tt = None
    r["tmeta"] = ((tt - mt) / 60.0) if (mt is not None and tt is not None) else None
    r["ana_min"] = ((at - mt) / 60.0) if (mt is not None and at is not None and at > mt) else None
_ana = [((at - mt) / 60.0) for mt, at in ph.values() if mt is not None and at is not None and at > mt]
MED_ANA = float(np.median(_ana)) if _ana else None


def num(r, k):
    try: return float(r[k])
    except Exception: return None


def band(ax, xs, ys, color, label, ls="-", marker="o", batches=None):
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    m = np.isfinite(xs) & np.isfinite(ys); xs, ys = xs[m], ys[m]
    if len(xs) < 6: return None
    ax.scatter(xs, ys, s=5, color=color, alpha=0.13, lw=0)
    # USER 2026-08-10: a group's TREND may not run past THAT group's median metaphase duration. Scatter still
    # shows every point; the binned median/IQR band and the fit are computed only on x <= cap.
    _cap = lib.trend_cap(batches) if batches else None
    if _cap is not None:
        _k = xs <= _cap
        if _k.sum() >= 4:
            xs, ys = xs[_k], ys[_k]
            lib.annotate_trend_cap(ax, _cap, color=color)
    lo, hi = np.percentile(xs, [2, 98]); bins = np.linspace(lo, hi, 12); idx = np.digitize(xs, bins)
    bx, bm, blo, bhi = [], [], [], []
    for bi in range(1, len(bins)):
        sel = ys[idx == bi]
        if len(sel) >= 4:
            bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel)); blo.append(np.percentile(sel,25)); bhi.append(np.percentile(sel,75))
    if bx:
        ax.plot(bx, bm, ls=ls, marker=marker, color=color, lw=2.2, ms=3.5)
        ax.fill_between(bx, blo, bhi, color=color, alpha=0.10)
    rho, p = st.spearmanr(xs, ys)
    ax.plot([], [], color=color, lw=2.2, ls=ls, marker=marker, ms=3.5,
            label=f"{label} (n={len(xs)}, ρ={rho:+.2f}, p={p:.1g})")
    return rho


# ITEM 10 (user 2026-08-04): G6time_dist pooled SINGLE and TRIPLE ablations into one trendline per state.
# Split each state's band by ablation number so there are 6 trendlines (3 states x {1,3}). The ablation
# number comes from the master "# Sisterless KTs" column — never from batch/file names.
_MASTER, _ = lib.load_master_plots()
_NSIS = {r["Batch Name"]: (r.get("# Sisterless KTs", "") or "").strip() for r in _MASTER}
def nsis(r): return _NSIS.get(r.get("batch", ""), "")
ABL_STYLE = {"1": ("-", "o", "single"), "3": ("--", "s", "triple")}


def traj(metric, ylabel, title, outname, split_by_ablation=False):
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    if split_by_ablation:
        for k in COL:
            for n, (ls, mk, nm) in ABL_STYLE.items():
                rs = [r for r in LM if r["label"] == k and nsis(r) == n
                      and r["tmeta"] is not None and num(r, metric) is not None]
                band(ax, [r["tmeta"] for r in rs], [num(r, metric) for r in rs], COL[k],
                     f"{k} · {nm}", ls=ls, marker=mk, batches=[r["batch"] for r in rs])
    else:
      for k in COL:
        rs = [r for r in LM if r["label"] == k and r["tmeta"] is not None and num(r, metric) is not None]
        band(ax, [r["tmeta"] for r in rs], [num(r, metric) for r in rs], COL[k], k,
             batches=[r["batch"] for r in rs])
    ax.axvline(0, ls=":", color="#3b6fb6", lw=1.4)
    _y0, _y1 = ax.get_ylim()
    ax.text(0, _y1, " metaphase onset", color="#3b6fb6", fontsize=7, va="top")
    if MED_ANA is not None:
        ax.axvline(MED_ANA, ls="--", color="#d1495b", lw=1.2)
        # drop this label a line lower: at MED_ANA ~ 12 min the two captions collided on every metric
        ax.text(MED_ANA, _y1 - 0.055 * (_y1 - _y0), " median anaphase", color="#d1495b", fontsize=7, va="top")
    ax.set_xlabel("minutes from metaphase onset (0 = metaphase onset; cells aligned here)"); ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=10.5); ax.legend(fontsize=7.5, loc="best")
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # Record the ACTUAL plotted values (2026-08-03). This was record_plot(["x"], []) - a placeholder that
    # registered the figure with an EMPTY data table, so the plot could not be checked against its own data
    # and any _zoom companion built from that CSV was built from nothing. The identical bug was found and
    # fixed in kt_phase_split.py on 2026-07-29 but never propagated to this file.
    try:
        _rows = [[r.get("batch", r.get("cell", "")), r.get("label", ""), nsis(r), round(float(r["tmeta"]), 4),
                  round(float(num(r, metric)), 5)]
                 for r in LM
                 if r.get("label") in COL and r.get("tmeta") is not None and num(r, metric) is not None]
        lib.record_plot(outname, ["batch", "label", "n_sisterless", "t_min_from_meta", metric], _rows,
                        {"family": "time", "metric": metric, "y": ylabel,
                         "split_by_ablation": bool(split_by_ablation),
                         **({"item10": "6 trendlines = 3 states x {single, triple}; ablation number from master "
                                       "'# Sisterless KTs'"} if split_by_ablation else {})},
                        script=__file__, caption=title, source=SRC, key_column="batch")
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (outname, _e))
    print("  " + outname)


if __name__ == "__main__":
    METRICS = [
        ("area_um2", "area (µm²)", "Kinetochore area over mitosis", "G6time_area"),
        ("perimeter_um", "perimeter (µm)", "Kinetochore perimeter over mitosis", "G6time_perimeter"),
        ("circularity", "circularity", "Kinetochore circularity over mitosis", "G6time_circularity"),
        ("solidity", "solidity", "Kinetochore solidity over mitosis", "G6time_solidity"),
        ("convexity", "convexity", "Kinetochore convexity over mitosis", "G6time_convexity"),
        ("aspect_ratio", "aspect ratio", "Kinetochore stretch (aspect) over mitosis", "G6time_aspect"),
        ("elongation", "elongation", "Kinetochore elongation over mitosis", "G6time_elongation"),
        ("major_um", "major axis (µm)", "Kinetochore major-axis over mitosis", "G6time_major"),
        ("dist_to_plate_um", "distance to plate (µm)", "Kinetochore distance-to-plate over mitosis", "G6time_dist"),
        ("anisotropy_par_perp", "anisotropy (spindle/cross)", "Stretch anisotropy over mitosis", "G6time_anisotropy"),
        ("stretch_radial_deg", "stretch angle vs plate (°)", "Stretch direction over mitosis", "G6time_stretchdir"),
        ("near_far_area_ratio", "near/far area (vase)", "Vase asymmetry over mitosis", "G6time_vase"),
        ("reflection_asym_perp", "reflection asymmetry", "Reflection asymmetry over mitosis", "G6time_reflasym"),
        ("R_toward_um", "toward-plate reach (µm)", "Leading-edge reach over mitosis", "G6time_Rtoward"),
        ("speed_um_s", "speed (µm/s)", "Kinetochore speed over mitosis", "G6time_speed"),
        ("radial_speed_um_s", "toward-plate speed (µm/s)", "Radial speed over mitosis", "G6time_radialspeed"),
        ("distortion", "distortion along the spindle axis", "Spindle-axis distortion over mitosis", "G6time_strain"),
    ]
    # ITEM 10: only the distance-to-plate plot she named is split single-vs-triple. Add ids here to extend.
    SPLIT_ABL = {"G6time_dist"}
    for m, yl, t, name in METRICS:
        traj(m, yl, t, name, split_by_ablation=(name in SPLIT_ABL))
    print(f"done time-trajectories ({len(METRICS)}); split single/triple: {sorted(SPLIT_ABL)}")
