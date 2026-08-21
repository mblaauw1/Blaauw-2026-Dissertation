#!/usr/bin/env python3
"""Do the TrackMate tracks actually cover anaphase -> anaphase+5 min / +10 min? (user, 2026-07-22)

For every batch in a results dir: take Anaphase Onset from the master, map each track's spots to real
time via the stack's own `_timing.csv`, and count the tracks whose OWN span covers the whole window
[anaphase, anaphase+N min] -- i.e. a track you could follow continuously across that window, not a
track that merely has a spot somewhere inside it.

Also reports partial coverage, because a track that covers 80% of the window is still usable for most
measurements and a strict all-or-nothing count would hide that.

Usage: python3 score_anaphase_window.py <results_dir> [more dirs...]
       KT_STACKS=/Volumes/4 MB/kt_tracking/stacks_long  (set this for the long-window runs)
"""
import csv, os, sys, glob
import numpy as np

ROOT = "/Volumes/4 MB"
STACKS = os.environ.get("KT_STACKS", f"{ROOT}/kt_tracking/stacks")
csv.field_size_limit(10 ** 9)


def master():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in rows[hi]]
    return {r[0].strip(): dict(zip(hdr, r)) for r in rows[hi + 1:] if r and r[0].strip()}


MR = master()


def hms(v):
    v = (v or "").strip().replace(",", "")
    if not v:
        return None
    if ":" in v:
        try:
            p = [float(x) for x in v.split(":")]
        except ValueError:
            return None
        s = 0.0
        for x in p:
            s = s * 60 + x
        return -s if v.strip().startswith("-") and s > 0 and p[0] == 0 else s
    try:
        return float(v)
    except ValueError:
        return None


def timing(batch):
    p = os.path.join(STACKS, batch.replace(" ", "_") + "_timing.csv")
    if not os.path.isfile(p):
        return None
    m = {}
    for r in csv.DictReader(open(p)):
        try:
            m[int(float(r.get("stitched_frame", r.get("frame", ""))))] = float(r["t_sec"])
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
        an = hms(MR[batch].get("Anaphase Onset (s)"))
        if tm is None or an is None:
            continue
        tmax = max(tm.values())
        per = {}
        for s in csv.DictReader(open(f)):
            tid = s.get("track_id") or s.get("TRACK_ID") or ""
            if tid in ("", "None", "-1"):
                continue
            try:
                t = tm.get(int(float(s.get("frame", s.get("FRAME")))))
            except Exception:
                continue
            if t is not None:
                per.setdefault(tid, []).append(t)
        out = {"batch": batch, "tmax_after_ana": tmax - an, "n_tracks": len(per)}
        for mins in (5, 10):
            end = an + mins * 60
            full = sum(1 for ts in per.values() if min(ts) <= an + 20 and max(ts) >= end - 20)
            best = 0.0
            for ts in per.values():
                ov = max(0.0, min(max(ts), end) - max(min(ts), an))
                best = max(best, ov / (end - an))
            out[f"full{mins}"] = full
            out[f"best{mins}"] = best
            out[f"reach{mins}"] = tmax >= end - 20
        rows.append(out)
    if not rows:
        print(f"[{os.path.basename(RES)}] nothing scorable"); continue
    print(f"\n[{os.path.basename(RES)}]  {len(rows)} batches with an anaphase time and a timing sidecar")
    for mins in (5, 10):
        have = [r for r in rows if r[f"reach{mins}"]]
        withtrack = [r for r in have if r[f"full{mins}"] > 0]
        med = float(np.median([r[f"best{mins}"] for r in have])) if have else 0
        tot = sum(r[f"full{mins}"] for r in have)
        print(f"  anaphase -> +{mins:2d} min : {len(have):3d} batches are imaged that long; "
              f"{len(withtrack):3d} have >=1 track spanning the WHOLE window "
              f"({tot} such tracks in total); median best-track coverage {med*100:.0f}%")
    print("  worst 5 by best-track coverage of the +10 min window:")
    for r in sorted([r for r in rows if r["reach10"]], key=lambda r: r["best10"])[:5]:
        print(f"     {r['best10']*100:5.0f}%  full={r['full10']:2d}  {r['batch']}")
