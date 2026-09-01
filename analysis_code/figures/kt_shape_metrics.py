#!/usr/bin/env python3
"""Compute kinetochore SHAPE metrics from the freehand outline traces in annotations/kt_outlines.csv.

RULE (data map §0): geometry is COMPUTED from the point/line annotation files, NEVER read from the
sparse master/annotation shape columns (they are empty here anyway). Each row of kt_outlines.csv is one
hand-traced kinetochore outline (a dense polygon in FLUOR px, pixel_size_um per row) on one frame,
labelled polar / plate / paired / lagging.

For each trace we compute, in physical units:
  area_um2        polygon area (shoelace) * px^2
  perimeter_um    closed-polygon perimeter * px
  circularity     4*pi*area / perimeter^2            (1 = perfect circle; low = irregular/elongated)
  solidity        area / convex-hull area            (1 = convex; low = concave/ragged)
  major_um        MAX caliper (Feret) size (um)      = the STRETCH length, MEASURED not fitted
  minor_um        MIN caliper width (um)             = the narrowest width over all rotations
  aspect_ratio    major/minor                        (1 = round; high = stretched)
  elongation      1 - minor/major                    (0 = round; ->1 = a line)
  roundness       4*area / (pi*major^2)              (area-based roundness, 1 = circle)
  eq_diam_um      equivalent-circle diameter from area

Provides load_shapes() -> list of dicts; run directly to (re)build the derived CSV + print a sanity table.
"""
import csv, json, os
import numpy as np
import cv2

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)
SRC = f"{ROOT}/annotations/kt_outlines.csv"
OUT = f"{ROOT}/ablation_plots/data/kt_shape_metrics.csv"

# her batch STRETCH-CLASS categorisation (handoff-5 user notes 2026-07-23)
STRETCH_VISIBLE = {
    "20250409 ptk_yfpcdc20_6", "20250806 single_ablation_3", "20260416 single ablation_15",
    "20251006 triple_ablation_8", "20250411 ptk_yfpcdc20_11",
}
LAGGING_NO_STRETCH = {
    "20250402 ptk_yfpcdc20_7", "20250403 ptk_yfpcdc20_22", "20250404 ptk_yfpcdc20_16",
    "20260303 Mad1_Ptk_Eyfpmad1_ablation_10", "20260420 ptk2 eyfp cdc20 1 ablation_22",
    "20260417 ptk2 eyfp cdc20 ablation_16", "20250401 ptk_yfpcdc20_28",
}
NO_LAGGING = {
    "20250402 ptk_yfpcdc20_13", "20250402 ptk_yfpcdc20_2", "20250417 ptk_yfpcdc20_3",
    "20250423 ptk_yfpcdc20_26", "20250423 ptk_yfpcdc20_3", "20260416 single ablation_16",
    "20260420 ptk2 eyfp cdc20 1 ablation_13", "20260420 ptk2 eyfp cdc20 1 ablation_18",
    "20260420 ptk2 eyfp cdc20 1 ablation_20", "20260420 ptk2 eyfp cdc20 1 ablation_26",
}
def stretch_class(b):
    if b in STRETCH_VISIBLE: return "stretch visible"
    if b in LAGGING_NO_STRETCH: return "lagging, no stretch"
    if b in NO_LAGGING: return "no lagging"
    return "unclassified"


def _raster(polys, pad=2):
    """Rasterise one or more traced polygons into a SINGLE boolean mask, at 1 px per pixel unit.

    Every area-derived shape metric is measured from this mask so they share one definition of the
    object: the enclosed region PLUS the pixels the traced line covers (PIL's polygon fill paints the
    boundary). Multiple polygons are drawn into the same mask, so fragments of one fractured
    kinetochore that overlap are counted once, not twice.
    Returns None if the bounding box is degenerate or implausibly large.
    """
    from PIL import Image, ImageDraw
    P = np.vstack([np.asarray(q, float) for q in polys])
    x0, y0 = float(P[:, 0].min()), float(P[:, 1].min())
    w = int(np.ceil(P[:, 0].max() - x0)) + 2 * pad
    h = int(np.ceil(P[:, 1].max() - y0)) + 2 * pad
    if w < 3 or h < 3 or w > 20000 or h > 20000:
        return None
    im = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(im)
    for q in polys:
        Q = np.asarray(q, float)
        if Q.ndim != 2 or len(Q) < 1:
            continue
        xy = [(float(a - x0) + pad, float(b - y0) + pad) for a, b in Q]
        # A piece with fewer than 3 points is still a piece SHE MARKED, so its pixels belong in the mask —
        # skipping it would drop part of the kinetochore from every area-derived measurement. Draw it as the
        # line/point it is (2026-08-03; `polygon()` requires >=3 points and used to silently skip these).
        if len(xy) >= 3:
            dr.polygon(xy, fill=1)
        elif len(xy) == 2:
            dr.line(xy, fill=1, width=1)
        else:
            dr.point(xy, fill=1)
    return np.asarray(im).astype(bool)


def _mask_area_px(poly):
    """Area of a traced outline in PIXELS, INCLUDING the pixels the traced line itself covers.

    USER RULE (2026-07-29, applies to EVERY measurement made from a manual kinetochore outline):
    "the whole encircled area of the outline should include the outline line itself, too, as well as
    that within." A shoelace integral treats the boundary as a zero-width mathematical curve and so
    counts only the interior; rasterising the polygon the way the intensity code already does
    (PIL polygon fill, which paints the boundary pixels) counts the line as part of the object.
    Measured over 1200 real outlines the mask area is a median +25.7% (mean +30.8%, p90 +47.1%)
    larger than the shoelace area - so this is not a rounding detail.

    This makes the shape family agree with polar_fluor_matched.area_um2, which was already
    mask-based; before this change the codebase carried two different definitions of "area".
    Falls back to shoelace only if rasterising fails."""
    from PIL import Image, ImageDraw
    P = np.asarray(poly, float)
    x0, y0 = float(P[:, 0].min()), float(P[:, 1].min())
    w = int(np.ceil(P[:, 0].max() - x0)) + 3
    h = int(np.ceil(P[:, 1].max() - y0)) + 3
    if w < 2 or h < 2 or w > 20000 or h > 20000:
        q = P if np.allclose(P[0], P[-1]) else np.vstack([P, P[0]])
        x, y = q[:, 0], q[:, 1]
        return 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(float(a - x0) + 1.0, float(b - y0) + 1.0) for a, b in P], fill=1)
    return float(np.asarray(m).sum())


def _calipers(pts):
    """MAXIMUM and MINIMUM caliper (Feret) size of a point set — measured, not fitted.

    USER RULE (2026-08-03): "not an appropriate way to make measurements. this loses accuracy. especially if
    a lagging chromosome is in many pieces." Stretch used to be major/minor of a `cv2.fitEllipse`. An ellipse
    is a 5-parameter MODEL: it assumes one smooth convex blob, and a kinetochore — above all a lagging one,
    which is irregular and often fractured into several pieces — is not that. Fitted to a point cloud made of
    separated fragments the conic is poorly conditioned, and the axes it returns describe a shape that is not
    there. These calipers make no assumption: they read the object's real extent off its convex hull.

      max caliper = the largest distance between any two boundary points (the true end-to-end extent)
      min caliper = the smallest width the object has over ALL rotations (rotating calipers on the hull)

    Returns (max_px, min_px, angle_deg of the max-caliper axis, hull_area_px, hull_points).
    """
    h = cv2.convexHull(np.asarray(pts, np.float32)).reshape(-1, 2).astype(float)
    if len(h) < 2:
        return np.nan, np.nan, np.nan, 0.0, h
    d = np.linalg.norm(h[:, None, :] - h[None, :, :], axis=-1)
    i, j = np.unravel_index(int(np.argmax(d)), d.shape)
    dmax = float(d[i, j])
    v = h[j] - h[i]
    ang = float(np.degrees(np.arctan2(v[1], v[0]))) % 180.0
    # rotating calipers: the minimum width is attained on a hull EDGE normal
    wmin = np.inf
    for k in range(len(h)):
        e = h[(k + 1) % len(h)] - h[k]
        n = float(np.hypot(*e))
        if n < 1e-9:
            continue
        nrm = np.array([-e[1], e[0]]) / n
        proj = (h - h[k]) @ nrm
        wmin = min(wmin, float(proj.max() - proj.min()))
    if not np.isfinite(wmin):
        wmin = np.nan
    hull_area = float(cv2.contourArea(h.astype(np.float32))) if len(h) >= 3 else 0.0
    return dmax, wmin, ang, hull_area, h


def _combined_metrics(pieces, px):
    """pieces = list of Nx2 polygons (px) that TOGETHER form ONE kinetochore. For paired/plate this list
    has a single polygon (each circle IS its own KT); for polar/lagging it can hold several pieces of the
    same kinetochore on one frame (user 2026-07-23: multiple polar/lagging circles = pieces of one KT).

    area/perimeter = SUM over the pieces (the real signal). Stretch (major/minor/aspect/elongation) and the
    convex hull are fit over ALL the combined points, so a KT traced in fragments is measured as one spread-
    out object — which is exactly what makes a stretched/lagging KT read as elongated. Returns None if no
    piece is a valid polygon."""
    # EVERY MARKED PIECE COUNTS (her rule, restated 2026-08-03): when one kinetochore is traced in several
    # pieces on one frame, every measurement — length above all — must be taken over the pieces TOGETHER, as
    # the full span of the whole set, never piece by piece and never on a subset.
    #
    # This used to `continue` past any piece with fewer than 5 points, which silently removed it from the
    # combined span AND from the mask. It bit 2 multi-piece LAGGING groups (`20250929 four_ablation_23`
    # f148 grp1, a 4-point mark; `20250904 triple_ablation_8` f143 grp1, a 3-point mark) — both degenerate
    # taps, but a genuine small fragment marked with 4 points would have vanished the same silent way.
    # A piece is now dropped ONLY if it carries no usable coordinate at all, and `n_dropped_pieces` records
    # it so the loss can never be invisible.
    allpts, n_dropped = [], 0
    for p in pieces:
        p = np.asarray(p, float)
        if p.ndim != 2 or p.shape[0] < 1 or not np.isfinite(p).all():
            n_dropped += 1
            continue
        allpts.append(p)
    if not allpts:
        return None
    allp = np.vstack(allpts)
    # ---- ONE raster for every area-derived quantity -------------------------------------------
    # USER RULE (2026-07-29): a manual outline's measurement covers the enclosed area PLUS the pixels
    # the traced line itself covers. That means area, PERIMETER, hull and therefore circularity and
    # solidity must ALL be read off the same rasterised object. A first attempt took the area from the
    # mask but kept the perimeter from the traced polyline: circularity = 4*pi*A/P^2 then mixed two
    # different definitions of the same object and inflated (paired 0.488 -> 0.622), and solidity
    # compared a SUM of per-piece mask areas against a single hull, saturating at 1.000.
    # All pieces of one kinetochore go into ONE mask, so overlapping fragments are not double-counted.
    m = _raster(allpts)
    if m is None:
        return None
    total_area_px = float(m.sum())
    if total_area_px <= 0:
        return None
    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    total_perim_px = float(sum(cv2.arcLength(c, True) for c in cnts))
    hull_pts = cv2.convexHull(np.vstack(cnts).reshape(-1, 2).astype(np.float32))
    hm = _raster([hull_pts.reshape(-1, 2)])
    hull_area_px = float(hm.sum()) if hm is not None else 0.0
    area = total_area_px * px * px
    perim = total_perim_px * px
    circ = min(4 * np.pi * area / (perim * perim), 1.0) if perim > 0 else np.nan
    solidity = min(total_area_px / hull_area_px, 1.0) if hull_area_px > 0 else np.nan
    # ---- EXTENT: measured with calipers, NOT fitted with an ellipse (user 2026-08-03) ----------
    # `major_um` / `minor_um` keep their names so every downstream figure keeps working, but they are now the
    # max and min CALIPER sizes of the traced object — read off the shape, with no model imposed.
    # cv2.fitEllipse is GONE from this file, not merely unused: it was kept briefly as `ellipse_*` audit
    # columns and she ruled that out too — a retired method does not stay live in the measurement path.
    # The code and the data it produced are in `_retired/` (see that folder's README, 2026-08-03).
    dmax_px, wmin_px, angle_deg, hull_px, _hull = _calipers(allp)
    if not (np.isfinite(dmax_px) and np.isfinite(wmin_px)) or dmax_px <= 0:
        return None
    major, minor = dmax_px * px, wmin_px * px
    if minor <= 0:
        minor = 1e-6
    aspect = major / minor
    elong = 1.0 - minor / major
    roundness = 4 * area / (np.pi * major * major) if major > 0 else np.nan
    eq_diam = 2 * np.sqrt(area / np.pi)
    # convexity: perimeter of the convex hull / actual (combined) perimeter (<=1; low = deep indentations)
    # hull_pts replaces the old `hull` name; it is the hull of the RASTERISED object's contour, so the
    # convexity ratio compares two perimeters measured the same way (2026-07-29).
    hull_perim_px = float(cv2.arcLength(hull_pts.astype(np.float32), True))
    convexity = min(hull_perim_px / total_perim_px, 1.0) if total_perim_px > 0 else np.nan
    # rectangularity (rotated extent): area / min-area-rotated-bounding-box area
    try:
        (_c, _s, _a) = cv2.minAreaRect(allp.astype(np.float32))
        rect_area_px = _s[0] * _s[1]
        rectangularity = min(total_area_px / rect_area_px, 1.0) if rect_area_px > 0 else np.nan
    except Exception:
        rectangularity = np.nan
    # ---- MULTI-PIECE HONESTY (user 2026-08-03) -------------------------------------------------
    # A caliper span across a kinetochore in several pieces measures the ENVELOPE of the fragments, which is
    # the right number for "how far has this thing been pulled apart" but NOT for "how deformed is one blob".
    # Emit both so the two can never be confused: `gap_fraction` is how much of the measured envelope is empty
    # space between fragments. `gap_fraction` is a property of the COMBINED object, so it is safe; a
    # per-PIECE size column was tried here (`piece_max_feret_um`) and REMOVED on 2026-08-03 — pieces of one
    # kinetochore are measured together, never piece by piece, so a standing "largest single fragment"
    # column is an invitation to break that rule, and nothing consumed it.
    # NB the envelope area comes from `hull_area_px` — the RASTERISED hull already used for solidity — and
    # NOT from `_calipers`' polygon hull area. Mixing a raster area (which includes the traced line pixels)
    # with a polygon area produced negative gaps on compact objects; §1 rule 21, one raster for all of it.
    envelope_area = hull_area_px * px * px
    gap_fraction = (1.0 - total_area_px / hull_area_px) if hull_area_px > 0 else np.nan
    return dict(area_um2=area, perimeter_um=perim, circularity=circ,
                solidity=solidity if np.isfinite(solidity) else np.nan,
                convexity=convexity if np.isfinite(convexity) else np.nan,
                rectangularity=rectangularity if np.isfinite(rectangularity) else np.nan,
                major_um=major, minor_um=minor, aspect_ratio=aspect, elongation=elong,
                angle_deg=angle_deg,
                envelope_area_um2=envelope_area,
                gap_fraction=gap_fraction if np.isfinite(gap_fraction) else np.nan,
                n_dropped_pieces=n_dropped,
                roundness=min(roundness, 1.0) if np.isfinite(roundness) else np.nan,
                eq_diam_um=eq_diam, n_pieces=len(allpts))


# A real PtK kinetochore blob is ~0.3-3 um across; a whole cell is ~15 um. A trace whose fitted major
# axis exceeds this is a degenerate freehand stroke (didn't close / crossed the cell), not a kinetochore.
MAX_MAJOR_UM = 5.0
MAX_MAJOR_MULTI_UM = 20.0   # a combined multi-piece KT may span farther, but not beyond the cell (~20um)
# Each paired/plate circle IS its own kinetochore -> one record per trace. polar & lagging circles on one
# frame are PIECES of one kinetochore -> combined into one record per (batch,label,frame,GRP).
# `paired`/`plate` traces that carry NO grp are one kinetochore per trace — that was the whole convention
# before the "+ New KT" button existed. A grp-TAGGED trace is governed by the grp rule like every other
# label (§1 rule 28): traces sharing a grp are ONE kinetochore, and several of them on one frame are its
# pieces. Keying paired per-trace regardless of grp SPLIT 154 kinetochores into 316 objects and is what put
# up to 3 rows of one frame into a single track (133 duplicate (track_id,frame) keys, 100% single-grp).
SEPARATE_LABELS = {"paired", "plate"}

# a combined group whose pieces sit further apart than this is not one kinetochore — reported, never
# silently merged into a giant object and never silently dropped by the plausibility cap
IMPLAUSIBLE_GROUP_SPREAD_UM = 10.0


def grp_of(row):
    """The kinetochore GROUP the annotation tool stamped into `notes` as "grp:N;trace:M".

    (Until 2026-08-07 `notes` also carried a `kttype:X` copy of the type. It was redundant with the `label`
    column, drifted out of sync on 19 rows, and nothing outside the annotation page ever parsed it — it has
    been removed from the store and the tool. TYPE now lives ONLY in `label`.)

    `grp` is her "+ New KT" identity (make_annotation_html.py `kt-newgroup`): traces sharing a grp are
    ONE kinetochore — several on one frame are pieces of a fractured/odd-shaped KT — and a DIFFERENT grp
    on the same frame is a DIFFERENT kinetochore. Returns None when the row carries no grp tag.
    """
    import re as _re
    m = _re.search(r"grp:([^;]*)", row.get("notes", "") or "")
    return m.group(1) if (m and m.group(1)) else None

def group_key(row):
    """THE one definition of "which traces form one kinetochore" — used by load_shapes AND kt_tracks.

    Both modules used to carry their own copy of this rule, and on 2026-08-03 fixing only one of them left
    `kt_tracks` still splitting grp-tagged paired traces, so 136 (track_id,frame) duplicates survived a fix
    that had "worked". One function, two callers, no drift.

    untagged paired/plate -> one kinetochore per TRACE (the pre-"+ New KT" convention)
    everything else       -> (batch, label, frame, grp): traces sharing a grp are ONE kinetochore
    """
    g = grp_of(row)
    if row["label"] in SEPARATE_LABELS and g is None:
        return ("trace", row.get("id"))
    return (row["batch"], row["label"], row.get("frame"), g)


def load_shapes(verbose=False):
    import collections as _c
    recs = []
    import lib as _lib
    for r in csv.DictReader(open(SRC)):
        if r.get("channel") != "fluor":      # 3 stray phase traces -> drop (keep one measurement basis)
            continue
        if _lib.kt_outline_excluded(r.get("batch")):   # user 2026-07-23 global kt-outline exclusion
            continue
        # USER 2026-08-06: prophase ablations are excluded from every plot that has no prophase group.
        # This is the SHARED loader for the whole kt-shape family (kt_shape_plots, custom_lagging_dynamics
        # and everything importing them), so one filter here covers all of them — they read kt_outlines.csv
        # directly and never derive their row set from the master, so no master-level gate reaches them.
        if _lib.is_prophase_ablation(r.get("batch", "")):
            continue
        if _lib.focus_excluded(r.get("id")):   # user 2026-07-27: out-of-focus polar frames
            continue
        try:
            pts = json.loads(r["points"])
        except Exception:
            continue
        recs.append((r, pts))
    # group: paired/plate keyed per-trace (each is its own KT); polar/lagging keyed per
    # (batch,label,frame,GRP).
    #
    # USER RULE (2026-08-03): the old key omitted grp, so EVERY polar (or lagging) trace on a frame was
    # merged into one kinetochore. That is right for a single-ablation cell, which has at most one of
    # each, but a DOUBLE or TRIPLE ablation cell can carry several polar and several lagging KTs at the
    # same time — and when she separates them with "+ New KT" the resulting traces ARE different
    # kinetochores and must be measured apart. Adding grp to the key makes her manual grouping
    # authoritative here, exactly as it already is in kt_tracks.build_objects.
    #
    # Rows with NO grp tag keep the old frame-level behaviour (grp is None, so they share one key):
    # those are the single-ablation cells traced before the group buttons existed, where all the
    # polygons on a frame really are pieces of one kinetochore.
    groups = _c.OrderedDict()
    for r, pts in recs:
        groups.setdefault(group_key(r), []).append((r, pts))
    out, dropped, implausible, capped = [], 0, [], []
    for key, members in groups.items():
        r0 = members[0][0]
        px = float(r0.get("pixel_size_um") or 0.062)
        pieces = [pts for (_, pts) in members]
        m = _combined_metrics(pieces, px)
        if m is None:
            continue
        # plausibility: a SINGLE-piece trace can't exceed a compact KT (~5um) -> artifact. A COMBINED
        # multi-piece polar/lagging KT is expected to span farther (that IS the stretch), but still cannot
        # exceed the cell (~20um) -> beyond that a stray piece is in the group.
        # A group whose pieces sit implausibly far apart is not one kinetochore. Previously the 20um
        # plausibility cap would just DELETE such a record; report it instead, so a mis-grouped annotation
        # surfaces for her to fix rather than vanishing from the data (2026-08-03).
        if m["n_pieces"] > 1 and isinstance(key, tuple) and len(key) == 4:
            allp = np.vstack([np.asarray(p, float) for (_, p) in members])
            spread = float(np.hypot(*(allp.max(0) - allp.min(0)))) * px
            if spread > IMPLAUSIBLE_GROUP_SPREAD_UM:
                implausible.append((key, round(spread, 2), m["n_pieces"],
                                    [mm.get("id") for (mm, _) in members]))
        cap = MAX_MAJOR_UM if m["n_pieces"] == 1 else MAX_MAJOR_MULTI_UM
        if m["major_um"] > cap:
            dropped += 1
            capped.append((key, round(m["major_um"], 2), [mm.get("id") for (mm, _) in members]))
            continue
        try:
            t_sec = float(r0.get("t_sec") or "nan")
        except Exception:
            t_sec = float("nan")
        try:
            frame = int(float(r0.get("frame") or -1))
        except Exception:
            frame = -1
        row = dict(id=r0.get("id"), batch=r0["batch"], label=r0["label"], frame=frame, t_sec=t_sec,
                   grp=(grp_of(r0) or ""),
                   n_pts=sum(len(p) for p in pieces), n_pieces=m["n_pieces"],
                   stretch_class=stretch_class(r0["batch"]))
        row.update({k: round(v, 4) if v is not None and np.isfinite(v) else "" for k, v in m.items()
                    if k != "n_pieces"})
        out.append(row)
    if implausible:
        print(f"  [!] {len(implausible)} grp GROUPS span more than {IMPLAUSIBLE_GROUP_SPREAD_UM} um — these "
              f"are unlikely to be one kinetochore; check the grouping:")
        for k, sp, n, ids in sorted(implausible, key=lambda x: -x[1])[:10]:
            print(f"      {sp:7.2f} um  {k[0][:34]:34s} {k[1]:8s} f{str(k[2]):>4s} grp{k[3]}  "
                  f"{n} pieces, ids={ids}")
    if capped:
        print(f"  [!] {len(capped)} records DROPPED by the plausibility cap (not silent):")
        for k, mj, ids in capped[:10]:
            print(f"      major {mj} um  {k}  ids={ids}")
    if verbose:
        print(f"  dropped {dropped} implausible kinetochores (major axis > {MAX_MAJOR_UM} um)")
    return out


if __name__ == "__main__":
    rows = load_shapes()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = ["id", "batch", "label", "grp", "stretch_class", "frame", "t_sec", "n_pts", "n_pieces",
            "area_um2", "perimeter_um", "circularity", "solidity", "convexity", "rectangularity",
            "major_um", "minor_um", "aspect_ratio", "elongation", "roundness", "angle_deg", "eq_diam_um",
            # multi-piece honesty + the retired ellipse fit, kept for audit (2026-08-03)
            "envelope_area_um2", "gap_fraction", "n_dropped_pieces"]
    # include any extra metric keys the metrics dict emits so the writer never drops a field
    seen = set(); cols = []
    for c in base + [k for r in rows for k in r]:
        if c not in seen:
            seen.add(c); cols.append(c)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} shape rows -> {OUT}\n")
    import collections, statistics
    print("=== median shape metric by label ===")
    by = collections.defaultdict(list)
    for r in rows:
        by[r["label"]].append(r)
    hdr = ["area_um2", "aspect_ratio", "elongation", "major_um", "circularity", "solidity"]
    print(f"{'label':10s} {'n':>4s} " + " ".join(f"{h:>12s}" for h in hdr))
    for lab in ("plate", "paired", "polar", "lagging"):
        rs = by.get(lab, [])
        if not rs: continue
        med = [statistics.median([r[h] for r in rs if r[h] != ""]) for h in hdr]
        print(f"{lab:10s} {len(rs):>4d} " + " ".join(f"{m:12.3f}" for m in med))
