#!/usr/bin/env python3
"""Round the hand-drawn crop boxes to the project's standard timestrip window.

USER 2026-07-22 (Mad1 slide note 5/28, `20260304 Mad1_timelapse_1_xy2`):
"Crop box defined (have crop box rounded to the standard crop box we've been using)".

THE STANDARD, taken from the code rather than guessed: `ts_render.STD_MAIN_UM = 78.0` µm -- the fixed
PHYSICAL square window every timestrip main tile uses, clamped to the frame's short side. At the usual
0.062 µm/px that is 1258 px, wider than the 1056-px frame height, so in practice the clamp makes it a
square of the frame's short side. The same clamp is applied here, so a rounded box matches exactly what
`std_square_crop` would produce for that batch.

WHAT CHANGES: only `w`, `h`, `x`, `y` of the crop box, re-centred on the box the user drew, so her
chosen position is kept and only the SHAPE is standardised. The original values are preserved in
`notes` so the hand-drawn box is never lost.

Run with --apply. Backs up, writes atomically, verifies by re-reading.
"""
import csv, json, os, sys, glob, shutil, datetime

ROOT = "/Volumes/4 MB"
CB = f"{ROOT}/annotations/crop_boxes.csv"
APPLY = "--apply" in sys.argv
csv.field_size_limit(10 ** 9)
sys.path.insert(0, f"{ROOT}/ablation_figures_20260625")
import lib
import ts_render

data, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in data}


def frame_size(batch):
    """(W, H) of the rendered frame for this batch, from its own frames.json roi."""
    p = (MR.get(batch, {}) or {}).get("Drive Path", "")
    if p and os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if f.endswith("_frames.json"):
                try:
                    j = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
                    roi = j.get("roi") or {}
                    if roi.get("w") and roi.get("h"):
                        return float(roi["w"]), float(roi["h"])
                except Exception:
                    pass
    return 1248.0, 1056.0


def pixel_size(batch):
    try:
        v = float((MR.get(batch, {}) or {}).get("Pixel Size (um)", "") or 0)
        return v if v > 0 else 0.062
    except Exception:
        return 0.062


rows = list(csv.DictReader(open(CB)))
hdr = list(rows[0].keys())
changed = []
for r in rows:
    b = r.get("batch", "")
    try:
        w, h = float(r["w"]), float(r["h"])
        x, y = float(r["x"]), float(r["y"])
    except Exception:
        continue
    W, H = frame_size(b)
    pxs = pixel_size(b)
    side = min(ts_render.STD_MAIN_UM / pxs, W, H)          # the same clamp std_square_crop applies
    cx, cy = x + w / 2.0, y + h / 2.0                       # keep her chosen centre
    nx = min(max(cx - side / 2.0, 0.0), W - side)
    ny = min(max(cy - side / 2.0, 0.0), H - side)
    if abs(w - side) < 0.5 and abs(h - side) < 0.5:
        continue
    old = f"hand-drawn box was x={x:.1f} y={y:.1f} w={w:.1f} h={h:.1f}"
    note = (r.get("notes") or "").strip()
    r["notes"] = (note + " | " if note else "") + \
                 f"[2026-07-22] rounded to the standard {ts_render.STD_MAIN_UM:.0f}um timestrip window " \
                 f"({side:.0f}px, clamped to the frame); {old}"
    r["x"], r["y"], r["w"], r["h"] = round(nx, 2), round(ny, 2), round(side, 2), round(side, 2)
    changed.append((b, w, h, side))

print(f"crop boxes: {len(rows)}   rounded: {len(changed)}")
for b, w, h, side in changed:
    print(f"   {b[:46]:46s} {w:7.1f}x{h:7.1f}  ->  {side:.0f}x{side:.0f}")

if APPLY and changed:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy(CB, f"{ROOT}/_master_backups/crop_boxes_pre_round_{ts}.csv")
    tmp = CB + ".tmp"
    with open(tmp, "w", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=hdr); w_.writeheader(); w_.writerows(rows)
    os.replace(tmp, CB)
    chk = list(csv.DictReader(open(CB)))
    ok = sum(1 for a, b2 in zip(chk, rows) if a["w"] == str(b2["w"]))
    print(f"WROTE {CB} -- {len(chk)} rows, verified {ok} widths match")
elif not APPLY:
    print("(dry run -- pass --apply)")
