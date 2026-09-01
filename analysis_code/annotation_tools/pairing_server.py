"""pairing_server.py <port> <root> — byte-range video server (same as range_server) PLUS a dedicated
per-chromosome length<->behavior pairing store. Does NOT touch the master; writes to its own CSV.
  GET  /pairing.json         -> {batch: {chr1_length_um:..., pairing_notes:...}, ...}
  POST /save_pairing         -> merge {batch_name, fields} into CHROMO_LENGTH_BEHAVIOR_PAIRING.csv (atomic)
Video byte-range serving is identical to range_server.py (HTTP/1.0, no keep-alive)."""
import sys, os, json, csv, re, threading, http.server
import io
PORT = int(sys.argv[1]); ROOT = sys.argv[2]
PAIR_CSV = "/Volumes/4 MB/annotations/CHROMO_LENGTH_BEHAVIOR_PAIRING.csv"
FIELDS = ["chr1_length_um", "chr1_length_um_free", "chr2_length_um", "chr2_length_um_free",
          "chr3_length_um", "chr3_length_um_free", "pairing_notes",
          "chr1_movement", "chr2_movement", "chr3_movement"]
HDR = ["id", "batch"] + FIELDS      # id-key convention (see _READ_FIRST_DATA_MAP.md §3c)
_lock = threading.Lock()

# --- freehand chromosome-measurement traces (frame-tracked), ISOLATED store (never touches chromo_lines.csv) ---
MEASURE_CSV = "/Volumes/4 MB/annotations/chromo_measure_lines.csv"
MHDR = ["id","batch","chr_num","video_url","phase","channel","frame","t_sec","points","length_um","pixel_size_um"]
def _load_measure():
    if not os.path.isfile(MEASURE_CSV): return []
    return list(csv.DictReader(open(MEASURE_CSV)))
def _write_measure(rows):
    tmp = MEASURE_CSV + ".tmp"; os.makedirs(os.path.dirname(MEASURE_CSV), exist_ok=True)
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MHDR, extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow(r)
    os.replace(tmp, MEASURE_CSV)
_ids = {}                           # batch -> stable id (preserved across saves)

def _load_pairs():
    out = {}
    if os.path.isfile(PAIR_CSV):
        for r in csv.DictReader(open(PAIR_CSV)):
            b = (r.get("batch") or "").strip()
            if b:
                out[b] = {k: (r.get(k) or "") for k in FIELDS}
                if (r.get("id") or "").strip(): _ids[b] = r["id"].strip()
    return out


CHROMO_MASTER = "/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
def _behav_from_movement(clause):
    """movement text -> (behavior, congression_seconds). Same vocabulary the review UI displays."""
    c = (clause or "").lower()
    if not c: return None
    if re.search(r'(polar|pole)', c) and 'anaphase' in c: return ("noncongression", None)
    if re.search(r'(entire|whole) time|from (onset|the beginning|metaphase onset)|since (onset|metaphase)|never (left|seen)', c) and re.search(r'plate|congress', c): return ("at_plate", None)
    m = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', c)
    if m and re.search(r'congress|moves?|converge|plate|reach', c):
        p = [float(x) for x in m.group(1).split(':')]
        while len(p) < 3: p.insert(0, 0)
        return ("congressed", p[0]*3600 + p[1]*60 + p[2])
    if re.search(r'congress', c): return ("congressed", None)
    if re.search(r'at (the )?plate', c): return ("at_plate", None)
    return None

def _mirror_chromosome_master(batch, rec, only_fields=None, src_tag="8781_pairing"):
    """Write this batch's per-chromosome length/behavior into the CHROMOSOME_MASTER (the ONE authoritative
    per-chromosome table the plots and this UI both read).  RULES:
      * never delete a row, never blank an existing value;
      * only write a field the pairing edit actually supplies;
      * atomic write + verify by re-read (a write that does not persist raises).
    Added 2026-07-22 after CHROMO_COMPLETE was found to have no write path at all."""
    import shutil
    if not os.path.isfile(CHROMO_MASTER): return
    txt = open(CHROMO_MASTER, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    rows = list(csv.reader(io.StringIO(txt)))
    hdr = rows[0]; ci = {c: i for i, c in enumerate(hdr)}
    n_before = len(rows)
    bi, xi = ci["batch"], ci["chr_num"]
    idx = {(r[bi].strip(), r[xi].strip()): r for r in rows[1:] if r and len(r) > max(bi, xi)}
    changed = []
    for cn in ("1", "2", "3"):
        lk, mk = "chr%s_length_um" % cn, "chr%s_movement" % cn
        # ONLY the fields this save actually supplied. Re-applying the whole stored PAIRING record would
        # overwrite curated CHROMOSOME_MASTER values with stale pairing text (caught in live test 2026-07-22).
        L = (rec.get(lk) or "").strip() if (only_fields is None or lk in only_fields) else ""
        mv = (rec.get(mk) or "").strip() if (only_fields is None or mk in only_fields) else ""
        if not L and not mv: continue
        r = idx.get((batch, cn))
        if r is None:
            r = [""] * len(hdr); r[ci["batch"]] = batch; r[ci["chr_num"]] = cn
            if "id" in ci:
                r[ci["id"]] = str(max([int(x[ci["id"]]) for x in rows[1:] if x and str(x[ci["id"]]).isdigit()] + [0]) + 1)
            r[ci["source"]] = src_tag
            rows.append(r); idx[(batch, cn)] = r
        while len(r) < len(hdr): r.append("")
        if L:
            r[ci["length_um"]] = L; changed.append((batch, cn, "length_um", L))
        bh = _behav_from_movement(mv)
        if bh:
            r[ci["behavior"]] = bh[0]; changed.append((batch, cn, "behavior", bh[0]))
            if bh[1] is not None:
                s = int(bh[1]); r[ci["congression_time_s"]] = str(s)
                r[ci["congression_hms"]] = "%d:%02d:%02d" % (s//3600, (s%3600)//60, s%60)
            elif bh[0] != "congressed":
                r[ci["congression_time_s"]] = ""; r[ci["congression_hms"]] = ""
        if src_tag not in (r[ci["source"]] or ""):
            r[ci["source"]] = (r[ci["source"]] + ";" + src_tag).strip(";")
    if not changed: return
    if len(rows) < n_before:
        raise RuntimeError("refusing to write CHROMOSOME_MASTER: row count would shrink")
    bak = "/Volumes/4 MB/_master_backups/CHROMOSOME_MASTER_pre_%s_write.csv" % src_tag
    shutil.copy2(CHROMO_MASTER, bak)
    tmp = CHROMO_MASTER + ".tmp"
    with open(tmp, "w", newline="") as f: csv.writer(f).writerows(rows)
    os.replace(tmp, CHROMO_MASTER)
    # verify by re-read
    txt2 = open(CHROMO_MASTER, encoding="utf-8", errors="replace").read().replace("\r\n", "\n").replace("\r", "\n")
    r2 = list(csv.reader(io.StringIO(txt2))); c2 = {c: i for i, c in enumerate(r2[0])}
    i2 = {(x[c2["batch"]].strip(), x[c2["chr_num"]].strip()): x for x in r2[1:] if x and len(x) > max(c2["batch"], c2["chr_num"])}
    for b, cn, col, val in changed:
        if i2[(b, cn)][c2[col]] != val:
            shutil.copy2(bak, CHROMO_MASTER)
            raise RuntimeError("CHROMOSOME_MASTER write did not persist - restored")
    with open("/Volumes/4 MB/_logs/dataops_audit.jsonl", "a") as f:
        f.write(json.dumps({"op": src_tag + "_mirror", "batch": batch, "changes": changed}) + "\n")

def _write_pairs(d):
    # assign stable ids: keep existing, new batches get max+1
    nxt = max([int(v) for v in _ids.values() if str(v).isdigit()] or [0]) + 1
    for b in sorted(d):
        if b not in _ids: _ids[b] = str(nxt); nxt += 1
    tmp = PAIR_CSV + ".tmp"
    os.makedirs(os.path.dirname(PAIR_CSV), exist_ok=True)
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f); w.writerow(HDR)
        for b in sorted(d):
            row = d[b]; w.writerow([_ids.get(b, ""), b] + [row.get(k, "") for k in FIELDS])
    os.replace(tmp, PAIR_CSV)

# ---- frame -> real acquisition t_sec ------------------------------------------------------------
# The tracking UI sends the browser's <video>.currentTime, which is CLIP seconds, not experiment time.
# Storing that in t_sec corrupted 2554 marks across 62 batches (found + repaired 2026-07-22): dt between
# consecutive marks came out ~0.05 s instead of ~20 s, inflating every rate ~400x. frames.json is the
# authority for frame -> t_sec, so the SERVER derives it and ignores whatever the client sent.
_FRAMEMAP = {}
def _frame_maps(batch):
    """role -> {frame index within that role: real t_sec}.  Every role, not just monitoring:
    the 8781 measure lines are drawn on the ABLATION clip, so a monitoring-only map left them
    holding the browser's clip clock (found 2026-07-22: 45 rows across 16 batches)."""
    if batch in _FRAMEMAP: return _FRAMEMAP[batch]
    maps = {}
    try:
        mr = list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
        hdr = [c.strip() for c in mr[1]]
        bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
        path = next((r[pi].strip() for r in mr[2:] if r and len(r) > pi and r[bi].strip() == batch), "")
        if path and os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                if f.endswith("_frames.json"):
                    d = json.loads(open(os.path.join(path, f), encoding="utf-8", errors="replace").read())
                    for role in ("monitoring", "ablation", "pre"):
                        sub = [x for x in d.get("frames", []) if x.get("role") == role]
                        if sub: maps[role] = {i: fr["t_sec"] for i, fr in enumerate(sub)}
                    break
    except Exception:
        maps = {}
    _FRAMEMAP[batch] = maps
    return maps

def _role_of(video_url, phase=""):
    s = (video_url or "").lower()
    if "_ablation" in s or phase == "abl": return "ablation"
    if "_pre" in s or phase == "pre": return "pre"
    return "monitoring"

def _frame_map(batch):
    return _frame_maps(batch).get("monitoring")

def _real_t(batch, frame, sent, role="monitoring"):
    fm = _frame_maps(batch).get(role)
    try: fi = int(float(frame))
    except Exception: return str(sent or ""), ""
    if fm and fi in fm:
        t = fm[fi]
        s = int(round(t)); sign = "-" if s < 0 else ""; s = abs(s)
        return f"{t:.2f}", f"{sign}{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
    return str(sent or ""), ""


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == "/pairing.json":
            with _lock: return self._json(_load_pairs())
        if self.path.startswith("/measure_lines.json"):
            from urllib.parse import urlparse, parse_qs
            bf = parse_qs(urlparse(self.path).query).get("batch", [None])[0]
            with _lock: rows = [r for r in _load_measure() if (not bf or r.get("batch") == bf)]
            return self._json({"rows": rows})
        if self.path.startswith("/trackmate_spots.json"):
            from urllib.parse import urlparse, parse_qs
            bf = parse_qs(urlparse(self.path).query).get("batch", [None])[0]
            # find spots csv + pixel size for this batch, return spots per frame in PIXEL coords for snapping
            import csv, io as _c
            kt = {r["batch"].strip(): r for r in _c.DictReader(open("/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv"))} \
                 if os.path.isfile("/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv") else {}
            # pixel size from master
            mrows = list(_c.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv"))); mcols = [c.strip() for c in mrows[1]]
            ps = 0.062
            try:
                pi = mcols.index("Pixel Size (um)")
                for r in mrows[2:]:
                    if r and r[0].strip() == bf and pi < len(r) and r[r.index(r[pi]) if False else pi].strip():
                        ps = float(r[pi]); break
            except Exception: pass
            byframe = {}
            r = kt.get(bf)
            if r:
                sc = os.path.join(r.get("results_dir",""), r.get("spots_timed_csv",""))
                if os.path.isfile(sc):
                    for s in _c.DictReader(open(sc)):
                        try:
                            f = int(s["frame"]); x = float(s["x_um"])/ps; y = float(s["y_um"])/ps
                            byframe.setdefault(f, []).append({"x": round(x,1), "y": round(y,1),
                                "int": float(s.get("mean_intensity") or 0)})
                        except Exception: pass
            return self._json({"pixel_size_um": ps, "spots_by_frame": byframe})
        if self.path.startswith("/track_marks.json"):
            from urllib.parse import urlparse, parse_qs
            bf = parse_qs(urlparse(self.path).query).get("batch", [None])[0]
            def pull(path, label):
                out = []
                for r in self._load_ann(path):
                    if (r.get("batch","") or "").strip() != bf or r.get("label") != label: continue
                    pts = []
                    if r.get("points"):
                        try: pts = json.loads(r["points"])
                        except Exception: pts = []
                    out.append({"id": r.get("id",""), "frame": r.get("frame",""), "t_sec": r.get("t_sec",""),
                                "x": r.get("x",""), "y": r.get("y",""), "points": pts, "video_file": r.get("video_file",""),
                                "notes": r.get("notes","")})
                return out
            with _lock:
                res = {"sisterless": pull("/Volumes/4 MB/annotations/kt_points.csv","sisterless"),
                       "meta_plate": pull("/Volumes/4 MB/annotations/meta_plates.csv","meta_plate")}
            return self._json(res)
        if self.path.startswith("/download_all_annotations"):
            # combined CSV of every KT + plate mark (all batches) — the tracking work product, for backup/export
            import io
            buf = io.StringIO(); w = csv.writer(buf)
            w.writerow(["batch","kind","kt_index","frame","t_sec","x","y","points","video_file","notes"])
            with _lock:
                for path, kind in (("/Volumes/4 MB/annotations/kt_points.csv","sisterless"),
                                   ("/Volumes/4 MB/annotations/meta_plates.csv","meta_plate")):
                    if not os.path.isfile(path): continue
                    for r in csv.DictReader(open(path)):
                        if r.get("label") != kind: continue
                        nt = r.get("notes","") or ""; mm = re.search(r'kt:(\d+)', nt)
                        w.writerow([r.get("batch",""), kind, (mm.group(1) if mm else ""), r.get("frame",""),
                                    r.get("t_sec",""), r.get("x",""), r.get("y",""), r.get("points",""),
                                    r.get("video_file",""), nt])
                # consolidated per-chromosome length + behavior + congression
                cf = "/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
                if os.path.isfile(cf):
                    for r in csv.DictReader(open(cf)):
                        note = "len=%s um; behavior=%s; congress=%s" % (r.get("length_um",""), r.get("behavior",""), r.get("congression_hms",""))
                        w.writerow([r.get("batch",""), "chromosome", r.get("chr_num",""), "","","","","","", note])
                # ALL per-batch comments from the master
                mrows = list(csv.reader(open("/Volumes/4 MB/ABLATION_MASTER.csv"))); mh = [h.strip() for h in mrows[1]]
                ccols = ["Notes","annotation_notes","Polar Comments","Lagging Comments","First Congression (s)","Polar Chromosomes","Lagging Chromosomes"]
                idxs = [(c, mh.index(c)) for c in ccols if c in mh]
                for r in mrows[2:]:
                    if not r or not r[0].strip(): continue
                    for c, i in idxs:
                        if i < len(r) and (r[i] or "").strip():
                            w.writerow([r[0].strip(), "comment", "", "","","","","","", c + ": " + r[i].strip()])
            body = buf.getvalue().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type","text/csv")
            self.send_header("Content-Disposition",'attachment; filename="kt_tracking_annotations.csv"')
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            try: self.wfile.write(body)
            except (ConnectionError, BrokenPipeError): pass
            return
        fpath = self.translate_path(self.path)
        if os.path.isfile(fpath) and self.headers.get("Range"): return self._range(fpath)
        return super().do_GET()
    def _range(self, fpath):
        sz = os.path.getsize(fpath); rng = self.headers.get("Range", "").split("=")[-1]
        a, b = (rng.split("-") + [""])[:2]; start = int(a) if a else 0; end = int(b) if b else sz - 1; end = min(end, sz - 1)
        self.send_response(206); self.send_header("Content-Type", self.guess_type(fpath))
        self.send_header("Content-Range", f"bytes {start}-{end}/{sz}")
        self.send_header("Content-Length", str(end - start + 1)); self.send_header("Accept-Ranges", "bytes"); self.end_headers()
        with open(fpath, "rb") as f:
            f.seek(start); rem = end - start + 1
            while rem > 0:
                chunk = f.read(min(65536, rem))
                if not chunk: break
                try: self.wfile.write(chunk)
                except (ConnectionError, BrokenPipeError): break
                rem -= len(chunk)
    def do_POST(self):
        if self.path not in ("/save_pairing", "/save_annotation", "/save_measure_line",
                             "/save_track_mark", "/delete_track_mark"):
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0))
        try: payload = json.loads(self.rfile.read(n))
        except Exception:
            self.send_response(400); self.send_header("Content-Length", "0"); self.end_headers(); return
        if self.path == "/save_measure_line":
            return self._save_measure_line(payload)
        if self.path == "/save_track_mark":
            return self._save_track_mark(payload)
        if self.path == "/delete_track_mark":
            return self._delete_track_mark(payload)
        bn = (payload.get("batch_name") or "").strip(); fields = payload.get("fields", {}) or {}
        if not bn: return self._json({"ok": False}, 400)
        if self.path == "/save_annotation":   # .af annotation-panel edits -> MASTER (columns that exist only), atomic
            return self._save_annotation(bn, fields)
        with _lock:
            d = _load_pairs()
            rec = d.get(bn, {})
            for k in FIELDS:
                if k in fields:
                    v = "" if fields[k] is None else str(fields[k])
                    # careless-overwrite guard: NEVER clobber an existing non-blank value with a blank
                    # (e.g. saving behavior with an empty length field must not wipe a stored length).
                    if v.strip() or not (rec.get(k) or "").strip():
                        rec[k] = v
            # drop empties -> if all blank, remove the row
            if any((rec.get(k) or "").strip() for k in FIELDS): d[bn] = rec
            elif bn in d: del d[bn]
            _write_pairs(d)
            _mirror_chromosome_master(bn, rec, set(fields))
            with open(os.path.join(ROOT, "_pairing_audit.log"), "a") as a: a.write(json.dumps(payload) + "\n")
        self._json({"ok": True})

    def _save_measure_line(self, payload):
        """Append/replace ONE freehand chromosome trace (frame-tracked) in the isolated measure store.
        Replaces any prior trace for the same (batch, chr_num) so re-measuring updates. Never touches
        chromo_lines.csv or the pairing CSV. Also mirrors the length into the pairing CSV summary."""
        b = (payload.get("batch") or "").strip(); cn = str(payload.get("chr_num") or "").strip()
        if not b or not cn: return self._json({"ok": False, "error": "batch/chr_num required"}, 400)
        with _lock:
            rows = [r for r in _load_measure() if not (r.get("batch") == b and str(r.get("chr_num")) == cn)]
            nid = str(max([int(r["id"]) for r in rows if str(r.get("id","")).isdigit()] + [0]) + 1)
            # t_sec comes from frames.json for the role this clip belongs to -- NEVER from the client,
            # which sends <video>.currentTime (clip seconds at the encode fps).
            _ts, _ = _real_t(b, payload.get("frame",""), payload.get("t_sec",""),
                             _role_of(payload.get("video_url",""), payload.get("phase","")))
            rows.append({"id": nid, "batch": b, "chr_num": cn,
                         "video_url": payload.get("video_url",""), "phase": payload.get("phase",""),
                         "channel": payload.get("channel",""), "frame": str(payload.get("frame","")),
                         "t_sec": _ts, "points": json.dumps(payload.get("points",[])),
                         "length_um": str(payload.get("length_um","")), "pixel_size_um": str(payload.get("pixel_size_um",""))})
            _write_measure(rows)
            # mirror the length into the pairing summary (chrN_length_um) so pairing stays in sync
            um = payload.get("length_um","")
            if um != "" and cn in ("1","2","3"):
                d = _load_pairs(); rec = d.get(b, {}); rec[f"chr{cn}_length_um"] = str(um)
                d[b] = rec; _write_pairs(d)
                # ...and into CHROMOSOME_MASTER, the table the plots and the review UI actually read.
                # Without this a length typed here stopped at chromo_measure_lines + PAIRING (P10, 2026-07-22).
                _mirror_chromosome_master(b, {f"chr{cn}_length_um": str(um)},
                                          {f"chr{cn}_length_um"}, src_tag="8781_measure")
        return self._json({"ok": True, "id": nid, "length_um": payload.get("length_um","")})

    # ---- semi-auto KT tracking: sisterless KT points + straight meta_plate lines, SAME stores/schema as
    #      the annotation slides (kt_points.csv / meta_plates.csv). Upsert by (batch,frame,label); id-keyed;
    #      mirror kt_point_ids / meta_plate_ids into the master. Never overwrites other frames/batches. ----
    def _track_path(self, kind):
        return ("/Volumes/4 MB/annotations/kt_points.csv", "kt_point_ids") if kind == "sisterless" \
          else ("/Volumes/4 MB/annotations/meta_plate.csv".replace("meta_plate.csv","meta_plates.csv"), "meta_plate_ids")
    def _ann_hdr(self):
        return ("id,batch,video_file,phase,channel,frame,t_sec,t_hms,nearest_event,type,label,x,y,points,w,h,"
                "crop_name,apply_both,all_frames,length_um,area_um2,perimeter_um,circularity,aspect_ratio,"
                "roundness,solidity,pixel_size_um,notes").split(",")
    def _load_ann(self, path):
        return list(csv.DictReader(open(path))) if os.path.isfile(path) else []
    def _write_ann(self, path, rows):
        tmp = path + ".tmp"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self._ann_hdr(), extrasaction="ignore"); w.writeheader()
            for r in rows: w.writerow(r)
        os.replace(tmp, path)
    def _mirror_ids(self, batch, path, idcol):
        rows = self._load_ann(path)
        ids = [r["id"] for r in rows if (r.get("batch","") or "").strip() == batch and r.get("id")]
        M = "/Volumes/4 MB/ABLATION_MASTER.csv"
        mr = list(csv.reader(open(M))); cols = [c.strip() for c in mr[1]]
        if idcol not in cols: return
        ci = cols.index(idcol)
        for r in mr[2:]:
            if r and r[0].strip() == batch:
                while len(r) <= ci: r.append("")
                r[ci] = ",".join(ids); break
        tmp = M + ".tmp"
        with open(tmp, "w", newline="") as f: csv.writer(f).writerows(mr)
        os.replace(tmp, M)
    def _save_track_mark(self, p):
        b = (p.get("batch") or "").strip(); kind = p.get("kind"); frame = str(p.get("frame",""))
        if not b or kind not in ("sisterless","meta_plate"): return self._json({"ok":False},400)
        path, idcol = self._track_path(kind)
        # multi-KT (2/3-ablation): a per-chromosome kt_index lets >1 sisterless coexist on one frame.
        # Upsert key = (batch,frame,label[,kt_index]); kt_index stored in notes as "kt:N". Missing kt_index
        # => legacy single-KT behavior (upsert by batch,frame,label), so the 1-sisterless tool is unchanged.
        ki = str(p.get("kt_index","") or "").strip()
        def _ktidx(nt):
            m = re.search(r'kt:(\d+)', nt or ""); return m.group(1) if m else ""
        with _lock:
            if kind=="sisterless" and ki:
                rows = [r for r in self._load_ann(path)
                        if not ((r.get("batch","") or "").strip()==b and str(r.get("frame",""))==frame
                                 and r.get("label")==kind and _ktidx(r.get("notes",""))==ki)]
            else:
                rows = [r for r in self._load_ann(path)
                        if not ((r.get("batch","") or "").strip()==b and str(r.get("frame",""))==frame and r.get("label")==kind)]
            nid = str(max([int(r["id"]) for r in rows if str(r.get("id","")).isdigit()]+[0])+1)
            src = str(p.get("source","") or "")
            notes_val = (f"kt:{ki};" if ki else "") + (f"source:{src}" if src else "")
            rec = {c:"" for c in self._ann_hdr()}
            _ts, _thms = _real_t(b, frame, p.get("t_sec",""))
            rec.update(id=nid, batch=b, video_file=p.get("video_file",""), phase=p.get("phase",""),
                       channel=p.get("channel",""), frame=frame, t_sec=_ts, t_hms=_thms,
                       type=("kt_point" if kind=="sisterless" else "meta_plate"), label=kind,
                       x=str(p.get("x","")), y=str(p.get("y","")),
                       points=(json.dumps(p.get("points")) if p.get("points") else ""),
                       pixel_size_um=str(p.get("pixel_size_um","")), notes=notes_val)
            rows.append(rec); self._write_ann(path, rows); self._mirror_ids(b, path, idcol)
        return self._json({"ok":True,"id":nid})
    def _delete_track_mark(self, p):
        b=(p.get("batch") or "").strip(); kind=p.get("kind"); rid=str(p.get("id",""))
        if not b or kind not in ("sisterless","meta_plate") or not rid: return self._json({"ok":False},400)
        path, idcol = self._track_path(kind)
        with _lock:
            rows=[r for r in self._load_ann(path) if not (str(r.get("id",""))==rid and (r.get("batch","") or "").strip()==b)]
            self._write_ann(path, rows); self._mirror_ids(b, path, idcol)
        return self._json({"ok":True})

    def _save_annotation(self, bn, fields):
        MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
        with _lock:
            rows = list(csv.reader(open(MASTER)))
            hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
            hdr = [c.strip() for c in rows[hi]]; idx = {c: i for i, c in enumerate(hdr)}
            hit = False
            for r in rows[hi + 1:]:
                if r and r[0].strip() == bn:
                    for col, val in fields.items():
                        if col in idx:
                            while len(r) <= idx[col]: r.append("")
                            r[idx[col]] = "" if val is None else str(val)
                    hit = True; break
            if hit:
                tmp = MASTER + ".tmp"
                with open(tmp, "w", newline="") as f: csv.writer(f).writerows(rows)
                os.replace(tmp, MASTER)
                with open(os.path.join(ROOT, "_save_audit.log"), "a") as a: a.write(json.dumps({"batch": bn, "fields": fields}) + "\n")
        self._json({"ok": hit}, 200 if hit else 404)

class TS(http.server.ThreadingHTTPServer): daemon_threads = True; allow_reuse_address = True
print(f"pairing_server on http://localhost:{PORT}  root={ROOT}  store={PAIR_CSV}", flush=True)
TS(("127.0.0.1", PORT), H).serve_forever()
