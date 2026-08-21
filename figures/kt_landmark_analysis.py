#!/usr/bin/env python3
"""Landmark-anchored (metaphase-plate) shape + motion descriptors per TRACKED kinetochore, per frame.

Landmark = the metaphase plate (meta_plates.csv line, nearest in time). For each tracked KT object we build a
plate-anchored frame: PARALLEL axis u = centroid->nearest-plate-point (the line of stretch toward the plate),
PERPENDICULAR axis v ⟂ u. Then, from the rasterised outline interior, we compute:

  dist_to_plate_um       |centroid - nearest plate point|                (reach / timing of the stretch)
  near_far_area_ratio    area of the half TOWARD the plate / half AWAY   (<1 = 'vase': mass kept away)
  reflection_asym_perp   1 - overlap(shape, shape mirrored over u)       (crookedness ⟂ to the stretch)
  anisotropy_par_perp    parallel extent / perpendicular extent          (>1 radial/toward-plate stretch)
  R_toward_um            leading-edge reach toward the plate from centroid
  R_away_um              trailing reach away from the plate
  stretch_radial_deg     angle(major axis, u) folded to [0,90]           (0 = radial toward/away; 90 = along plate)
  + all standard shape metrics (area/circ/solidity/convexity/aspect/elongation/major/minor/n_pieces)
  + phase (prometaphase/metaphase/anaphase), speed_um_s, radial_speed_um_s (toward+/away-), chromo_len_um.

Phase clock: master Metaphase/Anaphase are ELAPSED-from-frame-0; converted to the track t_sec clock via
mon_first_tsec offset (validated against the plate-annotation start). Output (NON-DESTRUCTIVE):
annotations/KT_LANDMARK_ANALYSIS_20260723.csv — one row per tracked object per frame.
"""
import csv, json, glob, os, sys, collections
import numpy as np
import cv2
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import kt_tracks as KT

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"


def load_plates():
    """batch -> sorted list of (t_sec, Nx2 polyline px)."""
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{ROOT}/annotations/meta_plates.csv")):
        if not (r.get("points") or "").strip():
            continue
        try:
            pts = np.asarray(json.loads(r["points"]), float)
            t = float(r["t_sec"])
        except Exception:
            continue
        if pts.ndim == 2 and len(pts) >= 2:
            out[r["batch"]].append((t, pts))
    for b in out:
        out[b].sort(key=lambda z: z[0])
    return out


def _polyline_len_um(pts, px):
    p = np.asarray(pts, float)
    if p.ndim != 2 or len(p) < 2:
        return None
    return float(np.sum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1])))) * px


def load_chromo_len():
    """batch -> FIRST recorded chromosome length (um) = the sisterless chromosome's length. length_um in
    chromo_lines.csv is EMPTY, so length is COMPUTED from the traced polyline. First = smallest id."""
    best = {}
    for r in csv.DictReader(open(f"{ROOT}/annotations/chromo_lines.csv")):
        b = r["batch"]
        try:
            pts = json.loads(r["points"]); px = float(r.get("pixel_size_um") or 0.062)
            L = _polyline_len_um(pts, px); i = int(float(r.get("id") or 1e9))
        except Exception:
            continue
        if L is None:
            continue
        if b not in best or i < best[b][0]:
            best[b] = (i, L)
    return {b: v[1] for b, v in best.items()}


# ANTIQUED-MASTER event-time corrections (user 2026-07-23). Batches whose master Metaphase Start / Anaphase
# Onset is stale. Each value was resolved by cross-checking Metaphase Start vs Ablation->Meta vs the
# metaphase-plate window vs the annotation (+0s) marks vs the movie's frame bounds (derivation in
# _scratch/time_resolve). These OVERRIDE the master column so real metaphase frames stop being mislabeled
# prometaphase and dropped from the tension calibration. (batch -> (metaphase_tsec, anaphase_tsec))
RESOLVED_EVENT_TIMES = {
    "20250930 four_ablation_57": (993.0, 2686.0),                 # MS 2157 stale; Abl->Meta 993 + plate start 974 agree
    "20260420 ptk2 eyfp cdc20 1 ablation_20": (952.0, 1676.0),    # MS 1151 vs Abl->Meta 952 (plate start 777)
    "20260420 ptk2 eyfp cdc20 1 ablation_22": (291.49, 736.33),   # master edited after annotation; AO was past movie end
    "20260420 ptk2 eyfp cdc20 1 ablation_30": (-59.27, 345.44),   # master edited after annotation; AO past movie end
}

_ANNOT_EVENTS = None
def annotation_event_times():
    """Per-batch {'Metaphase','Anaphase': t_sec} from the annotation files' baked nearest_event '(+0s)'
    marks — the frame the USER tagged as the event on the actual movie (the most-recent manual time). Used
    to correct an ANTIQUED master column: the master Metaphase/Anaphase can be edited after annotation and go
    stale or even out of the movie's frame range (20260420 _22/_30: master anaphase falls AFTER the movie's
    last frame). Median over all '(+0s)' marks per event, across every annotation csv that carries
    nearest_event. Cached."""
    global _ANNOT_EVENTS
    if _ANNOT_EVENTS is not None:
        return _ANNOT_EVENTS
    import re, statistics, collections as _c
    rx = re.compile(r"(Metaphase|Anaphase)\s*\(([+-]?\d+)s\)")
    acc = _c.defaultdict(lambda: _c.defaultdict(list))
    for f in glob.glob(f"{ROOT}/annotations/*.csv"):
        if "backup" in f.lower():
            continue
        try:
            rd = csv.DictReader(open(f))
        except Exception:
            continue
        if not rd.fieldnames or "nearest_event" not in rd.fieldnames:
            continue
        for r in rd:
            m = rx.search(r.get("nearest_event", "") or "")
            if not m or int(m.group(2)) != 0:
                continue
            try:
                acc[r.get("batch", "")][m.group(1)].append(float(r["t_sec"]))
            except Exception:
                pass
    _ANNOT_EVENTS = {b: {k: statistics.median(v) for k, v in d.items()} for b, d in acc.items()}
    return _ANNOT_EVENTS


def phase_times(only_batches):
    """batch -> (meta_tsec, ana_tsec) on the track t_sec clock, from master elapsed times + mon offset.
    ONE recursive glob (cached index), restricted to `only_batches` (the tracked cells) for speed."""
    mr = {r["Batch Name"]: r for r in lib.load_master()[0]}
    idx = {}
    for p in glob.glob(f"{ROOT}/**/*_frames.json", recursive=True):
        if "backup" in p.lower():
            continue
        idx.setdefault(os.path.basename(p)[:-len("_frames.json")], p)
    out = {}
    for b in only_batches:
        p = idx.get(b)
        if not p or b not in mr:
            continue
        try:
            d = json.load(open(p))
        except Exception:
            continue
        # Metaphase/Anaphase times in the master are ALREADY on the t_sec clock (t=0 = first ablation,
        # user-confirmed 2026-07-23; they equal Ablation->Meta and the plate-annotation start). Use them
        # DIRECTLY — do NOT add the monitoring offset (that was a bug that shifted phase labels, worst on
        # metaphase-ablation cells). The frames.json is loaded only to confirm the batch has movie timing.
        me = lib.parse_time(mr[b].get("Metaphase Start (s)", ""))
        ae = lib.parse_time(mr[b].get("Anaphase Onset (s)", ""))
        # ANTIQUED-MASTER CORRECTION (user 2026-07-23): the master Metaphase/Anaphase columns can be edited
        # after annotation and go stale. Cross-check against the annotation-embedded (+0s) event times (the
        # frames the user tagged on the movie). If the master is out of the movie's frame range, or off by
        # >600 s from the annotation, the master is wrong -> use the annotation times. Small (~frame-noise)
        # disagreements leave the master untouched.
        try:
            mvmax = max(f["t_sec"] for f in d["frames"] if f.get("t_sec") is not None)
        except Exception:
            mvmax = None
        aev = annotation_event_times().get(b, {})
        am, aa = aev.get("Metaphase"), aev.get("Anaphase")
        bad = ((am is not None and me is not None and abs(am - me) > 600)
               or (aa is not None and ae is not None and abs(aa - ae) > 600)
               or (mvmax is not None and me is not None and me > mvmax + 30)
               or (mvmax is not None and ae is not None and ae > mvmax + 30))
        if bad:
            if am is not None:
                me = am
            if aa is not None:
                ae = aa
        # explicit, auditable resolved times take precedence over any auto-correction / master value
        if b in RESOLVED_EVENT_TIMES:
            me, ae = RESOLVED_EVENT_TIMES[b]
        out[b] = (me, ae)
    return out


def nearest_on_polyline(pt, poly):
    """nearest point on the polyline `poly` (Nx2) to `pt`, plus the distance."""
    best_d, best_q = 1e18, poly[0]
    for i in range(len(poly) - 1):
        a, b = poly[i], poly[i + 1]
        ab = b - a; L2 = float(ab @ ab)
        t = 0.0 if L2 == 0 else float(np.clip((pt - a) @ ab / L2, 0, 1))
        q = a + t * ab
        d = float(np.hypot(*(pt - q)))
        if d < best_d:
            best_d, best_q = d, q
    return best_q, best_d


def raster_interior(pieces, pad=3):
    """Fill the (possibly multi-piece) outline; return interior pixel coords (Nx2 float, image px) + area centroid."""
    allp = np.vstack(pieces)
    x0, y0 = np.floor(allp.min(0) - pad).astype(int)
    x1, y1 = np.ceil(allp.max(0) + pad).astype(int)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None, None
    mask = np.zeros((h, w), np.uint8)
    for p in pieces:
        cv2.fillPoly(mask, [np.round(p - [x0, y0]).astype(np.int32)], 1)
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None, None
    P = np.column_stack([xs + x0, ys + y0]).astype(float)
    return P, P.mean(0)


def landmark_descriptors(pieces, plate_poly, px):
    P, C = raster_interior(pieces)
    if P is None:
        return None
    L, dpl = nearest_on_polyline(C, plate_poly)
    u = (L - C); nu = np.hypot(*u)
    if nu < 1e-6:
        return None
    u = u / nu
    v = np.array([-u[1], u[0]])
    rel = P - C
    par = rel @ u                       # + toward plate
    perp = rel @ v
    area_px = len(P)
    near = int((par > 0).sum()); far = int((par < 0).sum())
    near_far = (near / far) if far > 0 else np.nan
    # reflection asymmetry across the PARALLEL axis (mirror perp -> -perp): crookedness ⟂ to stretch
    bins = 0.75
    A = set(zip(np.round(par / bins).astype(int), np.round(perp / bins).astype(int)))
    Am = set((p, -q) for (p, q) in A)
    refl_perp = 1.0 - len(A & Am) / len(A)
    par_ext = float(par.max() - par.min()); perp_ext = float(perp.max() - perp.min())
    aniso = par_ext / perp_ext if perp_ext > 0 else np.nan
    return dict(
        dist_to_plate_um=dpl * px,
        near_far_area_ratio=near_far,
        reflection_asym_perp=refl_perp,
        anisotropy_par_perp=aniso,
        R_toward_um=float(par.max()) * px,
        R_away_um=float(-par.min()) * px,
        area_toward_um2=near * px * px,
        area_away_um2=far * px * px,
        cx_area_px=float(C[0]), cy_area_px=float(C[1]),
        u_x=float(u[0]), u_y=float(u[1]),
    )


if __name__ == "__main__":
    # build rows
    objs = KT.tracked_objects()
    plates = load_plates(); chromo = load_chromo_len()
    phases = phase_times(sorted({o["batch"] for o in objs}))
    by_track = collections.defaultdict(list)
    for o in objs:
        by_track[o["track_id"]].append(o)
    rows = []
    for tid, tobjs in by_track.items():
        tobjs.sort(key=lambda o: (o["frame"], o["t_sec"] if np.isfinite(o["t_sec"]) else o["frame"]))
        b = tobjs[0]["batch"]; px = tobjs[0]["px"]
        plist = plates.get(b, []); mt, at = phases.get(b, (None, None)); clen = chromo.get(b, "")
        prev_dpl = None; prev = None
        for o in tobjs:
            m = o["metrics"]
            plate_poly = min(plist, key=lambda z: abs(z[0] - o["t_sec"]))[1] if plist else None
            lm = landmark_descriptors(o["points"], plate_poly, px) if plate_poly is not None else None
            ph = ""
            if np.isfinite(o["t_sec"]):
                if mt is not None and o["t_sec"] < mt: ph = "prometaphase"
                elif at is not None and o["t_sec"] >= at: ph = "anaphase"
                elif mt is not None: ph = "metaphase"
            spd = rad = ""
            if prev is not None and np.isfinite(o["t_sec"]) and np.isfinite(prev["t_sec"]):
                dt = o["t_sec"] - prev["t_sec"]
                if dt > 0:
                    spd = round(np.hypot((o["cx"] - prev["cx"]) * px, (o["cy"] - prev["cy"]) * px) / dt, 4)
                    if lm and prev_dpl is not None:
                        rad = round((prev_dpl - lm["dist_to_plate_um"]) / dt, 4)
            row = dict(track_id=tid, batch=b, label=o["label"], frame=o["frame"],
                       t_sec=round(o["t_sec"], 2) if np.isfinite(o["t_sec"]) else "",
                       phase=ph, chromo_len_um=clen, n_pieces=m["n_pieces"],
                       area_um2=round(m["area_um2"], 4), perimeter_um=round(m["perimeter_um"], 4),
                       circularity=round(m["circularity"], 4),
                       solidity=round(m["solidity"], 4) if np.isfinite(m["solidity"]) else "",
                       convexity=round(m["convexity"], 4) if np.isfinite(m["convexity"]) else "",
                       aspect_ratio=round(m["aspect_ratio"], 4), elongation=round(m["elongation"], 4),
                       major_um=round(m["major_um"], 4), minor_um=round(m["minor_um"], 4),
                       speed_um_s=spd, radial_speed_um_s=rad,
                       dist_to_plate_um="", near_far_area_ratio="", reflection_asym_perp="",
                       anisotropy_par_perp="", R_toward_um="", R_away_um="",
                       area_toward_um2="", area_away_um2="", stretch_radial_deg="")
            if lm:
                for k in ("dist_to_plate_um", "near_far_area_ratio", "reflection_asym_perp",
                          "anisotropy_par_perp", "R_toward_um", "R_away_um", "area_toward_um2", "area_away_um2"):
                    row[k] = lm[k] if (not isinstance(lm[k], float) or np.isfinite(lm[k])) else ""
                amaj = np.radians(m["angle_deg"]); au = np.arctan2(lm["u_y"], lm["u_x"])
                dth = abs(np.degrees((amaj - au + np.pi / 2) % np.pi - np.pi / 2))
                row["stretch_radial_deg"] = round(min(dth, 180 - dth), 2)
                prev_dpl = lm["dist_to_plate_um"]
            else:
                prev_dpl = None
            prev = o
            rows.append(row)
    cols = ["track_id", "batch", "label", "frame", "t_sec", "phase", "chromo_len_um", "n_pieces",
            "area_um2", "perimeter_um", "circularity", "solidity", "convexity", "aspect_ratio", "elongation",
            "major_um", "minor_um", "speed_um_s", "radial_speed_um_s",
            "dist_to_plate_um", "near_far_area_ratio", "reflection_asym_perp", "anisotropy_par_perp",
            "R_toward_um", "R_away_um", "area_toward_um2", "area_away_um2", "stretch_radial_deg"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    nlm = sum(1 for r in rows if r["dist_to_plate_um"] != "")
    print(f"wrote {len(rows)} rows ({nlm} with plate landmark) -> {OUT}")
    import statistics as st
    for lab in ("paired", "polar", "lagging"):
        d = [r for r in rows if r["label"] == lab and r["dist_to_plate_um"] != ""]
        if not d: continue
        md = st.median([float(r["dist_to_plate_um"]) for r in d])
        ma = st.median([float(r["anisotropy_par_perp"]) for r in d if r["anisotropy_par_perp"] != ""])
        mr_ = st.median([float(r["stretch_radial_deg"]) for r in d if r["stretch_radial_deg"] != ""])
        print(f"  {lab:8s} n={len(d):4d}  med dist_to_plate={md:.2f}um  anisotropy={ma:.2f}  stretch_radial_deg={mr_:.0f}")
