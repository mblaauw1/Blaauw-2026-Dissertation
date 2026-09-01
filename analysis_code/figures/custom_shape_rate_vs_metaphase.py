"""SHAPE-RATE vs METAPHASE-DURATION scatters (custom analysis, NOT in main deck) — see NOTES.md §13.
Question (user 2026-07-11): do cells that round up / lose cross-sectional area faster have shorter/longer
metaphases?  All-cohort, from manual `cell_outlines`: roundness = 4πA/P², area = shoelace·px²; per-cell linear
slope vs metaphase duration (= Anaphase Onset − Metaphase Start).

Two slope windows:
  * WHOLE-trace (start .. anaphase)        -> ALLcohorts_metaDur_vs_{arearate,roundingrate}.png  (+ bare metaDur_vs_*)
  * FIRST-HALF (NEB .. midpoint-to-anaphase) -> firsthalf_metaDur_vs_{arearate,roundingrate}.png
The first-half decoupling kills the rounding artifact (whole-trace ρ overlaps the metaphase window).

RECOVERED 2026-07-14 from the session transcript (the original was run as an inline heredoc and never saved
to a .py, violating the save-the-generator protocol). CONSOLIDATED the two heredocs (ALLcohorts + firsthalf)
and FIXED the exclusion filter: was `lib.excluded` (REVIEW_EXCLUDE only) -> now `lib.plot_excluded` so drugged
+ Exclude=Yes batches (e.g. 20260113 ..._18/_19) are dropped from these quantitative scatters, per the standing
rule. Provenance is now recorded via lib.record_plot (data CSV + code/ archive)."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
from matplotlib.lines import Line2D
import lib
try: lib.apply_style()
except Exception: pass

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
SCRIPT=__file__

# ---- cohort set (exactly as group1_roundness.py) -- FIX: plot_excluded drops drug + Exclude=Yes + REVIEW_EXCLUDE
coh=lib.assign_cohorts(); b2={}
for k,lst in coh.items():
    for b,d in lst:
        if lib.plot_excluded(b): continue
        b2.setdefault(b,k)
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}

def pt(b,c): return lib.parse_time(mr.get(b,{}).get(c,""))
def m_(b,c):
    v=pt(b,c); return v/60.0 if v is not None else None
def ana_min(b): return m_(b,"Anaphase Onset (s)")
def meta_dur(b):
    a=pt(b,"Anaphase Onset (s)"); m=pt(b,"Metaphase Start (s)")
    return (a-m)/60.0 if (a is not None and m is not None) else None
def sis(b):
    v=(mr.get(b,{}).get("# Sisterless KTs","") or "").strip()
    try: return int(float(v))
    except Exception: return ""
def pr(p):
    p=np.array(p,float); x,y=p[:,0],p[:,1]; Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0])))); v=4*np.pi*Ar/per**2 if per else None
    return v if (v is not None and 0<v<=1.2) else None
def pa(p,px):
    p=np.array(p,float); x,y=p[:,0],p[:,1]; a=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))*px*px
    return a if 0<a<=5000 else None

rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
ps={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: ps[b]=float(r[ix['pixel_size_um']])
    except Exception: ps.setdefault(b,0.062)
R=defaultdict(list); Aa=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try: t=float(r[ix['t_sec']])/60.0; p=json.loads(r[ix['points']])
    except Exception: continue
    v=pr(p); w=pa(p,ps.get(b,0.062))
    if v is not None: R[b].append((t,v))
    if w is not None: Aa[b].append((t,w))

# ---- WHOLE-trace slope (start .. anaphase)
def slope_whole(tr,b):
    a=ana_min(b); tt=[(t,v) for t,v in sorted(tr) if a is None or t<=a+1e-6]
    if len(tt)<3: return None
    x=np.array([q[0] for q in tt]); y=np.array([q[1] for q in tt])
    return float(np.polyfit(x,y,1)[0]) if x.max()-x.min()>1e-6 else None

# ---- FIRST-HALF slope (NEB .. midpoint of NEB->anaphase; first-frame fallback if no NEB)
neb_used=0; fb_used=0
def window(b):
    global neb_used,fb_used
    end=m_(b,"Anaphase Onset (s)")
    if end is None: return None
    neb=m_(b,"NEB Time (s)")
    allt=[t for t,_ in R.get(b,[])]+[t for t,_ in Aa.get(b,[])]
    if not allt: return None
    if neb is not None and neb<end: start=neb; neb_used+=1
    else: start=min(allt); fb_used+=1
    if end<=start: return None
    return start, start+0.5*(end-start)
def slope_win(tr,win):
    if win is None: return None
    s,mid=win; tt=[(t,v) for t,v in sorted(tr) if s-1e-6<=t<=mid+1e-6]
    if len(tt)<3: return None
    x=np.array([q[0] for q in tt]); y=np.array([q[1] for q in tt])
    return float(np.polyfit(x,y,1)[0]) if x.max()-x.min()>1e-6 else None

recs_whole=[(b,k,slope_whole(R.get(b,[]),b),slope_whole(Aa.get(b,[]),b),meta_dur(b),sis(b)) for b,k in b2.items()]
recs_half =[]
for b,k in b2.items():
    w=window(b)
    recs_half.append((b,k,slope_win(R.get(b,[]),w),slope_win(Aa.get(b,[]),w),meta_dur(b),sis(b)))

def okey(k):
    order=["unModified","1-Sister","2-Sister","3-Sister","4-Sister","1-Sister Controls","2-Sister Controls","3-Sister Controls"]
    return order.index(k) if k in order else 99
def col(k): return lib.PALETTE.get(k,"#888")

def scatter(recs,idx,xlabel,fname,title,plot_id,caption):
    xs=[];ys=[];cs=[]
    for b,k,rs,as_,md,_s in recs:
        xv=(rs,as_)[idx]
        if xv is None or md is None: continue
        xs.append(xv);ys.append(md);cs.append(col(k))
    xs=np.array(xs);ys=np.array(ys); fig,ax=plt.subplots(figsize=(7.6,5.6))
    ax.scatter(xs,ys,c=cs,s=34,edgecolor="white",lw=.4,alpha=.85,zorder=3)
    rho=p=prr=pp=float("nan")
    if len(xs)>=3:
        m,c=np.polyfit(xs,ys,1); xx=np.linspace(xs.min(),xs.max(),50); ax.plot(xx,m*xx+c,color="#111",lw=2,ls="--",zorder=4)
        rho,p=stats.spearmanr(xs,ys); prr,pp=stats.pearsonr(xs,ys)
    ax.set_title(title+f"\nSpearman rho={rho:.2f} (p={p:.2g}) | Pearson r={prr:.2f} (p={pp:.2g}) | N={len(xs)}")
    ax.set_xlabel(xlabel); ax.set_ylabel("Metaphase duration (min)")
    ks=sorted(set(k for _,k,rs,as_,md,_s in recs if md is not None and (rs,as_)[idx] is not None),key=okey)
    ax.legend(handles=[Line2D([0],[0],marker='o',ls='',mfc=col(k),mec='white',label=lib.lbl(k).replace(chr(10)," ")) for k in ks],fontsize=7.5,loc="best",ncol=2)
    fig.tight_layout(); fig.savefig(f"{OUT}/{fname}",dpi=150); plt.close(fig)
    # provenance: one row per included cohort cell (blanks where a slope/duration is missing)
    csvrows=[[b,s,("" if rs is None else round(rs,5)),("" if as_ is None else round(as_,4)),("" if md is None else round(md,3))]
             for b,k,rs,as_,md,s in recs]
    lib.record_plot(plot_id,["batch","sisterless","rounding_slope_per_min","area_slope_um2_per_min","metaphase_duration_min"],
        csvrows,{"type":"shape-rate vs metaphase-duration scatter","window":("whole-trace" if recs is recs_whole else "first-half"),
                 "exclusion":"lib.plot_excluded (drug + Exclude=Yes + REVIEW_EXCLUDE dropped)","measure":"per-cell linear slope; roundness=4πA/P², area=shoelace·px²"},
        SCRIPT,caption,source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])
    print(f"wrote {fname}  (N={len(xs)}, rho={rho:.2f} p={p:.2g})")

# ALL cohorts (whole trace) — colored by cohort
scatter(recs_whole,0,"Rounding rate = roundness slope (/min); higher = rounds faster","ALLcohorts_metaDur_vs_roundingrate.png","Metaphase duration vs rounding rate — ALL cohorts","ALLcohorts_metaDur_vs_roundingrate","Metaphase duration vs rounding rate (all cohorts, whole trace)")
scatter(recs_whole,1,"Area-loss rate = area slope (um^2/min); more negative = faster loss","ALLcohorts_metaDur_vs_arearate.png","Metaphase duration vs area-loss rate — ALL cohorts","ALLcohorts_metaDur_vs_arearate","Metaphase duration vs area-loss rate (all cohorts, whole trace)")
# FIRST HALF of mitosis
scatter(recs_half,0,"First-half rounding rate = roundness slope (/min); higher = rounds faster","firsthalf_metaDur_vs_roundingrate.png","Metaphase duration vs FIRST-HALF rounding rate","firsthalf_metaDur_vs_roundingrate","Metaphase duration vs first-half rounding rate")
scatter(recs_half,1,"First-half area-loss rate = area slope (um^2/min); more negative = faster loss","firsthalf_metaDur_vs_arearate.png","Metaphase duration vs FIRST-HALF area-loss rate","firsthalf_metaDur_vs_arearate","Metaphase duration vs first-half area-loss rate")
# bare aliases (earliest naming; kept in sync = whole-trace)
scatter(recs_whole,0,"Rounding rate = roundness slope (/min); higher = rounds faster","metaDur_vs_roundingrate.png","Metaphase duration vs rounding rate","metaDur_vs_roundingrate","Metaphase duration vs rounding rate (whole trace)")
scatter(recs_whole,1,"Area-loss rate = area slope (um^2/min); more negative = faster loss","metaDur_vs_arearate.png","Metaphase duration vs area-loss rate","metaDur_vs_arearate","Metaphase duration vs area-loss rate (whole trace)")

print(f"cells in cohorts (post plot_excluded): {len(b2)} | first-half window: NEB used={neb_used}, first-frame fallback={fb_used}")
