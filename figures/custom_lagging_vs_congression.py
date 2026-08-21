"""#42 — Does congression TIMING relate to anaphase LAGGING? Per-cell congression delay (from the consolidated
CHROMOSOME_ANNOTATIONS_MASTER) vs the master 'Lagging Chromosomes' call, overall and split by 1- vs 2/3-sisterless.
Honest result: trend only (lagging cells tend to have a later-congressing chromosome; permanently-polar KTs rarely lag).
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict, Counter
from scipy import stats
import lib

# ---------------------------------------------------------------------------------------------------
# REVIEW_EXCLUDE CARVE-OUT — HER DECISION, 2026-08-18. DO NOT "FIX" THIS.
# `20251029 triple_ablation_12` is in `lib.REVIEW_EXCLUDE` (the blanket outlier list) yet appears in the
# two figures this file builds — `G3_lagging_behavior_composition` and
# `G3_lagging_vs_congression_timing_fraction`. An audit flagged that as an inconsistency; she looked at it
# and said to keep the cell in **these two analyses only**:
#     "including 20251029 triple_ablation_12 in the lagging analysis you mention is ok
#      (but just those named analyses)."
# So this builder deliberately does NOT call lib.excluded()/plot_excluded() for the review list. If you are
# here to make the exclusions consistent, that consistency stops at this file.
# ---------------------------------------------------------------------------------------------------
ALLOW_REVIEW_EXCLUDED = ("20251029 triple_ablation_12",)   # documented above; kept by her instruction

OUT="/Volumes/4 MB/ablation_figures_20260625/group3"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
SRC="/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv"
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def gv(b,c): return (mr.get(b,{}).get(c,"") or "").strip()
def nsis(b):
    v=gv(b,'# Sisterless KTs'); return int(v) if v.isdigit() else None
def lag(b):
    v=gv(b,'Lagging Chromosomes').lower()
    return 1 if v.startswith('y') else 0 if v.startswith('n') else None

# 2026-08-03: this read `congression_delay_from_meta_onset_s`, a column CHROMOSOME_MASTER.csv NO LONGER
# HAS -- it is now `congression_time_s` (+ `congression_hms`). csv.DictReader returns '' for the missing
# key, so every delay came back None, both panels of G3_lagging_vs_congression_timing drew EMPTY, and the
# composition figure collapsed its 'late' category into 'early'. Silent, because nothing errors.
# The old column was already relative to metaphase onset; the new one is ELAPSED FROM FRAME 0 (the
# standing rule for manual time columns), so the delay has to be derived per cell:
#     delay = congression_time_s - Metaphase Start (s)
# Cells with no Metaphase Start are dropped and counted rather than silently treated as delay 0.
_nometa=set()
chrom=defaultdict(list)
for r in csv.DictReader(open(SRC)):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    b=r['batch'].strip()
    d=(r.get('congression_time_s','') or '').strip()
    delay=None
    if d:
        _ms=lib.parse_time(gv(b,'Metaphase Start (s)'))
        if _ms is None: _nometa.add(b)
        else:
            delay=float(d)-_ms
            # ITEM 19 (user 2026-08-04): "remove points that start at a negative time for congression delay
            # (I just want points that are after the start of metaphase)." A negative delay means the
            # chromosome reached the plate BEFORE metaphase onset, so it never had a congression delay
            # within metaphase at all. Applied to BOTH this figure and the fraction version below.
            if delay<0:
                lib.log_review("congression_delay_negative",b,f"{delay/60:.2f} min",
                               "congressed before metaphase onset — dropped (ITEM 19)")
                delay=None
    chrom[b].append(dict(bh=r.get('behavior','').strip() or None,delay=delay))
if _nometa: print(f"  {len(_nometa)} batch(es) have a congression time but no Metaphase Start -> delay dropped")
cell=[]
for b,cs in chrom.items():
    if gv(b,'On-Target / Off-Target').lower()!='on-target': continue
    L=lag(b)
    if L is None: continue
    dl=[c['delay'] for c in cs if c['bh']=="congressed" and c['delay'] is not None]
    beh=[c['bh'] for c in cs if c['bh']]
    cell.append(dict(b=b,lag=L,meandelay=(np.mean(dl) if dl else None),maxdelay=(max(dl) if dl else None),
                     npolar=sum(1 for x in beh if x=="noncongression"),nbeh=len(beh),
                     grp=('1' if nsis(b)==1 else '2/3' if nsis(b) in (2,3) else None)))

def boxstrip(ax,groups,labels,colors,ylab,title):
    ps=[]
    for i,(g,lab,col) in enumerate(zip(groups,labels,colors)):
        x=i+1; v=[y for y in g if y is not None]
        if not v: continue
        ax.boxplot([v],positions=[x],widths=.55,patch_artist=True,boxprops=dict(facecolor=col,alpha=.22,edgecolor=col),
                   medianprops=dict(color=col,lw=2),whiskerprops=dict(color=col),capprops=dict(color=col),showfliers=False)
        jit=(np.random.RandomState(i).rand(len(v))-.5)*.28; ax.scatter(np.full(len(v),x)+jit,v,s=26,color=col,alpha=.75,edgecolor="white",lw=.3)
        ax.text(x,np.median(v),f"  {np.median(v):.1f}\n  n={len(v)}",ha="left",va="center",fontsize=8,color=col)
    ax.set_xticks(range(1,len(labels)+1)); ax.set_xticklabels(labels,fontsize=9); ax.set_ylabel(ylab); ax.set_title(title,fontsize=10)

fig,(axA,axB)=plt.subplots(1,2,figsize=(12.4,5.2))
# A: max congression delay by lagging (overall)
lp=[c['maxdelay']/60 for c in cell if c['lag']==1 and c['maxdelay'] is not None]
ln=[c['maxdelay']/60 for c in cell if c['lag']==0 and c['maxdelay'] is not None]
u=stats.mannwhitneyu(lp,ln) if (len(lp)>=3 and len(ln)>=3) else None
boxstrip(axA,[ln,lp],["no lagging","lagging"],["#2166ac","#b2182b"],
         "latest congression delay in cell (min)",
         "Latest-congressing chromosome vs lagging"+(f"\nMWU p={u.pvalue:.2g}, N={len(ln)+len(lp)}" if u else ""))
# B: same, split by sisterless group
g=[]
for grp in ['1','2/3']:
    for L in [0,1]:
        g.append([c['maxdelay']/60 for c in cell if c['grp']==grp and c['lag']==L and c['maxdelay'] is not None])
boxstrip(axB,g,["1-sis\nno lag","1-sis\nlag","2/3-sis\nno lag","2/3-sis\nlag"],
         ["#6baed6","#fb6a4a","#2166ac","#b2182b"],"latest congression delay (min)","Split by # sisterless KTs (small N)")
fig.suptitle("#42  Congression timing vs anaphase lagging — CHROMOSOME_ANNOTATIONS_MASTER (on-target)",
             fontweight="bold",fontsize=11.5,x=.01,ha="left")
plt.tight_layout(rect=[0,0,1,0.95]); plt.savefig(f"{OUT}/G3_lagging_vs_congression_timing.png",bbox_inches="tight",dpi=135)
plt.savefig(f"/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_lagging_vs_congression_timing.pdf",bbox_inches="tight"); plt.close()
# 2026-08-03: record_plot was called with a LITERAL EMPTY LIST, so the figure had no plot spreadsheet at
# all -- the same fault class as the 2026-07-29 empty-row bug. Write the rows the figure actually draws.
lib.record_plot("G3_lagging_vs_congression_timing",["batch","lagging","maxdelay_s","maxdelay_min","grp"],
                [[c['b'],c['lag'],round(c['maxdelay'],1),round(c['maxdelay']/60,2),c['grp'] or ""]
                 for c in cell if c['maxdelay'] is not None],
                {"source":"CHROMOSOME_MASTER.csv","MWU_p":round(u.pvalue,4) if u else None,
                 "N_cells":len(cell),"N_with_delay":sum(1 for c in cell if c['maxdelay'] is not None)},
                SCRIPT,"Congression timing vs lagging")

# second figure: CONGRESSION-TIMING composition by lagging — the full spectrum the user asked about:
# already at the plate at metaphase start (at_plate, delay<=0) -> congressed early -> congressed late -> never.
# at_plate delays are negative (reached plate BEFORE metaphase onset); congressed are positive (during metaphase).
_congd=[c['delay'] for b in chrom for c in chrom[b] if c['bh']=="congressed" and c['delay'] is not None]
MED=np.median(_congd) if _congd else 600.0    # split congressed into early vs late at the median delay
def tcat(x):
    if x['bh']=="at_plate": return 'already'            # already congressed at/before metaphase start
    if x['bh']=="noncongression": return 'never'         # stayed polar to anaphase
    if x['bh']=="congressed": return 'early' if (x['delay'] is None or x['delay']<=MED) else 'late'
    return None
fig2,ax=plt.subplots(figsize=(7.4,5.2))
CATS=[("already","already at plate\n(before metaphase)","#1b7837"),
      ("early",f"congressed early\n(≤{MED/60:.0f} min)","#66c2a5"),
      ("late",f"congressed late\n(>{MED/60:.0f} min)","#2166ac"),
      ("never","never congressed\n(polar)","#762a83")]
for i,L in enumerate([0,1]):
    sub=[c for c in cell if c['lag']==L]; allc=[]
    for c in sub:
        allc+= [tcat(x) for x in chrom[c['b']] if x['bh']]
    tot=len([a for a in allc if a]) or 1; cc=Counter(a for a in allc if a); bottom=0
    for k,lab,col in CATS:
        frac=cc[k]/tot; ax.bar(i,frac,bottom=bottom,color=col,edgecolor="white",width=.6,label=(lab if i==0 else None))
        if frac>.04: ax.text(i,bottom+frac/2,f"{100*frac:.0f}%",ha="center",va="center",color="white",fontsize=9,fontweight="bold")
        bottom+=frac
    ax.text(i,1.02,f"n={tot} chrom",ha="center",fontsize=8,color="#555")
ax.set_xticks([0,1]); ax.set_xticklabels(["no lagging","lagging"]); ax.set_ylabel("fraction of ablated chromosomes")
ax.set_ylim(0,1.12); ax.legend(fontsize=8,loc="center left",bbox_to_anchor=(1.01,.5))
ax.set_title("Congression TIMING composition by lagging\n(already-at-plate → early → late → never)",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G3_lagging_behavior_composition.png",bbox_inches="tight",dpi=135)
plt.savefig(f"/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_lagging_behavior_composition.pdf",bbox_inches="tight"); plt.close()
lib.record_plot("G3_lagging_behavior_composition",["batch","lagging","behavior","delay_s","timing_category"],
                [[c['b'],c['lag'],x['bh'],(round(x['delay'],1) if x['delay'] is not None else ""),tcat(x)]
                 for c in cell for x in chrom[c['b']] if x['bh']],
                {"source":"CHROMOSOME_MASTER.csv","median_split_s":round(MED,1)},
                SCRIPT,"Congression-timing composition by lagging")

print(f"built #42 | cells with lag+behavior: {len(cell)} (lag+ {sum(c['lag'] for c in cell)}, lag- {sum(1-c['lag'] for c in cell)})")
print(f"  max-delay lag+ median={np.median(lp):.1f} vs lag- {np.median(ln):.1f} min; MWU p={u.pvalue:.3g}" if u else "  (insufficient N)")


# ── ITEM 19 (user 2026-08-04): fraction-through-metaphase version ─────────────────────────────────
# "create version where you just keep the left plot and instead of using minutes use fraction through
#  metaphase." Single panel (the overall lagging vs no-lagging comparison), x expressed as the fraction of
# that cell's own metaphase elapsed at the LATEST congression — the 0-1 convention used by
# G4_lagging_vs_congression_fraction. Negative delays are already dropped upstream (same item).
def _fraction_version():
    def meta_dur_min(b):
        d=lib.parse_time(gv(b,'Meta Duration (s)'))
        if d is None or d<=0:
            m0=lib.parse_time(gv(b,'Metaphase Start (s)')); a0=lib.parse_time(gv(b,'Anaphase Onset (s)'))
            d=(a0-m0) if (m0 is not None and a0 is not None) else None
        return d/60.0 if d and d>0 else None
    lp,ln,rows=[],[],[]
    for c in cell:
        if c['maxdelay'] is None: continue
        dur=meta_dur_min(c['b'])
        if not dur: continue
        fr=(c['maxdelay']/60.0)/dur
        if fr>1.05: continue                      # congressed after anaphase onset
        fr=min(fr,1.0)
        (lp if c['lag']==1 else ln).append(fr)
        rows.append([c['b'],'lagging' if c['lag']==1 else 'no lagging',round(fr,4),round(dur,2)])
    if len(lp)<3 or len(ln)<3:
        print(f"ITEM 19 fraction version skipped — n lag={len(lp)} nolag={len(ln)}"); return
    u=stats.mannwhitneyu(lp,ln)
    fig,ax=plt.subplots(figsize=(6.6,5.2))
    boxstrip(ax,[ln,lp],["no lagging","lagging"],["#2166ac","#b2182b"],
             "Latest sisterless-KT congression\n(fraction of metaphase elapsed: 0=onset, 1=anaphase)",
             f"Does the last chromosome congress LATER in cells that lag?\nMWU p={u.pvalue:.2g}, N={len(ln)+len(lp)}")
    ax.set_ylim(-0.03,1.03)
    fig.suptitle("ITEM 19 — fraction-through-metaphase version (left panel only; points congressing before "
                 "metaphase onset removed)",x=.01,ha="left",fontweight="bold",fontsize=8.8)
    plt.tight_layout(rect=[0,0,1,0.94])
    plt.savefig(f"{OUT}/G3_lagging_vs_congression_timing_fraction.png",bbox_inches="tight",dpi=135)
    plt.savefig("/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf/G3_lagging_vs_congression_timing_fraction.pdf",bbox_inches="tight")
    plt.close()
    lib.record_plot("G3_lagging_vs_congression_timing_fraction",
                    ["batch","lagging","frac_meta_to_ana","meta_duration_min"],rows,
                    {"item19":"left panel only; x is fraction of metaphase elapsed, not minutes; "
                              "negative congression delays removed",
                     "test":f"Mann-Whitney p={float(u.pvalue):.4g}",
                     "y_label":"Latest congression (fraction of metaphase elapsed: 0=onset, 1=anaphase)"},
                    SCRIPT,"Latest congression as a fraction of metaphase, lagging vs no lagging")
    print(f"ITEM 19 fraction version: nolag={len(ln)} lag={len(lp)} p={u.pvalue:.3g}")

_fraction_version()
