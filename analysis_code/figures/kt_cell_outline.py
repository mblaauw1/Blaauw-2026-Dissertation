#!/usr/bin/env python3
"""Whole-cell outline analysis + its relationship to kinetochore metrics over mitosis.
cell_outlines.csv = periodic whole-cell traces. Compute cell area / perimeter / circularity / plate-symmetry
per frame, track them over mitotic time, and correlate with the KT metrics measured near the same time."""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
import kt_stats
from kt_shape_metrics import _combined_metrics
from kt_landmark_analysis import load_plates, nearest_on_polyline, phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/cell_outlines.csv", f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]
SCRIPT = __file__
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}


def plate_symmetry(pts, plate_poly, px):
    """near/far area of the CELL split by the plate line (1.0 = symmetric about the plate)."""
    p = np.asarray(pts, float)
    x0, y0 = np.floor(p.min(0) - 2).astype(int); x1, y1 = np.ceil(p.max(0) + 2).astype(int)
    import cv2
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mask, [np.round(p - [x0, y0]).astype(np.int32)], 1)
    ys, xs = np.where(mask > 0)
    P = np.column_stack([xs + x0, ys + y0]).astype(float)
    C = P.mean(0)
    L, _ = nearest_on_polyline(C, plate_poly)
    u = L - C; nu = np.hypot(*u)
    if nu < 1e-6: return np.nan
    u /= nu
    side = (P - C) @ u
    near = int((side > 0).sum()); far = int((side < 0).sum())
    return (near / far) if far else np.nan


def cell_rows():
    plates = load_plates()
    rows = []
    for r in csv.DictReader(open(f"{ROOT}/annotations/cell_outlines.csv")):
        if not (r.get("points") or "").strip(): continue
        try:
            pts = json.loads(r["points"]); px = float(r.get("pixel_size_um") or 0.062)
            t = float(r.get("t_sec") or "nan")
        except Exception:
            continue
        m = _combined_metrics([np.asarray(pts, float)], px)
        if m is None: continue
        plist = plates.get(r["batch"], [])
        sym = ""
        if plist and np.isfinite(t):
            poly = min(plist, key=lambda z: abs(z[0] - t))[1]
            s = plate_symmetry(pts, poly, px)
            sym = round(s, 3) if np.isfinite(s) else ""
        rows.append(dict(batch=r["batch"], frame=int(float(r.get("frame") or -1)), t_sec=t,
                         cell_area_um2=m["area_um2"], cell_perim_um=m["perimeter_um"],
                         cell_circularity=m["circularity"], cell_plate_symmetry=sym))
    return rows


if __name__ == "__main__":
    CR = cell_rows()
    LM = list(csv.DictReader(open(f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv")))
    def lnum(r, k):
        try: return float(r[k])
        except Exception: return None
    ph = phase_times(sorted({r["batch"] for r in CR}))
    # mitotic-progress for a cell frame: 0=metaphase onset, 1=anaphase onset
    def progress(b, t):
        mt, at = ph.get(b, (None, None))
        if mt is None or at is None or at <= mt: return None
        return (t - mt) / (at - mt)

    def _save(fig, name, cap, header=None, rows=None):
        fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
        # 2026-08-03: was record_plot(["x"], []) - a placeholder registering an EMPTY data table, so
        # the figure could not be checked against its own data and any _zoom companion was built from
        # nothing. Same bug fixed in kt_phase_split.py on 2026-07-29 and never propagated here.
        try:
            lib.record_plot(name, header or ["batch", "value"], rows or [], {"family": "cell"},
                            script=SCRIPT, caption=cap, source=SRC, key_column="batch")
        except Exception as _e:
            print("    record_plot(%s) failed: %s" % (name, _e))
        print("  " + name)

    # 1) cell circularity + area over mitotic progress
    for metric, ylab, name in [("cell_circularity", "cell circularity", "G6cell_circularity_vs_progress"),
                               ("cell_area_um2", "cell area (µm²)", "G6cell_area_vs_progress"),
                               ("cell_plate_symmetry", "cell symmetry about plate (near/far area)", "G6cell_symmetry_vs_progress")]:
        fig, ax = plt.subplots(figsize=(7.0, 5.0)); xs, ys = [], []
        for r in CR:
            v = r[metric] if metric != "cell_plate_symmetry" else (r[metric] if r[metric] != "" else None)
            pr = progress(r["batch"], r["t_sec"])
            try: v = float(v)
            except Exception: v = None
            if v is None or pr is None or not (-0.5 <= pr <= 1.5): continue
            xs.append(pr); ys.append(v)
        ax.scatter(xs, ys, s=14, color="#555", alpha=0.5, edgecolor="white", lw=0.2)
        xs, ys = np.array(xs), np.array(ys)
        if len(xs) > 8:
            bins = np.linspace(-0.2, 1.3, 8); idx = np.digitize(xs, bins); bx, bm = [], []
            for bi in range(1, len(bins)):
                sel = ys[idx == bi]
                if len(sel) >= 3: bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
            ax.plot(bx, bm, "-o", color="#c0392b", lw=2, ms=4)
            rho, p = st.spearmanr(xs, ys); kt_stats.add_corr_stats(ax, xs, ys, loc="lower left")
            ax.set_title(f"{ylab} vs mitotic progress   (ρ={rho:.2f}, p={p:.2g}, N={len(xs)})", loc="left", fontweight="bold", fontsize=10)
        ax.axvline(0, ls=":", color="#3b6fb6"); ax.axvline(1, ls="--", color="#d1495b")
        ax.set_xlabel("mitotic progress (0=metaphase onset, 1=anaphase onset)"); ax.set_ylabel(ylab)
        _save(fig, name, ylab + " vs mitotic progress",
              header=["mitotic_progress", metric], rows=[[round(float(x),5), round(float(y),5)] for x, y in zip(xs, ys)])

    # 2) KT metric vs cell metric (nearest-in-time, per polar KT frame)
    cell_by_batch = collections.defaultdict(list)
    for r in CR: cell_by_batch[r["batch"]].append(r)
    for ktm, cellm, xlab, ylab, name in [
        ("aspect_ratio", "cell_circularity", "cell circularity", "polar KT stretch (aspect)", "G6cell_ktstretch_vs_cellcirc"),
        ("dist_to_plate_um", "cell_area_um2", "cell area (µm²)", "polar KT distance to plate (µm)", "G6cell_ktdist_vs_cellarea")]:
        xs, ys = [], []
        for r in LM:
            if r["label"] != "polar": continue
            v = lnum(r, ktm); t = lnum(r, "t_sec")
            if v is None or t is None: continue
            cells = cell_by_batch.get(r["batch"], [])
            if not cells: continue
            c = min(cells, key=lambda cc: abs(cc["t_sec"] - t))
            if abs(c["t_sec"] - t) > 120: continue
            cv = c[cellm]
            try: cv = float(cv)
            except Exception: continue
            xs.append(cv); ys.append(v)
        fig, ax = plt.subplots(figsize=(6.4, 5.0))
        ax.scatter(xs, ys, s=10, color=COL["polar"], alpha=0.4, edgecolor="white", lw=0.2)
        if len(xs) > 8:
            rho, p = st.spearmanr(xs, ys); kt_stats.add_corr_stats(ax, xs, ys, loc="upper right")
            ax.set_title(f"{ylab} vs {xlab}   (ρ={rho:.2f}, p={p:.2g}, N={len(xs)})", loc="left", fontweight="bold", fontsize=9.5)
        ax.set_xlabel(xlab); ax.set_ylabel(ylab)
        _save(fig, name, f"{ylab} vs {xlab}",
              header=[cellm, metric], rows=[[round(float(x),5), round(float(y),5)] for x, y in zip(xs, ys)])
    print("done cell-outline")
