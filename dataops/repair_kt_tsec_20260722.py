"""repair_kt_tsec_20260722.py — fix the KT-tracking marks whose t_sec is the VIDEO clock.

FINDING (2026-07-22): marks saved by the 8781 KT-tracking tool (`_save_track_mark`) stored the browser's
`<video>.currentTime` — i.e. seconds into the CLIP — into `t_sec`, and left `t_hms` empty. Marks made in the
annotation slides stored the real acquisition t_sec with `t_hms` filled. Proof that the small values are
wrong: in `20260416 single ablation_15` frame 96 carries BOTH `t_sec=1986.31 (00:33:06)` and `t_sec=13.71`
(no t_hms). One frame is one instant, so the second value cannot be a time.

Consequence: any per-track TIME quantity (oscillation per 20 s, velocity, time-to-event) computed from these
rows is wrong — dt between consecutive marks came out ~0.05 s instead of ~20 s, inflating rates ~400x, which
the existing outlier caps then silently discarded.

REPAIR: `frame` is correct and frames.json is the authority for frame -> t_sec. For every affected row we
recompute t_sec (and t_hms) from its own batch's frames.json. Rows that already have a t_hms are left alone.
Nothing else in the row is touched. Runs through dataops (backup, atomic write, verify-by-re-read, audit).

Usage: python3 repair_kt_tsec_20260722.py [--apply]
"""
import csv, os, json, sys

sys.path.insert(0, "/Volumes/4 MB/dataops")
import dataops

ROOT = "/Volumes/4 MB"
KT = f"{ROOT}/annotations/kt_points.csv"
APPLY = "--apply" in sys.argv
SMALL = 120.0          # a t_sec below this with no t_hms is the clip clock, not experiment time


def drive_paths():
    rows = dataops.read(f"{ROOT}/ABLATION_MASTER.csv")
    hdr = [c.strip() for c in rows[1]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


def frame_map(path):
    """frame index -> t_sec, from the batch's frames.json. Monitoring frames are indexed from 0 within the
    monitoring role, which is the space the tracking tool's `frame` values live in."""
    if not path or not os.path.isdir(path):
        return None
    for f in sorted(os.listdir(path)):
        if f.endswith("_frames.json"):
            try:
                d = json.loads(open(os.path.join(path, f), encoding="utf-8", errors="replace").read())
            except Exception:
                return None
            mon = [x for x in d.get("frames", []) if x.get("role") == "monitoring"]
            return {i: fr["t_sec"] for i, fr in enumerate(mon)}
    return None


def hms(t):
    s = int(round(t)); sign = "-" if s < 0 else ""; s = abs(s)
    return f"{sign}{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def main():
    paths = drive_paths()
    rows = list(csv.DictReader(open(KT, encoding="utf-8", errors="replace")))
    maps, edits, skipped = {}, {}, {}
    for r in rows:
        if (r.get("t_hms") or "").strip():
            continue
        try:
            tv = float(r.get("t_sec") or "")
        except Exception:
            continue
        if tv >= SMALL:
            continue
        b = r["batch"].strip()
        if b not in maps:
            maps[b] = frame_map(paths.get(b, ""))
        fm = maps[b]
        if not fm:
            skipped[b] = skipped.get(b, 0) + 1
            continue
        try:
            fr = int(float(r["frame"]))
        except Exception:
            continue
        if fr not in fm:
            skipped[b] = skipped.get(b, 0) + 1
            continue
        t = fm[fr]
        edits[(r["id"],)] = {"t_sec": f"{t:.2f}", "t_hms": hms(t)}

    print(f"rows to repair: {len(edits)}  across {len({r for r in maps if maps[r]})} batches")
    if skipped:
        print(f"NOT repairable (no frames.json / frame out of range): "
              f"{sum(skipped.values())} rows in {len(skipped)} batches")
        for b, n in sorted(skipped.items(), key=lambda kv: -kv[1])[:8]:
            print(f"    {n:5d}  {b}")
    if not edits:
        return
    dataops.apply_edits(KT, ["id"], edits, tag="kt_tsec_repair_20260722",
                        reason=("KT-tracking marks stored the browser video clock in t_sec (clip seconds) "
                                "instead of the acquisition time, leaving t_hms empty; proven by one frame "
                                "carrying two different t_sec values. Recomputed t_sec/t_hms from the batch's "
                                "own frames.json via the row's (correct) frame index. Geometry untouched."),
                        dry_run=not APPLY)
    if not APPLY:
        print("\nDRY RUN — nothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
