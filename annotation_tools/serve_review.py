#!/usr/bin/env python3
"""
HTTP server with Range request support for serving video files.
Required for browser video scrubbing/seeking to work.

Usage:
    python serve_review.py "D:/Pipeline Output/20260325" [--port 8877]
"""

import http.server
import os
import sys
import mimetypes
import webbrowser


class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that supports Range requests for video streaming."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        """Handle GET with Range header support."""
        # Check for Range header
        range_header = self.headers.get('Range')
        if not range_header:
            # Normal request - use parent handler
            return super().do_GET()

        # Parse range
        try:
            path = self.translate_path(self.path)
            if not os.path.isfile(path):
                self.send_error(404, "File not found")
                return

            file_size = os.path.getsize(path)
            # Parse "bytes=start-end"
            range_spec = range_header.replace('bytes=', '')
            parts = range_spec.split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1

            if start >= file_size:
                self.send_error(416, "Range not satisfiable")
                return

            end = min(end, file_size - 1)
            content_length = end - start + 1

            # Determine content type
            content_type, _ = mimetypes.guess_type(path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Send partial content response
            self.send_response(206)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(content_length))
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Send the requested byte range
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = content_length
                buf_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    chunk = f.read(min(buf_size, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                        break
                    remaining -= len(chunk)

        except Exception as e:
            self.send_error(500, str(e))

    def do_HEAD(self):
        """Handle HEAD with Accept-Ranges."""
        path = self.translate_path(self.path)
        if os.path.isfile(path):
            file_size = os.path.getsize(path)
            content_type, _ = mimetypes.guess_type(path)
            if not content_type:
                content_type = 'application/octet-stream'

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
        else:
            self.send_error(404, "File not found")

    def log_message(self, format, *args):
        """Suppress noisy request logging."""
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Video-capable HTTP server")
    parser.add_argument('directory', help='Directory to serve')
    parser.add_argument('--port', type=int, default=8877)
    parser.add_argument('--no-open', action='store_true', help='Do not open browser')
    args = parser.parse_args()

    serve_dir = os.path.abspath(args.directory)
    if not os.path.isdir(serve_dir):
        print(f"ERROR: {serve_dir} not found")
        sys.exit(1)

    # Check for batch_review.html
    html_file = os.path.join(serve_dir, 'batch_review.html')
    if not os.path.isfile(html_file):
        print(f"WARNING: batch_review.html not found in {serve_dir}")
        print("Run create_batch_review_html.py first to generate it.")

    class Handler(RangeRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=serve_dir, **kw)

    server = http.server.HTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{args.port}/batch_review.html'

    print(f"Serving: {serve_dir}")
    print(f"URL: {url}")
    print(f"Press Ctrl+C to stop.\n")

    if not args.no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == '__main__':
    main()
