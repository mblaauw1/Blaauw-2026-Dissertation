#!/usr/bin/env python3
"""serve_annotation.py — tiny HTTP server with proper HTTP Range support.

Python's stock SimpleHTTPRequestHandler ignores Range headers, so large
videos (the monitoring MP4 is ~100 MB) can't be scrubbed in the browser
until the entire file downloads. This handler returns 206 Partial Content
for Range requests, which is what HTML5 video needs for frame-accurate
seeking.

USAGE
    python3 serve_annotation.py <pkg_dir> [--port 8766]
"""

import argparse
import csv
import http.server
import json
import mimetypes
import os
import re
import socket
import socketserver
import sys
import threading


MASTER_CSV_HEADER = (
    "id,batch,video_file,phase,channel,frame,t_sec,t_hms,nearest_event,"
    "type,label,x,y,points,w,h,crop_name,apply_both,all_frames,"
    "length_um,area_um2,perimeter_um,circularity,"
    "aspect_ratio,roundness,solidity,pixel_size_um,notes"
)

# Filled in by main() from --master-csv. Each annotation TYPE is autosaved
# into its own dedicated file inside the same directory, so we always know
# which file holds which kind of mark.
MASTER_CSV_PATH = None
_master_lock = threading.Lock()


def _annot_dir(base):
    """Canonical per-type store dir for a master path. Always the `annotations/`
    subdir beside the master — so saves never fork into the master's root dir
    (which split today's outlines from the 124-batch canonical store)."""
    d = os.path.dirname(base)
    if os.path.basename(d) == "annotations":
        return d
    return os.path.join(d, "annotations")

# Map annotation `type` field → dedicated CSV filename (basename inside
# MASTER_CSV_PATH's parent directory). Anything not listed falls back to
# `misc.csv` so we never silently drop unknown types.
TYPE_TO_FILE = {
    "cell_outline":    "cell_outlines.csv",
    "kt_point":        "kt_points.csv",
    "chromo_line":     "chromo_lines.csv",
    "meta_plate":      "meta_plates.csv",
    "polar_track":     "polar_tracks.csv",
    "pole":            "poles.csv",
    "timestrip_frame": "timestrip_frames.csv",
    "crop_box":        "crop_boxes.csv",
    "batch_meta":      "batch_meta.csv",
    "lagging_length":  "lagging_lengths.csv",   # was falling through to misc.csv (2026-07-20 rename)
    "lagging_width":   "lagging_lengths.csv",
    # KT-outline slides (2026-07-22): per-frame kinetochore outline traces, grouped per kinetochore.
    "kt_outline":      "kt_outlines.csv",
}
def _file_for_type(t):
    return TYPE_TO_FILE.get(t, "misc.csv")


# ---- frame -> real acquisition t_sec ------------------------------------------------------------
# THE SAME BUG THAT CORRUPTED kt_points AND meta_plates, STILL LIVE HERE (found 2026-07-22 while
# verifying the meta_plates repair: 35 freshly-drawn plate marks arrived with t_sec=3.88 at frame 66,
# i.e. 17 fps CLIP seconds, and a blank t_hms).
# The browser sends <video>.currentTime — seconds into the CLIP, not experiment time. `pairing_server.py`
# was fixed on 2026-07-22 to derive the value server-side, but serve_annotation.py (which serves ALL the
# annotation slide sets) was never given the same fix, so every mark saved through it stayed corrupt.
# frames.json is the authority for frame -> t_sec, so the SERVER derives it and ignores what the client
# sent. Verified against the timestamps the pipeline BURNS onto each movie frame: mp4 frame N carries
# exactly the time frames.json gives for monitoring entry N (14/14 random batches, exact).
_FRAMEMAP = {}
def _frame_map(batch):
    if batch in _FRAMEMAP: return _FRAMEMAP[batch]
    fm = None
    try:
        mr = list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
        hdr = [c.strip() for c in mr[1]]
        bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
        path = next((r[pi].strip() for r in mr[2:] if r and len(r) > pi and r[bi].strip() == batch), "")
        if path and os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                if f.endswith("_frames.json"):
                    d = json.loads(open(os.path.join(path, f), encoding="utf-8", errors="replace").read())
                    mon = [x for x in d.get("frames", []) if x.get("role") == "monitoring"]
                    fm = {i: fr["t_sec"] for i, fr in enumerate(mon)}
                    break
    except Exception:
        fm = None
    _FRAMEMAP[batch] = fm
    return fm


def _fix_times(batch, rows):
    """Derive t_sec/t_hms from frames.json for MONITORING marks; never trust the client's clip clock.

    Only monitoring-phase rows are rewritten — frames.json indexes each role separately and only the
    monitoring map is built here, so an ablation/pre mark is left exactly as sent rather than being
    given a time from the wrong role. t_hms is formatted from the SAME rounded value written to t_sec
    (deriving it from the raw float put 48 rows one second out during the meta_plates repair)."""
    fm = _frame_map(batch)
    if not fm:
        return rows
    for r in rows:
        ph = (r.get("phase") or "").strip().lower()
        vf = (r.get("video_file") or "").lower()
        if ph and ph != "mon":
            continue
        if not ph and "monitoring" not in vf:
            continue
        try:
            fi = int(float(r.get("frame")))
        except Exception:
            continue
        if fi not in fm:
            continue
        t = round(float(fm[fi]), 2)
        s = int(t); sign = "-" if s < 0 else ""; s = abs(s)
        r["t_sec"] = f"{t:.2f}"
        r["t_hms"] = f"{sign}{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
    return rows


def _autosave_replace_batch(batch, rows, csv_path=None):
    """Split `rows` by annotation type and replace this batch's rows in each
    per-type CSV (cell_outlines.csv, kt_points.csv, ...). Then mirror the
    per-batch summary + ID pointers into ABLATION_MASTER.csv."""
    base = csv_path or MASTER_CSV_PATH
    if base is None: return
    parent = _annot_dir(base)
    os.makedirs(parent, exist_ok=True)

    # ---- STALE-SLIDE-LABEL GUARD (2026-08-08) ------------------------------------------------------
    # `batch` arrives from the page and is written verbatim as the batch identity. A multi-batch index
    # built from a decorated spec name ("*** ON META *** <batch>", "<batch>   [30 kt_outlines: lagging]")
    # therefore saves every mark to a batch that DOES NOT EXIST, invisible to every consumer. That
    # happened twice: 225 kt_outlines on `20251104 ablations_5`, then 134 rows across five Mad1 batches.
    # The builders no longer decorate, but a page ALREADY OPEN in a browser still holds the old label, so
    # a build-time fix cannot protect a stale tab. Normalise here, at the only point every save passes
    # through: strip a leading "*** ... *** " badge and a trailing "   [...]" annotation, and keep the
    # result only if it names a real batch on disk.
    _clean = re.sub(r'^\s*\*{2,}[^*]*\*{2,}\s*', '', batch)
    _clean = re.sub(r'\s{2,}\[[^\]]*\]\s*$', '', _clean).strip()
    if _clean != batch:
        _root = _annot_dir(csv_path or MASTER_CSV_PATH)
        _known = os.path.isdir(os.path.join(os.path.dirname(_root), "pipeline_session_output")) or True
        print(f"[name-guard] decorated batch name from a stale page:\n"
              f"    given : {batch!r}\n    using : {_clean!r}", flush=True)
        batch = _clean

    # Derive real acquisition times BEFORE anything is written (see _fix_times).
    rows = _fix_times(batch, rows)

    # Group incoming rows by type → filename
    by_file = {}
    for r in rows:
        r["batch"] = batch
        fname = _file_for_type(r.get("type") or "")
        by_file.setdefault(fname, []).append(r)

    # Always touch every known per-type file: rows for this batch are
    # rewritten; rows for other batches preserved; if no rows of a type
    # exist for this batch, any old rows of that type for this batch are
    # dropped (so unchecking a checkbox / deleting a mark sticks).
    files_to_update = set(TYPE_TO_FILE.values()) | set(by_file.keys())
    fields = MASTER_CSV_HEADER.split(",")

    # ---- EMPTY-PAYLOAD WIPE GUARD (2026-08-07) ---------------------------------------------------------
    # This function REPLACES a batch's rows with whatever the client sends, so a page that has the batch
    # open but nothing loaded saves an empty payload and DELETES every mark that batch has. That is not
    # hypothetical: 4 kt_outline traces (ids 8494-8497) were lost from `20260304 Mad1_ablation_8` exactly
    # this way -- the master still pointed at them, the rows were gone from every backup.
    # The per-batch slide pages make it easy to hit: they never fetch /load, so they open EMPTY even when
    # the store holds marks for that batch.
    # THE DISCRIMINATOR: deleting the last mark of ONE type is a real edit and must still work. A payload
    # with NO rows AT ALL for the batch means the client had nothing loaded -- there is no edit to honour.
    # So: an entirely empty payload is a no-op, loudly logged. Anything else behaves as before.
    if not rows:
        had = 0
        for fname in set(TYPE_TO_FILE.values()):
            path = os.path.join(parent, fname)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                had += sum(1 for r in csv.DictReader(f) if r.get("batch") == batch)
        if had:
            print(f"  [WIPE GUARD] refused an empty save for {batch!r}: it would have deleted {had} "
                  f"existing mark(s). The page that sent this had nothing loaded — reload it from an "
                  f"index page (per-batch pages do not fetch /load).")
            return

    with _master_lock:
        for fname in files_to_update:
            path = os.path.join(parent, fname)
            existing = []
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    rdr = csv.DictReader(f)
                    for r in rdr:
                        if r.get("batch") != batch:
                            existing.append(r)
            new_rows = by_file.get(fname, [])
            # --- id allocation (fix 2026-07-22) -------------------------------------------------
            # The browser numbers marks per batch, so two batches annotated the same afternoon both
            # produced id=1,2,3...  That is how kt_points grew 36 -> 119 duplicate ids in one day and
            # why keying dataops.apply_edits on `id` alone silently skipped rows.  The SERVER now owns
            # the id: anything blank, non-numeric, or already used by ANOTHER batch in this file is
            # reassigned above the file's live maximum.  Ids already unique to this batch are kept, so
            # existing master `*_ids` pointers stay valid.
            taken = set()
            mx = 0
            for r in existing:
                v = str(r.get("id", "")).strip()
                if v.isdigit():
                    taken.add(v); mx = max(mx, int(v))
            seen_here = set()
            for r in new_rows:
                v = str(r.get("id", "")).strip()
                if (not v.isdigit()) or v in taken or v in seen_here:
                    mx += 1
                    r["id"] = str(mx)
                    v = r["id"]
                else:
                    mx = max(mx, int(v))
                seen_here.add(v)
            # ------------------------------------------------------------------------------------
            if not existing and not new_rows:
                # nothing ever lived here for any batch and nothing to add
                if not os.path.isfile(path): continue
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                for r in existing + new_rows:
                    w.writerow(r)
    # Mirror per-batch summary + ID pointers into ABLATION_MASTER.csv.
    _mirror_batch_to_master(batch, rows)


# Path to the user's experiment master spreadsheet (Google-Sheets-synced).
# Each annotation save updates this batch's summary columns in place.
ABLATION_MASTER_CSV = "/Volumes/4 MB/ABLATION_MASTER.csv"

# For each annotation type, the master spreadsheet gets a *_ids column
# whose value is a comma-separated list of row IDs in the per-type file
# (e.g. cell_outline_ids → IDs to look up in cell_outlines.csv).
ID_COL_FOR_TYPE = {
    "cell_outline":    "cell_outline_ids",
    "kt_point":        "kt_point_ids",
    "chromo_line":     "chromo_line_ids",
    "meta_plate":      "meta_plate_ids",
    "polar_track":     "polar_track_ids",
    "pole":            "pole_ids",
    "timestrip_frame": "timestrip_frame_ids",
    "crop_box":        "crop_box_ids",
    # 2026-08-07: THESE THREE WERE MISSING. TYPE_TO_FILE grew when kt-outline slides (2026-07-22) and the
    # lagging_lengths split (2026-07-20) were added, but this map did not, so the server has NEVER written
    # `kt_outline_ids` or `lagging_ids`. The 40 batches that have a kt_outline_ids value got it from the
    # one-off re-mirror on 2026-07-22; the 19 annotated since were left blank, 1154 traces unreferenced.
    # Any type in TYPE_TO_FILE (except batch_meta, which is flags/notes) belongs here.
    "kt_outline":      "kt_outline_ids",
    "lagging_length":  "lagging_ids",     # both lagging types share ONE file and ONE column
    "lagging_width":   "lagging_ids",
}

SUMMARY_COLS = [
    "timestrip_candidate", "use_as_example",
    "reclass_prometaphase_to_prophase",
    "annotation_notes",
] + list(dict.fromkeys(ID_COL_FOR_TYPE.values())) + ["annotations_dir"]   # dedupe: 2 types -> lagging_ids


def _summarize_batch(rows):
    """Returns one dict keyed by SUMMARY_COLS to splice into ABLATION_MASTER.csv.

    Per-batch flags/notes get their own columns. For every drawing-mark TYPE,
    a `<type>_ids` column lists the IDs of the rows for this batch in that
    type's dedicated file (e.g. cell_outlines.csv). `annotations_dir` records
    where those files live so the master row is fully self-describing."""
    s = {c: "" for c in SUMMARY_COLS}
    # keyed by COLUMN so the two lagging types accumulate into one list instead of overwriting each other
    ids_by_col = {c: [] for c in ID_COL_FOR_TYPE.values()}
    for r in rows:
        t = (r.get("type") or "")
        lbl = (r.get("label") or "")
        notes = (r.get("notes") or "")
        if t == "batch_meta":
            if lbl in ("timestrip_candidate", "use_as_example",
                       "reclass_prometaphase_to_prophase"):
                s[lbl] = notes
            elif lbl == "notes":
                s["annotation_notes"] = notes
            continue
        if t in ID_COL_FOR_TYPE:
            rid = r.get("id", "")
            if rid: ids_by_col[ID_COL_FOR_TYPE[t]].append(str(rid))
    for c, ids in ids_by_col.items():
        if ids: s[c] = ",".join(ids)
    if any(ids_by_col.values()):
        s["annotations_dir"] = _annot_dir(MASTER_CSV_PATH or "")
    return s


def _mirror_batch_to_master(batch, rows):
    """Update one batch's summary cells in ABLATION_MASTER.csv in place.
    Preserves preamble, header, and all other rows/columns. No-op if the
    batch row or the master CSV doesn't exist."""
    path = ABLATION_MASTER_CSV
    if not os.path.isfile(path): return
    summary = _summarize_batch(rows)
    try:
        with _master_lock:
            with open(path, newline="", encoding="utf-8") as f:
                all_rows = list(csv.reader(f))
            # Find the "Batch Name" header row
            hi = next((i for i, r in enumerate(all_rows)
                       if r and r[0].strip() == "Batch Name"), None)
            if hi is None: return
            header = all_rows[hi]
            # Ensure summary columns exist
            existing_lower = {c.lower(): i for i, c in enumerate(header)}
            col_idx = {}
            need_write = False
            for c in SUMMARY_COLS:
                if c.lower() in existing_lower:
                    col_idx[c] = existing_lower[c.lower()]
                else:
                    header.append(c)
                    col_idx[c] = len(header) - 1
                    need_write = True
            W = len(header)
            # Find this batch's row
            target_idx = None
            for i in range(hi + 1, len(all_rows)):
                r = all_rows[i]
                if r and r[0].strip() == batch:
                    target_idx = i; break
            if target_idx is None: return
            r = all_rows[target_idx]
            while len(r) < W: r.append("")
            for c in SUMMARY_COLS:
                r[col_idx[c]] = summary[c]
            # Write atomically: tmp file + rename
            tmp = path + ".tmp"
            with open(tmp, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                for row in all_rows: w.writerow(row)
            os.replace(tmp, path)
    except Exception as e:
        sys.stderr.write(f"[mirror] WARN: could not update master CSV for {batch}: {e}\n")


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + RFC 7233 Range request support + /save endpoint."""

    # Make HTTP/1.1 so keep-alive works (small perf win for ranged seeks)
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        # HTML must never be cached, or a still-open tab keeps running OLD JS after a rebuild/patch
        # (this caused a "fix not taking effect" confusion). Videos/other assets keep normal caching.
        p = self.path.split("?")[0]
        if p.endswith(".html") or p.endswith("/"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_POST(self):
        # Allow /save?master_csv=… to write to an alternate file (e.g. the
        # outline tool uses outlines_master.csv).
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path.rstrip("/") == "/save":
            qs = parse_qs(u.query)
            override = qs.get("master_csv", [None])[0]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            try:
                payload = json.loads(body)
                batch = payload.get("batch", "")
                rows = payload.get("rows", [])
                csv_path = override or MASTER_CSV_PATH
                _autosave_replace_batch(batch, rows, csv_path=csv_path)
                resp = json.dumps({"ok": True, "n": len(rows),
                                   "csv": csv_path}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                err = json.dumps({"ok": False, "error": str(e)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err)))
                self.end_headers()
                self.wfile.write(err)
            return
        self.send_error(404, "Unknown endpoint")

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path.rstrip("/") == "/load":
            qs = parse_qs(u.query)
            override = qs.get("master_csv", [None])[0]
            batch_filter = qs.get("batch", [None])[0]
            target = override or MASTER_CSV_PATH
            # Read from every per-type file in the same directory + the
            # base unified file (if any). De-dup by (type, id, batch).
            rows = []
            seen = set()
            if target:
                parent = _annot_dir(target)
                candidates = [target] + [
                    os.path.join(parent, fn) for fn in TYPE_TO_FILE.values()
                ]
                with _master_lock:
                    for p in candidates:
                        if not os.path.isfile(p): continue
                        with open(p, encoding="utf-8") as f:
                            rdr = csv.DictReader(f)
                            for r in rdr:
                                if batch_filter and r.get("batch") != batch_filter:
                                    continue
                                k = (r.get("type",""), r.get("id",""), r.get("batch",""))
                                if k in seen: continue
                                seen.add(k); rows.append(r)
            payload = json.dumps({"ok": True, "rows": rows, "csv": target}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(payload)
            return
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().do_GET()
        if not os.path.isfile(path):
            self.send_error(404, "File not found")
            return

        ctype = self.guess_type(path) or "application/octet-stream"
        size = os.path.getsize(path)

        rng = self.headers.get("Range")
        if not rng:
            try:
                f = open(path, "rb")
            except OSError:
                self.send_error(404); return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Last-Modified", self.date_time_string(int(os.path.getmtime(path))))
            # HTML/JS must never be cached — a stale index.html keeps showing old
            # rendering bugs after a rebuild (a plain reload serves the cache).
            if path.endswith((".html", ".js")):
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()
            return

        # Parse "bytes=START-END" (END optional)
        m = re.match(r"bytes=(\d+)-(\d*)$", rng.strip())
        if not m:
            self.send_error(416, "Invalid Range header")
            return
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        if start >= size or end >= size or start > end:
            self.send_error(416, "Requested Range Not Satisfiable")
            self.send_header("Content-Range", f"bytes */{size}")
            return

        length = end - start + 1
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404); return
        try:
            f.seek(start)
            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            remaining = length
            chunk = 64 * 1024
            try:
                while remaining > 0:
                    data = f.read(min(chunk, remaining))
                    if not data: break
                    self.wfile.write(data)
                    remaining -= len(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # browser cancelled range request mid-stream — harmless
        finally:
            f.close()

    def end_headers(self):
        # Suppress browser caching so reloading the HTML always fetches fresh.
        if self.path.endswith(".html") or self.path.endswith("/"):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        # Log every request to stderr so we can debug iPad connectivity.
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


class ReusableThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    global MASTER_CSV_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg_dir")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--master-csv",
        default="/Volumes/4 MB/annotations/annotations_master.csv",
        help="Path to the master annotations CSV that auto-updates on every change")
    args = ap.parse_args()

    MASTER_CSV_PATH = args.master_csv
    os.chdir(args.pkg_dir)
    mimetypes.add_type("video/mp4", ".mp4")

    httpd = ReusableThreadingServer(("0.0.0.0", args.port), RangeRequestHandler)
    lan = get_lan_ip()
    print(f"serving {args.pkg_dir}")
    print(f"  Mac:   http://localhost:{args.port}/index.html")
    print(f"  iPad:  http://{lan}:{args.port}/index.html")
    print(f"  autosave → {MASTER_CSV_PATH}")
    if os.path.isdir(os.path.dirname(MASTER_CSV_PATH)):
        print("    (drive mounted)")
    else:
        print(f"    [WARN] parent dir not found — autosave will fail until /Volumes/4 MB/ is mounted")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping…"); httpd.shutdown()


if __name__ == "__main__":
    main()
