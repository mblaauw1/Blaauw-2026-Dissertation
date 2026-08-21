"""repair_metaplate_tsec_20260722.py — fix meta_plates rows whose t_sec is the VIDEO CLIP clock.

FINDING (2026-07-22): `annotations/meta_plates.csv` carries the SAME bug that was repaired in kt_points
earlier the same day, and was never touched. Evidence:
  * 3856 of 4183 rows (92%) have a BLANK t_hms — the fingerprint of the clip-clock write.
    (kt_points is now 0% blank; cell_outlines is 0% blank.)
  * Those rows' t_sec equals frame / (that movie's fps) — seconds into the CLIP, not experiment time.
  * Per-video frame->t_sec rates come out at ~0.03-0.05 s/frame where the real acquisition interval is
    20-503 s (intervals VARY per batch — user, 2026-07-22: "in reality it can be more like 30s or greater,
    varying between batches", so a '20 s multiple' check is meaningless and is NOT used here).

WHAT IS AND IS NOT TOUCHED
  ONLY `t_sec` and `t_hms` change. The polyline in `points`, the `frame`, batch, video_file and label are
  untouched. The plate SHAPE — the actual measurement — is not modified in any way.
  Rows that already carry a t_hms are skipped entirely (they are the uncorrupted ones).

THE AUTHORITY FOR TIME (process.py:863, the real pipeline)
      t_sec = (file_frame_times[t_index] - timestamp_anchor_ms) / 1000
  t_sec is 0 at the FIRST ABLATION EVENT (timestamp_anchor_ms = ablation_events[0].epoch_ms - abl_start_ms)
  and negative before it; the per-frame times come from the TIFF/MicroManager metadata. The pipeline BURNS
  that value onto every frame as HH:MM:SS (int() truncation, not rounding).

TWO SOURCES, BOTH RECORDS — NOTHING IS FITTED OR INFERRED
  A. frames.json (64 batches, 3709 rows). The batch's own sidecar maps monitoring frame index -> t_sec.
     VERIFIED against the burned-in timestamps in the movies the marks were actually made on: mp4 frame N
     shows exactly the time frames.json gives for monitoring entry N (checked across batches; agreement is
     exact to the 1 s truncation).
  B. FILM_TIMES (5 batches, 147 rows) — the five 20260420 batches whose frames.json DISAGREES with their
     own movie (frames.json says ~00:08:49 at frame 30 where the film reads 00:15:09). Those batches were
     re-rendered after their frames.json was written, so for them the FILM is the record. Every one of the
     147 annotated frames was read directly off the movie; none is interpolated. Read 2026-07-22 from
     <batch>_Fluor_Monitoring.mp4 in pipeline_session_output.

  Both of these movies show real acquisition GAPS (e.g. ablation_13 jumps 00:19:29 -> 00:23:00 between
  frames 43 and 44). Those gaps are why a constant-interval model would be wrong, and why every frame was
  read individually rather than extrapolated.

Usage: python3 repair_metaplate_tsec_20260722.py [--apply]
"""
import csv, os, json, sys

sys.path.insert(0, "/Volumes/4 MB/dataops")
import dataops

ROOT = "/Volumes/4 MB"
MP = f"{ROOT}/annotations/meta_plates.csv"
APPLY = "--apply" in sys.argv


def drive_paths():
    rows = dataops.read(f"{ROOT}/ABLATION_MASTER.csv")
    hdr = [c.strip() for c in rows[1]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[2:] if r and len(r) > pi and r[bi].strip()}


def frame_map(path):
    """monitoring frame index -> t_sec, from the batch's own frames.json sidecar."""
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
    """MUST match process.py's overlay: truncation, not rounding."""
    s = int(t); sign = "-" if s < 0 else ""; s = abs(s)
    return f"{sign}{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def _t(h, m, s):
    return h * 3600 + m * 60 + s


# ---------------------------------------------------------------------------------------------------
# FILM_TIMES — read directly off each movie's burned-in timestamp, frame by frame (see header, source B).
# frame -> seconds. Every value below was READ, not computed.
# ---------------------------------------------------------------------------------------------------
FILM_TIMES = {
 "20260420 ptk2 eyfp cdc20 1 ablation_13": {
   30:_t(0,15,9), 32:_t(0,15,49), 33:_t(0,16,9), 34:_t(0,16,29), 35:_t(0,16,49), 36:_t(0,17,9),
   37:_t(0,17,29), 38:_t(0,17,49), 39:_t(0,18,9), 40:_t(0,18,30), 41:_t(0,18,49), 42:_t(0,19,9),
   43:_t(0,19,29), 44:_t(0,23,0), 45:_t(0,23,19), 46:_t(0,23,39), 47:_t(0,23,59), 48:_t(0,24,19),
   49:_t(0,24,39), 50:_t(0,24,59), 51:_t(0,25,19), 52:_t(0,25,39), 53:_t(0,25,59), 54:_t(0,26,19),
   55:_t(0,26,39), 56:_t(0,26,59), 57:_t(0,27,19), 58:_t(0,27,39), 59:_t(0,27,59), 60:_t(0,28,19),
   61:_t(0,28,39), 62:_t(0,28,59), 63:_t(0,29,19)},
 "20260420 ptk2 eyfp cdc20 1 ablation_20": {
   1:_t(0,12,57), 4:_t(0,15,8), 5:_t(0,15,52), 6:_t(0,19,11), 7:_t(0,19,55), 8:_t(0,20,38),
   9:_t(0,21,21), 10:_t(0,22,4), 11:_t(0,22,48), 12:_t(0,23,31), 13:_t(0,24,15), 14:_t(0,24,58),
   15:_t(0,25,42), 16:_t(0,26,25), 17:_t(0,27,8), 18:_t(0,27,52), 19:_t(0,28,35), 20:_t(0,29,19),
   21:_t(0,30,2)},
 "20260420 ptk2 eyfp cdc20 1 ablation_43": {
   6:_t(0,6,15), 7:_t(0,7,7), 8:_t(0,7,59), 9:_t(0,8,51), 10:_t(0,9,42), 11:_t(0,10,34),
   12:_t(0,11,26), 13:_t(0,12,18), 14:_t(0,13,10), 15:_t(0,14,2), 16:_t(0,14,53), 17:_t(0,15,45),
   18:_t(0,16,36), 19:_t(0,17,28), 20:_t(0,18,20), 21:_t(0,19,12), 22:_t(0,20,4), 23:_t(0,20,56),
   24:_t(0,21,48), 25:_t(0,22,41), 26:_t(0,23,33), 27:_t(0,24,25), 28:_t(0,25,17), 29:_t(0,26,9),
   30:_t(0,27,2), 31:_t(0,27,55), 32:_t(0,28,47), 33:_t(0,29,39), 34:_t(0,30,31), 35:_t(0,31,23)},
 "20260420 ptk2 eyfp cdc20 1 ablation_11": {
   24:_t(0,14,41), 25:_t(0,15,0), 26:_t(0,15,20), 27:_t(0,15,41), 28:_t(0,16,0), 29:_t(0,16,21),
   30:_t(0,16,41), 31:_t(0,17,1), 32:_t(0,17,20), 33:_t(0,17,41), 34:_t(0,18,0), 35:_t(0,18,20),
   36:_t(0,18,41), 37:_t(0,19,0), 38:_t(0,19,21), 39:_t(0,19,41), 40:_t(0,20,2), 41:_t(0,20,21),
   42:_t(0,20,40), 43:_t(0,21,1), 44:_t(0,24,31), 45:_t(0,24,51), 46:_t(0,25,11), 47:_t(0,25,31),
   48:_t(0,25,51), 49:_t(0,26,11), 50:_t(0,26,31), 51:_t(0,26,51), 52:_t(0,27,11), 53:_t(0,27,31),
   54:_t(0,27,51), 55:_t(0,28,11), 56:_t(0,28,31), 57:_t(0,28,51), 58:_t(0,29,11), 59:_t(0,29,31),
   60:_t(0,29,51)},
 "20260420 ptk2 eyfp cdc20 1 ablation_18": {
   34:_t(0,13,41), 35:_t(0,14,1), 36:_t(0,14,22), 37:_t(0,14,41), 38:_t(0,15,1), 39:_t(0,15,21),
   40:_t(0,15,41), 41:_t(0,16,1), 42:_t(0,16,21), 43:_t(0,16,41), 44:_t(0,17,1), 45:_t(0,17,21),
   46:_t(0,17,41), 47:_t(0,18,1), 48:_t(0,18,21), 49:_t(0,18,41), 50:_t(0,19,1), 51:_t(0,19,21),
   52:_t(0,19,41), 53:_t(0,20,1), 54:_t(0,20,21), 55:_t(0,20,41), 56:_t(0,21,1), 57:_t(0,21,21),
   58:_t(0,21,41), 59:_t(0,22,1), 60:_t(0,22,21), 61:_t(0,22,41)},
}


def main():
    paths = drive_paths()
    rows = list(csv.DictReader(open(MP, encoding="utf-8", errors="replace")))
    maps, edits = {}, {}
    src_count = {"frames.json": 0, "film": 0}
    skipped = {}

    for r in rows:
        # Re-derive only rows this repair itself wrote (t_hms present but inconsistent with t_sec)
        # or rows still blank. Rows whose t_hms was already there and self-consistent are left alone.
        th = (r.get("t_hms") or "").strip()
        if th:
            try:
                if th == hms(round(float(r["t_sec"]), 2)):
                    continue
            except Exception:
                continue
        b = r["batch"].strip()
        try:
            fr = int(float(r["frame"]))
        except Exception:
            skipped[b] = skipped.get(b, 0) + 1
            continue

        t, src = None, None
        film = FILM_TIMES.get(b)
        if film is not None:                          # film overrides: its frames.json is stale
            if fr in film:
                t, src = float(film[fr]), "film"
        else:
            if b not in maps:
                maps[b] = frame_map(paths.get(b, ""))
            fm = maps[b]
            if fm and fr in fm:
                t, src = float(fm[fr]), "frames.json"

        if t is None:
            skipped[b] = skipped.get(b, 0) + 1
            continue
        src_count[src] += 1
        # KEY ON (id, frame), NOT id alone: meta_plates carries 89 duplicate ids (217 rows) left
        # over from the 2026-07-22 probe-POST renumbering, and keying on id alone silently
        # skipped 73 rows. (id, frame) is unique across every row in the store.
        # t_hms MUST be derived from the SAME rounded value that gets written to t_sec. Deriving it
        # from the raw float put 48 rows one second out (t_sec 1564.00 with t_hms 00:26:03, because
        # the underlying value was 1563.9999 and int() truncates).
        tr = round(t, 2)
        edits[(r["id"], r["frame"])] = {"t_sec": f"{tr:.2f}", "t_hms": hms(tr)}

    print(f"rows to repair: {len(edits)}")
    print(f"   from frames.json (verified against the burned-in timestamps): {src_count['frames.json']}")
    print(f"   read directly off the film (5 re-rendered batches):           {src_count['film']}")
    if skipped:
        print(f"NOT repairable: {sum(skipped.values())} rows in {len(skipped)} batches")
        for b, n in sorted(skipped.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {n:5d}  {b}")
    if not edits:
        return
    dataops.apply_edits(MP, ["id", "frame"], edits, tag="metaplate_tsec_repair_20260722",
                        reason=("meta_plates rows stored the browser video-clip clock in t_sec and left "
                                "t_hms blank (92% of rows) — the same bug repaired in kt_points on "
                                "2026-07-22. t_sec/t_hms recomputed from each batch's own frames.json, or "
                                "for 5 re-rendered 20260420 batches read frame-by-frame off the movie's "
                                "burned-in timestamp. Plate polylines, frames and labels untouched."),
                        dry_run=not APPLY)
    if not APPLY:
        print("\nDRY RUN — nothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
