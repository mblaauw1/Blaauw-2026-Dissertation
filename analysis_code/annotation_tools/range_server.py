"""range_server.py <port> <root> — event-time review server (recreated per reference_event_time_review_tool).
Byte-range video server + GET /annotations.json (prefill from master) + POST /save_annotation (merge to master).
MASTER is the authoritative /Volumes/4 MB/ABLATION_MASTER.csv; writes are atomic (.tmp + os.replace)."""
import sys, os, json, csv, threading, http.server
PORT = int(sys.argv[1]); ROOT = sys.argv[2]
MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
_lock = threading.Lock()
def _load():
    rows = list(csv.reader(open(MASTER)))
    hi = next(i for i,r in enumerate(rows) if r and r[0].strip()=="Batch Name")
    return rows, hi, [c.strip() for c in rows[hi]]
def _annotations():
    rows, hi, hdr = _load(); out = {}
    for r in rows[hi+1:]:
        if r and r[0].strip():
            out[r[0].strip()] = {hdr[i]:(r[i] if i<len(r) else "") for i in range(len(hdr))}
    return out
class H(http.server.SimpleHTTPRequestHandler):
    # HTTP/1.0 (default): keep-alive OFF → each range = a fresh connection. This is the config that WORKED for
    # <video> playback. (An HTTP/1.1 keep-alive experiment on 2026-07-13 broke playback — do NOT re-add it.)
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/annotations.json":
            body = json.dumps(_annotations()).encode()
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        fpath = self.translate_path(self.path)
        if os.path.isfile(fpath) and self.headers.get("Range"):
            return self._range(fpath)
        return super().do_GET()
    def _range(self, fpath):
        sz = os.path.getsize(fpath); rng = self.headers.get("Range","").split("=")[-1]
        a,b = (rng.split("-")+[""])[:2]; start = int(a) if a else 0; end = int(b) if b else sz-1; end = min(end, sz-1)
        self.send_response(206); self.send_header("Content-Type", self.guess_type(fpath))
        self.send_header("Content-Range", f"bytes {start}-{end}/{sz}")
        self.send_header("Content-Length", str(end-start+1)); self.send_header("Accept-Ranges","bytes"); self.end_headers()
        with open(fpath,"rb") as f:
            f.seek(start); rem = end-start+1
            while rem>0:
                chunk = f.read(min(65536, rem))
                if not chunk: break
                try: self.wfile.write(chunk)
                except (ConnectionError, BrokenPipeError): break
                rem -= len(chunk)
    def do_POST(self):
        if self.path != "/save_annotation":
            self.send_response(404); self.send_header("Content-Length","0"); self.end_headers(); return
        n = int(self.headers.get("Content-Length",0))
        try: payload = json.loads(self.rfile.read(n))
        except Exception: self.send_response(400); self.send_header("Content-Length","0"); self.end_headers(); return
        bn = payload.get("batch_name",""); fields = payload.get("fields",{}) or {}
        with _lock:
            rows, hi, hdr = _load(); idx = {c:i for i,c in enumerate(hdr)}; hit = False
            for r in rows[hi+1:]:
                if r and r[0].strip()==bn:
                    for col,val in fields.items():
                        if col in idx:
                            while len(r) <= idx[col]: r.append("")
                            r[idx[col]] = "" if val is None else str(val)
                    hit = True; break
            if hit:
                tmp = MASTER+".tmp"
                with open(tmp,"w",newline="") as f: csv.writer(f).writerows(rows)
                os.replace(tmp, MASTER)
                with open(os.path.join(ROOT,"_save_audit.log"),"a") as a: a.write(json.dumps(payload)+"\n")
        body = json.dumps({"ok":hit}).encode()
        self.send_response(200 if hit else 404); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
class TS(http.server.ThreadingHTTPServer): daemon_threads=True; allow_reuse_address=True
print(f"range_server on http://localhost:{PORT}  root={ROOT}  master={MASTER}", flush=True)
TS(("127.0.0.1",PORT), H).serve_forever()
