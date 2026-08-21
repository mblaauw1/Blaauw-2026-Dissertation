#!/usr/bin/env python3
"""Timestrip extras, rebuilt to USE the page's own drawing instead of duplicating it.

USER 2026-08-10, on the previous version:
  1. "the crop box ... is shown on following frames as a dashed blue rectanglee (that is not what I drew nor
      the size that will be appropriatee for a timestrip built to the 'aligned' standards)"
  2. "Timestrip zoom crop box placement is also not working correctly as when I click on a frame to place it,
      it's not the predefined size. And I need centering point to leave a mark on the slides when I click
      ... these centering marks too should leave artifacts in other frames"

WHAT WAS ACTUALLY WRONG. My overlay drew boxes on a canvas of its own, mapping image coords with
`clientWidth / videoWidth`. That ignores devicePixelRatio AND the letterboxing that puts black bars beside
the movie, so the rectangle came out the wrong size and in the wrong place -- and it was drawn dashed blue
rather than in the page's own style. Meanwhile the page ALREADY solves all of this:

    panel._toCanvasCoords(x, y)                          <- the correct image -> canvas transform
    if (!a.all_frames && a.frame !== current) continue;  <- crop boxes persist across frames NATIVELY
    if (!cropSize) { ...drag to define... } else { ...click stamps the stored size... }

So this version deletes the private overlay and instead:
  * sets `crop-all-frames` when a timestrip crop button is used, so the box persists on every frame, drawn
    by the page in its own colour and geometry -- item 1 fixed by removing my code, not adding more;
  * pre-loads the ALIGNED standard size (STD_ZOOM_HALF_UM = 4.34 um -> 8.7 um window) into the page's
    `cropSize` when the ZOOM crop button is picked, so a click stamps the right box -- item 2;
  * hooks redrawPanel AFTER the native draw and renders centring marks from EVERY frame through
    `panel._toCanvasCoords`, ghosted for other frames and solid for this one, so a centring point leaves a
    visible artifact and you can see where it sits on past/future frames -- item 2;
  * keeps the ablation->monitoring pan bar and the counters.
Nothing here draws with its own coordinate maths, so this class of bug cannot come back.
"""
import sys, os, re

MARK = "<!-- TIMESTRIP-EXTRAS -->"
END = "<!-- /TIMESTRIP-EXTRAS -->"

# 8.7 um window at 0.062 um/px = 140 px, matching ts_render.STD_ZOOM_HALF_UM (4.34 um half-width)
ZOOM_PX = 140          # = 2 * ts_render.zoom_half_px(0.062) — the standard 8.68 µm close-up window
UM_PER_PX = 0.062      # every clip in these packages is 1248x1056 at this pixel size (checked 2026-08-10)

BLOCK = MARK + """
<style>
  /* ── ITEM 4: reclaim the black space beside the movies ────────────────────────────────────────
     USER 2026-08-10: "they do have large black spacers on either side, and this is a lot of room that
     could be made if the spacers were removed". Measured cause: 34 rows carry data-cols="3" while holding
     only TWO panels, and `.row > * { max-width:32% }` caps each panel at 32% of the row. Two panels then
     occupy 64% and 36% of the width is empty. The cap is lifted and data-cols is corrected to the real
     panel count below, so the two movies fill the row -- bigger movies AND a shorter page, which is also
     what makes the scroll bearable. The movies are never shrunk. */
  .row > * { max-width: none !important; }
  .row[data-cols="2"] { grid-template-columns: repeat(2, minmax(0,1fr)) !important; }
  /* controls as a RIGHT-HAND COLUMN so the per-button mark lists are always on screen instead of at the
     bottom of a long scroll (her item 4). Width is modest and comes out of space just reclaimed. */
  /* USER 2026-08-10: "i like the side placement of the buttons, but can you make the space given to it
     about 2.5 times as wide?" 330 -> 825px. The movies keep the rest of the width; because the earlier fix
     lifted the 32% per-panel cap and corrected data-cols, the two panels now fill whatever remains, so the
     wider sidebar is paid for out of space that was previously empty rather than out of the movies.
     At 825px the button column can hold two columns of buttons with their mark lists side by side. */
  @media (min-width: 1100px){
    #controls{ position:fixed; top:0; right:0; width:825px; height:100vh; overflow-y:auto;
               border-top:none; border-left:1px solid var(--border); z-index:40;
               display:block !important; }
    #grid-area, #top-strip{ margin-right:833px; }
    #controls #tool-buttons-flow{ column-width:250px !important; column-gap:14px !important; }
    #controls .btn-marks{ max-height:none !important; }
  }
  /* below 1600px total the sidebar would crowd the movies, so it narrows rather than squeezing them */
  @media (min-width: 1100px) and (max-width: 1599px){
    #controls{ width:430px; }
    #grid-area, #top-strip{ margin-right:438px; }
    #controls #tool-buttons-flow{ column-width:190px !important; }
  }
  #ts-panbar{flex:1 1 100%;display:flex;align-items:center;gap:8px;margin-top:4px}
  #ts-panbar input[type=range]{flex:1 1 auto}
  #ts-panbar .lab{font-size:11.5px;color:#8ab4f8;white-space:nowrap;min-width:200px}
  #ts-counts{flex:1 1 100%;font-size:11.5px;color:#9fd39f;white-space:nowrap;margin-top:2px}
  #ts-zoombar{display:flex;align-items:center;gap:6px;margin:4px 0 8px;font-size:11.5px;color:#8ab4f8}
  #ts-zoombar .lab{white-space:nowrap}
  #ts-zoombar button{background:#243040;color:#cfe3ff;border:1px solid #3a4a60;border-radius:4px;
    padding:1px 7px;cursor:pointer;font-size:11.5px;line-height:1.5}
  #ts-zoombar button:hover{background:#2f3f55}
  #ts-zoom-val{color:#9fd39f;white-space:nowrap;min-width:150px;text-align:center}
</style>
<script>
(function(){
  /* The STANDARD window, and where it comes from: ts_render.STD_ZOOM_HALF_UM = 70px * 0.062 um = 4.34 um
     HALF, so the full box is 140 px = 8.68 um. That is the same region the ablation-event close-ups crop
     (group_timestrips.aligned_closeup_panels half=70; closeup_portions half=zoom_half_px(pxs)=70, whose
     `zoom=3` only upscales the crop for display and does not widen it). Every clip is 1248x1056 at
     0.062 um/px, so 140 px means the same thing on the slide as in the strip.
     USER 2026-08-10 read the stamped box as too big, so the size is now SHOWN in um and adjustable here
     rather than being a constant only the source reveals. Her chosen size persists across slides. */
  var ZOOM_STD = __ZOOM_PX__;
  var ZOOM_KEY = 'ts_zoom_px_v1';
  var ZOOM_PX  = (function(){ var v = parseInt(localStorage.getItem(ZOOM_KEY)||'',10);
                              return (v && v>=20 && v<=600) ? v : ZOOM_STD; })();
  var UM_PER_PX = __UM_PER_PX__;
  function anns(){ try{ return (typeof currentAnns==='function')?currentAnns():[]; }catch(e){ return []; } }
  function sec(){ try{ return sections[currentBatchIdx]; }catch(e){ return document; } }

  /* ── zoom-box size: visible in um, adjustable, persisted ───────────────────────────────────────── */
  function zoomLabel(){
    var el = document.getElementById('ts-zoom-val');
    if(el) el.textContent = ZOOM_PX + ' px  (' + (ZOOM_PX*UM_PER_PX).toFixed(1) + ' µm)'
                            + (ZOOM_PX===ZOOM_STD ? '  ✓ standard' : '');
  }
  function setZoom(px){
    ZOOM_PX = Math.max(20, Math.min(600, px));
    try{ localStorage.setItem(ZOOM_KEY, String(ZOOM_PX)); }catch(e){}
    if(typeof setCropSize==='function'){ try{ setCropSize(ZOOM_PX, ZOOM_PX); }catch(e){} }
    zoomLabel();
  }
  function buildZoomUI(){
    if(document.getElementById('ts-zoombar')) return;
    var host = document.getElementById('tool-buttons-flow') || document.getElementById('controls');
    if(!host) return;
    var d = document.createElement('div');
    d.id = 'ts-zoombar';
    d.innerHTML = '<span class="lab">zoom box</span>'
                + '<button type="button" data-z="-10">−</button>'
                + '<span id="ts-zoom-val"></span>'
                + '<button type="button" data-z="10">+</button>'
                + '<button type="button" data-z="std">reset</button>';
    host.parentNode.insertBefore(d, host);
    d.addEventListener('click', function(e){
      var b = e.target.closest ? e.target.closest('button[data-z]') : null;
      if(!b) return;
      e.preventDefault(); e.stopPropagation();
      setZoom(b.dataset.z==='std' ? ZOOM_STD : ZOOM_PX + parseInt(b.dataset.z,10));
    }, true);
    zoomLabel();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', buildZoomUI);
  else buildZoomUI();

  /* ── crop buttons: name + persist-on-all-frames + the aligned standard size for the ZOOM row ────── */
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('.btn[data-tool^="tsbox:"]') : null;
    if(!b) return;
    var name = (b.dataset.tool||'').slice(6);
    var inp = document.getElementById('crop-name');
    if(inp){ inp.value = name; inp.dispatchEvent(new Event('input',{bubbles:true})); }
    /* persist across frames using the page's OWN all_frames flag, so it is drawn by the page */
    var all = document.getElementById('crop-all-frames');
    if(all && !all.checked){ all.checked = true; all.dispatchEvent(new Event('change',{bubbles:true})); }
    /* ZOOM row = the aligned standard window, so a click stamps the right size instead of whatever was
       last dragged. MAIN row keeps whatever size she dragged for this cell. */
    if(name === 'timestrip_zoom' && typeof setCropSize === 'function'){
      try{ setCropSize(ZOOM_PX, ZOOM_PX); }catch(err){}
    }
  }, true);

  /* ── centring marks: visible, and echoed onto other frames ──────────────────────────────────────
     Drawn INSIDE the page's redraw using panel._toCanvasCoords, so the geometry is the page's, not mine. */
  function drawCentres(panel){
    try{
      if(!panel || !panel._toCanvasCoords) return;
      var cv = panel.querySelector('canvas'); if(!cv) return;
      var ctx = cv.getContext('2d');
      var v = panel.querySelector('video'); if(!v) return;
      var cur = Math.round((v.currentTime||0) * (typeof fpsForVideo==='function'?fpsForVideo(v):4)) + 1;
      var myPhase = panel.dataset.phase;
      anns().forEach(function(a){
        if(a.type!=='timestrip_frame' || a.label!=='centre') return;
        if(a.phase && a.phase!==myPhase) return;
        var p = panel._toCanvasCoords(a.x, a.y);
        var here = (a.frame === cur);
        ctx.save();
        ctx.strokeStyle = here ? '#39d353' : 'rgba(57,211,83,0.42)';   // ghosted when it belongs to another frame
        ctx.lineWidth = here ? 2.2 : 1.4;
        var r = here ? 11 : 8;
        ctx.beginPath(); ctx.moveTo(p.x-r,p.y); ctx.lineTo(p.x+r,p.y);
                         ctx.moveTo(p.x,p.y-r); ctx.lineTo(p.x,p.y+r); ctx.stroke();
        ctx.beginPath(); ctx.arc(p.x,p.y,r*0.55,0,Math.PI*2); ctx.stroke();
        if(!here){ ctx.fillStyle='rgba(57,211,83,0.75)'; ctx.font='9px system-ui';
                   ctx.fillText('f'+a.frame, p.x+r+2, p.y-2); }
        ctx.restore();
      });
    }catch(e){}
  }

  /* ITEM 4: set data-cols to the ACTUAL panel count so a 2-panel row is a 2-column grid, not 2 of 3 */
  function fixCols(){
    try{
      Array.from(document.querySelectorAll('.row')).forEach(function(r){
        var n = r.querySelectorAll('.panel-wrap').length;
        if(n>0 && r.dataset.cols !== String(n)) r.dataset.cols = String(n);
      });
    }catch(e){}
  }

  /* ── pan bar: every ABLATION frame, then every MONITORING frame ─────────────────────────────────── */
  var host=document.getElementById('batch-meta-host');
  if(host && !document.getElementById('ts-panbar')){
    var bar=document.createElement('div'); bar.id='ts-panbar';
    bar.innerHTML='<button class="action-btn subtle" id="ts-pan-prev">&#9664;</button>'
                + '<input type="range" id="ts-pan" min="0" max="0" value="0" step="1">'
                + '<button class="action-btn subtle" id="ts-pan-next">&#9654;</button>'
                + '<span class="lab" id="ts-pan-lab">pan: ablation &rarr; monitoring</span>';
    host.appendChild(bar);
  }
  var STEPS=[];
  function vidsOf(role){ return Array.from(sec().querySelectorAll('.panel[data-phase="'+role+'"] video')); }
  function buildSteps(){
    STEPS=[];
    ['abl','mon'].forEach(function(role){
      var vs=vidsOf(role); if(!vs.length) return;
      var v=vs.find(function(x){return (x.dataset.src||'').indexOf('fluor')>=0;})||vs[0];
      var fps=parseFloat(v.dataset.fps||'4')||4, dur=v.duration||0;
      if(!dur) return;
      var n=Math.max(1,Math.round(dur*fps));
      for(var k=0;k<n;k++) STEPS.push({role:role, idx:k, n:n, t:k/fps});
    });
    var sl=document.getElementById('ts-pan'); if(sl) sl.max=String(Math.max(0,STEPS.length-1));
  }
  function goStep(i){
    if(!STEPS.length) return;
    i=Math.max(0,Math.min(STEPS.length-1,i));
    var s=STEPS[i];
    vidsOf(s.role).forEach(function(v){
      try{ v.currentTime=Math.max(0,Math.min((v.duration||0)-1e-6,s.t));
           if(typeof syncTargetFromTime==='function') syncTargetFromTime(v); }catch(e){}
    });
    var lab=document.getElementById('ts-pan-lab');
    if(lab) lab.textContent=(s.role==='abl'?'ABLATION':'MONITORING')+' frame '+(s.idx+1)+'/'+s.n
                          +'   ('+(i+1)+' of '+STEPS.length+' across both clips)';
    var sl=document.getElementById('ts-pan'); if(sl) sl.value=String(i);
    setTimeout(function(){ try{ redrawAllPanels(); }catch(e){} }, 40);
  }
  document.addEventListener('input', function(e){ if(e.target && e.target.id==='ts-pan') goStep(+e.target.value); });
  document.addEventListener('click', function(e){
    var sl=document.getElementById('ts-pan'); if(!sl||!e.target) return;
    if(e.target.id==='ts-pan-prev') goStep(+sl.value-1);
    if(e.target.id==='ts-pan-next') goStep(+sl.value+1);
  });

  /* ── counters ───────────────────────────────────────────────────────────────────────────────────── */
  function paintCounts(){
    var host=document.getElementById('batch-meta-host'); if(!host) return;
    var el=document.getElementById('ts-counts');
    if(!el){ el=document.createElement('span'); el.id='ts-counts'; host.appendChild(el); }
    var c={abl:0,mon:0,zoom:0,cut_abl:0,cut_mon:0,centre:0,box:0};
    anns().forEach(function(x){
      if(x.type==='timestrip_frame' && c.hasOwnProperty(x.label)) c[x.label]++;
      else if(x.type==='crop_box') c.box++;
    });
    el.textContent='timestrip frames — ABLATION '+c.abl+' · MONITORING '+c.mon+' · zoom '+c.zoom
                 +'   |   cut: abl '+c.cut_abl+', mon '+c.cut_mon
                 +'   |   centring '+c.centre+' · crop boxes '+c.box;
  }

  /* ── hook the page's own render cycle; never replace it ─────────────────────────────────────────── */
  var _rp = window.redrawPanel;
  if(typeof _rp === 'function'){
    window.redrawPanel = function(panel){ var r=_rp.apply(this,arguments); drawCentres(panel); return r; };
  }
  ['renderList','showBatch'].forEach(function(fn){
    var orig=window[fn];
    if(typeof orig==='function'){
      window[fn]=function(){ var r=orig.apply(this,arguments);
        try{ paintCounts(); if(fn==='showBatch'){ fixCols(); setTimeout(function(){fixCols();buildSteps();},300); } }catch(e){}
        return r; };
    }
  });
  document.addEventListener('loadedmetadata', buildSteps, true);
  fixCols();
  setTimeout(function(){ fixCols(); buildSteps(); paintCounts(); }, 700);
  setTimeout(function(){ buildSteps(); paintCounts(); }, 2200);
})();
</script>
""".replace("__ZOOM_PX__", str(ZOOM_PX)).replace("__UM_PER_PX__", repr(UM_PER_PX)) + END + "\n"


def build(path):
    html = open(path, encoding="utf-8", errors="replace").read()
    if MARK in html:
        html = re.sub(re.escape(MARK) + r"[\s\S]*?" + re.escape(END), "", html)
    # NO .zoomwrap position override: it is already position:absolute; inset:0, and forcing relative
    # un-pins it and crops the movies (that bug has already been shipped once).
    html = html.replace("</body>", BLOCK + "</body>", 1)
    tmp = path + ".tmp"
    open(tmp, "w", encoding="utf-8").write(html)
    os.replace(tmp, path)
    print(f"   {os.path.basename(path)}: extras rebuilt on the page's own drawing (no private overlay)")


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722/timestrip_setup_ALL.html"]):
        if os.path.isfile(t): build(t)
        else: print(f"   MISSING: {t}")
