#!/usr/bin/env python3
"""Timestrip setup slide — built on the REAL annotation-slide shell, with timestrip-specific buttons.

USER 2026-08-09, in order:
  * "i just want to build a slide setup specifically for this to make it fast and easy"
  * "when i draw a crop box i need it to be visible from frame to frame and i need to be able to adjust it
     without having to draw a new one - so move it around on a frame or grab the side and pull to reshape"
  * "if i click a centering point in a cell i want the mark to be shown on other frames so i can reference
     it when setting other center points. and i want the crop box to be the same shape and size on each
     frame but its center should be at the center point designated on that frame. if no center point is
     designated on that frame, use the center point from the nearest previous frame with one."
  * "i want the setup of the slides to look like the annotation slides but the buttons will just be
     different, customized to this purpose"  ... then: "no, the layout is nothing like the annotation slides"

WHY THIS VERSION LOOKS RIGHT. The first attempt re-implemented a layout from memory (one big canvas + a
custom filmstrip) and only borrowed a few colours. The real slide is a `#grid-area` holding a
`#status-banner`, `#jump-bar` and `#scrubber-bar` above a `.row` of `.panel-wrap`s, each a LIVE <video>
with a <canvas> overlay inside `.zoomwrap`, beside a `#controls` column of `.btn`s. This build reads that
batch's own `index.html`, lifts its <style> block VERBATIM, and reproduces the same DOM — so it cannot
drift from the annotation slides. Only the button column differs, which is what she asked for.

THE MODEL
  CROP BOX  = shape + size only, ONE per batch, identical on every frame (drag an edge/corner to resize).
  CENTRE    = per frame. The box is drawn centred on that frame's centre point. A frame with no centre of
              its own inherits the nearest PREVIOUS frame that has one, so you only place a point when the
              cell has actually moved. Inherited windows draw DASHED, owned ones SOLID.
  GHOSTS    = every other frame's centre point, faint, labelled with its frame number, so a new point can
              be lined up against the ones already placed.
  Fixed size + moving centre is what an aligned strip needs: the cell never changes scale between columns.

STORAGE — existing types, existing stores (convention in timestrip_spec.py):
  `timestrip_frame` per included frame; its x,y (when set) IS that frame's centre point
  ONE `crop_box` named "timestrip"; its w,h are the window shape/size

SAFETY. `_autosave_replace_batch` REPLACES every mark type for a batch with whatever the page posts, so a
partial save would DELETE that cell's outlines/kt_points/poles (4 kt_outline traces were lost from
`20260304 Mad1_ablation_8` exactly that way; the empty-payload guard only catches a totally empty save).
This page loads everything first, keeps every row verbatim, edits only its own two types, and REFUSES TO
SAVE if that load failed.
"""
import argparse, html, json, os, re, sys

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

PKG_ROOTS = ["/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722",
             "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725",
             "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723"]
FPS = 10.0

BODY = r"""
<div id="grid-area">
  <div id="top-strip">
    <div id="batch-nav"><span id="batch-title">__BATCH__</span></div>
    <span id="batch-meta-host"></span>
    <div id="jump-bar"></div>
    <span id="status-banner" class="idle">Click a video to set that frame's centre point. Drag a box edge to resize.</span>
    <div id="file-actions">
      <span id="save-indicator"></span>
      <button class="action-btn" id="save-csv">Save</button>
    </div>
  </div>
  <div id="scrubber-bar">
    <button id="play-pause">▶</button>
    <button class="jump-btn" id="step-back" title="◀ frame back (← key)">◀</button>
    <input type="range" id="scrubber" min="0" max="1" step="0.001" value="0">
    <button class="jump-btn" id="step-fwd" title="frame forward ▶ (→ key)">▶</button>
    <span id="frame-label">frame —/—</span>
    <span id="time-label">--:--:--</span>
  </div>
  <div class="batch-meta">__META__</div>
<div class="batch-section">__ROWS__</div>
</div>
<div id="controls">
  <div>
    <div class="btn-group" id="tool-buttons">
      <div id="tool-buttons-flow">
        <div class="row-label" style="margin:0 0 6px">__BATCH__</div>

        <button class="btn" id="toggleAbl">◉ include / exclude this ABLATION frame</button>
        <button class="btn" id="toggleMon">◉ include / exclude this MONITORING frame</button>
        <div class="btn-marks" id="m-frames">no frames selected</div>

        <button class="btn" id="everyN">▦ include every Nth frame…</button>
        <div class="btn-marks">bulk-select, then prune by hand</div>

        <button class="btn" id="dropCentre">✛ centre from this frame's cell outline</button>
        <div class="btn-marks" id="m-centres">no centre points</div>

        <button class="btn" id="clearCentre">✕ remove this frame's centre point</button>
        <div class="btn-marks">the frame then inherits the previous centre</div>

        <button class="btn" id="fit">⤢ fit box to the cell outline here</button>
        <div class="btn-marks" id="m-box">no box yet</div>

        <button class="btn" id="square">□ make the box square</button>
        <div class="btn-marks">same size on every frame — keeps the strip aligned</div>

        <div class="row-label" style="margin:12px 0 4px">processed movie</div>
        <button class="btn" id="exAbl">⊘ exclude this ABLATION frame from the movie</button>
        <button class="btn" id="exMon">⊘ exclude this MONITORING frame from the movie</button>
        <div class="btn-marks" id="m-excl">nothing excluded</div>

        <button class="btn" id="startAbl">⟦ ABLATION movie starts here</button>
        <button class="btn" id="stopAbl">⟧ ABLATION movie ends here</button>
        <div class="btn-marks" id="m-rangeAbl">ablation range: whole clip</div>

        <button class="btn" id="startMon">⟦ MONITORING movie starts here</button>
        <button class="btn" id="stopMon">⟧ MONITORING movie ends here</button>
        <div class="btn-marks" id="m-rangeMon">monitoring range: whole clip</div>

        <div class="row-label" style="margin:12px 0 4px">timestrip</div>
        <button class="btn" id="addZoom">⊕ add ablation zoom box (standard __ZOOM_UM__ µm)</button>
        <div class="btn-marks" id="m-zoomstd">fixed physical size — same magnification on every cell</div>

        <div class="row-label" style="margin:10px 0 4px">boxes</div>
        <div class="btn-marks" id="boxlist">none yet</div>

        <button class="btn" id="save" style="background:#5fa8ff;color:#04121f;font-weight:600">Save to annotations</button>
        <div class="btn-marks" id="m-save">loading…</div>
      </div>
    </div>
  </div>
</div>
<script>
/* MOVIE SETUP COPIED FROM THE ANNOTATION SLIDES.
   One MASTER scrubber holding a fraction in [0,1]; every video seeks to frac * ITS OWN duration, so the
   short ablation clip and the long monitoring clip stay in step instead of the ablation pinning at its end.
   Every panel is live and annotatable at once — that is the part the first build got wrong (it showed one
   role at a time). Each panel knows its own fps, so "the frame" is per panel, and a centre point or zoom
   box you place lands on that panel's own (role, frame). */
const BATCH=__BATCH_JSON__, FRAMES=__FRAMES_JSON__, ZOOM_PX=__ZOOM_PX__;
let allRows=null, loaded=false, sel=new Set(), centres={}, box=null, zooms=[], zsel=null, drag=null;
/* PROCESSED-MOVIE settings, kept separate from the timestrip frame selection: a frame can be in the
   timestrip and still be cut from the movie, and vice versa. `excl` holds role:frame keys; `range` holds
   an inclusive start/stop per role (null = use the whole clip). */
let excl=new Set(), range={abl:{start:null,stop:null}, mon:{start:null,stop:null}};
const panels=[...document.querySelectorAll('.panel')].map(p=>({
  el:p, role:p.dataset.phase, ch:p.dataset.channel, v:p.querySelector('video'), c:p.querySelector('canvas')}));
const videos=panels.map(p=>p.v);
const banner=m=>document.getElementById('status-banner').textContent=m;
const sav=m=>document.getElementById('m-save').textContent=m;
const nFrames=r=>FRAMES.filter(g=>g.role===r).length;
const info=new Map();                       /* video -> {fps, total} from its own duration */

function fpsFor(v){ const i=info.get(v); return i?i.fps:6; }
function frameOf(p){ const i=info.get(p.v); if(!i) return 0;
  return Math.max(0,Math.min(i.total-1,Math.round(p.v.currentTime*i.fps))); }
const K=(role,f)=>`${role}:${f}`;

function centreFor(role,f){
  if(centres[K(role,f)]) return centres[K(role,f)];
  const prev=Object.keys(centres).map(k=>k.split(':')).filter(([r,x])=>r===role&&Number(x)<f)
              .map(([,x])=>Number(x)).sort((a,b)=>b-a)[0];
  return prev!==undefined?centres[K(role,prev)]:null;
}
function sizeCanvases(){
  panels.forEach(p=>{ if(!p.v.videoWidth) return;
    p.c.width=p.v.videoWidth; p.c.height=p.v.videoHeight;
    p.c.style.width=p.v.clientWidth+'px'; p.c.style.height=p.v.clientHeight+'px'; });
}
panels.forEach(p=>p.v.addEventListener('loadedmetadata',()=>{
  const total=nFrames(p.role)||1;
  info.set(p.v,{fps: total/(p.v.duration||1), total});
  sizeCanvases();
  if(!box) box={w:Math.round(p.v.videoWidth*0.3),h:Math.round(p.v.videoWidth*0.3)};
  setMasterTime(0);
}));
window.addEventListener('resize',()=>{sizeCanvases();paint();});

function setMasterTime(frac){
  frac=Math.max(0,Math.min(1,frac));
  videos.forEach(v=>{ const t=frac*(v.duration||0);
    if(Math.abs(v.currentTime-t)>0.03) v.currentTime=t; });
  document.getElementById('scrubber').value=frac.toFixed(4);
  label();
}
function label(){
  document.getElementById('frame-label').textContent =
    panels.map(p=>`${p.role} ${frameOf(p)}`).filter((v,i,a)=>a.indexOf(v)===i).join(' · ');
  const p0=panels.find(p=>p.role==='mon')||panels[0];
  const f=FRAMES.find(g=>g.role===p0.role&&g.frame===frameOf(p0));
  document.getElementById('time-label').textContent=f?f.hms:'--:--:--';
}
function stepFrames(n){
  panels.forEach(p=>{ const fps=fpsFor(p.v);
    p.v.currentTime=Math.max(0,Math.min((p.v.duration||0)-1e-6,p.v.currentTime+n/fps)); });
  setTimeout(()=>{label();paint();},60);
}
panels.forEach(p=>p.v.addEventListener('seeked',()=>{label();paint();}));

function paint(){
  panels.forEach(p=>{
    const c=p.c.getContext('2d'), W=p.c.width; if(!W) return;
    const f=frameOf(p), lw=Math.max(2,W/500), r=Math.max(4,W/170);
    c.clearRect(0,0,p.c.width,p.c.height);
    c.font=`${Math.max(11,W/70)}px sans-serif`;
    for(const [k,q] of Object.entries(centres)){        /* ghosts: same role, other frames */
      const [rl,fr]=k.split(':'); if(rl!==p.role||Number(fr)===f) continue;
      c.strokeStyle='rgba(95,168,255,.30)'; c.lineWidth=lw*.7;
      c.beginPath(); c.moveTo(q[0]-r,q[1]); c.lineTo(q[0]+r,q[1]);
      c.moveTo(q[0],q[1]-r); c.lineTo(q[0],q[1]+r); c.stroke();
      c.fillStyle='rgba(95,168,255,.45)'; c.fillText(fr,q[0]+r+2,q[1]-2);
    }
    if(excl.has(K(p.role,f))){                       /* cut from the processed movie */
      c.save(); c.globalAlpha=.18; c.fillStyle='#ff3b5c'; c.fillRect(0,0,p.c.width,p.c.height); c.restore();
      c.strokeStyle='#ff3b5c'; c.lineWidth=lw*2;
      c.beginPath(); c.moveTo(0,0); c.lineTo(p.c.width,p.c.height); c.stroke();
    }
    const rg=range[p.role];
    if((rg.start!==null&&f<rg.start)||(rg.stop!==null&&f>rg.stop)){   /* outside the movie range */
      c.save(); c.globalAlpha=.30; c.fillStyle='#000'; c.fillRect(0,0,p.c.width,p.c.height); c.restore();
    }
    const ctr=centreFor(p.role,f);
    if(ctr&&box){
      const own=!!centres[K(p.role,f)];
      c.strokeStyle='#fff'; c.lineWidth=lw; c.setLineDash(own?[]:[9,7]);
      c.strokeRect(ctr[0]-box.w/2,ctr[1]-box.h/2,box.w,box.h); c.setLineDash([]);
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([sx,sy])=>{c.fillStyle='#5fa8ff';c.beginPath();
        c.arc(ctr[0]+sx*box.w/2,ctr[1]+sy*box.h/2,r,0,7);c.fill();});
      c.strokeStyle=own?'#3ddc84':'#5fa8ff';
      c.beginPath(); c.moveTo(ctr[0]-r*1.6,ctr[1]); c.lineTo(ctr[0]+r*1.6,ctr[1]);
      c.moveTo(ctr[0],ctr[1]-r*1.6); c.lineTo(ctr[0],ctr[1]+r*1.6); c.stroke();
    }
    zooms.forEach((z,i)=>{
      if(z.role!==p.role||z.frame!==f) return;
      c.strokeStyle=(i===zsel)?'#ffd54a':'#ff8c1a'; c.lineWidth=lw*(i===zsel?1.5:1);
      c.strokeRect(z.x,z.y,z.w,z.h);
      c.fillStyle=c.strokeStyle; c.fillText('Z'+(i+1),z.x+3,z.y-3);
      [[0,0],[1,0],[0,1],[1,1]].forEach(([ax,ay])=>{c.beginPath();
        c.arc(z.x+ax*z.w,z.y+ay*z.h,r*.8,0,7);c.fill();});
    });
  });
  counts(); movieState(); drawBoxList();
}
function counts(){
  const nA=[...sel].filter(k=>k.startsWith('abl:')).length, nM=[...sel].filter(k=>k.startsWith('mon:')).length;
  const pa=panels.find(p=>p.role==='abl'), pm=panels.find(p=>p.role==='mon');
  const inA=pa&&sel.has(K('abl',frameOf(pa))), inM=pm&&sel.has(K('mon',frameOf(pm)));
  document.getElementById('m-frames').innerHTML=
    `<b>ablation ${nA}</b>/${nFrames('abl')} ${pa?(inA?'<span style="color:#3ddc84">✓ this frame</span>':''):'<span style="opacity:.5">(none)</span>'}`+
    ` &nbsp;·&nbsp; <b>monitoring ${nM}</b>/${nFrames('mon')} ${inM?'<span style="color:#3ddc84">✓ this frame</span>':''}`;
  document.getElementById('m-centres').textContent=
    Object.keys(centres).length?`${Object.keys(centres).length} centre points`:'no centre points';
  document.getElementById('m-box').textContent=box?`crop box ${Math.round(box.w)}×${Math.round(box.h)} px`:'no crop box';
}
function movieState(){
  const nA=[...excl].filter(k=>k.startsWith('abl:')).length, nM=[...excl].filter(k=>k.startsWith('mon:')).length;
  const pa=panels.find(p=>p.role==='abl'), pm=panels.find(p=>p.role==='mon');
  const cutA=pa&&excl.has(K('abl',frameOf(pa))), cutM=pm&&excl.has(K('mon',frameOf(pm)));
  document.getElementById('m-excl').innerHTML =
    `<b>${nA}</b> ablation · <b>${nM}</b> monitoring cut` +
    (cutA?' <span style="color:#ff6b6b">· this abl frame CUT</span>':'') +
    (cutM?' <span style="color:#ff6b6b">· this mon frame CUT</span>':'');
  for(const [rl,el] of [['abl','m-rangeAbl'],['mon','m-rangeMon']]){
    const r=range[rl], n=nFrames(rl);
    document.getElementById(el).textContent =
      (r.start===null&&r.stop===null) ? `${rl} range: whole clip (0–${Math.max(0,n-1)})`
        : `${rl} range: ${r.start===null?0:r.start} – ${r.stop===null?Math.max(0,n-1):r.stop}`
          + ((r.start!==null&&r.stop!==null&&r.stop<r.start)?'  ⚠ stop is before start':'');
  }
}
function drawBoxList(){
  const el=document.getElementById('boxlist'); let h='';
  if(box) h+=`<div style="padding:4px;border:1px solid #333;border-radius:3px;margin:2px 0;background:#1f1f1f">
      <b>crop box</b> — whole cell · ${Math.round(box.w)}×${Math.round(box.h)}px · every frame
      <span data-del="box" style="float:right;cursor:pointer;color:#ff6b6b;font-weight:700">✕</span></div>`;
  else h+='<div style="opacity:.6;padding:3px 0">no crop box — use “fit box to the cell outline”</div>';
  zooms.forEach((z,i)=>{
    const p=panels.find(q=>q.role===z.role), here=p&&frameOf(p)===z.frame;
    h+=`<div data-i="${i}" style="padding:4px;border:1px solid #333;border-radius:3px;margin:2px 0;
        background:${i===zsel?'#3a3a2a':'transparent'};cursor:pointer">
        <b>Z${i+1}</b> ${z.role} frame ${z.frame} · ${Math.round(z.w)}×${Math.round(z.h)}px
        ${here?'<span style="color:#3ddc84"> · on this frame</span>':'<span style="opacity:.65"> · place here ▸</span>'}
        <span data-del="${i}" style="float:right;cursor:pointer;color:#ff6b6b;font-weight:700">✕</span></div>`;
  });
  el.innerHTML=h;
  el.querySelectorAll('[data-del]').forEach(x=>x.onclick=ev=>{ev.stopPropagation();
    if(x.dataset.del==='box'){box=null;banner('crop box deleted — gone from every frame');}
    else{const i=Number(x.dataset.del);zooms.splice(i,1); if(zsel===i)zsel=null; else if(zsel>i)zsel--;
         banner('zoom box deleted');}
    paint();});
  el.querySelectorAll('[data-i]').forEach(d=>d.onclick=()=>{
    const i=Number(d.dataset.i), z=zooms[i], p=panels.find(q=>q.role===z.role); if(!p) return;
    const f=frameOf(p);
    if(z.frame===f){zsel=i;paint();return;}
    zooms.push({...z,frame:f}); zsel=zooms.length-1; paint();
    banner(`Z${i+1} copied onto ${z.role} frame ${f}`);});
}
function toImg(p,e){const r=p.c.getBoundingClientRect();
  return [(e.clientX-r.left)/r.width*p.c.width,(e.clientY-r.top)/r.height*p.c.height];}
function hitZoom(p,x,y){ const f=frameOf(p), m=Math.max(9,p.c.width/95);
  for(let i=zooms.length-1;i>=0;i--){ const z=zooms[i];
    if(z.role!==p.role||z.frame!==f) continue;
    const L=Math.abs(x-z.x)<m,R=Math.abs(x-(z.x+z.w))<m,T=Math.abs(y-z.y)<m,B=Math.abs(y-(z.y+z.h))<m;
    if(L&&T)return[i,'nw']; if(R&&T)return[i,'ne']; if(L&&B)return[i,'sw']; if(R&&B)return[i,'se'];
    if(L)return[i,'w']; if(R)return[i,'e']; if(T)return[i,'n']; if(B)return[i,'s'];
    if(x>z.x&&x<z.x+z.w&&y>z.y&&y<z.y+z.h)return[i,'move']; }
  return null; }
function hitBox(p,x,y){ const ctr=centreFor(p.role,frameOf(p)); if(!ctr||!box) return null;
  const m=Math.max(10,p.c.width/90);
  const L=Math.abs(x-(ctr[0]-box.w/2))<m,R=Math.abs(x-(ctr[0]+box.w/2))<m;
  const T=Math.abs(y-(ctr[1]-box.h/2))<m,B=Math.abs(y-(ctr[1]+box.h/2))<m;
  if(L&&T)return'nw'; if(R&&T)return'ne'; if(L&&B)return'sw'; if(R&&B)return'se';
  if(L)return'w'; if(R)return'e'; if(T)return'n'; if(B)return's'; return null; }
panels.forEach(p=>{
  p.c.addEventListener('pointermove',e=>{ const [x,y]=toImg(p,e);
    if(!drag){const z=hitZoom(p,x,y),b=z?null:hitBox(p,x,y);
      p.c.style.cursor=z?(z[1]==='move'?'move':z[1]+'-resize'):b?b+'-resize':'crosshair'; return;}
    const dx=x-drag.x,dy=y-drag.y,o=drag.o;
    if(drag.kind==='zoom'){const z=zooms[drag.i];
      if(drag.mode==='move'){z.x=o.x+dx;z.y=o.y+dy;}
      else{ if(drag.mode.includes('w')){z.x=o.x+dx;z.w=Math.max(12,o.w-dx);}
            if(drag.mode.includes('e'))z.w=Math.max(12,o.w+dx);
            if(drag.mode.includes('n')){z.y=o.y+dy;z.h=Math.max(12,o.h-dy);}
            if(drag.mode.includes('s'))z.h=Math.max(12,o.h+dy);} }
    else{ if(drag.mode.includes('e'))box.w=Math.max(20,o.w+dx*2);
          if(drag.mode.includes('w'))box.w=Math.max(20,o.w-dx*2);
          if(drag.mode.includes('s'))box.h=Math.max(20,o.h+dy*2);
          if(drag.mode.includes('n'))box.h=Math.max(20,o.h-dy*2); }
    paint(); });
  p.c.addEventListener('pointerdown',e=>{ const [x,y]=toImg(p,e), f=frameOf(p);
    const z=hitZoom(p,x,y);
    if(z){zsel=z[0];drag={kind:'zoom',i:z[0],mode:z[1],x,y,o:{...zooms[z[0]]}};
          p.c.setPointerCapture(e.pointerId);paint();return;}
    const b=hitBox(p,x,y);
    if(b){drag={kind:'box',mode:b,x,y,o:{...box}};p.c.setPointerCapture(e.pointerId);return;}
    centres[K(p.role,f)]=[x,y]; sel.add(K(p.role,f)); paint();
    banner(`centre set on ${p.role} frame ${f} — later ${p.role} frames inherit it`); });
  p.c.addEventListener('pointerup',e=>{drag=null;try{p.c.releasePointerCapture(e.pointerId);}catch(_){}});
});
const pp=document.getElementById('play-pause');
pp.onclick=()=>{ const playing=videos.some(v=>!v.paused);
  videos.forEach(v=>playing?v.pause():v.play().catch(()=>{}));
  pp.textContent=playing?'▶':'❚❚'; };
videos.forEach(v=>v.addEventListener('timeupdate',()=>{ if(!v.paused){label();paint();} }));
document.getElementById('step-back').onclick=()=>stepFrames(-1);
document.getElementById('step-fwd').onclick=()=>stepFrames(1);
document.getElementById('scrubber').oninput=e=>setMasterTime(parseFloat(e.target.value));
function toggleRole(role){ const p=panels.find(q=>q.role===role); if(!p){banner('no '+role+' movie');return;}
  const k=K(role,frameOf(p)); if(sel.has(k))sel.delete(k); else sel.add(k); paint(); }
document.getElementById('toggleAbl').onclick=()=>toggleRole('abl');
document.getElementById('toggleMon').onclick=()=>toggleRole('mon');
document.getElementById('everyN').onclick=()=>{const n=Number(prompt('include every Nth frame of BOTH movies:','5')||0);
  if(n){sel=new Set(FRAMES.filter(g=>g.frame%n===0).map(g=>K(g.role,g.frame))); paint();}};
document.getElementById('clearCentre').onclick=()=>{
  panels.forEach(p=>delete centres[K(p.role,frameOf(p))]); paint();};
function outlineFor(p){ return (allRows||[]).find(a=>a.type==='cell_outline'&&
  Number(a.frame)===frameOf(p)&&((a.phase||'mon')==='abl'?'abl':'mon')===p.role&&a.points); }
document.getElementById('dropCentre').onclick=()=>{
  let n=0; panels.forEach(p=>{ const o=outlineFor(p); if(!o) return;
    const q=JSON.parse(o.points);
    centres[K(p.role,frameOf(p))]=[q.reduce((s,d)=>s+d[0],0)/q.length,q.reduce((s,d)=>s+d[1],0)/q.length];
    sel.add(K(p.role,frameOf(p))); n++; });
  paint(); banner(n?`centre taken from your cell outline on ${n} panel(s)`:'no cell outline on this frame');};
document.getElementById('fit').onclick=()=>{
  const p=panels.find(q=>outlineFor(q)); if(!p){banner('no cell outline on this frame');return;}
  const q=JSON.parse(outlineFor(p).points), xs=q.map(d=>d[0]), ys=q.map(d=>d[1]);
  const s=Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys))*1.6;
  box={w:s,h:s}; paint(); banner('crop box sized from the outline — identical on every frame');};
document.getElementById('square').onclick=()=>{if(!box){banner('no crop box yet');return;}
  const s=Math.max(box.w,box.h); box={w:s,h:s}; paint();};
function cutRole(role){ const p=panels.find(q=>q.role===role); if(!p){banner('no '+role+' movie');return;}
  const k=K(role,frameOf(p)); if(excl.has(k)) excl.delete(k); else excl.add(k); paint();
  banner(`${role} frame ${frameOf(p)} ${excl.has(k)?'CUT from':'restored to'} the processed movie`); }
document.getElementById('exAbl').onclick=()=>cutRole('abl');
document.getElementById('exMon').onclick=()=>cutRole('mon');
function setEdge(role,which){ const p=panels.find(q=>q.role===role); if(!p){banner('no '+role+' movie');return;}
  range[role][which]=frameOf(p); paint();
  banner(`${role} movie ${which==='start'?'starts':'ends'} at frame ${frameOf(p)} (click again elsewhere to move it)`); }
document.getElementById('startAbl').onclick=()=>setEdge('abl','start');
document.getElementById('stopAbl').onclick=()=>setEdge('abl','stop');
document.getElementById('startMon').onclick=()=>setEdge('mon','start');
document.getElementById('stopMon').onclick=()=>setEdge('mon','stop');
document.getElementById('addZoom').onclick=()=>{
  const p=panels.find(q=>q.role==='abl')||panels[0], f=frameOf(p);
  const ctr=centreFor(p.role,f)||[p.c.width/2,p.c.height/2];
  zooms.push({role:p.role,frame:f,x:ctr[0]-ZOOM_PX/2,y:ctr[1]-ZOOM_PX/2,w:ZOOM_PX,h:ZOOM_PX});
  zsel=zooms.length-1; paint();
  banner(`standard zoom box added on ${p.role} frame ${f} (${ZOOM_PX}px = the fixed 8.7 µm close-up window)`);};
window.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'){e.preventDefault();stepFrames(1);}
  if(e.key==='ArrowLeft'){e.preventDefault();stepFrames(-1);}
  if(e.key==='Backspace'&&zsel!==null){zooms.splice(zsel,1);zsel=null;paint();}});
async function load(){
  try{ const r=await fetch('/load?batch='+encodeURIComponent(BATCH));
    const j=await r.json(); allRows=j.rows||[]; loaded=true;
    for(const a of allRows){ const rl=(a.phase||'mon')==='abl'?'abl':'mon';
      if(a.type==='timestrip_frame'&&(a.label||'')!=='movie_exclude'){const k=K(rl,Number(a.frame)); sel.add(k);
        if(a.x!==''&&a.x!==null&&a.y!==''&&a.y!==null) centres[k]=[Number(a.x),Number(a.y)];}
      if(a.type==='crop_box'&&(a.crop_name||'')==='timestrip') box={w:Number(a.w),h:Number(a.h)};
      if(a.type==='timestrip_frame'&&(a.label||'')==='movie_exclude') excl.add(K(rl,Number(a.frame)));
      if(a.type==='batch_meta'&&/^movie_(start|stop)_(abl|mon)$/.test(a.label||'')){
        const [,w,r]=a.label.match(/^movie_(start|stop)_(abl|mon)$/);
        const v=Number(a.notes); if(!isNaN(v)) range[r][w]=v; }
      if(a.type==='crop_box'&&(a.crop_name||'')==='timestrip_zoom')
        zooms.push({role:rl,frame:Number(a.frame),x:Number(a.x),y:Number(a.y),w:Number(a.w),h:Number(a.h)});}
    sav(`loaded ${allRows.length} existing marks — safe to save`); paint();
  }catch(e){ sav('LOAD FAILED — saving disabled');
    banner('could not load existing marks; saving disabled so nothing is destroyed'); }
}
document.getElementById('save').onclick=async()=>{
  if(!loaded){sav('REFUSING TO SAVE — marks never loaded');return;}
  const mine=a=>a.type==='timestrip_frame'||
    (a.type==='crop_box'&&['timestrip','timestrip_zoom'].includes(a.crop_name||''))||
    (a.type==='batch_meta'&&/^movie_(start|stop)_(abl|mon)$/.test(a.label||''));
  const rows=allRows.filter(a=>!mine(a));
  let id=Math.max(0,...allRows.map(a=>Number(a.id)||0));
  for(const k of [...sel].sort()){ const [rl,fs]=k.split(':'), f=Number(fs);
    const fr=FRAMES.find(x=>x.role===rl&&x.frame===f)||{}, c=centres[k];
    rows.push({id:++id,batch:BATCH,type:'timestrip_frame',label:'',frame:f,t_sec:fr.t_sec??'',
               x:c?Math.round(c[0]):'',y:c?Math.round(c[1]):'',phase:rl,channel:'fluor',
               notes:'timestrip'+(c?';centre':'')}); }
  if(box) rows.push({id:++id,batch:BATCH,type:'crop_box',label:'crop',frame:'',t_sec:'',
                     crop_name:'timestrip',x:'',y:'',w:Math.round(box.w),h:Math.round(box.h),
                     phase:'mon',channel:'fluor',notes:'timestrip window shape+size (one per batch)'});
  for(const k of [...excl].sort()){ const [rl,fs]=k.split(':');
    rows.push({id:++id,batch:BATCH,type:'timestrip_frame',label:'movie_exclude',frame:Number(fs),t_sec:'',
               x:'',y:'',phase:rl,channel:'fluor',notes:'cut from the processed movie'}); }
  for(const rl of ['abl','mon']) for(const w of ['start','stop']){
    const v=range[rl][w]; if(v===null) continue;
    rows.push({id:++id,batch:BATCH,type:'batch_meta',label:`movie_${w}_${rl}`,frame:'',t_sec:'',
               x:'',y:'',phase:rl,channel:'',notes:String(v)}); }
  zooms.forEach(z=>rows.push({id:++id,batch:BATCH,type:'crop_box',label:'crop',frame:z.frame,t_sec:'',
                     crop_name:'timestrip_zoom',x:Math.round(z.x),y:Math.round(z.y),
                     w:Math.round(z.w),h:Math.round(z.h),phase:z.role,channel:'fluor',
                     notes:'ablation close-up zoom box (per frame, not propagated)'}));
  sav('saving…');
  const r=await fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},
                              body:JSON.stringify({batch:BATCH,rows})});
  const j=await r.json();
  document.getElementById('save-indicator').textContent = j.ok?'saved':'SAVE FAILED';
  sav(j.ok?`saved · ${sel.size} frames · ${Object.keys(centres).length} centres · ${zooms.length} zooms · ${excl.size} cut`
          :'SAVE FAILED: '+(j.error||'?'));};
document.getElementById('save-csv').onclick=()=>document.getElementById('save').click();
load();
</script>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batches", nargs="*", default=[])
    a = ap.parse_args()
    if not a.batches:
        print("give --batches"); return
    rows, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in rows}
    for b in a.batches:
        # PREFER A PACKAGE THAT ACTUALLY CARRIES THE ABLATION MOVIE. The same batch is packaged under
        # several roots and they do not all contain abl_*.mp4 — picking the first match silently dropped
        # the whole ablation row for `20250826 test_ablation_14`.
        cands = [os.path.join(r, b) for r in PKG_ROOTS if os.path.isdir(os.path.join(r, b))]
        pkg = next((c for c in cands
                    if os.path.isfile(os.path.join(c, "abl_fluor.mp4"))
                    or os.path.isfile(os.path.join(c, "abl_phase.mp4"))), None) or (cands[0] if cands else None)
        if not pkg:
            print(f"   NO PACKAGE for {b}"); continue
        # LIFT THE MULTI-BATCH SLIDE'S STYLESHEET. Earlier builds copied the PER-BATCH index.html, which is
        # a different layout: controls on the right, no #top-strip, css grid rows. The slides she actually
        # uses are the multi-batch indexes -- #top-strip + #scrubber-bar + .batch-section rows, with
        # #controls as a BOTTOM bar. Build one for this batch (index only, no re-encoding) and lift its CSS
        # so the movie area is identical; the override block below moves the controls to the right, which is
        # the single difference she asked for.
        css = ""
        tmp_idx = os.path.join(os.path.dirname(pkg), f"_tsstyle_{b.replace(' ', '_')}.html")
        try:
            import subprocess
            subprocess.run([sys.executable, "-u", os.path.expanduser("~/ablation-pipeline/make_annotation_html.py"),
                            "--multi-batch", json.dumps([{"name": b, "pkg_dir": pkg}]),
                            "--index-out", tmp_idx, "--pkg-root", os.path.dirname(pkg)],
                           capture_output=True, text=True, timeout=300)
            if os.path.isfile(tmp_idx):
                m = re.search(r"<style>(.*?)</style>",
                              open(tmp_idx, encoding="utf-8", errors="replace").read(), re.S)
                css = m.group(1) if m else ""
        except Exception as e:
            print(f"   (multi-batch css lift failed: {e})")
        finally:
            if os.path.isfile(tmp_idx):
                os.remove(tmp_idx)
        # the ONE deliberate deviation: controls down the right instead of across the bottom
        css += """
/* ---- timestrip setup: controls on the RIGHT (her request), everything else as the annotation slides ---- */
body { grid-template-columns: minmax(0,1fr) 460px !important; grid-template-rows: minmax(0,1fr) !important; }
#controls { border-top:0 !important; border-left:1px solid var(--border) !important;
            flex-direction:column !important; flex-wrap:nowrap !important; align-items:stretch !important;
            max-height:100vh; }
#controls > div { flex:0 0 auto !important; min-width:0 !important; width:100%; }
#tool-buttons { display:block !important; }
#tool-buttons-flow { column-width:auto !important; columns:1 !important; }
#tool-buttons-flow .btn { width:100%; text-align:left; }
"""
        p = (MR.get(b, {}).get("Drive Path", "") or "").strip()
        if not (p and os.path.isdir(p)):
            p = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
        fj = os.path.join(p, f"{b}_frames.json")
        try:
            px = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
        except Exception:
            px = 0.062
        # BOTH ROLES. Each movie is indexed from 0 within its own role, which is how the packaged
        # abl_*.mp4 / mon_*.mp4 are encoded, so a frame is identified by (role, index) — never by index
        # alone. Ablation frames come first so the strip reads in acquisition order.
        fr = []
        if os.path.isfile(fj):
            allf = json.load(open(fj)).get("frames", [])
            for role, tag in (("ablation", "abl"), ("monitoring", "mon")):
                seq = [f for f in allf if f.get("role") == role]
                for i, f in enumerate(seq):
                    t = f.get("t_sec"); sec = int(abs(t)) if t is not None else 0
                    fr.append({"role": tag, "frame": i, "t_sec": t,
                               "hms": ("-" if (t or 0) < 0 else "")
                                      + f"{sec//3600}:{(sec%3600)//60:02d}:{sec%60:02d}"})
        # panel rows: ablation row only when that package actually carries an ablation movie
        rows_html = ""
        for role, lab, files in (("abl", "Ablation", ("abl_phase.mp4", "abl_fluor.mp4")),
                                 ("mon", "Monitoring", ("mon_phase.mp4", "mon_fluor.mp4"))):
            have = [f for f in files if os.path.isfile(os.path.join(pkg, f))]
            if not have:
                continue
            cells = ""
            for f in have:
                ch = "phase" if "phase" in f else "fluor"
                cells += (f'<div class="panel-wrap"><div class="panel-label">{lab} · '
                          f'{"Phase / BF" if ch=="phase" else "Fluor"}</div>'
                          f'<div class="panel" data-phase="{role}" data-channel="{ch}"><div class="zoomwrap">'
                          f'<video src="{html.escape(b).replace(" ", "%20")}/{f}" muted playsinline '
                          f'preload="auto"></video><canvas></canvas></div></div></div>')
            rows_html += (f'<div><div class="row-label">{lab}</div>'
                          f'<div class="row" data-cols="{len(have)}">{cells}</div></div>')
        zoom_px = 2 * max(8, int(round(4.34 / px)))      # ts_render.STD_ZOOM_HALF_UM = 4.34 um, fixed physical
        # the metadata strip the kt-outline slides carry, same fields, same md-item/md-k/md-v markup
        r0 = MR.get(b, {})
        meta_pairs = [("Treatment", r0.get("On-Target / Off-Target", "")),
                      ("Phase at abl", r0.get("Phase of Ablations", "")),
                      ("Success", r0.get("Ablation Success", "")),
                      ("# Sisterless KTs (expected)", r0.get("# Sisterless KTs", "")),
                      ("Polar chromosomes", r0.get("Polar Chromosomes", "")),
                      ("Lagging chromosomes", r0.get("Lagging Chromosomes", "")),
                      ("Pixel size (um)", r0.get("Pixel Size (um)", "")),
                      ("Metaphase start", r0.get("Metaphase Start (s)", "")),
                      ("Anaphase onset", r0.get("Anaphase Onset (s)", ""))]
        meta_html = "".join(f'<div class="md-item"><span class="md-k">{html.escape(k)}:</span>'
                            f'<span class="md-v">{html.escape(str(v) or "—")}</span></div>'
                            for k, v in meta_pairs)
        body = (BODY.replace("__META__", meta_html)
                    .replace("__ROWS__", rows_html)
                    .replace("__ZOOM_PX__", str(zoom_px))
                    .replace("__ZOOM_UM__", "8.7")
                    .replace("__BATCH_JSON__", json.dumps(b))
                    .replace("__FRAMES_JSON__", json.dumps(fr))
                    .replace("__FPS__", repr(FPS))
                    .replace("__PKG__", html.escape(b).replace(" ", "%20"))
                    .replace("__BATCH__", html.escape(b)))
        page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                f'<title>Timestrip setup — {html.escape(b)}</title><style>{css}</style></head>'
                f'<body>{body}</body></html>')
        out = os.path.join(os.path.dirname(pkg), f"timestrip_setup_{b.replace(' ', '_')}.html")
        open(out, "w").write(page)
        print(f"   wrote {out}  ({sum(1 for x in fr if x['role']=='abl')} abl + {sum(1 for x in fr if x['role']=='mon')} mon frames, zoom box {zoom_px}px, css {len(css)}b)")


if __name__ == "__main__":
    main()
