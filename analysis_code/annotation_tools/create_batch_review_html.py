#!/usr/bin/env python3
"""
Generate an HTML-based batch review viewer with video playback controls.
Replaces PPTX approach — provides scrub bar, frame stepping, speed control.

Usage:
    python create_batch_review_html.py --local-output "D:/Pipeline Output/20260325"
    python create_batch_review_html.py --local-output "D:/Pipeline Output/20260325" --port 8888
"""

import argparse
import http.server
import json
import os
import re
import sys
import threading
import webbrowser
import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Batch / MP4 discovery (mirrors create_processed_pptx_v2.py logic)
# ---------------------------------------------------------------------------

def find_individual_dirs(batch_dir):
    """Find individual_NNNN_... directories."""
    dirs = []
    for name in sorted(os.listdir(batch_dir)):
        if re.match(r"individual_\d{4}_", name):
            full = os.path.join(batch_dir, name)
            if os.path.isdir(full):
                dirs.append(full)
    return dirs


def find_panel_mp4s(ind_dir):
    """Find MP4 files for the 4 (or 6) panel positions.
    Returns dict with keys: fluor_mod, phase_mod, fluor_tight, phase_tight,
    optionally fluor2_mod, fluor2_tight.
    """
    result = {}
    files = os.listdir(ind_dir)
    mp4s = sorted([f for f in files if f.lower().endswith('.mp4')
                   and 'unlabeled' not in f.lower()],
                  key=lambda f: (0 if 'cropped' in f.lower() else 1))

    # Categorise MP4s
    for mp4 in mp4s:
        lower = mp4.lower()
        path = os.path.join(ind_dir, mp4)

        # Skip combined / overlay / full-frame
        if 'combined' in lower or 'overlay' in lower:
            continue

        # Determine channel
        is_phase = '_phase_' in lower or '_phase.' in lower
        is_fluor2 = '_fluor2_' in lower or 'fluor_2_' in lower
        is_fluor = ('_fluor_' in lower or '_fluor.' in lower or
                    'cropped_o' in lower or 'cropped_arrow' in lower) and not is_fluor2

        # Determine crop level
        is_tight = '_tight' in lower or 'tight_crop' in lower

        if is_phase and is_tight:
            result.setdefault('phase_tight', path)
        elif is_phase:
            result.setdefault('phase_mod', path)
        elif is_fluor2 and is_tight:
            result.setdefault('fluor2_tight', path)
        elif is_fluor2:
            result.setdefault('fluor2_mod', path)
        elif is_fluor and is_tight:
            result.setdefault('fluor_tight', path)
        elif is_fluor:
            result.setdefault('fluor_mod', path)

    # Check Tight_Crops subdir
    tight_dir = os.path.join(ind_dir, 'Tight_Crops')
    if os.path.isdir(tight_dir):
        for f in os.listdir(tight_dir):
            if not f.lower().endswith('.mp4'):
                continue
            lower = f.lower()
            path = os.path.join(tight_dir, f)
            is_phase = '_phase' in lower
            is_fluor2 = '_fluor2' in lower or '_fluor_2' in lower
            if is_phase and 'phase_tight' not in result:
                result['phase_tight'] = path
            elif is_fluor2 and 'fluor2_tight' not in result:
                result['fluor2_tight'] = path
            elif not is_phase and not is_fluor2 and 'fluor_tight' not in result:
                result['fluor_tight'] = path

    # Prefer _O marker over _Arrow
    for key in list(result.keys()):
        path = result[key]
        if '_arrow' in path.lower():
            alt = path.lower().replace('_arrow', '_o')
            # Check both original case and lower
            for candidate in [path.replace('_Arrow', '_O'), path.replace('_arrow', '_o')]:
                if os.path.exists(candidate):
                    result[key] = candidate
                    break

    return result


def count_ablation_events(ind_dir):
    """Count ablation events from ablation_frames.txt."""
    abl_file = os.path.join(ind_dir, 'ablation_frames.txt')
    if not os.path.isfile(abl_file):
        return 0
    count = 0
    try:
        with open(abl_file) as f:
            for line in f:
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    count += 1
    except Exception:
        pass
    return count


def get_frame_count(ind_dir):
    """Get frame count from frame_data CSV."""
    for f in os.listdir(ind_dir):
        if f.endswith('_frame_data.csv'):
            csv_path = os.path.join(ind_dir, f)
            try:
                with open(csv_path) as fh:
                    return sum(1 for _ in fh) - 1  # subtract header
            except Exception:
                pass
    return 0


def gather_batch_mp4s(batch_dir):
    """Gather MP4s for ablation + monitoring rows.
    Returns (abl_mp4s, mon_mp4s) dicts.

    Uses ablation event count to determine which individual is ablation
    (most events = ablation target). When Role column is used during
    pipeline processing, only the ablation file will have events.
    """
    ind_dirs = find_individual_dirs(batch_dir)
    if not ind_dirs:
        return None, None

    scored = []
    for d in ind_dirs:
        abl_count = count_ablation_events(d)
        frame_count = get_frame_count(d)
        mp4s = find_panel_mp4s(d)
        if mp4s:
            scored.append((abl_count, frame_count, d, mp4s))

    if not scored:
        return None, None

    # Sort: most ablation events first, then most frames
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    abl_mp4s = scored[0][3]
    abl_mp4s['dir'] = scored[0][2]
    abl_mp4s['frames'] = scored[0][1]
    abl_mp4s['ablations'] = scored[0][0]

    mon_mp4s = None
    if len(scored) > 1 and scored[1][1] > 1:
        mon_mp4s = scored[1][3]
        mon_mp4s['dir'] = scored[1][2]
        mon_mp4s['frames'] = scored[1][1]
        mon_mp4s['ablations'] = scored[1][0]

    return abl_mp4s, mon_mp4s


def discover_batches(output_dir):
    """Discover all batch folders in output directory."""
    batches = []

    # Look for batch folders (they contain individual_NNNN dirs)
    for root, dirs, files in os.walk(output_dir):
        # Check if this dir has individual_NNNN subdirs
        ind_dirs = [d for d in dirs if re.match(r'individual_\d{4}_', d)]
        if ind_dirs:
            batch_name = os.path.basename(root)
            abl, mon = gather_batch_mp4s(root)
            if abl:
                batches.append({
                    'name': batch_name,
                    'path': root,
                    'abl': abl,
                    'mon': mon,
                })
            # Don't recurse into individual dirs
            dirs[:] = [d for d in dirs if not re.match(r'individual_\d{4}_', d)]

    # Sort batches by date then batch number for consistent slide ordering
    batches.sort(key=_batch_sort_key)

    return batches


def discover_batches_multi(output_dirs):
    """Discover batches from multiple directories, deduplicating by name.

    Later directories override earlier ones (for redo output).
    """
    seen = {}
    for output_dir in output_dirs:
        if not os.path.isdir(output_dir):
            continue
        for batch in discover_batches(output_dir):
            seen[batch['name']] = batch  # last wins = redo overrides original

    batches = list(seen.values())
    batches.sort(key=_batch_sort_key)
    return batches


def _batch_sort_key(b):
    name = b['name']
    m = re.match(r'(\d{8})\s+batch\s+(\d+)', name)
    if m:
        return (m.group(1), int(m.group(2)))
    return (name, 0)


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def path_to_url(path, base_dir, root_map=None):
    """Convert absolute path to URL relative to base_dir for HTTP server.

    If root_map is provided, uses virtual root prefixes for cross-drive paths.
    root_map: {abs_root_dir: "_root_N"} — maps filesystem roots to URL prefixes.
    """
    path = os.path.normpath(path)
    base_dir = os.path.normpath(base_dir)

    # Try relative to primary base_dir first
    try:
        rel = os.path.relpath(path, base_dir)
        # On Windows, cross-drive relpath starts with drive letter or ..
        if not rel.startswith('..') and ':' not in rel:
            return rel.replace('\\', '/')
    except ValueError:
        pass  # Cross-drive on Windows raises ValueError

    # Fall back to root_map for cross-drive paths
    if root_map:
        for root_dir, prefix in root_map.items():
            root_norm = os.path.normpath(root_dir)
            if path.startswith(root_norm + os.sep) or path == root_norm:
                rel = os.path.relpath(path, root_norm).replace('\\', '/')
                return f'{prefix}/{rel}'

    # Last resort: just use relpath (may produce broken URLs)
    return os.path.relpath(path, base_dir).replace('\\', '/')


def generate_html(batches, base_dir, root_map=None):
    """Generate the HTML batch review page."""

    # Build slides data for JavaScript
    slides_data = []
    for batch in batches:
        slide = {
            'name': batch['name'],
            'path': batch['path'],
            'panels': [],
        }

        # Column labels
        has_fluor2 = 'fluor2_mod' in batch['abl']
        if has_fluor2:
            col_labels = ['Fluor1 Moderate', 'Fluor2 Moderate', 'Phase Moderate',
                         'Fluor1 Tight', 'Fluor2 Tight', 'Phase Tight']
        else:
            col_labels = ['Fluor Moderate', 'Phase Moderate', 'Fluor Tight', 'Phase Tight']

        slide['col_labels'] = col_labels
        slide['has_fluor2'] = has_fluor2

        # Rows
        rows = []
        row_data = [('Ablation', batch['abl'])]
        if batch['mon']:
            row_data.append(('Monitoring', batch['mon']))

        for row_label, mp4s in row_data:
            row = {'label': row_label, 'videos': []}
            if has_fluor2:
                keys = ['fluor_mod', 'fluor2_mod', 'phase_mod', 'fluor_tight', 'fluor2_tight', 'phase_tight']
            else:
                keys = ['fluor_mod', 'phase_mod', 'fluor_tight', 'phase_tight']

            for key in keys:
                if key in mp4s:
                    row['videos'].append({
                        'url': path_to_url(mp4s[key], base_dir, root_map),
                        'label': key,
                    })
                else:
                    row['videos'].append(None)

            rows.append(row)

        slide['rows'] = rows
        slides_data.append(slide)

    slides_json = json.dumps(slides_data, indent=2)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Batch Review Viewer</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: #1a1a1a;
    color: #eee;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    overflow: hidden;
    height: 100vh;
}}

/* Navigation bar */
.navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 16px;
    background: #2a2a2a;
    border-bottom: 1px solid #444;
    height: 36px;
    flex-shrink: 0;
}}
.navbar button {{
    background: #444;
    color: #eee;
    border: none;
    padding: 4px 14px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
}}
.navbar button:hover {{ background: #555; }}
.navbar button:disabled {{ opacity: 0.3; cursor: default; }}
.slide-info {{
    font-size: 14px;
    font-weight: 600;
}}
.slide-counter {{
    font-size: 12px;
    color: #999;
}}

/* Main content area */
.slide-container {{
    display: flex;
    flex-direction: column;
    height: calc(100vh - 36px);
    padding: 4px;
    gap: 2px;
}}

/* Title bar */
.batch-title {{
    font-size: 15px;
    font-weight: 700;
    padding: 2px 8px;
    background: #222;
    border-radius: 3px;
    flex-shrink: 0;
}}

/* Column headers */
.col-headers {{
    display: grid;
    gap: 2px;
    padding: 0 2px;
    flex-shrink: 0;
}}
.col-headers.cols-4 {{ grid-template-columns: 40px repeat(4, 1fr); }}
.col-headers.cols-6 {{ grid-template-columns: 40px repeat(6, 1fr); }}
.col-header {{
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: #aaa;
    padding: 2px 0;
}}

/* Video grid */
.video-grid {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-height: 0;
}}
.video-row {{
    flex: 1;
    display: grid;
    gap: 2px;
    min-height: 0;
}}
.video-row.cols-4 {{ grid-template-columns: 40px repeat(4, 1fr); }}
.video-row.cols-6 {{ grid-template-columns: 40px repeat(6, 1fr); }}

.row-label {{
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: rotate(180deg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: #7799cc;
    background: #222;
    border-radius: 3px;
}}

.video-cell {{
    position: relative;
    background: #111;
    border-radius: 3px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
}}
.video-cell video {{
    width: 100%;
    height: 100%;
    object-fit: contain;
}}
.video-cell .no-video {{
    color: #555;
    font-size: 12px;
    text-align: center;
}}

/* Global controls bar */
.controls-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    background: #2a2a2a;
    border-top: 1px solid #444;
    flex-shrink: 0;
    height: 44px;
}}
.controls-bar button {{
    background: #444;
    color: #eee;
    border: none;
    padding: 3px 10px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 18px;
    min-width: 34px;
}}
.controls-bar button:hover {{ background: #555; }}
.controls-bar button.active {{ background: #4488cc; }}

/* Scrub bar */
.scrub-container {{
    flex: 1;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.scrub-bar {{
    flex: 1;
    height: 6px;
    -webkit-appearance: none;
    appearance: none;
    background: #444;
    border-radius: 3px;
    outline: none;
    cursor: pointer;
}}
.scrub-bar::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    background: #4488cc;
    border-radius: 50%;
    cursor: pointer;
}}
.scrub-bar::-moz-range-thumb {{
    width: 14px;
    height: 14px;
    background: #4488cc;
    border-radius: 50%;
    cursor: pointer;
    border: none;
}}
.time-display {{
    font-size: 11px;
    color: #aaa;
    font-family: monospace;
    min-width: 80px;
}}
.speed-control {{
    display: flex;
    align-items: center;
    gap: 4px;
}}
.speed-control label {{
    font-size: 11px;
    color: #aaa;
}}
.speed-control select {{
    background: #444;
    color: #eee;
    border: 1px solid #555;
    border-radius: 3px;
    padding: 2px 4px;
    font-size: 11px;
}}
.frame-display {{
    font-size: 11px;
    color: #aaa;
    font-family: monospace;
    min-width: 60px;
    text-align: right;
}}
</style>
</head>
<body>

<div class="navbar">
    <div style="display:flex; gap:8px; align-items:center;">
        <button id="prevSlide" onclick="changeSlide(-1)">&larr; Prev</button>
        <span class="slide-counter" id="slideCounter">1 / 1</span>
        <button id="nextSlide" onclick="changeSlide(1)">Next &rarr;</button>
    </div>
    <span class="slide-info" id="slideInfo">-</span>
    <div style="display:flex; gap:8px; align-items:center;">
        <label style="font-size:11px; color:#aaa;">
            <input type="checkbox" id="syncCheck" checked onchange="toggleSync()"> Sync all
        </label>
    </div>
</div>

<div class="slide-container" id="slideContainer">
    <!-- Dynamically filled -->
</div>

<div class="controls-bar">
    <button onclick="stepFrame(-1)" title="Previous frame (Left arrow)">&#9664;&#9664;</button>
    <button id="playPauseBtn" onclick="togglePlay()" title="Play/Pause (Space)">&#9654;</button>
    <button onclick="stepFrame(1)" title="Next frame (Right arrow)">&#9654;&#9654;</button>
    <div class="scrub-container">
        <input type="range" class="scrub-bar" id="scrubBar" min="0" max="1000" value="0"
               oninput="scrubTo(this.value)" />
        <span class="time-display" id="timeDisplay">0:00 / 0:00</span>
    </div>
    <span class="frame-display" id="frameDisplay">F: 0</span>
    <div class="speed-control">
        <label>Speed:</label>
        <select id="speedSelect" onchange="setSpeed(this.value)">
            <option value="0.1">0.1x</option>
            <option value="0.25">0.25x</option>
            <option value="0.5">0.5x</option>
            <option value="1" selected>1x</option>
            <option value="2">2x</option>
            <option value="4">4x</option>
        </select>
    </div>
</div>

<script>
const SLIDES = {slides_json};

let currentSlide = 0;
let isPlaying = false;
let syncEnabled = true;
let allVideos = [];
let primaryVideo = null;
let animFrame = null;

function changeSlide(delta) {{
    currentSlide = Math.max(0, Math.min(SLIDES.length - 1, currentSlide + delta));
    renderSlide();
}}

function renderSlide() {{
    if (SLIDES.length === 0) return;
    const slide = SLIDES[currentSlide];
    const container = document.getElementById('slideContainer');

    // Update nav
    document.getElementById('slideCounter').textContent =
        `${{currentSlide + 1}} / ${{SLIDES.length}}`;
    document.getElementById('slideInfo').textContent = slide.name;
    document.getElementById('prevSlide').disabled = currentSlide === 0;
    document.getElementById('nextSlide').disabled = currentSlide === SLIDES.length - 1;

    const ncols = slide.has_fluor2 ? 6 : 4;
    const colClass = `cols-${{ncols}}`;

    let html = '';

    // Title
    html += `<div class="batch-title">${{slide.name}}</div>`;

    // Column headers
    html += `<div class="col-headers ${{colClass}}">`;
    html += '<div></div>'; // spacer for row label column
    for (const label of slide.col_labels) {{
        html += `<div class="col-header">${{label}}</div>`;
    }}
    html += '</div>';

    // Video grid
    html += '<div class="video-grid">';
    for (const row of slide.rows) {{
        html += `<div class="video-row ${{colClass}}">`;
        html += `<div class="row-label">${{row.label}}</div>`;
        for (const vid of row.videos) {{
            html += '<div class="video-cell">';
            if (vid) {{
                html += `<video preload="auto" muted controls data-url="${{vid.url}}">` +
                        `<source src="${{vid.url}}" type="video/mp4">` +
                        '</video>';
            }} else {{
                html += '<div class="no-video">No video</div>';
            }}
            html += '</div>';
        }}
        html += '</div>';
    }}
    html += '</div>';

    container.innerHTML = html;

    // Collect all video elements
    allVideos = Array.from(container.querySelectorAll('video'));
    primaryVideo = allVideos.length > 0 ? allVideos[0] : null;

    // Set up event listeners
    if (primaryVideo) {{
        primaryVideo.addEventListener('loadedmetadata', () => {{
            const scrub = document.getElementById('scrubBar');
            scrub.max = Math.floor(primaryVideo.duration * 100);
            updateTimeDisplay();
        }});
        primaryVideo.addEventListener('timeupdate', () => {{
            if (!isPlaying) return;
            updateScrub();
            updateTimeDisplay();
        }});
        primaryVideo.addEventListener('ended', () => {{
            isPlaying = false;
            document.getElementById('playPauseBtn').innerHTML = '&#9654;';
            cancelAnimationFrame(animFrame);
        }});
    }}

    // Reset playback state
    isPlaying = false;
    document.getElementById('playPauseBtn').innerHTML = '&#9654;';
    document.getElementById('scrubBar').value = 0;
    updateTimeDisplay();

    // Apply current speed
    setSpeed(document.getElementById('speedSelect').value);
}}

function togglePlay() {{
    if (!primaryVideo) return;
    isPlaying = !isPlaying;
    document.getElementById('playPauseBtn').innerHTML = isPlaying ? '&#10074;&#10074;' : '&#9654;';

    if (isPlaying) {{
        allVideos.forEach(v => v.play());
        updateLoop();
    }} else {{
        allVideos.forEach(v => v.pause());
        cancelAnimationFrame(animFrame);
    }}
}}

function updateLoop() {{
    if (!isPlaying) return;
    updateScrub();
    updateTimeDisplay();
    animFrame = requestAnimationFrame(updateLoop);
}}

function updateScrub() {{
    if (!primaryVideo || !primaryVideo.duration) return;
    const scrub = document.getElementById('scrubBar');
    scrub.value = (primaryVideo.currentTime / primaryVideo.duration) * scrub.max;
}}

function updateTimeDisplay() {{
    if (!primaryVideo) return;
    const cur = primaryVideo.currentTime || 0;
    const dur = primaryVideo.duration || 0;
    const fps = 10; // default pipeline FPS
    const frame = Math.round(cur * fps);

    document.getElementById('timeDisplay').textContent =
        `${{formatTime(cur)}} / ${{formatTime(dur)}}`;
    document.getElementById('frameDisplay').textContent = `F: ${{frame}}`;
}}

function formatTime(s) {{
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${{m}}:${{sec.toString().padStart(2, '0')}}`;
}}

function scrubTo(val) {{
    if (!primaryVideo || !primaryVideo.duration) return;
    const scrub = document.getElementById('scrubBar');
    const time = (val / scrub.max) * primaryVideo.duration;

    if (syncEnabled) {{
        allVideos.forEach(v => {{ v.currentTime = time; }});
    }} else {{
        primaryVideo.currentTime = time;
    }}
    updateTimeDisplay();
}}

function stepFrame(delta) {{
    if (!primaryVideo) return;
    const fps = 10; // pipeline default
    const step = delta / fps;
    const wasPlaying = isPlaying;

    if (isPlaying) {{
        isPlaying = false;
        document.getElementById('playPauseBtn').innerHTML = '&#9654;';
        allVideos.forEach(v => v.pause());
        cancelAnimationFrame(animFrame);
    }}

    const newTime = Math.max(0, Math.min(primaryVideo.duration,
                   primaryVideo.currentTime + step));

    if (syncEnabled) {{
        allVideos.forEach(v => {{ v.currentTime = newTime; }});
    }} else {{
        primaryVideo.currentTime = newTime;
    }}
    updateScrub();
    updateTimeDisplay();
}}

function setSpeed(val) {{
    const speed = parseFloat(val);
    allVideos.forEach(v => {{ v.playbackRate = speed; }});
}}

function toggleSync() {{
    syncEnabled = document.getElementById('syncCheck').checked;
}}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {{
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

    switch(e.key) {{
        case ' ':
            e.preventDefault();
            togglePlay();
            break;
        case 'ArrowLeft':
            e.preventDefault();
            if (e.shiftKey) {{
                changeSlide(-1);
            }} else {{
                stepFrame(-1);
            }}
            break;
        case 'ArrowRight':
            e.preventDefault();
            if (e.shiftKey) {{
                changeSlide(1);
            }} else {{
                stepFrame(1);
            }}
            break;
        case 'ArrowUp':
            e.preventDefault();
            changeSlide(-1);
            break;
        case 'ArrowDown':
            e.preventDefault();
            changeSlide(1);
            break;
    }}
}});

// Initial render
renderSlide();
</script>
</body>
</html>'''
    return html


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves from a specific directory, quietly."""

    def __init__(self, *args, directory=None, **kwargs):
        self.serve_dir = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress request logging


def serve_and_open(html_path, base_dir, port=8877, root_map=None):
    """Start HTTP server and open browser."""
    from review_server import RangeHTTPRequestHandler

    # Set multi-root mapping on the class right before creating server
    if root_map:
        RangeHTTPRequestHandler.extra_roots = root_map
        print(f"Multi-root serving enabled: {root_map}")

    handler = lambda *args, **kwargs: RangeHTTPRequestHandler(
        *args, directory=base_dir, **kwargs
    )

    server = http.server.HTTPServer(('127.0.0.1', port), handler)

    # Get relative path of HTML from base_dir
    rel_html = os.path.relpath(html_path, base_dir).replace('\\', '/')
    url = f'http://127.0.0.1:{port}/{rel_html}'

    print(f"\nBatch Review Viewer running at: {url}")
    print(f"Serving files from: {base_dir}")
    print(f"Press Ctrl+C to stop.\n")
    print("Keyboard shortcuts:")
    print("  Space        — Play / Pause")
    print("  Left/Right   — Step frame backward/forward")
    print("  Up/Down      — Previous/Next batch")
    print("  Shift+L/R    — Previous/Next batch")

    # Open browser
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.shutdown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="HTML-based batch review viewer")
    parser.add_argument('--local-output', required=True,
                       help='Primary pipeline output directory (also serves as HTTP root)')
    parser.add_argument('--extra-dirs', nargs='*', default=[],
                       help='Additional directories to scan for batches (e.g., Z: redo output)')
    parser.add_argument('--port', type=int, default=8877,
                       help='HTTP server port (default: 8877)')
    parser.add_argument('--filter', nargs='*', default=[],
                       help='Only include batches matching these names (substring match)')
    args = parser.parse_args()

    output_dir = os.path.abspath(args.local_output)
    if not os.path.isdir(output_dir):
        print(f"ERROR: Directory not found: {output_dir}")
        sys.exit(1)

    # Build list of all directories to scan (primary first, extras after)
    all_dirs = [output_dir]
    root_map = {}  # abs_path -> URL prefix for cross-drive serving
    for i, extra in enumerate(args.extra_dirs):
        extra_abs = os.path.abspath(extra)
        if os.path.isdir(extra_abs):
            all_dirs.append(extra_abs)
            root_map[extra_abs] = f'_root_{i}'
            print(f"Extra source: {extra_abs} -> /_root_{i}/")
        else:
            print(f"WARNING: Extra dir not found, skipping: {extra}")

    print(f"Scanning for batches in {len(all_dirs)} director{'y' if len(all_dirs)==1 else 'ies'}...")
    batches = discover_batches_multi(all_dirs)
    if args.filter:
        batches = [b for b in batches if any(f in b['name'] for f in args.filter)]
        print(f"Filtered to {len(batches)} batch(es) matching: {args.filter}")
    else:
        print(f"Found {len(batches)} batch(es) with videos")

    if not batches:
        print("No batches with MP4 videos found.")
        sys.exit(1)

    for b in batches:
        n_vids = sum(1 for k in b['abl'] if k.endswith('_mod') or k.endswith('_tight'))
        if b['mon']:
            n_vids += sum(1 for k in b['mon'] if k.endswith('_mod') or k.endswith('_tight'))
        print(f"  {b['name']}: {n_vids} videos")

    # Generate HTML
    html = generate_html(batches, output_dir, root_map=root_map)
    html_path = os.path.join(output_dir, 'batch_review.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nHTML saved to: {html_path}")

    # Serve and open
    serve_and_open(html_path, output_dir, port=args.port, root_map=root_map)


if __name__ == '__main__':
    main()
