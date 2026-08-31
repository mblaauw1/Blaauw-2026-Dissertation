#!/usr/bin/env python3
"""Merge the localStorage-recovered outlines for ONE batch into kt_outlines.csv.

USER 2026-08-09: "you can update 20260108 two_sisterless_kinetochores_14 ... the rest of the unsaved
points are so few per batch that i think this might just be duplicates or cleanup, and you can go ahead
and discard them."

So: 98 traces for `20260108 two_sisterless_kinetochores_14` are merged; the other 17 across 5 batches are
DISCARDED (they stay in the recovery JSON, they are simply not written).

She also noted that batch is 2-SISTERLESS, and the kt-outline figures currently use 1- and 3-sisterless
only — so merging these does NOT change any current figure. It restores the annotation so the cell is
whole whenever 2-sisterless is brought in.

NON-DESTRUCTIVE (her standing rule): back up first, write to a temp file, verify row counts and that every
pre-existing row survives byte-identical, then atomically swap. IDs are allocated ABOVE the file's current
max so nothing collides with another batch.
"""
import csv, json, os, shutil, sys, datetime
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
SRC = A + "_localstorage_recovery_20260809/UNSAVED_CONFIRMED.json"
KT = A + "kt_outlines.csv"
TARGET = "20260108 two_sisterless_kinetochores_14"

rows_m, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in rows_m}
try:
    PX = float((MR.get(TARGET, {}).get("Pixel Size (um)", "") or 0.062))
except Exception:
    PX = 0.062

rec = json.load(open(SRC))
marks = rec.get(TARGET, [])
print(f"recovered traces for {TARGET}: {len(marks)}")
discarded = {b: len(v) for b, v in rec.items() if b != TARGET}
print(f"DISCARDING per her instruction: {sum(discarded.values())} traces across {len(discarded)} batches")
for b, n in sorted(discarded.items(), key=lambda x: -x[1]):
    print(f"    {b[:52]:52s} {n}")
if not marks:
    raise SystemExit("nothing to merge")

with open(KT, newline="", encoding="utf-8", errors="replace") as f:
    rd = csv.DictReader(f)
    FIELDS = rd.fieldnames
    existing = list(rd)
print(f"\nkt_outlines.csv currently: {len(existing)} rows")

maxid = 0
for r in existing:
    try:
        maxid = max(maxid, int(float(str(r.get("id", "") or 0))))
    except Exception:
        pass
print(f"max existing id: {maxid}")

before_target = sum(1 for r in existing if r.get("batch", "").strip() == TARGET)

new = []
nid = maxid
for m in marks:
    nid += 1
    pts = m.get("points") or []
    row = {k: "" for k in FIELDS}
    row.update({
        "id": nid,
        "batch": TARGET,
        "video_file": m.get("video_file", "") or "",
        "phase": m.get("phase", "") or "",
        "channel": m.get("channel", "") or "",
        "frame": m.get("frame", "") if m.get("frame") is not None else "",
        "t_sec": m.get("t_sec", "") if m.get("t_sec") is not None else "",
        "t_hms": m.get("t_hms", "") or "",
        "nearest_event": m.get("nearest_event", "") or "",
        "type": m.get("type", "kt_outline"),
        "label": (m.get("label") or "").strip(),
        "x": m.get("x", "") if m.get("x") is not None else "",
        "y": m.get("y", "") if m.get("y") is not None else "",
        "points": json.dumps([[round(float(p[0]), 2), round(float(p[1]), 2)] for p in pts]) if pts else "",
        "w": m.get("w", "") if m.get("w") is not None else "",
        "h": m.get("h", "") if m.get("h") is not None else "",
        "crop_name": m.get("crop_name", "") or "",
        "apply_both": m.get("apply_both", 0),
        "all_frames": m.get("all_frames", 0),
        "pixel_size_um": f"{PX:.4f}",
        # shape columns stay EMPTY on purpose: kt_shape_metrics.py computes them from `points`
        "notes": (m.get("notes") or ""),
    })
    new.append(row)

tmp = KT + ".tmp_merge"
with open(tmp, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(existing)
    w.writerows(new)

# ---- verify BEFORE swapping ----------------------------------------------------------------------
with open(tmp, newline="", encoding="utf-8", errors="replace") as f:
    chk = list(csv.DictReader(f))
ok = True
if len(chk) != len(existing) + len(new):
    print(f"ABORT: row count {len(chk)} != {len(existing)}+{len(new)}"); ok = False
for a, b in zip(existing, chk[:len(existing)]):
    if a != b:
        print("ABORT: a pre-existing row changed"); ok = False; break
ids = [r.get("id") for r in chk if str(r.get("id", "")).strip()]
if len(ids) != len(set(ids)):
    print("ABORT: duplicate ids after merge"); ok = False
after_target = sum(1 for r in chk if r.get("batch", "").strip() == TARGET)
if after_target != before_target + len(new):
    print(f"ABORT: target batch rows {after_target} != {before_target}+{len(new)}"); ok = False
if not ok:
    os.remove(tmp); raise SystemExit("verification failed — nothing written")

bak = KT + ".bak_pre_localstorage_merge_20260809"
shutil.copy2(KT, bak)
os.replace(tmp, KT)
print(f"\nbackup      : {bak}")
print(f"merged      : {len(new)} traces")
print(f"{TARGET}: {before_target} -> {after_target} rows")
print(f"total rows  : {len(existing)} -> {len(chk)}")
import collections
print("merged labels:", dict(collections.Counter(r["label"] for r in new)))
