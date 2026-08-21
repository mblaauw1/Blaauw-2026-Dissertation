#!/usr/bin/env python3
"""Timestrip setup = THE REAL kinetochore-outline slide, with its button panel swapped out.

USER 2026-08-09, twice: "still the slide format is not correct. look at the kinetochore outline slide
format if you need more help."

WHY THIS REPLACES make_timestrip_setup_20260809.py. Four earlier builds RE-IMPLEMENTED the slide — from
memory, then from the per-batch `index.html`, then from a multi-batch stylesheet, then element by element.
Every one was still wrong, and that approach cannot converge: the real slide is ~150 KB of markup, CSS and
video/scrubber logic, so any hand-copy is a guess about which parts matter.

This builds nothing. It RUNS `make_annotation_html.py --multi-batch` — the same call the kt-outline index
builders make — and post-processes the file it produces:
    1. replaces the contents of `#tool-buttons-flow` with the timestrip buttons,
    2. injects a transparent overlay <canvas class="ts-ov"> into every `.zoomwrap`, ABOVE the page's own
       canvas, so the annotation code's redraws cannot erase these boxes and this cannot corrupt its marks,
    3. appends ONE IIFE with all timestrip logic, every name prefixed so nothing collides with the page's
       own `panels` / `videos` / `scrubber`,
    4. adds a small CSS override putting `#controls` down the RIGHT instead of across the bottom — the one
       deviation she asked for.
Panel layout, #top-strip, .batch-meta, the scrubber, per-video fps and frame mapping are the real slide's,
untouched, so the format is identical BY CONSTRUCTION rather than by imitation.

THE MODEL
  CROP BOX  shape+size only, ONE per batch, identical on every frame; drag an edge/corner to resize.
  CENTRE    per frame; the box draws centred on it. A frame with no centre inherits the nearest PREVIOUS
            frame of the SAME movie that has one (dashed = inherited, solid = its own).
  GHOSTS    other frames' centres, faint and numbered, to line new points up against.
  ZOOM BOX  standard 8.7 um window (ts_render.STD_ZOOM_HALF_UM = 4.34 um half — fixed PHYSICAL size, so
            every ablation close-up renders at the same magnification). Per frame, NOT propagated; listed,
            and clicking a list entry drops a copy on the frame you are on.
  MOVIE     per role: frames cut from the processed movie, plus a start/stop range.

STORAGE — existing types, existing stores (convention in timestrip_spec.py):
  `timestrip_frame`                      one per frame in the strip; x,y = that frame's centre point
  `timestrip_frame` label=movie_exclude  cut from the processed movie
  `crop_box` crop_name=timestrip         the window shape+size (one per batch)
  `crop_box` crop_name=timestrip_zoom    per-frame ablation close-up
  `batch_meta` movie_{start,stop}_{abl,mon}

SAFETY. `_autosave_replace_batch` REPLACES every mark type for a batch with whatever the page posts, so
timestrip rows are MERGED INTO the page's own `annotations` array and saved by ITS save button — never
posted separately. A partial save would delete that cell's outlines/kt_points/poles (4 kt_outline traces
were lost from `20260304 Mad1_ablation_8` exactly that way).
"""
import argparse, html, json, os, re, subprocess, sys

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

PKG_ROOTS = ["/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723",
             "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725",
             "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"]
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")

BUTTONS = """
<!-- USER 2026-08-10: "when I make an annotation using one of the annotation buttons, the info for that
     annotation shows up underneath the button, and the button has a count". That is the page's own
     mechanism: a `.count[data-count=KEY]` inside the button and a `.btn-marks[data-marks-for=KEY]`
     under it, both filled by updateCounts(). It keys kt_point as `kt:<label>` and everything else by
     TYPE alone -- which would have lumped every timestrip mark into one list -- so updateCounts is
     patched below to key timestrip_frame as `ts:<label>` and crop_box as `box:<crop_name>`. -->
<div class="ts-tool"><button class="btn" data-tool="ts:abl"><span>&#9673; ABLATION frame</span><span class="count" data-count="ts:abl">0</span></button><div class="btn-marks" data-marks-for="ts:abl"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:mon"><span>&#9673; MONITORING frame</span><span class="count" data-count="ts:mon">0</span></button><div class="btn-marks" data-marks-for="ts:mon"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:zoom"><span>&#9673; ZOOM-row frame</span><span class="count" data-count="ts:zoom">0</span></button><div class="btn-marks" data-marks-for="ts:zoom"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:centre"><span>&#10011; centring point</span><span class="count" data-count="ts:centre">0</span></button><div class="btn-marks" data-marks-for="ts:centre"></div></div>
<div class="ts-tool"><button class="btn" data-tool="tsbox:timestrip"><span>&#9646; crop box — MAIN</span><span class="count" data-count="box:timestrip">0</span></button><div class="btn-marks" data-marks-for="box:timestrip"></div></div>
<div class="ts-tool"><button class="btn" data-tool="tsbox:timestrip_zoom"><span>&#9646; crop box — ZOOM (8.7&micro;m)</span><span class="count" data-count="box:timestrip_zoom">0</span></button><div class="btn-marks" data-marks-for="box:timestrip_zoom"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:cut_abl"><span>&#8856; cut ABLATION frame</span><span class="count" data-count="ts:cut_abl">0</span></button><div class="btn-marks" data-marks-for="ts:cut_abl"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:cut_mon"><span>&#8856; cut MONITORING frame</span><span class="count" data-count="ts:cut_mon">0</span></button><div class="btn-marks" data-marks-for="ts:cut_mon"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:start_abl"><span>&#10214; ABLATION starts</span><span class="count" data-count="ts:start_abl">0</span></button><div class="btn-marks" data-marks-for="ts:start_abl"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:stop_abl"><span>&#10215; ABLATION ends</span><span class="count" data-count="ts:stop_abl">0</span></button><div class="btn-marks" data-marks-for="ts:stop_abl"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:start_mon"><span>&#10214; MONITORING starts</span><span class="count" data-count="ts:start_mon">0</span></button><div class="btn-marks" data-marks-for="ts:start_mon"></div></div>
<div class="ts-tool"><button class="btn" data-tool="ts:stop_mon"><span>&#10215; MONITORING ends</span><span class="count" data-count="ts:stop_mon">0</span></button><div class="btn-marks" data-marks-for="ts:stop_mon"></div></div>
"""

DISPATCH_SRC = "    if (t.startsWith('kt:')) currentTool = { type:'kt_point', label: t.slice(3) };"
DISPATCH_NEW = ("    if (t.startsWith('ts:')) currentTool = { type:'timestrip_frame', label: t.slice(3) };\n"
                "    else if (t.startsWith('tsbox:')) currentTool = { type:'crop_box', label: t.slice(6), crop_name: t.slice(6) };\n"
                "    else if (t.startsWith('kt:')) currentTool = { type:'kt_point', label: t.slice(3) };")

# give timestrip marks their own count/list key, exactly as kt_point has
COUNTKEY_SRC = "    let key = a.type === 'kt_point' ? `kt:${a.label}` : a.type;"
COUNTKEY_NEW = ("    let key = a.type === 'kt_point' ? `kt:${a.label}`\n"
                "            : a.type === 'timestrip_frame' ? `ts:${a.label}`\n"
                "            : a.type === 'crop_box' ? `box:${a.crop_name||a.label||''}` : a.type;")
FILTKEY_SRC = "      let k = a.type === 'kt_point' ? `kt:${a.label}` : a.type;"
FILTKEY_NEW = ("      let k = a.type === 'kt_point' ? `kt:${a.label}`\n"
               "            : a.type === 'timestrip_frame' ? `ts:${a.label}`\n"
               "            : a.type === 'crop_box' ? `box:${a.crop_name||a.label||''}` : a.type;")

# A `ts:` mark is a SINGLE CLICK, exactly like a kt_point — it records "this frame". Without this the page
# treats it as the start of a polygon and waits for more vertices, so a click appears to do nothing at all.
# This lived only in fix_timestrip_buttons_20260810.py for a while, which meant every regeneration silently
# dropped it and all eight frame/start/stop buttons went dead again. It belongs here.
ISPOINT_SRC = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole');"""
ISPOINT_NEW = """const isPoint = (tool.type === 'kt_point'
                    || tool.type === 'polar_track'
                    || tool.type === 'pole'
                    || tool.type === 'timestrip_frame');"""


def patch_dispatcher(html):
    n = 0
    if DISPATCH_SRC in html: html = html.replace(DISPATCH_SRC, DISPATCH_NEW, 1); n += 1
    if COUNTKEY_SRC in html: html = html.replace(COUNTKEY_SRC, COUNTKEY_NEW, 1); n += 1
    if FILTKEY_SRC in html:  html = html.replace(FILTKEY_SRC,  FILTKEY_NEW, 1);  n += 1
    if ISPOINT_NEW in html:  n += 1                      # already a point tool
    elif ISPOINT_SRC in html: html = html.replace(ISPOINT_SRC, ISPOINT_NEW, 1); n += 1
    print(f"   dispatcher/count-key patches applied: {n}/4")
    if n < 4: print("   WARNING: not all anchors matched — buttons may not fire, list or count")
    return html

CSS = """
.ts-tool{break-inside:avoid;margin-bottom:6px}
.ts-tool .btn{width:100%}

/* timestrip setup: the ONE deviation from the kt-outline slide — controls down the RIGHT, not the bottom */
body { grid-template-columns: minmax(0,1fr) 430px !important; grid-template-rows: minmax(0,1fr) !important; }
#controls { border-top:0 !important; border-left:1px solid var(--border) !important;
  flex-direction:column !important; flex-wrap:nowrap !important; align-items:stretch !important;
  max-height:100vh; overflow-y:auto; }
#controls > div { flex:0 0 auto !important; min-width:0 !important; width:100%; }
#ts-tool-buttons { display:block !important; }
#ts-buttons-flow { column-width:auto !important; columns:1 !important; }
#ts-buttons-flow .btn { width:100%; text-align:left; }
#ts-orig-controls { display:none !important; }   /* kept in the DOM only so the slide's own JS still resolves */
/* NO .zoomwrap OVERRIDE. The slide styles it `position:absolute; inset:0; transform-origin:0 0` for its
   own zoom/pan; forcing `position:relative` dropped the inset sizing and cropped every movie. The overlay
   needs no positioning of its own either — the slide's `.panel canvas { position:absolute; inset:0;
   width:100%; height:100% }` already applies to it. Only stacking and cursor are ours. */
canvas.ts-ov { z-index:5; cursor:crosshair; }
"""

SCRIPT = r"""
<script>
/* ===== TIMESTRIP SETUP — on top of the real kt-outline multi-batch slide =====================
   Rewritten in one piece 2026-08-10: successive patches had silently stopped applying (the multi-batch
   conversion never landed because an earlier edit had moved its anchor), which left NF as an OBJECT while
   the scrubber called it as a FUNCTION -> total frames 0 -> the pan bar did nothing, and the INFO map was
   never injected -> the appearances panel stayed empty.
   Everything is scoped in one IIFE with prefixed names so nothing collides with the slide's own code. */
(function(){
const ZOOM_PX=__ZOOM_PX__, NFMAP=__NFRAMES__, INFO=__INFO__;
const ST={};                       /* per-batch state: the slide holds every batch at once */
function stateFor(b){ if(!ST[b]) ST[b]={sel:new Set(),centres:{},box:null,zooms:[],zsel:null,
  excl:new Set(),range:{abl:{start:null,stop:null},mon:{start:null,stop:null}}}; return ST[b]; }
let CUR='', P=[], drag=null, drawMode=false, band=null, gi=0;
let sel,centres,box,zooms,zsel,excl,range;
function bind(b){const s=stateFor(b);sel=s.sel;centres=s.centres;box=s.box;zooms=s.zooms;zsel=s.zsel;
  excl=s.excl;range=s.range;}
function stash(){ if(!CUR) return; const s=stateFor(CUR);
  s.sel=sel;s.centres=centres;s.box=box;s.zooms=zooms;s.zsel=zsel;s.excl=excl;s.range=range;}
/* BATCH_METAS and annByBatch are top-level `const`s in the slide's own classic script. Those live in the
   GLOBAL LEXICAL scope and are NOT window properties, so `window.BATCH_METAS` is undefined — which is why
   the info panel stayed blank and save/restore silently did nothing. Reference them by bare name (guarded),
   with the visible #batch-title as a DOM fallback. */
function metas(){ try{ return (typeof BATCH_METAS!=='undefined'&&BATCH_METAS)||[]; }catch(e){ return []; } }
function annMap(){ try{ return (typeof annByBatch!=='undefined'&&annByBatch)||null; }catch(e){ return null; } }
function curBatch(){
  const m=metas(), secs=[...document.querySelectorAll('.batch-section')];
  let i=secs.findIndex(function(x){return x.style.display!=='none';});
  if(i<0) i=0;
  if(m[i]&&m[i].name) return m[i].name;
  const t=document.getElementById('batch-title');
  const s=t?(t.textContent||'').trim():'';
  return (s&&s!=='—')?s:'';
}
function NF(r){const m=NFMAP[CUR]||{};return m[r]||0;}
const K=function(r,f){return r+':'+f;};
function collectPanels(){
  const secs=[...document.querySelectorAll('.batch-section')];
  const sec=secs.find(function(x){return x.style.display!=='none';})||secs[0]||document;
  /* LAZY LOAD. The slide assigns `v.src = v.dataset.src` from its OWN control handlers — and takeOver()
     clones the scrubber/step buttons, which drops those listeners. Any panel whose src had not yet been
     assigned then never loaded and rendered BLACK. Assign it here so the video loads regardless of who
     owns the controls. Same for the MIP <img data-src>. */
  sec.querySelectorAll('video[data-src]').forEach(function(v){
    if(!v.getAttribute('src') && v.dataset.src){ v.src=v.dataset.src; try{v.load();}catch(e){} }
  });
  sec.querySelectorAll('img[data-src]').forEach(function(im){
    if(!im.getAttribute('src') && im.dataset.src) im.src=im.dataset.src;
  });
  P=[...sec.querySelectorAll('.panel')].map(function(el){
    const w=el.querySelector('.zoomwrap'), v=el.querySelector('video');
    let ov=w&&w.querySelector('canvas.ts-ov');
    const p={el:el,role:(el.dataset.phase==='abl'?'abl':'mon'),v:v,ov:ov};
    if(w&&!ov){ ov=document.createElement('canvas'); ov.className='ts-ov'; w.appendChild(ov);
      p.ov=ov; wire(p); }
    return p;
  }).filter(function(p){return p.v&&p.ov;});
}
const fpsOf=function(p){const t=NF(p.role);return (p.v.duration&&t)?t/p.v.duration:6;};
const frameOf=function(p){return Math.max(0,Math.min(NF(p.role)-1,Math.round(p.v.currentTime*fpsOf(p))));};
function centreFor(role,f){
  if(centres[K(role,f)]) return centres[K(role,f)];
  const prev=Object.keys(centres).map(function(k){return k.split(':');})
    .filter(function(a){return a[0]===role&&+a[1]<f;}).map(function(a){return +a[1];})
    .sort(function(a,b){return b-a;})[0];
  return prev!==undefined?centres[K(role,prev)]:null;
}
/* ---- SEQUENTIAL PAN BAR: all ablation frames, then all monitoring frames ---------------------- */
function TOT(){return NF('abl')+NF('mon');}
/* SEEK EVERY PANEL OF THE ROLE, not just the first. Each role has TWO panels — phase/BF and 488/fluor —
   and `P.find` returned only the phase one, so the fluor movie sat on frame 0 while the pan bar moved
   phase. That is why "it doesnt go through 488 on most of the movies". */
function seekRole(role,f){
  P.filter(function(p){return p.role===role;}).forEach(function(p){
    const fp=fpsOf(p), t=Math.max(0,Math.min((p.v.duration||0)-1e-6,f/fp));
    if(Math.abs(p.v.currentTime-t)>0.02) p.v.currentTime=t;
  });
}
function gotoIndex(i){
  const NA=NF('abl'), T=TOT(); if(!T) return;
  gi=Math.max(0,Math.min(T-1,Math.round(i)));
  if(gi<NA){ seekRole('abl',gi); seekRole('mon',0); }
  else { seekRole('abl',Math.max(0,NA-1)); seekRole('mon',gi-NA); }
  const sc=document.getElementById('scrubber'); if(sc){sc.max=T-1; sc.value=gi;}
  const fl=document.getElementById('frame-label');
  if(fl) fl.textContent = gi<NA ? ('ablation '+gi+'/'+Math.max(0,NA-1))
                                : ('monitoring '+(gi-NA)+'/'+Math.max(0,NF('mon')-1));
  setTimeout(paint,40);
}
function takeOver(){
  const sc=document.getElementById('scrubber');
  if(sc && !sc.dataset.tsOwned){
    const c=sc.cloneNode(false); c.id='scrubber'; c.type='range'; c.min=0; c.step=1; c.value=0;
    c.max=Math.max(0,TOT()-1); c.dataset.tsOwned='1';
    sc.parentNode.replaceChild(c,sc);
    c.addEventListener('input',function(e){gotoIndex(+e.target.value);});
  }
  [['step-back',-1],['step-fwd',1]].forEach(function(a){
    const b=document.getElementById(a[0]); if(!b||b.dataset.tsOwned) return;
    const nb=b.cloneNode(true); nb.dataset.tsOwned='1'; b.parentNode.replaceChild(nb,b);
    nb.addEventListener('click',function(){gotoIndex(gi+a[1]);});
  });
  const pp=document.getElementById('play-pause');
  if(pp && !pp.dataset.tsOwned){
    const np=pp.cloneNode(true); np.dataset.tsOwned='1'; pp.parentNode.replaceChild(np,pp);
    let t=null;
    np.addEventListener('click',function(){
      if(t){clearInterval(t);t=null;np.textContent='▶';return;}
      np.textContent='❚❚';
      t=setInterval(function(){ if(gi>=TOT()-1){clearInterval(t);t=null;np.textContent='▶';return;}
        gotoIndex(gi+1);},120);
    });
  }
}
window.addEventListener('keydown',function(e){
  if(e.key==='ArrowRight'){e.preventDefault();e.stopPropagation();gotoIndex(gi+1);}
  if(e.key==='ArrowLeft'){e.preventDefault();e.stopPropagation();gotoIndex(gi-1);}
},true);
/* ---- drawing ---------------------------------------------------------------------------------- */
function paint(){
  P.forEach(function(p){
    if(!p.v.videoWidth) return;
    p.ov.width=p.v.videoWidth; p.ov.height=p.v.videoHeight;
    const c=p.ov.getContext('2d'), W=p.ov.width, f=frameOf(p);
    const lw=Math.max(2,W/500), r=Math.max(4,W/170);
    c.clearRect(0,0,p.ov.width,p.ov.height); c.font=Math.max(11,W/70)+'px sans-serif';
    if(excl.has(K(p.role,f))){ c.save(); c.globalAlpha=.18; c.fillStyle='#ff3b5c';
      c.fillRect(0,0,p.ov.width,p.ov.height); c.restore(); c.strokeStyle='#ff3b5c'; c.lineWidth=lw*2;
      c.beginPath(); c.moveTo(0,0); c.lineTo(p.ov.width,p.ov.height); c.stroke(); }
    const rg=range[p.role];
    if((rg.start!==null&&f<rg.start)||(rg.stop!==null&&f>rg.stop)){
      c.save(); c.globalAlpha=.32; c.fillStyle='#000'; c.fillRect(0,0,p.ov.width,p.ov.height); c.restore(); }
    for(const k in centres){ const a=k.split(':'); if(a[0]!==p.role||+a[1]===f) continue; const q=centres[k];
      c.strokeStyle='rgba(95,168,255,.30)'; c.lineWidth=lw*.7; c.beginPath();
      c.moveTo(q[0]-r,q[1]); c.lineTo(q[0]+r,q[1]); c.moveTo(q[0],q[1]-r); c.lineTo(q[0],q[1]+r); c.stroke();
      c.fillStyle='rgba(95,168,255,.45)'; c.fillText(a[1],q[0]+r+2,q[1]-2); }
    const ctr=centreFor(p.role,f);
    if(ctr&&box){ const own=!!centres[K(p.role,f)];
      c.strokeStyle='#fff'; c.lineWidth=lw; c.setLineDash(own?[]:[9,7]);
      c.strokeRect(ctr[0]-box.w/2,ctr[1]-box.h/2,box.w,box.h); c.setLineDash([]);
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(function(d){c.fillStyle='#5fa8ff';c.beginPath();
        c.arc(ctr[0]+d[0]*box.w/2,ctr[1]+d[1]*box.h/2,r,0,7);c.fill();});
      c.strokeStyle=own?'#3ddc84':'#5fa8ff'; c.beginPath();
      c.moveTo(ctr[0]-r*1.6,ctr[1]); c.lineTo(ctr[0]+r*1.6,ctr[1]);
      c.moveTo(ctr[0],ctr[1]-r*1.6); c.lineTo(ctr[0],ctr[1]+r*1.6); c.stroke(); }
    if(band&&band.role===p.role){ c.strokeStyle='#3ddc84'; c.lineWidth=lw*1.4; c.setLineDash([6,5]);
      c.strokeRect(Math.min(band.x0,band.x1),Math.min(band.y0,band.y1),
        Math.abs(band.x1-band.x0),Math.abs(band.y1-band.y0)); c.setLineDash([]); }
    zooms.forEach(function(z,i){ if(z.role!==p.role||z.frame!==f) return;
      c.strokeStyle=(i===zsel)?'#ffd54a':'#ff8c1a'; c.lineWidth=lw*(i===zsel?1.5:1);
      c.strokeRect(z.x,z.y,z.w,z.h); c.fillStyle=c.strokeStyle; c.fillText('Z'+(i+1),z.x+3,z.y-3);
      [[0,0],[1,0],[0,1],[1,1]].forEach(function(d){c.beginPath();
        c.arc(z.x+d[0]*z.w,z.y+d[1]*z.h,r*.8,0,7);c.fill();}); });
  });
  status(); renderInfo();     /* refresh with every repaint — batch-change polling alone was flaky */
}
function status(){
  const g=function(id){return document.getElementById(id);};
  const nA=[...sel].filter(function(k){return k[0]==='a';}).length;
  const nM=[...sel].filter(function(k){return k[0]==='m';}).length;
  if(g('ts-m-frames')) g('ts-m-frames').innerHTML='<b>ablation '+nA+'</b>/'+NF('abl')+
    ' &nbsp;·&nbsp; <b>monitoring '+nM+'</b>/'+NF('mon');
  if(g('ts-m-centres')) g('ts-m-centres').textContent=Object.keys(centres).length+' centre points';
  if(g('ts-m-cut')) g('ts-m-cut').textContent=
    [...excl].filter(function(k){return k[0]==='a';}).length+' ablation · '+
    [...excl].filter(function(k){return k[0]==='m';}).length+' monitoring cut';
  ['abl','mon'].forEach(function(rl){const r=range[rl],e=g('ts-m-'+rl); if(!e)return;
    e.textContent=(r.start===null&&r.stop===null)?rl+' range: whole clip'
      :rl+' range: '+(r.start===null?0:r.start)+' – '+(r.stop===null?NF(rl)-1:r.stop);});
  const el=g('ts-boxlist'); if(!el) return; let h='';
  h+= box?'<div style="padding:4px;border:1px solid #333;border-radius:3px;margin:2px 0;background:#1f1f1f">'
      +'<b>crop box</b> '+Math.round(box.w)+'×'+Math.round(box.h)+'px · every frame'
      +'<span data-del="box" style="float:right;cursor:pointer;color:#ff6b6b;font-weight:700">✕</span></div>'
     :'<div style="opacity:.6">no crop box</div>';
  zooms.forEach(function(z,i){h+='<div data-i="'+i+'" style="padding:4px;border:1px solid #333;'
    +'border-radius:3px;margin:2px 0;cursor:pointer;background:'+(i===zsel?'#3a3a2a':'transparent')+'">'
    +'<b>Z'+(i+1)+'</b> '+z.role+' frame '+z.frame+' · '+Math.round(z.w)+'×'+Math.round(z.h)
    +'<span data-del="'+i+'" style="float:right;cursor:pointer;color:#ff6b6b;font-weight:700">✕</span></div>';});
  el.innerHTML=h;
  el.querySelectorAll('[data-del]').forEach(function(x){x.onclick=function(e){e.stopPropagation();
    if(x.dataset.del==='box') box=null;
    else{const i=+x.dataset.del;zooms.splice(i,1);if(zsel===i)zsel=null;else if(zsel>i)zsel--;}
    paint();};});
  el.querySelectorAll('[data-i]').forEach(function(d){d.onclick=function(){
    const i=+d.dataset.i,z=zooms[i],p=P.find(function(q){return q.role===z.role;}); if(!p)return;
    const f=frameOf(p); if(z.frame===f){zsel=i;paint();return;}
    zooms.push(Object.assign({},z,{frame:f})); zsel=zooms.length-1; paint();};});
}
function renderInfo(){
  const el=document.getElementById('ts-info'); if(!el) return;
  const d=INFO[CUR]||{apps:[],frames:[]};
  let h='<div style="font-weight:600;margin-bottom:3px">timestrip appearances</div>';
  h+= (d.apps&&d.apps.length) ? d.apps.map(function(a){
        return '<div style="margin:3px 0;padding:4px 6px;border-left:3px solid var(--accent);'
             +'background:#181818"><b>'+a[1]+'</b> <span style="opacity:.7">— '+a[0]+'</span><br>'
             +'<span style="opacity:.6;font-size:11px">'+a[2]+'</span></div>';}).join('')
      : '<div style="opacity:.7">not used in any timestrip on the four decks</div>';
  h+='<div style="font-weight:600;margin:8px 0 3px">frames currently used</div>';
  h+= (d.frames&&d.frames.length) ? d.frames.map(function(x){
        return '<div style="font-size:11px;opacity:.85;margin:2px 0">• '+x+'</div>';}).join('')
      : '<div style="font-size:11px;opacity:.6">no explicit frame spec — builder default rule</div>';
  el.innerHTML=h;
}
/* ---- pointer interaction ----------------------------------------------------------------------- */
function toImg(p,e){const r=p.ov.getBoundingClientRect();
  return [(e.clientX-r.left)/r.width*p.ov.width,(e.clientY-r.top)/r.height*p.ov.height];}
function hitZ(p,x,y){const f=frameOf(p),m=Math.max(9,p.ov.width/95);
  for(let i=zooms.length-1;i>=0;i--){const z=zooms[i]; if(z.role!==p.role||z.frame!==f) continue;
    const L=Math.abs(x-z.x)<m,R=Math.abs(x-(z.x+z.w))<m,T=Math.abs(y-z.y)<m,B=Math.abs(y-(z.y+z.h))<m;
    if(L&&T)return[i,'nw'];if(R&&T)return[i,'ne'];if(L&&B)return[i,'sw'];if(R&&B)return[i,'se'];
    if(L)return[i,'w'];if(R)return[i,'e'];if(T)return[i,'n'];if(B)return[i,'s'];
    if(x>z.x&&x<z.x+z.w&&y>z.y&&y<z.y+z.h)return[i,'move'];} return null;}
function hitB(p,x,y){const ctr=centreFor(p.role,frameOf(p)); if(!ctr||!box) return null;
  const m=Math.max(10,p.ov.width/90);
  const L=Math.abs(x-(ctr[0]-box.w/2))<m,R=Math.abs(x-(ctr[0]+box.w/2))<m;
  const T=Math.abs(y-(ctr[1]-box.h/2))<m,B=Math.abs(y-(ctr[1]+box.h/2))<m;
  if(L&&T)return'nw';if(R&&T)return'ne';if(L&&B)return'sw';if(R&&B)return'se';
  if(L)return'w';if(R)return'e';if(T)return'n';if(B)return's'; return null;}
function wire(p){
  p.ov.addEventListener('pointermove',function(e){const a=toImg(p,e),x=a[0],y=a[1];
    if(band){band.x1=x;band.y1=y;paint();return;}
    if(!drag){const z=hitZ(p,x,y),b=z?null:hitB(p,x,y);
      p.ov.style.cursor=z?(z[1]==='move'?'move':z[1]+'-resize'):b?b+'-resize':'crosshair';return;}
    const dx=x-drag.x,dy=y-drag.y,o=drag.o;
    if(drag.kind==='z'){const z=zooms[drag.i];
      if(drag.mode==='move'){z.x=o.x+dx;z.y=o.y+dy;}
      else{if(drag.mode.indexOf('w')>=0){z.x=o.x+dx;z.w=Math.max(12,o.w-dx);}
           if(drag.mode.indexOf('e')>=0)z.w=Math.max(12,o.w+dx);
           if(drag.mode.indexOf('n')>=0){z.y=o.y+dy;z.h=Math.max(12,o.h-dy);}
           if(drag.mode.indexOf('s')>=0)z.h=Math.max(12,o.h+dy);}}
    else{if(drag.mode.indexOf('e')>=0)box.w=Math.max(20,o.w+dx*2);
         if(drag.mode.indexOf('w')>=0)box.w=Math.max(20,o.w-dx*2);
         if(drag.mode.indexOf('s')>=0)box.h=Math.max(20,o.h+dy*2);
         if(drag.mode.indexOf('n')>=0)box.h=Math.max(20,o.h-dy*2);}
    paint();});
  p.ov.addEventListener('pointerdown',function(e){const a=toImg(p,e),x=a[0],y=a[1],f=frameOf(p);
    if(drawMode){band={role:p.role,frame:f,x0:x,y0:y,x1:x,y1:y};
      p.ov.setPointerCapture(e.pointerId);paint();return;}
    const z=hitZ(p,x,y);
    if(z){zsel=z[0];drag={kind:'z',i:z[0],mode:z[1],x:x,y:y,o:Object.assign({},zooms[z[0]])};
      p.ov.setPointerCapture(e.pointerId);paint();return;}
    const b=hitB(p,x,y);
    if(b){drag={kind:'b',mode:b,x:x,y:y,o:Object.assign({},box)};p.ov.setPointerCapture(e.pointerId);return;}
    centres[K(p.role,f)]=[x,y]; sel.add(K(p.role,f)); paint();});
  p.ov.addEventListener('pointerup',function(e){
    if(band){const w=Math.abs(band.x1-band.x0),h=Math.abs(band.y1-band.y0);
      if(w>8&&h>8){box={w:w,h:h};
        centres[K(band.role,band.frame)]=[(band.x0+band.x1)/2,(band.y0+band.y1)/2];
        sel.add(K(band.role,band.frame));}
      band=null;drawMode=false;
      const db=document.getElementById('ts-draw'); if(db) db.classList.remove('active');
      try{p.ov.releasePointerCapture(e.pointerId);}catch(_){}
      paint();return;}
    drag=null;try{p.ov.releasePointerCapture(e.pointerId);}catch(_){}});
  p.v.addEventListener('seeked',paint);
  p.v.addEventListener('loadedmetadata',function(){
    if(!box) box={w:Math.round(p.v.videoWidth*.3),h:Math.round(p.v.videoWidth*.3)};
    const sc=document.getElementById('scrubber'); if(sc) sc.max=Math.max(0,TOT()-1);
    paint();});
}
/* ---- buttons ------------------------------------------------------------------------------------ */
const g=function(id){return document.getElementById(id);};
function on(id,fn){const b=g(id); if(b) b.onclick=fn;}
function incRole(r){const p=P.find(function(q){return q.role===r;}); if(!p)return;
  const k=K(r,frameOf(p)); if(sel.has(k))sel.delete(k); else sel.add(k); paint();}
on('ts-inc-abl',function(){incRole('abl');}); on('ts-inc-mon',function(){incRole('mon');});
function cutRole(r){const p=P.find(function(q){return q.role===r;}); if(!p)return;
  const k=K(r,frameOf(p)); if(excl.has(k))excl.delete(k); else excl.add(k); paint();}
on('ts-cut-abl',function(){cutRole('abl');}); on('ts-cut-mon',function(){cutRole('mon');});
function edge(r,w){const p=P.find(function(q){return q.role===r;}); if(!p)return;
  range[r][w]=frameOf(p); paint();}
on('ts-start-abl',function(){edge('abl','start');}); on('ts-stop-abl',function(){edge('abl','stop');});
on('ts-start-mon',function(){edge('mon','start');}); on('ts-stop-mon',function(){edge('mon','stop');});
on('ts-uncentre',function(){P.forEach(function(p){delete centres[K(p.role,frameOf(p))];});paint();});
on('ts-draw',function(){drawMode=!drawMode;band=null;
  const b=g('ts-draw'); if(b) b.classList.toggle('active',drawMode); paint();});
function annsFor(b){const m=annMap(); return (m&&m.get&&m.get(b))||[];}
function outlineFor(p){return annsFor(CUR).find(function(a){
  return a.type==='cell_outline'&&Number(a.frame)===frameOf(p)&&a.points;});}
function pts(o){return (typeof o.points==='string')?JSON.parse(o.points):o.points;}
on('ts-centre',function(){P.forEach(function(p){const o=outlineFor(p); if(!o)return; const q=pts(o);
  centres[K(p.role,frameOf(p))]=[q.reduce(function(s,d){return s+d[0];},0)/q.length,
                                 q.reduce(function(s,d){return s+d[1];},0)/q.length];
  sel.add(K(p.role,frameOf(p)));}); paint();});
on('ts-fit',function(){const p=P.find(function(q){return outlineFor(q);}); if(!p)return;
  const q=pts(outlineFor(p)),xs=q.map(function(d){return d[0];}),ys=q.map(function(d){return d[1];});
  const s2=Math.max(Math.max.apply(null,xs)-Math.min.apply(null,xs),
                    Math.max.apply(null,ys)-Math.min.apply(null,ys))*1.6;
  box={w:s2,h:s2}; paint();});
on('ts-square',function(){if(!box)return;const s2=Math.max(box.w,box.h);box={w:s2,h:s2};paint();});
on('ts-zoom',function(){const p=P.find(function(q){return q.role==='abl';})||P[0]; if(!p)return;
  const f=frameOf(p), ctr=centreFor(p.role,f)||[p.ov.width/2,p.ov.height/2];
  zooms.push({role:p.role,frame:f,x:ctr[0]-ZOOM_PX/2,y:ctr[1]-ZOOM_PX/2,w:ZOOM_PX,h:ZOOM_PX});
  zsel=zooms.length-1; paint();});
/* ---- persistence -------------------------------------------------------------------------------- */
function tsRows(){const out=[];let id=Date.now()%100000;
  sel.forEach(function(k){const a=k.split(':'),c=centres[k];
    out.push({id:++id,type:'timestrip_frame',label:'',frame:+a[1],phase:a[0],channel:'fluor',
              x:c?Math.round(c[0]):'',y:c?Math.round(c[1]):'',notes:'timestrip'});});
  excl.forEach(function(k){const a=k.split(':');
    out.push({id:++id,type:'timestrip_frame',label:'movie_exclude',frame:+a[1],phase:a[0],
              channel:'fluor',notes:'cut from the processed movie'});});
  if(box) out.push({id:++id,type:'crop_box',label:'crop',crop_name:'timestrip',frame:'',x:'',y:'',
                    w:Math.round(box.w),h:Math.round(box.h),phase:'mon',channel:'fluor',
                    notes:'timestrip window shape+size'});
  zooms.forEach(function(z){out.push({id:++id,type:'crop_box',label:'crop',crop_name:'timestrip_zoom',
    frame:z.frame,x:Math.round(z.x),y:Math.round(z.y),w:Math.round(z.w),h:Math.round(z.h),
    phase:z.role,channel:'fluor',notes:'ablation close-up zoom box'});});
  ['abl','mon'].forEach(function(r){['start','stop'].forEach(function(w){const v=range[r][w];
    if(v===null)return;
    out.push({id:++id,type:'batch_meta',label:'movie_'+w+'_'+r,frame:'',phase:r,channel:'',
              notes:String(v)});});});
  return out;}
function isMine(a){return a.type==='timestrip_frame'||
  (a.type==='crop_box'&&['timestrip','timestrip_zoom'].indexOf(a.crop_name||'')>=0)||
  (a.type==='batch_meta'&&/^movie_(start|stop)_(abl|mon)$/.test(a.label||''));}
function syncIntoPage(){
  stash();
  const m=annMap(); if(!m||!m.get) return;
  Object.keys(ST).forEach(function(b){
    const arr=m.get(b); if(!arr) return;
    for(let i=arr.length-1;i>=0;i--) if(isMine(arr[i])) arr.splice(i,1);
    const keep=[sel,centres,box,zooms,zsel,excl,range]; bind(b);
    tsRows().forEach(function(r){arr.push(r);});
    sel=keep[0];centres=keep[1];box=keep[2];zooms=keep[3];zsel=keep[4];excl=keep[5];range=keep[6];});
}
['save-csv','save'].forEach(function(id){const b=g(id); if(b) b.addEventListener('click',syncIntoPage,true);});
setInterval(syncIntoPage,4000);
function restore(){
  const arr=annsFor(CUR); if(!arr||!arr.length) return;
  arr.forEach(function(a){const rl=(a.phase==='abl')?'abl':'mon';
    if(a.type==='timestrip_frame'&&(a.label||'')==='movie_exclude') excl.add(K(rl,+a.frame));
    else if(a.type==='timestrip_frame'){sel.add(K(rl,+a.frame));
      if(a.x!==''&&a.x!=null) centres[K(rl,+a.frame)]=[+a.x,+a.y];}
    if(a.type==='crop_box'&&a.crop_name==='timestrip') box={w:+a.w,h:+a.h};
    if(a.type==='crop_box'&&a.crop_name==='timestrip_zoom')
      zooms.push({role:rl,frame:+a.frame,x:+a.x,y:+a.y,w:+a.w,h:+a.h});
    if(a.type==='batch_meta'&&/^movie_(start|stop)_(abl|mon)$/.test(a.label||'')){
      const mm=a.label.match(/^movie_(start|stop)_(abl|mon)$/); range[mm[2]][mm[1]]=+a.notes;}});
}
function onBatchChange(){
  const b=curBatch(); if(!b||b===CUR) return;
  stash(); CUR=b; bind(b); collectPanels(); renderInfo(); restore(); takeOver(); gi=0; gotoIndex(0);
}
setInterval(onBatchChange,400);
setTimeout(function(){CUR=curBatch();bind(CUR);collectPanels();renderInfo();restore();takeOver();
  gotoIndex(0);},1200);
})();

</script>
"""



DECKMAP, FRAMESPEC = {}, {}
try:
    DECKMAP = json.load(open("/Volumes/4 MB/_claude_tmp/timestrip_deck_map.json"))
except Exception:
    pass
try:
    import pickle
    FRAMESPEC = pickle.load(open("/Volumes/4 MB/_claude_tmp/timestrip_frames_per_batch.pkl", "rb"))
except Exception:
    pass



def info_json(batches):
    """The `INFO` map the slide's IIFE reads: {batch: {apps, frames}}.

    `__INFO__` was substituted by NEITHER build path, so every freshly generated slide carried the literal
    token inside the IIFE -- invalid JS, which killed the whole block: pan bar, appearances panel, zoom-row
    handling, all of it. The older shipped slides work only because they predate this template. 2026-08-11.
    """
    out = {}
    for b in batches:
        out[b] = {"apps": [list(a) for a in DECKMAP.get(b, [])],
                  "frames": list(FRAMESPEC.get(b, []))}
    return json.dumps(out)


def build_multi(batches, out):
    """ONE multi-batch slide, the way the kt-outline slides do it: every batch in a single index with
    prev/next navigation, rather than a separate file per cell."""
    specs, nfr, info = [], {}, {}
    rows, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in rows}
    for b in batches:
        cands = [os.path.join(r, b) for r in PKG_ROOTS if os.path.isdir(os.path.join(r, b))]
        pkg = next((c for c in cands if os.path.isfile(os.path.join(c, "abl_fluor.mp4"))
                    or os.path.isfile(os.path.join(c, "abl_phase.mp4"))), None) or (cands[0] if cands else None)
        if not pkg:
            print(f"   NO PACKAGE, skipped: {b}"); continue
        specs.append({"name": b, "pkg_dir": pkg})
        p = (MR.get(b, {}).get("Drive Path", "") or "").strip()
        if not (p and os.path.isdir(p)):
            p = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
        fj = os.path.join(p, f"{b}_frames.json")
        c = {"abl": 0, "mon": 0}
        if os.path.isfile(fj):
            for f in json.load(open(fj)).get("frames", []):
                if f.get("role") == "ablation": c["abl"] += 1
                elif f.get("role") == "monitoring": c["mon"] += 1
        nfr[b] = c
        info[b] = {"apps": DECKMAP.get(b, []), "frames": FRAMESPEC.get(b, [])}
    if not specs:
        print("nothing to build"); return
    root = os.path.dirname(specs[0]["pkg_dir"])
    r = subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                        "--index-out", out, "--pkg-root", root],
                       capture_output=True, text=True, timeout=3600)
    if r.returncode != 0 or not os.path.isfile(out):
        print(f"   BUILD FAILED: {(r.stderr or '')[-300:]}"); return
    s = open(out, encoding="utf-8", errors="replace").read(); before = len(s)
    # DROP DEAD PANELS. `20250402 ptk_yfpcdc20_2`'s abl_phase.mp4 is black end to end — the pipeline never
    # produced a good one (the SOURCE Phase_Ablation.mp4 is 3 KB, mean 0.0), and no other copy exists on
    # the drive. That is not a defect to fix here: the timestrip convention itself drops phase for the
    # ablation portion (`fluor_only=True` in make_strip), which is why other slide makers show this cell
    # fine. So any movie that is black on every sample gets its panel removed rather than rendered as a
    # black rectangle. Detection is per package, two samples, mean < 3/255.
    import cv2 as _cv2
    dead = []
    for sp in specs:
        for fn in ("abl_phase.mp4", "abl_fluor.mp4", "mon_phase.mp4", "mon_fluor.mp4"):
            fp = os.path.join(sp["pkg_dir"], fn)
            if not os.path.isfile(fp):
                continue
            try:
                cap = _cv2.VideoCapture(fp); n = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT)); vals = []
                for k in (0, max(0, n // 2)):
                    cap.set(_cv2.CAP_PROP_POS_FRAMES, k); ok, im = cap.read()
                    if ok: vals.append(float(im.mean()))
                cap.release()
                if vals and max(vals) < 3.0:
                    dead.append((sp["name"], fn))
            except Exception:
                pass
    for bname, fn in dead:
        role = "abl" if fn.startswith("abl") else "mon"
        ch = "phase" if "phase" in fn else "fluor"
        pat = re.compile(r'<div class="panel-wrap">(?:(?!</div>\s*</div>\s*</div>).)*?'
                         r'data-phase="' + role + r'" data-channel="' + ch + r'".*?</div>\s*</div>\s*</div>',
                         re.S)
        new_s, k = pat.subn("", s, count=1)
        if k:
            s = new_s
            print(f"   dropped dead panel: {bname} {fn} (black end to end)")
    if dead:
        s = re.sub(r'data-cols="2"', 'data-cols="1"', s) if False else s
    try:
        px = float(MR.get(specs[0]["name"], {}).get("Pixel Size (um)", "") or 0.062)
    except Exception:
        px = 0.062
    zoom_px = 2 * max(8, int(round(4.34 / px)))
    m = re.search(r'<div id="controls"[^>]*>', s)
    start = m.end(); depth, i = 1, start
    # APPEND the timestrip buttons into the page's own #tool-buttons-flow. The previous build replaced the
    # whole #controls panel and hid the original, which is what removed the per-mark list and the delete
    # affordance she relies on. Nothing is replaced or hidden now.
    FLOW = '<div id="tool-buttons-flow">'
    k = s.find(FLOW)
    if k >= 0:
        ins = k + len(FLOW)
        s = (s[:ins]
             + '\n<div style="break-inside:avoid;margin:6px 0 2px;font-weight:600;opacity:.85">Timestrip</div>\n'
             + BUTTONS + s[ins:])
        print("   timestrip buttons appended into the native tool panel")
    else:
        print("   WARNING: #tool-buttons-flow not found — buttons not added")
    s = patch_dispatcher(s)
    s = s.replace("<title>", "<title>Timestrip setup · ", 1)
    open(out, "w").write(s)
    print(f"   {out}\n      {len(specs)} batches · {before//1024}kb -> {len(s)//1024}kb")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", nargs="*", default=[])
    ap.add_argument("--multi", default=None, help="build ONE multi-batch slide at this path")
    a = ap.parse_args()
    if a.multi:
        build_multi(a.batches, a.multi); return
    if not a.batches:
        print("give --batches"); return
    rows, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in rows}
    for b in a.batches:
        cands = [os.path.join(r, b) for r in PKG_ROOTS if os.path.isdir(os.path.join(r, b))]
        pkg = next((c for c in cands if os.path.isfile(os.path.join(c, "abl_fluor.mp4"))
                    or os.path.isfile(os.path.join(c, "abl_phase.mp4"))), None) or (cands[0] if cands else None)
        if not pkg:
            print(f"   NO PACKAGE for {b}"); continue
        root = os.path.dirname(pkg)
        out = os.path.join(root, f"timestrip_setup_{b.replace(' ', '_')}.html")
        r = subprocess.run([sys.executable, "-u", TOOL, "--multi-batch",
                            json.dumps([{"name": b, "pkg_dir": pkg}]),
                            "--index-out", out, "--pkg-root", root],
                           capture_output=True, text=True, timeout=900)
        if r.returncode != 0 or not os.path.isfile(out):
            print(f"   BUILD FAILED for {b}: {(r.stderr or '')[-200:]}"); continue
        s = open(out, encoding="utf-8", errors="replace").read()
        before = len(s)
        # WHERE THIS BATCH'S TIMESTRIP LIVES, and the frames it currently uses — so she can see what the
        # published strip is showing before choosing a new set. One slide per batch; a batch used in
        # several strips gets one entry per appearance rather than a duplicate slide.
        apps = DECKMAP.get(b, [])
        fr = FRAMESPEC.get(b, [])
        rowsh = ""
        for deck, topic, stem in apps:
            rowsh += (f'<div style="margin:3px 0;padding:4px 6px;border-left:3px solid var(--accent);'
                      f'background:#181818"><b>{html.escape(topic)}</b>'
                      f' <span style="opacity:.7">— {html.escape(deck)}</span><br>'
                      f'<span style="opacity:.6;font-size:11px">{html.escape(stem)}</span></div>')
        if not apps:
            rowsh = ('<div style="opacity:.7;padding:4px 0">not currently used in any timestrip on the '
                     'four decks</div>')
        frh = "".join(f'<div style="font-size:11px;opacity:.85;margin:2px 0">• {html.escape(x)}</div>'
                      for x in fr) or ('<div style="font-size:11px;opacity:.6">no explicit frame spec — '
                                       'the builder picks frames by its default rule</div>')
        info_html = ('<div class="btn-marks" style="display:block;margin-bottom:10px">'
                     '<div style="font-weight:600;margin-bottom:3px">timestrip appearances</div>'
                     + rowsh +
                     '<div style="font-weight:600;margin:8px 0 3px">frames currently used</div>'
                     + frh + '</div>')

        p = (MR.get(b, {}).get("Drive Path", "") or "").strip()
        if not (p and os.path.isdir(p)):
            p = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
        fj = os.path.join(p, f"{b}_frames.json")
        nfr = {"abl": 0, "mon": 0}
        if os.path.isfile(fj):
            for f in json.load(open(fj)).get("frames", []):
                if f.get("role") == "ablation":
                    nfr["abl"] += 1
                elif f.get("role") == "monitoring":
                    nfr["mon"] += 1
        try:
            px = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
        except Exception:
            px = 0.062
        zoom_px = 2 * max(8, int(round(4.34 / px)))   # ts_render.STD_ZOOM_HALF_UM — fixed physical window

        # REPLACE THE WHOLE #controls BLOCK. Swapping only `#tool-buttons-flow` left every other
        # kt-outlining panel behind — "Kinetochore group", "Crop box options", "Batch flags",
        # "Saved marks" and a stray kt_outline tool button. This is the timestrip format now, so the
        # control column is entirely ours; the slide's movie area is what we are reusing.
        m = re.search(r'<div id="controls"[^>]*>', s)
        if not m:
            print(f"   !! no #controls in the generated slide for {b}"); continue
        start = m.end()
        depth, i = 1, start
        while i < len(s) and depth:
            nxt = re.search(r"<div\b|</div>", s[i:])
            if not nxt:
                break
            i += nxt.end()
            depth += 1 if nxt.group(0) != "</div>" else -1
        end = i - len("</div>")
        # KEEP the original controls in the DOM, HIDDEN. Deleting them broke the slide outright: its own
        # JS looks up 23 of those elements (kt-group, crop-name, ann-list, flag-timestrip, ...) during
        # init, hit a null, threw, and never wired the videos — so no movie appeared at all. Hiding
        # instead of removing keeps every lookup satisfied while showing only the timestrip buttons.
        orig = s[start:end]
        panel = ('<div><h3>Timestrip</h3>' + info_html +
                 '<div class="btn-group" id="ts-tool-buttons">'
                 '<div id="ts-buttons-flow">' + BUTTONS + '</div></div></div>'
                 '<div id="ts-orig-controls" hidden aria-hidden="true">' + orig + '</div>')
        s = s[:start] + panel + s[end:]
        s = s.replace("</style>", CSS + "</style>", 1)
        s = s.replace("</body>", SCRIPT.replace("__ZOOM_PX__", str(zoom_px))
                                       .replace("__NFRAMES__", json.dumps(nfr))
                                       .replace("__INFO__", info_json([b])) + "</body>", 1)
        s = s.replace("<title>", f"<title>Timestrip setup · {html.escape(b)} · ", 1)
        # The SINGLE-batch path built the buttons but never wired them: patch_dispatcher was called only in
        # build_multi, so a slide made with --batches got `ts:` buttons that fell through the dispatcher's
        # catch-all to {type:'ts:abl'}, which is in no isPoint set and starts a polygon that never closes.
        # Same dead-button symptom she reported before, reached by the other code path. 2026-08-11.
        s = patch_dispatcher(s)
        open(out, "w").write(s)
        print(f"   {out}\n      real slide {before//1024}kb -> {len(s)//1024}kb · "
              f"{nfr['abl']} abl + {nfr['mon']} mon frames · zoom {zoom_px}px")


if __name__ == "__main__":
    main()
