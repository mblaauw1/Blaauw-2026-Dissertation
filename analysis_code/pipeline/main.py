"""Microscopy ablation pipeline.

Usage:
    python main.py 20260420
    python main.py 20260420 20260416
    python main.py 20260420 --output-root G:/my_output
    python main.py 20260420 --dry-run
"""
import argparse
import os
import sys
import time

from drives import classify_drives, pick_output_drive, pick_cache_drive
from discover import find_date_folder, build_batches
from output import is_batch_done, batch_output_dir, cleanup_cache
from process import process_batch
from spreadsheet import init_spreadsheet, log_batch


def _do_batch(args_tuple):
    """Module-level wrapper so ProcessPoolExecutor can pickle and dispatch it.
    Args:
        args_tuple: (batch, output_root)
    Returns:
        (batch, result_dict)
    """
    batch, output_root = args_tuple
    output_dir = batch_output_dir(batch.name, output_root, batch.date_str)
    t0 = time.time()
    try:
        result = process_batch(batch, output_dir)
        result['elapsed'] = time.time() - t0
    except Exception as e:
        result = {'status': f'ERROR: {e}', 'elapsed': time.time() - t0}
    return batch, result


def show_drives():
    """Print drive summary."""
    drives = classify_drives()
    print("Drives:")
    for d, info in drives.items():
        print(f"  {d}: {info['type']:10s} {info['total_gb']:>6d}GB total  {info['free_gb']:>6d}GB free"
              + (f"  ({info['unc']})" if info['unc'] else ""))


def generate_slideshow(output_dir):
    """Generate and open an HTML batch review slideshow."""
    batches = sorted([d for d in os.listdir(output_dir)
                      if os.path.isdir(os.path.join(output_dir, d))])
    if not batches:
        return

    html = ('<!DOCTYPE html>\n<html><head><title>Batch Review</title>\n'
            '<style>\n'
            'body { background: #1a1a1a; color: #eee; font-family: Arial; margin: 20px; }\n'
            'h1 { text-align: center; }\n'
            '.nav { text-align: center; margin: 20px 0; }\n'
            '.nav button { font-size: 18px; padding: 10px 30px; margin: 0 10px; cursor: pointer; }\n'
            '.time-controls { text-align: center; margin: 8px 0; }\n'
            '.time-controls button { font-size: 14px; padding: 6px 14px; margin: 0 4px; cursor: pointer; }\n'
            '.time-controls .keys { font-size: 12px; color: #888; margin-left: 12px; }\n'
            '.batch-name { text-align: center; font-size: 24px; margin: 10px 0; color: #4fc3f7; }\n'
            '.counter { text-align: center; font-size: 16px; color: #999; }\n'
            '.section-label { text-align: center; font-size: 18px; color: #ff9800; margin: 15px 0 5px; '
            'max-width: 1400px; margin-left: auto; margin-right: auto; }\n'
            '.videos { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; '
            'max-width: 1400px; margin: 0 auto; }\n'
            '.videos video { width: 100%; background: #000; }\n'
            '.label { text-align: center; font-size: 14px; color: #aaa; margin-top: 4px; }\n'
            '.meta-caption { text-align: center; font-size: 12px; color: #6bc; margin: 2px 0 6px; '
            'font-family: monospace; }\n'
            '.cell-caption { font-size: 11px; color: #8be; margin-top: 3px; '
            'font-family: monospace; line-height: 1.3; padding: 2px 4px; word-break: break-word; }\n'
            '</style></head><body>\n'
            '<h1>Batch Review</h1>\n'
            '<div class="nav">\n'
            '<button onclick="prev()">&#9664; Prev batch</button>\n'
            '<button onclick="next()">Next batch &#9654;</button>\n'
            '</div>\n'
            '<div class="time-controls">\n'
            '<button onclick="step(-1)">-1s</button>\n'
            '<button onclick="frameStep(-1)">&#9664; frame</button>\n'
            '<button onclick="togglePlay()" id="playBtn">&#9654; Play</button>\n'
            '<button onclick="frameStep(1)">frame &#9654;</button>\n'
            '<button onclick="step(1)">+1s</button>\n'
            '<button onclick="restart()">&#8634; restart</button>\n'
            '<span class="keys">keys: ←→ batch &nbsp; J/L ±1s &nbsp; , / . ±1 frame &nbsp; Space play/pause</span>\n'
            '</div>\n'
            '<div class="counter" id="counter"></div>\n'
            '<div class="batch-name" id="bname"></div>\n'
            '<div class="section-label" id="pre_label">Pre-Ablation</div>\n'
            '<div class="meta-caption" id="pre_cap"></div>\n'
            '<div class="videos" id="pre_row"></div>\n'
            '<div class="section-label" id="abl_label">Ablation</div>\n'
            '<div class="meta-caption" id="abl_cap"></div>\n'
            '<div class="videos" id="abl_row"></div>\n'
            '<div class="section-label" id="mon_label">Monitoring</div>\n'
            '<div class="meta-caption" id="mon_cap"></div>\n'
            '<div class="videos" id="mon_row"></div>\n'
            '<script>\nvar batches = [\n')

    from urllib.parse import quote
    import json as _json
    MIN_VIDEO_SIZE = 1000  # bytes — smaller means empty/stub
    def has_size(path, name):
        p = os.path.join(path, name)
        return os.path.isfile(p) and os.path.getsize(p) > MIN_VIDEO_SIZE

    def _caption_for_role(source_files, role):
        files = [s for s in source_files if s.get('role') == role]
        if not files:
            return ""
        intervals = set()
        z_slices = set()
        n_frames_total = 0
        channels = []
        for f in files:
            iv = f.get('interval_ms')
            if f.get('is_z_stack'):
                intervals.add("z-stack")
            elif iv:
                intervals.add(f"{iv/1000:.1f}s")
            else:
                intervals.add("?")
            z_slices.add(f.get('n_slices', 1) or 1)
            n_frames_total += f.get('n_frames', 0) or 0
            for ch in f.get('channels', []):
                if ch not in channels:
                    channels.append(ch)
        z_list = sorted(z_slices)
        z_part = f"z={z_list[0]}" if len(z_list) == 1 else f"z=[{','.join(str(z) for z in z_list)}]"
        iv_list = sorted(intervals)
        iv_part = f"interval {iv_list[0]}" if len(iv_list) == 1 else f"intervals [{', '.join(iv_list)}]"
        return f"{len(files)} file{'s' if len(files)!=1 else ''} · {iv_part} · {z_part} · {n_frames_total} frames · ch: {', '.join(channels)}"

    def _read_batch_meta(batch_dir, batch_name):
        json_path = os.path.join(batch_dir, f'{batch_name}_frames.json')
        if not os.path.isfile(json_path):
            return {'pre': '', 'ablation': '', 'monitoring': ''}, 30, []
        try:
            with open(json_path) as f:
                data = _json.load(f)
        except Exception:
            return {'pre': '', 'ablation': '', 'monitoring': ''}, 30, []
        sf = data.get('source_files', [])
        caps = {r: _caption_for_role(sf, r) for r in ('pre', 'ablation', 'monitoring')}
        fps = data.get('fps', 30) or 30
        return caps, fps, sf

    def _resolve_channel(label, ch_names):
        """Map slideshow label ('Phase Pre', '640 Cy5 Monitoring', 'Fluor Ablation')
        to the actual channel name in source_files.
        """
        import re as _re
        from metadata import _PHASE as _PH, _FLUOR as _FL
        first_token = label.lower().split()[0]
        if first_token in ('phase',):
            for c in ch_names:
                if any(kw in c.lower() for kw in _PH): return c
        elif first_token in ('fluor',):
            for c in ch_names:
                if any(kw in c.lower() for kw in _FL): return c
        # Try sanitized match
        safe_label = _re.sub(r'[^A-Za-z0-9]+', '_', label.split(' Pre')[0].split(' Ablation')[0].split(' Monitoring')[0]).strip('_').lower()
        for c in ch_names:
            safe_c = _re.sub(r'[^A-Za-z0-9]+', '_', c).strip('_').lower()
            if safe_c == safe_label or (safe_c in safe_label and safe_c):
                return c
        return None

    def _video_caption(label, role_suffix, source_files, fps):
        """Build per-video caption: fps, n_frames, z, interval, exposure, binning, files."""
        role_l = role_suffix.lower()
        files = [s for s in source_files if (s.get('role') or '').lower() == role_l]
        if not files:
            return ""
        all_channels = set()
        for s in files:
            for c in s.get('channels', []):
                all_channels.add(c)
        ch_name = _resolve_channel(label, sorted(all_channels))
        # Collect per-file: interval, n_z, exposure, binning for this channel
        intervals, zs, exposures, binnings, fnames = [], [], [], [], []
        for s in files:
            if ch_name and ch_name not in s.get('channels', []):
                continue
            iv = s.get('interval_ms')
            if s.get('is_z_stack'):
                intervals.append('z-stack')
            elif iv:
                intervals.append(f"{iv/1000:.1f}s")
            zs.append(str(s.get('n_slices', 1) or 1))
            cs = (s.get('channel_settings') or {}).get(ch_name, {}) if ch_name else {}
            if 'exposure_ms' in cs:
                try: exposures.append(f"{float(cs['exposure_ms']):.0f}ms")
                except Exception: exposures.append(str(cs['exposure_ms']))
            if 'binning' in cs:
                binnings.append(str(cs['binning']))
            fnames.append(s.get('source', '?'))
        def uniq_join(lst):
            seen = []
            for x in lst:
                if x not in seen: seen.append(x)
            return '/'.join(seen) if seen else '?'
        parts = [f"fps {fps}"]
        if zs: parts.append(f"z={uniq_join(zs)}")
        if intervals: parts.append(f"interval {uniq_join(intervals)}")
        if exposures: parts.append(f"exp {uniq_join(exposures)}")
        if binnings: parts.append(f"bin {uniq_join(binnings)}")
        parts.append("intensity n/a")
        line1 = " · ".join(parts)
        # File list (truncate long lists)
        if len(fnames) <= 4:
            files_line = "files: " + ", ".join(fnames)
        else:
            files_line = f"files ({len(fnames)}): " + ", ".join(fnames[:3]) + f", ... +{len(fnames)-3}"
        return line1 + " — " + files_line

    def _discover_videos(bdir, batch_name, role_suffix):
        """Return list of {label, url} for all *_<role>.mp4 in bdir > 1KB.
        Primary order: Phase, Fluor (existing pipeline outputs), then extra channels
        sorted by filename.
        """
        results = []
        # Primary phase / fluor
        for prefix, label_prefix in (('Phase', 'Phase'), ('Fluor', 'Fluor')):
            fname = f'{batch_name}_{prefix}_{role_suffix}.mp4'
            if has_size(bdir, fname):
                results.append({
                    'label': f'{label_prefix} {role_suffix}',
                    'url': quote(f'{batch_name}/{fname}'),
                })
        # Extra channels: anything matching <batch>_<other>_<role>.mp4 that's not Phase/Fluor
        seen = {'Phase', 'Fluor', 'Phase_Cropped', 'Fluor_Cropped'}
        for f in sorted(os.listdir(bdir)):
            if not f.endswith(f'_{role_suffix}.mp4'):
                continue
            mid = f[len(batch_name) + 1:-(len(role_suffix) + 5)]  # strip "<batch>_" and "_<Role>.mp4"
            if mid in seen:
                continue
            if not has_size(bdir, f):
                continue
            results.append({
                'label': f'{mid.replace("_", " ")} {role_suffix}',
                'url': quote(f'{batch_name}/{f}'),
            })
        return results

    for b in batches:
        bdir = os.path.join(output_dir, b)
        caps, fps, source_files = _read_batch_meta(bdir, b)
        pre_vids = _discover_videos(bdir, b, 'Pre')
        abl_vids = _discover_videos(bdir, b, 'Ablation')
        mon_vids = _discover_videos(bdir, b, 'Monitoring')
        # Attach per-video caption
        for v in pre_vids: v['caption'] = _video_caption(v['label'], 'Pre', source_files, fps)
        for v in abl_vids: v['caption'] = _video_caption(v['label'], 'Ablation', source_files, fps)
        for v in mon_vids: v['caption'] = _video_caption(v['label'], 'Monitoring', source_files, fps)
        html += (f'  {{name:"{b}",\n'
                 f'   pre:{_json.dumps(pre_vids)},\n'
                 f'   abl:{_json.dumps(abl_vids)},\n'
                 f'   mon:{_json.dumps(mon_vids)},\n'
                 f'   fps:{fps},\n'
                 f'   pre_cap:{_json.dumps(caps["pre"])},\n'
                 f'   abl_cap:{_json.dumps(caps["ablation"])},\n'
                 f'   mon_cap:{_json.dumps(caps["monitoring"])}}},\n')

    html += ('];\nvar idx = 0;\n'
             'function renderRow(rowId, labelId, items, captionId, captionText) {\n'
             '  var row = document.getElementById(rowId);\n'
             '  var label = document.getElementById(labelId);\n'
             '  var cap = document.getElementById(captionId);\n'
             '  row.innerHTML = "";\n'
             '  var hasAny = items && items.length > 0;\n'
             '  row.style.display = hasAny ? "" : "none";\n'
             '  label.style.display = hasAny ? "" : "none";\n'
             '  cap.style.display = hasAny ? "" : "none";\n'
             '  cap.textContent = captionText || "";\n'
             '  /* Build via innerHTML — browser parses video element same as static HTML */\n'
             '  if (items) {\n'
             '    var htmlStr = "";\n'
             '    items.forEach(function(item){\n'
             '      var src = item.url ? (\' src="\' + item.url + \'"\') : "";\n'
             '      var lab = (item.label || "").replace(/[<>&"]/g, function(c){\n'
             '        return {"<":"&lt;",">":"&gt;","&":"&amp;","\\"":"&quot;"}[c];\n'
             '      });\n'
             '      var cap = (item.caption || "").replace(/[<>&"]/g, function(c){\n'
             '        return {"<":"&lt;",">":"&gt;","&":"&amp;","\\"":"&quot;"}[c];\n'
             '      });\n'
             '      var capDiv = cap ? \'<div class="cell-caption">\' + cap + \'</div>\' : "";\n'
             '      htmlStr += \'<div><video controls muted preload="metadata" playsinline\' + src + \'></video><div class="label">\' + lab + \'</div>\' + capDiv + \'</div>\';\n'
             '    });\n'
             '    row.innerHTML = htmlStr;\n'
             '  }\n'
             '}\n'
             'function show(i) {\n'
             '  idx = Math.max(0, Math.min(i, batches.length-1));\n'
             '  var b = batches[idx];\n'
             '  document.getElementById("bname").textContent = b.name;\n'
             '  document.getElementById("counter").textContent = (idx+1)+" / "+batches.length;\n'
             '  renderRow("pre_row", "pre_label", b.pre, "pre_cap", b.pre_cap);\n'
             '  renderRow("abl_row", "abl_label", b.abl, "abl_cap", b.abl_cap);\n'
             '  renderRow("mon_row", "mon_label", b.mon, "mon_cap", b.mon_cap);\n'
             '}\n'
             'function next() { show(idx+1); }\n'
             'function prev() { show(idx-1); }\n'
             'function visibleVideos() {\n'
             '  /* Dynamic: all videos currently in any of the three rows */\n'
             '  return Array.from(document.querySelectorAll("#pre_row video, #abl_row video, #mon_row video"))\n'
             '    .filter(function(v){ return v && v.src && v.offsetParent !== null; });\n'
             '}\n'
             'function step(seconds) {\n'
             '  visibleVideos().forEach(function(v){\n'
             '    v.pause();\n'
             '    v.currentTime = Math.max(0, Math.min((v.duration || 1e9), v.currentTime + seconds));\n'
             '  });\n'
             '  document.getElementById("playBtn").innerHTML = "&#9654; Play";\n'
             '}\n'
             'var FRAME_DUR = 1/30;  /* fallback frame step (~30fps) */\n'
             'function frameStep(dir) {\n'
             '  /* Use actual batch fps when available so steps align to real frames */\n'
             '  var fps = (batches[idx] && batches[idx].fps) || 30;\n'
             '  /* Slight margin so the player snaps to a new frame instead of staying on the same one */\n'
             '  step(dir * (1.0 / fps + 0.001));\n'
             '}\n'
             'function togglePlay() {\n'
             '  var vids = visibleVideos();\n'
             '  if (vids.length === 0) return;\n'
             '  var allPaused = vids.every(function(v){ return v.paused; });\n'
             '  if (allPaused) { vids.forEach(function(v){ v.play(); }); document.getElementById("playBtn").innerHTML = "&#10074;&#10074; Pause"; }\n'
             '  else { vids.forEach(function(v){ v.pause(); }); document.getElementById("playBtn").innerHTML = "&#9654; Play"; }\n'
             '}\n'
             'function restart() {\n'
             '  visibleVideos().forEach(function(v){ v.currentTime = 0; });\n'
             '}\n'
             'document.addEventListener("keydown", function(e) {\n'
             '  if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;\n'
             '  if (e.key === "ArrowRight") { next(); return; }\n'
             '  if (e.key === "ArrowLeft") { prev(); return; }\n'
             '  if (e.key === " ") { e.preventDefault(); togglePlay(); return; }\n'
             '  if (e.key === "j" || e.key === "J") { step(-1); return; }\n'
             '  if (e.key === "l" || e.key === "L") { step(1); return; }\n'
             '  if (e.key === ",") { frameStep(-1); return; }\n'
             '  if (e.key === ".") { frameStep(1); return; }\n'
             '});\nshow(0);\n</script></body></html>')

    path = os.path.join(output_dir, 'batch_review.html')
    with open(path, 'w') as f:
        f.write(html)

    # Serve via local HTTP server with range request support for video scrubbing
    _start_slideshow_server(output_dir)


# Module-level server so it persists across generate_slideshow calls
_slideshow_server = None

def _start_slideshow_server(serve_dir):
    """Start or restart the slideshow HTTP server."""
    import http.server
    import threading
    import webbrowser
    global _slideshow_server

    class RangeHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        """HTTP handler with Range request support for video seeking."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=serve_dir, **kwargs)

        def do_GET(self):
            fpath = self.translate_path(self.path)
            if os.path.isfile(fpath) and self.headers.get('Range'):
                self._serve_range(fpath)
            else:
                super().do_GET()

        def _serve_range(self, fpath):
            file_size = os.path.getsize(fpath)
            range_header = self.headers.get('Range', '')
            try:
                range_spec = range_header.strip().split('=')[1]
                start_str, end_str = range_spec.split('-')
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1

                self.send_response(206)
                ctype = self.guess_type(fpath)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(length))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                with open(fpath, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (ConnectionError, BrokenPipeError):
                pass
            except Exception:
                super().do_GET()

        def log_message(self, format, *args):
            pass

    port = 8765

    # Shut down old server if running
    if _slideshow_server is not None:
        try:
            _slideshow_server.shutdown()
        except Exception:
            pass

    try:
        server = http.server.HTTPServer(('127.0.0.1', port), RangeHTTPRequestHandler)
        _slideshow_server = server
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        webbrowser.open(f'http://127.0.0.1:{port}/batch_review.html')
        print(f"  Slideshow: http://127.0.0.1:{port}/batch_review.html")
    except Exception as e:
        print(f"  Could not start server: {e}")
        html_path = os.path.join(serve_dir, 'batch_review.html')
        try:
            os.startfile(html_path)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description='Microscopy ablation pipeline')
    parser.add_argument('dates', nargs='+', help='Date folders to process (e.g. 20260420)')
    parser.add_argument('--output-root', default=None, help='Output directory (auto-detected if omitted)')
    parser.add_argument('--dry-run', action='store_true', help='Discover batches but do not process')
    args = parser.parse_args()

    show_drives()

    # Pick output drive: removable preferred, internal fallback
    if args.output_root is None:
        drive = pick_output_drive()
        if drive is None:
            print("ERROR: No drive with enough free space for output.")
            sys.exit(1)
        args.output_root = os.path.join(drive + os.sep, 'pipeline_output')
    print(f"\nOutput: {args.output_root}")

    # Pick cache drive: fastest internal
    cache_drive = pick_cache_drive()
    cache_root = os.path.join(cache_drive + os.sep, 'raw_tifs') if cache_drive else None
    if cache_root:
        os.makedirs(cache_root, exist_ok=True)
    print(f"Cache:  {cache_root}")

    os.makedirs(args.output_root, exist_ok=True)

    # Discover batches for each date
    all_batches = []
    for date_str in args.dates:
        print(f"\n=== {date_str} ===")
        date_path = find_date_folder(date_str)
        if date_path is None:
            continue
        batches = build_batches(date_str, date_path)
        all_batches.extend(batches)

    # Process colcemid (control) batches LAST so the ablation data renders first.
    # Stable sort: False (non-colcemid) sorts before True (colcemid); all other order kept.
    all_batches.sort(key=lambda b: 'colcemid' in b.name.lower())

    if not all_batches:
        print("\nNo batches found.")
        return

    print(f"\n=== {len(all_batches)} batches to process ===")
    for i, b in enumerate(all_batches):
        n_abl = len(b.ablations) if b.ablations else (1 if b.ablation else 0)
        abl = f"{n_abl} ablation(s)" if n_abl else "no ablation"
        pre = len(b.pre_monitoring)
        mon = len(b.monitoring)
        files = (sum(len(a.tif_files) for a in b.ablations) if b.ablations
                 else (len(b.ablation.tif_files) if b.ablation else 0)) \
            + sum(len(m.tif_files) for m in b.monitoring) + sum(len(m.tif_files) for m in b.pre_monitoring)
        print(f"  {i+1}. {b.name}  ({abl}, {pre} pre, {mon} monitoring, {files} files)")

    if args.dry_run:
        print("\nDry run — nothing processed.")
        return

    # Init spreadsheet
    csv_path = init_spreadsheet(args.output_root, all_batches[0].date_str)
    print(f"Spreadsheet: {csv_path}")

    # Parallel batch processing — workers process_batch concurrently; the main
    # process serializes log_batch calls (CSV append) and slideshow triggers.
    # Each batch writes to its own output dir, so parallel writes don't collide.
    from concurrent.futures import ProcessPoolExecutor, as_completed
    import multiprocessing
    parallel = int(os.environ.get('PIPELINE_PARALLEL', str(min(4, multiprocessing.cpu_count()))))
    print(f"\nParallel workers: {parallel}")

    completed = 0
    failed = 0
    skipped = 0
    slideshow_opened = False

    # Pre-filter: skip is_batch_done batches before submitting to the pool
    work = []
    for batch in all_batches:
        if is_batch_done(batch.name, args.output_root, batch.date_str):
            print(f"  Already processed — skipping: {batch.name}")
            skipped += 1
        else:
            work.append(batch)
    print(f"  {len(work)} batches to process, {skipped} skipped")

    if parallel <= 1 or len(work) <= 1:
        # Serial path (debugging or single-batch)
        for batch in work:
            print(f"\n{'='*60}")
            print(f"Batch: {batch.name}")
            print(f"{'='*60}")
            _, result = _do_batch((batch, args.output_root))
            elapsed = result.get('elapsed', 0)
            if result.get('status') == 'OK':
                print(f"  Completed in {elapsed:.0f}s")
                completed += 1
            else:
                print(f"  Failed after {elapsed:.0f}s: {result.get('status')}")
                failed += 1
            log_batch(csv_path, batch, result)
    else:
        with ProcessPoolExecutor(max_workers=parallel) as ex:
            futures = {ex.submit(_do_batch, (b, args.output_root)): b for b in work}
            done_count = 0
            for fut in as_completed(futures):
                try:
                    batch, result = fut.result()
                except Exception as e:
                    batch = futures[fut]
                    result = {'status': f'ERROR: {e}', 'elapsed': 0}
                elapsed = result.get('elapsed', 0)
                done_count += 1
                if result.get('status') == 'OK':
                    print(f"  [{done_count}/{len(work)}] OK in {elapsed:.0f}s: {batch.name}")
                    completed += 1
                else:
                    print(f"  [{done_count}/{len(work)}] FAIL ({result.get('status')}): {batch.name}")
                    failed += 1
                log_batch(csv_path, batch, result)

                # Trigger preview slideshow once after 3 successes
                if completed >= 3 and not slideshow_opened:
                    date_output = os.path.join(args.output_root, batch.date_str)
                    print(f"\n  >>> Generating preview slideshow...")
                    generate_slideshow(date_output)
                    slideshow_opened = True

    # Final slideshow (regenerate with all batches)
    for date_str in args.dates:
        date_output = os.path.join(args.output_root, date_str)
        if os.path.isdir(date_output):
            generate_slideshow(date_output)

    print(f"\n=== DONE: {completed} completed, {skipped} skipped, {failed} failed ===")
    print(f"Spreadsheet: {csv_path}")


if __name__ == '__main__':
    main()
