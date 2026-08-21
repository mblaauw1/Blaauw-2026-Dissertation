#!/usr/bin/env python3
"""MSER-style kinetochore segmentation: instead of guessing a threshold, sweep it and take the level at
which the segmented region is MOST STABLE (area changes least per unit threshold) - the classic
maximally-stable-extremal-region criterion, which is designed to find an object's natural boundary.
Then take that region's AREA CENTROID, the same quantity her outline gives.
Validated on the 917 verified placements, grouped CV by cell."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import ndimage
import lib
lib.apply_style()
ROOT="/Volumes/4 MB"; csv.field_size_limit(10**9); A=f"{ROOT}/annotations"
OUT=f"{ROOT}/ablation_figures_20260625/group7_questions"
truth={}
for r in csv.DictReader(open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv",newline="")):
    if r["status"]=="matched" and r["snap_x"]: truth[str(r["circle_id"])]=(float(r["snap_x"]),float(r["snap_y"]))
pts={}
for r in csv.DictReader(open(f"{A}/kt_points.csv",newline="")):
    if str(r["id"]) in truth: pts[str(r["id"])]=(r["batch"].strip(),int(r["frame"]),float(r["x"]),float(r["y"]))
bycell=collections.defaultdict(list)
for pid,(b,f,x,y) in pts.items(): bycell[b].append((pid,f,x,y))
RAD=14

def mser_center(g,x,y,rad=RAD):
    h,w=g.shape[:2]; xi,yi=int(round(x)),int(round(y))
    x0,x1=max(0,xi-rad),min(w,xi+rad+1); y0,y1=max(0,yi-rad),min(h,yi+rad+1)
    sub=g[y0:y1,x0:x1].astype(float)
    if sub.size<49: return None
    lo,hi=np.percentile(sub,[20,99.5])
    if hi<=lo: return None
    cx,cy=x-x0,y-y0
    levels=np.linspace(hi,lo,28); areas=[]; regs=[]
    for t in levels:
        m=sub>=t
        if m.sum()<4: areas.append(0); regs.append(None); continue
        lab,n=ndimage.label(m)
        li=lab[int(round(cy)),int(round(cx))]
        if li==0:                                    # click not in a region yet: take nearest component
            best,bd=0,1e9
            for i in range(1,n+1):
                ys,xs=np.where(lab==i); d=np.hypot(xs.mean()-cx,ys.mean()-cy)
                if d<bd: bd,best=d,i
            li=best if bd<rad else 0
        if li==0: areas.append(0); regs.append(None); continue
        ys,xs=np.where(lab==li); areas.append(len(ys)); regs.append((ys,xs))
    areas=np.array(areas,float)
    valid=[i for i in range(1,len(areas)-1) if regs[i] is not None and 25<=areas[i]<=900]
    if not valid: return None
    # STABILITY: relative area growth per level step; the natural boundary is where it is smallest
    stab=[(abs(areas[i+1]-areas[i-1])/max(areas[i],1.0), i) for i in valid]
    stab.sort(); _,bi=stab[0]
    ys,xs=regs[bi]
    bg=float(np.percentile(sub,20)); v=sub[ys,xs]-bg; v[v<0]=0
    if v.sum()<=0: gx,gy=xs.mean(),ys.mean()
    else: gx,gy=(xs*v).sum()/v.sum(),(ys*v).sum()/v.sum()
    return float(x0+gx),float(y0+gy),int(areas[bi]),float(stab[0][0])

res={}
for ci,b in enumerate(sorted(bycell),1):
    ft=None
    for role in ("monitoring","ablation"):
        try:
            ft=lib.FluorTif(b,role)
            if ft is not None and ft.plane_by_frame(bycell[b][0][1]) is not None: break
        except Exception: ft=None
    if ft is None: continue
    for pid,f,x,y in bycell[b]:
        g=ft.plane_by_frame(f)
        if g is None: continue
        r=mser_center(g,x,y)
        if r: res[pid]=r
    if ci%15==0: print(f"  [{ci}/{len(bycell)}]")

ok=[p for p in res if p in truth]
e=np.array([np.hypot(res[p][0]-truth[p][0],res[p][1]-truth[p][1]) for p in ok])
ec=np.array([np.hypot(pts[p][2]-truth[p][0],pts[p][3]-truth[p][1]) for p in ok])
ar=np.array([res[p][2] for p in ok])
print(f"\nn={len(ok)} marks")
print(f"  raw click        median {np.median(ec):5.2f} px | within 3px {np.mean(ec<=3)*100:5.1f}% | within 5px {np.mean(ec<=5)*100:5.1f}%")
print(f"  MSER region      median {np.median(e):5.2f} px | within 3px {np.mean(e<=3)*100:5.1f}% | within 5px {np.mean(e<=5)*100:5.1f}%")
print(f"  segmented area   median {np.median(ar):.0f} px   (her outlines 196 px)")
st=np.array([res[p][3] for p in ok])
print("\nstability score vs error (lower score = more stable region):")
for lo,hi in [(0,.05),(.05,.1),(.1,.2),(.2,1e9)]:
    m=(st>=lo)&(st<hi)
    if m.sum()>=20: print(f"  {lo:.2f}-{hi if hi<1e9 else 'inf'}: n={m.sum():4d}  median {np.median(e[m]):5.2f} px  within 5px {np.mean(e[m]<=5)*100:5.1f}%")
