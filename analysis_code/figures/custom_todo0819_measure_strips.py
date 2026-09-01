#!/usr/bin/env python3
"""The artboard-4 measurement timestrips: one strip per measurement, on ONE cell, on the SAME five frames.

USER 2026-08-19 (to-do list 0819 1pm), figure item 12 — verbatim:
    "In addition to the timestrip showing cell outlines, also make 3 more timestrips of 5 panels (of this
     same cell and using the same frames if possible as the preexisting timestrip showing cell outlines, for
     ease of the viewer) marked with the annotations for the other two measurements (plate rotation, centroid
     movement). Also, instead of including the fluorescent channels with the phase channels that have the
     annotation markups, just make of the phase, and then include a single strip of the fluor that's
     unannotated. These timestrips should not be put together in a block."

SO FOUR STRIPS, each written as its own figure so she can move them independently:
    <base>_outline    phase, cell outline drawn, per-frame roundness
    <base>_rotation   phase, metaphase-plate line drawn, cumulative plate rotation
    <base>_centroid   phase, cell centroid + the path it has travelled, cumulative centroid movement
    <base>_fluor      fluorescence, NO annotation at all
The three annotated strips are PHASE ONLY, per the same instruction.

WHICH CELL, and why not the one already on the board
    The existing `traced_cell` strip is `20251029 triple_ablation_26`. That cell has 15 cell outlines and
    ZERO metaphase-plate marks, so a plate-rotation strip cannot be drawn for it -- the measurement does not
    exist there. Her instruction says "if possible", so the four strips are built on the cell that actually
    supports all three measurements: `20250901 triple_ablation_11` (8 outlines, 81 plate marks over a 27-min
    span), a triple-ablation cdc20 cell, which is the cohort the artboard-4 shape story is about.
    `traced_cell` is left exactly as it is; nothing is replaced.

The measurements are computed the SAME way the line plots compute them, so the numbers on the strip and the
numbers on the plot are the same quantity:
    roundness  4*pi*A/P^2 from the traced polygon (group1_roundness.poly_roundness)
    rotation   cumulative |step| of the plate's principal-axis angle, each step wrapped into (-90, 90]
               -- ABSOLUTE values, her item 3
    centroid   cumulative path length of the outline centroid in um, not straight-line displacement
"""
import csv
import json
import os
import sys

import numpy as np
import cv2

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import ts_render

lib.apply_style()

ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/group1/timestrips2"
SCRIPT = __file__
BATCH = os.environ.get("MEAS_BATCH", "20250901 triple_ablation_11")
NPANEL = 5
# One BASE per cell: item 3.3 asks for this same set on three more cells, and a fixed base would have
# each run silently overwrite the last.
BASE = os.environ.get("MEAS_BASE", "G1_measure")

CYAN = (255, 255, 80)      # BGR -- outline
MAGENTA = (255, 0, 255)    # BGR -- plate line (never red: NOTES rule 30)
AMBER = (0, 255, 255)      # BGR -- centroid + its path. USER 2026-08-20 (board 4, item 3): "The orange
                           # one is barely visible." Raised to full-luminance yellow AND drawn with the
                           # scale-aware stroke; on a grey phase frame yellow carries the most contrast of
                           # any hue that is neither red nor green (NOTES rule 30).
CHROMO = (0, 165, 255)     # BGR -- chromosome trace (its own row, so it never sits beside the centroid)
ROW_TITLE = {"outline": "cell outline", "chromo": "chromosome trace", "rotation": "metaphase plate",
             "centroid": "centroid movement", "fluor": "fluorescence (unannotated)"}


def load_rows(path, batch):
    out = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8", errors="replace")):
        if (r.get("batch") or "").strip() != batch:
            continue
        try:
            t = float(r["t_sec"]); pts = np.array(json.loads(r["points"]), float)
        except Exception:
            continue
        if len(pts) >= 2:
            out.append((t, pts))
    out.sort(key=lambda q: q[0])
    return out


def roundness(pts):
    p = np.asarray(pts, float)
    if len(p) < 3: return None
    x, y = p[:, 0], p[:, 1]
    A = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    per = np.sum(np.hypot(np.diff(np.append(x, x[0])), np.diff(np.append(y, y[0]))))
    if per == 0: return None
    r = 4 * np.pi * A / per ** 2
    return r if 0 < r <= 1.2 else None


# the rotation metric is defined once, in trendlib, so the strip and the line plots cannot drift
# apart in how they measure the same quantity
from trendlib import plate_rotation_trace


def plate_angle(pts):
    P = np.asarray(pts, float)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c)
    return float(np.degrees(np.arctan2(vt[0][1], vt[0][0]))) % 180.0, c


def plate_extent(pts):
    """Visible length of one hand-drawn plate mark: its extent ALONG its own principal axis."""
    P = np.asarray(pts, float)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c)
    t = (P - c) @ vt[0]
    return float(t.max() - t.min())


def plate_straight(pts, length):
    """Her plate mark redrawn as a PERFECTLY STRAIGHT segment of a FIXED length.

    USER 2026-08-20 (artboard 4, item 3.1): "the lines I manually annotated are not perfectly straight,
    so just make them perfectly straight and the same length (use the average length of them now)."

    Nothing is invented and no measurement changes: the segment keeps the mark's own centroid and its own
    principal-axis direction -- which is ALREADY the axis `plate_angle` measures the rotation from, so the
    drawn line and the reported angle now agree by construction instead of only approximately. Only the
    kinks (hand tremor) and the frame-to-frame length differences are removed, which is exactly what she
    asked for; a bent mark made the plate look like it wobbled when the fitted axis had not moved.
    """
    P = np.asarray(pts, float)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c)
    d = vt[0] / (np.linalg.norm(vt[0]) or 1.0)
    h = float(length) / 2.0
    return np.array([c - h * d, c + h * d])


def main():
    import group_timestrips as G           # crop + movie helpers, so the crop matches every other strip

    outs = load_rows(f"{ROOT}/annotations/cell_outlines.csv", BATCH)
    plates = load_rows(f"{ROOT}/annotations/meta_plates.csv", BATCH)
    chromos = load_rows(f"{ROOT}/annotations/chromo_lines.csv", BATCH)   # item 3.4: chromosome-trace row
    if len(outs) < 2:
        sys.exit(f"{BATCH}: only {len(outs)} outlines -- cannot build the strips")
    pxs = G.ps(BATCH)

    # PANELS FOLLOW THE OUTLINES. Intersecting the outline and plate time ranges was costing panels on
    # cells where she drew plates over a shorter stretch than outlines: 20250923 triple_ablation_collagen_25
    # has 6 outlines and 26 plate marks but their overlap admitted only TWO panels, and item 3.3 asks for
    # the same five-panel set on each cell so the three can be read side by side. The outline is the row
    # every panel needs (it carries the rounding), so it sets the window; the plate and chromosome rows draw
    # whatever she marked within tolerance of each panel and are dropped entirely if that is too sparse,
    # rather than repeating one distant mark and implying it never moved.
    win = outs
    idx = np.linspace(0, len(win) - 1, min(NPANEL, len(win))).astype(int)
    sel = [win[i] for i in sorted(set(idx))]
    print(f"{BATCH}: {len(outs)} outlines, {len(plates)} plate marks -> {len(sel)} panels "
          f"at t = {[round(t) for t, _ in sel]} s")

    # rotation and centroid movement up to each selected frame, over ALL marks (not just the five shown)
    #
    # 🔴 2026-08-20, her board-4 item 3.2: the printed rotation was a CUMULATIVE ABSOLUTE SUM and read
    # ~140 deg between panels on a plate she can see rotating a few degrees per frame. Measured on this very
    # cell (20250901 triple_ablation_11, 142 plate marks): median step 2.0 deg, NET rotation 7.9 deg,
    # cumulative 404 deg -- 51x. Summing |steps| rectifies annotation jitter, so the number grows with the
    # NUMBER OF MARKS rather than with the rotation. Now reported as NET |angle(t) - angle(t0)| on a
    # 3-point-smoothed unwrapped angle: still never negative (the point of her earlier instruction), but it
    # tracks what is visible in the strip.
    _marks = []
    for t, pts in plates:
        a, _ = plate_angle(pts)
        _marks.append((t, a))
    _marks.sort()
    rot_at = {t: v for t, v in plate_rotation_trace(_marks)}
    # item 3.1: ONE length for every frame -- the mean visible length of her own marks on this cell.
    _ext = [plate_extent(_p) for _, _p in plates if len(np.asarray(_p, float)) >= 2]
    PLATE_L = float(np.mean(_ext)) if _ext else None
    if _ext:
        print(f"   plate marks: {len(_ext)}  mean length {PLATE_L:.1f} px "
              f"(range {min(_ext):.0f}-{max(_ext):.0f}) -> all drawn straight at the mean")
    cen_at, prev_c, cumc = {}, None, 0.0
    for t, pts in outs:
        c = np.asarray(pts, float).mean(0)
        if prev_c is not None:
            cumc += float(np.hypot(*(c - prev_c))) * pxs
        prev_c = c
        cen_at[t] = (cumc, c)

    def near(d, t):
        if not d: return None
        k = min(d, key=lambda q: abs(q - t))
        return d[k]

    PLATE_TOL_S = 150.0

    def near_plate(t):
        if not plates: return None
        tt, pts = min(plates, key=lambda q: abs(q[0] - t))
        return pts if abs(tt - t) <= PLATE_TOL_S else None

    # A chromosome-trace row is only honest if she actually marked chromosomes NEAR each panel. On
    # 20250901 triple_ablation_11 there are 3 marks in the whole movie, all far from the five panels, so an
    # unguarded row drew the SAME mark five times -- a chromosome that appears never to move. The row is
    # therefore emitted only where a mark exists within CHROMO_TOL_S of the panel, on >= 3 panels.
    CHROMO_TOL_S = 150.0

    def near_chromo(t):
        """EVERY chromosome line within CHROMO_TOL_S of t, else [] (a cell has several at once)."""
        if not chromos: return []
        tb = min({q[0] for q in chromos}, key=lambda q: abs(q - t))
        if abs(tb - t) > CHROMO_TOL_S: return []
        return [pts for tt, pts in chromos if tt == tb]

    sq = G.square_crop(BATCH)
    capP = G.movie(BATCH, "Phase", "Monitoring")
    capF = G.movie(BATCH, "Fluor", "Monitoring")
    if not capP:
        sys.exit(f"{BATCH}: no phase monitoring movie")

    def shift(pts):
        return pts - np.array([sq[0], sq[1]]) if sq else pts

    strips = {"chromo": [], "outline": [], "rotation": [], "centroid": [], "fluor": []}
    cen_path = []
    for t, pts in sel:
        frP = G.grab(*capP, t)
        frF = G.grab(*capF, t) if capF else None
        if frP is None:
            print(f"   t={t:.0f}s: no phase frame -- column dropped"); continue
        base = ts_render.crop_pad(frP, sq).copy() if sq else frP.copy()

        # 0. CHROMOSOME TRACE (item 3.4)
        if chromos:
            z = base.copy()
            _cl = near_chromo(t)
            for _p in _cl:
                cv2.polylines(z, [shift(np.asarray(_p, float)).astype(np.int32)], False,
                              CHROMO, ts_render.stroke_px(z))
            strips["chromo"].append({"t": t, "phase": z,
                                     "caption": (f"{len(_cl)} chromosome{'s' if len(_cl) != 1 else ''}"
                                                 if _cl else "0 chromosomes")})

        # 1. OUTLINE
        a = base.copy()
        cv2.polylines(a, [shift(pts).astype(np.int32)], True, CYAN, ts_render.stroke_px(a))
        rd = roundness(pts)
        strips["outline"].append({"t": t, "phase": a, "value": rd,
                                  "caption": f"R {rd:.2f}" if rd is not None else "R n/a"})

        # 2. PLATE ROTATION
        b = base.copy()
        pl = near_plate(t)
        if pl is not None:
            _seg = plate_straight(pl, PLATE_L) if PLATE_L else np.asarray(pl, float)
            cv2.polylines(b, [shift(_seg).astype(np.int32)], False, MAGENTA, ts_render.stroke_px(b))
        rv = near(rot_at, t)
        strips["rotation"].append({"t": t, "phase": b, "value": rv,
                                   "caption": (f"{rv:.0f}\u00b0" if rv is not None else "no plate")})

        # 3. CENTROID MOVEMENT
        c = base.copy()
        cv = near(cen_at, t)
        if cv is not None:
            cum_um, cc = cv
            cen_path.append(shift(np.array([cc]))[0])
            if len(cen_path) > 1:
                cv2.polylines(c, [np.array(cen_path).astype(np.int32)], False, AMBER, ts_render.stroke_px(c))
            p0 = tuple(np.round(cen_path[-1]).astype(int))
            cv2.circle(c, p0, max(5, int(0.016 * c.shape[1])), AMBER, -1, cv2.LINE_AA)
            cap = f"{cum_um:.1f} \u00b5m"
        else:
            cap = "no outline"
        strips["centroid"].append({"t": t, "phase": c, "caption": cap,
                                   "value": (cv[0] if cv is not None else None)})

        # 4. FLUOR, UNANNOTATED
        if frF is not None:
            f4 = ts_render.crop_pad(frF, sq).copy() if sq else frF.copy()
            strips["fluor"].append({"t": t, "fluor": f4})

    capP[0].release()
    if capF: capF[0].release()

    _cn = sum(1 for q in strips["chromo"] if q.get("caption", "").split()[0].isdigit()
              and int(q["caption"].split()[0]) > 0)
    if strips["chromo"] and _cn < 3:
        print(f"   chromo: only {_cn}/{len(strips['chromo'])} panels have a chromosome mark within "
              f"{CHROMO_TOL_S:.0f}s -- row DROPPED rather than repeat one distant mark")
        strips["chromo"] = []
    _rn = sum(1 for q in strips["rotation"] if q.get("value") is not None)
    if strips["rotation"] and _rn < 3:
        print(f"   rotation: only {_rn}/{len(strips['rotation'])} panels have a plate mark within "
              f"{PLATE_TOL_S:.0f}s -- row DROPPED")
        strips["rotation"] = []

    made = []
    for key, panels in strips.items():
        if not panels:
            print(f"   {key}: no panels"); continue
        ref = panels[0].get("phase", panels[0].get("fluor"))
        res = ts_render.assemble(panels, pxs, ts_render.nice_scalebar_um(ref.shape[1] * pxs),
                                 fluor_only=(key == "fluor"))
        if not res:
            print(f"   {key}: assemble() returned nothing"); continue
        raster, geom = res
        name = f"{BASE}_{key}"
        ts_render.emit([(key, raster, geom)], f"{OUT}/{name}",
                       title=f"{ROW_TITLE.get(key, key)} — {BATCH}")
        made.append(name)
        print(f"   wrote {name} ({len(panels)} panels)")

    lib.record_plot(f"{BASE}_strips",
                    ["strip", "t_sec", "roundness", "cum_rotation_deg", "cum_centroid_um"],
                    # 🔴 RECORD WHAT THE PANEL ACTUALLY SHOWS (2026-08-20). This wrote three literal empty
                    # strings, so the data CSV could not be used to check the figure against its own numbers
                    # -- and the rotation values it should have carried were exactly the ones she caught as
                    # wrong. The value drawn on each panel is now carried on the panel dict and written here.
                    [[k, round(p["t"], 1),
                      (f'{p["value"]:.4f}' if k == "outline" and p.get("value") is not None else ""),
                      (f'{p["value"]:.2f}' if k == "rotation" and p.get("value") is not None else ""),
                      (f'{p["value"]:.3f}' if k == "centroid" and p.get("value") is not None else "")]
                     for k, ps_ in strips.items() for p in ps_],
                    {"type": "measurement timestrips, one per measurement",
                     "batch": BATCH, "panels": NPANEL,
                     "why": "user 2026-08-19 figure item 12 -- the other two measurements get their own "
                            "5-panel strips on the same cell and frames, phase only, plus one unannotated "
                            "fluorescence strip; not assembled into a block",
                     "note": "built on 20250901 triple_ablation_11 rather than the traced_cell cell "
                             "(20251029 triple_ablation_26), which has no metaphase-plate marks at all"},
                    SCRIPT, "Per-measurement timestrips for the artboard-4 shape/rotation/centroid plots")
    print(f"{len(made)} strips written: {made}")


if __name__ == "__main__":
    main()
