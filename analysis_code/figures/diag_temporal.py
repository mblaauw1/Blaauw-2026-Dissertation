"""For the worst-offset suspicious clicks: scan frames i-6..i+6 and find where (if anywhere) a bright KT
punctum sits AT the click location. If the best frame is a consistent non-zero offset -> a frame-mapping bug.
If the KT is brightest at offset 0 but still weak, or never a real punctum -> the click is genuinely misplaced
(not a mapping error). Also prints the video_file each annotation was drawn on."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np
from collections import defaultdict
import lib
SCREEN={"pre_abl","pre_abl_pair","post_abl_pair","polar","sisterless","paired_kt"}
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
byb=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lab not in SCREEN or lib.is_mad1(b): continue
    try: byb[b].append((r[ix['id']],lab,int(r[ix['frame']]),float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']]),r[ix['video_file']]))
    except: pass

def localz(g,x,y):
    """peak modified-z at the click (5px disk max) vs a 20px window — is there a real punctum here?"""
    h,w=g.shape; W=20; x0,y0=max(0,int(x)-W),max(0,int(y)-W); sub=g[y0:min(h,int(y)+W),x0:min(w,int(x)+W)].astype(float)
    if sub.size<25: return None
    med=np.median(sub); mad=np.median(np.abs(sub-med)) or 1.0
    d=g[max(0,int(y)-3):int(y)+4,max(0,int(x)-3):int(x)+4].astype(float)
    return 0.6745*(d.max()-med)/mad

REC=[]
for b in byb:
    for role in ("ablation","monitoring"):
        ft=lib.FluorTif(b,role)
        if not ft.ok(): ft.close(); continue
        for (aid,lab,frame,t,x,y,vf) in byb[b]:
            i=int(np.argmin(np.abs(ft.ts-t)))
            sx,sy=lib.snap_to_peak(ft.plane_by_pos(i),x,y,9) if ft.plane_by_pos(i) is not None else (x,y)
            off=float(np.hypot(sx-x,sy-y))
            zs=[]
            for k in range(-6,7):
                g=ft.plane_by_pos(i+k)
                if g is None: zs.append((k,None)); continue
                zs.append((k,localz(g,x,y)))
            valid=[(k,z) for k,z in zs if z is not None]
            if not valid: continue
            bk,bz=max(valid,key=lambda kz:kz[1])
            z0=dict(valid).get(0)
            REC.append((off,b[:20],aid,lab,frame,bk,round(bz,1),round(z0,1) if z0 is not None else None,vf.split("/")[-1][:34]))
        ft.close(); break

REC.sort(key=lambda r:-r[0])
print(f"{'off':>5} {'batch':22}{'id':>5} {'label':14} {'fcsv':>5} {'bestΔf':>7} {'bestZ':>6} {'Z@0':>6}  video_file")
for off,b,aid,lab,frame,bk,bz,z0,vf in REC[:18]:
    flag="  <-- KT is at Δf=0 (mapping OK)" if bk==0 else (f"  <-- KT brightest {bk:+d} frames away" if bz>=4 else "")
    print(f"{off:5.1f} {b:22}{aid:>5} {lab:14} {frame:>5} {bk:>+7d} {bz:>6} {str(z0):>6}  {vf}{flag}")
nz=[r for r in REC if r[5]==0]; shifted=[r for r in REC if r[5]!=0 and r[6]>=4]
print(f"\nof {len(REC)} suspicious: best frame is Δf=0 for {len(nz)}; a SHIFTED frame is clearly brighter (z>=4) for {len(shifted)}")
print("if 'shifted' is ~0 -> no frame bug; the bad ones are genuinely off-KT clicks")
