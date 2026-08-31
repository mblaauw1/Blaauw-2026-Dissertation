#!/usr/bin/env python3
"""Answer the question the recall number does NOT answer (user, 2026-07-22):

  "can it make tracks that last from metaphase through anaphase for some of the kinetochores
   with high confidence?"

Recall says how many manual marks a spot sits near.  It says nothing about whether the LINKING
survives across the metaphase->anaphase transition.  This measures that directly:

  for every batch, take the master's Metaphase Start and Anaphase Onset, and for each TrackMate track
  report the fraction of the metaphase->anaphase window its own time span covers.

Reported per run: how many batches have >=1 track spanning >=90% / >=75% / >=50% of that window, and
the median longest-track coverage.

Usage: python3 score_track_spans.py <results_dir> [more dirs...]
"""
import csv, os, sys, glob
import numpy as np

ROOT = "/Volumes/4 MB"
STACKS = os.environ.get("KT_STACKS", f"{ROOT}/kt_tracking/stacks")
csv.field_size_limit(10**9)


def master():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in rows[hi]]
    out = {}
    for r in rows[hi + 1:]:
        if r and len(r) > 1 and r[0].strip():
            out[r[0].strip()] = dict(zip(hdr, r))
    return out


MR = master()


def hms(v):
    v = (v or "").strip().replace(",", "")
    if not v:
        return None
    if ":" in v:
        try: p = [float(x) for x in v.split(":")]
        except ValueError: return None
        s = 0
        for x in p:
            s = s * 60 + x
        return s
    try:
        return float(v)
    except Exception:
        return None


def timing(batch):
    """stitched stack frame -> t_sec, from the stack's own _timing.csv sidecar"""
    p = os.path.join(STACKS, batch.replace(" ", "_") + "_timing.csv")
    if not os.path.isfile(p):
        g = glob.glob(os.path.join(STACKS, batch.replace(" ", "_") + "*timing*.csv"))
        p = g[0] if g else None
    if not p:
        return None
    m = {}
    for r in csv.DictReader(open(p)):
        try:
            k = int(float(r.get("stitched_frame", r.get("frame", ""))))
            m[k] = float(r.get("t_sec"))
        except Exception:
            pass
    return m or None


for RES in sys.argv[1:]:
    rows = []
    for f in sorted(glob.glob(os.path.join(RES, "*.spots.csv"))):
        key = os.path.basename(f)[:-len(".spots.csv")]
        batch = next((b for b in MR if b.replace(" ", "_") == key), None)
        if batch is None:
            continue
        tm = timing(batch)
        r = MR[batch]
        ms, an = hms(r.get("Metaphase Start (s)") or r.get("Metaphase Start")), \
                  hms(r.get("Anaphase Onset (s)") or r.get("Anaphase Onset"))
        if tm is None or ms is None or an is None or an <= ms:
            continue
        per = {}
        for s in csv.DictReader(open(f)):
            try:
                tid = s.get("track_id") or s.get("TRACK_ID") or ""
                fr = int(float(s.get("frame", s.get("FRAME"))))
            except Exception:
                continue
            if tid in ("", "None", "-1"):
                continue
            t = tm.get(fr)
            if t is None:
                continue
            per.setdefault(tid, []).append(t)
        best = 0.0
        for tid, ts in per.items():
            lo, hi = min(ts), max(ts)
            ov = max(0.0, min(hi, an) - max(lo, ms))
            best = max(best, ov / (an - ms))
        rows.append((batch, best, len(per)))
    if not rows:
        print(f"[{os.path.basename(RES)}] no scorable batches"); continue
    b90 = sum(1 for _, c, _ in rows if c >= 0.90)
    b75 = sum(1 for _, c, _ in rows if c >= 0.75)
    b50 = sum(1 for _, c, _ in rows if c >= 0.50)
    med = float(np.median([c for _, c, _ in rows]))
    print(f"[{os.path.basename(RES)}] batches={len(rows)}  median longest-track coverage of "
          f"metaphase->anaphase = {med*100:.0f}%   >=90%: {b90}  >=75%: {b75}  >=50%: {b50}")
    for b, c, n in sorted(rows, key=lambda r: r[1])[:5]:
        print(f"     worst {c*100:5.0f}%  {n:3d} tracks  {b}")
