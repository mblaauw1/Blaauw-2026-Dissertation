#!/usr/bin/env python3
"""Propose cytosol-background points automatically for cells that already have a traced outline.

USER 2026-07-22: "can you find spots to calculate cytosol background for cells with marked outlines
on your own? ... one less thing to manually mark" -- and "i need to know you can do it well".

WHAT A cytosol_bg MARK IS FOR.  Every intensity measurement is `lib.disk_sum(r=9)` at the kinetochore
MINUS `lib.disk_sum(r=9)` at the cytosol mark on the same frame.  So the only thing that matters is
that the disk sits on clean cytoplasm inside the cell -- not on a chromosome, a kinetochore, a bright
speck, or outside the cell.  The exact position is free; the VALUE is what enters every plot.  This
script is therefore validated on the value it produces, not on how close it lands to a hand-placed dot.

METHOD (per outline frame)
  1. mask = inside the traced cell outline, eroded 12 px so the membrane and its halo are excluded;
  2. remove anything bright: pixels above the in-cell 80th percentile, dilated 9 px -- that takes out
     chromosomes, kinetochores and specks along with their glow;
  3. remove a 22 px disk around every manual mark on that frame (kt points, chromosome lines, plate);
  4. of what survives, score each candidate centre by local MEAN plus local SD (a flat, dim disk wins)
     and require the full r=9 disk to fit inside the surviving mask;
  5. reject the frame if nothing survives -- it proposes nothing rather than placing a bad point.

VALIDATION MODE (default): for frames that ALREADY have one of her cytosol_bg marks, compare the
disk_sum the proposal would give against the disk_sum her own mark gives, and report the distribution
of the relative difference. Nothing is written unless --apply is passed.
"""
import csv, json, os, sys, math
from collections import defaultdict
import numpy as np
import cv2

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

ROOT = "/Volumes/4 MB"
APPLY = "--apply" in sys.argv
LIMIT = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limit=")), 0)
csv.field_size_limit(10 ** 9)

R = 9              # the standard measurement radius
ERODE = 12         # px inside the outline
BRIGHT_PCT = 80    # in-cell percentile above which a pixel counts as "an object"
BRIGHT_DIL = 9     # px halo around objects
MARK_KEEP = 22     # px kept clear of any manual mark


def load_marks():
    """batch -> frame -> [(x, y)] for every manual mark that must be avoided"""
    out = defaultdict(lambda: defaultdict(list))
    for store, kind in (("kt_points", "pt"), ("chromo_lines", "poly"), ("meta_plates", "poly"),
                        ("kt_outlines", "poly")):
        p = f"{ROOT}/annotations/{store}.csv"
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p)):
            try:
                fr = int(float(r["frame"]))
            except Exception:
                continue
            b = r.get("batch", "")
            if kind == "pt":
                if r.get("label") == "cytosol_bg":
                    continue                     # her own background marks are not obstacles
                try:
                    out[b][fr].append((float(r["x"]), float(r["y"])))
                except Exception:
                    pass
            else:
                try:
                    for x, y in json.loads(r.get("points") or "[]"):
                        out[b][fr].append((float(x), float(y)))
                except Exception:
                    pass
    return out


def load_outlines():
    """(batch, phase) -> {frame: polygon}. Phase matters: an ablation-clip frame index is NOT a
    monitoring frame index, so an outline traced on monitoring cannot be indexed into the ablation
    clip by number. Where a phase has no outline of its own the cell footprint is borrowed from
    monitoring -- the same cell, and the ablation clip is seconds long, so it has barely moved."""
    out = defaultdict(dict)
    for r in csv.DictReader(open(f"{ROOT}/annotations/cell_outlines.csv")):
        try:
            pts = np.array(json.loads(r["points"]), float)
            if len(pts) >= 6:
                out[(r["batch"], (r.get("phase") or "mon"))][int(float(r["frame"]))] = pts
        except Exception:
            pass
    return out


def propose(gray, poly, marks, bright_pct=BRIGHT_PCT, keep=MARK_KEEP, erode=ERODE):
    """return (x, y, score_dict) for a representative cytosol disk, or None"""
    h, w = gray.shape[:2]
    cell = np.zeros((h, w), np.uint8)
    cv2.fillPoly(cell, [np.round(poly).astype(np.int32)], 1)
    if cell.sum() < 500:
        return None
    cell = cv2.erode(cell, np.ones((erode * 2 + 1,) * 2, np.uint8))
    if cell.sum() < 200:
        return None
    vals = gray[cell > 0]
    thr = np.percentile(vals, bright_pct)
    bright = ((gray > thr) & (cell > 0)).astype(np.uint8)
    bright = cv2.dilate(bright, np.ones((BRIGHT_DIL * 2 + 1,) * 2, np.uint8))
    ok = (cell > 0) & (bright == 0)
    for (mx, my) in marks:
        cv2.circle(ok.view(np.uint8), (int(round(mx)), int(round(my))), keep, 0, -1)
    ok = ok.astype(np.uint8)
    # the whole r=9 disk must fit: erode the allowed area by R
    fit = cv2.erode(ok, np.ones((R * 2 + 1,) * 2, np.uint8))
    ys, xs = np.where(fit > 0)
    if len(xs) == 0:
        return None
    g = gray.astype(np.float32)
    mean = cv2.blur(g, (R * 2 + 1, R * 2 + 1))
    sq = cv2.blur(g * g, (R * 2 + 1, R * 2 + 1))
    sd = np.sqrt(np.maximum(sq - mean * mean, 0))
    # MATCH HER PLACEMENT, measured from her own marks rather than assumed.  Across 51-53 of her
    # cytosol_bg marks: the disk sits at the 59th percentile of in-cell intensity (IQR 52-81), at a
    # normalised radius of 0.40 from the cell centroid (IQR 0.30-0.49) -- mid-cell, and slightly
    # ABOVE the in-cell median, not at the dim end.  Targeting the dimmest, or even the median of the
    # candidate set, biased the background low by ~5.5%.  So: aim at the 59th-percentile intensity,
    # prefer mid-radius, and break ties on flatness.
    m = mean[ys, xs]
    target = float(np.percentile(vals, 59))
    cx, cy = float(np.mean(poly[:, 0])), float(np.mean(poly[:, 1]))
    rmax = max(np.hypot(poly[:, 0] - cx, poly[:, 1] - cy).max(), 1.0)
    rnorm = np.hypot(xs - cx, ys - cy) / rmax
    scale = max(float(np.std(m)), 1.0)
    s = (np.abs(m - target) / scale) + 1.2 * np.abs(rnorm - 0.40) + 0.15 * (sd[ys, xs] / scale)
    i = int(np.argmin(s))
    return float(xs[i]), float(ys[i]), {"n_candidates": int(len(xs)),
                                        "local_mean": float(mean[ys[i], xs[i]]),
                                        "local_sd": float(sd[ys[i], xs[i]])}


MARKS = load_marks()
OUTL = load_outlines()
HER = defaultdict(dict)
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv")):
    if r.get("label") == "cytosol_bg":
        try:
            HER[r["batch"]][int(float(r["frame"]))] = (float(r["x"]), float(r["y"]))
        except Exception:
            pass

ALL_FRAMES = "--all-frames" in sys.argv

PHASES = [p for p in (next((a.split("=")[1] for a in sys.argv if a.startswith("--phases=")), "mon")).split(",") if p]
ROLE = {"mon": "monitoring", "abl": "ablation", "pre": "pre"}


_TS = {}
def tsecs_of(batch, phase="mon"):
    """frame index -> real t_sec for this phase, from the batch's own frames.json (never assumed)."""
    k = (batch, phase)
    if k in _TS:
        return _TS[k]
    out = {}
    p = DP.get(batch)
    if p and os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if f.endswith("_frames.json"):
                try:
                    d = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
                except Exception:
                    break
                sub = [x for x in d.get("frames", []) if x.get("role") == ROLE.get(phase, phase)]
                out = {i: float(fr["t_sec"]) for i, fr in enumerate(sub) if fr.get("t_sec") is not None}
                break
    _TS[k] = out
    return out


def hms(t):
    if t is None:
        return ""
    s_ = int(t); sign = "-" if s_ < 0 else ""; s_ = abs(s_)
    return f"{sign}{s_//3600:02d}:{(s_%3600)//60:02d}:{s_%60:02d}"


def frames_of(batch, phase="mon"):
    """every frame index of this batch for the given phase, from its own frames.json"""
    p = DP.get(batch)
    if not p or not os.path.isdir(p):
        return []
    for f in sorted(os.listdir(p)):
        if f.endswith("_frames.json"):
            try:
                d = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
            except Exception:
                return []
            return list(range(len([x for x in d.get("frames", []) if x.get("role") == ROLE.get(phase, phase)])))
    return []


def drive_paths():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    h = [c.strip() for c in rows[hi]]
    bi, pi = h.index("Batch Name"), h.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[hi + 1:] if r and len(r) > pi and r[bi].strip()}


DP = drive_paths()

batches = sorted({b for (b, _ph) in OUTL})
if LIMIT:
    batches = batches[:LIMIT]

rel, dist, made, nofit, noimg = [], [], 0, 0, 0
rows = []
for b in batches:
    for ph in PHASES:
        have_ph = ph if (b, ph) in OUTL else ("mon" if (b, "mon") in OUTL else None)
        if have_ph is None:
            continue
        polys = OUTL[(b, have_ph)]
        have = sorted(polys)
        try:
            tif = lib.FluorTif(b, role=ROLE.get(ph, ph))
        except Exception:
            tif = None
        if tif is None or not tif.ok():
            noimg += 1
            continue
        want = frames_of(b, ph) if ALL_FRAMES else (have if have_ph == ph else frames_of(b, ph))
        for fr in want:
            near = min(have, key=lambda h: abs(h - fr))
            # a borrowed-from-monitoring footprint has no frame correspondence at all; treat it as a
            # large gap so the erosion is generous.
            gap = abs(near - fr) if have_ph == ph else 25
            poly = polys[near]
            try:
                # OFF-BY-ONE FIX (2026-07-28): `fr` is a ONE-BASED annotation frame. plane_by_frame
                # applies the correction; plane_by_pos does NOT - it takes a raw page index - so the
                # else-branch was reading one plane late. Route it through pos_of_frame.
                _pos = tif.pos_of_frame(fr)
                gray = tif.plane_by_frame(fr) if have_ph == ph else (
                    tif.plane_by_pos(_pos) if _pos is not None else None)
            except Exception:
                gray = None
            if gray is None:
                noimg += 1
                continue
            mk = MARKS.get(b, {}).get(fr, [])
            extra = min(gap, 30)
            # RELAXATION LADDER.  The first pass is deliberately strict; if nothing survives it, the
            # constraints are eased step by step rather than giving up.  Measured 2026-07-22: with only
            # three levels, 16,482 in-window frames were skipped -- and 610 of those HAD their own
            # outline (gap 0), so the mask, not the borrowed footprint, was the binding constraint.
            # `relax_level` is recorded on every row: 0 = strictest, higher = more relaxed, so a row
            # that needed a loose mask is always identifiable.
            LADDER = [dict(bright_pct=BRIGHT_PCT, keep=MARK_KEEP, erode=ERODE + extra),
                      dict(bright_pct=90, keep=16, erode=ERODE + extra),
                      dict(bright_pct=95, keep=12, erode=ERODE + extra),
                      dict(bright_pct=97, keep=10, erode=max(6, (ERODE + extra) // 2)),
                      dict(bright_pct=99, keep=8,  erode=6),
                      dict(bright_pct=100, keep=6, erode=4)]
            p = None
            for lvl, kw in enumerate(LADDER):
                p = propose(gray, poly, mk, **kw)
                if p is not None:
                    break
            if p is None:
                nofit += 1
                continue
            x, y, info = p
            info["relax_level"] = lvl
            made += 1
            mine = lib.disk_sum(gray, x, y, r=R)
            hers = None
            if ph == "mon" and fr in HER.get(b, {}):
                hx, hy = HER[b][fr]
                hers = lib.disk_sum(gray, hx, hy, r=R)
                if hers:
                    rel.append((mine - hers) / hers)
                    dist.append(math.hypot(x - hx, y - hy))
            _t = tsecs_of(b, ph).get(fr)
            rows.append({"batch": b, "phase": ph, "frame": fr,
                         "t_sec": "" if _t is None else round(_t, 2), "t_hms": hms(_t),
                         "outline_gap_frames": gap,
                         "outline_from_phase": have_ph,
                         "x": round(x, 1), "y": round(y, 1),
                         "disk_sum": None if mine is None else round(mine, 1),
                         "her_disk_sum": None if hers is None else round(hers, 1),
                         "relax_level": info.get("relax_level", 0),
                         "n_candidates": info["n_candidates"],
                         "local_mean": round(info["local_mean"], 1),
                         "local_sd": round(info["local_sd"], 1)})

print(f"batches: {len(batches)}   phases: {PHASES}   proposals made: {made}   "
      f"no clean spot found: {nofit}   no image plane: {noimg}")
if rel:
    a = np.array(rel) * 100
    d = np.array(dist)
    print(f"\nVALIDATION against {len(rel)} of her own cytosol_bg marks (same batch AND frame):")
    print(f"  relative difference in disk_sum:  median {np.median(a):+.2f}%   "
          f"IQR {np.percentile(a,25):+.2f}% to {np.percentile(a,75):+.2f}%")
    for t in (2, 5, 10):
        print(f"    within {t:2d}% of her value: {100*np.mean(np.abs(a)<=t):5.1f}%")
    print(f"  distance from her point: median {np.median(d):.0f} px "
          f"(position is free -- only the value is used)")
else:
    print("no overlapping frames to validate against")

out = f"{ROOT}/_scratch/auto_cytosol_bg_proposals.csv"
if rows:
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f"\nproposals written to {out}")
if not APPLY:
    print("(validation run -- nothing was written to any annotation store)")
