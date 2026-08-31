"""K-K (inter-kinetochore) distance vs time from (prometaphase) ablation to metaphase onset (USER 2026-07-19).
CORRECTED 2026-07-19: k-k distance is COMPUTED from kt_points.csv pre_abl / pre_abl_pair point pairs (the same
source + method as group2_kk.py), NOT the sparse master 'KK_Dist (um)' column (only 16 filled). Per cell we take
the MEAN k-k across its ablated chromosomes ('on average'). x = abl->meta (min). Hypothesis: k-k grows toward
metaphase => negative rho. Exclusions mirror group2_kk.py (mad1, double-chromosome, KK_LOWKK, near-zero, >20um)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(r,c): return (r.get(c,"") or "").strip()
def pxsize(b):
    try: return float(mr.get(b,{}).get("Pixel Size (um)","") or 0.062)
    except Exception: return 0.062
_dbl=lib.double_chromosome_batches()
KK_LOWKK_EXCLUDE={"20250901 triple_ablation_6","20260108 two_sisterless_kinetochores_18",
                  "20251029 triple_ablation_4","20250925 triple_ablation_26"}
# --- compute per-batch KK from kt_points.csv (group2_kk.py method) ---
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
byb=defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if lib.is_mad1(b) or b in _dbl or b in KK_LOWKK_EXCLUDE: continue
    try: x=float(r[ix['x']]); y=float(r[ix['y']])
    except Exception: continue
    byb[b][r[ix['frame']]][r[ix['label']].strip()].append((x,y))
def pair_nn(A,B):
    A=list(A); B=list(B); pairs=[]; used=set()
    for a in A:
        best=None; bd=1e18
        for j,bb in enumerate(B):
            if j in used: continue
            d=(a[0]-bb[0])**2+(a[1]-bb[1])**2
            if d<bd: bd=d; best=j
        if best is not None: used.add(best); pairs.append((a,B[best]))
    return pairs
batch_kk=defaultdict(list)
for b,frames in byb.items():
    ps=pxsize(b)
    for fr,labs in frames.items():
        for a,bb in pair_nn(labs.get("pre_abl",[]), labs.get("pre_abl_pair",[])):
            d=np.hypot(a[0]-bb[0],a[1]-bb[1])*ps
            if d>20 or d<0.30: continue   # implausible / near-zero (per group2_kk review flags)
            batch_kk[b].append(d)
print(f"batches with a computed KK pair: {len(batch_kk)} | total pairs: {sum(len(v) for v in batch_kk.values())}")

# --- match with prometaphase-ablated timing ---
pts=[]
for b,ds in batch_kk.items():
    r=mr.get(b)
    if not r: continue
    if not (gv(r,"Phase of Ablations").lower().startswith("promet") or lib.is_v2_prometaphase(b)): continue
    if gv(r,"Exclude") in ("Yes","yes") or lib.excluded(b): continue
    am,src=lib.abl_to_meta_min(r,fallback_metastart=True)
    if am is None or src=="metastart" or not (0<=am<200): continue
    pts.append((b,am,float(np.mean(ds)),gv(r,"# Sisterless KTs") or "?",len(ds)))
print(f"prometaphase-ablated cells with KK + measured abl->meta (PLOTTED): {len(pts)}")

CMAP={"1":lib.PALETTE.get("1-Sister","#2e9e3f"),"2":"#d68f00","3":lib.PALETTE.get("3-Sister","#8e44ad"),"4":"#c0392b"}
x=np.array([p[1] for p in pts]); y=np.array([p[2] for p in pts])
fig,ax=plt.subplots(figsize=(6.8,5.3))
for p in pts: ax.scatter(p[1],p[2],color=CMAP.get(p[3],"#888"),s=48,alpha=.82,edgecolor="w",lw=.5,zorder=3)
if len(x)>=4:
    m,b0=np.polyfit(x,y,1); xr=np.array([x.min(),x.max()]); ax.plot(xr,m*xr+b0,"k--",lw=1.6,alpha=.75)
    rho,p=stats.spearmanr(x,y); r_,pp=stats.pearsonr(x,y)
    ax.text(.97,.97,f"N={len(x)} cells\nSpearman rho={rho:+.2f}, p={p:.2g}\nPearson r={r_:+.2f}, p={pp:.2g}\n(neg. rho = k-k grows toward metaphase)",
            transform=ax.transAxes,va="top",ha="right",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec=".6"))
for g in ("1","2","3","4"):
    if any(p[3]==g for p in pts): ax.scatter([],[],color=CMAP[g],label=f"{g}-sisterless")
ax.set_xlabel("Time from (prometaphase) ablation to metaphase onset (min)")
ax.set_ylabel("Mean K–K distance of ablated chromosome(s) (µm)")
ax.set_title("Does inter-kinetochore distance grow as the cell nears metaphase?\n(k-k computed from pre_abl/pre_abl_pair points · closer to metaphase = smaller x)")
ax.legend(fontsize=8,title="cell group"); fig.tight_layout()
import os
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT+"/illustrator",exist_ok=True)
fig.savefig(OUT+"/G3_kk_distance_vs_time_to_meta.png",dpi=150,bbox_inches="tight"); fig.savefig(OUT+"/illustrator/G3_kk_distance_vs_time_to_meta.svg"); plt.close(fig)
lib.record_plot("G3_kk_distance_vs_time_to_meta",["batch","abl_to_meta_min","mean_kk_um","n_sisterless","n_kk_pairs"],
    [[p[0],round(p[1],2),round(p[2],3),p[3],p[4]] for p in pts],
    {"type":"scatter","x":"abl->meta (min)","y":"mean KK (um)","kk_source":"kt_points.csv pre_abl/pre_abl_pair (group2_kk method)",
     "cohort":"prometaphase-ablated non-excl non-mad1 non-double-chromosome","hypothesis":"k-k grows toward metaphase => neg rho"},
    __file__,"K-K distance (computed from paired points) vs time-to-metaphase",
    source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/kt_points.csv"])
print("wrote G3_kk_distance_vs_time_to_meta")
