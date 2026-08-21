#!/usr/bin/env python3
"""Fix the metaphase-plate lines that sit on the wrong frame (user report, 2026-07-22:
"20250403 ptk_yfpcdc20_22 has polar kinetochore annotations ... on the wrong frame ... this persists
through many of the single ablation movies").

DIAGNOSIS (measured, not assumed)
  There are two separate time bugs (_READ_FIRST_DATA_MAP §2b):
    blank t_hms -> the TIME is the browser clip clock, the FRAME is right
    has  t_hms  -> the TIME is right, the FRAME is stale from an older render
  Today's kt_points t_sec repair rewrote t_sec from the frame for BOTH groups.  For the 416 rows in
  the second group that inverted the good value: e.g. 20250403 ptk_yfpcdc20_22 polar id=583 held
  t=113.77 (00:01:53, correct) and frame=10; the repair rewrote it to 313.82 -- exactly +10 frames of
  20 s.  So those marks were already 10 frames off, and the repair hid the offset instead of fixing it.

FIX
  For rows that HAD a t_hms before the repair: restore the original t_sec/t_hms (the correct value)
  and re-anchor `frame` to the frames.json entry whose t_sec matches, only where the match is
  unambiguous (|dt| < 0.4 x frame spacing).  Ambiguous rows are left alone and listed.

Run with --apply.  Backs up, writes atomically, verifies by re-reading.
"""
import csv, json, os, sys, shutil, datetime
from collections import defaultdict

ROOT = "/Volumes/4 MB"
CUR = f"{ROOT}/annotations/meta_plates.csv"
BAK = f"{ROOT}/_master_backups/meta_plates_pre_tsec_repair_20260722.csv"
APPLY = "--apply" in sys.argv
csv.field_size_limit(10**9)

STALE = {"20260420 ptk2 eyfp cdc20 1 ablation_11", "20260420 ptk2 eyfp cdc20 1 ablation_13",
         "20260420 ptk2 eyfp cdc20 1 ablation_18", "20260420 ptk2 eyfp cdc20 1 ablation_20",
         "20260420 ptk2 eyfp cdc20 1 ablation_43"}


def drive_paths():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    h = [c.strip() for c in rows[1]]
    bi, pi = h.index("Batch Name"), h.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


DP = drive_paths()
_c = {}


def role_map(batch, role):
    key = (batch, role)
    if key in _c:
        return _c[key]
    out = None
    p = DP.get(batch)
    if p and os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if f.endswith("_frames.json"):
                try:
                    d = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
                except Exception:
                    break
                sub = [x for x in d.get("frames", []) if x.get("role") == role]
                if sub:
                    out = {i: float(fr["t_sec"]) for i, fr in enumerate(sub)}
                break
    _c[key] = out
    return out


ROLE = {"mon": "monitoring", "abl": "ablation", "pre": "pre"}
old = list(csv.DictReader(open(BAK)))
cur = list(csv.DictReader(open(CUR)))
hdr = list(cur[0].keys())
ko = {(r["id"], r["frame"], r["batch"], r["label"]): r for r in old}

restored, reanchored, ambiguous, nomap = 0, 0, [], []
for r in cur:
    o = ko.get((r["id"], r["frame"], r["batch"], r["label"]))
    if not o or not str(o.get("t_hms", "")).strip():
        continue
    try:
        if abs(float(o["t_sec"]) - float(r["t_sec"])) < 0.02:
            continue
    except Exception:
        continue
    # 2026-07-22 (later): those five sidecars were rebuilt FROM THE FILM, so they are the record now.
    # 1. the original time was the correct one
    r["t_sec"], r["t_hms"] = o["t_sec"], o["t_hms"]
    restored += 1
    # 2. move the mark to the frame that actually carries that time
    m = role_map(r["batch"], ROLE.get(r.get("phase", ""), "monitoring"))
    if not m:
        nomap.append((r["batch"], r["id"])); continue
    t = float(o["t_sec"])
    fr = sorted(m)
    sp = sorted(abs(m[b] - m[a]) for a, b in zip(fr, fr[1:]))
    spacing = sp[len(sp) // 2] if sp else 0
    best = min(m, key=lambda i: abs(m[i] - t))
    if spacing and abs(m[best] - t) < 0.4 * spacing:
        if str(best) != str(r["frame"]):
            r["frame"] = str(best); reanchored += 1
    else:
        ambiguous.append((r["batch"], r["id"], f"no frame within 0.4x spacing (dt={abs(m[best]-t):.1f}s)"))

print(f"rows={len(cur)}  times_restored={restored}  frames_reanchored={reanchored}  "
      f"ambiguous={len(ambiguous)}  no_frames_json={len(nomap)}")
for a in ambiguous[:8]:
    print("   ambiguous:", a)

if APPLY and restored:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    b = f"{ROOT}/_master_backups/meta_plates_pre_reanchor_{ts}.csv"
    shutil.copy(CUR, b)
    tmp = CUR + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(cur)
    os.replace(tmp, CUR)
    chk = list(csv.DictReader(open(CUR)))
    ok = sum(1 for a, b2 in zip(chk, cur) if a["t_sec"] == b2["t_sec"] and a["frame"] == b2["frame"])
    print(f"WROTE {CUR}  backup={b}  verified {ok}/{len(cur)}")
elif not APPLY:
    print("(dry run -- pass --apply to write)")
