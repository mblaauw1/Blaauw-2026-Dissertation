#!/usr/bin/env python3
"""HTTP server with Range request support for video scrubbing.

Supports multi-root serving: URL paths like /_root_0/..., /_root_1/... are
mapped to different filesystem directories via the `extra_roots` class attr.
"""

import http.server
import os
import posixpath
import sys
import webbrowser
from urllib.parse import unquote


class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that supports Range requests and multi-root serving."""

    # Class-level mapping: {"_root_0": "/some/path", "_root_1": "/other/path"}
    # Set before creating handler instances.
    extra_roots = {}

    def __init__(self, *args, directory=None, **kwargs):
        self._serve_dir = directory or os.getcwd()
        super().__init__(*args, directory=self._serve_dir, **kwargs)

    def log_message(self, format, *args):
        pass  # quiet

    def translate_path(self, path):
        """Override to handle /_root_N/ virtual prefixes for cross-drive serving."""
        # Decode the URL path
        decoded = unquote(path)
        if '?' in decoded:
            decoded = decoded.split('?')[0]
        # Normalize posix-style
        decoded = posixpath.normpath(decoded)

        # Check for multi-root prefix: /_root_N/rest/of/path
        for prefix, root_dir in self.__class__.extra_roots.items():
            tag = f'/{prefix}'
            if decoded == tag or decoded.startswith(tag + '/'):
                rel = decoded[len(tag):].lstrip('/')
                result = os.path.normpath(os.path.join(root_dir, rel))
                return result

        # Default: delegate to parent (which uses self.directory)
        return super().translate_path(path)

    def do_GET(self):
        # Check for Range header
        range_header = self.headers.get('Range')
        if not range_header:
            return super().do_GET()

        # Range request — use our translate_path (multi-root aware)
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404)
            return

        file_size = os.path.getsize(path)

        # Parse Range: bytes=start-end
        try:
            range_spec = range_header.replace('bytes=', '')
            parts = range_spec.split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
        except (ValueError, IndexError):
            self.send_error(416)
            return

        if start >= file_size:
            self.send_error(416)
            return

        end = min(end, file_size - 1)
        length = end - start + 1

        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
        self.send_header('Content-Length', str(length))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        try:
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = length
                buf_size = 64 * 1024
                while remaining > 0:
                    chunk = f.read(min(buf_size, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # Normal for video range requests — browser got what it needed

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()


def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8877
    html_file = sys.argv[3] if len(sys.argv) > 3 else 'batch_review_scroll.html'

    handler = lambda *args, **kwargs: RangeHTTPRequestHandler(
        *args, directory=base_dir, **kwargs
    )

    server = http.server.HTTPServer(('127.0.0.1', port), handler)
    url = f'http://127.0.0.1:{port}/{html_file}'
    print(f'Serving at {url}')
    print(f'Directory: {base_dir}')
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping.')
        server.shutdown()


if __name__ == '__main__':
    main()
