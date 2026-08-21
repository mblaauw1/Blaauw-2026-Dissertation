"""kt_outline_server.py <port> — serves the KT-OUTLINE slides and stores kinetochore outline traces.

STORE: /Volumes/4 MB/annotations/kt_outlines.csv   (id-keyed, same house style as the other annotation CSVs)
MASTER REF: ABLATION_MASTER.csv column `kt_outline_ids` (created if missing) — the §3c id-key convention.

WRITE DISCIPLINE (this project has lost annotation data to silent/partial writes — see NOTES §14, HANDOFF §18):
  1. one process-wide lock around every mutation
  2. timestamped backup of the store before the first write of each day
  3. write to .tmp then os.replace  (atomic)
  4. RE-READ FROM DISK and confirm the row is really there with the right values; restore + raise if not
  5. append every mutation to _logs/dataops_audit.jsonl
  6. nothing is ever deleted implicitly — deletes take an explicit id and archive the row first
The client re-fetches the stored rows after each save, so the UI shows what is ON DISK, never what it hoped.

Endpoints
  GET  /                       -> the slides page
  GET  /index.json             -> batch list
  GET  /pkg/<batch>/<file>     -> package media (byte-range, HTTP/1.1)
  GET  /outlines.json?batch=   -> stored rows for a batch (READ FROM DISK every time)
  POST /save_outline           -> upsert ONE trace  {batch, group_id, ..., points:[[x,y],...]}
  POST /delete_outline         -> {batch, id} archive + remove
  POST /save_group             -> rename/retype a group (updates every row in it)
"""
import sys, os, io, json, csv, re, shutil, threading, datetime, http.server

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8810
ROOT = "/Volumes/4 MB"
PKGS = f"{ROOT}/kt_outline_pkgs_20260722"
HERE = os.path.dirname(os.path.abspath(__file__))
STORE = f"{ROOT}/annotations/kt_outlines.csv"
MASTER = f"{ROOT}/ABLATION_MASTER.csv"
BACKUPS = f"{ROOT}/_master_backups"
ARCHIVE = f"{BACKUPS}/kt_outlines_DELETED_rows.csv"
AUDIT = f"{ROOT}/_logs/dataops_audit.jsonl"
MASTER_IDCOL = "kt_outline_ids"

HDR = ["id", "batch", "group_id", "group_label", "kt_type", "trace_index",
       "video_file", "phase", "channel", "frame", "t_sec", "t_hms", "z_slice", "z_run", "zoom_at_trace", "nearest_event",
       "type", "label", "points", "n_points", "x", "y",
       "length_um", "area_um2", "perimeter_um", "pixel_size_um", "roi_x", "roi_y",
       "source", "saved_at", "notes"]

KT_TYPES = ["polar", "lagging", "paired", "sisterless", "plate", "unaligned", "other"]

_lock = threading.RLock()


# ---------------------------------------------------------------- store I/O
def _read(path, hdr=None):
    if not os.path.isfile(path):
        return []
    t = open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    return list(csv.DictReader(io.StringIO(t)))


def _atomic_write(path, rows, hdr):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tmp, path)


def _backup_once():
    """One backup per day per store — enough to roll back a session, without spamming the folder."""
    if not os.path.isfile(STORE):
        return None
    day = datetime.date.today().isoformat().replace("-", "")
    bak = f"{BACKUPS}/kt_outlines_pre_{day}.csv"
    if not os.path.isfile(bak):
        os.makedirs(BACKUPS, exist_ok=True)
        shutil.copy2(STORE, bak)
    return bak


def _audit(op, payload):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps({"op": op, "at": datetime.datetime.now().isoformat(timespec="seconds"),
                            **payload}) + "\n")


def _next_id(rows):
    return str(max([int(r["id"]) for r in rows if str(r.get("id", "")).isdigit()] + [0]) + 1)


def _mirror_master_ids(batch, rows):
    """Keep ABLATION_MASTER.<kt_outline_ids> in sync (§3c). Row-count preserving; creates the column once."""
    if not os.path.isfile(MASTER):
        return
    t = open(MASTER, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    mr = list(csv.reader(io.StringIO(t)))
    hi = next((i for i, r in enumerate(mr) if r and r[0].strip() == "Batch Name"), 1)
    hdr = [c.strip() for c in mr[hi]]
    n_before = len(mr)
    if MASTER_IDCOL not in hdr:
        for i, r in enumerate(mr):
            r.append(MASTER_IDCOL if i == hi else "")
        hdr.append(MASTER_IDCOL)
    ci = hdr.index(MASTER_IDCOL)
    ids = ",".join(r["id"] for r in rows if r.get("batch", "").strip() == batch and r.get("id"))
    hit = False
    for r in mr[hi + 1:]:
        if r and r[0].strip() == batch:
            while len(r) <= ci:
                r.append("")
            r[ci] = ids
            hit = True
            break
    if not hit:
        return
    if len(mr) != n_before:
        raise RuntimeError("refusing to write ABLATION_MASTER: row count changed")
    bak = f"{BACKUPS}/ABLATION_MASTER_pre_ktoutline_{datetime.date.today().isoformat().replace('-','')}.csv"
    if not os.path.isfile(bak):
        shutil.copy2(MASTER, bak)
    tmp = MASTER + ".tmp"
    with open(tmp, "w", newline="") as f:
        csv.writer(f).writerows(mr)
    os.replace(tmp, MASTER)


def _verify_on_disk(rid, expect):
    """RULE 4: read the file back off the disk and prove the row is there with the values we wrote."""
    for r in _read(STORE):
        if r.get("id") == rid:
            for k, v in expect.items():
                if (r.get(k) or "") != (v or ""):
                    return False, f"field {k}: disk has {r.get(k)!r}, expected {v!r}"
            return True, ""
    return False, "row absent from disk after write"


# ---------------------------------------------------------------- geometry
def _resample(pts, step=0.25):
    """Resample a closed polygon at a FIXED image-pixel spacing.

    WHY: the drawing threshold is in SCREEN pixels, so a shape traced at 10x zoom captures ~2x the points
    of the same shape traced at fit. Measured 2026-07-22 on an identical synthetic square: positions agreed
    to 0.13 px, but PERIMETER differed by 1.4% purely from sampling density. Deriving the metrics from a
    resampled outline makes them independent of the zoom the user happened to be at. The RAW points the
    user drew are still stored untouched in `points` — nothing is lost, only the derived numbers are
    normalised."""
    ring = list(pts) + [pts[0]]
    out, carry = [ring[0]], 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        seg = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if seg <= 0:
            continue
        d = step - carry
        while d <= seg:
            out.append((x1 + (x2 - x1) * d / seg, y1 + (y2 - y1) * d / seg))
            d += step
        carry = (carry + seg) % step
    return out if len(out) >= 3 else list(pts)


def _poly_metrics(pts, ps):
    if not pts or len(pts) < 2:
        return "", "", "", "", ""
    pts = _resample(pts)
    per = sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
              for i in range(len(pts) - 1))
    closed = per + ((pts[0][0] - pts[-1][0]) ** 2 + (pts[0][1] - pts[-1][1]) ** 2) ** 0.5
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    area = abs(a) / 2.0
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return (round(per * ps, 4), round(area * ps * ps, 4), round(closed * ps, 4),
            round(cx, 2), round(cy, 2))


def _hms(t):
    try: s = int(round(float(t)))
    except Exception: return ""
    sign = "-" if s < 0 else ""; s = abs(s)
    return f"{sign}{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


# ---------------------------------------------------------------- handler
class H(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"          # HTTP/1.0 breaks <video> playback (NOTES §8)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try: self.wfile.write(body)
        except (ConnectionError, BrokenPipeError): pass

    def _send_file(self, path, ctype=None):
        if not os.path.isfile(path):
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        sz = os.path.getsize(path)
        rng = self.headers.get("Range")
        ctype = ctype or self.guess_type(path)
        if rng and "=" in rng:
            a, _, b = rng.split("=")[-1].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else sz - 1
            end = min(end, sz - 1)
            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Range", f"bytes {start}-{end}/{sz}")
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start); rem = end - start + 1
                while rem > 0:
                    c = f.read(min(65536, rem))
                    if not c: break
                    try: self.wfile.write(c)
                    except (ConnectionError, BrokenPipeError): return
                    rem -= len(c)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(sz))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(path, "rb") as f:
            try: shutil.copyfileobj(f, self.wfile)
            except (ConnectionError, BrokenPipeError): pass

    # ---------------- GET
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs, unquote
        u = urlparse(self.path); p = unquote(u.path); q = parse_qs(u.query)
        if p in ("/", "/index.html"):
            return self._send_file(os.path.join(HERE, "kt_outline.html"), "text/html; charset=utf-8")
        if p == "/index.json":
            return self._send_file(os.path.join(PKGS, "index.json"), "application/json")
        if p == "/kt_types.json":
            return self._json({"types": KT_TYPES})
        if p.startswith("/pkg/"):
            rel = p[len("/pkg/"):]
            full = os.path.normpath(os.path.join(PKGS, rel))
            if not full.startswith(os.path.realpath(PKGS)) and not full.startswith(PKGS):
                self.send_response(403); self.send_header("Content-Length", "0"); self.end_headers(); return
            return self._send_file(full)
        if p == "/outlines.json":
            b = (q.get("batch", [""])[0] or "").strip()
            with _lock:
                rows = [r for r in _read(STORE) if not b or r.get("batch", "").strip() == b]
            return self._json({"rows": rows, "store": STORE})
        self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()

    # ---------------- POST
    def do_POST(self):
        if self.path not in ("/save_outline", "/delete_outline", "/save_group"):
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n))
        except Exception:
            return self._json({"ok": False, "error": "bad JSON"}, 400)
        try:
            with _lock:
                if self.path == "/save_outline":
                    return self._json(self._save(payload))
                if self.path == "/delete_outline":
                    return self._json(self._delete(payload))
                return self._json(self._save_group(payload))
        except Exception as e:
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)

    def _save(self, p):
        b = (p.get("batch") or "").strip()
        gid = str(p.get("group_id") or "").strip()
        pts = p.get("points") or []
        if not b or not gid or len(pts) < 2:
            return {"ok": False, "error": "batch, group_id and >=2 points are required"}
        rows = _read(STORE)
        _backup_once()
        ps = float(p.get("pixel_size_um") or 0.062)
        per_um, area_um2, closed_um, cx, cy = _poly_metrics(pts, ps)
        rid = str(p.get("id") or "").strip()
        existing = next((r for r in rows if r.get("id") == rid), None) if rid else None
        # trace_index: several traces of ONE kinetochore on ONE frame are allowed (odd shapes).
        ti = p.get("trace_index")
        if ti in (None, ""):
            same = [r for r in rows if r.get("batch") == b and r.get("group_id") == gid
                    and str(r.get("frame")) == str(p.get("frame")) and r is not existing]
            ti = str(max([int(r["trace_index"]) for r in same if str(r.get("trace_index", "")).isdigit()] + [-1]) + 1)
        rec = {
            "id": rid or _next_id(rows),
            "batch": b, "group_id": gid,
            "group_label": p.get("group_label", ""), "kt_type": p.get("kt_type", ""),
            "trace_index": str(ti),
            "video_file": p.get("video_file", ""), "phase": "mon",
            "channel": p.get("channel", ""),
            "frame": str(p.get("frame", "")), "t_sec": str(p.get("t_sec", "")),
            "t_hms": _hms(p.get("t_sec")),
            # z_slice>0 => this frame is a z-slice the pipeline filed as monitoring, NOT a distinct timepoint
            "z_slice": str(p.get("z_slice", 0) or 0), "z_run": str(p.get("z_run", 1) or 1),
            # provenance: what zoom the trace was drawn at (metrics are resampled, so this is audit only)
            "zoom_at_trace": str(p.get("zoom_at_trace", "")),
            "nearest_event": p.get("nearest_event", ""),
            "type": "kt_outline", "label": "kt_outline",
            "points": json.dumps([[round(float(x), 2), round(float(y), 2)] for x, y in pts]),
            "n_points": str(len(pts)), "x": str(cx), "y": str(cy),
            "length_um": str(closed_um), "area_um2": str(area_um2), "perimeter_um": str(per_um),
            "pixel_size_um": str(ps),
            "roi_x": str(p.get("roi_x", "")), "roi_y": str(p.get("roi_y", "")),
            "source": p.get("source", "kt_outline_slides"),
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "notes": p.get("notes", ""),
        }
        if existing:
            existing.update(rec)
        else:
            rows.append(rec)
        before = len(rows)
        _atomic_write(STORE, rows, HDR)
        ok, why = _verify_on_disk(rec["id"], {"batch": b, "group_id": gid, "frame": rec["frame"],
                                              "points": rec["points"], "trace_index": rec["trace_index"]})
        if not ok:
            bak = f"{BACKUPS}/kt_outlines_pre_{datetime.date.today().isoformat().replace('-','')}.csv"
            if os.path.isfile(bak):
                shutil.copy2(bak, STORE)
            return {"ok": False, "error": f"WRITE DID NOT PERSIST — {why}. Store restored from backup."}
        disk = _read(STORE)
        if len(disk) != before:
            return {"ok": False, "error": f"row count on disk is {len(disk)}, expected {before}"}
        _mirror_master_ids(b, disk)
        _audit("kt_outline_save", {"batch": b, "id": rec["id"], "group_id": gid,
                                   "frame": rec["frame"], "trace_index": rec["trace_index"],
                                   "n_points": rec["n_points"]})
        return {"ok": True, "row": rec, "n_rows_for_batch": len([r for r in disk if r.get("batch") == b])}

    def _delete(self, p):
        b = (p.get("batch") or "").strip(); rid = str(p.get("id") or "").strip()
        if not b or not rid:
            return {"ok": False, "error": "batch and id required"}
        rows = _read(STORE)
        gone = [r for r in rows if r.get("id") == rid and r.get("batch") == b]
        if not gone:
            return {"ok": False, "error": "no such row"}
        _backup_once()
        os.makedirs(BACKUPS, exist_ok=True)          # NOTHING is destroyed — archive first
        new = not os.path.isfile(ARCHIVE)
        with open(ARCHIVE, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HDR, extrasaction="ignore")
            if new: w.writeheader()
            for r in gone:
                r = dict(r); r["notes"] = (r.get("notes") or "") + f" [deleted {datetime.datetime.now().isoformat(timespec='seconds')}]"
                w.writerow(r)
        keep = [r for r in rows if not (r.get("id") == rid and r.get("batch") == b)]
        _atomic_write(STORE, keep, HDR)
        disk = _read(STORE)
        if any(r.get("id") == rid and r.get("batch") == b for r in disk):
            return {"ok": False, "error": "delete did not persist"}
        _mirror_master_ids(b, disk)
        _audit("kt_outline_delete", {"batch": b, "id": rid, "archived_to": ARCHIVE})
        return {"ok": True, "deleted": rid, "archived": ARCHIVE}

    def _save_group(self, p):
        b = (p.get("batch") or "").strip(); gid = str(p.get("group_id") or "").strip()
        if not b or not gid:
            return {"ok": False, "error": "batch and group_id required"}
        rows = _read(STORE); _backup_once()
        touched = 0
        for r in rows:
            if r.get("batch") == b and r.get("group_id") == gid:
                if "group_label" in p: r["group_label"] = p["group_label"]
                if "kt_type" in p:     r["kt_type"] = p["kt_type"]
                if "notes" in p and p["notes"]:
                    r["notes"] = (r.get("notes") or "")
                touched += 1
        if not touched:
            return {"ok": True, "touched": 0}
        _atomic_write(STORE, rows, HDR)
        disk = _read(STORE)
        bad = [r for r in disk if r.get("batch") == b and r.get("group_id") == gid
               and "kt_type" in p and r.get("kt_type") != p["kt_type"]]
        if bad:
            return {"ok": False, "error": "group update did not persist"}
        _audit("kt_outline_group", {"batch": b, "group_id": gid, "touched": touched,
                                    "kt_type": p.get("kt_type"), "group_label": p.get("group_label")})
        return {"ok": True, "touched": touched}


class TS(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    if not os.path.isfile(STORE):
        _atomic_write(STORE, [], HDR)
        print(f"created empty store {STORE}", flush=True)
    print(f"kt_outline_server on http://127.0.0.1:{PORT}   pkgs={PKGS}   store={STORE}", flush=True)
    TS(("127.0.0.1", PORT), H).serve_forever()
