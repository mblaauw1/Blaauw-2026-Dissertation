#!/usr/bin/env python3
"""SFF (Standard Frame Footprint) crop windows for the 5 hand-cropped Mad1 batches (handoff-5 §14).

Her spec: for each batch where she drew a manual crop box, compute the SMALLEST square window that
CONTAINS the entire manual crop area -> side = max(box_w, box_h), centred on her crop-box centre,
clamped to the frame. "Include all of the manual crop area in as small a space as possible."

Crop-box convention (make_annotation_html.py pointerup): x,y = TOP-LEFT corner in ROI px, w,h = size.
So centre = (x + w/2, y + h/2). Frame = the ROI (frames.json roi w,h); all 5 are 1248x1056.

NON-DESTRUCTIVE: reads annotations/crop_boxes.csv, writes a NEW file
annotations/SFF_CROPS_20260723.csv. Does NOT touch her 5 crop_boxes rows.
"""
import csv, json, os, glob

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)

# frames.json (for the ROI = frame dims) located once per batch
FJ = {}
for b in ["20260304 Mad1_timelapse_1_xy2", "20260304 Mad1_timelapse_1_xy6",
          "20260310 ptk2_eyfp_mad1_14",
          "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy5",
          "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy8"]:
    hits = glob.glob(f"{ROOT}/**/{b}_frames.json", recursive=True)
    # prefer a pipeline_session_output / mad1_timelapse_review copy (avoid backups)
    hits.sort(key=lambda p: ("backup" in p.lower(), len(p)))
    FJ[b] = hits[0] if hits else None

boxes = {r["batch"]: r for r in csv.DictReader(open(f"{ROOT}/annotations/crop_boxes.csv"))}

out_rows = []
for b, fj in FJ.items():
    r = boxes.get(b)
    if r is None:
        print(f"  {b}: NO crop box row -> skip"); continue
    d = json.load(open(fj))
    W, H = int(d["roi"]["w"]), int(d["roi"]["h"])
    x, y, w, h = float(r["x"]), float(r["y"]), float(r["w"]), float(r["h"])
    cx, cy = x + w / 2.0, y + h / 2.0
    side = max(w, h)
    # clamp the square inside the frame, keeping it square (shift inward; side < frame here so no scaling)
    side = min(side, W, H)
    x0 = max(0.0, min(W - side, cx - side / 2.0))
    y0 = max(0.0, min(H - side, cy - side / 2.0))
    out_rows.append({
        "batch": b, "frame_w": W, "frame_h": H,
        "manual_x": round(x, 2), "manual_y": round(y, 2),
        "manual_w": round(w, 2), "manual_h": round(h, 2),
        "sff_x0": round(x0, 2), "sff_y0": round(y0, 2),
        "sff_side": round(side, 2),
        "sff_x1": round(x0 + side, 2), "sff_y1": round(y0 + side, 2),
        "sff_center_x": round(cx, 2), "sff_center_y": round(cy, 2),
        "sff_um": round(side * float(r.get("pixel_size_um") or 0.062), 2),
        "pixel_size_um": r.get("pixel_size_um") or "0.062",
        "note": "smallest square containing the manual crop box, clamped to frame; source of truth = crop_boxes.csv",
    })
    print(f"  {b}: manual {w:.0f}x{h:.0f} @ ({x:.0f},{y:.0f}) -> SFF side {side:.0f}px "
          f"({side*0.062:.1f}um) @ ({x0:.0f},{y0:.0f})..({x0+side:.0f},{y0+side:.0f})  frame {W}x{H}")

outp = f"{ROOT}/annotations/SFF_CROPS_20260723.csv"
with open(outp, "w", newline="") as fh:
    wtr = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
    wtr.writeheader(); wtr.writerows(out_rows)
print(f"\nwrote {len(out_rows)} rows -> {outp}")
