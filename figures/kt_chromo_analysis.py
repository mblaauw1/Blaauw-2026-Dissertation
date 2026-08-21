#!/usr/bin/env python3
"""Chromosome-line analysis: each traced chromosome (chromo_lines.csv, length COMPUTED from the polyline)
paired to a kinetochore, positioned relative to the metaphase plate.

Pairing (user 2026-07-23): the FIRST chromosome line per batch (smallest id) is the sisterless chromosome
whose length is assigned to the polar/lagging KT (even if not spatially closest that frame). Every OTHER
chromosome line pairs to the spatially-CLOSEST kinetochore outline in its frame. A pairing whose nearest KT
is implausibly far (> FAR_FLAG_UM) is flagged for review rather than trusted.

Per chromosome line we compute, relative to the plate:
  length_um                traced polyline length
  orient_vs_plate_deg      angle between the chromosome long axis and the plate line, [0,90]
                             (0 = PARALLEL to the plate, 90 = PERPENDICULAR / along the spindle axis)
  near_end_dist_um         distance of the CLOSEST chromosome end to the plate
  far_end_dist_um          distance of the FURTHEST chromosome end to the plate
  mid_dist_um              distance of the chromosome midpoint to the plate
  span_across_plate_um     far_end - near_end (how much of its length is 'radial' reach)
  paired_label / track_id  the kinetochore it pairs to
Output (NON-DESTRUCTIVE): annotations/KT_CHROMO_ANALYSIS_20260723.csv
"""
import csv, json, os, sys, collections
import numpy as np
import collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import kt_tracks as KT
from kt_landmark_analysis import load_plates, nearest_on_polyline, _polyline_len_um

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/annotations/KT_CHROMO_ANALYSIS_20260723.csv"
FAR_FLAG_UM = 6.0   # a non-first chromosome whose nearest KT is farther than this is flagged (review)


def ends_and_axis(pts):
    """Two extreme endpoints along the polyline's principal axis + the unit long-axis vector."""
    p = np.asarray(pts, float)
    c = p - p.mean(0)
    _, v = np.linalg.eigh(np.cov(c.T))
    axis = v[:, -1]                       # principal direction
    proj = c @ axis
    e0 = p[int(np.argmin(proj))]; e1 = p[int(np.argmax(proj))]
    d = e1 - e0; n = np.hypot(*d)
    return e0, e1, (d / n if n > 0 else np.array([1.0, 0.0]))


def plate_axis(poly):
    p = np.asarray(poly, float); c = p - p.mean(0)
    _, v = np.linalg.eigh(np.cov(c.T))
    return v[:, -1]


def run():
    # KT objects per (batch, frame) for spatial pairing
    objs = KT.tracked_objects()
    bybf = collections.defaultdict(list)
    for o in objs:
        bybf[(o["batch"], o["frame"])].append(o)
    frames_by_batch = collections.defaultdict(set)
    for o in objs:
        frames_by_batch[o["batch"]].add(o["frame"])
    plates = load_plates()

    # chromosome lines grouped per batch, ordered by id
    chl = collections.defaultdict(list)
    for r in csv.DictReader(open(f"{ROOT}/annotations/chromo_lines.csv")):
        if lib.kt_outline_excluded(r.get("batch")):   # user 2026-07-23 global kt-outline exclusion
            continue
        if not (r.get("points") or "").strip():
            continue
        try:
            pts = json.loads(r["points"]); i = int(float(r.get("id") or 1e9))
            fr = int(float(r.get("frame") or -1)); t = float(r.get("t_sec") or "nan")
            px = float(r.get("pixel_size_um") or 0.062)
        except Exception:
            continue
        chl[r["batch"]].append(dict(id=i, frame=fr, t_sec=t, px=px, pts=np.asarray(pts, float)))

    # SISTERLESS-CHROMOSOME ATTACHMENT (rewritten 2026-08-10).
    # The old rule was `first = (k == 0)` over `chl[batch]`, i.e. ALL of a cell's chromosome lines across ALL
    # frames sorted by id. That force-assigned exactly ONE row per cell to a polar/lagging kinetochore; every
    # other frame -- and every additional sisterless chromosome -- fell through to "nearest kinetochore" and
    # landed on a PAIRED KT. In a triple-sisterless cell there are up to three sisterless chromosomes, so most
    # of them were being attached to the wrong kinetochore: of 10 triple cells carrying both polar tension and
    # chromosome tracing, only 5 ended up with any length on a polar track.
    # Now: PER FRAME, the first `# Sisterless KTs` lines (by id) are the sisterless chromosomes and are matched
    # one-to-one to that frame's polar/lagging kinetochores, nearest first, with no kinetochore reused.
    _MRC = {r["Batch Name"]: r for r in lib.load_master()[0]}
    def _nsis(bb):
        v = (_MRC.get(bb, {}) or {}).get("# Sisterless KTs", "")
        try: return max(1, int(float(str(v).strip())))
        except Exception: return 1

    rows = []
    for b, lines in chl.items():
        lines.sort(key=lambda z: z["id"])
        # which lines are the sisterless ones, per frame
        _byfr = collections.defaultdict(list)
        for _l in lines: _byfr[_l["frame"]].append(_l)
        _sisterless_ids = set()
        for _fr, _ls in _byfr.items():
            for _l in sorted(_ls, key=lambda z: z["id"])[:_nsis(b)]:
                _sisterless_ids.add(_l["id"])
        _claimed = collections.defaultdict(set)   # frame -> track_ids already taken by a sisterless line
        plist = plates.get(b, [])
        for k, cl in enumerate(lines):
            px = cl["px"]
            # nearest KT in the same frame (fallback nearest frame)
            cxy = cl["pts"].mean(0)
            cand_frames = bybf
            fr = cl["frame"]
            near_kt, near_d = None, 1e18
            frames_avail = frames_by_batch.get(b, set())
            use_fr = fr if fr in frames_avail else (min(frames_avail, key=lambda f: abs(f - fr)) if frames_avail else None)
            for o in bybf.get((b, use_fr), []):
                d = np.hypot(o["cx"] - cxy[0], o["cy"] - cxy[1]) * px
                if d < near_d:
                    near_d, near_kt = d, o
            first = cl["id"] in _sisterless_ids
            if first:
                # a SISTERLESS chromosome: attach to a polar/lagging KT in this frame even if not spatially
                # closest, and never to one already claimed by another sisterless line in the same frame.
                pol = [o for o in bybf.get((b, use_fr), [])
                       if o["label"] in ("polar", "lagging") and o["track_id"] not in _claimed[use_fr]]
                paired = min(pol, key=lambda o: np.hypot(o["cx"] - cxy[0], o["cy"] - cxy[1])) if pol else near_kt
                if paired is not None and paired.get("label") in ("polar", "lagging"):
                    _claimed[use_fr].add(paired["track_id"])
                flag = "sisterless"
            else:
                paired = near_kt
                flag = "" if (near_kt and near_d <= FAR_FLAG_UM) else f"FAR({near_d:.1f}um)_REVIEW"
            # geometry vs plate
            length = _polyline_len_um(cl["pts"], px)
            e0, e1, axis = ends_and_axis(cl["pts"])
            orient = near = far = mid = span = ""
            if plist:
                poly = min(plist, key=lambda z: abs(z[0] - cl["t_sec"]))[1]
                pax = plate_axis(poly)
                ang = abs(np.degrees(np.arctan2(axis[1], axis[0]) - np.arctan2(pax[1], pax[0])))
                ang = ang % 180.0; orient = round(min(ang, 180 - ang), 2)  # 0=parallel,90=perp to plate
                d0 = nearest_on_polyline(e0, poly)[1] * px
                d1 = nearest_on_polyline(e1, poly)[1] * px
                near = round(min(d0, d1), 3); far = round(max(d0, d1), 3)
                mid = round(nearest_on_polyline(cl["pts"].mean(0), poly)[1] * px, 3)
                span = round(far - near, 3)
            rows.append(dict(batch=b, chromo_id=cl["id"], frame=cl["frame"],
                             t_sec=round(cl["t_sec"], 2) if np.isfinite(cl["t_sec"]) else "",
                             length_um=round(length, 4) if length else "",
                             paired_label=(paired["label"] if paired else ""),
                             paired_track=(paired["track_id"] if paired else ""),
                             pair_dist_um=round(near_d, 3) if near_d < 1e17 else "",
                             orient_vs_plate_deg=orient, near_end_dist_um=near, far_end_dist_um=far,
                             mid_dist_um=mid, span_across_plate_um=span, note=flag))
    cols = ["batch", "chromo_id", "frame", "t_sec", "length_um", "paired_label", "paired_track",
            "pair_dist_um", "orient_vs_plate_deg", "near_end_dist_um", "far_end_dist_um",
            "mid_dist_um", "span_across_plate_um", "note"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = run()
    nflag = sum(1 for r in rows if "REVIEW" in r["note"])
    print(f"wrote {len(rows)} chromosome lines -> {OUT}")
    print(f"  paired_label counts: {dict(collections.Counter(r['paired_label'] for r in rows))}")
    print(f"  flagged FAR (review): {nflag}")
    import statistics as stt
    ori = [float(r["orient_vs_plate_deg"]) for r in rows if r["orient_vs_plate_deg"] != "" and r["paired_label"] == "polar"]
    if ori:
        print(f"  polar chromosomes: median orient_vs_plate={stt.median(ori):.0f}deg (0=parallel,90=perp), n={len(ori)}")
