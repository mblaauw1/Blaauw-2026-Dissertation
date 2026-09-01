#!/usr/bin/env python3
"""Repair chromo_measure_lines.csv t_sec -- the last store still holding the browser clip clock.

Evidence: every flagged row satisfies t_sec == frame / 17.0 (the encode fps), e.g. frame 57 -> 3.35 s,
while the batch's own frames.json puts that frame minutes into the movie.  The FRAME is correct; only
the TIME is wrong (the blank-t_hms bug class, _READ_FIRST_DATA_MAP §2b).

The measure lines are drawn on the *_Phase_Ablation.mp4 clip, so the frame indexes the ABLATION role.
Time is read from each batch's own frames.json for that role; no interval is ever assumed.

Run with --apply to write.  Backs up first, verifies by re-reading.
"""
import csv, json, os, sys, shutil, datetime

ROOT = "/Volumes/4 MB"
CSVP = f"{ROOT}/annotations/chromo_measure_lines.csv"
APPLY = "--apply" in sys.argv


def drive_paths():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    hdr = [c.strip() for c in rows[1]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


DP = drive_paths()
_c = {}


def maps(batch):
    if batch in _c:
        return _c[batch]
    out = {}
    p = DP.get(batch)
    if p and os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if f.endswith("_frames.json"):
                try:
                    d = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
                except Exception:
                    break
                for role in ("monitoring", "ablation", "pre"):
                    sub = [x for x in d.get("frames", []) if x.get("role") == role]
                    if sub:
                        out[role] = {i: fr["t_sec"] for i, fr in enumerate(sub)}
                break
    _c[batch] = out
    return out


def role_of(url):
    s = (url or "").lower()
    if "_ablation" in s:
        return "ablation"
    if "_pre" in s:
        return "pre"
    return "monitoring"


# These five were re-rendered AFTER their frames.json was written, so their sidecar disagrees with
# their own movie (NOTES §8).  For them the FILM is the record -- never write a frames.json time.
STALE = {"20260420 ptk2 eyfp cdc20 1 ablation_11", "20260420 ptk2 eyfp cdc20 1 ablation_13",
         "20260420 ptk2 eyfp cdc20 1 ablation_18", "20260420 ptk2 eyfp cdc20 1 ablation_20",
         "20260420 ptk2 eyfp cdc20 1 ablation_43"}

rows = list(csv.DictReader(open(CSVP)))
hdr = list(rows[0].keys())
fixed, skipped, unchanged = [], [], 0
for r in rows:
    b, fr, url = r["batch"], r.get("frame", ""), r.get("video_url", "")
    try:
        fi = int(float(fr))
    except Exception:
        skipped.append((b, fr, "no frame")); continue
    # 2026-07-22 (later): those five sidecars were rebuilt FROM THE FILM, so they are now the record
    # and no longer have to be held back.
    m = maps(b).get(role_of(url))
    if not m or fi not in m:
        skipped.append((b, fr, "no frames.json entry for role " + role_of(url))); continue
    new = round(float(m[fi]), 2)
    old = r.get("t_sec", "")
    try:
        same = abs(float(old) - new) < 0.02
    except Exception:
        same = False
    if same:
        unchanged += 1; continue
    fixed.append((r["id"], b, fi, old, new, role_of(url)))
    r["t_sec"] = f"{new:.2f}"

print(f"rows={len(rows)}  to_fix={len(fixed)}  already_correct={unchanged}  skipped={len(skipped)}")
for f in fixed[:10]:
    print("   id=%s %s frame=%s  %s -> %s  (%s)" % f)
if skipped:
    print("  skipped examples:", skipped[:5])

if APPLY and fixed:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{ROOT}/_master_backups/chromo_measure_lines_pre_tsec_repair_{ts}.csv"
    shutil.copy(CSVP, bak)
    tmp = CSVP + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr); w.writeheader(); w.writerows(rows)
    os.replace(tmp, CSVP)
    chk = list(csv.DictReader(open(CSVP)))
    ok = sum(1 for a, b in zip(chk, rows) if a["t_sec"] == b["t_sec"])
    print(f"WROTE {CSVP}  backup={bak}  verified {ok}/{len(rows)} rows match")
elif not APPLY:
    print("(dry run -- pass --apply to write)")
