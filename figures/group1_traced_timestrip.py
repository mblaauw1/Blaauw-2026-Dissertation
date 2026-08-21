"""time-strip of a cell with its traced outline overlaid (phase frames)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, glob, json, os, numpy as np, cv2
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT=__file__

# pick a batch with several mon outlines + an available phase monitoring movie on 4 MB
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c:i for i,c in enumerate(rows[0])}
from collections import defaultdict
import ts_render   # scale-aware overlay stroke (user 2026-08-20, board 8 item 4)
ob=defaultdict(list)
for r in rows[1:]:
    if r[ix['phase']]!='mon': continue
    try: ts=float(r[ix['t_sec']]); pts=np.array(json.loads(r[ix['points']]),np.int32)
    except: continue
    ob[r[ix['batch']].strip()].append((ts,pts))
def render_for(b):
    for fj in glob.glob(f"/Volumes/4 MB/**/{b}/{b}_frames.json",recursive=True):
        mp4=fj.replace("_frames.json","_Phase_Monitoring.mp4")
        if os.path.isfile(mp4):
            J=json.load(open(fj))
            mon=[f['t_sec'] for f in J['frames'] if f['role']=='monitoring']
            pxs=float(J.get('pixel_size_um',0.062) or 0.062)
            cap=cv2.VideoCapture(mp4); n=int(cap.get(7)); cap.release()
            if n==len(mon): return mp4,np.array(mon),pxs
    return None
def _scalebar(img,pxs,um=10):
    h,w=img.shape[:2]; L=max(3,int(um/pxs))
    cv2.rectangle(img,(w-L-12,h-20),(w-12,h-12),(255,255,255),-1)
    cv2.putText(img,f"{um}um",(w-L-12,h-24),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1,cv2.LINE_AA)
def _clabel(img,txt):   # channel label bottom-left (scalebar sits bottom-right -> no overlap)
    cv2.putText(img,txt,(6,img.shape[0]-10),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1,cv2.LINE_AA)
# choose: most outlines, render available, good match
cand=None
for b in sorted(ob,key=lambda b:-len(ob[b])):
    r=render_for(b)
    if r:
        mp4,mon,pxs=r; cand=(b,mp4,mon,pxs); break
b,mp4,mon,pxs=cand
outs=sorted(ob[b],key=lambda x:x[0])
# pick up to 5 evenly spaced
idxs=np.linspace(0,len(outs)-1,min(5,len(outs))).astype(int)
sel=[outs[i] for i in idxs]
cap=cv2.VideoCapture(mp4)
# common crop box around all selected outlines
allp=np.vstack([p for _,p in sel]); x0,y0=allp.min(0); x1,y1=allp.max(0)
m=60; H=int(cap.get(4));W=int(cap.get(3))
x0=max(0,x0-m);y0=max(0,y0-m);x1=min(W,x1+m);y1=min(H,y1+m)
_fmt="HH:MM:SS" if max(abs(int(t)) for t,_ in sel)>=3600 else "MM:SS"   # time-format line under leftmost timestamp
panels=[]
for _i,(ts,pts) in enumerate(sel):
    fi=int(np.argmin(np.abs(mon-ts)))
    cap.set(cv2.CAP_PROP_POS_FRAMES,fi); ok,fr=cap.read()
    if not ok: continue
    cv2.polylines(fr,[pts],True,(80,220,255),ts_render.stroke_px(fr))         # cyan outline (thicker, easier to see)
    crop=fr[y0:y1,x0:x1].copy()
    s=int(ts); lab=f"{'-' if s<0 else ''}{abs(s)//60}:{abs(s)%60:02d}"
    cv2.putText(crop,lab,(8,26),cv2.FONT_HERSHEY_SIMPLEX,0.8,(255,255,255),2,cv2.LINE_AA)
    if _i==0: cv2.putText(crop,_fmt,(8,52),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1,cv2.LINE_AA)  # fmt line, leftmost col
    _clabel(crop,"Phase")                               # channel label (this strip is phase-only)
    if _i==len(sel)-1: _scalebar(crop,pxs)              # scalebar bottom-right of the rightmost panel
    panels.append(crop)
cap.release()
hgt=min(p.shape[0] for p in panels); panels=[cv2.resize(p,(int(p.shape[1]*hgt/p.shape[0]),hgt)) for p in panels]
strip=np.hstack([np.hstack([p,np.full((hgt,6,3),20,np.uint8)]) for p in panels])
cv2.imwrite(f"{OUT}/G1_traced_timestrip.png",strip)
lib.record_plot("G1_traced_timestrip",["batch","panel_t_sec"],[[b,round(t,1)] for t,_ in sel],
  {"type":"timestrip with traced outline overlay","source":"_Phase_Monitoring.mp4","overlay":"cyan outline polygon","n_panels":len(panels)},
  SCRIPT,f"Traced-cell time-strip ({b}) — outline overlaid on phase frames")
print(f"traced timestrip: {b}, {len(panels)} panels at t={[round(t,0) for t,_ in sel]}")
