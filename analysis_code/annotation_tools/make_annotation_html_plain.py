#!/usr/bin/env python3
"""make_annotation_html.py — generate a touch-friendly annotation page.

For a batch already located on disk (flat or new pipeline output format),
this writes:
   <pkg_out>/<batch>/index.html      — annotation UI
   <pkg_out>/<batch>/<all-mp4s>      — copies of the pipeline-rendered MP4s
   (existing) frame_map.csv          — for Mac-side measurement round-trip

The HTML page plays the pipeline MP4s natively (so they look exactly like
your slide viewer), with a canvas overlay on each video for marking.
Annotation buttons live in a side panel. Save exports a CSV in the same
format `apply_annotations.ijm` consumes for ImageJ measurement on raw TIFs.

Designed for iPad Safari + Apple Pencil; works equally well on desktop.

USAGE
    python3 make_annotation_html.py --batch "<batch folder>" --out <pkg root>
"""

import argparse
import json
import os
import re
import shutil
import sys


# ── Layout & button definitions (single source of truth) ────────────────

KT_BUTTONS = [
    ("sisterless",      "Sisterless KT",         "#ff3030"),
    ("polar",           "Polar KT",              "#ffffff"),
    ("lagging",         "Lagging KT",            "#ff9090"),
    ("pre_abl",         "Pre-ablation KT",       "#ffd000"),
    ("post_abl",        "Post-ablation KT",      "#ff8800"),
    ("pre_abl_pair",    "Pre-ablation KT pair",  "#ffec80"),
    ("post_abl_pair",   "Post-ablation KT pair", "#ffb070"),
    ("paired_kt",       "Paired KT",             "#30ff30"),
    ("mad1_ablated",         "Mad1 ablated KT",          "#ff5500"),
    ("mad1_sister",          "Mad1 sister KT",           "#ffcc00"),
    ("mad1_attached_control","Mad1 attached control KT", "#00e0a0"),
    ("mad1_polar",           "Mad1 polar KT",            "#c060ff"),
    ("cytosol_bg",      "Cytosol background",    "#3080ff"),
]

PHASE_LABEL = {"pre": "Pre-ablation", "abl": "Ablation", "mon": "Monitoring",
               "amon": "Ablation monitoring"}

# Phase short→long directory token used in the pipeline's split-format MP4 names
# (<batch>_<Channel>_<Phase>.mp4).
PHASE_DIRS = (("pre", "Pre"), ("abl", "Ablation"), ("mon", "Monitoring"))

# Canonical channel sort order for panel layout: phase/BF first, then the
# primary fluor, then the named extra fluor channels low→high wavelength.
_CHANNEL_ORDER = {"phase": 0, "fluor": 1, "405_DAPI": 2, "488_GFP": 3,
                  "561_mCherry": 4, "640_Cy5": 5}

def channel_sort_key(ch):
    return (_CHANNEL_ORDER.get(ch, 9), ch)

def channel_label(ch_short, ch_names=None):
    """Human-readable panel label for a channel id. `ch_names` (from
    frames.json) lets the generic 'fluor' panel show its real wavelength
    (488 for live, 405/DAPI for IF)."""
    if ch_short == "phase":
        return "Phase / BF"
    if ch_short == "fluor":
        if ch_names:
            for n in ch_names:
                if "bright" not in n.lower():   # primary (first non-BF) fluor
                    return n
        return "Fluor"
    # Named extras like "488_GFP" / "561_mCherry" / "640_Cy5" → "488" / "561" / "640"
    return ch_short.split("_")[0]

# Display colors for the live channel-merge view (additive compositing).
_WAVELENGTH_COLOR = {
    "405": "#4488ff", "488": "#33ff66", "515": "#ffd23a",
    "561": "#ff5a33", "555": "#ff5a33", "640": "#c84bff", "647": "#c84bff",
}
def channel_color(ch_short, ch_names=None):
    """Hex display color for a channel in the merge view. Phase/BF = white
    (grayscale passthrough); fluor channels keyed by wavelength."""
    if ch_short == "phase":
        return "#ffffff"
    lab = channel_label(ch_short, ch_names)
    m = re.search(r'(\d{3})', lab or "")
    if m and m.group(1) in _WAVELENGTH_COLOR:
        return _WAVELENGTH_COLOR[m.group(1)]
    return "#33ff66"   # default green


MASTER_CSV = "/Volumes/4 MB/ABLATION_MASTER.csv"

ANALYSIS_TIME_COLS = [
    ("NEBD",        ["NEB Time (s)", "NEB Time", "NEBD"]),
    ("FirstCong",   ["First Congression (s)", "First Congression"]),
    ("Metaphase",   ["Metaphase Start (s)", "Metaphase Start", "Metaphase"]),
    ("Anaphase",    ["Anaphase Onset (s)", "Anaphase Onset", "Anaphase"]),
    ("Cytokinesis", ["Cytokinesis Onset (s)", "Cytokinesis"]),
]


def parse_hms(s):
    if not s: return None
    s = s.strip()
    if not s: return None
    if ":" not in s:
        try: return float(s)
        except ValueError: return None
    try:
        parts = [int(p) for p in s.split(":")]
    except ValueError:
        return None
    if len(parts) == 3: return parts[0]*3600 + parts[1]*60 + parts[2]
    if len(parts) == 2: return parts[0]*60 + parts[1]
    return None


def _read_master_row(batch_name, master_csv=MASTER_CSV):
    """Return (row_dict, header_list) for this batch, or (None, None)."""
    import csv
    if not os.path.isfile(master_csv): return None, None
    with open(master_csv, encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    header_idx = next((i for i, r in enumerate(rows)
                       if r and r[0].strip() == "Batch Name"), None)
    if header_idx is None: return None, None
    header = rows[header_idx]
    bn = batch_name.strip().lower()
    for r in rows[header_idx + 1:]:
        if r and r[0].strip().lower() == bn:
            return dict(zip(header, r)), header
    return None, None


def load_master_key_times(batch_name, master_csv=MASTER_CSV):
    """Return list of {label, t_sec} from the master spreadsheet for this batch."""
    target, _ = _read_master_row(batch_name, master_csv)
    if target is None: return []
    out = []
    for label, candidates in ANALYSIS_TIME_COLS:
        for c in candidates:
            if c in target and target[c]:
                t = parse_hms(target[c])
                if t is not None:
                    out.append({"label": label, "t_sec": t})
                    break
    return out


# Columns to surface in the metadata panel at the top of the page.
# Each tuple: (display label, list of candidate CSV column names).
METADATA_COLS = [
    ("Treatment",      ["On-Target / Off-Target"]),
    ("Phase at abl",   ["Phase of Ablations"]),
    ("Stage at abl",   ["Stage at Ablation"]),
    ("Success",        ["Ablation Success"]),
    ("Spindle damage", ["Spindle Damage"]),
    ("# Sisterless KTs (expected)", ["# Sisterless KTs"]),
    ("# Ablation events", ["# Ablation Events"]),
    ("Healthy anaphase",  ["Healthy Anaphase"]),
    ("Polar chromosomes", ["Polar Chromosomes"]),
    ("Lagging chromosomes", ["Lagging Chromosomes"]),
    ("Cell fate",       ["Cell Fate"]),
    ("Condition",       ["Condition"]),
    ("Pixel size (um)", ["Pixel Size (um)"]),
    ("Notes",           ["Notes"]),
]


def load_master_metadata(batch_name, master_csv=MASTER_CSV):
    """Return list of (display_label, value_str) for the metadata panel."""
    target, _ = _read_master_row(batch_name, master_csv)
    if target is None: return []
    out = []
    for label, candidates in METADATA_COLS:
        for c in candidates:
            if c in target:
                v = (target[c] or "").strip()
                if v:
                    out.append((label, v))
                    break
    return out


def is_excluded(batch_name, master_csv=MASTER_CSV):
    """Return (excluded_bool, reason_str)."""
    target, _ = _read_master_row(batch_name, master_csv)
    if target is None: return False, ""
    excl = (target.get("Exclude", "") or "").strip().lower()
    reason = (target.get("Exclude Reason", "") or "").strip()
    return excl in ("yes", "true", "1", "y"), reason


def find_flat_mp4s(batch_dir, batch_name):
    """Return dict (phase, channel) → mp4_path for the flat pipeline format.
    channels = {phase, fluor}."""
    out = {}
    # Per-phase split format: <batch>_<Channel>_<Phase>.mp4 — discover ALL
    # channels present (Phase, Fluor, 488_GFP, 561_mCherry, 640_Cy5, …), not
    # just phase+fluor, so multi-channel batches (Hec1 dual, IF 5-channel) get
    # a panel per channel. Canonicalize the generic Phase/Fluor tokens to the
    # short ids used everywhere else; keep named extras verbatim (e.g. 488_GFP).
    canon = {"Phase": "phase", "Fluor": "fluor"}
    try:
        listing = os.listdir(batch_dir)
    except OSError:
        listing = []
    prefix = batch_name + "_"
    for f in listing:
        if not f.endswith(".mp4") or not f.startswith(prefix): continue
        if "uncropped" in f or "nolabel" in f: continue
        stem = f[len(prefix):-4]                       # <Channel>_<Phase>
        for ph_short, ph_long in PHASE_DIRS:
            if stem.endswith("_" + ph_long):
                ch_raw = stem[:-(len(ph_long) + 1)]    # <Channel>
                if not ch_raw: break
                ch_short = canon.get(ch_raw, ch_raw)
                p = os.path.join(batch_dir, f)
                if os.path.getsize(p) > 2048:
                    out[(ph_short, ch_short)] = p
                break
    if out: return out

    # Newer single-MP4 format: <batch>_488.mp4 (fluor) and <batch>_phase.mp4
    # (phase) cover the whole experiment in one file, no Pre/Abl/Mon split.
    # Filter out *_uncropped_nolabel.mp4 helpers. We map both to ("mon", ch)
    # since the slides only render the abl + mon rows; the JS phase_ranges
    # for "mon" will span the full t_sec range from frames.json.
    NEW_FORMAT_CH = [
        ("fluor", ["488", "488_GFP", "GFP"]),
        ("phase", ["phase", "Phase", "Brightfield", "BF"]),
    ]
    for ch_short, tokens in NEW_FORMAT_CH:
        for tok in tokens:
            # Prefer exact `<batch>_<tok>.mp4`; also accept `*_MMStack*_<tok>.mp4`
            cands = [
                os.path.join(batch_dir, f"{batch_name}_{tok}.mp4"),
            ]
            for f in os.listdir(batch_dir):
                if not f.endswith(".mp4"): continue
                if "uncropped" in f or "nolabel" in f: continue
                # Pattern: <prefix>_MMStack_<...>_<tok>.mp4
                if f.endswith(f"_{tok}.mp4") and "MMStack" in f:
                    cands.append(os.path.join(batch_dir, f))
            for p in cands:
                if os.path.isfile(p) and os.path.getsize(p) > 2048:
                    out[("mon", ch_short)] = p
                    break
            if ("mon", ch_short) in out: break
    return out


def load_frame_map(pkg_dir):
    """Read the package's frame_map.csv into a dict for per-frame raw lookup."""
    p = os.path.join(pkg_dir, "frame_map.csv")
    if not os.path.isfile(p): return None
    import csv
    rows = []
    with open(p) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append(r)
    return rows


def copy_mp4s_into_package(mp4s, pkg_dir):
    """Re-encode MP4s with all-keyframe video into pkg_dir.

    The pipeline-encoded MP4s have ~1 keyframe per video, so HTML5 seeking
    snaps to the first keyframe and frame-by-frame stepping appears to do
    nothing in browsers (especially for long videos). Re-encoding with
    -g 1 -keyint_min 1 makes every frame a keyframe → frame-perfect seek.
    File size grows ~2-3× but stays well under iCloud limits.
    """
    import subprocess
    copied = {}
    for (phase, ch), src in mp4s.items():
        dst_name = f"{phase}_{ch}.mp4"
        dst = os.path.join(pkg_dir, dst_name)
        # Re-encode if dst is missing or source mtime is newer
        need = (not os.path.isfile(dst)
                or os.path.getmtime(src) > os.path.getmtime(dst))
        if need:
            print(f"  [reencode] {dst_name}…", flush=True)
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", src,
                "-c:v", "libx264",
                "-g", "1", "-keyint_min", "1",
                "-bf", "0",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-an",
                "-movflags", "+faststart",
                dst,
            ]
            try:
                subprocess.check_call(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError:
                # Fallback to a raw copy if ffmpeg fails (seeking won't be
                # frame-precise but at least the video plays)
                shutil.copy(src, dst)
        copied[(phase, ch)] = dst_name
    return copied


# ── HTML generation ─────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Annotate — __BATCH__</title>
<style>
  :root {
    --bg: #111; --fg: #e8e8e8; --panel-bg: #1c1c1c;
    --accent: #5fa8ff; --border: #2a2a2a;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: var(--bg); color: var(--fg);
               font: 14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  body { display: grid; grid-template-columns: 1fr 560px; height: 100vh; overflow: hidden; }

  /* LEFT: video grid */
  #grid-area { padding: 3px; overflow: auto; display: flex; flex-direction: column; gap: 5px; }
  h2 { margin: 0 0 4px 0; font-weight: 500; font-size: 16px; }
  .row { display: grid; gap: 4px; }
  .row[data-cols="2"] { grid-template-columns: repeat(2, 1fr); }
  .row[data-cols="3"] { grid-template-columns: repeat(3, 1fr); }
  .row-label { font-size: 12px; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
  .panel-wrap { display: flex; flex-direction: column; }
  .panel-label { background: #2a2a2a; color: #ddd; padding: 5px 8px;
                 border-radius: 6px 6px 0 0; font-size: 12px; font-weight: 500;
                 border: 1px solid var(--border); border-bottom: 0; }
  .panel { background: #000; border: 1px solid var(--border); border-radius: 0 0 6px 6px;
           position: relative; aspect-ratio: 1248 / 1056; overflow: hidden; }
  .panel video { width: 100%; height: 100%; display: block; object-fit: contain; }
  .panel canvas { position: absolute; inset: 0; width: 100%; height: 100%;
                  touch-action: none; cursor: crosshair; }

  /* Status banner (shows what tool is active and what to do) */
  #status-banner { background: #1c4a82; color: #fff; padding: 9px 14px; border-radius: 6px;
                   font-size: 14px; display: flex; align-items: center; gap: 8px; }
  #status-banner.idle { background: #2a2a2a; color: #888; }
  #status-banner.success { background: #1c6a2a; }
  /* Jump-to-key-frame bar */
  #jump-bar { background: var(--panel-bg); padding: 8px 12px; border-radius: 6px;
              display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  #jump-bar .jump-btn { padding: 6px 12px; background: #2a2a2a; border: 1px solid var(--border);
                        color: var(--fg); border-radius: 4px; cursor: pointer; font: inherit; }
  #jump-bar .jump-btn:hover { background: #3a3a3a; }
  /* Master scrubber */
  #scrubber-bar { background: var(--panel-bg); padding: 10px 12px; border-radius: 6px;
                  display: flex; align-items: center; gap: 10px; }
  #scrubber-bar input[type="range"] { flex: 1; }
  #scrubber-bar button { padding: 6px 12px; }
  #frame-label { font-variant-numeric: tabular-nums; min-width: 90px; text-align: right; }

  /* RIGHT: control panel */
  #controls { background: var(--panel-bg); border-left: 1px solid var(--border);
              padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
  #controls h3 { margin: 0; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #888; }
  .btn-group { display: grid; gap: 6px; }
  .btn { padding: 11px 12px; background: #2a2a2a; border: 1px solid var(--border);
         color: var(--fg); border-radius: 6px; cursor: pointer; text-align: left;
         font: inherit; display: flex; justify-content: space-between; align-items: center; }
  .btn:hover { background: #353535; }
  .btn.active { background: var(--accent); color: #000; border-color: var(--accent); }
  .btn .count { background: #000; color: #fff; padding: 1px 7px; border-radius: 10px;
                font-size: 11px; min-width: 18px; text-align: center; }
  .btn.active .count { background: rgba(0,0,0,.3); }
  /* Per-button mark list (sits between this button and the next) */
  .btn-marks { background: #141414; border: 1px solid var(--border); border-top: 0;
               border-radius: 0 0 6px 6px; padding: 4px; margin: -4px 0 4px 0;
               display: none; }
  .btn-marks.has-rows { display: block; }
  .mark-row { display: flex; justify-content: space-between; align-items: center;
              padding: 3px 6px; font-size: 11px; color: #ccc; border-bottom: 1px solid #222; }
  .mark-row:last-child { border: 0; }
  .mark-row .meta { font-variant-numeric: tabular-nums; }
  .mark-row .x { background: none; border: 0; color: #c44; cursor: pointer;
                 font-size: 14px; padding: 0 4px; }
  .mark-row .x:hover { color: #f88; }
  .mark-row .jump { background: none; border: 0; color: #5fa8ff; cursor: pointer;
                    font-size: 11px; padding: 0 6px; }
  .color-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
               margin-right: 7px; vertical-align: middle; }

  .action-btn { padding: 11px 12px; background: #1c4a82; border: none; color: #fff;
                border-radius: 6px; cursor: pointer; font: inherit; }
  .action-btn.danger { background: #6c1c1c; }
  .action-btn.subtle { background: #2a2a2a; }

  /* Annotation list */
  #ann-list { max-height: 200px; overflow: auto; background: #181818;
              border: 1px solid var(--border); border-radius: 6px; padding: 6px; }
  .ann-row { display: grid; grid-template-columns: 1fr auto; gap: 6px;
             padding: 4px 6px; border-bottom: 1px solid var(--border);
             font-size: 12px; align-items: center; }
  .ann-row:last-child { border: 0; }
  .ann-row .del { background: none; border: 0; color: #c44; cursor: pointer;
                  font-size: 14px; padding: 0 4px; }
  .ann-row .del:hover { color: #f88; }

  textarea { width: 100%; min-height: 60px; background: #181818; color: var(--fg);
             border: 1px solid var(--border); border-radius: 4px; padding: 6px; font: inherit; }
  select { background: #181818; color: var(--fg); border: 1px solid var(--border);
           border-radius: 4px; padding: 4px; }
  label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
</style>
</head>
<body>

<div id="grid-area">
  <div id="status-banner" class="idle">Pick a tool from the right panel, then click/drag on a video.</div>
  <div id="jump-bar"></div>
  <div id="scrubber-bar">
    <button id="play-pause">▶</button>
    <button class="jump-btn" id="step-back" title="◀ frame back (← key)">◀</button>
    <input type="range" id="scrubber" min="0" max="1" step="0.01" value="0">
    <button class="jump-btn" id="step-fwd" title="frame forward ▶ (→ key)">▶</button>
    <span id="frame-label">frame —/—</span>
    <span id="time-label">--:--:--</span>
  </div>
  __GRID__
</div>

<div id="controls">
  <div>
    <h3>Tool</h3>
    <div class="btn-group" id="tool-buttons">
      __KT_BUTTONS__
      <button class="btn" data-tool="pole"><span><span class="color-dot" style="background:#c050ff"></span>Spindle pole</span><span class="count" data-count="pole">0</span></button>
      <div class="btn-marks" data-marks-for="pole"></div>
      <button class="btn" data-tool="meta_plate"><span><span class="color-dot" style="background:#80ff80"></span>Metaphase plate (line)</span><span class="count" data-count="meta_plate">0</span></button>
      <div class="btn-marks" data-marks-for="meta_plate"></div>
      <button class="btn" data-tool="lagging_length"><span><span class="color-dot" style="background:#ff8c1a"></span>Lagging KT length (pole&ndash;pole axis)</span><span class="count" data-count="lagging_length">0</span></button>
      <div class="btn-marks" data-marks-for="lagging_length"></div>
      <button class="btn" data-tool="lagging_width"><span><span class="color-dot" style="background:#19e6d2"></span>Lagging KT width</span><span class="count" data-count="lagging_width">0</span></button>
      <div class="btn-marks" data-marks-for="lagging_width"></div>
      <button class="btn" data-tool="chromo_line"><span><span class="color-dot" style="background:#00d4ff"></span>Chromosome line</span><span class="count" data-count="chromo_line">0</span></button>
      <div class="btn-marks" data-marks-for="chromo_line"></div>
      <button class="btn" data-tool="cell_outline"><span><span class="color-dot" style="background:#ff30ff"></span>Cell outline</span><span class="count" data-count="cell_outline">0</span></button>
      <div class="btn-marks" data-marks-for="cell_outline"></div>
    </div>
  </div>
  <div>
    <h3>Cell outline stage</h3>
    <select id="outline-stage">
      <option value="meta">Metaphase</option>
      <option value="nebd">NEBD</option>
      <option value="abl">Ablation</option>
      <option value="ana">Anaphase</option>
      <option value="other">Other</option>
    </select>
  </div>
  <div>
    <h3>Batch flags</h3>
    <label><input type="checkbox" id="flag-example"> Mark as example</label>
    <button class="action-btn subtle" id="flag-timestrip">⌖ Mark this frame as timestrip</button>
    <textarea id="batch-notes" placeholder="Batch notes (free text)…"></textarea>
  </div>
  <div>
    <h3>Saved marks</h3>
    <div id="ann-list"></div>
  </div>
  <div class="btn-group">
    <button class="action-btn" id="save-csv">⬇ Download annotations CSV</button>
    <button class="action-btn subtle" id="load-csv">⬆ Load existing CSV…</button>
    <input type="file" id="load-input" accept=".csv" style="display:none">
    <button class="action-btn danger" id="clear-all">Clear all marks</button>
  </div>
  <div style="margin-top:auto; font-size:11px; color:#666;">
    Batch: __BATCH__<br>
    Saves to: <code>__BATCH___annotations.csv</code>
  </div>
</div>

<script>
console.log('[annotate] script loaded for batch:', '__BATCH__');
const BATCH = "__BATCH__";
const PANEL_DIMS = { w: 1248, h: 1056 };   // original cropped pixel space
const KEY_TIMES    = __KEY_TIMES__;      // [{label, t_sec}, ...] from master CSV
const PHASE_STARTS = __PHASE_STARTS__;   // {pre,abl,mon → t_sec at which that MP4 begins}
const PHASE_FRAMES = __PHASE_FRAMES__;   // {pre,abl,mon → frame count in that MP4}
console.log('[annotate] KEY_TIMES:', KEY_TIMES);
console.log('[annotate] PHASE_STARTS:', PHASE_STARTS);

// State — declared early so init-time callbacks (e.g. ResizeObserver
// firing redrawPanel) don't hit TDZ ReferenceErrors.
const annotations = [];
let nextId = 1;
let currentTool = null;

// ── Status banner feedback ──
const status = document.getElementById('status-banner');
function setStatus(text, kind) {
  status.textContent = text;
  status.className = kind || '';
  if (kind === 'success') setTimeout(() => { if (currentTool) showToolHint(); else status.className = 'idle'; }, 1500);
}
function showToolHint() {
  if (!currentTool) { setStatus('Pick a tool from the right panel, then click/drag on a video.', 'idle'); return; }
  if (currentTool.type === 'kt_point')      setStatus(`Click on a video to mark a ${currentTool.label} KT.`, '');
  else if (currentTool.type === 'polar_track') setStatus(`Click to mark a polar-KT track point.`, '');
  else if (currentTool.type === 'chromo_line') setStatus(`Drag freehand on a video to trace a chromosome line.`, '');
  else if (currentTool.type === 'cell_outline') setStatus(`Drag freehand on a video to trace the cell outline.`, '');
  else if (currentTool.type === 'lagging_length') setStatus(`Drag a line along the pole–pole axis to measure lagging-KT length. The line stays visible after you draw it.`, '');
  else if (currentTool.type === 'lagging_width') setStatus(`Drag a line across the lagging KT to measure its width. The line stays visible after you draw it.`, '');
  else setStatus(`Tool active: ${currentTool.type}`, '');
}

// ── Synced playback across panels ──
const videos = Array.from(document.querySelectorAll('video'));
let isScrubbing = false;
function setMasterTime(frac) {
  // frac in [0,1] -> put EACH video at that fraction of ITS OWN duration, so a short clip (ablation) is never
  // pinned at its end once the scrubber passes its length. Every phase stays scrubbable/steppable throughout.
  frac = Math.max(0, Math.min(1, frac));
  videos.forEach(v => { const target = frac * (v.duration || 0); if (Math.abs(v.currentTime - target) > 0.03) v.currentTime = target; });
  updateScrubLabel(frac);
}
function getDuration() {
  return Math.max(...videos.map(v => v.duration || 0));
}
// Per-video info computed once metadata loads (different phases are
// encoded at different fps by the pipeline: abl is short/fast, mon is
// long/slow with more compressed playback fps).
const videoInfo = new Map();   // video el → { phase, totalFrames, fps }
function fpsForVideo(v) {
  const info = videoInfo.get(v);
  if (info) return info.fps;
  return 6;   // fallback
}
function getFps() {
  // Used for the master scrubber's frame counter; pick the longest video's fps.
  let best = 6;
  videos.forEach(v => {
    const info = videoInfo.get(v);
    if (info && v.duration === getDuration()) best = info.fps;
  });
  return best;
}
const scrubber = document.getElementById('scrubber');
const playPause = document.getElementById('play-pause');
const frameLabel = document.getElementById('frame-label');
const timeLabel = document.getElementById('time-label');
function updateScrubLabel(frac) {
  frac = Math.max(0, Math.min(1, frac));
  scrubber.max = 1; scrubber.value = frac.toFixed(4);
  const d = getDuration();
  const fps = getFps();
  const t = frac * d;
  const frame = Math.round(t * fps) + 1;
  const totalFrames = Math.round(d * fps);
  frameLabel.textContent = `frame ${frame}/${totalFrames}`;
  const fmt = (s) => {
    const sign = s < 0 ? '-' : ''; s = Math.abs(s);
    const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = Math.floor(s%60);
    return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
  };
  timeLabel.textContent = fmt(t);
}
scrubber.addEventListener('input', e => { isScrubbing = true; setMasterTime(parseFloat(e.target.value)); });
scrubber.addEventListener('change', e => { isScrubbing = false; });
playPause.addEventListener('click', () => {
  if (videos[0]?.paused) { videos.forEach(v => v.play()); playPause.textContent = '⏸'; }
  else { videos.forEach(v => v.pause()); playPause.textContent = '▶'; }
});
videos.forEach(v => {
  v.addEventListener('timeupdate', () => { if (!isScrubbing) updateScrubLabel(v.currentTime); });
  v.addEventListener('loadedmetadata', () => {
    const phase = v.closest('.panel')?.dataset.phase;
    const totalFrames = (PHASE_FRAMES && PHASE_FRAMES[phase]) || 0;
    const fps = totalFrames > 0 && v.duration > 0
              ? totalFrames / v.duration : 6;
    videoInfo.set(v, { phase, totalFrames, fps });
    console.log(`[fps] ${phase}: ${totalFrames} frames / ${v.duration.toFixed(2)}s = ${fps.toFixed(2)} fps`);
    updateScrubLabel(0);
  });
});

// ── Canvas overlay setup per panel ──
const panels = Array.from(document.querySelectorAll('.panel'));
panels.forEach(panel => {
  const canvas = panel.querySelector('canvas');
  const video  = panel.querySelector('video');
  const phase   = panel.dataset.phase;
  const channel = panel.dataset.channel;

  // Resize canvas backing to its visible dimensions (HiDPI safe)
  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    redrawPanel(panel);
  };
  new ResizeObserver(resize).observe(canvas);
  resize();

  // Coordinate mapping: canvas px → original panel px (PANEL_DIMS)
  panel._toPanelCoords = (clientX, clientY) => {
    const rect = canvas.getBoundingClientRect();
    const x = (clientX - rect.left) / rect.width  * PANEL_DIMS.w;
    const y = (clientY - rect.top)  / rect.height * PANEL_DIMS.h;
    return { x, y };
  };
  panel._toCanvasCoords = (xp, yp) => {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    return { x: xp / PANEL_DIMS.w * canvas.width, y: yp / PANEL_DIMS.h * canvas.height };
  };

  // Pointer handling: point click for KT/track; drag for line/outline
  let drawing = null;  // { tool, points, label, panel, frame }
  canvas.addEventListener('pointerdown', e => {
    e.preventDefault();
    const tool = currentTool;
    if (!tool) return;
    const pt = panel._toPanelCoords(e.clientX, e.clientY);
    const frame = Math.round(video.currentTime * getFps()) + 1;
    if (tool.type === 'kt_point' || tool.type === 'polar_track') {
      addAnnotation({ type: tool.type, label: tool.label, frame,
                      x: pt.x, y: pt.y, panel: `${phase}_${channel}` });
    } else if (tool.type === 'chromo_line' || tool.type === 'cell_outline') {
      drawing = { tool, points: [[pt.x, pt.y]], panel, frame, label: tool.label };
      canvas.setPointerCapture(e.pointerId);
    }
  });
  canvas.addEventListener('pointermove', e => {
    if (!drawing) return;
    const pt = panel._toPanelCoords(e.clientX, e.clientY);
    drawing.points.push([pt.x, pt.y]);
    redrawPanel(panel);
    // Draw current path
    const ctx = canvas.getContext('2d');
    ctx.beginPath();
    drawing.points.forEach((p, i) => {
      const c = panel._toCanvasCoords(p[0], p[1]);
      if (i === 0) ctx.moveTo(c.x, c.y); else ctx.lineTo(c.x, c.y);
    });
    ctx.strokeStyle = drawing.tool.type === 'chromo_line' ? '#00d4ff' : '#ff30ff';
    ctx.lineWidth = 3;
    ctx.stroke();
  });
  canvas.addEventListener('pointerup', e => {
    if (!drawing) return;
    const d = drawing; drawing = null;
    canvas.releasePointerCapture(e.pointerId);
    if (d.points.length < 2) return;
    addAnnotation({
      type: d.tool.type,
      label: d.tool.type === 'cell_outline'
             ? document.getElementById('outline-stage').value
             : d.label,
      frame: d.frame,
      points: d.points,
      panel: `${phase}_${channel}`
    });
  });
});

// ── Tool selection ──
const toolButtons = Array.from(document.querySelectorAll('.btn[data-tool]'));
toolButtons.forEach(b => {
  b.addEventListener('click', () => {
    toolButtons.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    const t = b.dataset.tool;
    if (t.startsWith('kt:')) {
      currentTool = { type: 'kt_point', label: t.slice(3) };
    } else {
      currentTool = { type: t, label: t };  // label set later for cell_outline
    }
    showToolHint();
  });
});

// ── Annotation store (declared at top of script for TDZ safety) ──
function addAnnotation(ann) {
  ann.id = nextId++;
  ann.notes = '';
  annotations.push(ann);
  updateCounts();
  renderList();
  redrawAllPanels();
  autosave();
  setStatus(`✓ saved #${ann.id} ${ann.type.replace('_',' ')} [${ann.label}] on frame ${ann.frame}`, 'success');
}
function deleteAnnotation(id) {
  const i = annotations.findIndex(a => a.id === id);
  if (i >= 0) annotations.splice(i, 1);
  updateCounts(); renderList(); redrawAllPanels(); autosave();
}
function updateCounts() {
  const counts = {};
  annotations.forEach(a => {
    const key = a.type === 'kt_point' ? `kt:${a.label}` : a.type;
    counts[key] = (counts[key] || 0) + 1;
  });
  document.querySelectorAll('.count').forEach(el => {
    el.textContent = counts[el.dataset.count] || 0;
  });
  // Render per-button mark lists (so you see what you've marked for each
  // tool right beneath its button, with delete + jump shortcuts).
  document.querySelectorAll('.btn-marks').forEach(host => {
    const key = host.dataset.marksFor;
    host.innerHTML = '';
    const matching = annotations.filter(a => {
      const k = a.type === 'kt_point' ? `kt:${a.label}` : a.type;
      return k === key;
    });
    if (matching.length === 0) { host.classList.remove('has-rows'); return; }
    host.classList.add('has-rows');
    for (const a of matching) {
      const row = document.createElement('div');
      row.className = 'mark-row';
      const meta = document.createElement('span');
      meta.className = 'meta';
      meta.textContent = `#${a.id} · f${a.frame} · ${a.panel || '–'}`;
      const buttons = document.createElement('span');
      const jump = document.createElement('button');
      jump.className = 'jump';
      jump.textContent = '↗';
      jump.title = 'jump to this frame';
      jump.addEventListener('click', () => {
        const t = (a.frame - 1) / getFps();
        setMasterTime(t);
      });
      const del = document.createElement('button');
      del.className = 'x';
      del.textContent = '×';
      del.title = 'delete this mark';
      del.addEventListener('click', () => deleteAnnotation(a.id));
      buttons.appendChild(jump);
      buttons.appendChild(del);
      row.appendChild(meta);
      row.appendChild(buttons);
      host.appendChild(row);
    }
  });
}
function renderList() {
  const host = document.getElementById('ann-list');
  host.innerHTML = '';
  if (annotations.length === 0) {
    host.innerHTML = '<div style="color:#666;text-align:center;padding:8px">no marks yet</div>';
    return;
  }
  // Most recent first
  for (let i = annotations.length - 1; i >= 0; i--) {
    const a = annotations[i];
    const row = document.createElement('div');
    row.className = 'ann-row';
    row.innerHTML = `<span>#${a.id} ${a.type.replace('_', ' ')} [${a.label}] f=${a.frame} @ ${a.panel}</span>
                     <button class="del" title="delete">×</button>`;
    row.querySelector('.del').addEventListener('click', () => deleteAnnotation(a.id));
    host.appendChild(row);
  }
}
function redrawPanel(panel) {
  const ctx = panel.querySelector('canvas').getContext('2d');
  ctx.clearRect(0, 0, panel.querySelector('canvas').width, panel.querySelector('canvas').height);
  const myKey = `${panel.dataset.phase}_${panel.dataset.channel}`;
  const current = Math.round((panel.querySelector('video').currentTime || 0) * getFps()) + 1;
  for (const a of annotations) {
    if (a.panel !== myKey) continue;
    // For KT points: always visible. For lines/outlines: show on their frame.
    // ALL annotations are frame-scoped: only visible on the frame they
    // were placed on. This matches the user's mental model (each frame
    // is a distinct biological moment).
    if (a.frame !== current) continue;
    if (a.type === 'kt_point' || a.type === 'polar_track') {
      const c = panel._toCanvasCoords(a.x, a.y);
      ctx.beginPath();
      ctx.arc(c.x, c.y, 9, 0, Math.PI * 2);
      ctx.strokeStyle = colorForLabel(a);
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif';
      ctx.fillText(`#${a.id}`, c.x + 12, c.y - 8);
    } else if (a.points) {
      ctx.beginPath();
      a.points.forEach((p, i) => {
        const c = panel._toCanvasCoords(p[0], p[1]);
        if (i === 0) ctx.moveTo(c.x, c.y); else ctx.lineTo(c.x, c.y);
      });
      ctx.strokeStyle = a.type === 'chromo_line' ? '#00d4ff' : '#ff30ff';
      ctx.lineWidth = 3;
      ctx.stroke();
    }
  }
}
function redrawAllPanels() { panels.forEach(redrawPanel); }
videos.forEach(v => v.addEventListener('timeupdate', redrawAllPanels));

function colorForLabel(a) {
  const map = {
    sisterless:'#ff3030', polar:'#ffffff', lagging:'#ff9090',
    pre_abl:'#ffd000', post_abl:'#ff8800', paired_kt:'#30ff30',
    cytosol_bg:'#3080ff'
  };
  return map[a.label] || '#ffff00';
}

// ── CSV save/load ──
function csvEscape(s) {
  if (s == null) return '';
  s = String(s);
  return /[,"\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function buildCsv() {
  const header = "id,image_file,type,label,frame,x,y,points,length_um,area_um2,perimeter_um,circularity,aspect_ratio,roundness,solidity,pixel_size_um,notes";
  const rows = [header];
  for (const a of annotations) {
    const points = a.points
      ? '[' + a.points.map(p => `[${p[0].toFixed(2)},${p[1].toFixed(2)}]`).join(',') + ']'
      : '';
    rows.push([
      a.id, csvEscape(`${a.panel}.tif`), a.type, csvEscape(a.label),
      a.frame,
      a.x != null ? a.x.toFixed(2) : '', a.y != null ? a.y.toFixed(2) : '',
      csvEscape(points),
      '', '', '', '', '', '', '', '0.062', csvEscape(a.notes)
    ].join(','));
  }
  return rows.join('\n');
}
document.getElementById('save-csv').addEventListener('click', () => {
  const csv = buildCsv();
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `${BATCH}_annotations.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
});
document.getElementById('load-csv').addEventListener('click', () => {
  document.getElementById('load-input').click();
});
document.getElementById('load-input').addEventListener('change', e => {
  const f = e.target.files[0]; if (!f) return;
  const reader = new FileReader();
  reader.onload = ev => {
    parseCsv(ev.target.result);
    updateCounts(); renderList(); redrawAllPanels();
  };
  reader.readAsText(f);
});
function parseCsv(txt) {
  const lines = txt.split(/\r?\n/);
  if (lines.length < 2) return;
  annotations.length = 0; nextId = 1;
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i]) continue;
    const cols = parseCsvLine(lines[i]);
    if (cols.length < 17) continue;
    let points = null;
    if (cols[7] && cols[7].startsWith('[[')) {
      try { points = JSON.parse(cols[7]); } catch (e) {}
    }
    const panel = (cols[1] || '').replace(/\.tif$/, '');
    annotations.push({
      id: parseInt(cols[0]) || nextId++,
      panel, type: cols[2], label: cols[3],
      frame: parseInt(cols[4]) || 0,
      x: cols[5] ? parseFloat(cols[5]) : null,
      y: cols[6] ? parseFloat(cols[6]) : null,
      points, notes: cols[16] || ''
    });
    nextId = Math.max(nextId, parseInt(cols[0]) + 1);
  }
}
function parseCsvLine(line) {
  const out = []; let cur = ''; let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQ) {
      if (c === '"' && line[i+1] === '"') { cur += '"'; i++; }
      else if (c === '"') inQ = false;
      else cur += c;
    } else {
      if (c === ',') { out.push(cur); cur = ''; }
      else if (c === '"') inQ = true;
      else cur += c;
    }
  }
  out.push(cur); return out;
}

document.getElementById('clear-all').addEventListener('click', () => {
  if (!confirm('Delete all annotations? (this also clears autosave)')) return;
  annotations.length = 0; nextId = 1;
  updateCounts(); renderList(); redrawAllPanels();
  localStorage.removeItem(autosaveKey());
});

// ── Frame stepping + keyboard shortcuts ──
function stepFrames(n) {
  videos.forEach(v => {
    const fps = fpsForVideo(v);
    const before = v.currentTime;
    const newT = before + n / fps;
    const clamped = Math.max(0, Math.min((v.duration || newT) - 1e-6, newT));
    v.currentTime = clamped;
    // Force a visible decode: play one frame's worth then pause.
    if (v.paused) {
      v.play().then(() => setTimeout(() => v.pause(), 20)).catch(() => {});
    }
    console.log(`[step ${n}] ${v.closest('.panel')?.dataset.phase}_${v.closest('.panel')?.dataset.channel}: `
              + `before=${before.toFixed(3)} → newT=${newT.toFixed(3)} → set=${clamped.toFixed(3)} `
              + `fps=${fps.toFixed(2)} duration=${v.duration?.toFixed(2)}`);
  });
  const lv = videos.reduce((a,b)=>((b.duration||0)>(a.duration||0)?b:a), videos[0]);
  setTimeout(() => updateScrubLabel(lv && lv.duration ? (lv.currentTime/lv.duration) : 0), 50);
  setTimeout(redrawAllPanels, 120);   // give async video seek a bit longer to finish before repaint
}
document.getElementById('step-back').addEventListener('click', () => stepFrames(-1));
document.getElementById('step-fwd' ).addEventListener('click', () => stepFrames( 1));

document.addEventListener('keydown', e => {
  // Don't intercept keys while typing in inputs
  if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowLeft')  { stepFrames(e.shiftKey ? -10 : -1); e.preventDefault(); }
  else if (e.key === 'ArrowRight') { stepFrames(e.shiftKey ?  10 :  1); e.preventDefault(); }
  else if (e.key === ' ')          { playPause.click(); e.preventDefault(); }
  else if (e.key === 'Escape')     { currentTool = null;
                                     toolButtons.forEach(x => x.classList.remove('active'));
                                     showToolHint(); }
});

// ── Jump-to-frame bar (from master CSV times) ──
const jumpBar = document.getElementById('jump-bar');
// Invert frames.json timing: for `phase`, find the video FRAME whose real
// t_sec is nearest `target`, and convert it to a seek time within video `v`
// (using v's OWN duration, since fluor/brightfield/abl/mon differ in length).
// The videos are time-compressed, so we must map through t_secs — NOT seek to
// raw elapsed seconds (that overshoots, clamping to the end of the clip).
function nearestFrameSeek(phase, target, v) {
  const ranges = BATCH_METAS[currentBatchIdx]?.phase_ranges || {};
  const ts = ranges[phase] && ranges[phase].t_secs;
  if (!ts || !ts.length || !v.duration) return null;
  let bestI = 0, bestD = Infinity;
  for (let i = 0; i < ts.length; i++) {
    const d = Math.abs(ts[i] - target);
    if (d < bestD) { bestD = d; bestI = i; }
  }
  return { vtime: (bestI / Math.max(1, ts.length - 1)) * v.duration,
           dist: bestD, frame: bestI };
}
function jumpToAbsTime(t_global) {
  // Seek EVERY video (both channels, all phases) to the frame nearest t_global
  // in ITS phase — so brightfield and fluor both move, and each phase row shows
  // its closest available frame. Track which phase actually contains t_global
  // (smallest distance) for the status readout.
  let any = false, bestPhase = null, bestDist = Infinity;
  videos.forEach(v => {
    const phase = v.closest('.panel')?.dataset.phase;
    if (!phase) return;
    const m = nearestFrameSeek(phase, t_global, v);
    if (!m) return;
    v.currentTime = m.vtime;
    any = true;
    if (m.dist < bestDist) { bestDist = m.dist; bestPhase = phase; }
  });
  if (any) {
    isScrubbing = true;
    updateScrubLabel(videos[0] ? videos[0].currentTime : 0);
    isScrubbing = false;
    const off = Math.round(bestDist);
    setStatus(`Jumped to ${fmtT(t_global)} — nearest frame in ${bestPhase}`
              + (off > 1 ? ` (Δ${off}s)` : ''), 'success');
  } else {
    // Fallback: no per-frame timing — old PHASE_STARTS bracket approach.
    const cands = Object.entries(PHASE_STARTS).map(([k,x]) => [k, parseFloat(x)]).sort((a,b)=>a[1]-b[1]);
    let ph = cands[0]?.[0] || 'abl', st = 0;
    for (const [p, s] of cands) if (t_global >= s) { ph = p; st = s; }
    const v = videos.find(vid => vid.closest('.panel')?.dataset.phase === ph);
    if (v) { v.currentTime = Math.max(0, Math.min(v.duration||0, t_global - st)); setStatus(`Jumped (approx) to ${ph}`, ''); }
    else setStatus(`No video for ${ph} phase`, '');
  }
}
function fmtT(s) {
  const sign = s<0?'-':''; s=Math.abs(s);
  const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60);
  return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}
if (KEY_TIMES.length === 0) {
  jumpBar.innerHTML = '<span style="color:#888;font-size:12px">no key times in master CSV for this batch</span>';
} else {
  jumpBar.appendChild(Object.assign(document.createElement('span'),
    { textContent: 'Jump to:', style: 'color:#888;font-size:12px;margin-right:4px' }));
  KEY_TIMES.forEach(k => {
    const b = document.createElement('button');
    b.className = 'jump-btn';
    b.textContent = `${k.label} (${fmtT(k.t_sec)})`;
    b.addEventListener('click', () => jumpToAbsTime(k.t_sec));
    jumpBar.appendChild(b);
  });
}

// ── Autosave to localStorage so refresh / accidental close doesn't lose work ──
function autosaveKey() { return `annotate:${BATCH}`; }
function autosave() {
  try { localStorage.setItem(autosaveKey(), JSON.stringify(annotations)); } catch(e) {}
}
(function loadAutosave() {
  try {
    const s = localStorage.getItem(autosaveKey());
    if (!s) return;
    const arr = JSON.parse(s);
    if (Array.isArray(arr) && arr.length) {
      annotations.push(...arr);
      nextId = Math.max(nextId, ...arr.map(a => a.id + 1));
      updateCounts(); renderList(); redrawAllPanels();
    }
  } catch (e) {}
})();

// Timestrip flag — special "annotation" with type=timestrip_frame
document.getElementById('flag-timestrip').addEventListener('click', () => {
  const frame = Math.round(videos[0].currentTime * getFps()) + 1;
  addAnnotation({ type: 'timestrip_frame', label: '', frame,
                  x: null, y: null, panel: '' });
});

// Example flag + notes — saved as batch_meta rows
function syncBatchMeta() {
  // Remove existing batch_meta of same key, then add fresh.
  for (let i = annotations.length - 1; i >= 0; i--)
    if (annotations[i].type === 'batch_meta') annotations.splice(i, 1);
  const isEx = document.getElementById('flag-example').checked;
  annotations.push({
    id: nextId++, type: 'batch_meta', label: 'use_as_example',
    frame: 0, x: null, y: null, panel: '',
    notes: isEx ? 'yes' : 'no'
  });
  const notes = document.getElementById('batch-notes').value;
  if (notes) {
    annotations.push({
      id: nextId++, type: 'batch_meta', label: 'notes',
      frame: 0, x: null, y: null, panel: '', notes
    });
  }
  updateCounts(); renderList(); autosave();
}
document.getElementById('flag-example').addEventListener('change', syncBatchMeta);
document.getElementById('batch-notes').addEventListener('input',  syncBatchMeta);
</script>
</body>
</html>
"""


def kt_button_html():
    out = []
    for label, display, color in KT_BUTTONS:
        out.append(
            f'<button class="btn" data-tool="kt:{label}">'
            f'<span><span class="color-dot" style="background:{color}"></span>{display}</span>'
            f'<span class="count" data-count="kt:{label}">0</span></button>'
            f'<div class="btn-marks" data-marks-for="kt:{label}"></div>'
        )
    return "\n      ".join(out)


def render_grid(mp4s, ch_names=None):
    """Build the grid HTML for whichever phases × channels have MP4s."""
    phases = ["pre", "abl", "mon"]
    rows_html = []
    for phase in phases:
        channels = sorted((c for (p, c) in mp4s if p == phase), key=channel_sort_key)
        cells = []
        for channel in channels:
            mp4 = mp4s.get((phase, channel))
            if not mp4:
                continue
            cells.append(
                f'<div class="panel-wrap">'
                f'<div class="panel-label">{PHASE_LABEL[phase]} · {channel_label(channel, ch_names)}</div>'
                f'<div class="panel" data-phase="{phase}" data-channel="{channel}">'
                f'<video src="{phase}_{channel}.mp4" muted playsinline preload="auto"></video>'
                f'<canvas></canvas>'
                f'</div>'
                f'</div>'
            )
        if cells:
            rows_html.append(
                f'<div><div class="row-label">{PHASE_LABEL[phase]}</div>'
                f'<div class="row" data-cols="{len(cells)}">{"".join(cells)}</div></div>'
            )
    return "\n  ".join(rows_html)


def write_html(pkg_dir, batch_name, mp4_rel,
               key_times=None, phase_starts=None, phase_frames=None):
    grid_html = render_grid(mp4_rel)
    html = (HTML_TEMPLATE
            .replace("__BATCH__", batch_name)
            .replace("__GRID__", grid_html)
            .replace("__KT_BUTTONS__", kt_button_html())
            .replace("__KEY_TIMES__",    json.dumps(key_times or []))
            .replace("__PHASE_STARTS__", json.dumps(phase_starts or {}))
            .replace("__PHASE_FRAMES__", json.dumps(phase_frames or {})))
    out = os.path.join(pkg_dir, "index.html")
    with open(out, "w") as f:
        f.write(html)
    return out


# ── Main ────────────────────────────────────────────────────────────────

MULTI_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Annotate batches</title>
<style>
  :root { --bg:#111; --fg:#e8e8e8; --panel-bg:#1c1c1c; --accent:#5fa8ff; --border:#2a2a2a; }
  * { box-sizing: border-box; }
  html,body { margin:0; padding:0; background:var(--bg); color:var(--fg);
              font: 14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  /* Movies are WIDTH-driven and fill the left column edge-to-edge (no side bars);
     the toolbar takes the other half of the width. */
  body { display:grid; grid-template-columns: 1fr 1fr; height:100vh; overflow:hidden; }
  #grid-area { padding:2px; overflow:auto; display:flex; flex-direction:column; gap:2px;
               min-height:0; }
  /* Top strip auto-sizes; the batch-section grabs whatever vertical space
     remains so the 2 phase rows always fill the rest of the viewport. */
  #top-strip { background:var(--panel-bg); padding:9px 14px; border-radius:4px;
               display:flex; align-items:center; gap:9px 14px; flex-wrap:wrap;
               font-size:18px; line-height:1.4; flex: 0 0 auto; }
  #scrubber-bar { flex: 0 0 auto; }
  .batch-section { display:flex; flex-direction:column; gap:8px; flex: 1 1 auto;
                   min-height: 0; overflow-y: auto; }
  .batch-section > div:has(> .row) { flex: 0 0 auto; min-height: 0; display:flex; flex-direction:column; }
  /* Auto-fit columns with a generous min width so movies stay LARGE (≥440px);
     rows wrap and the section scrolls vertically instead of cramming everything
     into one screen (which made panels tiny when a batch has many channels). */
  .batch-section .row { flex: 0 0 auto; min-height: 0; gap:8px;
                        grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)) !important;
                        max-height: none !important; }
  .batch-section .panel-wrap { min-height: 0; }
  /* Width-driven: panel fills its grid column, height follows the 1248:1056 aspect. */
  .batch-section .panel { aspect-ratio: 1248/1056; width: 100%; height: auto; }
  /* batch-meta-host claims a full row inside the top strip so the metadata
     chips can wrap freely across as many lines as needed. */
  #batch-meta-host { flex: 1 1 100%; display:flex; flex-wrap:wrap; gap:4px 10px;
                     align-items:center; }
  #top-strip > #batch-nav,
  #top-strip > #jump-bar,
  #top-strip > #status-banner { flex: 0 0 auto; }
  #batch-nav { display:flex; align-items:center; gap:4px; }
  #batch-nav button { padding:6px 13px; font-size:15px; background:#2a2a2a;
                      border:1px solid var(--border); color:var(--fg);
                      border-radius:3px; cursor:pointer; }
  #batch-title { font-weight:600; font-size:20px; }
  #status-banner { padding:3px 10px; border-radius:3px; font-size:14px;
                   background:transparent; color:#888; }
  #status-banner.success { background:#1c6a2a; color:#fff; }
  .row { display:grid; gap:3px; }
  .row[data-cols="1"] { grid-template-columns: 1fr; }
  .row[data-cols="2"] { grid-template-columns: repeat(2,1fr); }
  .row-label { display:none; }
  .panel-wrap { display:flex; flex-direction:column; }
  .panel-label { background:#2a2a2a; color:#ddd; padding:1px 4px;
                 border-radius:3px 3px 0 0; font-size:9px; font-weight:500;
                 border:1px solid var(--border); border-bottom:0; line-height:1.1; }
  .pc-bar { display:flex; align-items:center; justify-content:center; gap:6px;
            background:#222; border:1px solid var(--border); border-top:0;
            border-radius:0 0 3px 3px; padding:1px 4px; }
  .pc-bar .pc-btn { padding:0 8px; background:#333; color:#eee; border:1px solid var(--border);
                    border-radius:3px; font-size:11px; line-height:1.5; cursor:pointer; }
  .pc-bar .pc-btn:hover { background:#454545; }
  .pc-bar .pc-lbl { font-size:9px; color:#bbb; font-variant-numeric:tabular-nums; min-width:108px; text-align:center; }
  .pc-bar input.pc-scrub { flex:1 1 90px; min-width:70px; height:12px; cursor:pointer; }
  .merge-panel { background:#000; }
  .merge-panel canvas { position:static; width:100%; height:100%; object-fit:contain; }
  .mg-toggles { display:flex; flex-wrap:wrap; gap:4px 10px; padding:3px 5px; background:#222;
                border:1px solid var(--border); border-top:0; border-radius:0 0 3px 3px; }
  .mg-tog { display:inline-flex; align-items:center; gap:3px; font-size:10px; color:#ddd; cursor:pointer; user-select:none; }
  .mg-tog input { margin:0; cursor:pointer; }
  .mg-sw { display:inline-block; width:9px; height:9px; border-radius:2px; border:1px solid #000; }
  .panel img.mip-img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; display:none; background:#000; }
  .panel.show-mip > video { visibility:hidden; }
  .panel.show-mip img.mip-img { display:block; }
  .pc-bar .bc { display:inline-flex; align-items:center; gap:2px; color:#999; font-size:8px; }
  .pc-bar .bc input[type=range] { width:42px; height:10px; }
  .pc-bar .pc-proj { padding:0 6px; background:#3a3a55; color:#dde; border:1px solid var(--border);
                     border-radius:3px; font-size:9px; cursor:pointer; }
  .pc-bar .pc-proj.on { background:#5a5a8a; }
  .panel { background:#000; border:1px solid var(--border); border-radius:0 0 3px 3px;
           position:relative; aspect-ratio:1248/1056; overflow:hidden; }
  .panel video { width:100%; height:100%; display:block; object-fit:contain; }
  .panel canvas { position:absolute; inset:0; width:100%; height:100%;
                  touch-action:none; cursor:crosshair; }
  .batch-section > .batch-meta { display:none; }   /* hoisted into #top-strip */
  .batch-meta { display:flex; flex-wrap:wrap; gap:13px; font-size:17px;
                line-height:1.4; align-items:center; }
  .md-item .md-k { color:#888; margin-right:2px; }
  .md-item .md-v { color:#ddd; font-weight:500; }
  #jump-bar { display:flex; gap:6px; flex-wrap:wrap; align-items:center; font-size:15px; }
  #jump-bar .jump-btn { padding:6px 13px; background:#2a2a2a; border:1px solid var(--border);
                        color:var(--fg); border-radius:3px; cursor:pointer; font:inherit;
                        font-size:15px; }
  #jump-bar .jump-btn:hover { background:#3a3a3a; }
  #scrubber-bar { background:var(--panel-bg); padding:2px 6px; border-radius:3px;
                  display:flex; align-items:center; gap:6px; font-size:10px; }
  #scrubber-bar input[type="range"] { flex:1; }
  #scrubber-bar button { padding:6px 12px; }
  #frame-label { font-variant-numeric:tabular-nums; min-width:90px; text-align:right; }
  #controls { background:var(--panel-bg); border-left:1px solid var(--border);
              padding:12px 15px; overflow-y:auto; display:flex; flex-direction:column;
              gap:9px; font-size:14px; }
  #controls h3 { margin:0; font-size:16px; text-transform:uppercase; letter-spacing:.05em;
                 color:#888; padding:5px 0 3px; }
  .btn-group { display:grid; gap:6px; }
  /* Tool buttons in TWO columns (the wide toolbar). Mark-lists are display:none
     until populated (so they take no grid cell); when shown they span full width. */
  /* TOOL LIST: one button per annotation type, each with its saved marks directly beneath it.
     USER 2026-07-22: with a single narrow column this was unusable -- you had to scroll past every
     mark list to reach the next button. The section now spans the whole panel and the buttons flow
     into as many COLUMNS as fit. CSS multi-column (not grid) is used on purpose: a button and its
     .btn-marks list are SIBLINGS, so only column flow can keep the pair together, which the
     break-after/break-before rules below enforce. */
  #controls > div:first-child { flex:1 1 100%; min-width:0; }
  #tool-buttons { display:block; column-width:260px; column-gap:16px; }
  #tool-buttons .btn { width:100%; break-inside:avoid; break-after:avoid;
                       -webkit-column-break-inside:avoid; -webkit-column-break-after:avoid; }
  #tool-buttons .btn-marks { break-before:avoid; break-inside:avoid; margin-bottom:8px;
                       -webkit-column-break-before:avoid; -webkit-column-break-inside:avoid; }
  .btn { padding:13px 14px; background:#2a2a2a; border:1px solid var(--border);
         color:var(--fg); border-radius:5px; cursor:pointer; text-align:left;
         font:inherit; font-size:22px; line-height:1.2;
         display:flex; justify-content:space-between; align-items:center; gap:6px; }
  .btn:hover { background:#353535; }
  .btn.active { background:var(--accent); color:#000; border-color:var(--accent); }
  .btn .count { background:#000; color:#fff; padding:1px 8px; border-radius:10px;
                font-size:16px; min-width:22px; text-align:center; }
  .btn.active .count { background:rgba(0,0,0,.3); }
  .btn-marks { background:#141414; border:1px solid var(--border); border-top:0;
               border-radius:0 0 3px 3px; padding:3px; margin:-3px 0 3px 0; display:none;
               grid-column:1 / -1; }
  .btn-marks.has-rows { display:block; }
  .mark-row { display:flex; justify-content:space-between; align-items:center;
              padding:3px 6px; font-size:16px; color:#ccc; border-bottom:1px solid #222; }
  .mark-row:last-child { border:0; }
  .mark-row .x { background:none; border:0; color:#c44; cursor:pointer; font-size:20px; padding:0 6px; }
  .mark-row .x:hover { color:#f88; }
  .mark-row .jump { background:none; border:0; color:#5fa8ff; cursor:pointer; font-size:15px; padding:0 6px; }
  .color-dot { display:inline-block; width:13px; height:13px; border-radius:50%;
               margin-right:7px; vertical-align:middle; }
  .action-btn { padding:9px 13px; background:#1c4a82; border:none; color:#fff;
                border-radius:4px; cursor:pointer; font:inherit; font-size:16px;
                line-height:1.25; }
  .action-btn.danger { background:#6c1c1c; }
  .action-btn.subtle { background:#2a2a2a; }
  textarea { width:100%; min-height:48px; background:#181818; color:var(--fg);
             border:1px solid var(--border); border-radius:3px; padding:5px; font:inherit;
             font-size:16px; }
  select { background:#181818; color:var(--fg); border:1px solid var(--border);
           border-radius:3px; padding:5px 7px; font-size:16px; }
  label { display:flex; align-items:center; gap:7px; cursor:pointer; font-size:16px; line-height:1.3; }
  /* Cap each row's max-height so videos zoom out a bit and the metadata
     wrap-strip has more room without crushing the videos either. */
  .batch-section .row { max-height: 42vh; }
</style>
</head>
<body>

<div id="grid-area">
  <div id="top-strip">
    __NAV__
    <span id="batch-meta-host"></span>
    <div id="jump-bar"></div>
    <span id="status-banner" class="idle">Pick a tool · click/drag on a video</span>
  </div>
  <div id="scrubber-bar">
    <button id="play-pause">▶</button>
    <button class="jump-btn" id="step-back" title="◀ frame back (← key)">◀</button>
    <input type="range" id="scrubber" min="0" max="1" step="0.01" value="0">
    <button class="jump-btn" id="step-fwd" title="frame forward ▶ (→ key)">▶</button>
    <span id="frame-label">frame —/—</span>
    <span id="time-label">--:--:--</span>
  </div>
  __SECTIONS__
</div>

<div id="controls">
  <div><h3>Tool</h3>
    <div class="btn-group" id="tool-buttons">
      __KT_BUTTONS__
      <button class="btn" data-tool="pole"><span><span class="color-dot" style="background:#c050ff"></span>Spindle pole</span><span class="count" data-count="pole">0</span></button>
      <div class="btn-marks" data-marks-for="pole"></div>
      <button class="btn" data-tool="meta_plate"><span><span class="color-dot" style="background:#80ff80"></span>Metaphase plate (line)</span><span class="count" data-count="meta_plate">0</span></button>
      <div class="btn-marks" data-marks-for="meta_plate"></div>
      <button class="btn" data-tool="lagging_length"><span><span class="color-dot" style="background:#ff8c1a"></span>Lagging KT length (pole&ndash;pole axis)</span><span class="count" data-count="lagging_length">0</span></button>
      <div class="btn-marks" data-marks-for="lagging_length"></div>
      <button class="btn" data-tool="lagging_width"><span><span class="color-dot" style="background:#19e6d2"></span>Lagging KT width</span><span class="count" data-count="lagging_width">0</span></button>
      <div class="btn-marks" data-marks-for="lagging_width"></div>
      <button class="btn" data-tool="chromo_line"><span><span class="color-dot" style="background:#00d4ff"></span>Chromosome line</span><span class="count" data-count="chromo_line">0</span></button>
      <div class="btn-marks" data-marks-for="chromo_line"></div>
      <button class="btn" data-tool="cell_outline"><span><span class="color-dot" style="background:#ff30ff"></span>Cell outline</span><span class="count" data-count="cell_outline">0</span></button>
      <div class="btn-marks" data-marks-for="cell_outline"></div>
      <button class="btn" data-tool="crop_box"><span><span class="color-dot" style="background:#ffe000"></span>Crop box</span><span class="count" data-count="crop_box">0</span></button>
      <div class="btn-marks" data-marks-for="crop_box"></div>
    </div>
  </div>
  <div><h3>Crop box options</h3>
    <div style="font-size:11px;color:#999;line-height:1.4;margin-bottom:4px;">
      <b>Drag</b> on a movie to define a new box (its size is stored).
      <b>Click</b> to stamp the stored size at that spot. These are annotations
      only — the movie is never actually cropped.
    </div>
    <input type="text" id="crop-name" placeholder="Crop name (for sorting later)…"
           style="width:100%;box-sizing:border-box;margin-bottom:5px;">
    <label><input type="checkbox" id="crop-apply-both"> Apply to <b>both</b> monitoring &amp; ablation (default: only this movie type)</label>
    <label><input type="checkbox" id="crop-all-frames"> Apply to <b>all frames</b> of the movie (default: only this frame)</label>
    <div id="crop-stored-size" style="font-size:11px;color:#ffe000;padding:3px 0;">stored size: (none yet — drag once to set)</div>
    <button class="action-btn subtle" id="crop-clear-size">Clear stored size</button>
  </div>
  <div><h3>Batch flags (current batch)</h3>
    <label><input type="checkbox" id="flag-example"> Mark as example</label>
    <label><input type="checkbox" id="flag-reclass-prophase"> Consider reclassifying prometaphase → prophase</label>
    <label><input type="checkbox" id="flag-timestrip-candidate"> Timestrip candidate</label>
    <button class="action-btn subtle" id="flag-timestrip">⌖ Mark this frame as timestrip</button>
    <textarea id="batch-notes" placeholder="Batch notes…"></textarea>
  </div>
  <div><h3>Saved marks (this batch)</h3>
    <div id="ann-list"></div>
  </div>
  <div id="save-indicator" style="font-size:11px;color:#888;text-align:center;padding:4px;">
    autosave: master CSV on disk
  </div>
  <div class="btn-group">
    <button class="action-btn" id="save-csv">⬇ Download ALL batches' annotations (combined CSV)</button>
    <button class="action-btn subtle" id="load-csv">⬆ Load existing CSV…</button>
    <input type="file" id="load-input" accept=".csv" style="display:none">
    <button class="action-btn danger" id="clear-batch">Clear marks for this batch</button>
  </div>
</div>

<script>
console.log('[annotate] multi-batch index loaded');
const BATCH_METAS = __BATCH_METAS__;   // [{name, key_times}, ...]
const PANEL_DIMS = { w: 1248, h: 1056 };

// ── Crop-box: a persisted "stored size" (video px) that carries from slide to
// slide AND across server restarts (localStorage is keyed by origin). It is NOT
// auto-placed; you stamp it where you choose. Drag defines a new size; a plain
// click stamps the stored size centered on the click.
const CROP_SIZE_KEY = 'kt_crop_size';
let cropSize = (() => { try { return JSON.parse(localStorage.getItem(CROP_SIZE_KEY) || 'null'); } catch(e){ return null; } })();
function setCropSize(w, h) {
  cropSize = { w, h };
  try { localStorage.setItem(CROP_SIZE_KEY, JSON.stringify(cropSize)); } catch(e){}
  updateCropSizeReadout();
}
function updateCropSizeReadout() {
  const el = document.getElementById('crop-stored-size');
  if (!el) return;
  el.textContent = cropSize
    ? `stored size: ${Math.round(cropSize.w)}×${Math.round(cropSize.h)} px (persists across slides & restarts)`
    : 'stored size: (none yet — drag once to set)';
}

// Per-batch annotation state, keyed by batch name.
const annByBatch = new Map();          // batch_name → Array<annotation>
const nextIdByBatch = new Map();
BATCH_METAS.forEach(m => { annByBatch.set(m.name, []); nextIdByBatch.set(m.name, 1); });

let currentTool = null;
let currentBatchIdx = 0;
const sections = Array.from(document.querySelectorAll('.batch-section'));

function currentBatch() { return BATCH_METAS[currentBatchIdx]?.name || ''; }
function currentAnns() { return annByBatch.get(currentBatch()) || []; }
function nextId() {
  const b = currentBatch();
  const id = nextIdByBatch.get(b) || 1;
  nextIdByBatch.set(b, id + 1);
  return id;
}
function currentVideos() {
  const sec = sections[currentBatchIdx];
  return sec ? Array.from(sec.querySelectorAll('video')) : [];
}
function currentPanels() {
  const sec = sections[currentBatchIdx];
  return sec ? Array.from(sec.querySelectorAll('.panel')) : [];
}

// ── Status banner ──
const status = document.getElementById('status-banner');
function setStatus(text, kind) {
  status.textContent = text;
  status.className = kind || '';
  if (kind === 'success') setTimeout(() => { showToolHint(); }, 1500);
}
function showToolHint() {
  if (!currentTool) { setStatus('Pick a tool from the right panel, then click/drag on a video.', 'idle'); return; }
  const t = currentTool;
  if (t.type === 'crop_box')      setStatus(`Crop box: DRAG to define a new size, or CLICK to stamp the stored size. (annotation only — no real cropping)`, '');
  else if (t.type === 'kt_point')      setStatus(`Click on a video to mark a ${t.label} KT.`, '');
  else if (t.type === 'polar_track') setStatus(`Click to mark a polar-KT track point.`, '');
  else if (t.type === 'chromo_line') setStatus(`Drag freehand on a video to trace a chromosome line.`, '');
  else if (t.type === 'cell_outline') setStatus(`Drag freehand on a video to trace the cell outline.`, '');
}

// ── Per-video fps + scrubber/state ──
const videoInfo = new Map();
function fpsForVideo(v) { return (videoInfo.get(v) || {}).fps || 6; }
function getDuration() { return Math.max(0, ...currentVideos().map(v => v.duration || 0)); }
function getMasterFps() {
  let best = 6;
  currentVideos().forEach(v => {
    const info = videoInfo.get(v);
    if (info && v.duration === getDuration()) best = info.fps;
  });
  return best;
}
let isScrubbing = false;
function setMasterTime(t) {
  // Scrub the reference (densest) channel to t, then snap the other channels to
  // the frame nearest its real t_sec so all panels stay time-aligned even when
  // channels were captured at different rates.
  const ref = refVideo();
  if (ref) {
    if (Math.abs(ref.currentTime - t) > 0.02) ref.currentTime = t;
    syncTargetFromTime(ref);
    const tsec = videoCurTsec(ref);
    currentVideos().forEach(v => { if (v !== ref) seekVideoToTsec(v, tsec); });
  } else {
    currentVideos().forEach(v => {
      if (Math.abs(v.currentTime - t) > 0.05) v.currentTime = t;
      syncTargetFromTime(v);
    });
  }
  updateScrubLabel(t);
  setTimeout(() => { updatePanelLabels(); redrawAllPanels(); }, 60);
}
const scrubber = document.getElementById('scrubber');
const playPause = document.getElementById('play-pause');
const frameLabel = document.getElementById('frame-label');
const timeLabel = document.getElementById('time-label');
function updateScrubLabel(t) {
  const d = getDuration();
  scrubber.max = d.toFixed(3); scrubber.value = t.toFixed(3);
  const fps = getMasterFps();
  const frame = Math.round(t * fps) + 1;
  const total = Math.round(d * fps);
  frameLabel.textContent = `frame ${frame}/${total}`;
  const fmt = s => {
    if (s == null || !isFinite(s)) return '--:--:--';
    const sign = s<0?'-':''; s = Math.abs(s);
    const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60);
    return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
  };
  // Show experiment-anchored t_sec (t=0 = first ablation) instead of
  // video-local time. Pick the furthest-along visible video and map via
  // its phase's t_secs array from frames.json (or synthesized fallback).
  let tsec = null;
  let bestV = null, bestT = -1, bestPhase = null;
  currentVideos().forEach(v => {
    if ((v.currentTime||0) >= bestT) {
      bestT = v.currentTime||0; bestV = v;
      bestPhase = v.closest('.panel')?.dataset.phase;
    }
  });
  const ranges = BATCH_METAS[currentBatchIdx]?.phase_ranges || {};
  if (bestV && bestPhase && ranges[bestPhase]?.t_secs?.length) {
    const ts = ranges[bestPhase].t_secs;
    const idx = Math.round((bestV.currentTime / (bestV.duration||1)) * (ts.length - 1));
    tsec = ts[Math.max(0, Math.min(ts.length-1, idx))];
  }
  timeLabel.textContent = (tsec != null) ? `t=${fmt(tsec)}` : fmt(t);
}
scrubber.addEventListener('input', e => { isScrubbing = true; setMasterTime(parseFloat(e.target.value)); });
scrubber.addEventListener('change', () => { isScrubbing = false; });
playPause.addEventListener('click', () => {
  const vs = currentVideos();
  if (vs[0]?.paused) { vs.forEach(v => v.play()); playPause.textContent = '⏸'; }
  else { vs.forEach(v => v.pause()); playPause.textContent = '▶'; }
});

function bindVideoMetadata() {
  // Wire metadata + timeupdate handlers for ALL videos across batches.
  document.querySelectorAll('video').forEach(v => {
    if (videoInfo.has(v)) return;
    v.addEventListener('timeupdate', () => {
      if (!isScrubbing && v === currentVideos()[0]) updateScrubLabel(v.currentTime);
      if (v.closest('.batch-section') === sections[currentBatchIdx]) redrawAllPanels();
      // Keep the frame-stepper's target in sync with the real playhead so the
      // first arrow click after playback advances exactly one frame (not the
      // gap between the stale target and where the video actually paused).
      syncTargetFromTime(v);
    });
    // Same sync after any seek (jump-to-event, scrub) and on pause/end.
    // CRUCIAL: also redraw the overlay here. setMasterTime() schedules a redraw
    // on a 60ms timeout, but a video seek is async and can complete LATER than
    // that (cold videos loading from disk) — so the 60ms redraw paints the OLD
    // frame's marks and the overlay then stays frozen on it. Redrawing when the
    // seek actually finishes keeps outlines/marks on the correct frame.
    ['seeked', 'pause', 'ended'].forEach(ev =>
      v.addEventListener(ev, () => {
        syncTargetFromTime(v);
        if (v.closest('.batch-section') === sections[currentBatchIdx]) redrawAllPanels();
      }));
    v.addEventListener('loadedmetadata', () => {
      // Real encoded fps is embedded as data-fps at build time (ffprobe). This
      // MUST be the true per-video rate (6/8/13/… fps differ per batch); a
      // wrong fps makes a single step land across >1 real frame. Fall back to
      // the typical re-encode rate only if the attribute is missing.
      const fps = parseFloat(v.dataset.fps) || 9;
      videoInfo.set(v, { fps });
    });
  });
}

// ── Panel canvas pointer handling ──
function setupPanelCanvases() {
  document.querySelectorAll('.panel').forEach(panel => {
    if (panel.dataset.bound) return;
    panel.dataset.bound = '1';
    // Merge panels have no video and aren't annotatable — just keep their
    // composite re-rendered on resize.
    if (panel.dataset.merge) {
      new ResizeObserver(() => renderMergePanel(panel)).observe(panel.querySelector('canvas'));
      renderMergePanel(panel);
      return;
    }
    const canvas = panel.querySelector('canvas');
    const video  = panel.querySelector('video');
    const phase   = panel.dataset.phase;
    const channel = panel.dataset.channel;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width  = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
      redrawPanel(panel);
    };
    new ResizeObserver(resize).observe(canvas);
    resize();
    // Coordinate mapping: ALWAYS expressed in the original video's pixel
    // space (= cropped TIF pixel space, typically 1248×1056). The Mac-side
    // ImageJ macro then adds crop_fixed_x/y from frame_map.csv to map to
    // the raw TIF coords. CSS object-fit:contain can letterbox the video
    // inside the canvas; we account for that so clicks in the dark bars
    // don't get scaled into the video pixel range.
    panel._toPanelCoords = (clientX, clientY) => {
      const rect = canvas.getBoundingClientRect();
      // Fall back to PANEL_DIMS only until video metadata loads
      const vw = video.videoWidth  || PANEL_DIMS.w;
      const vh = video.videoHeight || PANEL_DIMS.h;
      const containerAR = rect.width / rect.height;
      const videoAR = vw / vh;
      let dispW, dispH, offX, offY;
      if (videoAR > containerAR) {
        dispW = rect.width;  dispH = rect.width / videoAR;
        offX = 0;            offY = (rect.height - dispH) / 2;
      } else {
        dispH = rect.height; dispW = rect.height * videoAR;
        offY = 0;            offX = (rect.width - dispW) / 2;
      }
      const cx = clientX - rect.left - offX;
      const cy = clientY - rect.top  - offY;
      // Clamp clicks in letterbox to nearest video edge (or return null to ignore)
      const x = Math.max(0, Math.min(vw - 1, cx / dispW * vw));
      const y = Math.max(0, Math.min(vh - 1, cy / dispH * vh));
      return { x, y, inside: cx >= 0 && cx <= dispW && cy >= 0 && cy <= dispH };
    };
    panel._toCanvasCoords = (xp, yp) => {
      const vw = video.videoWidth  || PANEL_DIMS.w;
      const vh = video.videoHeight || PANEL_DIMS.h;
      // Inverse of _toPanelCoords: video px → canvas-internal px (with HiDPI)
      const rect = canvas.getBoundingClientRect();
      const containerAR = rect.width / rect.height;
      const videoAR = vw / vh;
      let dispW, dispH, offX, offY;
      if (videoAR > containerAR) {
        dispW = rect.width;  dispH = rect.width / videoAR;
        offX = 0;            offY = (rect.height - dispH) / 2;
      } else {
        dispH = rect.height; dispW = rect.height * videoAR;
        offY = 0;            offX = (rect.width - dispW) / 2;
      }
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (offX + xp / vw * dispW) * scaleX,
        y: (offY + yp / vh * dispH) * scaleY,
      };
    };
    let drawing = null;
    canvas.addEventListener('pointerdown', e => {
      e.preventDefault();
      const tool = currentTool; if (!tool) return;
      const pt = panel._toPanelCoords(e.clientX, e.clientY);
      if (!pt.inside) { setStatus('Click landed in the letterbox area — ignored.', ''); return; }
      const fps = fpsForVideo(video);
      const frame = Math.round((video.currentTime||0) * fps) + 1;
      const t_sec = videoToT(video, phase);
      if (tool.type === 'crop_box') {
        drawing = { tool, isCrop: true, start: [pt.x, pt.y], cur: [pt.x, pt.y],
                    panel, frame, t_sec };
        canvas.setPointerCapture(e.pointerId);
        return;
      }
      const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole');
      if (isPoint) {
        addAnnotation({ type: tool.type, label: tool.label, frame,
                        x: pt.x, y: pt.y, panel: `${phase}_${channel}`,
                        phase, channel, t_sec });
      } else {
        drawing = { tool, points: [[pt.x, pt.y]], panel, frame, label: tool.label,
                    t_sec };
        canvas.setPointerCapture(e.pointerId);
      }
    });
    canvas.addEventListener('pointermove', e => {
      if (!drawing) return;
      const pt = panel._toPanelCoords(e.clientX, e.clientY);
      if (drawing.isCrop) {
        drawing.cur = [pt.x, pt.y];
        redrawPanel(panel);
        const ctx = canvas.getContext('2d');
        const a = panel._toCanvasCoords(drawing.start[0], drawing.start[1]);
        const b = panel._toCanvasCoords(pt.x, pt.y);
        ctx.strokeStyle = '#ffe000'; ctx.lineWidth = 2; ctx.setLineDash([6,4]);
        ctx.strokeRect(Math.min(a.x,b.x), Math.min(a.y,b.y),
                       Math.abs(b.x-a.x), Math.abs(b.y-a.y));
        ctx.setLineDash([]);
        return;
      }
      drawing.points.push([pt.x, pt.y]);
      redrawPanel(panel);
      const ctx = canvas.getContext('2d');
      ctx.beginPath();
      drawing.points.forEach((p,i) => {
        const c = panel._toCanvasCoords(p[0], p[1]);
        if (i===0) ctx.moveTo(c.x,c.y); else ctx.lineTo(c.x,c.y);
      });
      ctx.strokeStyle = drawing.tool.type === 'chromo_line' ? '#00d4ff'
                      : drawing.tool.type === 'meta_plate' ? '#80ff80'
                      : drawing.tool.type === 'lagging_length' ? '#ff8c1a'
                      : drawing.tool.type === 'lagging_width' ? '#19e6d2'
                      : '#ff30ff';
      ctx.lineWidth = 3; ctx.stroke();
    });
    canvas.addEventListener('pointerup', e => {
      if (!drawing) return;
      const d = drawing; drawing = null;
      canvas.releasePointerCapture(e.pointerId);
      if (d.isCrop) {
        const [x0,y0] = d.start, [x1,y1] = d.cur;
        const movedW = Math.abs(x1-x0), movedH = Math.abs(y1-y0);
        let bx, by, bw, bh;
        if (movedW < 4 && movedH < 4) {            // click → stamp stored size
          if (!cropSize) { setStatus('No stored crop size yet — DRAG once to define one.', ''); return; }
          bw = cropSize.w; bh = cropSize.h; bx = x0 - bw/2; by = y0 - bh/2;
        } else {                                    // drag → define new size
          bx = Math.min(x0,x1); by = Math.min(y0,y1); bw = movedW; bh = movedH;
          setCropSize(bw, bh);
        }
        const vw = video.videoWidth || PANEL_DIMS.w, vh = video.videoHeight || PANEL_DIMS.h;
        bx = Math.max(0, Math.min(vw - bw, bx)); by = Math.max(0, Math.min(vh - bh, by));
        const cname = (document.getElementById('crop-name')?.value || '').trim();
        const applyBoth = document.getElementById('crop-apply-both')?.checked ? 1 : 0;
        const allFrames = document.getElementById('crop-all-frames')?.checked ? 1 : 0;
        addAnnotation({ type:'crop_box', label: cname || 'crop', crop_name: cname,
                        frame: d.frame, x: bx, y: by, w: bw, h: bh,
                        panel: `${phase}_${channel}`, phase, channel, t_sec: d.t_sec,
                        apply_both: applyBoth, all_frames: allFrames });
        return;
      }
      if (d.points.length < 2) return;
      addAnnotation({
        type: d.tool.type,
        label: d.label,
        frame: d.frame, points: d.points, panel: `${phase}_${channel}`,
        phase, channel, t_sec: d.t_sec
      });
    });
  });
}

// ── Tool selection ──
const toolButtons = Array.from(document.querySelectorAll('.btn[data-tool]'));
toolButtons.forEach(b => {
  b.addEventListener('click', () => {
    toolButtons.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    const t = b.dataset.tool;
    if (t.startsWith('kt:')) currentTool = { type:'kt_point', label: t.slice(3) };
    else currentTool = { type: t, label: t };
    showToolHint();
  });
});

// ── Annotation store / rendering ──
function addAnnotation(ann) {
  ann.id = nextId();
  ann.notes = '';
  if (ann.t_sec != null) {
    ann.t_hms = fmtHMS(ann.t_sec);
    ann.nearest_event = findNearestEvent(ann.t_sec);
  }
  currentAnns().push(ann);
  updateCounts(); renderList(); redrawAllPanels(); autosave();
  const ev = ann.nearest_event ? ` · ${ann.nearest_event}` : '';
  setStatus(`✓ saved #${ann.id} ${ann.type.replace('_',' ')} [${ann.label}] on frame ${ann.frame}${ev}`, 'success');
}
function deleteAnnotation(id) {
  const arr = currentAnns();
  const i = arr.findIndex(a => a.id === id);
  if (i >= 0) arr.splice(i,1);
  updateCounts(); renderList(); redrawAllPanels(); autosave();
}
function updateCounts() {
  const counts = {};
  currentAnns().forEach(a => {
    const key = a.type === 'kt_point' ? `kt:${a.label}` : a.type;
    counts[key] = (counts[key]||0) + 1;
  });
  document.querySelectorAll('.count').forEach(el => {
    el.textContent = counts[el.dataset.count] || 0;
  });
  document.querySelectorAll('.btn-marks').forEach(host => {
    const key = host.dataset.marksFor;
    host.innerHTML = '';
    const matching = currentAnns().filter(a => {
      const k = a.type === 'kt_point' ? `kt:${a.label}` : a.type;
      return k === key;
    });
    if (matching.length === 0) { host.classList.remove('has-rows'); return; }
    host.classList.add('has-rows');
    matching.forEach(a => {
      const row = document.createElement('div');
      row.className = 'mark-row';
      row.innerHTML = `<span class="meta">#${a.id} · f${a.frame} · ${a.panel||'–'}</span>`;
      const buttons = document.createElement('span');
      const jump = document.createElement('button');
      jump.className = 'jump'; jump.textContent = '↗';
      jump.addEventListener('click', () => {
        const t = (a.frame - 1) / fpsForVideo(currentVideos()[0]||{});
        setMasterTime(t);
      });
      const del = document.createElement('button');
      del.className = 'x'; del.textContent = '×';
      del.addEventListener('click', () => deleteAnnotation(a.id));
      buttons.appendChild(jump); buttons.appendChild(del);
      row.appendChild(buttons);
      host.appendChild(row);
    });
  });
}
function renderList() {
  const host = document.getElementById('ann-list');
  host.innerHTML = '';
  const arr = currentAnns();
  if (arr.length === 0) { host.innerHTML = '<div style="color:#666;text-align:center;padding:8px">no marks yet</div>'; return; }
  for (let i = arr.length-1; i >= 0; i--) {
    const a = arr[i];
    const row = document.createElement('div');
    row.className = 'mark-row';
    row.innerHTML = `<span>#${a.id} ${a.type.replace('_',' ')} [${a.label}] f=${a.frame} @ ${a.panel}</span>
                     <button class="x">×</button>`;
    row.querySelector('.x').addEventListener('click', () => deleteAnnotation(a.id));
    host.appendChild(row);
  }
}
function redrawPanel(panel) {
  if (panel.dataset.merge) { renderMergePanel(panel); return; }   // merge panels draw their own composite
  const ctx = panel.querySelector('canvas').getContext('2d');
  const canvas = panel.querySelector('canvas');
  ctx.clearRect(0,0,canvas.width,canvas.height);
  const myKey = `${panel.dataset.phase}_${panel.dataset.channel}`;
  const video = panel.querySelector('video');
  const current = Math.round((video.currentTime||0) * fpsForVideo(video)) + 1;
  const myPhase = panel.dataset.phase;
  // Ablation target markers: DISABLED. The laser-fire positions from frames.json
  // (ablation_events_local) are NOT in this movie's video-pixel space, so drawing
  // them client-side via _toCanvasCoords placed the crosshair in the wrong spot.
  // The CORRECT markers are already baked into the pipeline-rendered review movies
  // (the *_Phase_Ablation.mp4 the review slideshow plays); the annotation viewer
  // should not re-derive them. Left gated so it can be re-enabled if/when the
  // ablation_events coords are mapped into video-pixel space (x_px - roi.x, etc.).
  const DRAW_CLIENT_ABLATION_MARKERS = false;
  if (DRAW_CLIENT_ABLATION_MARKERS && myPhase === 'abl') {
    const evs = BATCH_METAS[currentBatchIdx]?.ablation_events || [];
    for (const e of evs) {
      const ex = (e.x_px != null) ? e.x_px : e.x;
      const ey = (e.y_px != null) ? e.y_px : e.y;
      if (ex == null || ey == null) continue;
      const c = panel._toCanvasCoords(ex, ey);
      ctx.strokeStyle = '#ff2d2d'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(c.x, c.y, 9, 0, 2*Math.PI); ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(c.x-13, c.y); ctx.lineTo(c.x-4, c.y);
      ctx.moveTo(c.x+4, c.y);  ctx.lineTo(c.x+13, c.y);
      ctx.moveTo(c.x, c.y-13);  ctx.lineTo(c.x, c.y-4);
      ctx.moveTo(c.x, c.y+4);   ctx.lineTo(c.x, c.y+13);
      ctx.stroke();
    }
  }
  for (const a of currentAnns()) {
    if (a.type === 'crop_box') {
      // Crop applies to BOTH channels of its movie type by default; to all
      // movie types if apply_both; to its frame only unless all_frames.
      const phaseOK = a.apply_both ? true : (a.phase === myPhase);
      if (!phaseOK) continue;
      if (!a.all_frames && a.frame !== current) continue;
      const c0 = panel._toCanvasCoords(a.x, a.y);
      const c1 = panel._toCanvasCoords(a.x + a.w, a.y + a.h);
      ctx.strokeStyle = '#ffe000'; ctx.lineWidth = 2;
      ctx.strokeRect(c0.x, c0.y, c1.x - c0.x, c1.y - c0.y);
      const tag = (a.crop_name || a.label || 'crop')
                + (a.all_frames ? ' ⟳' : '') + (a.apply_both ? ' ⇄' : '');
      ctx.fillStyle = '#ffe000'; ctx.font = '12px sans-serif';
      ctx.fillText(`#${a.id} ${tag}`, c0.x + 3, c0.y - 4);
      continue;
    }
    if (a.panel !== myKey) continue;
    // WHERE to show an OUTLINE. Two regimes, picked automatically per outline:
    //  (a) STORED FRAME still valid (its timestamp ≈ the outline's, i.e. it's the
    //      nearest frame) → show on the stored frame. This is exact on movies that
    //      weren't re-rendered AND it disambiguates FROZEN-timestamp runs, where
    //      many frames share one timestamp and the timestamp alone can't tell them
    //      apart (it would collapse them onto one frame).
    //  (b) STORED FRAME stale (movie re-rendered to a different length, so the index
    //      no longer points to the right moment) → map by TIMESTAMP using the same
    //      fractional mapping that recorded it (videoToT), so it lands on the moment
    //      traced. KT/chromo keep their stored frame and are never moved.
    {
      const _ts = (a.type === 'cell_outline' && a.t_sec != null && isFinite(a.t_sec))
                  ? (BATCH_METAS[currentBatchIdx]?.phase_ranges?.[myPhase] || {}).t_secs : null;
      if (_ts && _ts.length > 1) {
        const _N = _ts.length;
        let _bi = 0, _bd = Infinity;
        for (let i = 0; i < _N; i++) { const d = Math.abs(_ts[i] - a.t_sec); if (d < _bd) { _bd = d; _bi = i; } }
        const _sf = a.frame;
        const _storedValid = (_sf >= 1 && _sf <= _N && Math.abs(_ts[_sf - 1] - a.t_sec) <= _bd + 0.5);
        if (_storedValid) {
          if (current !== _sf) continue;            // exact / frozen-run safe
        } else {
          const _curIdx = Math.round((video.currentTime / (video.duration || 1)) * (_N - 1));
          if (_curIdx !== _bi) continue;            // re-rendered: map by timestamp
        }
      } else if (a.frame !== current) continue;
    }
    const isPoint = (a.type === 'kt_point' || a.type === 'polar_track' || a.type === 'pole');
    if (isPoint) {
      const c = panel._toCanvasCoords(a.x, a.y);
      ctx.beginPath(); ctx.arc(c.x, c.y, 9, 0, Math.PI*2);
      ctx.strokeStyle = colorForLabel(a); ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif';
      ctx.fillText(`#${a.id}`, c.x+12, c.y-8);
    } else if (a.points) {
      ctx.beginPath();
      a.points.forEach((p,i) => {
        const c = panel._toCanvasCoords(p[0], p[1]);
        if (i===0) ctx.moveTo(c.x,c.y); else ctx.lineTo(c.x,c.y);
      });
      ctx.strokeStyle = a.type === 'chromo_line' ? '#00d4ff'
                      : a.type === 'meta_plate' ? '#80ff80'
                      : a.type === 'lagging_length' ? '#ff8c1a'
                      : a.type === 'lagging_width' ? '#19e6d2'
                      : '#ff30ff';
      ctx.lineWidth = 3; ctx.stroke();
    }
  }
}
function redrawAllPanels() { currentPanels().forEach(redrawPanel); renderMerges(); }
function colorForLabel(a) {
  if (a.type === 'pole')        return '#c050ff';   // spindle pole = purple
  if (a.type === 'polar_track') return '#ffa030';
  const m = { sisterless:'#ff3030', polar:'#fff', lagging:'#ff9090',
              pre_abl:'#ffd000', post_abl:'#ff8800',
              pre_abl_pair:'#ffec80', post_abl_pair:'#ffb070',
              paired_kt:'#30ff30', cytosol_bg:'#3080ff' };
  return m[a.label] || '#ff0';
}

// ── Frame stepping + keyboard ──
// Track the logical target frame per video so rapid arrow presses don't
// race against in-flight seeks. Without this, reading v.currentTime
// returns the OLD time if the previous seek hasn't completed, and 1/3
// of presses appear to do nothing.
const targetFrame = new WeakMap();   // video → integer frame index
function syncTargetFromTime(v) {
  const fps = fpsForVideo(v);
  targetFrame.set(v, Math.round((v.currentTime||0) * fps));
}
function stepFrames(n) {
  // Master step — advance ONE frame like the review slides' ◀/▶. Step each PHASE
  // independently: within a phase, advance that phase's densest channel by n frames
  // and snap its OTHER channels by t_sec (keeps a phase's multi-rate channels — e.g.
  // 488 captured 1/6 as often as phase — aligned in real time). Phases are NOT
  // cross-aligned: the ablation clip and the monitoring movie live in different time
  // domains, so snapping the short abl clip to mon's t_sec parked it on its last
  // frame (and made its frame-anchored KT/chromo marks unreachable). Stepping each
  // phase on its own timeline fixes that and makes every phase's marks navigable.
  const vids = currentVideos();
  if (!vids.length) return;
  const byPhase = {};
  vids.forEach(v => {
    const ph = (v.closest('.panel') && v.closest('.panel').dataset.phase) || '_';
    (byPhase[ph] = byPhase[ph] || []).push(v);
  });
  let globalRef = null, gn = -1;
  Object.keys(byPhase).forEach(ph => {
    const group = byPhase[ph];
    let ref = null, bn = -1;
    group.forEach(v => { const c = videoFrameCount(v); if (c > bn) { bn = c; ref = v; } });
    if (!ref) return;
    seekVideoFrame(ref, videoCurFrame(ref) + n);
    const tsec = videoCurTsec(ref);
    group.forEach(v => { if (v !== ref) seekVideoToTsec(v, tsec); });
    if (bn > gn) { gn = bn; globalRef = ref; }
  });
  if (globalRef) setTimeout(() => updateScrubLabel(globalRef.currentTime || 0), 30);
  setTimeout(() => { updatePanelLabels(); redrawAllPanels(); }, 60);
}
document.getElementById('step-back').addEventListener('click', () => stepFrames(-1));
document.getElementById('step-fwd' ).addEventListener('click', () => stepFrames( 1));
document.addEventListener('keydown', e => {
  if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowLeft')  { stepFrames(e.shiftKey ? -10 : -1); e.preventDefault(); }
  else if (e.key === 'ArrowRight') { stepFrames(e.shiftKey ?  10 :  1); e.preventDefault(); }
  else if (e.key === ' ')          { playPause.click(); e.preventDefault(); }
  else if (e.key === 'Escape')     { currentTool = null;
                                     toolButtons.forEach(x => x.classList.remove('active'));
                                     showToolHint(); }
  else if (e.key === 'n' || e.key === 'N') { goNext(); }
  else if (e.key === 'p' || e.key === 'P') { goPrev(); }
});

// ── Per-channel timelines + independent per-panel scrubbing (multi-rate aware) ──
// Multi-rate batches capture some fluor channels less often than phase, so each
// channel's MP4 has its own frame count + t_sec timeline (phase_ranges[phase]
// .channels[channel]). Per-panel ◀/▶ scrub each channel independently; the
// master controls keep all channels aligned by real t_sec.
function _fmtHMS(s) {
  if (s == null || !isFinite(s)) return '--:--:--';
  const sign = s < 0 ? '-' : ''; s = Math.abs(s);
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = Math.floor(s%60);
  return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}
function _panelTsecs(p) {
  const r = (BATCH_METAS[currentBatchIdx]?.phase_ranges || {})[p?.dataset.phase];
  if (!r) return null;
  const ch = r.channels && r.channels[p.dataset.channel];
  return (ch && ch.length) ? ch : (r.t_secs && r.t_secs.length ? r.t_secs : null);
}
function videoTsecs(v) { const p = v.closest('.panel'); return p ? _panelTsecs(p) : null; }
function videoFrameCount(v) {
  const ts = videoTsecs(v); if (ts) return ts.length;
  return Math.max(1, Math.round((v.duration || 1) * fpsForVideo(v)));
}
function videoCurFrame(v) {
  return targetFrame.has(v) ? targetFrame.get(v)
                            : Math.round((v.currentTime || 0) * fpsForVideo(v));
}
function videoTsecAt(v, f) {
  const ts = videoTsecs(v);
  if (ts && ts.length) return ts[Math.max(0, Math.min(ts.length-1, f))];
  return f / fpsForVideo(v);
}
function videoCurTsec(v) { return videoTsecAt(v, videoCurFrame(v)); }
function seekVideoFrame(v, f) {
  const maxF = Math.max(0, videoFrameCount(v) - 1);
  f = Math.max(0, Math.min(maxF, f));
  targetFrame.set(v, f);
  v.currentTime = f / fpsForVideo(v);
}
function seekVideoToTsec(v, tsec) {
  const ts = videoTsecs(v);
  if (!ts || !ts.length) { seekVideoFrame(v, Math.round(tsec * fpsForVideo(v))); return; }
  let best = 0, bd = Infinity;
  for (let i = 0; i < ts.length; i++) { const d = Math.abs(ts[i] - tsec); if (d < bd) { bd = d; best = i; } }
  seekVideoFrame(v, best);
}
function refVideo() {            // densest channel in the current section
  let best = null, bn = -1;
  currentVideos().forEach(v => { const n = videoFrameCount(v); if (n > bn) { bn = n; best = v; } });
  return best;
}
function panelStep(p, n) {       // step ONLY this channel
  const v = p.querySelector('video');
  seekVideoFrame(v, videoCurFrame(v) + n);
  updatePanelLabel(p);
  setTimeout(() => redrawPanel(p), 20);
}
// Currently-visible media element of a panel (the MIP still if shown, else the video).
function panelMedia(p) {
  if (p.classList.contains('show-mip')) { const im = p.querySelector('img.mip-img'); if (im) return im; }
  return p.querySelector('video');
}
// Pseudocolor: SVG feColorMatrix that maps the (green-only) intensity of the
// pipeline-rendered fluor video to the channel's conventional wavelength color.
let _svgDefs = null; const _tintIds = {};
function tintFilterId(hex) {
  if (_tintIds[hex]) return _tintIds[hex];
  const NS = 'http://www.w3.org/2000/svg';
  if (!_svgDefs) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('style', 'position:absolute;width:0;height:0');
    _svgDefs = document.createElementNS(NS, 'defs');
    svg.appendChild(_svgDefs); document.body.appendChild(svg);
  }
  const id = 'tint' + Object.keys(_tintIds).length;
  const r = parseInt(hex.slice(1,3),16)/255, g = parseInt(hex.slice(3,5),16)/255, b = parseInt(hex.slice(5,7),16)/255;
  const f = document.createElementNS(NS, 'filter');
  f.setAttribute('id', id); f.setAttribute('color-interpolation-filters', 'sRGB');
  const m = document.createElementNS(NS, 'feColorMatrix');
  m.setAttribute('type', 'matrix');
  // intensity lives in the green channel → output = intensity·(r,g,b)
  m.setAttribute('values', `0 ${r} 0 0 0  0 ${g} 0 0 0  0 ${b} 0 0 0  0 0 0 1 0`);
  f.appendChild(m); _svgDefs.appendChild(f);
  _tintIds[hex] = id; return id;
}
// Apply this panel's brightness/contrast (+ wavelength tint) to its video and MIP.
function applyBC(p) {
  const b = (p._bc && p._bc.b != null) ? p._bc.b : 1;
  const c = (p._bc && p._bc.c != null) ? p._bc.c : 1;
  let f = `brightness(${b}) contrast(${c})`;
  if (p.dataset.tint) f += ` url(#${tintFilterId(p.dataset.tint)})`;
  const v = p.querySelector('video'); if (v) v.style.filter = f;
  const im = p.querySelector('img.mip-img'); if (im) im.style.filter = f;
  renderMerges();
}
function setPanelMip(p, on) {
  if (!p.dataset.hasMip) return;
  const im = p.querySelector('img.mip-img');
  if (im && !im.src && im.dataset.src) im.src = im.dataset.src;   // lazy-load
  p.classList.toggle('show-mip', !!on);
  renderMergePanelsFor(p);
  setTimeout(() => { redrawPanel(p); renderMerges(); }, 10);
}
function ensurePanelControls() { // inject [MIP] ◀ f/t ▶ B C bar once per panel
  currentPanels().forEach(p => {
    if (p.dataset.merge) return;
    const wrap = p.closest('.panel-wrap');
    if (!wrap || wrap.querySelector('.pc-bar')) return;
    const bar = document.createElement('div'); bar.className = 'pc-bar';
    // MIP/Z toggle for z-stack channels (default to MIP for clarity)
    if (p.dataset.hasMip) {
      const proj = document.createElement('button'); proj.type='button'; proj.className='pc-proj on'; proj.textContent='MIP';
      proj.title = 'Toggle max-projection ⇄ z-stack';
      proj.addEventListener('click', e => { e.stopPropagation();
        const on = !p.classList.contains('show-mip'); setPanelMip(p, on);
        proj.classList.toggle('on', on); proj.textContent = on ? 'MIP' : 'z'; });
      bar.appendChild(proj); p._pcProj = proj;
      p.dataset.bound2 || (p.dataset.bound2 = '1', setPanelMip(p, true));   // default MIP
    }
    const bk = document.createElement('button'); bk.type='button'; bk.className='pc-btn'; bk.textContent='◀';
    const lbl = document.createElement('span'); lbl.className='pc-lbl';
    const fw = document.createElement('button'); fw.type='button'; fw.className='pc-btn'; fw.textContent='▶';
    bk.addEventListener('click', e => { e.stopPropagation(); panelStep(p, -1); });
    fw.addEventListener('click', e => { e.stopPropagation(); panelStep(p,  1); });
    // Per-panel scrubber (slider version of the frame buttons; seeks THIS channel)
    const scr = document.createElement('input'); scr.type='range'; scr.className='pc-scrub';
    scr.min='0'; scr.step='1'; scr.value='0';
    scr.addEventListener('input', e => {
      e.stopPropagation();
      if (p.classList.contains('show-mip')) {   // scrubbing implies viewing z-slices
        setPanelMip(p, false);
        if (p._pcProj) { p._pcProj.classList.remove('on'); p._pcProj.textContent='z'; }
      }
      const v = p.querySelector('video');
      seekVideoFrame(v, parseInt(e.target.value));
      updatePanelLabel(p);
      setTimeout(() => { redrawPanel(p); renderMergePanelsFor(p); }, 15);
    });
    p._pcScrub = scr;
    bar.append(bk, lbl, fw, scr);
    // Brightness / contrast sliders (apply to video + MIP image)
    p._bc = { b: 1, c: 1 };
    const mk = (key, title) => {
      const box = document.createElement('span'); box.className='bc';
      const t = document.createElement('span'); t.textContent = title;
      const r = document.createElement('input'); r.type='range'; r.min='0.2'; r.max='3'; r.step='0.05'; r.value='1';
      r.title = title==='B' ? 'brightness' : 'contrast';
      r.addEventListener('input', e => { e.stopPropagation(); p._bc[key] = parseFloat(e.target.value); applyBC(p); });
      box.append(t, r); return box;
    };
    bar.append(mk('b','B'), mk('c','C'));
    wrap.appendChild(bar); p._pcLabel = lbl;
    applyBC(p);   // apply wavelength tint (+ default B/C) immediately
  });
  updatePanelLabels();
}
function renderMergePanelsFor(p) {   // re-render merge panel(s) of p's phase
  const sec = sections[currentBatchIdx]; if (!sec) return;
  sec.querySelectorAll(`.panel[data-merge][data-phase="${p.dataset.phase}"]`).forEach(renderMergePanel);
}
function updatePanelLabel(p) {
  if (!p._pcLabel) return;
  const v = p.querySelector('video');
  if (!v || !v.duration) { p._pcLabel.textContent = 'f –/–'; return; }
  const f = videoCurFrame(v), n = videoFrameCount(v);
  p._pcLabel.textContent = `f${f+1}/${n} · t=${_fmtHMS(videoCurTsec(v))}`;
  if (p._pcScrub) { p._pcScrub.max = Math.max(0, n - 1); p._pcScrub.value = f; }
}
function updatePanelLabels() { currentPanels().forEach(updatePanelLabel); }

// ── Live channel-merge rendering ──────────────────────────────────────────
// For each "Merge" panel, composite the enabled channels of its phase. Each
// channel frame is grayscaled (canvas filter), tinted with its display color,
// and added (globalCompositeOperation 'lighter'). Channels are already
// timepoint-aligned by the master t_sec sync, so the merge is per-timepoint.
const _mgOff = document.createElement('canvas');   // shared offscreen
const MERGE_RES = { w: 624, h: 528 };              // half PANEL_DIMS — fast, crisp enough
function renderMergePanel(panel) {
  const canvas = panel.querySelector('canvas');
  if (!canvas) return;
  if (canvas.width !== MERGE_RES.w) { canvas.width = MERGE_RES.w; canvas.height = MERGE_RES.h; }
  const ctx = canvas.getContext('2d');
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  const wrap = panel.closest('.panel-wrap');
  const phase = panel.dataset.phase;
  const sec = sections[currentBatchIdx];
  if (!wrap || !sec) return;
  const want = {};
  wrap.querySelectorAll('[data-mg-ch]').forEach(cb => { if (cb.checked) want[cb.dataset.mgCh] = cb.dataset.mgColor || '#33ff66'; });
  _mgOff.width = canvas.width; _mgOff.height = canvas.height;
  const octx = _mgOff.getContext('2d');
  sec.querySelectorAll(`.panel[data-phase="${phase}"][data-channel]`).forEach(p => {
    const ch = p.dataset.channel;
    if (!(ch in want)) return;
    const v = panelMedia(p);                       // MIP image or video frame
    const ready = v && ((v.tagName === 'IMG' && v.complete && v.naturalWidth) || (v.tagName === 'VIDEO' && v.videoWidth));
    if (!ready) return;
    const b = (p._bc && p._bc.b != null) ? p._bc.b : 1;
    const c = (p._bc && p._bc.c != null) ? p._bc.c : 1;
    octx.globalCompositeOperation = 'source-over';
    octx.filter = `brightness(${b}) contrast(${c}) grayscale(1)`;   // honor per-channel B/C
    octx.clearRect(0, 0, _mgOff.width, _mgOff.height);
    try { octx.drawImage(v, 0, 0, _mgOff.width, _mgOff.height); } catch (e) { return; }
    octx.filter = 'none';
    octx.globalCompositeOperation = 'multiply';
    octx.fillStyle = want[ch];
    octx.fillRect(0, 0, _mgOff.width, _mgOff.height);
    ctx.globalCompositeOperation = 'lighter';
    ctx.drawImage(_mgOff, 0, 0);
  });
  ctx.globalCompositeOperation = 'source-over';
}
function renderMerges() {
  currentPanels().forEach(p => { if (p.dataset.merge) renderMergePanel(p); });
}
// Toggle checkboxes re-render their merge live.
document.addEventListener('change', e => {
  if (e.target && e.target.matches('[data-mg-ch]')) {
    const panel = e.target.closest('.panel-wrap')?.querySelector('.merge-panel');
    if (panel) renderMergePanel(panel);
  }
});

// ── Multi-batch navigation ──
const titleEl = document.getElementById('batch-title');
function showBatch(i) {
  if (i < 0 || i >= sections.length) return;
  currentBatchIdx = i;
  sections.forEach((s, j) => { s.style.display = j === i ? '' : 'none'; });
  titleEl.textContent = `${i+1}/${sections.length} · ${currentBatch()}`;
  // Pull this batch's .batch-meta up into the top strip so it doesn't
  // steal a vertical row inside the section.
  const host = document.getElementById('batch-meta-host');
  if (host) {
    host.innerHTML = '';
    const meta = sections[i].querySelector('.batch-meta');
    if (meta) host.appendChild(meta.cloneNode(true));
  }
  // Lazy-load videos: this batch + adjacent only; clear src on far ones.
  sections.forEach((s, j) => {
    const vids = s.querySelectorAll('video');
    if (j === i || Math.abs(j - i) === 1) {
      vids.forEach(v => {
        if (!v.src && v.dataset.src) { v.src = v.dataset.src; v.preload = 'auto'; }
      });
    } else {
      vids.forEach(v => {
        if (v.src) { v.pause(); v.removeAttribute('src'); v.load(); }
      });
    }
  });
  document.querySelectorAll('video').forEach(v => {
    if (v.closest('.batch-section') !== sections[i]) v.pause();
  });
  playPause.textContent = '▶';
  setupPanelCanvases();
  bindVideoMetadata();
  ensurePanelControls();
  rebuildJumpBar();
  setTimeout(() => { updateScrubLabel(0); redrawAllPanels(); updateCounts(); renderList(); updatePanelLabels(); syncBatchFlagInputs(); }, 100);
}
function goPrev() { if (currentBatchIdx > 0) showBatch(currentBatchIdx - 1); }
function goNext() { if (currentBatchIdx < sections.length - 1) showBatch(currentBatchIdx + 1); }
document.getElementById('prev-batch').addEventListener('click', goPrev);
document.getElementById('next-batch').addEventListener('click', goNext);

// Map a specific panel's video time → absolute experiment t_sec (using
// frames.json t_secs for that phase). Call with the SAME video the user drew
// on, so out-of-sync panels don't contaminate the saved timestamp.
function videoToT(v, phase) {
  const ranges = BATCH_METAS[currentBatchIdx]?.phase_ranges || {};
  if (!v || !ranges[phase] || !ranges[phase].t_secs?.length) return null;
  const ts = ranges[phase].t_secs;
  const idx = Math.round((v.currentTime / (v.duration||1)) * (ts.length - 1));
  return ts[Math.max(0, Math.min(ts.length-1, idx))];
}
function fmtHMS(s) {
  if (s == null || !isFinite(s)) return '';
  const sign = s<0?'-':''; s = Math.abs(s);
  const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60);
  return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
}
// Pick the named event (NEBD, Metaphase, Anaphase, Cytokinesis, "First
// ablation" at t=0) closest to this t_sec. Returns e.g. "Metaphase (+12s)".
function findNearestEvent(t_sec) {
  if (t_sec == null) return '';
  const events = (BATCH_METAS[currentBatchIdx]?.key_times || []).slice();
  events.push({ label: 'First ablation', t_sec: 0 });
  let best = null, bestD = Infinity;
  events.forEach(k => {
    const d = Math.abs(t_sec - k.t_sec);
    if (d < bestD) { bestD = d; best = k; }
  });
  if (!best) return '';
  const off = Math.round(t_sec - best.t_sec);
  const sign = off >= 0 ? '+' : '';
  return `${best.label} (${sign}${off}s)`;
}

// Seek every "current-phase" video by +secs from whichever video is furthest
// along. Used by the +10 min button.
function seekByOffset(secs) {
  const ranges = BATCH_METAS[currentBatchIdx]?.phase_ranges || {};
  // Pick the video that is furthest along; use its t_sec as the base.
  let best = null, bestT = -Infinity, bestPhase = null;
  currentVideos().forEach(v => {
    const phase = v.closest('.panel')?.dataset.phase;
    if (!ranges[phase] || !ranges[phase].t_secs?.length) return;
    if ((v.currentTime||0) >= bestT) { bestT = v.currentTime||0; best = v; bestPhase = phase; }
  });
  if (!best) { setStatus('No phase data — cannot offset.', ''); return; }
  const r = ranges[bestPhase];
  const ts = r.t_secs;
  const idx0 = Math.round((best.currentTime / (best.duration||1)) * (ts.length - 1));
  const baseT = ts[Math.max(0, Math.min(ts.length-1, idx0))];
  jumpToAbsT(baseT + secs);
}
function jumpToAbsT(target_t) {
  const meta = BATCH_METAS[currentBatchIdx];
  const ranges = meta?.phase_ranges || {};
  // Pick the phase whose ACTUAL frames have a t_sec closest to target_t.
  // Robust to merged/interleaved timelines where abl/mon ranges overlap or have gaps
  // (range-contains tests pick the wrong video in those cases).
  let targetPhase = null, bestD = Infinity;
  for (const [phase, r] of Object.entries(ranges)) {
    const ts = r.t_secs;
    if (!ts || !ts.length) continue;
    let nd = Infinity;
    for (let i = 0; i < ts.length; i++) { const dd = Math.abs(ts[i] - target_t); if (dd < nd) nd = dd; }
    if (nd < bestD) { bestD = nd; targetPhase = phase; }
  }
  if (!targetPhase) return;
  const r = ranges[targetPhase];
  const ts = r.t_secs;
  let frac = 0;
  if (ts && ts.length > 0) {
    let lo = 0, hi = ts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (ts[mid] < target_t) lo = mid + 1; else hi = mid;
    }
    let bestIdx = lo;
    if (lo > 0 && Math.abs(ts[lo-1] - target_t) < Math.abs(ts[lo] - target_t)) bestIdx = lo - 1;
    frac = bestIdx / Math.max(1, ts.length - 1);
  }
  currentVideos().filter(v => v.closest('.panel')?.dataset.phase === targetPhase)
    .forEach(v => {
      v.currentTime = Math.max(0, Math.min((v.duration||0) - 1e-6, frac * (v.duration||0)));
      syncTargetFromTime(v);
    });
  setTimeout(() => updateScrubLabel(currentVideos()[0]?.currentTime||0), 30);
  setTimeout(redrawAllPanels, 60);
}

function rebuildJumpBar() {
  const jumpBar = document.getElementById('jump-bar');
  jumpBar.innerHTML = '';
  const meta = BATCH_METAS[currentBatchIdx];
  const kts = meta?.key_times || [];
  // Always include +10 min button, even when there are no master-CSV key times
  jumpBar.appendChild(Object.assign(document.createElement('span'),
    { textContent: 'Jump to:', style:'color:#888;font-size:12px;margin-right:4px' }));
  const firstAbl = document.createElement('button');
  firstAbl.className = 'jump-btn'; firstAbl.textContent = 'First ablation';
  firstAbl.addEventListener('click', () => jumpToAbsT(0));
  jumpBar.appendChild(firstAbl);
  const plus10 = document.createElement('button');
  plus10.className = 'jump-btn'; plus10.textContent = '+10 min';
  plus10.addEventListener('click', () => seekByOffset(600));
  jumpBar.appendChild(plus10);
  if (kts.length === 0) {
    jumpBar.appendChild(Object.assign(document.createElement('span'),
      { textContent: '— no key times in master CSV',
        style:'color:#888;font-size:11px;margin-left:6px' }));
    return;
  }
  const fmt = s => {
    const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60);
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
  };
  kts.forEach(k => {
    const b = document.createElement('button');
    b.className = 'jump-btn';
    b.textContent = `${k.label} (${fmt(k.t_sec)})`;
    b.addEventListener('click', () => {
      // Map the absolute experiment time (k.t_sec) → which phase contains
      // it → seek THAT phase's videos to the correct video-time using the
      // phase's actual t_sec range from frames.json.
      const ranges = meta.phase_ranges || {};
      // Pick the phase whose [start,end] brackets k.t_sec
      let targetPhase = null;
      for (const [phase, r] of Object.entries(ranges)) {
        if (k.t_sec >= r.start && k.t_sec <= r.end) { targetPhase = phase; break; }
      }
      // If not in any phase, pick the closest (probably mon end if past it)
      if (!targetPhase) {
        let bestD = Infinity;
        for (const [phase, r] of Object.entries(ranges)) {
          const d = Math.min(Math.abs(k.t_sec - r.start), Math.abs(k.t_sec - r.end));
          if (d < bestD) { bestD = d; targetPhase = phase; }
        }
      }
      if (!targetPhase) {
        setStatus(`Could not locate phase for ${k.label}`, '');
        return;
      }
      const r = ranges[targetPhase];
      const vs = currentVideos().filter(v =>
        v.closest('.panel')?.dataset.phase === targetPhase);
      // Use per-frame t_sec to map to the EXACT closest frame index,
      // then convert that index → video time. Linear span-interpolation
      // is wrong when frames are unevenly spaced in real time.
      let frac;
      const ts = r.t_secs;
      if (ts && ts.length > 0) {
        // Binary search for closest t_sec
        let lo = 0, hi = ts.length - 1;
        while (lo < hi) {
          const mid = (lo + hi) >> 1;
          if (ts[mid] < k.t_sec) lo = mid + 1; else hi = mid;
        }
        // lo is the smallest index with ts[lo] >= k.t_sec
        let bestIdx = lo;
        if (lo > 0 && Math.abs(ts[lo-1] - k.t_sec) < Math.abs(ts[lo] - k.t_sec)) {
          bestIdx = lo - 1;
        }
        frac = bestIdx / Math.max(1, ts.length - 1);
      } else {
        const span = r.end - r.start;
        frac = span > 0 ? Math.max(0, Math.min(1, (k.t_sec - r.start) / span)) : 0;
      }
      vs.forEach(v => {
        const tt = Math.max(0, Math.min((v.duration||0) - 1e-6, frac * (v.duration||0)));
        v.currentTime = tt;
        syncTargetFromTime(v);
      });
      setTimeout(() => updateScrubLabel(currentVideos()[0]?.currentTime||0), 30);
      setTimeout(redrawAllPanels, 60);
      setStatus(`Jumped to ${k.label} (${targetPhase} frame ≈ ${Math.round((frac*((vs[0]?.duration||1)*9))+1)}/${Math.round((vs[0]?.duration||1)*9)})`, 'success');
    });
    jumpBar.appendChild(b);
  });
}

// ── Save / load CSV across all batches ──
function csvEscape(s) {
  if (s==null) return ''; s = String(s);
  return /[,"\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
}
function buildCsv() {
  const header = "id,batch,video_file,phase,channel,frame,t_sec,t_hms,nearest_event,type,label,x,y,points,length_um,area_um2,perimeter_um,circularity,aspect_ratio,roundness,solidity,pixel_size_um,notes";
  const rows = [header];
  BATCH_METAS.forEach(m => {
    const arr = annByBatch.get(m.name) || [];
    arr.forEach(a => {
      const points = a.points
        ? '[' + a.points.map(p => `[${p[0].toFixed(2)},${p[1].toFixed(2)}]`).join(',') + ']'
        : '';
      rows.push([
        a.id, csvEscape(m.name),
        csvEscape(a.panel ? `${a.panel}.mp4` : ''),
        csvEscape(a.phase || ''), csvEscape(a.channel || ''),
        a.frame,
        a.t_sec!=null?a.t_sec.toFixed(2):'',
        csvEscape(a.t_hms || ''), csvEscape(a.nearest_event || ''),
        a.type, csvEscape(a.label),
        a.x!=null?a.x.toFixed(2):'', a.y!=null?a.y.toFixed(2):'',
        csvEscape(points), '','','','','','','', '0.062', csvEscape(a.notes||'')
      ].join(','));
    });
  });
  return rows.join('\n');
}
document.getElementById('save-csv').addEventListener('click', () => {
  const csv = buildCsv();
  const blob = new Blob([csv], { type:'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `annotations_${new Date().toISOString().slice(0,16).replace(/[:T]/g,'-')}.csv`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
});
document.getElementById('clear-batch').addEventListener('click', () => {
  if (!confirm(`Delete all marks for ${currentBatch()}?`)) return;
  annByBatch.set(currentBatch(), []);
  nextIdByBatch.set(currentBatch(), 1);
  updateCounts(); renderList(); redrawAllPanels(); autosave();
});

// ── Crop-box options init ──
updateCropSizeReadout();
document.getElementById('crop-clear-size')?.addEventListener('click', () => {
  cropSize = null;
  try { localStorage.removeItem(CROP_SIZE_KEY); } catch(e){}
  updateCropSizeReadout();
  setStatus('Cleared stored crop size — drag to define a new one.', '');
});

// ── Autosave: localStorage (instant) + POST to server (debounced) ──
// Versioned per-origin key: bumping the version makes the page ignore any stale
// browser-cached annotation state and load fresh from the server store (which has
// the corrected outline frames). Origin (port) already separates slide sets.
const AS_KEY = 'annotate:multi:v20260625f:' + location.port;
const _saveTimers = new Map();   // batch_name → setTimeout handle
function autosave() {
  // 1. Local browser autosave — instant, survives reload of this device.
  const obj = {};
  BATCH_METAS.forEach(m => obj[m.name] = annByBatch.get(m.name));
  try { localStorage.setItem(AS_KEY, JSON.stringify(obj)); } catch(e) {}

  // 2. Server autosave — debounced, writes the master CSV on disk.
  const batch = currentBatch();
  if (!batch) return;
  if (_saveTimers.has(batch)) clearTimeout(_saveTimers.get(batch));
  _saveTimers.set(batch, setTimeout(() => sendToServer(batch), 600));
}
function sendToServer(batch) {
  const arr = annByBatch.get(batch) || [];
  const rows = arr.map(a => ({
    id: a.id,
    video_file: a.panel ? `${a.panel}.mp4` : '',
    phase: a.phase || '',
    channel: a.channel || '',
    frame: a.frame,
    t_sec: (a.t_sec != null) ? a.t_sec.toFixed(2) : '',
    t_hms: a.t_hms || '',
    nearest_event: a.nearest_event || '',
    type: a.type, label: a.label || '',
    x: (a.x != null) ? a.x.toFixed(2) : '',
    y: (a.y != null) ? a.y.toFixed(2) : '',
    points: a.points ? '[' + a.points.map(p =>
      `[${p[0].toFixed(2)},${p[1].toFixed(2)}]`).join(',') + ']' : '',
    w: (a.w != null) ? a.w.toFixed(2) : '',
    h: (a.h != null) ? a.h.toFixed(2) : '',
    crop_name: a.crop_name || '',
    apply_both: (a.type === 'crop_box') ? (a.apply_both ? 1 : 0) : '',
    all_frames: (a.type === 'crop_box') ? (a.all_frames ? 1 : 0) : '',
    length_um: '', area_um2: '', perimeter_um: '',
    circularity: '', aspect_ratio: '', roundness: '', solidity: '',
    pixel_size_um: '0.062',
    notes: a.notes || ''
  }));
  const indicator = document.getElementById('save-indicator');
  if (indicator) indicator.textContent = '💾 saving…';
  fetch('/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batch, rows })
  }).then(r => r.json()).then(j => {
    if (indicator) indicator.textContent = j.ok
      ? `✓ saved ${rows.length} → master CSV`
      : `⚠ autosave failed: ${j.error || 'unknown'}`;
  }).catch(e => {
    if (indicator) indicator.textContent = `⚠ autosave error: ${e}`;
  });
}
(function loadAutosave() {
  try {
    const s = localStorage.getItem(AS_KEY); if (!s) return;
    const obj = JSON.parse(s);
    Object.entries(obj).forEach(([bn, arr]) => {
      if (annByBatch.has(bn) && Array.isArray(arr)) {
        annByBatch.set(bn, arr);
        const maxId = arr.reduce((m,a)=>Math.max(m, a.id||0), 0);
        nextIdByBatch.set(bn, maxId + 1);
      }
    });
  } catch(e) {}
})();

// Belt-and-suspenders: also fetch from the master CSV on the server, so the
// page restores annotations even if localStorage is empty (different browser,
// private window, manual clear, switched device). Rows in the server CSV that
// aren't already in memory get appended.
function csvRowToAnn(r) {
  const num = v => (v === '' || v == null) ? null : parseFloat(v);
  const pts = (() => {
    if (!r.points) return null;
    try { return JSON.parse(r.points); } catch(e) { return null; }
  })();
  return {
    id: parseInt(r.id) || 0,
    type: r.type, label: r.label || '',
    panel: r.video_file ? r.video_file.replace(/\.mp4$/,'') : '',
    phase: r.phase || '', channel: r.channel || '',
    frame: parseInt(r.frame) || 0,
    t_sec: num(r.t_sec), t_hms: r.t_hms || '',
    nearest_event: r.nearest_event || '',
    x: num(r.x), y: num(r.y),
    points: pts,
    w: num(r.w), h: num(r.h),
    crop_name: r.crop_name || '',
    apply_both: (r.apply_both === '1' || r.apply_both === 1 || r.apply_both === 'true') ? 1 : 0,
    all_frames: (r.all_frames === '1' || r.all_frames === 1 || r.all_frames === 'true') ? 1 : 0,
    notes: r.notes || ''
  };
}
fetch('/load').then(r => r.ok ? r.json() : null).then(j => {
  if (!j || !j.ok || !Array.isArray(j.rows)) return;
  // Group rows by batch, keep only batches we recognise.
  const grouped = new Map();
  for (const row of j.rows) {
    const bn = row.batch;
    if (!annByBatch.has(bn)) continue;
    if (!grouped.has(bn)) grouped.set(bn, []);
    grouped.get(bn).push(csvRowToAnn(row));
  }
  // For each batch, merge: server wins for IDs already present, server-only
  // IDs get appended. nextId always advances past the highest seen id.
  let totalRestored = 0;
  grouped.forEach((serverArr, bn) => {
    const localArr = annByBatch.get(bn) || [];
    const localIds = new Set(localArr.map(a => a.id));
    const merged = localArr.slice();
    serverArr.forEach(s => { if (!localIds.has(s.id)) { merged.push(s); totalRestored++; } });
    annByBatch.set(bn, merged);
    const maxId = merged.reduce((m,a)=>Math.max(m, a.id||0), 0);
    nextIdByBatch.set(bn, Math.max(nextIdByBatch.get(bn) || 1, maxId + 1));
  });
  if (totalRestored > 0) {
    // Refresh whatever's showing now
    updateCounts(); renderList(); redrawAllPanels(); syncBatchFlagInputs();
    setStatus(`Restored ${totalRestored} mark(s) from master CSV`, 'success');
  }
}).catch(e => console.warn('[load] server fetch failed:', e));

// Batch flags (example flag + notes) — stored as batch_meta rows per batch
function syncBatchFlagInputs() {
  const arr = currentAnns();
  const ex = arr.find(a => a.type === 'batch_meta' && a.label === 'use_as_example');
  const nt = arr.find(a => a.type === 'batch_meta' && a.label === 'notes');
  const rc = arr.find(a => a.type === 'batch_meta' && a.label === 'reclass_prometaphase_to_prophase');
  const tc = arr.find(a => a.type === 'batch_meta' && a.label === 'timestrip_candidate');
  document.getElementById('flag-example').checked = (ex && ex.notes === 'yes');
  document.getElementById('flag-reclass-prophase').checked = (rc && rc.notes === 'yes');
  document.getElementById('flag-timestrip-candidate').checked = (tc && tc.notes === 'yes');
  document.getElementById('batch-notes').value = nt ? nt.notes || '' : '';
}
function upsertBatchMeta(label, value) {
  const arr = currentAnns();
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i].type === 'batch_meta' && arr[i].label === label) { arr.splice(i,1); break; }
  }
  arr.push({ id: nextId(), type:'batch_meta', label, frame:0, x:null, y:null, panel:'', notes:value });
  updateCounts(); renderList(); autosave();
}
document.getElementById('flag-example').addEventListener('change', e => {
  upsertBatchMeta('use_as_example', e.target.checked ? 'yes' : 'no');
});
document.getElementById('flag-reclass-prophase').addEventListener('change', e => {
  upsertBatchMeta('reclass_prometaphase_to_prophase', e.target.checked ? 'yes' : 'no');
});
document.getElementById('flag-timestrip-candidate').addEventListener('change', e => {
  upsertBatchMeta('timestrip_candidate', e.target.checked ? 'yes' : 'no');
});
document.getElementById('batch-notes').addEventListener('input', e => {
  upsertBatchMeta('notes', e.target.value);
});
document.getElementById('flag-timestrip').addEventListener('click', () => {
  const v = currentVideos()[0]; if (!v) return;
  const f = Math.round(v.currentTime * fpsForVideo(v)) + 1;
  currentAnns().push({ id: nextId(), type:'timestrip_frame', label:'', frame:f,
                       x:null, y:null, panel:'', notes:'' });
  updateCounts(); renderList(); autosave();
  setStatus(`Marked frame ${f} as timestrip candidate`, 'success');
});

// Init: show first batch
showBatch(0);
// If the page is restored from the browser's back-forward cache (reopen from
// history), the DOM keeps the last-viewed section — force back to the first.
window.addEventListener('pageshow', e => { if (e.persisted) showBatch(0); });
</script>
</body>
</html>
"""


def load_phase_acquisition_info(batch_name, master_csv=MASTER_CSV):
    """Return list of (label, value_str) describing per-phase interval + z-stack
    count per channel, read from frames.json's source_files block."""
    row, _ = _read_master_row(batch_name, master_csv)
    if row is None: return []
    dp = (row.get("Drive Path", "") or "").strip()
    if dp.startswith(("E:\\", "F:\\", "G:\\")) or "\\" in dp:
        import re as _re
        tail = _re.sub(r"^[A-Za-z]:\\", "", dp).replace("\\", "/")
        tail = _re.sub(r"^Maddie/", "", tail)
        for vol in os.listdir("/Volumes"):
            cand = os.path.join("/Volumes", vol, tail)
            if os.path.isdir(cand): dp = cand; break
    fj = os.path.join(dp, f"{batch_name}_frames.json")
    if not os.path.isfile(fj): return []
    try:
        with open(fj) as f: meta = json.load(f)
    except Exception:
        return []
    out = []
    pretty = {"pre": "Pre", "ablation": "Abl", "monitoring": "Mon"}
    for sf in meta.get("source_files", []):
        role = sf.get("role", "")
        label = pretty.get(role, role.title()) if role else "Phase"
        try: secs = float(sf.get("interval_ms", 0)) / 1000.0
        except (TypeError, ValueError): secs = 0
        nz = sf.get("n_slices") or 1
        chs = sf.get("channels") or []
        # Channel-specific z: assume the source TIF's n_slices applies to
        # whichever channels are present. Display as "488 z=N · BF z=N".
        z_parts = []
        for ch in chs:
            short = ("488" if "488" in ch else
                     "BF"  if "Brightfield" in ch or "Phase" in ch else
                     ch)
            z_parts.append(f"{short} z={nz}")
        interval_str = f"{secs:g}s" if secs else "?s"
        val = interval_str + ((" · " + " · ".join(z_parts)) if z_parts else "")
        out.append((label, val))
    return out


def _ffprobe_nframes(mp4):
    try:
        import subprocess
        out = subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v",
             "-count_frames","-show_entries","stream=nb_read_frames",
             "-of","csv=p=0", mp4], stderr=subprocess.DEVNULL).strip()
        return int(out or 0)
    except Exception:
        return 0


def _probe_fps(mp4):
    """Return the encoded frame rate of an MP4 as a float (e.g. 13.0), or 0 on
    failure. The re-encoded clips are constant-rate, so avg_frame_rate is exact;
    this is what the frame-stepper needs so one click == exactly one frame."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["ffprobe","-v","error","-select_streams","v:0",
             "-show_entries","stream=avg_frame_rate",
             "-of","csv=p=0", mp4], stderr=subprocess.DEVNULL).strip().decode()
        if "/" in out:
            num, den = out.split("/")
            den = float(den)
            return float(num) / den if den else 0.0
        return float(out or 0)
    except Exception:
        return 0.0


def _lookup_processing_log(batch_name):
    """Search /Volumes/*/pipeline_output/<date>/<date>_processing_log.csv for
    this batch's row. Returns dict or {}."""
    import re as _re, csv as _csv
    m = _re.match(r"(\d{8})\s+", batch_name)
    if not m: return {}
    date = m.group(1)
    for vol in os.listdir("/Volumes"):
        for sub in ("pipeline_output", "pipeline_session_output"):
            p = os.path.join("/Volumes", vol, sub, date, f"{date}_processing_log.csv")
            if not os.path.isfile(p): continue
            try:
                with open(p) as f:
                    raw = list(_csv.reader(f))
                if len(raw) < 3: continue
                header = raw[1]   # row 0 = category labels, row 1 = field names
                for r in raw[2:]:
                    if r and r[0].strip() == batch_name:
                        return dict(zip(header, r))
            except Exception:
                continue
    return {}


def _synthesize_phase_ranges(batch_name, master_csv=MASTER_CSV):
    """Build approximate per-phase t_sec ranges when frames.json is missing.
    Prefers values from the date's processing_log.csv (Total Duration,
    Ablation Span) when available; otherwise falls back to MP4 frame counts
    + Time Interval + master CSV key times."""
    pkg = os.path.join("/Volumes/2 MB/ipad_packages", batch_name)
    if not os.path.isdir(pkg): return {}
    row, _ = _read_master_row(batch_name, master_csv)
    try: interval = float((row.get("Time Interval (s)", "") or "3").strip())
    except (ValueError, TypeError, AttributeError): interval = 3.0
    key_times = load_master_key_times(batch_name, master_csv)
    latest   = max((k["t_sec"] for k in key_times), default=600.0)

    plog = _lookup_processing_log(batch_name)
    def _f(v, default=None):
        try: return float(v)
        except (TypeError, ValueError): return default
    total_dur  = _f(plog.get("Total Duration (s)", ""))
    abl_span   = _f(plog.get("Ablation Span (s)", ""))
    # Some rows in processing_log have absolute Unix timestamps (~1.7e9)
    # accidentally stored in Total Duration. Anything > 24h is bogus.
    if total_dur and total_dur > 24*3600: total_dur = None
    if abl_span and abl_span > 600: abl_span = None

    ranges = {}
    n_abl = n_mon = 0
    abl_mp4 = mon_mp4 = None
    for phase in ("abl", "mon"):
        for ch in ("fluor", "phase"):
            c = os.path.join(pkg, f"{phase}_{ch}.mp4")
            if os.path.isfile(c):
                if phase == "abl": abl_mp4 = c
                else: mon_mp4 = c
                break
    if abl_mp4: n_abl = _ffprobe_nframes(abl_mp4)
    if mon_mp4: n_mon = _ffprobe_nframes(mon_mp4)

    # abl: span = Ablation Span if known, else n_abl × interval. Empirically
    # the older batches that DO have frames.json show the ablation MP4
    # contains mostly pre-laser frames (~60% before laser fire, ~40% after),
    # so we put t=0 at ~60% through the abl mp4. This is still an
    # approximation — without frames.json we can't pinpoint the laser fire
    # frame exactly.
    if n_abl > 0:
        span = abl_span if (abl_span and abl_span > 0) else n_abl * interval
        pre_frac = 0.60
        start_t = -span * pre_frac
        ts = [start_t + (i / max(1, n_abl - 1)) * span for i in range(n_abl)] if n_abl > 1 else [0.0]
        ranges["abl"] = {"start": ts[0], "end": ts[-1], "t_secs": ts}

    # mon: span [end_of_abl + buffer, Total Duration] if total_dur known
    if n_mon > 0:
        abl_end = (abl_span or n_abl * interval) / 2.0 if n_abl else 0
        start = abl_end + max(interval, 5.0)
        if total_dur and total_dur > start:
            end = total_dur
        else:
            # No processing log: pad past last key-time by 25% as a guess
            end = max(latest * 1.25, start + n_mon * interval * 3)
        ts = [start + (i / max(1, n_mon - 1)) * (end - start) for i in range(n_mon)] if n_mon > 1 else [start]
        ranges["mon"] = {"start": ts[0], "end": ts[-1], "t_secs": ts}
    return ranges


def _resolve_frames_json(batch_name, master_csv=MASTER_CSV):
    """Locate a batch's frames.json on disk. Returns (fj_path_or_None, dp).
    Shared by phase-range, channel and ablation-marker readers."""
    row, _ = _read_master_row(batch_name, master_csv)
    if row is None: return None, ""
    dp = (row.get("Drive Path", "") or "").strip()
    # PREFER pipeline_correct (reprocessed source of truth) over the master's
    # Drive Path, which may point at OLD renders whose frames.json is stale.
    import re as _re0
    _m = _re0.match(r"(\d{8})\s+", batch_name)
    if _m:
        _date = _m.group(1)
        for _vol in os.listdir("/Volumes"):
            _cand = os.path.join("/Volumes", _vol, "pipeline_correct", _date, batch_name)
            if os.path.isfile(os.path.join(_cand, f"{batch_name}_frames.json")):
                dp = _cand
                break
    if not os.path.isdir(dp) and (dp.startswith(("E:\\", "F:\\", "G:\\")) or "\\" in dp):
        import re as _re
        tail = _re.sub(r"^[A-Za-z]:\\", "", dp).replace("\\", "/")
        tail = _re.sub(r"^Maddie/", "", tail)
        for vol in os.listdir("/Volumes"):
            cand = os.path.join("/Volumes", vol, tail)
            if os.path.isdir(cand):
                dp = cand; break
    if not os.path.isdir(dp):
        import re as _re
        m = _re.match(r"(\d{8})\s+", batch_name)
        date = m.group(1) if m else None
        if date:
            for vol in os.listdir("/Volumes"):
                for sub in ("pipeline_output", "pipeline_session_output"):
                    cand = os.path.join("/Volumes", vol, sub, date, batch_name)
                    if os.path.isdir(cand): dp = cand; break
    fj_path = os.path.join(dp, f"{batch_name}_frames.json")
    return (fj_path if os.path.isfile(fj_path) else None), dp


def read_batch_channel_info(batch_name, master_csv=MASTER_CSV):
    """Return {'ch_names': [...], 'ablation_events': [{x,y,t_sec}...]} from a
    batch's frames.json (empty dict if unavailable)."""
    fj_path, _dp = _resolve_frames_json(batch_name, master_csv)
    if not fj_path: return {}
    try:
        with open(fj_path) as f: meta = json.load(f)
    except (OSError, ValueError): return {}
    return {"ch_names": meta.get("ch_names", []),
            "ablation_events": meta.get("ablation_events_local", [])}


def _read_phase_time_ranges(batch_name, master_csv=MASTER_CSV):
    """Locate the batch's frames.json on disk + compute per-phase t_sec ranges
    so the jump-to-frame buttons can map absolute experiment time → video time.

    Each ranges[phase] also carries a per-channel 'channels' map: {ch_short →
    [t_secs]} for the frames where THAT channel was captured. Multi-rate batches
    (488 captured less often than phase) have different frame counts per channel,
    so each channel's video must map through its own t_secs."""
    import csv as _csv
    fj_path, dp = _resolve_frames_json(batch_name, master_csv)
    # PREFER pipeline_correct (today's reprocessed source of truth) over the
    # master's Drive Path, which points at OLD pipeline_output renders whose
    # frames.json has a stale/different timeline. Reading the stale frames.json
    # makes jump-to land on the wrong frame (the per-frame t_secs are wrong).
    if not fj_path:
        # Pipeline didn't write frames.json (older runs). Synthesize approximate
        # phase_ranges from packaged-MP4 frame counts + master CSV's key times +
        # Time Interval so the JS jump-to buttons still work.
        return _synthesize_phase_ranges(batch_name, master_csv)
    with open(fj_path) as f:
        meta = json.load(f)
    # Pipeline MP4 split: Ablation.mp4 = ALL role=ablation frames,
    # Monitoring.mp4 = all role=monitoring frames. NEW single-MP4 batches
    # (<batch>_488.mp4 / <batch>_phase.mp4) collapse every frame into "mon".
    has_split = any(
        os.path.isfile(os.path.join(dp, f"{batch_name}_{ch}_{ph}.mp4"))
        for ch in ("Fluor","Phase") for ph in ("Ablation","Monitoring")
    )
    # Map each sanitized extra-channel id (e.g. 488_GFP) → its frames.json name
    # (e.g. "488 (GFP)") so we can test per-frame presence in extra_tif_idx.
    extra_san2name = {e.get("sanitized"): e.get("name")
                      for e in meta.get("extra_fluor_channels", []) if e.get("sanitized")}
    def _channel_present(fr, ch):
        if ch == "phase":  return fr.get("phase_tif_idx") is not None
        if ch == "fluor":  return fr.get("fluor_tif_idx") is not None
        nm = extra_san2name.get(ch)
        return nm is not None and (fr.get("extra_tif_idx") or {}).get(nm) is not None
    channel_ids = ["phase", "fluor"] + list(extra_san2name.keys())
    # Collect per-phase, per-channel t_sec lists (a channel's video contains only
    # the frames where THAT channel was captured → its own t_secs timeline).
    by_phase = {"abl": {c: [] for c in channel_ids},
                "mon": {c: [] for c in channel_ids}}
    for fr in meta.get("frames", []):
        try: t = float(fr.get("t_sec", 0))
        except (TypeError, ValueError): continue
        role = fr.get("role", "")
        if not has_split:
            phase = "mon" if role in ("ablation", "monitoring", "pre") else None
        elif role == "ablation":  phase = "abl"
        elif role == "monitoring": phase = "mon"
        else: phase = None
        if phase is None: continue
        for c in channel_ids:
            if _channel_present(fr, c):
                by_phase[phase][c].append(t)
    ranges = {}
    for phase, chmap in by_phase.items():
        chans = {c: sorted(ts) for c, ts in chmap.items() if ts}
        if not chans: continue
        # Legacy default timeline = phase channel's t_secs (else first present).
        default = chans.get("phase") or next(iter(chans.values()))
        ranges[phase] = {"start": default[0], "end": default[-1],
                         "t_secs": default, "channels": chans}
    return ranges


def build_multi_batch_index(specs, pkg_root, out_path, phases=("abl", "mon"), markers=None):
    """specs = list of {name, pkg_dir}. Generates a multi-batch HTML where
    each batch is a section that can be navigated with Prev/Next.

    phases: which movie phases to render (default both). Pass ("abl",) to build
    an ablation-only index — the abl movie then fills the screen for more
    accurate annotation. Batches with no clip in the selected phases are
    skipped entirely (e.g. monitoring-only batches in an abl-only index)."""
    sections = []
    metas    = []   # JS-readable metadata per batch
    for s in specs:
        bn  = s["name"]
        pkg = s["pkg_dir"]
        # Per-batch path relative to pkg_root, used for MP4 sources.
        rel = os.path.relpath(pkg, pkg_root)
        # Find which phases × channels the batch actually has on disk by scanning
        # the package for every <phase>_<channel>.mp4 (auto-detects 488/561/640/…
        # so Hec1 dual + IF 5-channel batches get a panel per channel).
        present = {}
        try: pkg_files = os.listdir(pkg)
        except OSError: pkg_files = []
        for phase in phases:
            pref = f"{phase}_"
            for fn in pkg_files:
                if fn.startswith(pref) and fn.endswith(".mp4"):
                    ch = fn[len(pref):-4]
                    present[(phase, ch)] = f"{rel}/{fn}"
        # Skip batches that have nothing to show in the selected phase(s).
        if not present:
            continue
        # Per-batch metadata (master CSV) + per-phase interval/z-stack info
        md = load_master_metadata(bn) + load_phase_acquisition_info(bn)
        key_times = load_master_key_times(bn)
        # Per-phase t_sec ranges (with per-channel timelines) → accurate
        # jump-to-frame mapping + master sync across multi-rate channels.
        phase_ranges = _read_phase_time_ranges(bn)
        chinfo = read_batch_channel_info(bn)
        ch_names = chinfo.get("ch_names", [])
        abl_events = chinfo.get("ablation_events", [])
        # Combined IF slide: a spec may carry a paired ablation batch (abl_batch).
        # Its movie is copied into this package as abl_*/amon_* mp4s; pull its
        # time ranges + ablation markers from its OWN frames.json (the IF z-stack
        # has none). 'abl' = the ablation movie's ablation phase, 'amon' = its
        # post-ablation monitoring. The two acquisitions are at different times,
        # so their panels scrub independently (no shared t_sec).
        abl_batch = s.get("abl_batch")
        abl_ch_names = []
        if abl_batch:
            ar = _read_phase_time_ranges(abl_batch)
            if ar.get("abl"):  phase_ranges["abl"]  = ar["abl"]
            if ar.get("mon"):  phase_ranges["amon"] = ar["mon"]
            ai = read_batch_channel_info(abl_batch)
            # prefer ch_names passed in the spec (ablation may be removed from master)
            abl_ch_names = s.get("abl_ch_names") or ai.get("ch_names", [])
            if ai.get("ablation_events"): abl_events = ai["ablation_events"]
        # Build grid
        rows = []
        for phase in phases:
            chans = sorted((c for (p, c) in present if p == phase), key=channel_sort_key)
            # Label/color the paired-ablation rows (abl/amon) with the ABLATION
            # batch's channel names (its fluor is 488/green), not the IF's (405/blue).
            chn = abl_ch_names if (phase in ("abl", "amon") and abl_ch_names) else ch_names
            cells = []
            for ch in chans:
                src = present[(phase, ch)]
                fps = _probe_fps(os.path.join(pkg, f"{phase}_{ch}.mp4"))
                fps_attr = f' data-fps="{fps:.6g}"' if fps else ""
                # Max-intensity-projection still (IF z-stacks): if a precomputed
                # MIP PNG exists, embed it; the panel defaults to MIP with a
                # toggle to scrub the z-stack video.
                mip_img = ""; mip_attr = ""
                if os.path.isfile(os.path.join(pkg, f"{phase}_{ch}_mip.png")):
                    mip_img = f'<img class="mip-img" data-src="{rel}/{phase}_{ch}_mip.png" alt="MIP">'
                    mip_attr = ' data-has-mip="1"'
                # Pseudocolor by wavelength (academic convention); phase/BF stays grayscale.
                tint_attr = "" if ch == "phase" else f' data-tint="{channel_color(ch, chn)}"'
                # Optional biological marker label keyed by WAVELENGTH (e.g.
                # "Mad1 (488)", "Hec1 (640)", "eYFP-Cdc20 (488)"). Wavelength comes
                # from the channel's real name so "fluor" resolves correctly whether
                # it's 488 or 640. BgSub channels get a "bg-sub" suffix.
                _wlfull = channel_label(ch, chn)
                _m = re.search(r'(\d{3})', _wlfull)
                wl = _m.group(1) if _m else _wlfull           # "488" / "640" / "Phase / BF"
                mk = (markers or {}).get(phase, {}).get(wl)
                if mk and "(" in mk:        # full label provided, e.g. "Mad2 (555)"
                    lab = mk.replace(" (", " bg-sub (") if "BgSub" in ch else mk
                elif mk:                    # marker name only → append metadata wavelength
                    if "BgSub" in ch: mk = mk + " bg-sub"
                    lab = f"{mk} ({wl})"
                else:
                    lab = wl
                cells.append(
                    f'<div class="panel-wrap">'
                    f'<div class="panel-label">{PHASE_LABEL[phase]} · {lab}</div>'
                    f'<div class="panel" data-phase="{phase}" data-channel="{ch}"{mip_attr}{tint_attr}>'
                    f'<video data-src="{src}"{fps_attr} muted playsinline preload="none"></video>'
                    f'{mip_img}'
                    f'<canvas></canvas>'
                    f'</div></div>'
                )
            # Live channel-merge panel: composite of all channels (timepoint-aligned
            # via the master t_sec sync), with per-channel toggle checkboxes.
            if len(chans) >= 2:
                toggles = "".join(
                    f'<label class="mg-tog"><input type="checkbox" checked data-mg-ch="{c}" '
                    f'data-mg-color="{channel_color(c, ch_names)}">'
                    f'<span class="mg-sw" style="background:{channel_color(c, ch_names)}"></span>'
                    f'{channel_label(c, ch_names)}</label>'
                    for c in chans)
                cells.append(
                    f'<div class="panel-wrap merge-wrap">'
                    f'<div class="panel-label">{PHASE_LABEL[phase]} · Merge</div>'
                    f'<div class="panel merge-panel" data-phase="{phase}" data-merge="1">'
                    f'<canvas class="merge-canvas"></canvas>'
                    f'</div>'
                    f'<div class="mg-toggles">{toggles}</div>'
                    f'</div>'
                )
            if cells:
                rows.append(
                    f'<div><div class="row-label">{PHASE_LABEL[phase]}</div>'
                    f'<div class="row" data-cols="{len(cells)}">{"".join(cells)}</div></div>'
                )
        meta_html = "".join(
            f'<div class="md-item"><span class="md-k">{k}:</span> '
            f'<span class="md-v">{v}</span></div>'
            for k, v in md
        )
        section = (
            f'<section class="batch-section" data-batch="{bn}" style="display:none">'
            f'<div class="batch-meta">{meta_html or "<em>no master-CSV metadata</em>"}</div>'
            + "\n".join(rows) +
            "</section>"
        )
        sections.append(section)
        metas.append({"name": bn,
                      "key_times": key_times,
                      "phase_ranges": phase_ranges,
                      "ch_names": ch_names,
                      "ablation_events": abl_events})

    nav = (
        '<div id="batch-nav">'
        '<button id="prev-batch" class="action-btn subtle">◀ Prev batch</button>'
        '<span id="batch-title">—</span>'
        '<button id="next-batch" class="action-btn subtle">Next batch ▶</button>'
        '</div>'
    )

    html = (MULTI_TEMPLATE
            .replace("__SECTIONS__", "\n".join(sections))
            .replace("__NAV__", nav)
            .replace("__BATCH_METAS__", json.dumps(metas))
            .replace("__KT_BUTTONS__", kt_button_html()))
    with open(out_path, "w") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-dir", help="Source batch folder (single-batch mode)")
    ap.add_argument("--pkg-dir",   help="Package output folder (single-batch mode)")
    ap.add_argument("--multi-batch", help="JSON list of {name, pkg_dir} for multi-batch index")
    ap.add_argument("--index-out", help="Output path for the multi-batch index HTML")
    ap.add_argument("--pkg-root", help="Common parent folder for all batch packages")
    ap.add_argument("--phases", default="abl,mon",
        help="Comma-separated movie phases to render in multi-batch mode "
             "(default 'abl,mon'). Use 'abl' for an ablation-only index.")
    args = ap.parse_args()

    # Multi-batch index mode
    if args.multi_batch:
        specs = json.loads(args.multi_batch)
        if not (args.index_out and args.pkg_root):
            sys.exit("--multi-batch requires --index-out and --pkg-root")
        phases = tuple(p.strip() for p in args.phases.split(",") if p.strip())
        build_multi_batch_index(specs, args.pkg_root, args.index_out, phases=phases)
        print(f"  → {args.index_out}  (phases={phases})")
        return

    if not (args.batch_dir and args.pkg_dir):
        sys.exit("Either --batch-dir/--pkg-dir or --multi-batch is required")
    if not os.path.isdir(args.batch_dir):
        sys.exit(f"Not a directory: {args.batch_dir}")
    os.makedirs(args.pkg_dir, exist_ok=True)

    batch_name = os.path.basename(args.batch_dir.rstrip("/"))
    mp4s = find_flat_mp4s(args.batch_dir, batch_name)
    if not mp4s:
        sys.exit(f"No usable pipeline MP4s found in {args.batch_dir}")
    print(f"[{batch_name}] found {len(mp4s)} MP4(s):")
    for k, v in sorted(mp4s.items()):
        print(f"  {k[0]}/{k[1]:5s} → {os.path.basename(v)}  ({os.path.getsize(v)/1e6:.1f} MB)")

    copied = copy_mp4s_into_package(mp4s, args.pkg_dir)
    print(f"  copied {len(copied)} MP4(s) into {args.pkg_dir}")

    key_times = load_master_key_times(batch_name)
    if key_times:
        print(f"  key times from master CSV: " +
              ", ".join(f"{k['label']}={k['t_sec']:.0f}s" for k in key_times))

    # Compute phase metadata for jump-to-frame + per-video fps
    frames_json = os.path.join(args.batch_dir, f"{batch_name}_frames.json")
    phase_starts = {}     # phase → t_sec at which that phase's MP4 begins
    phase_frames = {}     # phase → number of frames in that phase's MP4
    if os.path.isfile(frames_json):
        with open(frames_json) as f:
            meta = json.load(f)
        counts = {"pre": 0, "abl": 0, "mon": 0}
        for fr in meta.get("frames", []):
            role = fr.get("role")
            t = float(fr.get("t_sec", 0))
            if role == "ablation":
                if t < 0: counts["pre"] += 1
                else:     counts["abl"] += 1
            elif role == "monitoring":
                counts["mon"] += 1
        phase_frames = {k: v for k, v in counts.items() if v > 0}

        for phase_key, role_match in (("pre", "ablation"), ("abl", "ablation"), ("mon", "monitoring")):
            for fr in meta.get("frames", []):
                if fr.get("role") == role_match:
                    if phase_key == "pre" and float(fr.get("t_sec", 0)) >= 0:
                        continue
                    if phase_key == "abl" and float(fr.get("t_sec", 0)) < 0:
                        continue
                    phase_starts.setdefault(phase_key, float(fr.get("t_sec", 0)))

    html_path = write_html(args.pkg_dir, batch_name, copied,
                           key_times=key_times, phase_starts=phase_starts,
                           phase_frames=phase_frames)
    print(f"  → {html_path}")


if __name__ == "__main__":
    main()
