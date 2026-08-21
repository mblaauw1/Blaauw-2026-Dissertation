#!/usr/bin/env python3
"""TIMESTRIP ANNOTATION SPEC — how she tells the builder which frames, where to centre, and what zoom.

USER 2026-08-09: "im trying to figure out a way to give you annotations on how to center each frame on
the cell, what frames to include in the timestrip, and what zoom i want for a cell's frames, all while
structuring these instructions so that they can be seamlessly turned into the aligned timestrip setup
we've created."

NOTHING NEW TO LEARN AND NO NEW MARK TYPE. All three already exist in the annotation tool and already
route to their own stores via serve_annotation.TYPE_TO_FILE. This module just fixes the CONVENTION and
reads it back. Today the same three knobs live as hard-coded python dicts inside group_timestrips.py
(`ROI_UM_FRAMES` for per-frame shifts, `CROP_TRIM` for per-cell trim), which means every art-direction
tweak is a code edit; after this they are annotations.

    WHICH FRAMES   the "⌖ Mark this frame as timestrip" button  -> type `timestrip_frame`
                   One mark per frame she wants in the strip. Frame order = strip order.
                   `label` (optional) names the ROW: "abl" | "mon" | "zoom". Blank = main row.

    ZOOM           a crop box drawn ONCE for the batch          -> type `crop_box`
                   Its w/h set the WINDOW SIZE. `crop_name`:
                       "timestrip"      -> size for the main row
                       "timestrip_zoom" -> size for the close-up row (optional)
                   Drawn on any frame; only its SIZE is taken from here, never its position.

    CENTERING      per frame, first of these that exists:
                       1. a `crop_box` drawn ON THAT FRAME     -> its centre
                       2. her `cell_outline` centroid on that frame
                       3. the batch crop box's own centre
                       4. auto `tight_crop` (current behaviour)

THE ONE RULE THAT MAKES IT "ALIGNED": SIZE IS FIXED PER BATCH, ONLY THE CENTRE MOVES. If a per-frame box
were allowed to resize the window, the cell would change scale between columns and the strip would stop
being comparable frame-to-frame. So size comes from the batch-level box (or the median of her boxes) and
per-frame annotations may only re-centre. A frame whose window would fall outside the image is clamped
back inside, exactly as `apply_roi_um_frame` already does.

`plan_for(batch)` returns everything the builder needs:
    {"frames": [ {frame, t_sec, row}, ... ],          # empty -> builder picks frames as it does today
     "size_px": int | None,                            # None -> fall back to tight_crop's sizing
     "zoom_size_px": int | None,
     "centers": {frame: (cx, cy)},                     # per-frame centre, image pixels
     "source": {...}}                                  # which annotation supplied each piece
"""
import csv, json, collections, os

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"


def _rows(name):
    p = A + name
    if not os.path.isfile(p):
        return []
    return list(csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")))


def _centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def plan_for(batch):
    out = {"frames": [], "size_px": None, "zoom_size_px": None, "centers": {}, "source": {}}

    # ---- WHICH FRAMES ----------------------------------------------------------------------------
    fr = []
    for r in _rows("timestrip_frames.csv"):
        if (r.get("batch") or "").strip() != batch:
            continue
        try:
            f = int(r["frame"])
        except Exception:
            continue
        t = None
        try:
            t = float(r["t_sec"])
        except Exception:
            pass
        fr.append({"frame": f, "t_sec": t, "row": (r.get("label") or "").strip() or "main"})
    fr.sort(key=lambda d: d["frame"])
    out["frames"] = fr
    out["source"]["frames"] = f"timestrip_frames.csv ({len(fr)} marks)" if fr else "none — builder default"

    # ---- ZOOM (size only) + any per-frame boxes ---------------------------------------------------
    boxes = []
    for r in _rows("crop_boxes.csv"):
        if (r.get("batch") or "").strip() != batch:
            continue
        try:
            x = float(r["x"]); y = float(r["y"]); w = float(r["w"]); h = float(r["h"])
        except Exception:
            continue
        f = None
        try:
            f = int(r["frame"])
        except Exception:
            pass
        boxes.append({"frame": f, "x": x, "y": y, "w": w, "h": h,
                      "name": (r.get("crop_name") or "").strip()})
    def _size(named):
        b = [q for q in boxes if q["name"] == named]
        if not b:
            return None
        # square window: the larger side, so the cell is never cropped by the shorter axis
        return int(round(max(max(q["w"], q["h"]) for q in b)))
    out["size_px"] = _size("timestrip") or (int(round(max(max(q["w"], q["h"]) for q in boxes)))
                                            if boxes else None)
    out["zoom_size_px"] = _size("timestrip_zoom")
    out["source"]["size"] = ("crop_box crop_name='timestrip'" if _size("timestrip")
                             else f"largest of {len(boxes)} crop_box(es)" if boxes
                             else "none — tight_crop sizing")

    # ---- CENTERING, per frame ---------------------------------------------------------------------
    centers, why = {}, collections.Counter()
    # 2. her cell outlines, per frame
    for r in _rows("cell_outlines.csv"):
        if (r.get("batch") or "").strip() != batch:
            continue
        try:
            pts = json.loads(r.get("points") or "[]")
            f = int(r["frame"])
        except Exception:
            continue
        if pts:
            centers[f] = _centroid(pts); why["cell_outline centroid"] += 1
    # 1. a crop box drawn on a specific frame WINS (highest priority, applied last)
    for q in boxes:
        if q["frame"] is not None:
            centers[q["frame"]] = (q["x"] + q["w"] / 2.0, q["y"] + q["h"] / 2.0)
            why["per-frame crop_box"] += 1
    out["centers"] = centers
    # 3. batch-level fallback centre
    if boxes:
        b0 = boxes[0]
        out["default_center"] = (b0["x"] + b0["w"] / 2.0, b0["y"] + b0["h"] / 2.0)
        out["source"]["default_center"] = "batch crop_box centre"
    else:
        out["default_center"] = None
        out["source"]["default_center"] = "none — tight_crop centre"
    out["source"]["centers"] = dict(why) or "none — tight_crop centre for every frame"
    return out


def window_for(plan, frame, W=None, H=None):
    """The crop box (x0,y0,x1,y1) for one frame: FIXED size from the plan, centre from the annotation."""
    s = plan.get("size_px")
    if not s:
        return None
    c = plan["centers"].get(frame) or plan.get("default_center")
    if not c:
        return None
    cx, cy = c
    x0 = int(round(cx - s / 2.0)); y0 = int(round(cy - s / 2.0))
    x1, y1 = x0 + s, y0 + s
    if W is not None:
        if x0 < 0: x1 -= x0; x0 = 0
        if x1 > W: x0 -= (x1 - W); x1 = W
    if H is not None:
        if y0 < 0: y1 -= y0; y0 = 0
        if y1 > H: y0 -= (y1 - H); y1 = H
    return (x0, y0, x1, y1)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
    import lib
    # which batches on NEW_TIMESTRIPS already carry enough annotation to drive this?
    seen = collections.Counter()
    batches = sorted({(r.get("batch") or "").strip()
                      for n in ("timestrip_frames.csv", "crop_boxes.csv", "cell_outlines.csv")
                      for r in _rows(n)} - {""})
    print(f"batches with any of the three annotation kinds: {len(batches)}\n")
    ready = []
    for b in batches:
        p = plan_for(b)
        has = (bool(p["frames"]), p["size_px"] is not None, bool(p["centers"]))
        seen[has] += 1
        if all(has):
            ready.append(b)
    print("coverage (frames / size / centers):")
    for k, v in sorted(seen.items(), key=lambda t: -t[1]):
        print(f"   frames={k[0]!s:5s} size={k[1]!s:5s} centers={k[2]!s:5s}  {v} batches")
    print(f"\nfully specified today: {len(ready)}")
    for b in ready[:10]:
        p = plan_for(b)
        print(f"   {b[:46]:46s} frames={len(p['frames'])} size={p['size_px']}px centers={len(p['centers'])}")
