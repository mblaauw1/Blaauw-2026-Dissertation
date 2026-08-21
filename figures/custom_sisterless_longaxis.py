"""Sisterless-KT position along the SPINDLE LONG AXIS vs behavior + metaphase time (user 2026-07-20).
Two long-axis definitions:
  (a) SHAPE: PCA long axis of the cell outline (shape defined only periodically -> carry the last outline forward
      until the next one), origin = outline centroid; position = |(KT-c)·d1|/ext1 (0=equator, 1=pole).
  (b) PERP-TO-PLATE: distance from the KT to the manual metaphase-plate line (µm) — the plate normal IS the long axis.
Compares the two, relates position to behavior (congress/polar), and (for polar KTs) to metaphase duration.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, glob, json, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def px(b):
    try: return float(gv(b,'Pixel Size (um)') or 0.062)
    except: return 0.062
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
def md(b):
    r=mr.get(b);
    if not r: return None
    d,ok=lib.mitotic_duration_min(r); return d if ok else None
def cell_frame(poly):
    c=poly.mean(0); _,_,vt=np.linalg.svd(poly-c); d1=vt[0]
    if d1[0]<0 or (d1[0]==0 and d1[1]<0): d1=-d1
    e1=np.abs((poly-c)@d1).max() or 1.0
    return c,d1,e1
# cell outlines by batch->frame
_co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); cx={c:i for i,c in enumerate(_co[0])}
outl=defaultdict(dict)
for r in _co[1:]:
    try:
        b=r[cx['batch']].strip(); p=np.array(json.loads(r[cx['points']]),float)
        if len(p)>=6: outl[b][int(r[cx['frame']])]=p
    except: pass
def carry_outline(b,f):
    o=outl.get(b,{})
    if not o: return None
    prev=[k for k in o if k<=f]
    return o[max(prev)] if prev else o[min(o)]   # carry last defined outline forward
sis=defaultdict(dict); plate=defaultdict(dict)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv")):
    if r.get('label')=='sisterless':
        try: sis[r['batch'].strip()][int(float(r['frame']))]=(float(r['x']),float(r['y']))
        except: pass
for r in csv.DictReader(open("/Volumes/4 MB/annotations/meta_plates.csv")):
    if r.get('label')=='meta_plate':
        try:
            p=json.loads(r.get('points','') or '[]')
            if len(p)>=2: plate[r['batch'].strip()][int(float(r['frame']))]=(p[0],p[-1])
        except: pass
beh={}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if r.get('behavior','').strip(): beh[r['batch'].strip()]=r['behavior'].strip()
def dist_to_plate(pt,line,ps):
    (ax,ay),(bx,by)=line; x,y=pt
    return abs((bx-ax)*(ay-y)-(ax-x)*(by-ay))/(np.hypot(bx-ax,by-ay) or 1.0)*ps
def nearest_plate(b,f):
    pl=plate.get(b,{});
    if not pl: return None
    nf=min(pl,key=lambda k:abs(k-f)); return pl[nf] if abs(nf-f)<=3 else None

# per-KT: mean position under both definitions (over the metaphase phase = all tracked frames)
rows=[]
for b in sis:
    if nsis(b)!=1 or b not in beh: continue
    frames=sorted(sis[b]); ps=px(b)
    if len(frames)<8: continue
    shape_pos=[]; plate_dist=[]
    for f in frames:
        pt=np.array(sis[b][f])
        o=carry_outline(b,f)
        if o is not None:
            c,d1,e1=cell_frame(o); shape_pos.append(abs(float((pt-c)@d1/e1)))
        ln=nearest_plate(b,f)
        if ln is not None: plate_dist.append(dist_to_plate(sis[b][f],ln,ps))
    rows.append(dict(b=b,beh=beh[b],
                     shape=(np.median(shape_pos) if shape_pos else None),
                     plate=(np.median(plate_dist) if plate_dist else None),
                     dur=md(b)))
print(f"{len(rows)} single-ablation KTs; with shape-axis: {sum(1 for r in rows if r['shape'] is not None)}, with plate-dist: {sum(1 for r in rows if r['plate'] is not None)}")

CATS=[("at_plate","at plate","#1b7837"),("congressed","congressed","#2166ac"),("noncongression","stayed polar","#762a83")]
fig,axs=plt.subplots(1,3,figsize=(15.5,5.0))
def boxby(ax,key,ylab,title):
    for i,(bh,lab,col) in enumerate(CATS):
        v=[r[key] for r in rows if r['beh']==bh and r[key] is not None]
        if not v: continue
        x=i+1; ax.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.25,edgecolor=col),medianprops=dict(color=col,lw=2),showfliers=False)
        jit=(np.random.RandomState(i).rand(len(v))-.5)*.28; ax.scatter(np.full(len(v),x)+jit,v,s=28,color=col,alpha=.75,edgecolor="white",lw=.3)
        ax.text(x,np.median(v),f"  {np.median(v):.2f}\n  n={len(v)}",ha="left",va="center",fontsize=8,color=col)
    # at_plate/congressed vs polar test
    a=[r[key] for r in rows if r['beh'] in('at_plate','congressed') and r[key] is not None]; p=[r[key] for r in rows if r['beh']=='noncongression' and r[key] is not None]
    u=stats.mannwhitneyu(a,p) if len(a)>=3 and len(p)>=3 else None
    ax.set_xticks([1,2,3]); ax.set_xticklabels([c[1] for c in CATS],fontsize=9); ax.set_ylabel(ylab)
    ax.set_title(title+(f"\nreached-plate vs polar: MWU p={u.pvalue:.2g}" if u else ""),fontsize=10)
boxby(axs[0],'shape',"|position| along shape long axis\n(0=equator, 1=pole)","(a) Long axis = cell SHAPE (PCA, carried over)")
boxby(axs[1],'plate',"median distance to plate (µm)","(b) Long axis = PERP-TO-PLATE (plate distance)")
# panel C: polar KTs — position vs metaphase duration
pol=[(r['plate'],r['dur']) for r in rows if r['beh']=="noncongression" and r['plate'] is not None and r['dur'] is not None]
if len(pol)>=4:
    X=[a for a,_ in pol]; Y=[b for _,b in pol]; axs[2].scatter(X,Y,s=44,color="#762a83",alpha=.8,edgecolor="white",lw=.4)
    m,bb=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); axs[2].plot(xr,m*xr+bb,"-",color="#222",lw=1.6); rho,p=stats.spearmanr(X,Y)
    axs[2].set_title(f"(c) Polar KTs: plate-distance vs metaphase time\nρ={rho:.2f}, p={p:.2g}, N={len(X)}",fontsize=10)
else: axs[2].set_title("(c) Polar KTs vs metaphase time (too few)",fontsize=10)
axs[2].set_xlabel("median distance to plate (µm)"); axs[2].set_ylabel("metaphase duration (min)")
fig.suptitle("#MOVE-5  Sisterless-KT position along spindle long axis vs behavior (single-ablation, manual)",fontweight="bold",fontsize=11,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig(f"{OUT}/G4_sisterless_longaxis_position.png",bbox_inches="tight",dpi=130); plt.savefig(f"{PDF}/G4_sisterless_longaxis_position.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G4_sisterless_longaxis_position",["batch","shape_pos","plate_dist","behavior","dur"],[],{"source":"manual tracks + cell_outlines","N":len(rows)},SCRIPT,"Position along spindle long axis", fig=fig)
print("built G4_sisterless_longaxis_position (both long-axis definitions)")
