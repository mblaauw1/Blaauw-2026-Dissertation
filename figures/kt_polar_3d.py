#!/usr/bin/env python3
"""Joint relationship: TIME (from metaphase onset) × polar-KT AREA × polar-KT DISTANCE-to-plate.
2D view (time vs distance, colour = area, per-track trajectories) + a 3D view. Polar kinetochores only."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa
import lib
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]

LM = list(csv.DictReader(open(SRC[0])))
ph = phase_times(sorted({r["batch"] for r in LM}))
def num(r, k):
    try: return float(r[k])
    except Exception: return None
pts = collections.defaultdict(list)   # track_id -> [(tmeta, dist, area)]
for r in LM:
    if r["label"] != "polar": continue
    mt, at = ph.get(r["batch"], (None, None))
    t = num(r, "t_sec"); d = num(r, "dist_to_plate_um"); a = num(r, "area_um2")
    if None in (t, d, a) or mt is None: continue
    pts[r["track_id"]].append(((t - mt) / 60.0, d, a))
for k in pts: pts[k].sort()
ana = [((at - mt) / 60.0) for mt, at in ph.values() if mt is not None and at is not None and at > mt]
MED_ANA = float(np.median(ana)) if ana else None
allpts = [p for v in pts.values() for p in v]
T = np.array([p[0] for p in allpts]); D = np.array([p[1] for p in allpts]); A = np.array([p[2] for p in allpts])
# USER 2026-07-27: drop the few extreme points that were setting the axis range and ruining the fit
# (a lone dist~35um frame, a handful of area>2.5um2). Robust MAD rule, and it says what it dropped.
_keep = lib.robust_keep(T, D, A, verbose_name="polar time/dist/area")
T, D, A = T[_keep], D[_keep], A[_keep]
_lim = dict(t=(T.min(), T.max()), d=(D.min(), D.max()), a=(A.min(), A.max()))
allpts = [p for p, kp in zip(allpts, _keep) if kp]
# keep the per-track trajectory lines consistent with the trimmed cloud
_ok = {(round(p[0], 6), round(p[1], 6), round(p[2], 6)) for p in allpts}
for _k in list(pts):
    pts[_k] = [p for p in pts[_k] if (round(p[0], 6), round(p[1], 6), round(p[2], 6)) in _ok]


def _save(fig, name, cap):
    fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # Record the plotted cloud (2026-07-29) - was record_plot(["x"], []), an empty placeholder. All three
    # G6 overflow families did this, which is why the overflow board had nothing to test or group.
    # allpts is the robust_keep-trimmed set of (t_min_from_meta, dist_to_plate_um, area_um2) points.
    try:
        _rows = [[round(float(p[0]), 4), round(float(p[1]), 4), round(float(p[2]), 5)] for p in allpts]
        lib.record_plot(name, ["t_min_from_meta", "dist_to_plate_um", "area_um2"], _rows,
                        {"family": "polar3d", "axes": ["time from metaphase onset", "distance to plate",
                                                       "outline area"],
                         "filter": "lib.robust_keep on all three axes"},
                        script=__file__, caption=cap, source=SRC, key_column=None)
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (name, _e))
    print("  " + name)


if __name__ == "__main__":
    # 2D: time vs distance, colour = area, per-track faint trajectories
    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    for tid, v in pts.items():
        if len(v) >= 2:
            ax.plot([p[0] for p in v], [p[1] for p in v], "-", color="#bbb", lw=0.6, alpha=0.5, zorder=1)
    sc = ax.scatter(T, D, c=A, s=26, cmap="viridis", alpha=0.85, edgecolor="white", lw=0.2, zorder=2,
                    vmin=np.percentile(A, 2), vmax=np.percentile(A, 98))
    cb = fig.colorbar(sc, ax=ax); cb.set_label("polar KT area (µm²)")
    ax.axvline(0, ls=":", color="#3b6fb6", lw=1.4); ax.text(0, ax.get_ylim()[1], " metaphase onset", color="#3b6fb6", fontsize=7, va="top")
    if MED_ANA is not None:
        ax.axvline(MED_ANA, ls="--", color="#d1495b", lw=1.2); ax.text(MED_ANA, ax.get_ylim()[1], " median anaphase", color="#d1495b", fontsize=7, va="top")
    ax.set_xlabel("minutes from metaphase onset (cells aligned)"); ax.set_ylabel("distance to plate (µm)")
    ax.set_title(f"Polar KT: time × distance-to-plate × area  (N={len(allpts)} frames, {len(pts)} tracks)", loc="left", fontweight="bold", fontsize=10.5)
    fig.tight_layout(); _save(fig, "G6poly_time_dist_area_2d", "polar time x dist x area (2D)")

    # 3D: time, distance, area
    fig = plt.figure(figsize=(8.4, 6.6)); ax = fig.add_subplot(111, projection="3d")
    for tid, v in pts.items():
        if len(v) >= 2:
            ax.plot([p[0] for p in v], [p[1] for p in v], [p[2] for p in v], "-", color="#bbb", lw=0.6, alpha=0.5)
    # USER 2026-07-27: this used to colour by TIME, which is already the x-axis - so time was encoded twice
    # and AREA (the z-axis) was the hard-to-read variable. Colour by AREA instead, so each of the three
    # variables appears once and the area spread is legible.
    p3 = ax.scatter(T, D, A, c=A, cmap="viridis", s=18, alpha=0.85, edgecolor="white", lw=0.15,
                    vmin=np.percentile(A, 2), vmax=np.percentile(A, 98))
    cb = fig.colorbar(p3, ax=ax, pad=0.1, shrink=0.6); cb.set_label("polar KT area (µm²)")
    ax.set_xlabel("time from metaphase (min)"); ax.set_ylabel("distance to plate (µm)"); ax.set_zlabel("area (µm²)")
    ax.set_title("Polar KT: time × distance × area (3D)", fontweight="bold", fontsize=11)
    ax.view_init(elev=16, azim=-72)
    # USER 2026-08-03 ("idk what this is"): a 3-D scatter is not self-evident, so say on the figure what one
    # point is and how to read the three axes together. Colour duplicates the z-axis deliberately - it makes
    # depth readable on a flat print, where a 3-D projection alone is ambiguous.
    fig.text(0.005, 0.005,
             "HOW TO READ THIS: every point is ONE polar kinetochore on ONE frame. X = minutes from that "
             "cell's metaphase onset; Y = that kinetochore's distance to the metaphase plate (µm); "
             "Z (and the colour) = the area of its traced outline (µm²).\n"
             "So a point drifting left-to-right is time passing, dropping toward the front is the kinetochore "
             "approaching the plate, and rising is its outline getting larger. Colour repeats the Z axis so "
             "depth stays readable in print.",
             fontsize=6.8, color="#444", ha="left", va="bottom", linespacing=1.5)
    _save(fig, "G6poly_time_dist_area_3d", "polar time x dist x area (3D)")

    # bonus: area vs distance, colour = time (does a polar KT that nears the plate change area?)
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    sc = ax.scatter(D, A, c=T, s=24, cmap="plasma", alpha=0.85, edgecolor="white", lw=0.2,
                    vmin=np.percentile(T, 2), vmax=np.percentile(T, 98))
    cb = fig.colorbar(sc, ax=ax); cb.set_label("minutes from metaphase onset")
    from scipy import stats as st
    rho, pv = st.spearmanr(D, A)
    ax.text(0.98, 0.98, f"Spearman(dist,area) ρ={rho:.2f}, p={pv:.1g}\nN={len(allpts)}", transform=ax.transAxes,
            ha="right", va="top", fontsize=7.5, family="monospace", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("distance to plate (µm)"); ax.set_ylabel("polar KT area (µm²)")
    ax.set_title("Polar KT area vs distance-to-plate (coloured by time)", loc="left", fontweight="bold", fontsize=10.5)
    fig.tight_layout(); _save(fig, "G6poly_area_vs_dist", "polar area vs dist colored by time")
    print("done polar-3d")
