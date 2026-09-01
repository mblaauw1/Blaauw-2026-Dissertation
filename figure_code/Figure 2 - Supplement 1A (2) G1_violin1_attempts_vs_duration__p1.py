"""Violin 1, statistical grid, survival, roundness traces."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, numpy as np, matplotlib.pyplot as plt
from scipy import stats
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT=__file__
# cohort membership = lib.assign_cohorts() (Exclude/drug/mad1/double-chromosome filtered + IQR screened).
# Explicit hec1 guard per 2026-07-06 feedback ("not drug treated, mad1, or hec1"); no-op today (all hec1
# batches also carry 'mad1' and are already excluded) but keeps Violin1/Violin2 membership identical + safe.
coh={k:[(b,v) for b,v in lst if "hec1" not in b.lower()] for k,lst in lib.assign_cohorts().items()}
batch2coh={}
for k,lst in coh.items():
    for b,_ in lst: batch2coh.setdefault(b,k)

# ---------- Violin 1: ablation attempts vs duration ----------
# ITEM 3 (2026-07-06): Violin1's N must equal Violin2's (identical lib.assign_cohorts() membership).
# The only reason they differed was a handful of cohort members with a BLANK '# Unique Targets' in the
# master, which the old code dropped (no x-position). Recover a target count for those from the PAS-derived
# frames.json 'ablation_events_local' (cluster events within 18px ~1.1um) so every cohort member is plotted
# and N matches Violin2 exactly. Then fit each group with a linear trendline.
from scipy.stats import linregress as _linreg, spearmanr as _spear
import json as _json, os as _os
data,_=lib.load_master_plots()
mrec={r["Batch Name"]:r for r in data}
def _recover_targets(b):
    dp=mrec.get(b,{}).get("Drive Path",""); fj=_os.path.join(dp,f"{b}_frames.json")
    if not (dp and _os.path.isfile(fj)): return None
    try: evs=_json.load(open(fj)).get("ablation_events_local",[]) or []
    except Exception: return None
    cents=[]
    for e in evs:
        x,y=e.get("x_px"),e.get("y_px")
        if x is None: continue
        if not any((cx-x)**2+(cy-y)**2<=18*18 for cx,cy in cents): cents.append((x,y))
    return len(cents) or None
_TCACHE={}
def targ(b):
    if b in _TCACHE: return _TCACHE[b]
    nt=mrec.get(b,{}).get("# Unique Targets","")
    if nt.isdigit(): t=int(nt)
    else:
        t=_recover_targets(b)
        if t is not None:
            lib.log_review("violin1:#targets",b,t,"master '# Unique Targets' blank — recovered from frames.json ablation_events_local (18px cluster) so N matches Violin2")
    _TCACHE[b]=t; return t
fig,axes=plt.subplots(1,2,figsize=(11,4.6),sharey=True)
_wg={}   # USER 2026-07-16: within-group #targets-vs-duration significance (all n.s.)
for ax,(title,groups) in zip(axes,[("Experimental (on-target)",["1-Sister","2-Sister","3-Sister"]),
                                    ("Off-target",["Off-Target/Control"])]):
    for g in groups:
        xs=[];ys=[]
        for b,d in coh[g]:
            t=targ(b)
            if t is None:
                lib.log_review("violin1:#targets",b,"","no target count (master blank + no frames.json) — not plotted"); continue
            if t>25: lib.log_review("violin1:#targets",b,t,"extreme attempt count (>25) — excluded"); continue
            xs.append(t); ys.append(d)
        xs=np.array(xs,float); ys=np.array(ys,float)
        if len(xs)>=4: _r,_p=_spear(xs,ys); _wg[g]=(_r,_p,len(xs))
        # marker size raised 20 -> 55 (user 2026-08-04: points were hard to see)
        ax.scatter(xs+np.random.RandomState(1).rand(len(xs))*0.3-0.15,ys,s=55,
                   color=lib.PALETTE[g],alpha=0.85,edgecolor="white",linewidth=0.5,label=f"{lib.lbl(g).replace(chr(10),chr(32))} (N={len(xs)})")
        # per-group linear trendlines REMOVED 2026-07-10 (user): show scatter/points only, no fitted trend line.
    ax.set_title(title,fontsize=11); ax.set_xlabel("# ablation targets placed"); ax.legend(fontsize=8)
axes[0].set_ylabel("Metaphase duration (min)")
fig.suptitle("Violin 1 — Ablation attempts vs metaphase duration",x=0.01,ha="left",fontweight="bold")
_wgtxt="No significant within-group trend of # targets vs metaphase duration — Spearman:  "+"   ".join(f"{lib.lbl(g).replace(chr(10),chr(32))} rho={r:+.2f}, p={p:.2f} (n.s.)" for g,(r,p,n) in _wg.items())
fig.text(0.005,0.004,_wgtxt,fontsize=6.5,color="#333",ha="left",va="bottom")
plt.tight_layout(); plt.savefig(f"{OUT}/G1_violin1_attempts_vs_duration.png",bbox_inches="tight"); plt.close()
_r1=[[b,g,targ(b),round(d,3)] for g in ["1-Sister","2-Sister","3-Sister","Off-Target/Control"] for b,d in coh[g] if targ(b) is not None and targ(b)<=25]
lib.record_plot("G1_violin1_attempts_vs_duration",["batch","cohort","n_targets","mitotic_duration_min"],_r1,
  {"type":"scatter (2 panels: experimental / off-target)","x":"# Unique Targets","outlier":">25 targets excluded"},SCRIPT,
  "Ablation attempts vs metaphase duration")

# ---------- Statistical grid (Mann-Whitney U pairwise) ----------
# Double Chromosome is globally empty (feedback) -> dropped so it isn't an all-blank row/column.
ORDER=["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls",
       "3-Sister","3-Sister Controls","Off-Target/Control"]
vals={k:[v for _,v in coh[k]] for k in ORDER}
n=len(ORDER); P=np.full((n,n),np.nan)
for i in range(n):
    for j in range(n):
        if i==j: continue
        a,b=vals[ORDER[i]],vals[ORDER[j]]
        if len(a)>=3 and len(b)>=3:
            P[i,j]=stats.mannwhitneyu(a,b,alternative="two-sided").pvalue
fig,ax=plt.subplots(figsize=(8.2,7))
import matplotlib.colors as mcol
cmap=mcol.ListedColormap(["#08519c","#3182bd","#9ecae1","#deebf7","#f7f7f7"])
bounds=[0,0.001,0.01,0.05,0.1,1]; norm=mcol.BoundaryNorm(bounds,cmap.N)
im=ax.imshow(P,cmap=cmap,norm=norm)
for i in range(n):
    for j in range(n):
        if np.isnan(P[i,j]): continue
        p=P[i,j]
        ax.text(j,i,lib.sig_cell(p),ha="center",va="center",fontsize=6.6,linespacing=1.25,
                color="#111" if p>.05 else "white")
ax.set_xticks(range(n));ax.set_yticks(range(n))
ax.set_xticklabels([lib.lbl(k).replace(chr(10),"/") for k in ORDER],rotation=40,ha="right",fontsize=8);ax.set_yticklabels([lib.lbl(k).replace(chr(10),"/") for k in ORDER],fontsize=8)
ax.set_title("Statistical grid — Mann–Whitney U (metaphase duration)",loc="left",fontweight="bold",fontsize=11)
cb=fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04,ticks=[0.0005,0.005,0.03,0.075,0.5])
cb.ax.set_yticklabels(["<.001","<.01","<.05","<.1","ns"]); cb.set_label("p-value")
plt.tight_layout(); plt.savefig(f"{OUT}/G1_statgrid.png",bbox_inches="tight"); plt.close()
_rg=[[ORDER[i],ORDER[j],("" if np.isnan(P[i,j]) else round(float(P[i,j]),6))] for i in range(n) for j in range(n) if i!=j]
lib.record_plot("G1_statgrid",["cohort_a","cohort_b","p_value"],_rg,
  {"type":"significance matrix","test":"Mann-Whitney U two-sided","metric":"metaphase duration"},SCRIPT,
  "Pairwise Mann-Whitney U across cohorts")

# ---------- Survival curve (fraction not yet at anaphase vs time) ----------
fig,ax=plt.subplots(figsize=(8.6,5.2))
# 2026-07-10 (user): show ONE pooled "All off-target" (Off-Target/Control) line instead of the
# per-cohort 1/2/3-Sisterless off-target partitions. Double-chromosome stays out.
SURV=["unModified","1-Sister","2-Sister","3-Sister","Off-Target/Control"]
for k in SURV:
    d=sorted(vals.get(k,[]))
    if len(d)<3: continue
    xs=np.sort(d); ys=1-np.arange(1,len(xs)+1)/len(xs)
    ls="-" if (k not in ("Off-Target/Control",) and "Controls" not in k) else (0,(4,1.5))   # all-off-target line dashed
    ax.step(np.concatenate([[0],xs]),np.concatenate([[1],ys]),where="post",color=lib.PALETTE[k],lw=2,ls=ls,
            label=f"{lib.lbl(k).replace(chr(10),' ')} (N={len(xs)})")
ax.set_xlabel("Time in metaphase (min)"); ax.set_ylabel("Fraction not yet at anaphase")
ax.set_title("Survival — time to anaphase by cohort",loc="left",fontweight="bold",fontsize=11)
ax.legend(fontsize=7,ncol=2,loc="upper right"); ax.set_ylim(0,1.02)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_survival.png",bbox_inches="tight"); plt.close()
_rs=[[b,k,round(d,3)] for k in SURV for b,d in coh.get(k,[])]
lib.record_plot("G1_survival",["batch","cohort","mitotic_duration_min"],_rs,
  {"type":"KM-style step (fraction not yet at anaphase)","offtarget":"pooled into ONE All off-target line (per-cohort partitions removed 2026-07-10)"},SCRIPT,
  "Time-to-anaphase survival by cohort")

# ---------- Roundness traces ----------
def poly_roundness(pts):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]
    A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))))
    if per==0: return None
    r=4*np.pi*A/per**2
    return r if 0<r<=1.2 else None
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c:i for i,c in enumerate(rows[0])}
from collections import defaultdict
traces=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in batch2coh: continue
    try:
        ts=float(r[ix['t_sec']]); rd=poly_roundness(json.loads(r[ix['points']]))
    except: continue
    if rd is None: continue
    tmin=ts/60.0  # outline t_sec is already ablation-anchored (t=0 = first ablation)
    if abs(tmin)>600:  # implausible (>10 h) — screen out
        lib.log_review("roundness:time",b,f"{tmin:.0f} min","implausible normalized time — excluded"); continue
    traces[b].append((tmin,rd))
fig,ax=plt.subplots(figsize=(9.5,5.4))
gpts=defaultdict(list)
for b,pts in traces.items():
    if len(pts)<2: continue
    pts=sorted(pts); g=batch2coh[b]
    ax.plot([p[0] for p in pts],[p[1] for p in pts],color=lib.PALETTE.get(g,"#999"),alpha=0.15,lw=0.8,zorder=1)
    gpts[g].extend(pts)
# binned-mean TREND line per group
for g,pts in gpts.items():
    a=np.array(sorted(pts)); t,r=a[:,0],a[:,1]
    if len(t)<5: continue
    bins=np.linspace(max(t.min(),-5),min(t.max(),110),10); idx=np.digitize(t,bins)
    bx=[];by=[]
    for k in range(1,len(bins)+1):
        m=idx==k
        if m.sum()>=3: bx.append(t[m].mean()); by.append(r[m].mean())
    if len(bx)>=2:
        ax.plot(bx,by,color=lib.PALETTE.get(g,"#999"),lw=2.6,marker="o",ms=4,zorder=3,
                label=lib.lbl(g).replace(chr(10),' '))
ax.axvline(0,color="#333",ls=":",lw=1); ax.text(0.3,0.02,"first ablation",rotation=90,fontsize=7,color="#333")
ax.set_xlabel("Time from first ablation (min)"); ax.set_ylabel("Cell roundness  (4πA/P²)")
ax.set_title("Cell roundness — per-cell traces + per-group trend",loc="left",fontweight="bold",fontsize=11)
ax.legend(fontsize=7,ncol=2,title="trend (binned mean)"); ax.set_ylim(0,1.05)
plt.tight_layout(); plt.savefig(f"{OUT}/G1_roundness_traces.png",bbox_inches="tight"); plt.close()

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print("Group 1 plots done. cohort N:",{k:len(coh[k]) for k in ORDER})
print("roundness: traced cells:",sum(1 for b,p in traces.items() if len(p)>=2))
print("review items:",len(lib.REVIEW))
