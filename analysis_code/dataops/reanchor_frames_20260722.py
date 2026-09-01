"""reanchor_frames_20260722.py — re-anchor annotation `frame` indices onto each batch's real frames.json.

WHY: ANNOTATION_FRAME_MISMATCH_AUDIT_20260720.csv listed 22 batches whose annotation `frame` values run past
the movie's frame count. The stored `t_sec` is the trustworthy value (it is what the annotation UI recorded);
the frame INDEX was computed against a different/assumed fps. So: for each row, find the frames.json frame
whose t_sec is closest and rewrite `frame` to that index. `t_sec` and geometry are never touched.

SAFETY: a batch is only re-anchored when EVERY one of its rows matches a frame within
`TOL_FRAC` x the batch's median frame spacing — i.e. the mapping is unambiguous. Batches that fail that
test are reported and left alone; they need a human (a wrong-cell trace or a genuinely different movie),
not an automatic remap. All writes go through dataops.apply_edits (backup + atomic + verify-by-re-read).

Usage:  python3 reanchor_frames_20260722.py [--apply]
"""
import csv, os, json, sys, statistics

sys.path.insert(0, "/Volumes/4 MB/dataops")
import dataops

ROOT = "/Volumes/4 MB"
AUDIT = f"{ROOT}/ANNOTATION_FRAME_MISMATCH_AUDIT_20260720.csv"
TOL_FRAC = 0.4          # |dt| must be < 0.4 * median frame spacing => nearest frame is unambiguous
APPLY = "--apply" in sys.argv


def drive_paths():
    rows = dataops.read(f"{ROOT}/ABLATION_MASTER.csv")
    hdr = [c.strip() for c in rows[1]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


def frames_of(path):
    if not path or not os.path.isdir(path):
        return None, "no output dir"
    for f in sorted(os.listdir(path)):
        if f.endswith("_frames.json"):
            try:
                d = json.loads(open(os.path.join(path, f), encoding="utf-8", errors="replace").read())
            except Exception as e:
                return None, f"frames.json unreadable ({type(e).__name__})"
            return [fr["t_sec"] for fr in d["frames"]], None
    return None, "no frames.json"


def main():
    paths = drive_paths()
    ok, deferred = {}, []
    for a in csv.DictReader(open(AUDIT)):
        b, af = a["batch"], a["annotation_file"]
        ts, err = frames_of(paths.get(b, ""))
        if ts is None:
            deferred.append((af, b, err)); continue
        spacing = statistics.median([j - i for i, j in zip(ts, ts[1:])]) if len(ts) > 1 else 0
        tol = max(TOL_FRAC * spacing, 0.05)
        src = f"{ROOT}/annotations/{af}.csv"
        changes, worst = {}, 0.0
        for r in csv.DictReader(open(src)):
            if r["batch"].strip() != b:
                continue
            try:
                f0, t = int(float(r["frame"])), float(r["t_sec"])
            except Exception:
                continue
            j = min(range(len(ts)), key=lambda k: abs(ts[k] - t))
            worst = max(worst, abs(ts[j] - t))
            if j != f0:
                changes[(r["id"],)] = {"frame": str(j)}
        if worst > tol:
            deferred.append((af, b, f"max |dt| {worst:.1f}s > tol {tol:.1f}s (spacing {spacing:.1f}s)"))
            continue
        if changes:
            ok.setdefault(af, {}).update(changes)
            print(f"  RE-ANCHOR {af:14s} {b:52s} {len(changes):3d} rows  (max |dt| {worst:.3f}s, tol {tol:.1f}s)")

    print("\nDEFERRED — not re-anchored, needs a human:")
    for af, b, why in deferred:
        print(f"  {af:14s} {b:52s} {why}")

    for af, edits in ok.items():
        path = f"{ROOT}/annotations/{af}.csv"
        print(f"\n=== {af}: {len(edits)} rows ===")
        dataops.apply_edits(path, ["id"], edits, tag="frame_reanchor_20260722",
                            reason=("ANNOTATION_FRAME_MISMATCH_AUDIT_20260720: frame index was computed against "
                                    "the wrong fps and ran past the movie length. Re-anchored to the frames.json "
                                    "frame with the matching t_sec (unambiguous: |dt| < 0.4x frame spacing). "
                                    "t_sec and geometry unchanged."),
                            dry_run=not APPLY)
    if not APPLY:
        print("\nDRY RUN — nothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
