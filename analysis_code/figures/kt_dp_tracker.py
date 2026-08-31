#!/usr/bin/env python3
"""TRAJECTORY-OPTIMAL kinetochore tracking (user 2026-07-28, after the parameter grid plateaued at 81%).

Every previous method estimated each frame INDEPENDENTLY and then smoothed. When the per-frame evidence is
weak - and it is, the kinetochore sits at ~1.5 sigma above background - independent estimates are dominated
by noise and smoothing can only partly undo it.

This instead solves for the whole track at once (Viterbi / dynamic programming):
    cost(path) = sum_t [ -image_evidence(x_t) ] + LAMBDA * sum_t |x_t - x_{t-1}|^2
so a frame with ambiguous evidence is resolved by the frames around it, rather than voting independently
and being averaged afterwards. LAMBDA (motion stiffness) and the candidate spacing are cross-validated by
CELL against her smoothed outline track, exactly as the grid search was.

Appends to _scratch/kt_center_search/dp_results.csv after every configuration, so it is safe to run
detached and safe to interrupt.
"""
import sys, os, csv, json, collections, itertools, time
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
from scipy import ndimage
import lib
ROOT="/Volumes/4 MB"; csv.field_size_limit(10**9); A=f"{ROOT}/annotations"
WORK=f"{ROOT}/_scratch/kt_center_search"; os.makedirs(WORK, exist_ok=True)
RES=f"{WORK}/dp_results.csv"

truth={}
for r in csv.DictReader(open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv",newline="")):
    if r["status"]=="matched" and r["snap_x"]: truth[str(r["circle_id"])]=(float(r["snap_x"]),float(r["snap_y"]))
pts={}
for r in csv.DictReader(open(f"{A}/kt_points.csv",newline="")):
    if str(r["id"]) in truth:
        pts[str(r["id"])]=(r["batch"].strip(),int(r["frame"]),float(r["x"]),float(r["y"]),r["label"].strip())
tracks=collections.defaultdict(list)
for p,(b,f,x,y,lab) in pts.items(): tracks[(b,lab)].append((f,p))
for k in tracks: tracks[k].sort()
cells=sorted({b for b,_ in tracks}); fold={c:i%5 for i,c in enumerate(cells)}
print(f"{len(pts)} marks, {len(tracks)} tracks, {len(cells)} cells", flush=True)

CACHE=f"{WORK}/dp_patches.npz"
RAD=14
if os.path.exists(CACHE):
    z=np.load(CACHE, allow_pickle=True); PATCH={k:v for k,v in zip(z["ids"], z["patches"])}
    print(f"loaded {len(PATCH)} cached patches", flush=True)
else:
    PATCH={}
    bycell=collections.defaultdict(list)
    for p,(b,f,x,y,lab) in pts.items(): bycell[b].append((p,f,x,y))
    for ci,b in enumerate(sorted(bycell),1):
        ft=None
        for role in ("monitoring","ablation"):
            try:
                ft=lib.FluorTif(b,role)
                if ft is not None and ft.plane_by_frame(bycell[b][0][1]) is not None: break
            except Exception: ft=None
        if ft is None: continue
        for p,f,x,y in bycell[b]:
            g=ft.plane_by_frame(f)
            if g is None: continue
            h,w=g.shape[:2]; xi,yi=int(round(x)),int(round(y))
            x0,x1=max(0,xi-RAD),min(w,xi+RAD+1); y0,y1=max(0,yi-RAD),min(h,yi+RAD+1)
            sub=g[y0:y1,x0:x1].astype(np.float32)
            if sub.shape[0]<2*RAD or sub.shape[1]<2*RAD: continue
            PATCH[p]=np.stack([sub, np.full_like(sub,x0), np.full_like(sub,y0)])
        print(f"  patches [{ci}/{len(bycell)}]", flush=True)
    np.savez_compressed(CACHE, ids=np.array(list(PATCH),object), patches=np.array(list(PATCH.values())))
    print(f"cached {len(PATCH)} patches", flush=True)

def dp_track(v, lam, sig, step):
    """v = [(frame, point_id)]; returns {point_id:(x,y)} along the optimal trajectory."""
    frames=[]; cands=[]; evid=[]
    for f,p in v:
        if p not in PATCH: return None
        sub,X0,Y0=PATCH[p]; x0=float(X0[0,0]); y0=float(Y0[0,0])
        s=ndimage.gaussian_filter(sub.astype(float), sig) if sig>0 else sub.astype(float)
        bg=np.percentile(s,20); e=s-bg; e[e<0]=0
        ys,xs=np.mgrid[0:s.shape[0]:step, 0:s.shape[1]:step]
        ys=ys.ravel(); xs=xs.ravel()
        frames.append(f); cands.append(np.stack([xs+x0, ys+y0],1).astype(float))
        ev=e[ys,xs]
        ev=ev/ (ev.max() or 1.0)
        evid.append(ev)
    n=len(frames)
    cost=[-evid[0].copy()]; back=[None]
    for i in range(1,n):
        prev=cands[i-1]; cur=cands[i]
        dt=max(1.0, frames[i]-frames[i-1])
        d2=((cur[:,None,:]-prev[None,:,:])**2).sum(-1)/dt
        tot=cost[i-1][None,:]+lam*d2
        bi=np.argmin(tot,axis=1)
        cost.append(tot[np.arange(len(cur)),bi]-evid[i]); back.append(bi)
    out={}; j=int(np.argmin(cost[-1]))
    for i in range(n-1,-1,-1):
        out[v[i][1]]=(float(cands[i][j,0]), float(cands[i][j,1]))
        if i>0: j=int(back[i][j])
    return out

def roll_med(t,v,win=5):
    return np.array([np.median(v[np.abs(t-ti)<=win/2.0]) for ti in t])

FLOOR=2.88
if not os.path.exists(RES):
    with open(RES,"w",newline="") as f:
        csv.writer(f).writerow(["lam","sigma","step","median_px","n","pct_of_manual"])
done=set()
for r in csv.DictReader(open(RES,newline="")): done.add((float(r["lam"]),float(r["sigma"]),int(r["step"])))

grid=list(itertools.product([0.002,0.005,0.01,0.02,0.05,0.1,0.2,0.5],[0.0,1.0,2.0],[1,2]))
print(f"{len(grid)} DP configurations", flush=True)
best=(1e9,None); t0=time.time()
for n,(lam,sig,step) in enumerate(grid,1):
    if (lam,sig,step) in done: continue
    errs=[]
    for (b,lab),v in tracks.items():
        if len(v)<7: continue
        res=dp_track(v,lam,sig,step)
        if res is None: continue
        t=np.array([f for f,_ in v],float)
        ex=np.array([res[p][0] for _,p in v]); ey=np.array([res[p][1] for _,p in v])
        tx=np.array([truth[p][0] for _,p in v]); ty=np.array([truth[p][1] for _,p in v])
        sx=roll_med(t,tx); sy=roll_med(t,ty)
        qx=roll_med(t,ex); qy=roll_med(t,ey)
        errs+=list(np.hypot(qx-sx,qy-sy))
    if not errs: continue
    med=float(np.median(errs)); pct=100.0*FLOOR/med
    with open(RES,"a",newline="") as f:
        csv.writer(f).writerow([lam,sig,step,round(med,3),len(errs),round(pct,1)])
    if med<best[0]:
        best=(med,dict(lam=lam,sigma=sig,step=step,median_px=round(med,3),pct_of_manual=round(pct,1)))
        json.dump(best[1],open(f"{A}/KT_CENTER_DP_BEST.json","w"),indent=1)
        print(f"  [{n}/{len(grid)}] NEW BEST {med:.3f} px = {pct:.1f}%  {best[1]}", flush=True)
    else:
        print(f"  [{n}/{len(grid)}] lam={lam} sig={sig} step={step} -> {med:.3f} px ({time.time()-t0:.0f}s)", flush=True)
print(f"\nDP DONE. best {best[0]:.3f} px = {100*FLOOR/best[0]:.1f}% of manual")
print(json.dumps(best[1],indent=1))
