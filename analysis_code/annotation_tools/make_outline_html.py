#!/usr/bin/env python3
"""make_outline_html.py — generates `outline_index.html`, a stripped-down
multi-batch viewer focused on serial cell-outline tracking.

Workflow per batch:
   1. View opens at the first ablation event (t = abl_start).
   2. User drags a freehand outline of the cell.
   3. Click "+10 min" → page seeks to the closest available frame whose
      t_sec ≥ current + 600 (skips into monitoring if needed; tolerates
      acquisition gaps by jumping to nearest after the target time).
   4. Outline again, repeat. Stops when no frame >current + 600 exists.
   5. Click Next batch.

All outlines autosave to a SEPARATE master CSV
(/Volumes/4 MB/annotations/outlines_master.csv) so they don't mix with
the full annotator's CSV.

This file reuses helpers from make_annotation_html.py — wavelength color,
master-CSV lookup, phase ranges — for consistency.
"""

import argparse
import json
import os
import sys

# Re-use the existing module's helpers (loaded as module import).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_annotation_html import (
    PHASE_LABEL, MASTER_CSV,
    load_master_metadata, _read_phase_time_ranges,
    load_master_key_times,
)


OUTLINE_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Outline tracker</title>
<style>
  :root { --bg:#111; --fg:#e8e8e8; --panel-bg:#1c1c1c; --accent:#5fa8ff; --border:#2a2a2a; }
  * { box-sizing: border-box; }
  html,body { margin:0; padding:0; background:var(--bg); color:var(--fg);
              font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
  body { display:grid; grid-template-columns: 1fr 340px; height:100vh; overflow:hidden; }
  #grid-area { padding:12px; overflow:auto; display:flex; flex-direction:column; gap:10px; }
  #batch-nav { background:var(--panel-bg); padding:8px 12px; border-radius:6px;
               display:flex; align-items:center; justify-content:space-between; gap:10px; }
  #batch-title { font-weight:500; font-size:15px; }
  .row { display:grid; gap:8px; }
  .row[data-cols="1"] { grid-template-columns: 1fr; }
  .row[data-cols="2"] { grid-template-columns: repeat(2,1fr); }
  .row-label { font-size:12px; color:#888; margin-bottom:4px; text-transform:uppercase; letter-spacing:.05em; }
  .panel-wrap { display:flex; flex-direction:column; }
  .panel-label { background:#2a2a2a; color:#ddd; padding:5px 8px;
                 border-radius:6px 6px 0 0; font-size:12px; font-weight:500;
                 border:1px solid var(--border); border-bottom:0; }
  .panel { background:#000; border:1px solid var(--border); border-radius:0 0 6px 6px;
           position:relative; aspect-ratio:1248/1056; overflow:hidden; }
  .panel video { width:100%; height:100%; display:block; object-fit:contain; }
  /* touch-action: pan-y → single-finger touch scrolls the page; Apple
     Pencil (pointerType="pen") still draws because pen events ignore
     touch-action restrictions. */
  .panel canvas { position:absolute; inset:0; width:100%; height:100%;
                  touch-action:pan-y; cursor:crosshair; }
  /* Sticky top bar — stays visible regardless of scroll position. */
  #sticky-top { position:sticky; top:0; z-index:100; background:var(--bg);
                padding-bottom:8px; display:flex; flex-direction:column; gap:8px; }
  #status-banner { background:#1c4a82; color:#fff; padding:9px 14px; border-radius:6px;
                   font-size:14px; }
  /* Quick-action bar (always visible) */
  #quick-bar { background:var(--panel-bg); padding:8px 12px; border-radius:6px;
               display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  #quick-bar .qa-btn { padding:10px 16px; background:#1c4a82; color:#fff;
                       border:0; border-radius:6px; cursor:pointer; font:600 14px inherit; }
  #quick-bar .qa-btn.subtle { background:#2a2a2a; color:var(--fg); }
  #quick-bar .qa-btn:active { transform: scale(0.97); }
  #status-banner.success { background:#1c6a2a; }
  #scrubber-bar { background:var(--panel-bg); padding:10px 12px; border-radius:6px;
                  display:flex; align-items:center; gap:10px; }
  #scrubber-bar input[type="range"] { flex:1; }
  #frame-label { font-variant-numeric:tabular-nums; min-width:140px; text-align:right; }
  .jump-btn { padding:6px 12px; background:#2a2a2a; border:1px solid var(--border);
              color:var(--fg); border-radius:4px; cursor:pointer; font:inherit; }
  .jump-btn:hover { background:#3a3a3a; }
  #controls { background:var(--panel-bg); border-left:1px solid var(--border);
              padding:14px; overflow-y:auto; display:flex; flex-direction:column; gap:14px; }
  #controls h3 { margin:0; font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:#888; }
  .big-btn { padding:18px 12px; background:#1c4a82; border:none; color:#fff;
             border-radius:8px; cursor:pointer; font:600 16px inherit; }
  .big-btn:hover { background:#2c5a92; }
  .big-btn.danger { background:#6c1c1c; }
  .big-btn.subtle { background:#2a2a2a; color:var(--fg); }
  .timeline { background:#181818; border:1px solid var(--border); border-radius:6px;
              padding:6px; display:flex; flex-direction:column; gap:4px; }
  .tl-row { display:flex; justify-content:space-between; align-items:center;
            padding:5px 8px; font-size:12px; border-bottom:1px solid #222; }
  .tl-row:last-child { border:0; }
  .tl-row.current { background:#1c4a82; color:#fff; border-radius:3px; }
  .tl-row .stage { font-weight:500; }
  .tl-row .t { color:#888; font-variant-numeric:tabular-nums; }
  .tl-row .actions button { background:none; border:0; color:#5fa8ff; cursor:pointer;
                            font-size:11px; padding:0 4px; }
  .tl-row .actions button.x { color:#c44; }
  #save-indicator { font-size:11px; color:#888; text-align:center; padding:4px; }
</style>
</head>
<body>

<div id="grid-area">
  <div id="sticky-top">
    <div id="batch-nav">
      <button id="prev-batch" class="jump-btn">◀ Prev batch</button>
      <span id="batch-title">—</span>
      <button id="next-batch" class="jump-btn">Next batch ▶</button>
    </div>
    <div id="quick-bar">
      <button class="qa-btn" id="plus10-top">+10 min →</button>
      <button class="qa-btn subtle" id="reset-to-abl-top">⌖ First ablation</button>
      <span style="color:#888;font-size:12px;margin:0 6px">jumps:</span>
      <span id="jump-bar" style="display:flex;gap:4px;flex-wrap:wrap;align-items:center;"></span>
    </div>
    <div id="status-banner">Drag freehand on a video to outline the cell.</div>
    <div id="scrubber-bar">
      <button id="play-pause" class="jump-btn">▶</button>
      <button class="jump-btn" id="step-back" title="◀ (← key)">◀</button>
      <input type="range" id="scrubber" min="0" max="1" step="0.01" value="0">
      <button class="jump-btn" id="step-fwd" title="▶ (→ key)">▶</button>
      <span id="frame-label">—</span>
    </div>
  </div>
  __SECTIONS__
</div>

<div id="controls">
  <div>
    <h3>Cell outline workflow</h3>
    <div style="margin:8px 0; font-size:12px; color:#aaa">
      Start: first ablation event. Outline the cell. Then click <b>+10 min</b>
      to advance, outline again. Continue until end.
    </div>
  </div>
  <button class="big-btn" id="plus10">+10 min →</button>
  <button class="big-btn subtle" id="reset-to-abl">Reset to first ablation</button>
  <div>
    <h3>Outlines saved (this batch)</h3>
    <div class="timeline" id="timeline"></div>
  </div>
  <div id="save-indicator">autosave → outlines_master.csv</div>
  <button class="big-btn danger" id="clear-batch">Clear outlines for this batch</button>
</div>

<script>
console.log('[outline] loaded');
const BATCH_METAS = __BATCH_METAS__;
const PANEL_DIMS = { w: 1248, h: 1056 };

const outlinesByBatch = new Map();
const nextIdByBatch = new Map();
BATCH_METAS.forEach(m => { outlinesByBatch.set(m.name, []); nextIdByBatch.set(m.name, 1); });

let currentBatchIdx = 0;
const sections = Array.from(document.querySelectorAll('.batch-section'));
function currentBatch() { return BATCH_METAS[currentBatchIdx]?.name || ''; }
function currentOutlines() { return outlinesByBatch.get(currentBatch()) || []; }
function nextId() { const b=currentBatch(); const id=nextIdByBatch.get(b)||1; nextIdByBatch.set(b,id+1); return id; }
function currentVideos() { return sections[currentBatchIdx] ? Array.from(sections[currentBatchIdx].querySelectorAll('video')) : []; }
function currentPanels() { return sections[currentBatchIdx] ? Array.from(sections[currentBatchIdx].querySelectorAll('.panel')) : []; }

// Status
const status = document.getElementById('status-banner');
function setStatus(text, kind) {
  status.textContent = text;
  status.className = kind || '';
  if (kind === 'success') setTimeout(() => { status.className = ''; status.textContent = 'Drag freehand on a video to outline the cell.'; }, 1500);
}

// Per-video fps
const videoInfo = new Map();
function fpsForVideo(v) { return (videoInfo.get(v) || {}).fps || 9; }
function getDuration() { return Math.max(0, ...currentVideos().map(v=>v.duration||0)); }
const scrubber = document.getElementById('scrubber');
const frameLabel = document.getElementById('frame-label');
function fmt(s){ const sign=s<0?'-':''; s=Math.abs(s); const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), sec=Math.floor(s%60); return `${sign}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`; }
function videoToT(v, phase) {
  // Convert a specific video's currentTime → t_sec using that phase's
  // frames.json mapping. Caller passes which video they care about so
  // we don't accidentally use a different (out-of-sync) panel's time.
  const meta = BATCH_METAS[currentBatchIdx];
  const ranges = meta?.phase_ranges || {};
  if (!v || !ranges[phase] || !ranges[phase].t_secs?.length) return 0;
  const ts = ranges[phase].t_secs;
  const idx = Math.round((v.currentTime / (v.duration||1)) * (ts.length - 1));
  return ts[Math.max(0, Math.min(ts.length-1, idx))];
}
function activeRealT() {
  // For the scrub-position label only. Picks whichever video is
  // furthest along — fine for an at-a-glance readout.
  let best = null, bestT = -1, bestPhase = null;
  currentVideos().forEach(v => {
    const phase = v.closest('.panel')?.dataset.phase;
    if ((v.currentTime||0) > bestT) { bestT = v.currentTime||0; best = v; bestPhase = phase; }
  });
  return videoToT(best, bestPhase);
}
function updateScrubLabel() {
  const t = activeRealT();
  frameLabel.textContent = `t = ${fmt(t)} (real)`;
}
function bindVideoMetadata() {
  document.querySelectorAll('video').forEach(v => {
    if (videoInfo.has(v)) return;
    v.addEventListener('timeupdate', () => {
      if (v.closest('.batch-section') === sections[currentBatchIdx]) {
        updateScrubLabel(); redrawAllPanels();
      }
    });
    v.addEventListener('loadedmetadata', () => {
      videoInfo.set(v, { fps: 9 });
      updateScrubLabel();
    });
  });
}

// Canvas panel setup
function setupPanelCanvases() {
  document.querySelectorAll('.panel').forEach(panel => {
    if (panel.dataset.bound) return;
    panel.dataset.bound = '1';
    const canvas = panel.querySelector('canvas');
    const video = panel.querySelector('video');
    const phase = panel.dataset.phase, channel = panel.dataset.channel;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.round(rect.width*dpr); canvas.height = Math.round(rect.height*dpr);
      redrawPanel(panel);
    };
    new ResizeObserver(resize).observe(canvas); resize();
    panel._toPanelCoords = (clientX, clientY) => {
      const rect = canvas.getBoundingClientRect();
      const vw = video.videoWidth || PANEL_DIMS.w, vh = video.videoHeight || PANEL_DIMS.h;
      const containerAR = rect.width / rect.height, videoAR = vw / vh;
      let dispW, dispH, offX, offY;
      if (videoAR > containerAR) { dispW=rect.width; dispH=rect.width/videoAR; offX=0; offY=(rect.height-dispH)/2; }
      else { dispH=rect.height; dispW=rect.height*videoAR; offY=0; offX=(rect.width-dispW)/2; }
      const cx = clientX-rect.left-offX, cy = clientY-rect.top-offY;
      return { x: Math.max(0, Math.min(vw-1, cx/dispW*vw)),
               y: Math.max(0, Math.min(vh-1, cy/dispH*vh)),
               inside: cx>=0&&cx<=dispW&&cy>=0&&cy<=dispH };
    };
    panel._toCanvasCoords = (xp, yp) => {
      const vw = video.videoWidth || PANEL_DIMS.w, vh = video.videoHeight || PANEL_DIMS.h;
      const rect = canvas.getBoundingClientRect();
      const containerAR = rect.width / rect.height, videoAR = vw / vh;
      let dispW, dispH, offX, offY;
      if (videoAR > containerAR) { dispW=rect.width; dispH=rect.width/videoAR; offX=0; offY=(rect.height-dispH)/2; }
      else { dispH=rect.height; dispW=rect.height*videoAR; offY=0; offX=(rect.width-dispW)/2; }
      const sx = canvas.width/rect.width, sy = canvas.height/rect.height;
      return { x: (offX + xp/vw*dispW)*sx, y: (offY + yp/vh*dispH)*sy };
    };
    let drawing = null;
    canvas.addEventListener('pointerdown', e => {
      // Only Apple Pencil / mouse triggers drawing. Finger touches fall
      // through so the page can scroll (iPad usability).
      if (e.pointerType !== 'pen' && e.pointerType !== 'mouse') return;
      e.preventDefault();
      const pt = panel._toPanelCoords(e.clientX, e.clientY);
      if (!pt.inside) return;
      const fps = fpsForVideo(video);
      const frame = Math.round((video.currentTime||0) * fps) + 1;
      drawing = { points:[[pt.x, pt.y]], panel, frame, phase, channel };
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', e => {
      if (!drawing) return;
      const pt = panel._toPanelCoords(e.clientX, e.clientY);
      drawing.points.push([pt.x, pt.y]);
      redrawPanel(panel);
      const ctx = canvas.getContext('2d');
      ctx.beginPath();
      drawing.points.forEach((p,i)=>{ const c=panel._toCanvasCoords(p[0],p[1]); if(i===0) ctx.moveTo(c.x,c.y); else ctx.lineTo(c.x,c.y); });
      ctx.strokeStyle = '#ff30ff'; ctx.lineWidth = 3; ctx.stroke();
    });
    canvas.addEventListener('pointerup', e => {
      if (!drawing) return;
      const d = drawing; drawing = null;
      canvas.releasePointerCapture(e.pointerId);
      if (d.points.length < 3) return;
      addOutline({
        id: nextId(), frame: d.frame, points: d.points,
        panel: `${d.phase}_${d.channel}`,
        phase: d.phase,
        t_sec: videoToT(video, d.phase),
        outline_idx: currentOutlines().length + 1,
      });
    });
  });
}

function addOutline(o) {
  currentOutlines().push(o);
  renderTimeline(); redrawAllPanels(); autosave();
  setStatus(`✓ outline #${o.outline_idx} saved at t = ${fmt(o.t_sec)}`, 'success');
}
function deleteOutline(id) {
  const arr = currentOutlines();
  const i = arr.findIndex(a => a.id === id);
  if (i >= 0) arr.splice(i, 1);
  // Renumber
  arr.forEach((a, k) => a.outline_idx = k + 1);
  renderTimeline(); redrawAllPanels(); autosave();
}
function renderTimeline() {
  const host = document.getElementById('timeline');
  host.innerHTML = '';
  const arr = currentOutlines();
  if (arr.length === 0) {
    host.innerHTML = '<div style="color:#666;text-align:center;padding:8px">no outlines yet</div>';
    return;
  }
  arr.forEach(o => {
    const row = document.createElement('div'); row.className = 'tl-row';
    const stage = o.outline_idx === 1 ? 'Ablation' : `+${(o.outline_idx-1)*10} min`;
    row.innerHTML = `<span class="stage">#${o.outline_idx} · ${stage}</span>
                     <span class="t">${fmt(o.t_sec)} · ${o.phase}</span>
                     <span class="actions"><button class="jump-to">↗</button>
                     <button class="x">×</button></span>`;
    row.querySelector('.jump-to').addEventListener('click', () => seekToT(o.t_sec));
    row.querySelector('.x').addEventListener('click', () => deleteOutline(o.id));
    host.appendChild(row);
  });
}
function redrawPanel(panel) {
  const ctx = panel.querySelector('canvas').getContext('2d');
  const canvas = panel.querySelector('canvas');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const myKey = `${panel.dataset.phase}_${panel.dataset.channel}`;
  const video = panel.querySelector('video');
  const current = Math.round((video.currentTime||0) * fpsForVideo(video)) + 1;
  for (const o of currentOutlines()) {
    if (o.panel !== myKey) continue;
    if (o.frame !== current) continue;
    ctx.beginPath();
    o.points.forEach((p, i) => {
      const c = panel._toCanvasCoords(p[0], p[1]);
      if (i === 0) ctx.moveTo(c.x, c.y); else ctx.lineTo(c.x, c.y);
    });
    ctx.closePath();
    ctx.strokeStyle = '#ff30ff'; ctx.lineWidth = 3; ctx.stroke();
    ctx.fillStyle = '#fff'; ctx.font = '11px sans-serif';
    ctx.fillText(`#${o.outline_idx}`, o.points[0][0] * canvas.width / PANEL_DIMS.w + 4,
                                       o.points[0][1] * canvas.height / PANEL_DIMS.h - 4);
  }
}
function redrawAllPanels() { currentPanels().forEach(redrawPanel); }

// ── Seek by absolute real-time t_sec ──
function seekToT(target_t) {
  console.log(`[seekToT] target=${target_t}s  batch=${currentBatch()}`);
  const meta = BATCH_METAS[currentBatchIdx];
  const ranges = meta?.phase_ranges || {};
  // 1. Pick the phase whose [start, end] contains target_t.
  // 2. If none contains it (e.g. event is in a gap), pick the next-later
  //    phase whose start is >= target_t, otherwise the last phase.
  const phaseOrder = ['pre', 'abl', 'mon'];
  let bestPhase = null;
  for (const phase of phaseOrder) {
    const r = ranges[phase];
    if (!r) continue;
    if (target_t >= r.start && target_t <= r.end) { bestPhase = phase; break; }
  }
  if (!bestPhase) {
    // Pick the closest phase by either end (after) or start (before).
    let bestDist = Infinity;
    for (const phase of phaseOrder) {
      const r = ranges[phase];
      if (!r) continue;
      const dist = target_t < r.start ? (r.start - target_t)
                 : target_t > r.end   ? (target_t - r.end)
                 : 0;
      if (dist < bestDist) { bestDist = dist; bestPhase = phase; }
    }
  }
  if (!bestPhase) {
    setStatus(`No phase data for ${fmt(target_t)}`, '');
    return null;
  }
  const r = ranges[bestPhase];
  // Find the closest acquired frame to target_t via binary search on
  // per-frame t_secs (frames.json). Then convert that frame index to the
  // MP4's video time using the ACTUAL mp4 frame count (via ffprobe) —
  // this is the only mapping that's accurate even when the pipeline
  // encoded MP4s with a different frame count from the t_secs array.
  const ts = r.t_secs || [];
  const mp4N = (meta?.mp4_frames || {})[bestPhase];
  let bestIdx = 0, bestDiff = Infinity, frac;
  if (ts.length > 0) {
    let lo = 0, hi = ts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (ts[mid] < target_t) lo = mid + 1; else hi = mid;
    }
    bestIdx = lo;
    if (lo > 0 && Math.abs(ts[lo-1] - target_t) < Math.abs(ts[lo] - target_t)) bestIdx = lo - 1;
    bestDiff = Math.abs(ts[bestIdx] - target_t);
    // If MP4 frame count is known and differs from t_secs.length, scale
    // the index proportionally so we land on the correct MP4 frame.
    const effN = mp4N || ts.length;
    const scaledIdx = mp4N
      ? Math.round(bestIdx * (mp4N - 1) / Math.max(1, ts.length - 1))
      : bestIdx;
    frac = scaledIdx / Math.max(1, effN - 1);
  } else {
    const span = r.end - r.start;
    frac = span > 0 ? Math.max(0, Math.min(1, (target_t - r.start) / span)) : 0;
  }
  const vs = currentVideos().filter(v => v.closest('.panel')?.dataset.phase === bestPhase);
  currentVideos().forEach(v => {
    if (v.closest('.panel')?.dataset.phase !== bestPhase) v.currentTime = 0;
  });
  vs.forEach(v => {
    const tt = Math.max(0, Math.min((v.duration||0) - 1e-6, frac * (v.duration||0)));
    v.currentTime = tt;
  });
  // Auto-scroll to the panel we just seeked so the user sees the result.
  if (vs[0]) {
    vs[0].closest('.panel-wrap')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  console.log(`[seekToT] → phase=${bestPhase}, frac=${frac.toFixed(3)}, video_time=${(frac*(vs[0]?.duration||0)).toFixed(2)}s, target_frame_t_sec=${ts.length?ts[bestIdx]:'?'}`);
  setTimeout(() => { updateScrubLabel(); redrawAllPanels(); }, 60);
  return { phase: bestPhase,
           t_sec: ts.length ? ts[bestIdx] : r.start,
           diff: bestDiff };
}

// "First ablation" target is the laser-fire moment (t_sec ≈ 0 in the
// pipeline's reference). seekToT will find the closest acquired abl
// frame, which is the right behavior — there's typically no frame at
// exactly t_sec=0 because of acquisition timing, so we land on whichever
// is closest. Returns null if the batch has no abl phase at all.
function firstAblationTime() {
  const r = BATCH_METAS[currentBatchIdx]?.phase_ranges?.abl;
  if (!r) return null;
  return 0;
}

function doPlus10() {
  const last = currentOutlines()[currentOutlines().length - 1];
  const fa = firstAblationTime();
  const baseT = last ? last.t_sec : (fa ?? 0);
  const target = baseT + 600;
  const result = seekToT(target);
  if (result) {
    const gap = Math.round(result.diff);
    setStatus(`Jumped to ${fmt(result.t_sec)} (${result.phase})` +
              (gap > 30 ? ` — nearest frame, ${gap}s past target` : ''), 'success');
  }
}
function doResetToAbl() {
  const t = firstAblationTime();
  if (t === null) {
    setStatus(`This batch has no ablation phase — nothing to jump to.`, '');
    return;
  }
  const result = seekToT(t);
  if (result) setStatus(`Jumped to first acquired ablation frame at ${fmt(result.t_sec)} (${result.phase} video)`, 'success');
}
document.getElementById('plus10').addEventListener('click', doPlus10);
document.getElementById('reset-to-abl').addEventListener('click', doResetToAbl);
document.getElementById('plus10-top').addEventListener('click', doPlus10);
document.getElementById('reset-to-abl-top').addEventListener('click', doResetToAbl);

// Frame step + keyboard
function stepFrames(n) {
  currentVideos().forEach(v => {
    const fps = fpsForVideo(v);
    v.currentTime = Math.max(0, Math.min((v.duration||1)-1e-6, (v.currentTime||0) + n/fps));
  });
  setTimeout(() => { updateScrubLabel(); redrawAllPanels(); }, 40);
}
document.getElementById('step-back').addEventListener('click', () => stepFrames(-1));
document.getElementById('step-fwd' ).addEventListener('click', () => stepFrames( 1));
document.getElementById('play-pause').addEventListener('click', () => {
  const vs = currentVideos();
  if (vs[0]?.paused) { vs.forEach(v=>v.play()); document.getElementById('play-pause').textContent='⏸'; }
  else { vs.forEach(v=>v.pause()); document.getElementById('play-pause').textContent='▶'; }
});
document.addEventListener('keydown', e => {
  if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'ArrowLeft')  { stepFrames(e.shiftKey?-10:-1); e.preventDefault(); }
  else if (e.key === 'ArrowRight'){ stepFrames(e.shiftKey?10:1); e.preventDefault(); }
  else if (e.key === ' ')         { document.getElementById('play-pause').click(); e.preventDefault(); }
  else if (e.key === 'n' || e.key === 'N') goNext();
  else if (e.key === 'p' || e.key === 'P') goPrev();
});

// Multi-batch nav
const titleEl = document.getElementById('batch-title');
function rebuildJumpBar() {
  const jumpBar = document.getElementById('jump-bar');
  jumpBar.innerHTML = '';
  const meta = BATCH_METAS[currentBatchIdx];
  const kts = meta?.key_times || [];
  jumpBar.appendChild(Object.assign(document.createElement('span'),
    { textContent: 'Jump to:', style:'color:#888;font-size:12px;margin-right:4px' }));
  // "First ablation" jump — disabled for batches without abl phase
  const ablT = firstAblationTime();
  const abl = document.createElement('button');
  abl.className = 'jump-btn';
  if (ablT !== null) {
    abl.textContent = `First ablation (${fmt(ablT)})`;
    abl.addEventListener('click', doResetToAbl);
  } else {
    abl.textContent = 'First ablation (no abl phase)';
    abl.disabled = true;
    abl.style.opacity = '0.5';
  }
  jumpBar.appendChild(abl);
  if (kts.length === 0) {
    jumpBar.appendChild(Object.assign(document.createElement('span'),
      { textContent: '  (no NEB/Meta/Ana in master CSV)', style:'color:#666;font-size:11px' }));
    return;
  }
  kts.forEach(k => {
    const b = document.createElement('button');
    b.className = 'jump-btn';
    b.textContent = `${k.label} (${fmt(k.t_sec)})`;
    b.addEventListener('click', () => {
      const r = seekToT(k.t_sec);
      if (r) setStatus(`Jumped to ${k.label} (${fmt(r.t_sec)} ${r.phase})`, 'success');
    });
    jumpBar.appendChild(b);
  });
}

function showBatch(i) {
  if (i < 0 || i >= sections.length) return;
  currentBatchIdx = i;
  sections.forEach((s, j) => { s.style.display = j === i ? '' : 'none'; });
  titleEl.textContent = `${i+1}/${sections.length} · ${currentBatch()}`;
  // Lazy-load videos: set src on this batch's videos, clear src on
  // far-away batches to free bandwidth/memory. Preload adjacent batches.
  sections.forEach((s, j) => {
    const vids = s.querySelectorAll('video');
    if (j === i || Math.abs(j - i) === 1) {
      vids.forEach(v => {
        if (!v.src && v.dataset.src) {
          v.src = v.dataset.src;
          v.preload = 'auto';
        }
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
  setupPanelCanvases(); bindVideoMetadata();
  rebuildJumpBar();
  setTimeout(() => {
    // Auto-seek to first ablation when entering a batch (if abl exists).
    const fa = firstAblationTime();
    if (fa !== null) seekToT(fa);
    updateScrubLabel(); redrawAllPanels(); renderTimeline();
  }, 200);
}
function goPrev() { if (currentBatchIdx > 0) showBatch(currentBatchIdx - 1); }
function goNext() { if (currentBatchIdx < sections.length - 1) showBatch(currentBatchIdx + 1); }
document.getElementById('prev-batch').addEventListener('click', goPrev);
document.getElementById('next-batch').addEventListener('click', goNext);

document.getElementById('clear-batch').addEventListener('click', () => {
  if (!confirm(`Delete all outlines for ${currentBatch()}?`)) return;
  outlinesByBatch.set(currentBatch(), []);
  renderTimeline(); redrawAllPanels(); autosave();
});

// ── Autosave to dedicated outlines_master.csv ──
const _saveTimers = new Map();
function autosave() {
  const batch = currentBatch();
  if (_saveTimers.has(batch)) clearTimeout(_saveTimers.get(batch));
  _saveTimers.set(batch, setTimeout(() => sendToServer(batch), 600));
}
function sendToServer(batch) {
  const arr = outlinesByBatch.get(batch) || [];
  const rows = arr.map(o => ({
    id: o.id,
    image_file: `${o.panel||''}.tif`,
    type: 'cell_outline',
    label: `outline_${o.outline_idx}`,
    frame: o.frame,
    x: '', y: '',
    points: '[' + o.points.map(p=>`[${p[0].toFixed(2)},${p[1].toFixed(2)}]`).join(',') + ']',
    length_um:'', area_um2:'', perimeter_um:'',
    circularity:'', aspect_ratio:'', roundness:'', solidity:'',
    pixel_size_um: '0.062',
    notes: `outline_idx=${o.outline_idx}; phase=${o.phase}; t_sec=${o.t_sec.toFixed(2)}`
  }));
  const indicator = document.getElementById('save-indicator');
  if (indicator) indicator.textContent = '💾 saving…';
  fetch('/save?master_csv=' + encodeURIComponent('/Volumes/4 MB/annotations/outlines_master.csv'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batch, rows })
  }).then(r=>r.json()).then(j => {
    if (indicator) indicator.textContent = j.ok
      ? `✓ saved ${rows.length} → outlines_master.csv`
      : `⚠ ${j.error||'unknown'}`;
  }).catch(e => { if (indicator) indicator.textContent = `⚠ ${e}`; });
}

showBatch(0);
</script>
</body>
</html>
"""


def render_grid(mp4_rel):
    """Render videos with data-src instead of src so they don't all
    eagerly download on page load. JS sets src only on the active batch."""
    phases = ["pre", "abl", "mon"]
    channels = ["phase", "fluor"]
    rows = []
    for phase in phases:
        cells = []
        for ch in channels:
            if (phase, ch) not in mp4_rel: continue
            src = mp4_rel[(phase, ch)]
            cells.append(
                f'<div class="panel-wrap">'
                f'<div class="panel-label">{PHASE_LABEL[phase]} · {ch}</div>'
                f'<div class="panel" data-phase="{phase}" data-channel="{ch}">'
                f'<video data-src="{src}" muted playsinline preload="none"></video>'
                f'<canvas></canvas>'
                f'</div></div>'
            )
        if cells:
            rows.append(
                f'<div><div class="row-label">{PHASE_LABEL[phase]}</div>'
                f'<div class="row" data-cols="{len(cells)}">{"".join(cells)}</div></div>'
            )
    return "\n".join(rows)


def _mp4_frame_count(path):
    """Run ffprobe to get the actual frame count of an MP4. None on failure."""
    import subprocess
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_packets", "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0", path
        ], stderr=subprocess.DEVNULL, timeout=20).decode().strip()
        return int(out)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def build_outline_index(specs, pkg_root, out_path):
    sections = []
    metas = []
    for s in specs:
        bn, pkg = s["name"], s["pkg_dir"]
        rel = os.path.relpath(pkg, pkg_root)
        present = {}
        mp4_frames = {}   # phase → fluor MP4's frame count (used for seek math)
        for phase in ("pre", "abl", "mon"):
            for ch in ("phase", "fluor"):
                f = os.path.join(pkg, f"{phase}_{ch}.mp4")
                if os.path.isfile(f):
                    present[(phase, ch)] = f"{rel}/{phase}_{ch}.mp4"
                    if ch == "fluor" and phase not in mp4_frames:
                        n = _mp4_frame_count(f)
                        if n: mp4_frames[phase] = n
        if not present:
            print(f"  [skip] {bn} — no MP4s in {pkg}")
            continue
        phase_ranges = _read_phase_time_ranges(bn)
        key_times = load_master_key_times(bn)
        section = (
            f'<section class="batch-section" data-batch="{bn}" style="display:none">'
            + render_grid(present) +
            '</section>'
        )
        sections.append(section)
        metas.append({"name": bn,
                      "phase_ranges": phase_ranges,
                      "key_times": key_times,
                      "mp4_frames": mp4_frames})

    html = (OUTLINE_TEMPLATE
            .replace("__SECTIONS__", "\n".join(sections))
            .replace("__BATCH_METAS__", json.dumps(metas)))
    with open(out_path, "w") as f:
        f.write(html)
    print(f"  → {out_path}  ({len(specs)} batches → {len(metas)} usable)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--specs", required=True,
        help="JSON list of {name, pkg_dir}")
    ap.add_argument("--pkg-root", required=True)
    ap.add_argument("--out", required=True,
        help="Output path for outline_index.html")
    args = ap.parse_args()
    specs = json.loads(args.specs)
    build_outline_index(specs, args.pkg_root, args.out)


if __name__ == "__main__":
    main()
