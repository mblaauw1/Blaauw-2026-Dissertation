"""IMPROVED automatic lagging-KT shape measurement (USER 2026-07-17).
Seed-guided: each manual cross (annotations/lagging_lengths.csv) gives the APPROX location of a kinetochore.
At that location we segment the actual fluorescent object in the cropped fluor TIF and measure its
true extent by PCA projection (NOT a fixed cap — lagging KTs reach 6um+), giving length/width/aspect/area.
Lagging-vs-control identity is taken from the manual marks (longest mark in the frame = lagging), same as
the manual plot; we then report the AUTO shape for each. Also validates auto length vs manual length.
Keeps the manual plot (G4_lagging_vs_control_length_over_time) untouched."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, glob, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
import tifffile, scipy.ndimage as ndi
import lib
try: lib.apply_style()
except Exception: pass
PX=0.062; HALF=95   # ~11.8um analysis window (generous for 6um+ stretched KTs)

def extent_um(pts):
    p=np.array(pts,float)
    if len(p)<2: return 0.0
    d=0.0
    for i in range(len(p)):
        dd=np.hypot(p[:,0]-p[i,0],p[:,1]-p[i,1]).max()
        if dd>d: d=dd
    return d*PX
def centroid(pts): p=np.array(pts,float); return p.mean(axis=0)
def pair_marks(marks):
    cs=[centroid(m['pts']) for m in marks]; used=set(); crosses=[]; order=[]
    for i in range(len(marks)):
        for j in range(i+1,len(marks)): order.append((np.hypot(*(cs[i]-cs[j])),i,j))
    order.sort()
    for d,i,j in order:
        if i in used or j in used: continue
        used.add(i); used.add(j); crosses.append([marks[i],marks[j]])
    for i in range(len(marks)):
        if i not in used: crosses.append([marks[i]])
    return crosses
def mark_axis(pts):
    p=np.array(pts,float); c=p.mean(0); cc=p-c
    if len(cc)<2: return np.array([1.0,0.0])
    ev,evec=np.linalg.eigh(cc.T@cc); v=evec[:,-1]; return v/ (np.hypot(*v)+1e-9)
def _run_through_center(prof, thr, ci):
    above=prof>=thr
    if not above[ci]:
        idxs=np.where(above)[0]
        if len(idxs)==0: return None
        ci=int(idxs[np.abs(idxs-ci).argmin()])
        if abs(ci-len(prof)//2) > (25/0.5): return None   # nearest object >25px from seed
    l=ci
    while l>0 and above[l-1]: l-=1
    r=ci
    while r<len(above)-1 and above[r+1]: r+=1
    return l,r
def measure(plane, seed, axis=None, exclude=None):
    """Low-SNR safe: Gaussian-smooth the window to pull the diffuse stretched KT out of the pixel noise,
    segment the blob at the seed, measure length = extent along its own major axis (PCA projection).
    `exclude` = other kinetochores' seeds to blank out (prevents grabbing the nearby paired KT)."""
    x0,y0=int(round(seed[0])),int(round(seed[1])); H,W=plane.shape
    xa,xb=max(0,x0-HALF),min(W,x0+HALF); ya,yb=max(0,y0-HALF),min(H,y0+HALF)
    raw=plane[ya:yb,xa:xb].astype(float).copy()
    if raw.size<25: return None
    # blank a disk around each other-KT seed so the segmentation can't merge with it
    if exclude:
        yy,xx=np.ogrid[:raw.shape[0],:raw.shape[1]]
        bgv=np.percentile(raw,30)
        for ex in exclude:
            ex_x,ex_y=ex[0]-xa,ex[1]-ya
            # only blank if it's not essentially the same point as this seed
            if (ex_x-(x0-xa))**2+(ex_y-(y0-ya))**2 < 10**2: continue
            raw[((yy-ex_y)**2+(xx-ex_x)**2) < 14**2] = bgv
    sm=ndi.gaussian_filter(raw, 2.0)
    sy,sx=y0-ya,x0-xa
    bg=np.percentile(sm,30); lo=sm<np.percentile(sm,55)
    noise=(sm[lo].std() if lo.any() else sm.std())+1e-9
    if axis is None: axis=np.array([1.0,0.0])
    STEP=0.5; ts=np.arange(-HALF,HALF+STEP,STEP)
    # length: 1D profile ALONG the manual axis on the smoothed image, threshold near the noise floor.
    prof=ndi.map_coordinates(sm,[sy+ts*axis[1], sx+ts*axis[0]],order=1,mode='nearest')
    peak=float(prof.max())
    if peak-bg < 4*noise: return None
    thr=bg + max(3.0*noise, 0.15*(peak-bg))   # noise-floor captures dim tail; peak-frac caps runaway
    run=_run_through_center(prof,thr,len(ts)//2)
    if run is None: return None
    l,r=run; length=float(ts[r]-ts[l])*PX
    # width: perpendicular profile at the run midpoint
    perp=np.array([-axis[1],axis[0]]); mid=(l+r)//2
    cx=sx+ts[mid]*axis[0]; cy=sy+ts[mid]*axis[1]
    wt=np.arange(-40,40+STEP,STEP)
    wp=ndi.map_coordinates(sm,[cy+wt*perp[1], cx+wt*perp[0]],order=1,mode='nearest')
    wthr=np.percentile(wp,30)+max(3.0*noise,0.15*(wp.max()-np.percentile(wp,30)))
    wrun=_run_through_center(wp,wthr,len(wt)//2)
    width=float(wt[wrun[1]]-wt[wrun[0]])*PX if wrun else PX
    # A width at or below ONE PIXEL is not a measurement - the perpendicular profile collapsed, so the
    # object has no resolvable width and length/width is meaningless. Unguarded this produced
    # aspect = 1.364/0 = 1,364,000 on 20250901 triple_ablation_11 and a band of ~100-110 wherever the
    # width landed on exactly one pixel (0.062 um), i.e. max/p95 = 66,781x on the plot (found 2026-07-29).
    # Report the shape as unmeasurable (nan) rather than emit a number that is really a divide-by-zero.
    if not np.isfinite(width) or width < PX*1.5:
        return dict(length=length,width=float("nan"),aspect=float("nan"),area=float("nan"))
    return dict(length=length,width=width,aspect=length/width,area=length*width)

# load manual marks per cell/frame
rows=[r for r in csv.DictReader(open("/Volumes/4 MB/annotations/lagging_lengths.csv")) if "lag" in (r.get("type") or "").lower()]
by=defaultdict(lambda: defaultdict(list))
for r in rows:
    try: pts=json.loads(r["points"])
    except Exception: continue
    _b=(r.get("batch") or "").strip()
    # USER 2026-08-10: standing cohort exclusion (prophase / drug / metaphase-abl / 4-sis / Mad1).
    if lib.plot_excluded(_b) or lib.is_mad1(_b): continue
    by[_b][r.get("frame")].append({"pts":pts,"t":float(r.get("t_sec") or 0)})

records=[]   # cell,t,role,auto_length,auto_width,auto_aspect,auto_area,manual_length
for cell in sorted(by):
    dirs=glob.glob(f"/Volumes/4 MB/pipeline_session_output/*/{cell}")
    if not dirs: print("NO DIR",cell); continue
    d=dirs[0]
    fj=json.load(open(glob.glob(d+"/*frames.json")[0]))
    mon=[f for f in fj["frames"] if f.get("role")=="monitoring" and f.get("fluor_tif_idx") is not None]
    mts=np.array([f["t_sec"] for f in mon]); midx=[f["fluor_tif_idx"] for f in mon]
    tif=tifffile.TiffFile(glob.glob(d+"/*Fluor_Cropped.tif")[0])
    plane_cache={}
    def get_plane(pi):
        if pi not in plane_cache: plane_cache[pi]=tif.pages[pi].asarray()
        return plane_cache[pi]
    nmark=0
    for fr,marks in by[cell].items():
        crosses=pair_marks(marks)
        man=[max(extent_um(m['pts']) for m in cr) for cr in crosses]   # manual length per cross
        seeds=[np.mean([centroid(m['pts']) for m in cr],axis=0) for cr in crosses]
        axes=[mark_axis(max(cr,key=lambda m:extent_um(m['pts']))['pts']) for cr in crosses]  # longer mark's axis
        t=marks[0]['t']
        # map to fluor plane by nearest t_sec
        pi=midx[int(np.abs(mts-t).argmin())]
        plane=get_plane(pi)
        auto=[measure(plane,seeds[k],axes[k],exclude=[seeds[j] for j in range(len(crosses)) if j!=k]) for k in range(len(crosses))]
        # classify by manual length (longest = lagging)
        idx=sorted(range(len(man)),key=lambda k:-man[k])
        if len(man)==1: roles={idx[0]:"lagging"}
        elif len(man)==2: roles={idx[0]:"lagging",idx[1]:"control"}
        else: roles={**{k:"lagging" for k in idx[:-1]},idx[-1]:"control"}
        for k in range(len(crosses)):
            a=auto[k]
            if a is None: continue
            nmark+=1
            records.append((cell,t,roles[k],a["length"],a["width"],a["aspect"],a["area"],man[k]))
    tif.close()
    print(f"  {cell[:40]:40} auto-measured {nmark} crosses")
print("total auto records:",len(records))

COL={"lagging":"#d62728","control":"#1f77b4"}
fig,(ax,ax2)=plt.subplots(1,2,figsize=(13.5,5.6))
# left: auto length over time (aligned per cell to first observation)
cells=sorted(set(r[0] for r in records))
t0={c:min(r[1] for r in records if r[0]==c) for c in cells}
for cell in cells:
    for role in ("lagging","control"):
        pr=sorted([(r[1],r[3]) for r in records if r[0]==cell and r[2]==role])
        if not pr: continue
        ax.plot([(t-t0[cell])/60 for t,_ in pr],[v for _,v in pr],color=COL[role],alpha=.5,lw=1.2,marker="o",ms=3)
ax.plot([],[],color=COL["lagging"],lw=2,marker="o",ms=4,label=f"Lagging KT (n={sum(1 for r in records if r[2]=='lagging')})")
ax.plot([],[],color=COL["control"],lw=2,marker="o",ms=4,label=f"Control KT (n={sum(1 for r in records if r[2]=='control')})")
ax.set_xlabel("Time from first lagging observation (min)"); ax.set_ylabel("AUTO kinetochore length (µm, PCA major-axis extent)")
ax.set_title("Auto-segmented lagging vs control KT length over time"); ax.legend(fontsize=9); ax.set_ylim(bottom=0)
# right: validation auto vs manual
for role in ("lagging","control"):
    xs=[r[7] for r in records if r[2]==role]; ys=[r[3] for r in records if r[2]==role]
    ax2.scatter(xs,ys,s=16,color=COL[role],alpha=.5,label=role)
mx=max([r[7] for r in records]+[r[3] for r in records]+[1])
ax2.plot([0,mx],[0,mx],"k--",lw=1,alpha=.6,label="y=x")
allx=np.array([r[7] for r in records]); ally=np.array([r[3] for r in records])
if len(allx)>2:
    rr=np.corrcoef(allx,ally)[0,1]; ax2.text(0.03,0.97,f"Pearson r={rr:.2f} (n={len(allx)})",transform=ax2.transAxes,va="top",fontsize=9)
ax2.set_xlabel("Manual length (µm, longer cross mark)"); ax2.set_ylabel("AUTO length (µm)")
ax2.set_title("Validation: auto vs manual"); ax2.legend(fontsize=9)
fig.tight_layout()
OUTD="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(os.path.join(OUTD,"illustrator"),exist_ok=True)
nm="G4_lagging_auto_shape_v2"
fig.savefig(os.path.join(OUTD,nm+".png"),dpi=150); fig.savefig(os.path.join(OUTD,"illustrator",nm+".svg")); plt.close(fig)
lib.record_plot(nm,["cell","t_sec","role","auto_length_um","auto_width_um","auto_aspect","auto_area_um2","manual_length_um"],
    [[c,round(t,2),role,round(L,3),round(W,3),round(asp,3),round(ar,3),round(ml,3)] for c,t,role,L,W,asp,ar,ml in records],
    {"type":"auto lagging-KT shape (seed-guided segmentation + PCA)","cells":len(cells),
     "method":"segment fluor object at manual cross centroid; length=PCA major-axis extent (uncapped); window=±95px",
     "role_source":"lagging/control identity from manual marks (longest=lagging)"},
    __file__,"Auto lagging-KT shape (seed-guided) + validation vs manual",
    source=["/Volumes/4 MB/annotations/lagging_lengths.csv","/Volumes/4 MB/pipeline_session_output"])
print("wrote",nm)
