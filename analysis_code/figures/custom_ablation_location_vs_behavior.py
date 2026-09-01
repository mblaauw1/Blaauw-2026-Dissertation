"""#46 — Does the LOCATION of the sisterless KT at time of ablation relate to its behavior?
Location = midpoint of the pre_abl / pre_abl_pair marks (the sister pair right before ablation), normalized in the
cell's own frame EXACTLY as G4_lagging_position (group4_lagging_shape.py task I9): centroid of the nearest-frame
cell_outline = origin (0,0); PCA long axis = division axis. Two coordinates:
  radial = sqrt(a1²+a2²): 0 = cell centroid, 1 = cell boundary   (the 'distance from centroid' the user asked for)
  |a1|   = |(KT-c)·d1|/ext1: 0 = cell equator/plate, 1 = a spindle pole   (pole-axis position — plate vs polar)
Behavior = consolidated CHROMOSOME_MASTER (per-chromosome).

2026-08-03 REBUILD (feedback: "Include all on-target. Split into two plots.")
  - COHORT WIDENED: was restricted to single-sisterless (On-target AND '# Sisterless KTs'==1, N=35). Per her
    cohort rule (single on-target = On-target AND '# Sisterless KTs'==1, NOT the automated '#Unique Targets'
    column), "all on-target" = drop the ==1 restriction, keep On-target only -> N=61 (35 with nsis==1, 6 with
    nsis==2, 20 with nsis==3). The multi-KT chromosome-numbering ambiguity the ==1 restriction existed to avoid
    is a labeling problem for MASTER-level summaries, not for this plot: each row here already keys off a single
    pre_abl/pre_abl_pair mark pair (one physical KT-pair location) joined to one CHROMOSOME_MASTER behavior row,
    so widening does not introduce any many-to-one ambiguity in what gets plotted.
  - SPLIT INTO TWO PLOTS: the original was one figure, two panels (radial-from-centroid, pole-axis position),
    each panel showing a 3-way behavior breakdown (at_plate / congressed / noncongression) but only ONE stat
    test (at_plate vs the other two pooled as "ever-displaced"). That pooling conflates two different biological
    questions and only tests one of them. Chosen split = BY BEHAVIOUR OUTCOME (the obvious candidate, per her
    note), turning the single 3-way comparison into two clean, independently-testable binary comparisons, each
    its own 2-panel (radial / pole-axis) figure:
      Plot 1 (G3_ablation_location_vs_platefate)      : at_plate vs ever-displaced (congressed+noncongression)
                                                          -> does ablation-time location predict EVER leaving plate?
      Plot 2 (G3_ablation_location_vs_recongression)   : congressed vs noncongression, DISPLACED KTs only
                                                          -> among displaced KTs, does location predict RECOVERY?
    This is more informative than an arbitrary metric-based split (radial-plot / pole-axis-plot) because the two
    original panels are not independent hypotheses -- they are two readouts of the same displacement event -- so
    keeping them together per question (and splitting the QUESTION instead) is what actually separates two
    different comparisons that were previously smushed into one MWU p-value.
  - Old combined single-figure output backed up (non-destructively) to
    _retired_figs/pre_split_20260803/G3_ablation_location_vs_behavior.{png,pdf} before this rebuild.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, json, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def px(b):
    try: return float(gv(b,'Pixel Size (um)') or 0.062)
    except: return 0.062
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
KK_LOW={"20250901 triple_ablation_6","20260108 two_sisterless_kinetochores_18","20251029 triple_ablation_4","20250925 triple_ablation_26"}
def cell_frame(poly):   # identical to group4_lagging_shape.py I9
    c=poly.mean(0); _,_,vt=np.linalg.svd(poly-c); d1=vt[0]
    if d1[0]<0 or (d1[0]==0 and d1[1]<0): d1=-d1
    d2=np.array([-d1[1],d1[0]]); e1=np.abs((poly-c)@d1).max() or 1.0; e2=np.abs((poly-c)@d2).max() or 1.0
    return c,d1,d2,e1,e2
_co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); cx={c:i for i,c in enumerate(_co[0])}
outl=defaultdict(dict)
for r in _co[1:]:
    try:
        b=r[cx['batch']].strip(); p=np.array(json.loads(r[cx['points']]),float)
        if len(p)>=6: outl[b][int(r[cx['frame']])]=p
    except: pass
kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); kx={c:i for i,c in enumerate(kt[0])}
pre=defaultdict(lambda: defaultdict(list))
for r in kt[1:]:
    lab=r[kx['label']].strip()
    if lab not in ('pre_abl','pre_abl_pair'): continue
    try: pre[r[kx['batch']].strip()][lab].append((int(float(r[kx['frame']])),float(r[kx['x']]),float(r[kx['y']])))
    except: pass
chb=defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    if r.get('behavior','').strip(): chb[r['batch'].strip()].append(r['behavior'].strip())

rec=[]
n_single_sisterless=0
for b in mr:
    if gv(b,'On-Target / Off-Target').lower()!='on-target': continue   # ALL on-target (widened from nsis==1 only)
    if lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b) or b in KK_LOW: continue
    bh=chb.get(b)
    if not bh: continue
    A=pre[b].get('pre_abl',[]); Bp=pre[b].get('pre_abl_pair',[])
    if not A or not Bp or b not in outl: continue
    a=A[0]; bb=Bp[0]; fr=a[0]; mid=np.array([(a[1]+bb[1])/2,(a[2]+bb[2])/2])
    kk=np.hypot(a[1]-bb[1],a[2]-bb[2])*px(b)
    if kk>20 or kk<0.3: continue
    nf=min(outl[b],key=lambda f:abs(f-fr)); c,d1,d2,e1,e2=cell_frame(outl[b][nf])
    a1=abs(float((mid-c)@d1/e1)); a2=float((mid-c)@d2/e2); rad=float(np.hypot((mid-c)@d1/e1,a2))
    rec.append(dict(b=b,beh=bh[0],rad=rad,a1=a1,nsis=nsis(b)))
    if nsis(b)==1: n_single_sisterless+=1

N_ALL=len(rec)
N_SINGLE=n_single_sisterless
print(f"cohort widened: single-sisterless-only N={N_SINGLE}  ->  all on-target N={N_ALL}")

def two_panel(rec_sub,cats,fname,plotid,question,extra_caption):
    fig,(axA,axB)=plt.subplots(1,2,figsize=(12.4,5.4))
    def panel(ax,metric,ylab,title):
        for i,(k,lab,col) in enumerate(cats):
            v=[r[metric] for r in rec_sub if r['beh_grp']==k]
            if not v: continue
            x=i+1
            ax.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.22,edgecolor=col),
                       medianprops=dict(color=col,lw=2),whiskerprops=dict(color=col),capprops=dict(color=col),showfliers=False)
            jit=(np.random.RandomState(i).rand(len(v))-.5)*.28; ax.scatter(np.full(len(v),x)+jit,v,s=30,color=col,alpha=.8,edgecolor="white",lw=.3)
            ax.text(x,np.median(v),f"  {np.median(v):.2f}\n  n={len(v)}",ha="left",va="center",fontsize=8,color=col)
        g0=[r[metric] for r in rec_sub if r['beh_grp']==cats[0][0]]; g1=[r[metric] for r in rec_sub if r['beh_grp']==cats[1][0]]
        u=stats.mannwhitneyu(g0,g1) if (len(g0)>=3 and len(g1)>=3) else None
        ax.set_xticks([1,2]); ax.set_xticklabels([c[1] for c in cats],fontsize=9); ax.set_ylabel(ylab)
        ax.set_title(title+(f"\n{cats[0][1].splitlines()[0]} vs {cats[1][1].splitlines()[0]}: MWU p={u.pvalue:.2g}" if u else ""),fontsize=9.5)
        return u
    panel(axA,'rad',"radial distance from cell centroid\n(0 = centroid · 1 = cell boundary)","Distance from centroid at ablation")
    u_a1=panel(axB,'a1',"|position| along division axis\n(0 = cell equator/plate · 1 = spindle pole)","Pole-axis position at ablation")
    fig.suptitle(f"#46  {question} — ALL on-target (N={len(rec_sub)})\n"
                 f"normalized in the cell frame identically to G4_lagging_position (centroid origin, PCA division axis){extra_caption}",
                 fontweight="bold",fontsize=10.2,x=.01,ha="left")
    plt.tight_layout(rect=[0,0,1,0.86])
    plt.savefig(f"{OUT}/{fname}.png",bbox_inches="tight",dpi=135)
    plt.savefig(f"{PDF}/{fname}.pdf",bbox_inches="tight"); plt.close()
    lib.record_plot(plotid,["batch","behavior_group","radial","pole_axis_a1"],
                     [[r['b'],r['beh_grp'],r['rad'],r['a1']] for r in rec_sub],
                     {"source":"kt_points(pre_abl)+cell_outlines+CHROMOSOME_MASTER","N":len(rec_sub),
                      "cohort":"ALL on-target (widened from single-sisterless-only, was N=35)",
                      "method":"cell_frame same as G4_lagging_position",
                      "split_rationale":"split by behaviour outcome (see module docstring 2026-08-03)"},
                     SCRIPT,question)
    return u_a1

# ---- Plot 1: at_plate vs ever-displaced (does location predict EVER leaving the plate?) ----
# NOTE: build INDEPENDENT dict copies per plot (not shared references) -- rec1/rec2 both draw from the same
# underlying `rec` rows, and mutating a shared dict's 'beh_grp' in place would silently corrupt the other plot's
# grouping once both loops had run (caught during verification: diagnostic counts read 0 until this was fixed).
rec1=[dict(r, beh_grp=('at_plate' if r['beh']=='at_plate' else 'ever_displaced'))
      for r in rec if r['beh'] in('at_plate','congressed','noncongression')]
CATS1=[("at_plate","at plate\n(immediate)","#1b7837"),("ever_displaced","ever displaced\n(congressed + stayed polar)","#b2182b")]
u1=two_panel(rec1,CATS1,"G3_ablation_location_vs_platefate","G3_ablation_location_vs_platefate",
             "Sisterless-KT location at ablation vs EVER leaving the plate",
             "\nPlot 1/2: does location predict whether the KT ever left the metaphase plate?")

# ---- Plot 2: among displaced KTs, congressed (recovered) vs noncongression (stayed polar to anaphase) ----
rec2=[dict(r, beh_grp=r['beh']) for r in rec if r['beh'] in('congressed','noncongression')]
CATS2=[("congressed","displaced →\ncongressed (recovered)","#2166ac"),("noncongression","stayed polar\n(→ anaphase)","#762a83")]
u2=two_panel(rec2,CATS2,"G3_ablation_location_vs_recongression","G3_ablation_location_vs_recongression",
             "Sisterless-KT location at ablation vs RECOVERY among displaced KTs",
             "\nPlot 2/2: among displaced KTs only, does location predict recongression vs staying polar?")

print(f"built #46 (split x2) | cohort widened single-sisterless N={N_SINGLE} -> all on-target N={N_ALL}")
print(f"  Plot1 G3_ablation_location_vs_platefate      N={len(rec1)} (at_plate={sum(1 for r in rec1 if r['beh_grp']=='at_plate')}, "
      f"ever_displaced={sum(1 for r in rec1 if r['beh_grp']=='ever_displaced')})"
      + (f" pole-axis MWU p={u1.pvalue:.3g}" if u1 else ""))
print(f"  Plot2 G3_ablation_location_vs_recongression  N={len(rec2)} (congressed={sum(1 for r in rec2 if r['beh_grp']=='congressed')}, "
      f"noncongression={sum(1 for r in rec2 if r['beh_grp']=='noncongression')})"
      + (f" pole-axis MWU p={u2.pvalue:.3g}" if u2 else ""))
