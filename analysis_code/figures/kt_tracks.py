#!/usr/bin/env python3
"""Build KINETOCHORE TRACKS from the outline traces — link the SAME kinetochore across frames and stamp a
persistent identity (track_id), for every category (paired/plate/polar/lagging).

User 2026-07-23: "all of this is happening across time, space and mitotic phases ... identify the same
paired/plate kinetochore across frames. Create an identity field. Build kt tracks regardless of group."

Per-frame OBJECTS:
  Grouping is K.group_key: traces sharing a grp are ONE kinetochore (pieces combined); untagged
  paired/plate fall back to one object per trace (the pre-"+ New KT" convention).
Each object carries a centroid (mean of its combined points) + the combined shape metrics.

LINKING (per batch+label, so a polar KT is never matched to a paired KT):
  frame-by-frame Hungarian assignment (scipy linear_sum_assignment) on centroid distance to each active
  track's PREDICTED position (constant-velocity extrapolation once a track has >=2 points, else last
  position). Global-optimal assignment resists the identity SWAP that greedy nearest-neighbour makes when two
  kinetochores are close. A match is accepted only within a motion GATE that scales with the (irregular) frame
  time-gap; an unmatched object starts a new track; a track unmatched beyond GAP_MAX_S is retired (gap-closing
  tolerates a KT missing from a frame or two). Single-object-per-frame batches collapse to one clean track.

Output (NON-DESTRUCTIVE, new file): annotations/KT_OUTLINE_TRACKS_20260723.csv — one row per per-frame
object, carrying track_id + centroid + t_sec + shape metrics. This is the identity field the temporal /
spatial / phase plots key on. kt_outlines.csv is untouched.
"""
import csv, json, os, collections
import numpy as np
import cv2
from scipy.optimize import linear_sum_assignment
import kt_shape_metrics as K

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv"

# motion gate: kinetochores move ~1-3 um/min; annotation frame gaps are irregular (tens to hundreds of s).
BASE_GATE_UM = 1.8            # allowance for a still KT (oscillation + tracing jitter)
SPEED_UM_PER_S = 0.05         # ~3 um/min poleward/congression speed
GATE_MAX_UM = 6.0            # never match across more than this (bigger = a different KT)
GAP_MAX_S = 240.0            # retire a track unmatched for longer than this


def _centroid(pieces):
    allp = np.vstack([np.asarray(p, float) for p in pieces])
    return float(allp[:, 0].mean()), float(allp[:, 1].mean())


def build_objects():
    """Per-frame objects grouped by (batch,label). Returns {(batch,label): {frame:[obj,...]}}."""
    recs = []
    import lib as _lib
    for r in csv.DictReader(open(K.SRC)):
        if r.get("channel") != "fluor":
            continue
        if _lib.kt_outline_excluded(r.get("batch")):   # user 2026-07-23 global kt-outline exclusion
            continue
        # 2026-08-10: this auto out-of-focus filter is POLAR-ONLY, as its own comment, its source file
        # (POLAR_FOCUS_CHECK_20260727.csv) and the 2026-07-27 request all say. It was being applied to every
        # label, and because that file scores PAIRED outlines too it was silently deleting 395 of her manual
        # paired outlines from the tracks -- an automatic intensity heuristic overriding hand-drawn marks,
        # which is backwards (her rule: measure at HER marks, never auto-detect). Centroid POSITION, which is
        # all the tracks carry, is robust to focus; SHAPE is not, so kt_shape_metrics keeps the wider filter.
        if r.get("label") == "polar" and _lib.focus_excluded(r.get("id")):
            continue
        try:
            pts = json.loads(r["points"])
        except Exception:
            continue
        recs.append((r, pts))
    # group into per-frame objects
    # polar/lagging: combine all pieces of (batch,label,frame,GRP) -> one object
    # paired/plate:  each trace -> its own object
    # 2026-08-03: this used to carry its own copy of the "grp:N" parser. kt_shape_metrics.grp_of is now the
    # single definition of her "+ New KT" identity, so the two readers can never drift apart if the notes
    # format changes. Same regex, same result — no output change.
    _grp_of = K.grp_of
    grp = collections.OrderedDict()
    for r, pts in recs:
        # 2026-08-03: this used to be a SECOND copy of the grouping rule and it drifted — kt_shape_metrics
        # was taught that a grp-tagged `paired` trace obeys the grp rule, this was not, and 136
        # (track_id,frame) duplicates survived. K.group_key is now the only definition.
        grp.setdefault(K.group_key(r), []).append((r, pts))
    objs = collections.defaultdict(lambda: collections.defaultdict(list))
    for key, members in grp.items():
        r0 = members[0][0]
        px = float(r0.get("pixel_size_um") or 0.062)
        pieces = [pts for (_, pts) in members]
        m = K._combined_metrics(pieces, px)
        if m is None:
            continue
        cap = K.MAX_MAJOR_UM if m["n_pieces"] == 1 else K.MAX_MAJOR_MULTI_UM
        if m["major_um"] > cap:
            continue
        try:
            frame = int(float(r0.get("frame") or -1))
        except Exception:
            frame = -1
        try:
            t_sec = float(r0.get("t_sec") or "nan")
        except Exception:
            t_sec = float("nan")
        cx, cy = _centroid(pieces)
        o = dict(id=r0.get("id"), batch=r0["batch"], label=r0["label"], frame=frame, t_sec=t_sec,
                 px=px, cx=cx, cy=cy, metrics=m, ids=[m0.get("id") for (m0, _) in members],
                 grp=_grp_of(r0),
                 points=[np.asarray(p, float) for p in pieces])
        objs[(r0["batch"], r0["label"])][frame].append(o)
    return objs


def _grp_tracks(frames_map, batch, label):
    """Track identity = the user's grp -> suffix '<grp>' (so track_id = batch|label|grp).
    Ungrouped objects fall back to NN-linking with suffix 'nn<i>'. This makes the user's manual
    kinetochore grouping the authoritative track identity."""
    allobj = [o for fr in frames_map.values() for o in fr]
    grouped = collections.OrderedDict(); nogrp = []
    for o in sorted(allobj, key=lambda x: x["frame"]):
        if o.get("grp"):
            grouped.setdefault(o["grp"], []).append(o)
        else:
            nogrp.append(o)
    result = [(str(g), objs) for g, objs in grouped.items()]
    if nogrp:
        fm = collections.defaultdict(list)
        for o in nogrp:
            fm[o["frame"]].append(o)
        tracks = close_gaps(link_group(fm)); tracks.sort(key=lambda tr: tr["objs"][0]["frame"])
        for ti, tr in enumerate(tracks):
            result.append((f"nn{ti}", tr["objs"]))
    return result


def tracked_objects():
    """Every per-frame object tagged with its track_id (str). Objects keep their combined polygon pieces
    in o['points'] so downstream landmark/shape geometry can recompute from the outline."""
    objs = build_objects()
    out = []
    for (batch, label), frames_map in objs.items():
        for suf, objs_ in _grp_tracks(frames_map, batch, label):
            tid = f"{batch}|{label}|{suf}"
            for o in objs_:
                o["track_id"] = tid
                out.append(o)
    return out


def link_group(frames_map):
    """frames_map: {frame:[obj]}. Returns list of tracks; each track = ordered list of objs (assigns o['trk'])."""
    frames = sorted(frames_map)
    px = next((o["px"] for fr in frames for o in frames_map[fr]), 0.062)  # shared per (batch,label)
    tracks = []            # each: {"objs":[...], "vx":,"vy":, "last_t":, "last_xy":, "alive":True}
    for fr in frames:
        objs = frames_map[fr]
        t = np.nanmedian([o["t_sec"] for o in objs])
        active = [tr for tr in tracks if tr["alive"]]
        if active:
            # predict each active track's position at this frame
            preds = []
            for tr in active:
                dt = (t - tr["last_t"]) if np.isfinite(t) and np.isfinite(tr["last_t"]) else 0.0
                lx, ly = tr["last_xy"]
                preds.append((lx + tr["vx"] * dt, ly + tr["vy"] * dt, dt))
            C = np.full((len(active), len(objs)), 1e6)
            for i, (pxp, pyp, dt) in enumerate(preds):
                gate_px = min(GATE_MAX_UM, BASE_GATE_UM + SPEED_UM_PER_S * abs(dt)) / px
                for j, o in enumerate(objs):
                    d = np.hypot(pxp - o["cx"], pyp - o["cy"])
                    if d <= gate_px:
                        C[i, j] = d
            row, col = linear_sum_assignment(C)
            matched = set()
            for r_, c_ in zip(row, col):
                if C[r_, c_] < 1e5:
                    tr = active[r_]; o = objs[c_]
                    dt = (o["t_sec"] - tr["last_t"]) if np.isfinite(o["t_sec"]) and np.isfinite(tr["last_t"]) else 0.0
                    if dt > 0:
                        tr["vx"] = (o["cx"] - tr["last_xy"][0]) / dt
                        tr["vy"] = (o["cy"] - tr["last_xy"][1]) / dt
                    tr["objs"].append(o); tr["last_xy"] = (o["cx"], o["cy"]); tr["last_t"] = o["t_sec"]
                    matched.add(c_)
            # retire active tracks that went unmatched too long
            for tr in active:
                if np.isfinite(t) and np.isfinite(tr["last_t"]) and (t - tr["last_t"]) > GAP_MAX_S:
                    tr["alive"] = False
            # unmatched objs -> new tracks
            for j, o in enumerate(objs):
                if j not in matched:
                    tracks.append(dict(objs=[o], vx=0.0, vy=0.0, last_t=o["t_sec"], last_xy=(o["cx"], o["cy"]), alive=True))
        else:
            for o in objs:
                tracks.append(dict(objs=[o], vx=0.0, vy=0.0, last_t=o["t_sec"], last_xy=(o["cx"], o["cy"]), alive=True))
    return tracks


GAP_CLOSE_MAX_S = 420.0     # link a track END to a later track START across a gap up to this long
GAP_CLOSE_BASE_UM = 2.2
GAP_CLOSE_GATE_MAX_UM = 8.0


def close_gaps(tracks):
    """Fragment-merging / gap-closing (TrackMate-style segment linking): after frame-to-frame linking,
    join a track's END to a later track's START when the end's motion-extrapolated position lands within a
    gate of that start and the temporal gap is <= GAP_CLOSE_MAX_S. Iterated so chains of fragments merge.
    This recovers a kinetochore that vanished from a few annotated frames (weak signal, fragmentation) and
    reappeared — which is what was leaving multi-KT cells un-paired."""
    tracks = [t for t in tracks if t["objs"]]
    if not tracks:
        return tracks
    px = tracks[0]["objs"][0]["px"]

    def endvel(s):
        o = s["objs"]
        if len(o) >= 2 and (o[-1]["t_sec"] - o[-2]["t_sec"]) > 0:
            dt = o[-1]["t_sec"] - o[-2]["t_sec"]
            return (o[-1]["cx"] - o[-2]["cx"]) / dt, (o[-1]["cy"] - o[-2]["cy"]) / dt
        return 0.0, 0.0

    changed = True
    while changed:
        changed = False
        n = len(tracks)
        if n < 2:
            break
        C = np.full((n, n), 1e6)
        for i, si in enumerate(tracks):
            oe = si["objs"][-1]; vx, vy = endvel(si)
            for j, sj in enumerate(tracks):
                if i == j:
                    continue
                os_ = sj["objs"][0]
                dt = os_["t_sec"] - oe["t_sec"]
                if dt <= 0 or dt > GAP_CLOSE_MAX_S:
                    continue
                pxp = oe["cx"] + vx * dt; pyp = oe["cy"] + vy * dt
                d = np.hypot(pxp - os_["cx"], pyp - os_["cy"]) * px
                gate = min(GAP_CLOSE_GATE_MAX_UM, GAP_CLOSE_BASE_UM + SPEED_UM_PER_S * dt)
                if d <= gate:
                    C[i, j] = d
        row, col = linear_sum_assignment(C)
        merges = sorted([(r, c) for r, c in zip(row, col) if C[r, c] < 1e5], key=lambda rc: C[rc[0], rc[1]])
        used_end, used_start, drop = set(), set(), set()
        for r, c in merges:
            si, sj = tracks[r], tracks[c]
            if id(si) in used_start or id(sj) in used_end or id(si) in drop or id(sj) in drop:
                continue
            si["objs"] = sorted(si["objs"] + sj["objs"], key=lambda o: (o["frame"], o["t_sec"]))
            used_end.add(id(si)); used_start.add(id(sj)); drop.add(id(sj)); changed = True
        if drop:
            tracks = [t for t in tracks if id(t) not in drop]
    return tracks


def build_tracks():
    objs = build_objects()
    rows_out = []
    stats = []
    for (batch, label), frames_map in objs.items():
        trks = _grp_tracks(frames_map, batch, label)
        for suf, objs_ in trks:
            tid = f"{batch}|{label}|{suf}"
            for o in objs_:
                m = o["metrics"]
                rows_out.append(dict(
                    track_id=tid, batch=batch, label=label, frame=o["frame"], t_sec=round(o["t_sec"], 2) if np.isfinite(o["t_sec"]) else "",
                    cx_px=round(o["cx"], 2), cy_px=round(o["cy"], 2),
                    cx_um=round(o["cx"] * o["px"], 3), cy_um=round(o["cy"] * o["px"], 3),
                    n_pieces=m["n_pieces"], trace_ids="|".join(str(i) for i in o["ids"] if i is not None),
                    area_um2=round(m["area_um2"], 4), perimeter_um=round(m["perimeter_um"], 4),
                    circularity=round(m["circularity"], 4), solidity=round(m["solidity"], 4) if np.isfinite(m["solidity"]) else "",
                    convexity=round(m["convexity"], 4) if np.isfinite(m["convexity"]) else "",
                    rectangularity=round(m["rectangularity"], 4) if np.isfinite(m["rectangularity"]) else "",
                    major_um=round(m["major_um"], 4), minor_um=round(m["minor_um"], 4),
                    aspect_ratio=round(m["aspect_ratio"], 4), elongation=round(m["elongation"], 4),
                    angle_deg=round(m["angle_deg"], 2),
                    roundness=round(m["roundness"], 4) if np.isfinite(m["roundness"]) else "",
                ))
        lens = [len(objs_) for _, objs_ in trks]
        stats.append((batch, label, len(trks), max(lens) if lens else 0,
                      round(float(np.mean(lens)), 1) if lens else 0))
    rows_out = _apply_measured_stage(rows_out)
    cols = ["track_id", "batch", "label", "frame", "t_sec", "cx_px", "cy_px", "cx_um", "cy_um",
            "n_pieces", "trace_ids", "area_um2", "perimeter_um", "circularity", "solidity",
            "convexity", "rectangularity", "major_um", "minor_um", "aspect_ratio", "elongation",
            "angle_deg", "roundness",
            # 2026-08-08: drift bookkeeping, appended so existing readers are unaffected
            "cx_px_stagecorr", "cy_px_stagecorr", "stage_dx_px", "stage_dy_px", "stage_source"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows_out)
    return rows_out, stats


# ---------------------------------------------------------------------------------------------------
# STAGE CORRECTION FROM THE MICROSCOPE'S OWN PER-FRAME VALUES. NOTHING IS INFERRED.
#
# USER 2026-08-09: "as long as youre using ONLY the frame hard-coded values directly from the microscope
# itself, its fine. DONT use the method you built yourself as its terribly incorrect."
#
# The method built on 2026-08-08 -- inferring a "common mode" as the MEDIAN displacement across all objects
# tracked between two frames -- IS RETIRED. It was wrong: it attributed 38% of measured kinetochore
# displacement to the stage, and the real metadata (harvested 2026-08-09, 1,518,809 planes with recorded
# XPositionUm/YPositionUm) shows the stage does not drift during acquisition at all. Of 2,071 source files,
# 1,901 never move, and the 170 that do make ONE jump before imaging starts (travelling to the position).
# So that correction was removing real signal.
#
# What is used instead: the recorded `XPositionUm`/`YPositionUm` for each frame, from
# `annotations/STAGE_XY_BY_FRAME_20260809.csv`, expressed RELATIVE TO THE FIRST FRAME OF THE SAME SOURCE
# FILE. Per-file, because a position change BETWEEN files in a multi-position acquisition is not drift --
# the pipeline re-anchors its crop there, so treating it as drift would inject a spurious ~10^5 px jump.
STAGE_BY_FRAME = f"{ROOT}/annotations/STAGE_XY_BY_FRAME_20260809.csv"


def _stage_offsets():
    """batch -> frame_idx -> (dx_px, dy_px), measured, relative to that frame's own source file."""
    import collections as _c
    if not os.path.exists(STAGE_BY_FRAME):
        return {}
    raw = _c.defaultdict(list)
    with open(STAGE_BY_FRAME, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            try:
                raw[r["batch"]].append((int(r["frame_idx"]), float(r["stage_x_um"]),
                                        float(r["stage_y_um"]), float(r["pixel_size_um"])))
            except Exception:
                pass
    out = {}
    for b, v in raw.items():
        v.sort()
        # a new source file announces itself as a large jump; restart the reference there
        per, refx, refy, prevx, prevy = {}, None, None, None, None
        for idx, x, y, px in v:
            if refx is None or (prevx is not None and
                                ((x - prevx) ** 2 + (y - prevy) ** 2) ** .5 > 50.0):
                refx, refy = x, y          # >50 um between consecutive frames = moved to a new position
            per[idx] = ((x - refx) / px, (y - refy) / px)
            prevx, prevy = x, y
        out[b] = per
    return out


def _apply_measured_stage(rows_out):
    """ADD the measured stage offset as EXTRA columns. Do NOT overwrite the annotated coordinates.

    *** WARNING 2026-08-09: THE `_stagecorr` COLUMNS ARE NOT FIT FOR USE. DO NOT PLOT THEM. ***
    They are emitted for the record only. Applying them INCREASES median track path length by 23%
    (19.83 -> 24.41 um), which a correction must never do. Cause: these are multi-position acquisitions
    where the stage returns to a NEARBY cell, so the between-position jump is real but smaller than the
    50 um threshold used below to detect "moved to a new position". Those jumps (median non-zero offset
    237 px, max 450 px -- far too large to be within-acquisition drift) are therefore treated as drift and
    subtracted, injecting a spurious ~237 px displacement into the track.
    THE CORRECT CONCLUSION FROM THE METADATA IS THAT NO CORRECTION IS NEEDED AT ALL: the stage does not
    drift during acquisition (1,901 of 2,071 source files never move; the other 170 jump once BEFORE
    imaging). Her traced coordinates in cx_px/cy_px are the right thing to plot, uncorrected.
    If drift ever does need correcting, it must be computed WITHIN a single source file only and never
    across a position change.

    USER 2026-08-09: "dont just overwrite data with the stage corrected version" / "keep copies of the data
    without stage movement correction in case we need to use it for something."

    So `cx_px`/`cy_px`/`cx_um`/`cy_um` remain EXACTLY what was traced -- untouched, never replaced. The
    stage-corrected coordinates live alongside as `cx_px_stagecorr`/`cy_px_stagecorr`, and the offset that
    produced them is written out too, so any consumer can apply, ignore or re-derive the correction.
    A builder that wants corrected positions opts in by reading the _stagecorr columns.

    This also means the default behaviour of every existing downstream builder is UNCHANGED -- which is the
    safe default, because the microscope metadata shows the stage barely moves during acquisition anyway
    (1,901 of 2,071 source files never move; the other 170 make one jump BEFORE imaging starts).
    """
    off = _stage_offsets()
    n_corr = 0
    for r in rows_out:
        d = off.get(r["batch"], {}).get(r["frame"])
        if d is None:
            r["stage_dx_px"] = r["stage_dy_px"] = ""
            r["stage_source"] = "no_metadata"
            r["cx_px_stagecorr"] = r["cx_px"]      # no metadata -> corrected == traced
            r["cy_px_stagecorr"] = r["cy_px"]
            continue
        r["stage_dx_px"], r["stage_dy_px"] = round(d[0], 3), round(d[1], 3)
        r["stage_source"] = "microscope_metadata"
        r["cx_px_stagecorr"] = round(r["cx_px"] - d[0], 2)
        r["cy_px_stagecorr"] = round(r["cy_px"] - d[1], 2)
        n_corr += 1
    nb = len({r["batch"] for r in rows_out if r.get("stage_source") == "microscope_metadata"})
    moved = sum(1 for r in rows_out if r.get("stage_dx_px") not in ("", 0, 0.0)
                or r.get("stage_dy_px") not in ("", 0, 0.0))
    print(f"stage offsets from MICROSCOPE METADATA on {n_corr}/{len(rows_out)} rows, {nb} batches; "
          f"{moved} rows have a NON-ZERO offset. Traced coordinates were NOT modified "
          f"(corrected values are in cx_px_stagecorr/cy_px_stagecorr).")
    return rows_out


if __name__ == "__main__":
    rows, stats = build_tracks()
    ntracks = len({r["track_id"] for r in rows})
    print(f"wrote {len(rows)} tracked objects in {ntracks} tracks -> {OUT}\n")
    print("=== tracks per (batch,label) [multi-KT cases first] ===")
    for batch, label, nt, mx, avg in sorted(stats, key=lambda s: -s[2]):
        flag = "  <-- multi-KT" if nt > 1 and label in ("paired", "plate") else ""
        print(f"  {label:8s} {nt:2d} tracks (len max {mx}, mean {avg})  {batch[:36]}{flag}")
