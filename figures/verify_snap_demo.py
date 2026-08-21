"""Demonstrate that the MEASUREMENT re-centers on the kinetochore (snap-to-peak), so an off-centre click
still captures the whole KT. Each crop shows: your RAW click (white +), the SNAPPED centre where the disk
is actually placed (cyan +), and the r=5 disk on the snapped centre (cyan circle)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625"
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
P=defaultdict(lambda: defaultdict(list))
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_mad1(b) or lab not in ("pre_abl","polar","sisterless"): continue
    try: P[b][lab].append((float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass
cands=[b for b in P if (P[b].get("pre_abl") or P[b].get("polar") or P[b].get("sisterless"))]
items=[]; moved=[]
for b in cands:
    role='ablation' if P[b].get("pre_abl") else 'monitoring'
    ft=lib.FluorTif(b,role)
    if not ft.ok(): ft=lib.FluorTif(b,'monitoring')
    if not ft.ok(): continue
    lab='pre_abl' if P[b].get('pre_abl') else ('polar' if P[b].get('polar') else 'sisterless')
    for (t,x,y) in P[b][lab][:2]:
        g=ft.plane_at(t)
        if g is None: continue
        sx,sy=lib.snap_to_peak(g,x,y)        # the measurement re-centres here
        moved.append(np.hypot(sx-x,sy-y))
        if len(items)<18:
            W=15;h,w=g.shape;x0,y0=max(0,int(x)-W),max(0,int(y)-W);cr=g[y0:min(h,int(y)+W),x0:min(w,int(x)+W)].astype(float)
            lo,hi=np.percentile(cr,[15,99.7]); items.append((np.clip((cr-lo)/(hi-lo+1e-6),0,1),x-x0,y-y0,sx-x0,sy-y0,b[:16]))
    ft.close()
n=len(items); ncol=6; nrow=(n+ncol-1)//ncol
fig,axs=plt.subplots(nrow,ncol,figsize=(ncol*2.2,nrow*2.4),squeeze=False)
for k,(im,rx,ry,sxx,syy,ttl) in enumerate(items):
    a=axs[k//ncol][k%ncol]; a.imshow(im,cmap="gray",interpolation="nearest")
    a.plot(rx,ry,"+",color="white",ms=9,mew=1.3)                       # raw click
    a.plot(sxx,syy,"+",color="#37c8ff",ms=9,mew=1.3)                   # snapped centre
    a.add_patch(plt.Circle((sxx,syy),5,fill=False,color="#37c8ff",lw=1.3))   # r=5 disk where measured
    a.set_title(ttl,fontsize=6); a.set_xticks([]); a.set_yticks([])
for k in range(n,nrow*ncol): axs[k//ncol][k%ncol].axis("off")
fig.suptitle("Off-centre clicks are auto-corrected — WHITE + = your click · CYAN + = snapped KT centre where the r=5 disk is actually placed",
             x=.01,ha="left",fontweight="bold",fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/_SNAP_DEMO.png",bbox_inches="tight",dpi=140); plt.close()
moved=np.array(moved)
# capture fraction of a Gaussian within radius R, for the measured KT widths
def cap(R,sigma): return 1-np.exp(-R*R/(2*sigma*sigma))
for rhalf in (2.1,3.3):   # median and 95th-pct half-max equiv radius
    sig=rhalf/1.177
    print(f"KT half-max radius {rhalf}px (sigma~{sig:.1f}px): r=5 captures {100*cap(5,sig):.0f}% | r=6 {100*cap(6,sig):.0f}% | r=7 {100*cap(7,sig):.0f}% of integrated signal")
print(f"\nsnap moved the centre by median {np.median(moved):.1f}px (your click->KT peak); max {moved.max():.1f}px")
print(f"snap demo -> {OUT}/_SNAP_DEMO.png")
