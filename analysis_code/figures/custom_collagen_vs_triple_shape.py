"""Collagen (on-target) vs non-collagen triple-on-target — cell roundness & cross-sectional area over time.

RECOVERED 2026-07-16 from the session transcript (inline heredoc, never saved). CLEANED: group B (non-collagen
triple on-target) was loaded from a now-stale /tmp/shape_groups.json that included metaphase/4-sisterless cells;
it is now rebuilt from lib.assign_cohorts()["3-Sister"] (which already excludes metaphase, 4-sisterless, drug,
Exclude, mad1) minus the collagen batches. Group A = the 4 on-target collagen triples. Produces the 4
collagenON_vs_triple_{roundness,area}_{binned,linear}.png figures + provenance CSVs."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
import lib
try: lib.apply_style()
except Exception: pass
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
coh=lib.assign_cohorts()
def _ismeta(b):  # USER 2026-07-17: never plot metaphase-ablation batches in any collagen plot
    return (mr.get(b,{}).get("Phase of Ablations") or "").strip().lower()=="metaphase"
# group A: on-target collagen triples — DATA-DRIVEN (was hardcoded to 4; USER 2026-07-17). Mirrors B:
# every 3-Sister (=3 on-target ablations) collagen-named batch, non-excluded. Picks up newly-annotated
# collagen batches (e.g. collagen_22, now #Sisterless=3 + meta/ana + outlines) automatically.
A=set(b for b,_ in coh.get("3-Sister",[]) if "collagen" in b.lower() and not lib.plot_excluded(b) and not _ismeta(b))
# group B: clean triple on-target NON-collagen (cohort already drops metaphase/4-sis/drug/excluded)
B=set(b for b,_ in coh.get("3-Sister",[]) if "collagen" not in b.lower() and b not in A and not lib.plot_excluded(b) and not _ismeta(b))
print(f"collagen A (on-target collagen): {len(A)} | B (non-collagen triple on-target, clean): {len(B)}")
def ana_min(b):
    v=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)","")); return v/60.0 if v is not None else None
def poly_round(pts):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]; Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))))
    if per==0: return None
    r=4*np.pi*Ar/per**2; return r if 0<r<=1.2 else None
def poly_area(pts,pxs):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]; Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    a=Ar*pxs*pxs; return a if 0<a<=5000 else None
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
psize={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: psize[b]=float(r[ix['pixel_size_um']])
    except Exception: psize.setdefault(b,0.062)
def build(metric):
    tr=defaultdict(list)
    for r in rows[1:]:
        b=r[ix['batch']].strip()
        if b not in A and b not in B: continue
        try:
            t=float(r[ix['t_sec']])/60.0; pts=json.loads(r[ix['points']])
            v=poly_round(pts) if metric=="round" else poly_area(pts,psize.get(b,0.062))
        except Exception: continue
        if v is None: continue
        tr[b].append((t,v))
    return tr
def ref_clip(b,trace):
    a=ana_min(b); tt=[(t,v) for (t,v) in sorted(trace) if (a is None or t<=a+1e-6)]
    if len(tt)<2: return None,None
    x0=tt[0][0]
    if x0>0.5: tt=[(t-x0,v) for (t,v) in tt]; a=(a-x0) if a is not None else None
    return tt,a
def trend_to_mean(pts,md,nb=8,minpts=3):
    if md is None or md<=0: return [],[]
    arr=np.array(sorted(pts)); t=arr[:,0]; y=arr[:,1]; bins=np.linspace(0,md,nb); idx=np.digitize(t,bins); bx=[];by=[]
    for k in range(1,len(bins)):
        m=idx==k
        if m.sum()>=minpts: bx.append(float(t[m].mean())); by.append(float(y[m].mean()))
    if bx and bx[-1]<md-1e-6:
        ml=(t>=bins[-2])&(t<=md+1e-6); by.append(float(y[ml].mean()) if ml.sum()>=1 else by[-1]); bx.append(md)
    return bx,by
COL={"A":"#1f77b4","B":"#d62728"}
LBL={"A":f"Triple ablation — collagen ON-TARGET (N={len(A)})","B":f"Triple ablation — on-target, non-collagen (N={len(B)})"}
YL={"round":"Cell roundness (4πA/P²)","area":"Cross-sectional area (µm²)"}
OUTD="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"; os.makedirs(OUTD,exist_ok=True)
_prov=defaultdict(list)
for style in ("binned","linear"):
    for metric in ("round","area"):
        tr=build(metric); fig,ax=plt.subplots(figsize=(8,5.6))
        for grpname,members in (("A",A),("B",B)):
            allpts=[]; anas=[]
            for b in members:
                if b not in tr: continue
                pts,a=ref_clip(b,tr[b])
                if pts is None: continue
                allpts+=pts
                if a is not None: anas.append(a)
                xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
                ax.plot(xs,ys,color=COL[grpname],alpha=.18,lw=1,zorder=1)
                ax.scatter(xs,ys,s=14,color=COL[grpname],alpha=.32,edgecolor="none",zorder=2)
                if style=="linear": _prov[metric]+=[[b,grpname,round(t,3),round(v,4)] for t,v in pts]
            md=float(np.median(anas)) if anas else None  # USER 2026-08-10: MEDIAN, not mean
            arr=np.array(allpts); x=arr[:,0]; y=arr[:,1]
            if style=="binned":
                bx,by=trend_to_mean(allpts,md)
                if bx: ax.plot(bx,by,color=COL[grpname],lw=3,zorder=5,label=LBL[grpname])
                else: ax.plot([],[],color=COL[grpname],lw=3,label=LBL[grpname])
            else:
                m,c=np.polyfit(x,y,1); r=np.corrcoef(x,y)[0,1]; xx=np.array([0.0, md if md else x.max()])
                ax.plot(xx,m*xx+c,color=COL[grpname],lw=3,zorder=5,label=LBL[grpname]+f"  [slope={m:.3g}/min, r={r:.2f}]")
            if md: ax.axvline(md,color=COL[grpname],ls=":",lw=1.2,alpha=.7,zorder=3)
        ax.set_xlabel("Time from first ablation (min)"); ax.set_ylabel(YL[metric])
        sty="binned-mean trend" if style=="binned" else "straight-line fit"
        ax.set_title(f"Collagen (on-target only) vs non-collagen triple on-target — {'roundness' if metric=='round' else 'cross-sectional area'}\n({sty}; dotted = group mean anaphase)")
        if metric=="round": ax.set_ylim(0,1.15)
        ax.legend(loc="best",fontsize=8.5,framealpha=.9); ax.set_xlim(left=0)
        fig.tight_layout()
        # USER 2026-07-22: these four collagenON figures were REVIVED onto the live artboards, so the
        # baked "RETIRED" watermark is removed -- a stamp on a figure that is not on the retired
        # artboard is just confusing. The caveat it carried is NOT lost: it is recorded in
        # PLOT_SETTINGS under `caveat` for each of these four figures.
        fp=os.path.join(OUTD,f"collagenON_vs_triple_{'roundness' if metric=='round' else 'area'}_{style}.png")
        fig.savefig(fp,dpi=150); plt.close(fig); print("wrote",fp)
for metric in ("round","area"):
    nm=f"collagenON_vs_triple_{'roundness' if metric=='round' else 'area'}_linear"
    lib.record_plot(nm,["batch","group","time_from_ablation_min","value"],_prov[metric],
        {"type":"collagen-vs-triple shape trace","group_A":"on-target collagen (N=%d)"%len(A),
         "group_B":"non-collagen triple on-target (clean cohort, N=%d)"%len(B),"metric":metric},
        __file__,"Collagen vs non-collagen triple — %s"%("roundness" if metric=="round" else "area"),
        source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])

# ---- no-ON variant: collagen_vs_triple_{metric}.png (A = ALL collagen-named batches with outline data, clean B) ----
A_all=set(b for b in set(r[ix['batch']].strip() for r in rows[1:]) if "collagen" in b.lower())
for metric in ("round","area"):
    tr=build(metric)
    # rebuild trace dict to also include A_all members
    tr2=defaultdict(list)
    for r in rows[1:]:
        b=r[ix['batch']].strip()
        if b not in A_all and b not in B: continue
        try:
            t=float(r[ix['t_sec']])/60.0; pts=json.loads(r[ix['points']])
            v=poly_round(pts) if metric=="round" else poly_area(pts,psize.get(b,0.062))
        except Exception: continue
        if v is None: continue
        tr2[b].append((t,v))
    fig,ax=plt.subplots(figsize=(8,5.6))
    # USER 2026-08-05: "it says that for this non-collagen group there should be 31 traces plotted but i
    # dont think there is". Correct — the N in these labels counted COHORT MEMBERSHIP and was computed
    # BEFORE the per-cell filter below (a cell is skipped when it has no usable trace in the window), so
    # the legend reported the roster while the axes showed who actually turned up. Measured 2026-08-05:
    # this figure claimed A=20/B=25 and drew A=5/B=21. Count the traces as they are drawn instead.
    for grpname,members,col,lab0 in (("A_all",A_all,"#1f77b4","Collagen triple (all"),("B",B,"#d62728","Non-collagen triple on-target")):
        allpts=[]; _ndrawn=0
        for b in members:
            if b not in tr2: continue
            pts,a=ref_clip(b,tr2[b])
            if pts is None: continue
            _ndrawn+=1
            allpts+=pts; xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
            ax.plot(xs,ys,color=col,alpha=.18,lw=1); ax.scatter(xs,ys,s=14,color=col,alpha=.32,edgecolor="none")
        lab=f"{lab0}, N={_ndrawn})" if lab0.endswith("(all") else f"{lab0} (N={_ndrawn})"
        if _ndrawn < len(members):
            print(f"  [{metric}] {grpname}: {len(members)-_ndrawn} of {len(members)} cells have no usable trace in the window -> label now says N={_ndrawn}")
        if len(allpts)>=2:
            arr=np.array(allpts); m,c=np.polyfit(arr[:,0],arr[:,1],1); xx=np.array([0.0,arr[:,0].max()])
            ax.plot(xx,m*xx+c,color=col,lw=3,label=lab+f"  [slope={m:.3g}/min]")
    ax.set_xlabel("Time from first ablation (min)"); ax.set_ylabel(YL[metric])
    ax.set_title(f"Collagen triple vs non-collagen triple on-target — {'roundness' if metric=='round' else 'cross-sectional area'}")
    if metric=="round": ax.set_ylim(0,1.15)
    ax.legend(loc="best",fontsize=8.5); ax.set_xlim(left=0); fig.tight_layout()
    lib.mark_retired(fig, note="pools on-target + off-target collagen ablations — use the collagenON (on-target only) version")
    fp=os.path.join(OUTD,f"collagen_vs_triple_{'roundness' if metric=='round' else 'area'}.png")
    fig.savefig(fp,dpi=150); plt.close(fig); print("wrote",fp)

# ============ METAPHASE -> ANAPHASE window versions (USER 2026-07-16) ============
# X = time from Metaphase Start (min); outline points clipped to [Metaphase Start, Anaphase Onset].
# A = 4 on-target collagen (named); B = 27 triple on-target NOT named collagen. Linear fit per group +
# slope-difference significance: ANCOVA group x time interaction (pooled) AND per-cell-slope Mann-Whitney.
import scipy.stats as _ss
# 4 group-B cells that ARE specified as collagen in imaging-log COMMENTS (flag on plot; user decides)
COMMENT_COLLAGEN_IN_B={"20250918 triple_ablation_15","20250918 triple_ablation_29",
                       "20250925 triple_ablation_7","20250925 triple_ablation_13"}
_CCma=set(b for b in COMMENT_COLLAGEN_IN_B if not _ismeta(b))   # drop any metaphase-ablation comment-collagen
A_ma=set(A)|_CCma   # WITH collagen = named collagen + comment-identified collagen
B_ma=set(B)-_CCma   # WITHOUT collagen = remaining on-target triples
def _ma_win(b):
    r=mr.get(b,{}); ms=lib.parse_time(r.get("Metaphase Start (s)","") or ""); an=lib.parse_time(r.get("Anaphase Onset (s)","") or "")
    return ms,an
def build_ma(metric):
    tr=defaultdict(list)
    for r in rows[1:]:
        b=r[ix['batch']].strip()
        if b not in A and b not in B: continue
        ms,an=_ma_win(b)
        if ms is None or an is None: continue
        try:
            ts=float(r[ix['t_sec']]); pts=json.loads(r[ix['points']])
            if ts<ms-1e-6 or ts>an+1e-6: continue
            v=poly_round(pts) if metric=="round" else poly_area(pts,psize.get(b,0.062))
        except Exception: continue
        if v is None: continue
        tr[b].append(((ts-ms)/60.0, v))
    return tr
def _cell_slopes(members,tr):
    out=[]
    for b in members:
        if b not in tr or len(tr[b])<3: continue
        arr=np.array(sorted(tr[b]));
        if np.ptp(arr[:,0])<=0: continue
        out.append(float(np.polyfit(arr[:,0],arr[:,1],1)[0]))
    return out
def _ancova_interaction(ptsA, ptsB):
    # pooled OLS: y = b0 + b1*t + b2*G + b3*(t*G); G=1 collagen. b3 = slope diff, test H0: b3=0
    if len(ptsA)<2 or len(ptsB)<2: return None
    X=[]; Y=[]
    for (t,v) in ptsA: X.append([1.0,t,1.0,t]); Y.append(v)
    for (t,v) in ptsB: X.append([1.0,t,0.0,0.0]); Y.append(v)
    X=np.array(X); Y=np.array(Y); n=len(Y)
    if n-4<1: return None
    beta,_,_,_=np.linalg.lstsq(X,Y,rcond=None)
    resid=Y-X@beta; rss=float(resid@resid); sigma2=rss/(n-4)
    try: cov=sigma2*np.linalg.inv(X.T@X)
    except np.linalg.LinAlgError: return None
    se3=float(np.sqrt(cov[3,3]))
    if se3==0: return None
    tstat=float(beta[3])/se3; p=float(2*_ss.t.sf(abs(tstat),df=n-4))
    return {"slope_collagen":float(beta[1]+beta[3]),"slope_noncoll":float(beta[1]),"diff":float(beta[3]),"t":tstat,"df":n-4,"p":p}
for metric in ("round","area"):
    tr=build_ma(metric); fig,ax=plt.subplots(figsize=(8.2,5.8))
    grp_pts={}
    _NDRAWN={}
    for grpname,members,col in (("A",A_ma,"#1f77b4"),("B",B_ma,"#d62728")):
        allpts=[]; durs=[]; _ndrawn=0     # count traces DRAWN, not cohort membership (USER 2026-08-05)
        for b in members:
            if b not in tr: continue
            _ndrawn+=1
            arr=sorted(tr[b]); allpts+=arr
            ms,an=_ma_win(b);
            if ms is not None and an is not None: durs.append((an-ms)/60.0)
            xs=[p[0] for p in arr]; ys=[p[1] for p in arr]
            flagged = b in COMMENT_COLLAGEN_IN_B
            ax.plot(xs,ys,color=col,alpha=.16,lw=1,zorder=1)
            ax.scatter(xs,ys,s=15,color=col,alpha=.30,edgecolor=("k" if flagged else "none"),
                       linewidth=(0.9 if flagged else 0),zorder=(4 if flagged else 2))
        grp_pts[grpname]=allpts
        _NDRAWN[grpname]=_ndrawn
        if _ndrawn < len(members):
            print(f"  [{metric} meta] {grpname}: {len(members)-_ndrawn} of {len(members)} cells have no trace in the metaphase window -> label now says N={_ndrawn}")
        mean_ana=float(np.mean(durs)) if durs else None
        if len(allpts)>=2:
            arr=np.array(allpts)
            # USER 2026-07-17: fit the trendline ONLY on points from metaphase start to the GROUP MEAN
            # anaphase onset, and stop the drawn line at that mean anaphase onset (not the group max x).
            fit=arr[arr[:,0]<=mean_ana] if mean_ana is not None else arr
            if len(fit)<2: fit=arr                       # safety fallback if too few points in-window
            m,c=np.polyfit(fit[:,0],fit[:,1],1)
            xx=np.array([0.0, mean_ana if mean_ana is not None else arr[:,0].max()])
            lab={"A":f"On-target triple, WITH collagen (N={_NDRAWN.get('A',0)})","B":f"On-target triple, WITHOUT collagen (N={_NDRAWN.get('B',0)})"}[grpname]
            ax.plot(xx,m*xx+c,color=col,lw=3,zorder=5,label=lab+f"  [slope={m:.3g}/min]")
        if durs: ax.axvline(mean_ana,color=col,ls=":",lw=1.1,alpha=.6,zorder=3)
    # --- stats ---
    anc=_ancova_interaction(grp_pts.get("A",[]),grp_pts.get("B",[]))
    sA=_cell_slopes(A_ma,tr); sB=_cell_slopes(B_ma,tr)
    mw=None
    if len(sA)>=1 and len(sB)>=2:
        try: mw=float(_ss.mannwhitneyu(sA,sB,alternative="two-sided").pvalue)
        except Exception: mw=None
    def _sig(p): return "***" if p<1e-3 else "**" if p<1e-2 else "*" if p<0.05 else "n.s."
    lines=["Slope difference (with vs without collagen):"]
    if anc: lines.append(f"  ANCOVA group×time: p={anc['p']:.3g} {_sig(anc['p'])}  (Δslope={anc['diff']:.3g}/min)")
    if mw is not None: lines.append(f"  per-cell slope MWU: p={mw:.3g} {_sig(mw)}  (n={len(sA)} vs {len(sB)})")
    lines.append("black-edged pts = collagen identified by comment, not name")
    box="\n".join(lines)
    yloc,va=(0.03,"bottom") if metric=="round" else (0.97,"top")
    ax.text(0.98,yloc,box,transform=ax.transAxes,ha="right",va=va,fontsize=7.6,
            bbox=dict(boxstyle="round",fc="white",ec="#888",alpha=.92),zorder=20)
    ax.set_xlabel("Time from metaphase start (min)"); ax.set_ylabel(YL[metric])
    ax.set_title(f"On-target triple ablations — WITH vs WITHOUT collagen — {'roundness' if metric=='round' else 'cross-sectional area'}\n(cells: metaphase to anaphase; dotted = group mean anaphase; trendline fit on points ≤ mean anaphase, ends there)")
    if metric=="round": ax.set_ylim(0,1.15)
    ax.legend(loc=("upper left" if metric=="round" else "lower left"),fontsize=8.3,framealpha=.9); ax.set_xlim(left=0)
    fig.tight_layout()
    fp=os.path.join(OUTD,f"collagenON_vs_triple_{'roundness' if metric=='round' else 'area'}_meta_to_ana.png")
    fig.savefig(fp,dpi=150); plt.close(fig); print("wrote",fp)
    _pp=[]
    for g,members in (("A",A_ma),("B",B_ma)):
        for b in members:
            if b in tr:
                for t,v in tr[b]: _pp.append([b,g,round(t,3),round(v,4)])
    lib.record_plot(f"collagenON_vs_triple_{'roundness' if metric=='round' else 'area'}_meta_to_ana",
        ["batch","group","time_from_metaphase_min","value"],_pp,
        {"type":"collagen-vs-triple shape, metaphase->anaphase window","group_A":"on-target triple WITH collagen (N=%d)"%len(A_ma),
         "group_B":"on-target triple WITHOUT collagen (N=%d)"%len(B_ma),"metric":metric,
         "slope_diff_ancova_p":(anc['p'] if anc else None),"per_cell_slope_mwu_p":mw,
         "flagged_comment_collagen_in_B":sorted(COMMENT_COLLAGEN_IN_B)},
        __file__,"Collagen vs non-collagen triple, metaphase->anaphase %s"%("roundness" if metric=="round" else "area"),
        source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])

print("done")
