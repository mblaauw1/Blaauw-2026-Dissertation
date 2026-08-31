#!/usr/bin/env python3
"""Audit EVERY annotation store for the clip-clock t_sec bug found in kt_points and meta_plates.

Fingerprint (documented in _READ_FIRST_DATA_MAP §2b): t_hms blank AND a frame->t_sec rate far below
the batch's real acquisition interval, because the browser wrote video-clip seconds (~17 fps).
The real interval is NOT 20 s -- it is read per batch from that batch's own *_frames.json, never assumed.

Report only; changes nothing.  Writes _scratch/tsec_suspect_<store>.csv for anything flagged.
"""
import csv, json, os, sys
from collections import defaultdict

ROOT = "/Volumes/4 MB"
ANN = f"{ROOT}/annotations"
STORES = ["kt_points", "meta_plates", "cell_outlines", "chromo_lines", "lagging_lengths",
          "kt_outlines", "crop_boxes", "polar_tracks", "poles", "timestrip_frames",
          "batch_meta", "misc", "chromo_measure_lines"]

csv.field_size_limit(10**9)


def drive_paths():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    hdr = [c.strip() for c in rows[1]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


DP = drive_paths()
_cache = {}


def role_rates(batch):
    """role -> median seconds per frame, from the batch's own frames.json"""
    if batch in _cache:
        return _cache[batch]
    out = {}
    p = DP.get(batch)
    if p and os.path.isdir(p):
        for f in sorted(os.listdir(p)):
            if f.endswith("_frames.json"):
                try:
                    d = json.loads(open(os.path.join(p, f), encoding="utf-8", errors="replace").read())
                except Exception:
                    break
                by = defaultdict(list)
                for fr in d.get("frames", []):
                    if fr.get("t_sec") is not None:
                        by[fr.get("role") or "?"].append(float(fr["t_sec"]))
                for role, ts in by.items():
                    ds = sorted(abs(b - a) for a, b in zip(ts, ts[1:]))
                    if ds:
                        out[role] = ds[len(ds) // 2]
                break
    _cache[batch] = out
    return out


def obs_rate(rows):
    pts = sorted((int(float(r["frame"])), float(r["t_sec"])) for r in rows)
    ds = sorted(abs((b[1] - a[1]) / (b[0] - a[0])) for a, b in zip(pts, pts[1:]) if b[0] != a[0])
    return ds[len(ds) // 2] if ds else None


report = []
for st in STORES:
    p = f"{ANN}/{st}.csv"
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p)))
    if not rows or "t_sec" not in rows[0]:
        report.append((st, len(rows), 0, 0, 0, "no t_sec column")); continue
    usable = [r for r in rows
              if str(r.get("t_sec", "")).strip() not in ("", "None")
              and str(r.get("frame", "")).strip() not in ("", "None")]
    blank_hms = sum(1 for r in rows if "t_hms" in r and not str(r.get("t_hms", "")).strip())
    grp = defaultdict(list)
    for r in usable:
        grp[(r.get("batch", ""), r.get("phase", ""))].append(r)
    susp, srows, checked = [], 0, 0
    for (batch, phase), g in grp.items():
        rt = obs_rate(g)
        if rt is None:
            continue
        checked += 1
        rr = role_rates(batch)
        # annotation `phase` is abbreviated; frames.json spells the role out
        ROLE = {"abl": "ablation", "mon": "monitoring", "pre": "pre", "": None}
        want = ROLE.get(phase, phase)
        real = rr.get(want) if want else None
        if real is None:
            real = rr.get("monitoring") or (max(rr.values()) if rr else None)
        if real and real > 1 and rt < real * 0.25:
            susp.append((batch, phase, round(rt, 3), round(real, 1), len(g))); srows += len(g)
        elif not real and rt and rt < 0.3:
            susp.append((batch, phase, round(rt, 3), "", len(g))); srows += len(g)
    report.append((st, len(rows), blank_hms, len(susp), srows, f"{checked} groups checked"))
    if susp:
        with open(f"{ROOT}/_scratch/tsec_suspect_{st}.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["batch", "phase", "observed_s_per_frame", "real_s_per_frame", "n_rows"])
            w.writerows(sorted(susp))

print(f"{'store':22s} {'rows':>7s} {'blank_t_hms':>12s} {'susp_grp':>9s} {'susp_rows':>10s}  note")
for r in report:
    print(f"{r[0]:22s} {r[1]:7d} {r[2]:12d} {r[3]:9d} {r[4]:10d}  {r[5]}")
