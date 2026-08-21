"""DEMO lineplot — cell shape (roundness + area) through metaphase, split WITHIN the on-target 1-ablation and
3-ablation sets into their fastest vs slowest metaphase thirds, with a trendline per group.

USER 2026-07-16: the previous version pooled ALL on-target 1/2/3 cells and split that pool by metaphase
duration — which confounds ablation number with metaphase length (the "longest third" was dominated by triples).
Fix: rank by metaphase duration WITHIN each of the 1-ablation (1-Sister) and 3-ablation (3-Sister) on-target
cohorts, take the fastest third (shortest metaphase) and slowest third (longest metaphase) of EACH to 4 groups.
X-axis = time from METAPHASE ONSET (Metaphase Start); points windowed to [Metaphase Start .. Anaphase Onset].
Two panels: roundness (4πA/P²) and cross-sectional area (µm²). Data: manual cell_outlines + master timing.
USER 2026-07-17: single and triple now get their OWN figure each (not plotted together). Writes
DEMO_lineplot_shape_by_metaphase_single.png and _triple.png (+ SVGs); each has fastest vs slowest thirds only."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from collections import defaultdict
import lib
try: lib.apply_style()
except Exception: pass

OUT="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
os.makedirs(os.path.join(OUT,"illustrator"),exist_ok=True)
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
coh=lib.assign_cohorts()

def ptime(b,c): return lib.parse_time(mr.get(b,{}).get(c,""))
def meta_start(b): return ptime(b,"Metaphase Start (s)")
def ana(b): return ptime(b,"Anaphase Onset (s)")
def meta_dur(b):
    a=ana(b); m=meta_start(b)
    return (a-m)/60.0 if (a is not None and m is not None) else None
def poly_round(pts):
    p=np.array(pts,float); x,y=p[:,0],p[:,1]
    Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))))
    if per==0: return None
    r=4*np.pi*Ar/per**2; return r if 0<r<=1.2 else None
def poly_area(pts,px):
    p=np.array(pts,float); x,y=p[:,0],p[:,1]
    Ar=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))*px*px
    return Ar if 0<Ar<=5000 else None

rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
ps={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: ps[b]=float(r[ix['pixel_size_um']])
    except Exception: ps.setdefault(b,0.062)

# per-cell traces windowed to [metaphase onset .. anaphase]; x = minutes from metaphase onset
Rtr=defaultdict(list); Atr=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    ms=meta_start(b); an=ana(b)
    if ms is None or an is None: continue
    try: ts=float(r[ix['t_sec']]); pts=json.loads(r[ix['points']])
    except Exception: continue
    if ts<ms-1e-6 or ts>an+1e-6: continue
    x=(ts-ms)/60.0
    v=poly_round(pts); w=poly_area(pts,ps.get(b,0.062))
    if v is not None: Rtr[b].append((x,v))
    if w is not None: Atr[b].append((x,w))

def tertiles(C):
    # on-target cohort, not excluded, has metaphase duration + >=2 windowed roundness points
    members=[b for b,_ in coh.get(C,[]) if not lib.plot_excluded(b) and meta_dur(b) is not None and len(Rtr.get(b,[]))>=2]
    members=sorted(members,key=meta_dur)
    n=len(members)//3
    if n==0: return [],[],members
    return members[:n], members[-n:], members
f1,s1,all1=tertiles("1-Sister")
f3,s3,all3=tertiles("3-Sister")
print(f"1-Sister: {len(all1)} usable -> fastest {len(f1)} (meta<= {meta_dur(f1[-1]):.1f}m), slowest {len(s1)} (meta>= {meta_dur(s1[0]):.1f}m)" if f1 else f"1-Sister: {len(all1)} usable (too few for tertiles)")
print(f"3-Sister: {len(all3)} usable -> fastest {len(f3)} (meta<= {meta_dur(f3[-1]):.1f}m), slowest {len(s3)} (meta>= {meta_dur(s3[0]):.1f}m)" if f3 else f"3-Sister: {len(all3)} usable (too few for tertiles)")

# One SEPARATE figure per ablation-number cohort (single=1-abl, triple=3-abl); light=fastest third, dark=slowest.
def mlab(members,which):
    ds=sorted(meta_dur(b) for b in members)
    return (f"meta≤{ds[-1]:.0f}m" if which=="fast" else f"meta≥{ds[0]:.0f}m") if ds else ""
PAN=[(Rtr,"Cell roundness (4πA/P²)","Roundness (cell rounding)",(0,1.15)),
     (Atr,"Cross-sectional area (µm²)","Cross-sectional area (area loss)",None)]

# per-cohort: (slug, human label, fastest members, slowest members, light color, dark color)
COHORTS=[
 ("single","1-ablation (single) on-target", f1, s1, "#f4a582", "#b2182b"),
 ("triple", "3-ablation (triple) on-target", f3, s3, "#92c5de", "#2166ac"),
]

# FEEDBACK 2026-07/08 ("since essentially binned, would make more sense not as line plot") applies to the
# SINGLE (1-ablation) cohort figure only (message-2 item M2-08 names DEMO_lineplot_shape_by_metaphase_single
# specifically). The comparison itself is a tercile split (fastest vs slowest third of metaphase duration),
# not a continuous function of time -- drawing it as per-cell LINE traces over time implies a continuity the
# comparison doesn't have. The underlying per-cell data is UNCHANGED: it is the exact same per-cell rate
# (linear slope of roundness/area vs time-from-metaphase-onset) that already drove the trendline in the old
# line plot -- only now every cell's own rate is drawn as a point (box/violin per tercile) instead of hiding
# it inside one pooled trendline. The "triple" cohort figure is untouched (not named in her feedback).
def _violin_rates(ax, groups, ylab, ptitle):
    """groups = [(name, [per-cell slopes], color, mtag), ...]. Box+violin+jittered per-cell points, matching
    the site-wide violin() convention used elsewhere (custom_plots_to_make_20260722.py) for tercile/binned
    comparisons: violin body + median bar + individual points, N in the tick label."""
    from scipy import stats as _stats
    xt=[]
    for i,(name,vals,color,mtag) in enumerate(groups):
        v=np.array(vals,float)
        if len(v)==0:
            xt.append(f"{name}\nN=0"); continue
        if len(v)>1:
            for bd in ax.violinplot([v],positions=[i],widths=.7,showextrema=False)['bodies']:
                bd.set_facecolor(color); bd.set_alpha(.28); bd.set_edgecolor(color)
        ax.scatter(np.zeros(len(v))+i+(np.random.RandomState(0).rand(len(v))-.5)*.22,v,
                   s=lib.VIOLIN_DOT_S,color=color,alpha=.85,edgecolor="white",lw=.4,zorder=3)
        ax.hlines(np.median(v),i-.32,i+.32,color=color,lw=2.4,zorder=4)
        xt.append(f"{name}\nN={len(v)} ({mtag})")
    ax.axhline(0,color="#999",lw=.8,ls=":",zorder=1)
    ax.set_xticks(range(len(groups))); ax.set_xticklabels(xt,fontsize=8.5)
    ax.set_ylabel(ylab); ax.set_title(ptitle,loc="left",fontweight="bold",fontsize=10)
    v0=[g[1] for g in groups if len(g[1])>0]
    if len(v0)==2 and len(v0[0])>=2 and len(v0[1])>=2:
        u,p=_stats.mannwhitneyu(v0[0],v0[1])
        ax.text(.5,1.13,f"Mann-Whitney fastest vs slowest: p={p:.3g}",transform=ax.transAxes,ha="center",fontsize=8.5,color="#333")

for slug,clabel,fast,slow,c_fast,c_slow in COHORTS:
    GROUPS=[("fastest 1/3", fast, c_fast, mlab(fast,"fast")),
            ("slowest 1/3", slow, c_slow, mlab(slow,"slow"))]
    as_violin = (slug=="single")
    fig,axes=plt.subplots(1,2,figsize=(13 if as_violin else 15,6))
    _prov=defaultdict(list)
    for ax,(trd,ylab,ptitle,ylim) in zip(axes,PAN):
        metric="round" if trd is Rtr else "area"
        rate_groups=[]
        for name,members,color,mtag in GROUPS:
            allpts=[]; cell_slopes=[]
            for b in members:
                arr=sorted(trd.get(b,[]))
                if len(arr)<2: continue
                allpts+=arr
                a=np.array(arr); sl,_=np.polyfit(a[:,0],a[:,1],1); cell_slopes.append(sl)  # per-cell rate; cell = unit
                if not as_violin: lib.cell_line(ax,a[:,0],a[:,1],color,alpha=.16,lw=1,zorder=1)
                _prov[metric]+=[[b,name,round(t,3),round(v,4)] for t,v in arr]
            rate_groups.append((name,cell_slopes,color,mtag))
            # Trendline from PER-CELL slopes (median), NOT pooled OLS over all timepoints.
            # Pooling frames pseudoreplicates + lets between-cell baseline differences flip the slope sign
            # (Simpson's paradox); median per-cell slope also resists single-cell segmentation outliers.
            if (not as_violin) and cell_slopes and len(allpts)>=2:
                arr=np.array(allpts)
                mslope=float(np.median(cell_slopes))
                mx=float(np.median(arr[:,0])); my=float(np.median(arr[:,1])); c=my-mslope*mx
                xx=np.array([0.0,arr[:,0].max()])
                ax.plot(xx,mslope*xx+c,color=color,lw=3.2,zorder=5,
                        label=f"{name}  N={len(cell_slopes)} cells ({mtag}), median slope={mslope:.3g}/min")
        if as_violin:
            _violin_rates(ax,rate_groups,f"per-cell rate of {ylab} (slope, /min)",ptitle+" — per-cell rate")
            continue
        ax.set_xlabel("Time from metaphase onset (min)"); ax.set_ylabel(ylab); ax.set_title(ptitle)
        if ylim: ax.set_ylim(*ylim)
        ax.set_xlim(left=0); ax.legend(fontsize=8,loc="best",framealpha=.9)
    if as_violin:
        fig.suptitle(f"Cell shape through metaphase — per-cell rate of change, fastest vs slowest metaphase thirds, {clabel}\n"
                     f"(binned comparison shown as box/violin per tercile, not a line plot — same per-cell rates that drove the old trendline)",fontsize=11)
    else:
        fig.suptitle(f"Cell shape through metaphase (onset to anaphase) — fastest vs slowest metaphase thirds, {clabel}",fontsize=12)
    fig.tight_layout()
    stem=f"DEMO_lineplot_shape_by_metaphase_{slug}"
    png=os.path.join(OUT,stem+".png")
    fig.savefig(png,dpi=150); fig.savefig(os.path.join(OUT,"illustrator",stem+".svg"))
    plt.close(fig); print("wrote",png)

    for metric in ("round","area"):
        _cap = (f"DEMO shape through metaphase — per-cell RATE (box/violin), fastest/slowest metaphase thirds, {clabel} "
                f"(rebuilt 2026-08-03, feedback M2-08: binned comparison, not a line plot)") if as_violin else \
               f"DEMO shape through metaphase — fastest/slowest metaphase thirds, {clabel}"
        lib.record_plot(stem if metric=="round" else stem+"_area",
            ["batch","group","time_from_metaphase_min","value"],_prov[metric],
            {"type":("per-cell rate (slope) of shape metric, shown as box/violin per tercile -- same "
                     "per-frame trace data as before, just visualized as its own per-cell summary statistic "
                     "instead of a per-cell line-over-time" if as_violin else
                     "shape through metaphase, fastest/slowest metaphase thirds within one ablation-number cohort"),
             "x":"time from Metaphase Start (min); window [Metaphase Start, Anaphase Onset]","metric":metric,
             "cohort":clabel,"groups":f"{clabel} x {{fastest third, slowest third}} by metaphase duration",
             "exclusion":"lib.plot_excluded (drug/Exclude/metaphase/4-sis dropped)"},
            __file__,_cap,
            source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])
print("done")
