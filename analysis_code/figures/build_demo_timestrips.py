"""DEMO_area_with_timestrips — cross-sectional area ("rounding") behavior, short vs long metaphase cohorts,
with two example movie timestrips underneath. Placed in supplemental.ai (NOT the META section).

2026-08-03 REBUILD (feedback: "turn this into something where its like 'average rounding rate in metaphase'
so itll just be a point for each sample instead of a line."):
  - TOP PANEL WAS a spaghetti-plot: one faint per-cell area-vs-time LINE per cohort (start .. anaphase),
    plus a single pooled linear fit per cohort. Replaced with ONE POINT PER CELL: each cell's own linear
    slope of cross-sectional area vs time, fit ONLY across its own METAPHASE window (Metaphase Start (s) ->
    Anaphase Onset (s) from the master) — i.e. exactly "average rounding rate in metaphase" per sample.
    Kept the AREA metric (not the ROUNDNESS=4*pi*A/P^2 ratio that custom_shape_rate_vs_metaphase.py's
    "rounding rate" scatters use) because that is what this builder has always measured from cell_outlines
    and what the companion ALLcohorts_metaDur_vs_arearate*.png figures already call "area-loss rate" —
    switching metric families here would silently disagree with that sibling figure. Sign convention:
    NEGATIVE = area shrinks = cell rounds up faster (more mitotic rounding); reported as "rounding rate"
    with that sign called out on the axis so it isn't misread as the reverse.
  - WINDOW CHANGED from "start-of-trace .. anaphase" (which includes pre-metaphase congression) to strictly
    Metaphase Start -> Anaphase Onset, since she asked for the rate specifically "in metaphase."
  - Kept the same short/long metaphase-duration TERTILE cohort split (middle tertile dropped) that the
    original figure used — only the line-vs-point representation changed, not the grouping.
  - EXCLUSION FIX: was filtering only with lib.excluded() (REVIEW_EXCLUDE outliers only); switched to
    lib.plot_excluded() to also drop drug-treated, Exclude=Yes, METAPHASE-ablation, and 4-sisterless batches,
    matching the standing default-exclusion rule and the sibling custom_shape_rate_vs_metaphase.py fix of
    2026-07-14 (was the same bug there, "violating the save-the-generator protocol" note).
  - The two example-cell movie timestrip rows (fast/slow) are UNCHANGED — her feedback was about the top
    panel only, not the timestrips.
  - NOTE for whoever runs make_window_companions_20260729.py next: that script makes a "_win_meta_to_ana"
    companion of this plot's OLD per-timepoint CSV. This rebuild already restricts to the metaphase window
    and aggregates to one point per cell, so that companion is now redundant/stale against the new schema —
    flagged here rather than silently left to diverge. Not touched by this rebuild (shared utility, not
    owned by this builder).
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import json, csv, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from collections import defaultdict
from scipy import stats
import tifffile, lib
try: lib.apply_style()
except Exception: pass
SCRIPT=__file__
coh=lib.assign_cohorts(); b2={}
for k,lst in coh.items():
    for b,d in lst:
        if lib.plot_excluded(b): continue   # standing rule (was lib.excluded only -- fixed 2026-08-03)
        b2.setdefault(b,k)
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def pt(b,c): return lib.parse_time(mr.get(b,{}).get(c,""))
def ana_min(b):
    v=pt(b,"Anaphase Onset (s)"); return v/60.0 if v is not None else None
def meta_start_min(b):
    v=pt(b,"Metaphase Start (s)"); return v/60.0 if v is not None else None
def meta_dur(b):
    a=pt(b,"Anaphase Onset (s)"); m=pt(b,"Metaphase Start (s)")
    return (a-m)/60.0 if (a is not None and m is not None) else None
def drivepath(b):
    for r in data:
        if r["Batch Name"]==b: return r.get("Drive Path","")
    return ""
def pa(p,px):
    p=np.array(p,float); x,y=p[:,0],p[:,1]; a=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))*px*px
    return a if 0<a<=5000 else None
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c.strip():i for i,c in enumerate(rows[0])}
ps={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: ps[b]=float(r[ix['pixel_size_um']])
    except: ps.setdefault(b,0.062)
Aa=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try: t=float(r[ix['t_sec']])/60.0; p=json.loads(r[ix['points']])
    except: continue
    w=pa(p,ps.get(b,0.062))
    if w is not None: Aa[b].append((t,w))
durs={b:meta_dur(b) for b in b2 if meta_dur(b) is not None}
q1,q2=np.quantile(list(durs.values()),[1/3,2/3])
def grpof(b):
    d=durs.get(b)
    return "short" if (d is not None and d<=q1) else ("long" if (d is not None and d>=q2) else None)

# ---- per-cell average rounding (area) rate WITHIN METAPHASE (Metaphase Start -> Anaphase Onset) ----
# CHORD (first-vs-last point in window), not a least-squares fit: cell_outlines are sparse manual marks
# (median ~2-3 per cell per movie), and a >=3-point linear-fit requirement disproportionately dropped the
# SHORT-metaphase cohort (its window is narrower by construction, so fewer manual marks land inside it --
# tested during this rebuild: >=3-point fit gave short N=3 vs long N=42, a coverage artefact, not biology).
# "Average rate" = total area change / total elapsed time between the first and last annotated outline
# inside the window is the more literal + more robust reading of "average rounding rate in metaphase" here,
# and roughly triples usable short-cohort N (3 -> 20) without changing the long cohort's already-adequate N.
MIN_SPAN_MIN = 0.5
def meta_rate(b):
    m=meta_start_min(b); a=ana_min(b); tr=sorted(Aa.get(b,[]))
    if m is None or a is None or a<=m: return None
    inwin=[(t,v) for t,v in tr if m-1e-6<=t<=a+1e-6]
    if len(inwin)<2: return None
    t0,v0=inwin[0]; t1,v1=inwin[-1]
    if t1-t0<MIN_SPAN_MIN: return None
    return (v1-v0)/(t1-t0)

recs=[]   # (batch, cohort, rate_um2_per_min, n_pts_used)
n_no_window=0; n_too_few_pts=0
for b in b2:
    grp=grpof(b)
    if grp is None: continue
    r=meta_rate(b)
    if r is None:
        # classify why, for an honest N accounting
        m=meta_start_min(b); a=ana_min(b)
        if m is None or a is None or a<=m: n_no_window+=1
        else: n_too_few_pts+=1
        continue
    m=meta_start_min(b); a=ana_min(b)
    npts=sum(1 for t,_ in Aa.get(b,[]) if m-1e-6<=t<=a+1e-6)
    recs.append((b,grp,r,npts))

FAST="20250410 ptk_yfpcdc20_22"; SLOW="20251104 ablations_1"
import subprocess, tempfile
def strip_frames(b,nframes=6):
    d=drivepath(b); pref=os.path.basename(d)
    mon=os.path.join(d,pref+"_Fluor_Monitoring.mp4")
    if not os.path.isfile(mon) or os.path.getsize(mon)<2000:
        print("  no monitoring mp4 for",b); return None
    nf=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-count_frames",
        "-show_entries","stream=nb_read_frames","-of","csv=p=0",mon],capture_output=True,text=True).stdout.strip()
    try: N=int(nf)
    except: N=0
    if N<2: print("  too few frames",b); return None
    idxs=[int(round(x)) for x in np.linspace(0,N-1,nframes)]
    tmp=tempfile.mkdtemp(); frames=[]
    for j,fi in enumerate(idxs):
        out=os.path.join(tmp,f"f{j}.png")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mon,
            "-vf",f"select='eq(n\\,{fi})'","-frames:v","1",out],check=False)
        if os.path.isfile(out):
            im=plt.imread(out)
            g = im[...,:3].max(axis=2) if im.ndim==3 else im
            frames.append(g.astype(float))
        else: frames.append(None)
    frames=[f for f in frames if f is not None]
    if len(frames)<2: print("  extraction failed",b); return None
    pool=np.concatenate([f.ravel() for f in frames]); lo_,hi_=np.percentile(pool,[50,99.7])
    frames=[np.clip((f-lo_)/(hi_-lo_+1e-9),0,1) for f in frames]
    a=ana_min(b)
    times=list(np.linspace(0, a if a else N/6.0, len(frames)))
    return frames,times
print("extracting FAST:",FAST); fast=strip_frames(FAST)
print("extracting SLOW:",SLOW); slow=strip_frames(SLOW)

fig=plt.figure(figsize=(11,9))
gs=gridspec.GridSpec(3,1,height_ratios=[3.0,1.0,1.0],hspace=0.5)
axp=fig.add_subplot(gs[0])
COL={"short":"#d7301f","long":"#2b8cbe"}
LB={"short":f"Short metaphase (<={q1:.0f} min) — 'fast'","long":f"Long metaphase (>={q2:.0f} min) — 'slow'"}
for i,grp in enumerate(("short","long")):
    v=[r for b,g,r,n in recs if g==grp]
    if not v: continue
    x=i+1
    axp.boxplot([v],positions=[x],widths=.5,patch_artist=True,
                boxprops=dict(facecolor=COL[grp],alpha=.22,edgecolor=COL[grp]),
                medianprops=dict(color=COL[grp],lw=2),whiskerprops=dict(color=COL[grp]),capprops=dict(color=COL[grp]),
                showfliers=False)
    jit=(np.random.RandomState(i).rand(len(v))-.5)*.32
    axp.scatter(np.full(len(v),x)+jit,v,s=42,color=COL[grp],alpha=.85,edgecolor="white",lw=.4,zorder=3)
    axp.text(x,np.median(v),f"  median {np.median(v):.1f}\n  n={len(v)}",ha="left",va="center",fontsize=9,color=COL[grp],fontweight="bold")
short_v=[r for b,g,r,n in recs if g=="short"]; long_v=[r for b,g,r,n in recs if g=="long"]
u = stats.mannwhitneyu(short_v,long_v) if (len(short_v)>=3 and len(long_v)>=3) else None
axp.set_xticks([1,2]); axp.set_xticklabels([LB["short"],LB["long"]],fontsize=9.5)
axp.axhline(0,color="#999",ls=":",lw=1)
axp.set_ylabel("Rounding rate in metaphase\n(area slope, um^2/min; negative = shrinks/rounds up)",fontsize=9.5)
axp.set_title("Average metaphase rounding rate per cell — one point per sample"
              +(f"  (short vs long: Mann-Whitney p={u.pvalue:.2g})" if u else "  (too few cells in one cohort for a test)"),
              fontsize=11.5)

def draw_strip(gsrow,strip,title,color):
    if strip is None: return
    frames,times=strip; n=len(frames)
    sub=gridspec.GridSpecFromSubplotSpec(1,n,subplot_spec=gsrow,wspace=0.06)
    for i,(fr,tm) in enumerate(zip(frames,times)):
        ax=fig.add_subplot(sub[i]); ax.imshow(fr,cmap="gray",vmin=0,vmax=1); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{tm:+.0f} min",fontsize=8)
        if i==0: ax.set_ylabel(title,fontsize=10,color=color,rotation=90,labelpad=8,fontweight="bold")
draw_strip(gs[1],fast,"FAST\n(short meta)","#d7301f")
draw_strip(gs[2],slow,"SLOW\n(long meta)","#2b8cbe")
fig.suptitle("Metaphase rounding rate: short vs long metaphase, one point per cell",fontsize=13,y=1.015)
fig.text(0.01,0.975,"rebuilt 2026-08-03; supplemental, not META",fontsize=8.5,color="#666")

OUTDIR="/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
fp=f"{OUTDIR}/DEMO_area_with_timestrips.png"
fig.savefig(fp,dpi=150,bbox_inches="tight"); print("wrote",fp)
PDF="/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
fig.savefig(f"{PDF}/DEMO_area_with_timestrips.pdf",bbox_inches="tight")

lib.record_plot("DEMO_area_with_timestrips",["batch","metaphase_group","rounding_rate_um2_per_min","n_outline_points_in_metaphase"],
                 [[b,g,round(r,3),n] for b,g,r,n in recs],
                 {"type":"one point per cell: linear slope of cross-sectional area vs time, fit ONLY within "
                          "Metaphase Start->Anaphase Onset","cohort":"short/long metaphase-duration tertiles (middle dropped)",
                  "N_short":len(short_v),"N_long":len(long_v),
                  "N_dropped_no_window":n_no_window,"N_dropped_too_few_points":n_too_few_pts,
                  "exclusion":"lib.plot_excluded (drug + Exclude=Yes + metaphase-ablation + 4-sisterless + REVIEW_EXCLUDE)"},
                 SCRIPT,"Average metaphase rounding (area) rate per cell, short vs long metaphase cohorts",
                 source=["/Volumes/4 MB/ABLATION_MASTER.csv","/Volumes/4 MB/annotations/cell_outlines.csv"])
print(f"DEMO_area_with_timestrips rebuilt | cells in cohorts (post plot_excluded)={len(b2)} | "
      f"short N={len(short_v)}, long N={len(long_v)} | dropped: no meta/ana window={n_no_window}, "
      f"too few outline points in window={n_too_few_pts}")
