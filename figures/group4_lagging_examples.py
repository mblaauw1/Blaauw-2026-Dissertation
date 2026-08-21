"""lagging-chromosome EXAMPLE images (fills the placeholder).
Comments specify the representative frame per cell ('slide for lagging kinetochore = monitoring NN').
For each lagging KT we crop the 16-bit fluor TIF at that frame around the marked KT, display-scale it,
overlay the half-max shape outline, and label time-since-anaphase + length + aspect. Montage them."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, re, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from skimage import measure
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}

# representative frame per cell (from batch_meta notes). 'shows both' cells display both lagging KTs.
LAG_SLIDE={"20250409 ptk_yfpcdc20_1":32,"20250410 ptk_yfpcdc20_17":110,"20250411 ptk_yfpcdc20_11":108,
 "20250901 triple_ablation_11":218,"20250923 triple_ablation_collagen_25":61,"20250929 four_ablation_23":131,
 "20250930 four_ablation_59":76,"20251006 triple_ablation_8":57,"20251029 single_ablation_13":92,
 "20251029 triple_ablation_12":178}
ID_SPLITS={"20250901 triple_ablation_11":[("L1",411,427),("L2",428,446)],
 "20250929 four_ablation_23":[("L1",162,201),("L2",342,370)],
 "20251029 triple_ablation_12":[("L1",184,256),("L2",520,548)]}

rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
lag=defaultdict(list)
for r in rows[1:]:
    if r[ix['label']].strip()!='lagging' or lib.is_mad1(r[ix['batch']].strip()): continue
    try: lag[r[ix['batch']].strip()].append((int(r[ix['id']]),int(r[ix['frame']]),float(r[ix['t_sec']]),
                                              float(r[ix['x']]),float(r[ix['y']]),r[ix['nearest_event']].strip()))
    except: pass
def tana(ev,t,b):
    m=re.search(r"Anaphase\s*\(([+-]?\d+)\s*s\)",ev or "")
    if m: return float(m.group(1))
    a=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)","")); return (t-a) if a is not None else None
def tracks_for(b):
    sp=ID_SPLITS.get(b)
    if not sp: return {b:lag[b]}
    seeds={}
    for nm,lo,hi in sp:
        s=[(p[3],p[4]) for p in lag[b] if lo<=p[0]<=hi]
        if s: seeds[nm]=(np.mean([z[0] for z in s]),np.mean([z[1] for z in s]))
    out=defaultdict(list)
    for p in lag[b]: out[f"{b} · {min(seeds,key=lambda nm:(p[3]-seeds[nm][0])**2+(p[4]-seeds[nm][1])**2)}"].append(p)
    return out

def _pca_len(xs,ys):
    """major-axis extent (µm) and aspect from the pixel cloud."""
    P=np.column_stack([xs,ys]).astype(float); ctr=P.mean(0); _,_,vt=np.linalg.svd(P-ctr)
    p1=(P-ctr)@vt[0]; p2=(P-ctr)@vt[1]
    maj=float(p1.max()-p1.min()); mnr=float(max(p2.max()-p2.min(),1.0))
    return maj*0.062, maj/mnr

def shape_outline(sub,cx,cy):
    from skimage import morphology as _mp
    from skimage.filters import gaussian as _gauss
    bg=np.median(sub); yy,xx=np.ogrid[:sub.shape[0],:sub.shape[1]]; near=((xx-cx)**2+(yy-cy)**2)<=7*7
    subs=_gauss(sub,sigma=1.2,preserve_range=True)      # smooth -> smoother outline, recovers faint edges
    peak=sub[near].max() if near.any() else sub.max()
    sig=1.4826*np.median(np.abs(sub-bg)) or 1.0         # robust noise sigma (MAD)
    # LOOSER than before so faint KTs still get an outline: 0.30 of peak, floored at 1.8σ over background
    # (background is still excluded). SNR gate lowered so only truly signal-free crops are skipped.
    if peak-bg >= max(4,2.0*sig):
        thr=max(bg+0.30*(peak-bg), bg+1.8*sig)
        mask=subs>=thr                                  # segment on the smoothed image
        mask=_mp.closing(mask,_mp.disk(3))              # bridge intra-object gaps + smoother boundary
        mask=_mp.opening(mask,_mp.disk(1))              # drop isolated background speckle
        lbl=measure.label(mask)
        ci,cj=int(round(cy)),int(round(cx)); comp=lbl[ci,cj] if (0<=ci<lbl.shape[0] and 0<=cj<lbl.shape[1]) else 0
        if comp==0 and lbl.max():
            ys,xs=np.nonzero(lbl); d=(xs-cx)**2+(ys-cy)**2; comp=lbl[ys[d.argmin()],xs[d.argmin()]]
        if comp:
            sel=(lbl==comp)
            # MERGE broken pieces of ONE stretched lagging chromosome: union any other component whose pixels
            # come within ~6px of the clicked component (a stretched KT often reads as 2 split objects).
            grown=_mp.dilation(sel,_mp.disk(6))
            for tl in set(lbl[grown & (lbl>0)]) - {0,comp}: sel = sel | (lbl==tl)
            ys,xs=np.nonzero(sel)
            if len(ys)>=5:
                lenum,asp=_pca_len(xs,ys)
                sel_draw=_gauss(sel.astype(float),sigma=1.5)   # smoother red contour at level 0.5
                return sel_draw, lenum, asp
    # FALLBACK: guarantee an outline even for very faint objects (top-row crops) — threshold a central disk
    # at a modest percentile above background so every crop gets a (smoothed) contour; background excluded.
    cdisk=((xx-cx)**2+(yy-cy)**2)<=13*13
    lo=np.percentile(subs[cdisk],62)
    sel=(subs>=max(lo,bg+1.0*sig)) & cdisk
    sel=_mp.closing(sel,_mp.disk(2)); sel=_mp.opening(sel,_mp.disk(1))
    ys,xs=np.nonzero(sel)
    if len(ys)<5: return None,None,None
    lenum,asp=_pca_len(xs,ys)
    sel_draw=_gauss(sel.astype(float),sigma=1.5)
    return sel_draw, lenum, asp

# collect example crops
items=[]   # (title, crop_disp, outline, t_ana)
for b in sorted(LAG_SLIDE):
    if b not in lag: continue
    ft=lib.FluorTif(b,'monitoring')
    if not ft.ok(): print(f"  skip {b}: no fluor TIF"); continue
    NN=LAG_SLIDE[b]
    for key,pts in tracks_for(b).items():
        # the annotation in this track nearest the noted frame
        p=min(pts,key=lambda p:abs(p[1]-NN))
        pid,fr,t,x,y,ev=p; g=ft.plane_by_frame(fr)   # map by FRAME (ground-truth), not t_sec (shifted)
        if g is None: continue
        W=34; h,w=g.shape; x0,x1=max(0,int(x)-W),min(w,int(x)+W); y0,y1=max(0,int(y)-W),min(h,int(y)+W)
        sub=g[y0:y1,x0:x1].astype(float)
        if sub.size<100: continue
        cx,cy=x-x0,y-y0; outline,lenum,asp=shape_outline(sub,cx,cy)
        lo,hi=np.percentile(sub,[20,99.7]); disp=np.clip((sub-lo)/(hi-lo+1e-6),0,1)
        ta=tana(ev,t,b); short=key.replace(b,'').strip(' ·') or ''
        ttl=f"{b[:22]}{(' '+short) if short else ''}\nt+{ta/60:.1f}min" + (f" · {lenum:.2f}µm a{asp:.1f}" if lenum else "")
        items.append((ttl,disp,outline,(cx,cy),b))
    ft.close()

n=len(items); ncol=4; nrow=(n+ncol-1)//ncol; barpx=2.0/0.062   # 2 µm scale bar
def build(show_outline,fname,note):
    fig,axs=plt.subplots(nrow,ncol,figsize=(ncol*3.0,nrow*3.2),squeeze=False)
    for k,(ttl,disp,outline,(cx,cy),b) in enumerate(items):
        a=axs[k//ncol][k%ncol]; a.imshow(disp,cmap="gray",interpolation="nearest")
        if show_outline and outline is not None:
            a.contour(outline,levels=[0.5],colors="#ff3b3b",linewidths=1.1)
        lib.mark_excluded_ax(a,b,ttl,fontsize=7.2); a.set_xticks([]); a.set_yticks([])   # mark Exclude/drug
        a.plot([3,3+barpx],[disp.shape[0]-5,disp.shape[0]-5],color="white",lw=2.5)
        a.text(3+barpx/2,disp.shape[0]-7,"2 µm",color="white",fontsize=6.5,ha="center",va="bottom")   # labelled bar
    for k in range(n,nrow*ncol): axs[k//ncol][k%ncol].axis("off")
    fig.suptitle(f"Lagging-chromosome examples (16-bit fluor TIF; {note}; white bar = 2µm) — {n} lagging KTs at noted frames",
                 x=.01,ha="left",fontweight="bold",fontsize=11)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight",dpi=130); plt.close()
build(False,"G4_lagging_examples.png","no outline")
build(True,"G4_lagging_examples_outlined.png","red = half-max shape outline, broken pieces merged")
print(f"lagging examples: {n} crops -> G4_lagging_examples.png + _outlined.png")
