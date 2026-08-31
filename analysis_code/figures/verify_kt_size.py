"""Measure the ACTUAL size of the eYFP-Cdc20 kinetochore puncta (half-max extent) to choose a disk radius
that ENCOMPASSES the whole KT (not just part of it). Also overlay r=5/6/7/8 circles on real KT crops so the
size can be judged by eye, and check the nearest-neighbour KT spacing (so the disk doesn't catch a neighbour)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from skimage import measure
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625"
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
P=defaultdict(lambda: defaultdict(list))
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_mad1(b) or lab not in ("pre_abl","pre_abl_pair","polar","sisterless"): continue
    try: P[b][lab].append((float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass

def kt_radius(g,x,y,win=16):
    """equivalent radius (px) of the KT punctum at HALF-MAX, centred near (x,y)."""
    h,w=g.shape; x0,y0=max(0,int(x)-win),max(0,int(y)-win); sub=g[y0:min(h,int(y)+win),x0:min(w,int(x)+win)].astype(float)
    if sub.size<25: return None
    cx,cy=x-x0,y-y0; bg=np.median(sub)
    yy,xx=np.ogrid[:sub.shape[0],:sub.shape[1]]; near=((xx-cx)**2+(yy-cy)**2)<=7*7
    peak=sub[near].max() if near.any() else sub.max()
    if peak-bg<8: return None
    mask=sub>=(bg+0.5*(peak-bg)); lbl=measure.label(mask)
    ci,cj=int(round(cy)),int(round(cx)); comp=lbl[ci,cj] if (0<=ci<lbl.shape[0] and 0<=cj<lbl.shape[1]) else 0
    if comp==0:
        ys,xs=np.nonzero(lbl)
        if not len(ys): return None
        d=(xs-cx)**2+(ys-cy)**2; comp=lbl[ys[d.argmin()],xs[d.argmin()]]
    area=int((lbl==comp).sum())
    if area<3: return None
    return float(np.sqrt(area/np.pi))   # equivalent radius

PIX=0.062
radii=[]; items=[]
cands=[b for b in P if (P[b].get("pre_abl") or P[b].get("polar") or P[b].get("sisterless"))]
for b in cands:
    role='ablation' if P[b].get("pre_abl") else 'monitoring'
    ft=lib.FluorTif(b,role)
    if not ft.ok(): ft=lib.FluorTif(b,'monitoring')
    if not ft.ok(): continue
    lab='pre_abl' if P[b].get('pre_abl') else ('polar' if P[b].get('polar') else 'sisterless')
    for (t,x,y) in P[b][lab][:3]:
        g=ft.plane_at(t)
        if g is None: continue
        # snap to the punctum centre first (so radius is measured from the true centre)
        sx,sy=lib.snap_to_peak(g,x,y,7)
        rr=kt_radius(g,sx,sy)
        if rr: radii.append(rr)
        if len(items)<18:
            h,w=g.shape; W=16; x0,y0=max(0,int(sx)-W),max(0,int(sy)-W); cr=g[y0:min(h,int(sy)+W),x0:min(w,int(sx)+W)].astype(float)
            lo,hi=np.percentile(cr,[15,99.7]); items.append((np.clip((cr-lo)/(hi-lo+1e-6),0,1),sx-x0,sy-y0,b[:18]))
    ft.close()
radii=np.array(radii)

# montage with r=5/6/7/8 circles on real KT crops
n=len(items); ncol=6; nrow=(n+ncol-1)//ncol
fig,axs=plt.subplots(nrow,ncol,figsize=(ncol*2.2,nrow*2.4),squeeze=False)
COLS={5:"#ff3b3b",6:"#ffd23b",7:"#3bff7a",8:"#3bc9ff"}
for k,(im,mx,my,ttl) in enumerate(items):
    a=axs[k//ncol][k%ncol]; a.imshow(im,cmap="gray",interpolation="nearest")
    for R,c in COLS.items(): a.add_patch(plt.Circle((mx,my),R,fill=False,color=c,lw=1.1))
    a.set_title(ttl,fontsize=6); a.set_xticks([]); a.set_yticks([])
for k in range(n,nrow*ncol): axs[k//ncol][k%ncol].axis("off")
fig.suptitle("KT size vs disk radius — circles: r=5 (red) · 6 (yellow) · 7 (green) · 8 (cyan).  Which encompasses the whole punctum?",
             x=.01,ha="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/_KT_SIZE_CHECK.png",bbox_inches="tight",dpi=140); plt.close()

print(f"=== KT SIZE (half-max equivalent radius), N={len(radii)} kinetochores ===")
for p in (50,75,90,95):
    print(f"  {p}th percentile equivalent radius: {np.percentile(radii,p):.1f}px  ({np.percentile(radii,p)*PIX:.2f}µm)")
print(f"  mean {radii.mean():.1f}px, max {radii.max():.1f}px")
print(f"  -> a disk of radius R encompasses a KT of equiv-radius r when R>=~r (half-max edge).")
print(f"  fraction of KTs with equiv-radius > 5px (r=5 too small): {100*np.mean(radii>5):.0f}%")
print(f"  fraction > 6px: {100*np.mean(radii>6):.0f}% | > 7px: {100*np.mean(radii>7):.0f}%")
print(f"montage -> {OUT}/_KT_SIZE_CHECK.png")
