#!/usr/bin/env python3
"""Tiny static file server WITH HTTP Range support (Safari requires 206 for
video playback). Serves the KT overlay gallery. Usage: serve_overlays.py [port]"""
import os, sys, http.server, socketserver

DIR = "/Volumes/5 MB/kt_tracking/overlays"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8770


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not (rng and os.path.isfile(path)):
            return super().do_GET()
        size = os.path.getsize(path)
        try:
            unit, rest = rng.split("=")
            start_s, end_s = rest.split("-")
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else size - 1
        except ValueError:
            return super().do_GET()
        start = max(0, start); end = min(end, size - 1)
        length = end - start + 1
        ctype = self.guess_type(path)
        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(chunk)


class TCP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"serving {DIR} on http://127.0.0.1:{PORT} (Range-enabled)")
    TCP(("127.0.0.1", PORT), H).serve_forever()
