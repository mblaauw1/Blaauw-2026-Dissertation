"""Cell-centroid movement during the METAPHASE->ANAPHASE window vs # sisterless kinetochores.

RECOVERED + CORRECTED 2026-07-16: the original (lost) heredoc measured centroid movement over
ANAPHASE->cytokinesis (`a-30 <= t <= cytokinesis`) — user flagged this was wrong; it should be the
metaphase-to-anaphase period. Window is now [Metaphase Start, Anaphase Onset]. Cohort membership is
lib.assign_cohorts() (which already excludes metaphase-ablation, 4-sisterless, drug, Exclude, mad1); an
explicit lib.plot_excluded() guard is added for belt-and-suspenders. Centroid from manual cell_outlines
(shoelace area-centroid), converted to µm via per-batch pixel size. Two metrics: centroid SPEED (path/min)
and NET displacement over the window. New filename (old 'anaphase_centroid_movement...' was mis-scoped)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, re, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass
OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
coh=lib.assign_cohorts(); b2={}
for k,lst in coh.items():
    for b,d in lst:
        if lib.plot_excluded(b): continue          # metaphase/4-sis/drug/excluded out (defensive; coh already drops them)
        b2.setdefault(b,k)
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def pt(b,c): return lib.parse_time(mr.get(b,{}).get(c,""))
def sis_of(k):
    if k=="unModified": return 0
    m=re.match(r"(\d)-Sister",k); return int(m.group(1)) if m else None
def area_centroid(pts):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]; cross=x*np.roll(y,-1)-np.roll(x,-1)*y; A=cross.sum()/2.0
    if abs(A)<1e-6: return p.mean(0)
    return np.array([((x+np.roll(x,-1))*cross).sum()/(6*A),((y+np.roll(y,-1))*cross).sum()/(6*A)])
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
ps={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: ps[b]=float(r[ix['pixel_size_um']])
    except Exception: ps.setdefault(b,0.062)
cen=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try:
        t=float(r[ix['t_sec']]); c=area_centroid(json.loads(r[ix['points']]))
        if c is None: continue
        px=ps.get(b,0.062); cen[b].append((t,c[0]*px,c[1]*px))
    except Exception: continue
recs=[]   # (sis, speed_um_per_min, net_disp_um, batch)
for b in b2:
    ms=pt(b,"Metaphase Start (s)"); a=pt(b,"Anaphase Onset (s)"); s=sis_of(b2[b])
    if ms is None or a is None or s is None or a<=ms: continue       # need a real metaphase->anaphase window
    tr=sorted(cen.get(b,[]))
    win=[p for p in tr if ms-1e-6<=p[0]<=a+1e-6]                     # METAPHASE START -> ANAPHASE ONSET
    if len(win)<2: continue
    pts=np.array([(x,y) for _,x,y in win]); ts=np.array([t for t,_,_ in win])
    path=np.sum(np.hypot(np.diff(pts[:,0]),np.diff(pts[:,1])))       # total path (µm)
    net=np.hypot(*(pts[-1]-pts[0]))                                  # net displacement (µm)
    dur=(ts[-1]-ts[0])/60.0
    if dur<=0: continue
    # USER 2026-08-05: "this only needs to include data for 1 sisterless and 3 sisterless, as in the
    # plot NF1". Drops the 0- and 2-sisterless groups (22 and 11 cells) so this matches NF1's cohorts.
    if int(s) not in (1, 3): continue
    recs.append((s, path/dur, net, b))
S=np.array([r[0] for r in recs]); SP=np.array([r[1] for r in recs]); ND=np.array([r[2] for r in recs])
print(f"N={len(recs)} cells (metaphase->anaphase window)")
rho,p=stats.spearmanr(S,SP); rho2,p2=stats.spearmanr(S,ND)
print(f"sisterless# vs centroid SPEED (µm/min): Spearman rho={rho:.2f} p={p:.2g}")
print(f"sisterless# vs NET displacement (µm):   Spearman rho={rho2:.2f} p={p2:.2g}")
for s in sorted(set(S.astype(int))):
    m=S==s; print(f"  {s}-sis (N={m.sum():2}): speed median={np.median(SP[m]):.2f} µm/min | net median={np.median(ND[m]):.2f} µm")
fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax,(vals,lab,rr,pp) in zip(axs,[(SP,"Centroid speed, metaphase to anaphase (µm/min)",rho,p),(ND,"Net centroid displacement, metaphase to anaphase (µm)",rho2,p2)]):
    # USER 2026-08-05: "you can shrink the x-axis now that youve made it so its only 2 groups, just use
    # the setup you use for NF1". Boxes were positioned at the literal sisterless numbers (1 and 3), which
    # left an empty slot at 2 and stretched the axis. Categorical positions 0/1 like _box2 in the NF set.
    groups=sorted(set(S.astype(int))); data_g=[vals[S==g] for g in groups]
    _pos=list(range(len(groups)))
    bp=ax.boxplot(data_g,positions=_pos,widths=.55,showfliers=False,patch_artist=True)
    for pa in bp['boxes']: pa.set_facecolor("#4a90d9"); pa.set_alpha(.35)
    for i,g in enumerate(groups):
        v=vals[S==g]; xj=np.random.default_rng(g).normal(i,0.07,len(v))
        ax.scatter(xj,v,s=26,color="#1f5c9e",alpha=.8,edgecolor="white",lw=.3,zorder=3)
    ax.set_xticks(_pos); ax.set_xticklabels([f"{g}-sisterless\n(n={(S==g).sum()})" for g in groups])
    ax.set_xlim(-0.6, len(groups)-0.4)
    # USER 2026-08-05: with only two groups (1 and 3) a fitted line through two x-values is decorative and
    # a Spearman on it is just a rank test between them. Report the Mann-Whitney directly instead.
    _g1=vals[S==1]; _g3=vals[S==3]
    if len(_g1)>=3 and len(_g3)>=3:
        _u,_pmw=stats.mannwhitneyu(_g1,_g3,alternative="two-sided")
        _st="***" if _pmw<1e-3 else "**" if _pmw<1e-2 else "*" if _pmw<.05 else "n.s."
        ax.text(.99,.99,f"1 vs 3: Mann-Whitney p={_pmw:.3g} {_st}",transform=ax.transAxes,
                ha="right",va="top",fontsize=8.5,color="#222")
    ax.set_xlabel("# Sisterless kinetochores"); ax.set_ylabel(lab)
    ax.set_title(f"{lab.split('(')[0].strip()}\nSpearman rho={rr:.2f}, p={pp:.2g}, N={len(vals)}",fontsize=10)
fig.suptitle("Cell-midpoint movement during METAPHASE to ANAPHASE vs # sisterless KTs",fontsize=12.5,y=1.01)
fig.tight_layout()
fp=f"{OUT}/centroid_movement_metaphase_to_anaphase_vs_sisterless.png"
fig.savefig(fp,dpi=140,bbox_inches="tight"); print("wrote",fp)
lib.record_plot("centroid_movement_metaphase_to_anaphase_vs_sisterless",
    ["batch","n_sisterless","centroid_speed_um_per_min","net_disp_um"],
    [[b,s,round(sp,3),round(nd,3)] for s,sp,nd,b in recs],
    {"type":"centroid movement vs #sisterless","window":"Metaphase Start -> Anaphase Onset","metric":"cell-outline area-centroid, µm","exclusion":"assign_cohorts + plot_excluded (metaphase/4-sis/drug/excluded out)"},
    __file__,"Cell-midpoint movement metaphase->anaphase vs #sisterless",
    source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])
