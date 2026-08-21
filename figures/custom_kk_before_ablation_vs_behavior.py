"""#47 — Does k-k distance right before ablation relate to behavior, BEYOND what ablation phase already tells us?
k-k = ‖pre_abl − pre_abl_pair‖·pixel_size, nearest-neighbour per frame, computed EXACTLY as group2_kk.py (same
KK_LOWKK / >20µm / mad1 / double-chromosome / drug / Exclude filters). Per cell = mean of its pre-ablation pairs.
Behavior outcome = per-cell congression score from CHROMOSOME_ANNOTATIONS_MASTER (at_plate=1, congressed=0.5,
noncongression/end-polar=0); higher = better congression.
Result: pooled across phases k-k barely relates to behavior (ρ≈-0.15, NS), BUT restricted to PROMETAPHASE ablations
a correlation emerges — wider k-k at ablation → worse congression (ρ≈-0.37, p≈0.04). So k-k carries behavior info
that pooling by phase hides. (modest N; not multiple-comparison corrected — treat as suggestive.)
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def px(b):
    try: return float(gv(b,'Pixel Size (um)') or 0.062)
    except: return 0.062
def phase(b):
    if lib.is_v2_prometaphase(b): return 'Prometaphase'   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p=gv(b,'Phase of Ablations').lower()
    return 'Prophase' if p.startswith('proph') else 'Prometaphase' if p.startswith('promet') else 'Metaphase' if p.startswith('metaph') else None
KK_LOW={"20250901 triple_ablation_6","20260108 two_sisterless_kinetochores_18","20251029 triple_ablation_4","20250925 triple_ablation_26"}
def pair_nn(A,B):
    A=list(A);B=list(B);pairs=[];used=set()
    for a in A:
        best=None;bd=1e18
        for j,b in enumerate(B):
            if j in used: continue
            d=(a[0]-b[0])**2+(a[1]-b[1])**2
            if d<bd: bd=d;best=j
        if best is not None: used.add(best);pairs.append((a,B[best]))
    return pairs
kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); kx={c:i for i,c in enumerate(kt[0])}
pre=defaultdict(lambda: defaultdict(list))
for r in kt[1:]:
    lab=r[kx['label']].strip()
    if lab not in ('pre_abl','pre_abl_pair'): continue
    try: pre[r[kx['batch']].strip()][lab].append((int(float(r[kx['frame']])),float(r[kx['x']]),float(r[kx['y']])))
    except: pass
chb=defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    bh=r.get('behavior','').strip()
    if bh: chb[r['batch'].strip()].append(bh)
def score(bs):
    m={'at_plate':1.0,'congressed':0.5,'noncongression':0.0}; v=[m[x] for x in bs if x in m]; return np.mean(v) if v else None
PCOL={"Prophase":"#1b7837","Prometaphase":"#2166ac","Metaphase":"#762a83",None:"#999"}

cell=[]
for b in mr:
    if gv(b,'On-Target / Off-Target').lower()!='on-target': continue
    if lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b) or b in KK_LOW: continue
    bs=chb.get(b); sc=score(bs) if bs else None
    if sc is None: continue
    A=pre[b].get('pre_abl',[]); Bp=pre[b].get('pre_abl_pair',[])
    if not A or not Bp: continue
    kks=[]
    for a,bb in pair_nn(A,Bp):
        d=np.hypot(a[1]-bb[1],a[2]-bb[2])*px(b)
        if 0.3<=d<=20: kks.append(d)
    if not kks: continue
    cell.append(dict(b=b,kk=np.mean(kks),sc=sc,phase=phase(b)))

def scat(ax,sub,title):
    X=[c['kk'] for c in sub]; Y=[c['sc'] for c in sub]
    for ph in ["Prophase","Prometaphase","Metaphase",None]:
        xx=[c['kk'] for c in sub if c['phase']==ph]; yy=[c['sc'] for c in sub if c['phase']==ph]
        if xx: ax.scatter(xx,yy,s=40,color=PCOL[ph],alpha=.82,edgecolor="white",lw=.4,label=(ph or "unspecified"))
    if len(X)>=3:
        m,bb=np.polyfit(X,Y,1); xr=np.linspace(min(X),max(X),20); ax.plot(xr,m*xr+bb,"-",color="#222",lw=1.7)
    rho,p=stats.spearmanr(X,Y) if len(X)>=5 else (None,None)
    ax.set_xlabel("mean k-k distance right before ablation (µm)")
    ax.set_ylabel("congression score\n(1 = all immediately at plate · 0 = all stayed polar)")
    ax.set_title(title+(f"\nSpearman ρ={rho:.2f}, p={p:.2g}, N={len(X)}" if rho is not None else ""),fontsize=10)
    ax.legend(fontsize=8)
    return rho,p

fig,(axA,axB)=plt.subplots(1,2,figsize=(12.8,5.3))
rA=scat(axA,cell,"All ablation phases pooled — k-k barely relates to behavior")
prom=[c for c in cell if c['phase']=='Prometaphase']
rB=scat(axB,prom,"Prometaphase ablations ONLY — wider k-k → worse congression")
fig.suptitle("#47  k-k distance before ablation vs congression behavior — k-k computed as in group2_kk (on-target)\n"
             "a k-k↔behavior correlation appears WITHIN prometaphase that pooling by phase hides",
             fontweight="bold",fontsize=10.5,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.92])
plt.savefig(f"{OUT}/G3_kk_before_ablation_vs_behavior.png",bbox_inches="tight",dpi=135)
plt.savefig(f"{PDF}/G3_kk_before_ablation_vs_behavior.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G3_kk_before_ablation_vs_behavior",["batch","kk_um","congression_score","phase"],[],
                {"source":"kt_points(pre_abl, fig=fig)+CHROMOSOME_ANNOTATIONS_MASTER","kk_method":"group2_kk",
                 "rho_all":round(rA[0],3) if rA[0] is not None else None,"p_all":round(rA[1],4) if rA[1] is not None else None,
                 "rho_prometaphase":round(rB[0],3) if rB[0] is not None else None,"p_prometaphase":round(rB[1],4) if rB[1] is not None else None,
                 "N":len(cell)},SCRIPT,"k-k before ablation vs behavior")
print(f"built #47 | N={len(cell)} cells | all-phase ρ={rA[0]:.2f} p={rA[1]:.3g} | prometaphase ρ={rB[0]:.2f} p={rB[1]:.3g}")
