"""DEMO shape-rate vs metaphase-duration COMPOSITE (4-panel) — single/triple/all versions.

Recovered + saved 2026-07-17 (the original DEMO_shape_rate_vs_metaphase.png was an unsaved heredoc; only the
component scatters in custom_shape_rate_vs_metaphase.py were saved). This rebuilds the 4-panel composite and
adds per-cohort versions, per user 2026-07-17 ("single and triple should each have their own version").

Per-cell FIRST-HALF slope (NEB..midpoint-to-anaphase; first-frame fallback if no NEB), exactly as
custom_shape_rate_vs_metaphase.py. Each dot = ONE cell's slope (cell is the unit — no pooled-timepoint OLS).
Panels: (TL) rounding-rate scatter vs metaphase duration, (TR) area-rate scatter, (BL/BR) metaphase duration
by median split of each rate (slow vs fast), Mann-Whitney. roundness=4πA/P², area=shoelace·px².
Writes DEMO_shape_rate_vs_metaphase{,_single,_triple}.png (+ SVG + _ai_relink/pdf). Exclusion: lib.plot_excluded."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
try: lib.apply_style()
except Exception: pass

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
SCRIPT=__file__

coh=lib.assign_cohorts(); b2={}
for k,lst in coh.items():
    for b,d in lst:
        if lib.plot_excluded(b): continue
        b2.setdefault(b,k)
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}

def pt(b,c): return lib.parse_time(mr.get(b,{}).get(c,""))
def m_(b,c):
    v=pt(b,c); return v/60.0 if v is not None else None
def meta_dur(b):
    a=pt(b,"Anaphase Onset (s)"); m=pt(b,"Metaphase Start (s)")
    return (a-m)/60.0 if (a is not None and m is not None) else None
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

# FIRST-HALF window + slope (identical to custom_shape_rate_vs_metaphase.py)
def window(b):
    end=m_(b,"Anaphase Onset (s)")
    if end is None: return None
    neb=m_(b,"NEB Time (s)")
    allt=[t for t,_ in R.get(b,[])]+[t for t,_ in Aa.get(b,[])]
    if not allt: return None
    start=neb if (neb is not None and neb<end) else min(allt)
    if end<=start: return None
    return start, start+0.5*(end-start)
# FEEDBACK 2026-08 ("should definitely be more samples"): the old threshold demanded >=3 outline points
# inside the first-half window before a per-cell rate was computed, but a linear slope is mathematically
# defined by as few as 2 points -- 3 was a stricter-than-necessary guard, not a real requirement. Relaxing
# it to the true minimum (>=2 points) recovers every cell that has real, honestly-measured outline data in
# the window but was previously discarded purely for having "only" 2 usable frames. This is applied
# UNIFORMLY to every cohort composite below (all/single/triple/unmodified) -- not cherry-picked per cohort.
# Verified count (1-Sister): 25 cells had NO usable rate before; of those, 14 had exactly 1-2 points in the
# window (now rescued), the remaining had 0 points or no outline at all (still correctly excluded).
def slope_win(tr,win):
    if win is None: return None
    s,mid=win; tt=[(t,v) for t,v in sorted(tr) if s-1e-6<=t<=mid+1e-6]
    if len(tt)<2: return None
    x=np.array([q[0] for q in tt]); y=np.array([q[1] for q in tt])
    return float(np.polyfit(x,y,1)[0]) if x.max()-x.min()>1e-6 else None

# per-cell first-half records: (batch, cohort, rounding_slope, area_slope, metaphase_dur)
recs=[]
for b,k in b2.items():
    w=window(b)
    recs.append((b,k,slope_win(R.get(b,[]),w),slope_win(Aa.get(b,[]),w),meta_dur(b)))

# FEEDBACK 2026-08 ("resolve unmodified"): `_single` had NO unModified reference at all. `composite()` now
# takes a LIST of (sel_cohorts, label, color) groups instead of one, so an extra cohort can be overlaid on
# the SAME axes -- its own colour, own trendline/Spearman/N (never pooled into the primary cohort's stats,
# so the existing 1-Sister correlation numbers are not changed by adding a reference group), and its own
# pair of boxes in the median-split panel below (each group split on ITS OWN median, same as the
# single-group case always did). Called with one group, behaviour is identical to before (mod. wider N).
SHORT={"1-ablation (single) on-target":"single","3-ablation (triple) on-target":"triple",
       "Unmodified (no ablation)":"unmod","all cohorts":"all"}
def composite(groups, slug, human):
    fig,axes=plt.subplots(2,2,figsize=(11 if len(groups)==1 else 13.5,9))
    prov=[]
    SCAT=[(0,"round","Rate of rounding, first half of mitosis\n(roundness slope /min)","Rounding rate"),
          (1,"area","Rate of area loss, first half of mitosis\n(area slope µm²/min)","Area-loss rate")]
    for col,(idx,mkey,xlab,short) in enumerate(SCAT):
        ax=axes[0][col]; axb=axes[1][col]
        boxes=[]; blabels=[]; bcols=[]; titles=[]
        for gi,(sel_cohorts,glabel,dot_color) in enumerate(groups):
            rr=[(b,k,rs,as_,md) for (b,k,rs,as_,md) in recs if (sel_cohorts is None or k in sel_cohorts)]
            xs=[];ys=[];keep=[]
            for b,k,rs,as_,md in rr:
                xv=(rs,as_)[idx]
                if xv is None or md is None: continue
                xs.append(xv);ys.append(md);keep.append((b,xv,md))
            xs=np.array(xs);ys=np.array(ys)
            ax.scatter(xs,ys,c=dot_color,s=34,edgecolor="white",lw=.4,alpha=.85,zorder=3)
            rho=p=float("nan")
            if len(xs)>=3:
                m,c=np.polyfit(xs,ys,1); xx=np.linspace(xs.min(),xs.max(),50)
                ax.plot(xx,m*xx+c,color=dot_color,lw=1.8,ls="--",zorder=4)
                rho,p=stats.spearmanr(xs,ys)
            titles.append(f"{glabel}: ρ={rho:.2f}, p={p:.2g}, N={len(xs)}")
            if len(groups)>1:
                ax.plot([],[],color=dot_color,lw=2,label=f"{glabel} (N={len(xs)})")
            if len(xs)>=4:
                med=np.median(xs)
                lo=[md for xv,md in zip(xs,ys) if xv<=med]; hi=[md for xv,md in zip(xs,ys) if xv>med]
                tag=SHORT.get(glabel,glabel) if len(groups)>1 else ("Slow rounders" if mkey=="round" else "Slow shrinkers")
                tag2=SHORT.get(glabel,glabel) if len(groups)>1 else ("Fast rounders" if mkey=="round" else "Fast shrinkers")
                boxes+=[lo,hi]
                blabels+=[f"{tag}\nlow\nN={len(lo)}", f"{tag2}\nhigh\nN={len(hi)}"]
                bcols+=[dot_color,dot_color]
                prov+=[[b,glabel,short,round(float(xv),5),round(float(md),3),("low" if xv<=med else "high")] for (b,xv,md) in keep]
        ax.set_xlabel(xlab,fontsize=9); ax.set_ylabel("Metaphase duration (min)")
        ax.set_title("  |  ".join(titles),fontsize=9.5 if len(groups)>1 else 10)
        if len(groups)>1: ax.legend(fontsize=8,loc="best")
        # bottom: metaphase duration by median split of this rate, one box-pair per group
        if boxes and all(len(g) for g in boxes):
            bp=axb.boxplot(boxes,labels=blabels,widths=.55,patch_artist=True,showfliers=False)
            for patch,c in zip(bp['boxes'],bcols): patch.set_facecolor(c); patch.set_alpha(.45)
            for i,(g,c) in enumerate(zip(boxes,bcols)):
                axb.scatter(np.random.default_rng(idx*7+i).normal(i+1,.05,len(g)),g,c=c,s=18,alpha=.8,zorder=3,edgecolor="white",lw=.3)
            pps=[]
            for gi in range(len(boxes)//2):
                lo,hi=boxes[2*gi],boxes[2*gi+1]
                if len(lo)>=1 and len(hi)>=1 and (len(lo)+len(hi))>=5:
                    try:
                        _,pp=stats.mannwhitneyu(lo,hi,alternative="two-sided")
                        pps.append(f"{SHORT.get(groups[gi][1],groups[gi][1])} p={pp:.2g}")
                    except Exception: pass
            # short group tags (not the full glabel) so this title can't run into the neighbouring subplot's
            # title -- with two long group names ("1-ablation (single) on-target" x "Unmodified (no
            # ablation)") the full-name version overflowed past the axes and collided with the panel next
            # to it (matplotlib titles aren't clipped to the subplot box).
            axb.set_title("Metaphase duration by within-group median split — MW "+" | ".join(pps),fontsize=8.5)
            axb.set_ylabel("Metaphase duration (min)")
            axb.tick_params(axis='x',labelsize=7.5)
        else:
            axb.text(.5,.5,"too few cells",ha="center",va="center",transform=axb.transAxes); axb.axis("off")
    fig.suptitle(f"Early-mitosis shape-change rate vs metaphase duration — {human}",fontsize=13)
    fig.tight_layout(rect=[0,0,1,0.97])
    stem=f"DEMO_shape_rate_vs_metaphase{('' if slug=='all' else '_'+slug)}"
    png=os.path.join(OUT,stem+".png")
    fig.savefig(png,dpi=150); fig.savefig(os.path.join(OUT,"illustrator",stem+".svg"))
    plt.close(fig)
    ncells={glabel:len({b for b,k in b2.items() if (sel_cohorts is None or k in sel_cohorts)}) for sel_cohorts,glabel,_ in groups}
    print("wrote",png, "  cells per group:",ncells)
    lib.record_plot(stem,["batch","group","panel","rate","metaphase_duration_min","median_split"],prov,
        {"type":"shape-rate vs metaphase-duration composite (scatter + median-split boxplot)","cohort":human,
         "groups":[g[1] for g in groups],
         "window":"first-half (NEB..midpoint-to-anaphase)","unit":"per-cell slope (cell = unit, no pooled-timepoint OLS)",
         "exclusion":"lib.plot_excluded (drug + Exclude=Yes + REVIEW_EXCLUDE dropped)",
         "min_window_points":"2026-08-03: relaxed from >=3 to >=2 (the true minimum for a linear slope) to "
                              "recover honestly-measured cells with only 2 outline points in the first-half "
                              "window -- see comment above slope_win()."},
        SCRIPT,f"Early-mitosis shape-change rate vs metaphase duration — {human}",
        source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])

# all (reproduces the original composite for validation), then single & triple.
# FEEDBACK 2026-08-03 (M2-15, "should definitely be more samples (and resolve unmodified)"): `single` had NO
# unModified reference at all -- it now carries unModified as a second, separately-coloured, separately-fit
# group on the SAME axes (never pooled into the 1-Sister stats). unModified also gets its OWN standalone
# composite (matching the "single/triple each get their own version" convention already used here), so it is
# not only visible as a small overlay.
UNMOD=({"unModified"},"Unmodified (no ablation)", "#4d4d4d")
composite([(None,"all cohorts","#4a78b5")],                                                    "all",    "all cohorts")
composite([({"1-Sister"},"1-ablation (single) on-target", lib.PALETTE.get("1-Sister","#f39c5b")), UNMOD], "single", "1-ablation (single) on-target + Unmodified")
composite([({"3-Sister"},"3-ablation (triple) on-target", lib.PALETTE.get("3-Sister","#3b6fb0"))],        "triple", "3-ablation (triple) on-target")
composite([UNMOD],                                                                              "unmodified", "Unmodified (no ablation)")
print("done")
