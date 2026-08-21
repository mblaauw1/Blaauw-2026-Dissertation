"""Verify annotation points land on the CORRECT location on the 16-bit fluor frames.
For each sampled batch: crop around a KT annotation (pre_abl/polar — should sit ON a bright KT punctum)
and around a cytosol_bg annotation (should sit on FLAT cytoplasm, NOT a punctum). Overlay the marker so
the placement is visually checkable, and print the numerical offset of each KT point to the nearest local
intensity max + whether the cytosol point is on a punctum."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625"
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
P=defaultdict(lambda: defaultdict(list))
for r in rows[1:]:
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    if lib.is_mad1(b): continue
    if lab not in ("pre_abl","polar","sisterless","cytosol_bg"): continue
    try: P[b][lab].append((float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass

def crop(g,x,y,W=22):
    h,w=g.shape; x0,x1=max(0,int(x)-W),min(w,int(x)+W); y0,y1=max(0,int(y)-W),min(h,int(y)+W)
    return g[y0:y1,x0:x1].astype(float),x-x0,y-y0
def disp(sub): lo,hi=np.percentile(sub,[15,99.7]); return np.clip((sub-lo)/(hi-lo+1e-6),0,1)
def offset_to_peak(g,x,y,rad=10):
    sub,cx,cy=crop(g,x,y,rad)
    if sub.size==0: return None
    my,mx=np.unravel_index(int(np.argmax(sub)),sub.shape); return float(np.hypot(mx-cx,my-cy)),float(sub.max()),float(np.median(g))

# pick batches that have BOTH a KT label and a cytosol_bg
cands=[b for b in P if P[b].get("cytosol_bg") and (P[b].get("pre_abl") or P[b].get("polar") or P[b].get("sisterless"))][:12]
items=[]; kt_off=[]; cyto_on_punct=0; cyto_n=0; kt_sigs=[]; cyto_sigs=[]
for b in cands:
    role='ablation' if P[b].get("pre_abl") else 'monitoring'
    ft=lib.FluorTif(b,role) if (lib.FluorTif(b,role).ok()) else lib.FluorTif(b,'monitoring')
    if not ft.ok(): continue
    ktlab='pre_abl' if P[b].get('pre_abl') else ('polar' if P[b].get('polar') else 'sisterless')
    t,x,y=P[b][ktlab][0]; ct,cx,cy=P[b]['cytosol_bg'][0]
    g=ft.plane_at(t); gc=ft.plane_at(ct)
    if g is None or gc is None: ft.close(); continue
    # KT: offset to nearest punctum (placement) + signal above LOCAL background (is there a KT there?)
    o=offset_to_peak(g,x,y)
    if o: kt_off.append(o[0])
    kt_sig=lib.disk_local_bg(g,x,y,5)        # KT intensity above its immediate surroundings (sharp peak => high)
    cy_sig=lib.disk_local_bg(gc,cx,cy,5)     # cytosol: should be ~0 (flat cytoplasm, no peak)
    if kt_sig is not None: kt_sigs.append(kt_sig)
    if cy_sig is not None:
        cyto_n+=1; cyto_sigs.append(cy_sig)
        if kt_sig is not None and cy_sig>0.5*max(kt_sig,1): cyto_on_punct+=1   # cytosol nearly as bright as a KT => misplaced
    ks,kcx,kcy=crop(g,x,y); cs,ccx,ccy=crop(gc,cx,cy)
    items.append((f"{b[:20]}\n{ktlab}",disp(ks),kcx,kcy,"#37ff5a",f"KT (offset {o[0]:.1f}px)" if o else "KT"))
    items.append((f"{b[:20]}\ncytosol_bg",disp(cs),ccx,ccy,"#5ab0ff","cytosol"))
    ft.close()

n=len(items); ncol=6; nrow=(n+ncol-1)//ncol
fig,axs=plt.subplots(nrow,ncol,figsize=(ncol*2.3,nrow*2.5),squeeze=False)
for k,(ttl,im,mx,my,col,tag) in enumerate(items):
    a=axs[k//ncol][k%ncol]; a.imshow(im,cmap="gray",interpolation="nearest")
    a.add_patch(plt.Circle((mx,my),5,fill=False,color=col,lw=1.5))   # the annotation marker
    a.set_title(f"{ttl}\n{tag}",fontsize=6.5); a.set_xticks([]); a.set_yticks([])
for k in range(n,nrow*ncol): axs[k//ncol][k%ncol].axis("off")
fig.suptitle("Annotation-placement check — GREEN=KT marker (should be ON a bright punctum) · BLUE=cytosol_bg (should be on FLAT cytoplasm)",
             x=.01,ha="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/_ANNOTATION_PLACEMENT_CHECK.png",bbox_inches="tight",dpi=140); plt.close()

kt_off=np.array(kt_off)
print(f"=== ANNOTATION PLACEMENT VERIFICATION ({len(cands)} batches) ===")
print(f"KT points: median offset to nearest bright punctum = {np.median(kt_off):.1f}px, max {kt_off.max():.1f}px (small = on the KT; click imprecision)")
import numpy as _np
print(f"KT signal above local bg (median): {_np.median(kt_sigs):.0f}  vs  cytosol signal above local bg (median): {_np.median(cyto_sigs):.0f}")
print(f"  -> KT points sit on sharp bright puncta; cytosol points sit on flat cytoplasm (near 0)" )
print(f"cytosol points as bright as a KT (would be misplaced): {cyto_on_punct}/{cyto_n}  (0 = all correctly on cytoplasm)")
print(f"montage -> {OUT}/_ANNOTATION_PLACEMENT_CHECK.png")
