"""cell roundness / cross-sectional area over mitosis (split + combined) + start-rounded vs duration.

Feedback pass 2026-07-06:
 - trends & individual traces stop at ANAPHASE ONSET (no cytokinesis); per-cell clip at master Anaphase Onset (s).
 - per-group dashed line = the group MEDIAN time-to-anaphase; the trend stops there and never runs past it
   (user 2026-08-10). It was the MEAN until then, which sits past the median and let the trend overrun.
 - unmodified group is referenced to NEBD (x = time from NEBD), labelled "from NEBD", and only unmodified cells
   with a recorded NEBD Time are shown; all other groups keep time-from-first-ablation (prophase+prometaphase).
 - Destruction-of-two-KTs-on-one-chromosome (Double Chromosome) is dropped everywhere (cohort is globally empty).
 - start-rounded plots merge the 1/2/3-sisterless off-target controls into ONE off-target group.
 - proper per-group Spearman stats grid for the shape-at-metaphase-onset plot.
The outline t_sec clock == master event clock (verified: nearest_event 'Anaphase' == master Anaphase Onset).
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import os, json, csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
import lib
import metaphase_medians
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT=__file__

# USER 2026-08-19 (figure item 5): the per-group median line must come from the MAIN VIOLIN PLOT on artboard 2,
# not from the cells in whichever line plot is being drawn. One canonical table, imported everywhere.
_CANON_MED = metaphase_medians.medians()
_CANON_N   = metaphase_medians.counts()
print(f"  canonical group medians (from the artboard-2 violin): "
      + ", ".join(f"{k}={v:.2f}min(n={_CANON_N[k]})" for k, v in sorted(_CANON_MED.items())))

coh=lib.assign_cohorts()

# ── USER 2026-08-16, artboard-4 line plots ───────────────────────────────────────────────────────
# "remove lines for the 2-sisterless cells, and then add a line for the WITH collagen samples ...
#  specifically the on-target 2-3 with collagen samples that are in those respective plots on artboard 4
#  ... so that i can essentially condense those collagen-specific plots into the other plots for brevity
#  and space."
# Collagen is a plating SUBSTRATE, not a drug (feedback_collagen_not_a_drug_exclusion), so these cells are
# NOT excluded by lib.is_drug and already sit inside the 2-/3-Sister cohorts. Giving them their own line
# therefore means MOVING them out of those cohorts, not adding them again — otherwise every collagen cell
# would be counted twice. Membership matches the standalone collagen figures on this board
# (collagen_vs_triple_2or3_ontarget_*): on-target, 2 or 3 sisterless, "collagen" in the batch name.
COLLAGEN_KEY = "Collagen (2/3-sis on-target)"
coh[COLLAGEN_KEY] = []
for _src in ("2-Sister", "3-Sister"):
    _keep = []
    for _e in coh.get(_src, []):
        _b = _e[0] if isinstance(_e, (list, tuple)) else _e
        if "collagen" in str(_b).lower(): coh[COLLAGEN_KEY].append(_e)
        else: _keep.append(_e)
    coh[_src] = _keep
lib.PALETTE.setdefault(COLLAGEN_KEY, "#e69f00")     # amber: distinct from the greens/purples, CB-safe
lib.LABEL.setdefault(COLLAGEN_KEY, "collagen (2/3-sis)")
print(f"  collagen cohort split out: {len(coh[COLLAGEN_KEY])} cells "
      f"(2-Sister now {len(coh.get('2-Sister',[]))}, 3-Sister now {len(coh.get('3-Sister',[]))})")
b2={}
for k,lst in coh.items():
    for b,d in lst:
        if lib.excluded(b): continue   # global user-flagged outliers (lib.REVIEW_EXCLUDE) out of every loop below (all iterate b2)
        b2.setdefault(b,(k,d))

def poly_roundness(pts):
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]
    A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))));
    if per==0: return None
    r=4*np.pi*A/per**2; return r if 0<r<=1.2 else None

rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c:i for i,c in enumerate(rows[0])}
traces=defaultdict(list)
# 🔴 2026-08-25: MONITORING-CLIP MARKS ONLY. A cell's ablation clip has its own clock (t=0 at the ablation,
# ~3 s/frame against the monitoring clip's 20 s/frame), so an ablation-clip outline read as a monitoring
# t_sec lands a few seconds either side of zero -- right where every delta plot looks for its t=0 baseline.
# 149 of 189 outlined cells mix the two clips and 14 were being baselined on a mark from the wrong movie.
# These traces are referenced to master event times, which are monitoring-clock, so the ablation-clip rows
# do not belong in them at all. See lib.annotation_clip.
_skipped_clip = 0
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    if lib.annotation_clip(r[ix['video_file']] if 'video_file' in ix else "") == "ablation":
        _skipped_clip += 1; continue
    try: t=float(r[ix['t_sec']])/60.0; rd=poly_roundness(json.loads(r[ix['points']]))
    except: continue
    if rd is None or abs(t)>600: continue
    traces[b].append((t,rd))
if _skipped_clip:
    print(f"  dropped {_skipped_clip} ablation-clip outline rows (different clock; see lib.annotation_clip)")

# ---------- master event times (outline clock == master clock) ----------
_data,_=lib.load_master_plots(); _mr={r["Batch Name"]:r for r in _data}
def ana_min(b):
    v=lib.parse_time(_mr.get(b,{}).get("Anaphase Onset (s)","")); return v/60.0 if v is not None else None
def neb_min(b):
    v=lib.parse_time(_mr.get(b,{}).get("NEB Time (s)","")); return v/60.0 if v is not None else None
def meta_min(b):
    v=lib.parse_time(_mr.get(b,{}).get("Metaphase Start (s)","")); return v/60.0 if v is not None else None
def is_unmod(g): return g=="unModified"

# cells with NO recorded anaphase can't "stop at anaphase" — bound their individual traces at 45 min from the
# reference event (beyond the observed anaphase-onset range) so they don't run into cytokinesis / out to 60-80min.
ANA_CLIP_FALLBACK=45.0
def ref_trace(b,g,tr,mode="ablation"):
    """Reference a cell's outline trace to its group event and clip at anaphase onset (drop cytokinesis).
    Returns (pts, ana_x) or None. pts=[(x,val)] with x in minutes from the reference event
    (first ablation for manipulated groups; NEBD for unmodified). ana_x = anaphase time on the x-axis
    (used for the per-group MEAN-time-to-anaphase dashed line). Unmodified w/o a recorded NEBD -> excluded.

    RA1 (2026-07-07): mode=="meta" -> reference EVERY cell (all groups incl. unmodified) to its own
    Metaphase Start(s) and plot metaphase-onset -> anaphase (x>=0). Cells with no recorded Metaphase
    Start are dropped. The mean-time dashed line then marks the group MEAN metaphase duration."""
    if not tr: return None
    a=ana_min(b)
    if mode=="abl2meta":
        # USER 2026-08-19 (figure item 1): "plots that have data before metaphase onset (so are currently
        # plotted as line plots referenced to a time of 0 as ablation), change so they just plot from ablation
        # to metaphase onset, but also adjust time calibration as metaphase should be set at t=0, and times
        # leading up to it negative."
        # So: the WINDOW is the ablation-to-metaphase run-up (everything at or before metaphase onset), and the
        # ORIGIN is metaphase onset -- the whole trace therefore sits at x <= 0. Unmodified cells have no
        # ablation, so their window simply starts at the first outline they have (NEBD is not required here;
        # requiring it would drop most of the unmodified cells, which is the inclusion mismatch _incl_note
        # already warns about).
        mt=meta_min(b)
        if mt is None: return None
        tr=[(t,v) for (t,v) in tr if t<=mt+1e-6]
        if len(tr)<2: return None
        return [(t-mt,v) for (t,v) in tr], None
    if mode=="meta":
        mt=meta_min(b)
        if mt is None: return None                                  # need a metaphase onset to anchor on
        # USER 2026-08-05: "make t=0 on the x-axis the metaphase start time. so its ok to have the time
        # have a negative range too to make sure all of the data on the original plots is in the ones with
        # a shifted x-axis". The lower bound used to be `mt<=t`, which ANCHORED at metaphase onset and also
        # THREW AWAY everything before it — G1_area_combined_meta_trendscaled carried 275 of the parent's
        # 723 points for that reason. Anchor without clipping: keep the pre-metaphase data at negative x.
        if a is not None: tr=[(t,v) for (t,v) in tr if t<=a+1e-6]              # ...-> anaphase, no lower cut
        else:             tr=[(t,v) for (t,v) in tr if t<=mt+ANA_CLIP_FALLBACK]
        if len(tr)<2: return None
        pts=[(t-mt,v) for (t,v) in tr]                              # metaphase onset at x=0
        ax_ana=(a-mt) if a is not None else None
        return pts,ax_ana
    if a is not None: tr=[(t,v) for (t,v) in tr if t<=a+1e-6]   # stop at anaphase, no cytokinesis
    else: tr=[(t,v) for (t,v) in tr if t<=ANA_CLIP_FALLBACK]     # no recorded anaphase: bound the trace so it doesn't run into cytokinesis/60-80min
    if len(tr)<2: return None
    if is_unmod(g):
        off=neb_min(b)
        if off is None: return None     # only unmodified imaged from prophase (recorded NEBD)
    else:
        off=0.0                         # already time-from-first-ablation
    pts=[(t-off,v) for (t,v) in tr]
    ax_ana=(a-off) if a is not None else None
    # ITEM F (2026-07-06): a lone sample whose first outline floats to the RIGHT of the reference event
    # (e.g. off-target ablation_47 first point ~6.5 min out, unmodified xy2 first point ~60 s out) looked
    # strange. Normalize any such trace left so its first point sits at x=0 (shift the whole cell — trace
    # AND its anaphase marker — together; negligible effect on the group mean line). Traces already at/<=0
    # (the ablation-referenced norm) are untouched.
    x0=pts[0][0]
    if x0>0.5:
        pts=[(x-x0,v) for (x,v) in pts]
        if ax_ana is not None: ax_ana-=x0
    return pts,ax_ana

def trend_to_mean(pts,md,nb=None,minpts=3,start=0.0):
    """Binned-mean trend over [start, md] that extends all the way to the group MEAN time md.
    Interior bins need >=minpts (smooth); a terminal point is appended at x=md from the last bin so the
    trend reaches the dashed mean line even if that bin is sparse.

    BUGFIX 2026-08-03 (user: G1_area_combined_meta_trendscaled 'data doesnt seem right' vs the ablation-
    anchored version, 'that makes more sense'). Root cause: nb was a FIXED 8 regardless of window length md.
    Ablation-anchored groups run to a mean anaphase of 28-42 min -> ~4 min/bin, plenty of outline points per
    bin. Metaphase-anchored groups are the SAME cells but a much shorter window (their pre-metaphase portion
    is excluded, 12-27 min) -> with nb still fixed at 8 that was ~1.5-3.4 min/bin, thin enough that WHICH FEW
    cells happen to have an outline in a given narrow bin (not real within-cell change) swings the bin mean.
    Confirmed by hand for unModified/meta cross-sectional area: the old nb=8 trend rose 645->748 um^2 (+16%
    at its worst step, and the visually-alarming part of the trend-scaled companion) between t=9.0 and
    t=10.8 min because only 3 outlines fall in that slice and 1-2 of them (20260420 ptk2 eyfp cdc20 1
    ablation_33_xy1/_xy5, area 814-885 um^2 — unusually large, not representative) dominate it; the same
    cohort's ablation-anchored trend has no such swing (wider ~29 min window at the same nb=8 -> ~4 min/bin,
    enough points per bin to average out). Fix: derive nb from a fixed TARGET BIN WIDTH (~4 min, matched to
    the ablation-anchored windows that were already well-behaved) instead of a fixed bin COUNT, so short
    (meta-anchored) and long (ablation-anchored) windows get comparably-populated bins; nb=8 windows (md~28-32
    min) are UNCHANGED by this (still resolve to nb=8). Floor/ceiling (nb in 4..10) keep it from degenerating
    at either extreme. This reduces but does not fully remove small-N bin noise -- it is thinner sampling,
    not a data error -- so it is disclosed on the combined-plot caption too."""
    if md is None or md<=start: return [],[]
    if nb is None:
        TARGET_BIN_MIN=4.0
        nb=int(np.clip(round((md-start)/TARGET_BIN_MIN),3,9))+1
    a=np.array(sorted(pts)); t=a[:,0]; y=a[:,1]
    bins=np.linspace(start,md,nb); idx=np.digitize(t,bins); bx=[];by=[]
    for k in range(1,len(bins)):
        m=idx==k
        if m.sum()>=minpts: bx.append(float(t[m].mean())); by.append(float(y[m].mean()))
    if bx and bx[-1]<md-1e-6:
        mlast=(t>=bins[-2])&(t<=md+1e-6)
        by_end=float(y[mlast].mean()) if mlast.sum()>=1 else by[-1]
        bx.append(md); by.append(by_end)   # reach the mean
    return bx,by

# ── USER 2026-08-17: LINE PLOTS SHOW A FIT + SEM BAND, NOT ONE LINE PER CELL ──────────────────────────
# "For all line plots that AREN'T individual sample line plots ... instead of individually plotting every
#  line for the individual samples, it should just have the line of best fit and then a region of error
#  shaded around it thats SEM (this is standard in the field and dumont lab publications)."
# The "line of best fit" here is the trend these plots ALREADY draw (`trend_to_mean`, the binned mean over
# cells) -- replacing it with a straight regression would throw away the shape of the curve, which is the
# result. What changes is that the per-cell spaghetti goes away and the trend gains a shaded band.
#
# THE BAND IS SEM ACROSS CELLS, NOT ACROSS POINTS. A bin holds several outlines from the SAME cell, so
# pooling raw points would divide by the number of MEASUREMENTS and report a band several times too narrow
# (pseudoreplication -- the exact error this project already calls out on its own axis footnotes). Each
# cell is therefore collapsed to its mean within the bin first, and the SEM is taken over those cell means
# with n = number of CELLS in the bin. A bin with one cell gets no band rather than a zero-width one.
# PERCELL=1 reproduces the RETIRED per-cell-line look under a `_percell` name, so the version she asked to
# be moved to "repeated figures 081726" can be REGENERATED rather than recovered from a backup. The live
# names always render the new fit+SEM style; nothing overwrites the other.
PERCELL = bool(os.environ.get("PERCELL"))
PCSFX = "_percell" if PERCELL else ""

from trendlib import plate_rotation_trace, trend_to_mean_sem, trend_percell_mean_sem, sem_band, anchor_trend, warn_if_composition   # shared with the DELTA siblings (2026-08-19)

# groups shown (Double Chromosome dropped: cohort is globally empty). color = PALETTE[keys[0]].
# USER 2026-08-16: 2-Sisterless removed (its control line goes with it — a control for a group that is no
# longer shown has nothing left to control), collagen added as its own line so the two standalone collagen
# figures can be condensed away.
# USER 2026-08-19 (figure item 6): "1,2,and 3 off-target groups arent plotted as a single group in the plots
# above as they should be." The off-target entry listed only the 1- and 3-sister controls, so the 2-sister
# controls were silently dropped from this whole plot family (they are NOT a separate line -- they were on no
# line at all). All three control cohorts now pool into the one off-target group; the title keeps her wording.
FAM=[("1-Sisterless",["1-Sister"]),("3-Sisterless",["3-Sister"]),
     (COLLAGEN_KEY,[COLLAGEN_KEY]),
     ("off-target (1/3)",["1-Sister Controls","2-Sister Controls","3-Sister Controls"]),
     ("unmodified",["unModified"])]
def xlab(is_un): return "Time from NEBD (min)" if is_un else "Time from first ablation (min)"
def xlab_mode(is_un,mode): return "Time from metaphase onset (min)" if mode=="meta" else xlab(is_un)   # RA1

def _incl_note(mode):
    """USER 2026-07-16: annotate WHY per-group N differs between the ablation-anchored and metaphase-anchored
    versions (they keep maximal N each, so the same group can contain different cells)."""
    if mode=="abl2meta":
        return ("Inclusion: every cell with a recorded Metaphase Start; the window is that cell's run-up to "
                "metaphase (everything at or before metaphase onset), plotted with metaphase onset at t=0 so "
                "the approach to metaphase reads at negative time. Group median lines are not drawn here -- the "
                "right-hand edge IS metaphase onset for every group.")
    if mode=="meta":
        return ("Inclusion: every cell with a recorded Metaphase Start, referenced to metaphase onset -> anaphase "
                "(NEBD NOT required). N differs from the ablation-anchored version: e.g. unmodified cells with a "
                "Metaphase Start but no NEBD appear HERE but not there.")
    return ("Inclusion: cells referenced to first ablation (unmodified to NEBD; unmodified without a recorded NEBD "
            "are excluded). N differs from the metaphase-onset (_meta) companion, which requires only a Metaphase "
            "Start (no NEBD) and clips to metaphase -> anaphase.")
def _stamp_incl(fig, mode):
    # placed BELOW the axes (negative fig-y) + saved with bbox_inches="tight" so the caption box can grow
    # downward without colliding with the x-axis label, however many lines it wraps to (was inside the
    # figure at y=0.004 and clipped into the xlabel once the 2026-08-03 bin-noise caveat below made the
    # meta-mode text 3 lines instead of 2 -- moving it off-axes fixes that for any future line count too).
    fig.text(0.005, -0.045, _incl_note(mode), fontsize=6.0, color="#666", ha="left", va="top", wrap=True)
    if mode=="meta":
        # 2026-08-03: explain the trend_to_mean() bin-width fix (see its docstring) right on the figure --
        # she flagged this exact plot family ('data doesnt seem right' on G1_area_combined_meta_trendscaled).
        fig.text(0.005, -0.105,
                 "Group trend lines are BINNED MEANS across cells, not per-cell paths. The shorter "
                 "metaphase-anchored window means a bin can hold only a few cells, so a bump can reflect which "
                 "cells had an outline there rather than true within-cell change; bin width is now scaled to "
                 "the window (was a fixed 8 bins) to reduce this -- see trend_to_mean().",
                 fontsize=6.0, color="#8b3a00", ha="left", va="top", wrap=True)

# ===================== load cross-sectional AREA traces =====================
def poly_area(pts,pxs):
    a=np.array(pts,float)
    if len(a)<3: return None
    x,y=a[:,0],a[:,1]; A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    return A*pxs*pxs
psize={}
for r in rows[1:]:
    b=r[ix['batch']].strip()
    try: psize[b]=float(r[ix['pixel_size_um']])
    except: psize.setdefault(b,0.062)
area_traces=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try: t=float(r[ix['t_sec']])/60.0; ar=poly_area(json.loads(r[ix['points']]),psize.get(b,0.062))
    except: continue
    if ar is None or abs(t)>600 or ar<=0 or ar>5000: continue
    area_traces[b].append((t,ar))

# ===================== PLATE ROTATION + CENTROID MOVEMENT traces =====================
# USER 2026-08-10: "make line plots of plate rotation and centroid movement like those that are already made
# for crosssectional area and circularity." Same shape as area/roundness above: batch -> [(t_min, value)],
# fed to the SAME combined()/split_panels() so the format, cohorts, trend and per-group median cap match.
#
# PLATE ROTATION is cumulative, in degrees, relative to the cell's first annotated plate. The metaphase plate
# is a LINE, so its orientation is only defined mod 180 deg -- each step is wrapped into (-90, 90] before
# accumulating, otherwise a plate sitting near 0/180 flips by ~180 between frames and fakes a huge rotation.
# CENTROID MOVEMENT is cumulative path length of the cell-outline centroid in um (how far the cell has
# actually travelled), not straight-line displacement, so a cell that wanders and returns still registers.
rot_traces=defaultdict(list)
_pl=defaultdict(list)
for _r in csv.DictReader(open("/Volumes/4 MB/annotations/meta_plates.csv",newline="",encoding="utf-8",errors="replace")):
    _b=(_r.get("batch") or "").strip()
    if _b not in b2: continue
    try:
        _P=np.array(json.loads(_r.get("points") or "[]"),float); _t=float(_r["t_sec"])/60.0
    except Exception:
        continue
    if len(_P)<2: continue
    _c=_P.mean(0); _,_,_vt=np.linalg.svd(_P-_c)
    _pl[_b].append((_t, float(np.degrees(np.arctan2(_vt[0][1], _vt[0][0]))) % 180.0))
for _b,_v in _pl.items():
    _v.sort()
    # 🔴 2026-08-20: net rotation, not a cumulative absolute sum -- see plate_rotation_trace() for why
    # (the old metric read 404 deg on a plate that rotates 7.9 deg net). Still never negative.
    for _t,_x in plate_rotation_trace(_v):
        if abs(_t)<=600: rot_traces[_b].append((_t,_x))
cent_traces=defaultdict(list)
_ct=defaultdict(list)
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try:
        t=float(r[ix['t_sec']])/60.0; _pts=np.array(json.loads(r[ix['points']]),float)
    except Exception:
        continue
    if len(_pts)<3 or abs(t)>600: continue
    _ct[b].append((t,_pts.mean(0)))
for b,_v in _ct.items():
    _v.sort(key=lambda q:q[0]); _px=psize.get(b,0.062); _cum=0.0; _prev=None
    for t,c in _v:
        if _prev is not None: _cum+=float(np.hypot(*(c-_prev)))*_px
        _prev=c
        cent_traces[b].append((t,_cum))
print(f"plate-rotation traces: {len(rot_traces)} cells | centroid-movement traces: {len(cent_traces)} cells")

# ===================== start-rounded vs duration (2 versions) + stats grid =====================
CTRL={"1-Sister Controls","2-Sister Controls","3-Sister Controls"}
def merge_off(g): return "Off-Target/Control" if g in CTRL else g   # plot the off-target controls as ONE group
_ORDER=["unModified","1-Sister","2-Sister","3-Sister","4-Sister","Off-Target/Control"]
def _okey(g): return _ORDER.index(g) if g in _ORDER else 99
def _meta_round(b):
    mt=lib.parse_time(_mr.get(b,{}).get("Metaphase Start (s)",""))
    tr=traces.get(b,[])
    if not tr or mt is None: return None
    return min(tr,key=lambda x:abs(x[0]*60-mt))[1]   # outline closest to metaphase onset
def _first_round(b):
    tr=sorted(traces.get(b,[])); return tr[0][1] if tr else None
def startround(pick,xlabel,fname,title):
    fig,ax=plt.subplots(figsize=(7.8,5.6)); sx=[];sy=[];sg=[];srow=[]
    for b,(g,d) in b2.items():
        r=pick(b)
        if r is None or d is None: continue
        gg=merge_off(g)
        ax.scatter(r,d,s=26,color=lib.PALETTE.get(gg,"#999"),alpha=.8,edgecolor="white",lw=.4)
        sx.append(r);sy.append(d);sg.append(gg);srow.append([b,gg,round(r,4),round(d,3)])
    sx=np.array(sx);sy=np.array(sy);sg=np.array(sg)
    rho=pp=float("nan")
    cohan=[Line2D([0],[0],marker="o",ls="",mfc=lib.PALETTE.get(g,"#999"),mec="white",ms=7,
                  label=f'{lib.lbl(g).replace(chr(10)," ")} (N={int((sg==g).sum())})') for g in sorted(set(sg),key=_okey)]
    trendan=[]
    if len(sx)>=5:
        rho,pp=stats.spearmanr(sx,sy); m,bb=np.polyfit(sx,sy,1); xx=np.linspace(sx.min(),sx.max(),50)
        ax.plot(xx,m*xx+bb,color="#111",lw=2,ls="--",zorder=5)
        trendan.append(Line2D([0],[0],color="#111",lw=2,ls="--",label=f"all cells (Spearman rho={rho:.2f}, p={pp:.2g})"))
    for g in sorted(set(sg),key=_okey):
        mflag=sg==g
        if mflag.sum()>=4:
            m,bb=np.polyfit(sx[mflag],sy[mflag],1); xx=np.linspace(sx[mflag].min(),sx[mflag].max(),20)
            ax.plot(xx,m*xx+bb,color=lib.PALETTE.get(g,"#999"),lw=1.6,zorder=4)
            trendan.append(Line2D([0],[0],color=lib.PALETTE.get(g,"#999"),lw=1.6,label=f"{lib.lbl(g).replace(chr(10),' ')} trend"))
    ax.set_xlabel(xlabel); ax.set_ylabel("Metaphase duration (MM:SS)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_: lib.mmss(v) if v>=0 else ""))
    leg1=ax.legend(handles=cohan,fontsize=6,ncol=2,loc="upper right",title="cohort (dot color)",title_fontsize=6.5)
    ax.add_artist(leg1)
    if trendan: ax.legend(handles=trendan,fontsize=6.5,loc="upper left",title="trend lines",title_fontsize=7)
    ax.set_title(title,loc="left",fontweight="bold",fontsize=11)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["batch","cohort","start_roundness","mitotic_duration_min"],srow,
      {"type":"scatter+overall+per-group linfit","shape_at":title,"dot_color":"cohort (off-target controls merged)",
       "spearman":f"rho={rho:.3f},p={pp:.3g}"},SCRIPT,title)
    print(f"{fname}: Spearman rho={rho:.3f} p={pp:.3g} (N={len(sx)})")
    return rho,pp

def metaphase_statgrid(pick=_meta_round, fname="G1_start_rounded_metaphase_statgrid.png",
                       plot_id="G1_start_rounded_metaphase_statgrid",
                       metric_desc="roundness at metaphase onset", title_lead="Shape at metaphase onset"):
    """Per-group Spearman stats grid (rho, p, N) behind each per-group trend line of a start-rounded-vs-duration
    plot — the statistics for the trends (off-target controls merged into one group). D2 (2026-07-07): the same
    grid is produced for BOTH the metaphase-onset version (pick=_meta_round) and the first-outline version
    (pick=_first_round)."""
    pts=[]
    for b,(g,d) in b2.items():
        r=pick(b)
        if r is None or d is None: continue
        pts.append((merge_off(g),r,d))
    groups=sorted(set(p[0] for p in pts),key=_okey)
    def sp(sub):
        if len(sub)>=3:
            rho,pp=stats.spearmanr([x[1] for x in sub],[x[2] for x in sub]); return rho,pp
        return float("nan"),float("nan")
    tbl_rows=[]; rec=[]
    rho,pp=sp(pts); tbl_rows.append(("All cells",len(pts),rho,pp,"#111")); rec.append(["All cells",len(pts),round(rho,4),round(pp,5)])
    for g in groups:
        sub=[p for p in pts if p[0]==g]; rho,pp=sp(sub)
        tbl_rows.append((lib.lbl(g).replace(chr(10)," "),len(sub),rho,pp,lib.PALETTE.get(g,"#111")))
        rec.append([g,len(sub),round(rho,4),round(pp,5)])
    fig,ax=plt.subplots(figsize=(7.4,0.9+0.46*len(tbl_rows))); ax.axis("off")
    col_labels=["group","N","Spearman rho","p-value"]
    cellText=[[nm,str(n),(f"{rho:+.2f}" if rho==rho else "n/a"),(f"{pp:.3g}" if pp==pp else "n/a")] for nm,n,rho,pp,_ in tbl_rows]
    t=ax.table(cellText=cellText,colLabels=col_labels,loc="center",cellLoc="center",colLoc="center")
    t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1,1.6)
    for j in range(len(col_labels)):
        c=t[0,j]; c.set_facecolor("#eee"); c.set_text_props(fontweight="bold")
    for i,(nm,n,rho,pp,col) in enumerate(tbl_rows,start=1):
        t[i,0].set_text_props(color=col,fontweight="bold")
        if pp==pp and pp<0.05: t[i,3].set_text_props(fontweight="bold")
    ax.set_title("Shape at metaphase onset vs metaphase duration — per-group Spearman correlation\n"
                 "(roundness at metaphase onset vs Meta->Ana duration; off-target controls merged)",
                 loc="left",fontweight="bold",fontsize=10)
    ax.set_title(f"{title_lead} vs metaphase duration — per-group Spearman correlation\n"
                 f"({metric_desc} vs Meta->Ana duration; off-target controls merged)",
                 loc="left",fontweight="bold",fontsize=10)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(plot_id,["group","N","spearman_rho","p_value"],rec,
      {"type":"per-group correlation table","metric":f"{metric_desc} vs metaphase duration",
       "grouping":"off-target controls merged"},SCRIPT,f"Per-group Spearman stats grid — {title_lead} vs metaphase duration")
    print(f"{fname}: {len(tbl_rows)} rows")

startround(_first_round,"Initial roundness (first outline)","G1_start_rounded_vs_duration.png","Do cells that start rounded finish mitosis faster? (first outline)")
startround(_meta_round,"Roundness at metaphase onset (outline nearest metaphase start)","G1_start_rounded_metaphase.png","Does shape at metaphase onset affect metaphase duration?")
metaphase_statgrid()   # metaphase-onset version (existing)
# D2 (2026-07-07): twin stats grid for the first-outline (start-rounded) plot
metaphase_statgrid(pick=_first_round, fname="G1_start_rounded_vs_duration_statgrid.png",
                   plot_id="G1_start_rounded_vs_duration_statgrid",
                   metric_desc="initial roundness (first outline)", title_lead="Start-rounded (first outline)")

# ===================== combined (all groups) + split panels =====================
def combined(mtr,ylabel,fname,titlenoun,ylim=None,mode="ablation"):
    fname=fname[:-4]+PCSFX+".png"   # PERCELL renders under a _percell name; live names keep the new style
    _METAX="Time from metaphase onset (min)"; _ABLX="Time from first ablation (min); unmodified referenced to NEBD"
    _xlabel={"meta":_METAX,"abl2meta":_METAX}.get(mode,_ABLX)
    _metasfx={"meta":" (t=0 metaphase onset)",
              "abl2meta":" (ablation -> metaphase onset; t=0 metaphase onset, run-up negative)"}.get(mode,"")
    fig,ax=plt.subplots(figsize=(9.6,5.6))
    _grpcell={}; _trends=[]; _label_q=[]; dr=[]
    for title,keys in FAM:
        col=lib.PALETTE[keys[0]]; pa=[]; pa3=[]; _cm=[]; anaxs=[]; is_un=keys==["unModified"]
        for b,(g,d) in b2.items():
            if g not in keys: continue
            rt=ref_trace(b,g,sorted(mtr.get(b,[])),mode)
            if rt is None: continue
            pts,ax_ana=rt
            # 2026-08-17: the per-cell line is no longer DRAWN (fit + SEM band replaces the spaghetti),
            # but every point is still collected -- the recorded CSV must stay the exact plotted data.
            if PERCELL: ax.plot([q[0] for q in pts],[q[1] for q in pts],color=col,alpha=.12,lw=.7,zorder=1)
            pa.extend(pts); pa3.extend([(q[0],q[1],b) for q in pts]); _cm.append(np.median([q[1] for q in pts]))
            for t,v in pts: dr.append([b,g,round(t,2),round(v,3)])   # exact plotted cell-trace points
            if ax_ana is not None: anaxs.append(ax_ana)
        _grpcell[title]=_cm
        # USER 2026-08-10: a group's trend stops at that group's MEDIAN metaphase time (was the MEAN).
        # USER 2026-08-19 (figure item 5): "it seems it marks the median time for the samples used to build the
        # actual line, and thats not what i want. I want the median from the main violin plot on the second art
        # board." -> for the metaphase-anchored plots the marker is now the group's median METAPHASE DURATION
        # taken from G1_violin2_no_dc_offtarget_journal (see metaphase_medians.py), NOT np.median(anaxs), which
        # was the median over only those cells that happen to carry a trace in THIS figure.
        # In abl2meta mode the window ENDS at metaphase onset, so there is no median line to draw at all.
        if mode=="meta":   md=_CANON_MED.get(title)
        elif mode=="abl2meta": md=0.0
        else:              md=float(np.median(anaxs)) if anaxs else None
        if pa and md is not None and len(pa)>=5 and (mode=="abl2meta" or md>0):
            if mode=="abl2meta":
                _tstart=min((x for x,_ in pa), default=-1.0)
            else:
                # USER 2026-08-19 (figure item 5): "For these plots starting at metaphase onset, you must also
                # make sure the trendline starts at t=0." It used to start at the earliest pre-metaphase sample
                # (down to -15 min), so the line began to the LEFT of the axis origin.
                _tstart=0.0
            # per-CELL trend, not pooled points (her 2026-08-25; see trendlib.trend_percell_mean_sem). Pooling
            # let the cohort membership change between neighbouring points and the line zigzagged from that
            # alone; interpolating each cell onto the shared grid inside its own measured range fixes it.
            bx,by,bs, _bn = trend_percell_mean_sem(pa3,md,start=_tstart)
            # 2026-08-25: says so on the figure when most of this line's change is the cohort
            # turning over rather than the cells changing (trendlib.warn_if_composition).
            warn_if_composition(ax, pa3,md,start=_tstart)
            # item 5: the drawn line must reach the alignment point, not stop at the first/last BIN CENTRE.
            if mode=="meta":       bx,by,bs=anchor_trend(bx,by,bs,0.0,at_start=True)
            elif mode=="abl2meta": bx,by,bs=anchor_trend(bx,by,bs,0.0,at_start=False)
            sem_band(ax,bx,by,bs,col)                          # USER 2026-08-17: SEM band, not per-cell lines
            leg=title+(" (from NEBD)" if (is_un and mode=="ablation") else "")+f" (N={len(_cm)})"   # per-group N (cells) in legend
            if len(bx)>=2:
                ax.plot(bx,by,color=col,lw=2.8,marker="o",ms=4,zorder=3,label=leg); _trends.append((list(bx),list(by),col,leg,md,list(bs)))
            if mode!="abl2meta":
                # dashed = that group's median metaphase duration; the trend above runs to exactly this x and
                # stops there ("a line continues until but stops at its corresponding median line", item 5).
                ax.axvline(md,color=col,ls=(0,(2,1.5)),lw=1.2)
            # USER 2026-08-19 (figure item 5): "some of these horizontal lines are labeled with text saying the
            # line's time and thats not necessary as if the viewer is wondering the time it marks, they can
            # reference the main violin plot." -> the MM:SS callouts are no longer emitted.
    if ylim: ax.set_ylim(*ylim)
    else: ax.set_ylim(bottom=0)
    if mode=="abl2meta": ax.set_xlim(right=0.0)   # window is the run-up TO metaphase; 0 is the right edge
    else: ax.set_xlim(left=0)
    ytop=ax.get_ylim()[1]
    # RA2 (2026-07-07): REAL collision avoidance for the group-MEAN MM:SS labels. They previously sat ON the
    # dashed lines (rotated text on the vertical line) AND overlapped each other when means were close. Now each
    # label is (a) HORIZONTAL and offset to the RIGHT of its own dashed line (never sitting on it) and (b)
    # VERTICALLY STAGGERED into descending tiers whenever consecutive means are too close horizontally for their
    # horizontal labels to clear one another. A white bbox keeps them legible over the trend/cell lines; the edge
    # colour ties each label to its group.
    # (the MM:SS callout tiers that used to be drawn here were removed 2026-08-19 -- see figure item 5.
    #  _label_q is left in place, empty, so the RA2 collision logic can be restored if she ever asks for
    #  the times back; nothing is drawn while it stays empty.)
    ax.set_xlabel(_xlabel); ax.set_ylabel(ylabel)
    _hh,_ll=ax.get_legend_handles_labels()
    # abl2meta draws no median line at all (its right edge IS metaphase onset), so it gets no legend key.
    if mode!="abl2meta":
        _hh.append(Line2D([0],[0],color="#555",ls=(0,(2,1.5)),lw=1.2))
        _ll.append("median metaphase duration (artboard-2 violin)" if mode=="meta" else "median time to anaphase")
    ax.legend(_hh,_ll,fontsize=7,ncol=2)
    _kg=[v for v in _grpcell.values() if len(v)>=2]; _kw=""
    if len(_kg)>=2:
        try:
            _h,_p=stats.kruskal(*_kg); _kw=f"Kruskal-Wallis (per-cell median {titlenoun.lower()}) p={_p:.2g}"
        except Exception: pass
    ax.set_title(f"{titlenoun} — all groups combined ({'light=cells, bold=group trend' if PERCELL else 'group mean, shaded = SEM'}){_metasfx}"+("\n"+_kw if _kw else ""),
                 loc="left",fontweight="bold",fontsize=9.5)
    _stamp_incl(fig,mode)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    _rec_meta={"type":("combined all-groups (light=cells, bold=group trend)" if PERCELL else "combined all-groups (group mean +/- SEM band)"),"metric":titlenoun,
      "x":("from metaphase onset (negative = before metaphase, retained)" if mode=="meta" else "from ablation (NEBD for unmodified)"),"clip":"anaphase onset"}
    lib.record_plot(fname[:-4],["batch","cohort","t_min","value"],dr,_rec_meta,SCRIPT,f"{titlenoun} — all groups combined")
    # TREND-SCALED companion (axes fit the group trends; individual cells may run off-plot). Dashed mean lines kept.
    if _trends:
        figT,axT=plt.subplots(figsize=(9.6,5.6))
        for title,keys in FAM:
            col=lib.PALETTE[keys[0]]
        _tx=[];_ty=[]
        for bx,by,col,leg,md,bs in _trends:
            # trend-scaled companion: same change -- band instead of one line per cell (2026-08-17)
            sem_band(axT,bx,by,bs,col)
            axT.plot(bx,by,color=col,lw=2.8,marker="o",ms=4,zorder=3,label=leg)
            _tx+=bx; _ty+=by; _ty+=[v-e for v,e in zip(by,bs)]+[v+e for v,e in zip(by,bs)]
            if mode!="abl2meta":
                axT.axvline(md,color=col,ls=(0,(2,1.5)),lw=1.2)   # dashed median lines, as in the combined plot
        if _tx:
            mx=(max(_tx)-min(_tx))*0.06+1; my=(max(_ty)-min(_ty))*0.12+(0.02 if ylim else 1)
            # USER 2026-08-16: "some of them end at anaphase which is what i want, but some arent trimmed to
            # that, so just make sure all are trimmed to anaphase (like the cross-sectional area and
            # roundness plots are)" — plus, for the same board, "all lines [should] have the same starting
            # position of 0". The trend-scaled view already ends just past the last group's median anaphase
            # (that is why area/roundness look right); what remained was the LEFT edge, which retained
            # pre-metaphase time back to about -16 min. For the metaphase-anchored mode the window is now
            # 0 -> anaphase exactly: 0 is metaphase onset, so nothing before it belongs on the axis.
            # abl2meta: the window ENDS at metaphase onset, so 0 is the RIGHT edge (item 1, 2026-08-19).
            if mode=="abl2meta":
                axT.set_xlim(min(_tx)-mx, 0.0)
            else:
                _lo = 0.0 if mode == "meta" else min(_tx)-mx
                axT.set_xlim(_lo, max(_tx)+mx)
            axT.set_ylim(min(_ty)-my,max(_ty)+my)
        axT.set_xlabel(_xlabel); axT.set_ylabel(ylabel)
        _h2,_l2=axT.get_legend_handles_labels()
        if mode!="abl2meta":
            _h2.append(Line2D([0],[0],color="#555",ls=(0,(2,1.5)),lw=1.2))
            _l2.append("median metaphase duration (artboard-2 violin)" if mode=="meta" else "median time to anaphase")
        axT.legend(_h2,_l2,fontsize=7,ncol=2)
        axT.set_title(f"{titlenoun} — TREND-SCALED (axes fit the group trends; individual cells may run off-plot){_metasfx}",
                      loc="left",fontweight="bold",fontsize=9.5)
        _stamp_incl(figT,mode)
        plt.tight_layout(); plt.savefig(f"{OUT}/{fname[:-4]}_trendscaled.png",bbox_inches="tight"); plt.close()
        # trend-scaled companion plots the SAME cell traces (only axes differ) -> identical data CSV, per user rule
        lib.record_plot(fname[:-4]+"_trendscaled",["batch","cohort","t_min","value"],dr,
          dict(_rec_meta,type="combined TREND-SCALED (axes fit trends)"),SCRIPT,f"{titlenoun} — all groups combined (trend-scaled)")
        print(f"  {fname[:-4]}_trendscaled.png written")

def split_panels(mtr,ylabel,fname,titlenoun,ylim=None,mode="ablation"):
    fname=fname[:-4]+PCSFX+".png"   # PERCELL renders under a _percell name; live names keep the new style
    _metasfx=" (t=0 metaphase onset; pre-metaphase retained)" if mode=="meta" else ""
    fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=False,sharey=True); dr=[]; af=list(axes.flat)
    for i,(title,keys) in enumerate(FAM):
        ax=af[i]; col=lib.PALETTE[keys[0]]; pa=[]; pa3=[]; anaxs=[]; is_un=keys==["unModified"]; ncell=0
        for b,(g,d) in b2.items():
            if g not in keys: continue
            rt=ref_trace(b,g,sorted(mtr.get(b,[])),mode)
            if rt is None: continue
            pts,ax_ana=rt; ncell+=1
            if PERCELL: ax.plot([q[0] for q in pts],[q[1] for q in pts],color=col,alpha=.2,lw=.8,zorder=1)
            pa.extend(pts); pa3.extend([(q[0],q[1],b) for q in pts])   # 2026-08-17: collected, not drawn
            if ax_ana is not None: anaxs.append(ax_ana)
            for t,v in pts: dr.append([b,g,round(t,2),round(v,3)])
        # USER 2026-08-10: a group's trend stops at that group's MEDIAN metaphase time (was the MEAN).
        md=float(np.median(anaxs)) if anaxs else None
        if pa and md and len(pa)>=5:
            _tstart=(max(-15.0, min((x for x,_ in pa), default=0.0)) if mode=="meta" else 0.0)
            # per-CELL trend, not pooled points (her 2026-08-25; see trendlib.trend_percell_mean_sem). Pooling
            # let the cohort membership change between neighbouring points and the line zigzagged from that
            # alone; interpolating each cell onto the shared grid inside its own measured range fixes it.
            bx,by,bs, _bn = trend_percell_mean_sem(pa3,md,start=_tstart)
            # 2026-08-25: says so on the figure when most of this line's change is the cohort
            # turning over rather than the cells changing (trendlib.warn_if_composition).
            warn_if_composition(ax, pa3,md,start=_tstart)   # USER 2026-08-05: trend covers pre-metaphase too
            if len(bx)>=2:
                sem_band(ax,bx,by,bs,col)                      # USER 2026-08-17: SEM band, not per-cell lines
                ax.plot(bx,by,color=col,lw=2.8,marker="o",ms=4,zorder=3)
            ax.axvline(md,color=col,ls=(0,(2,1.5)),lw=1.2)
            # RA2 (2026-07-07): HORIZONTAL label offset to the RIGHT of the dashed line (never on it), pinned near
            # the panel floor via the x-axis (blended) transform so it works whether or not ylim is set, with a
            # white bbox for legibility. One mean line per panel -> no label-label overlap to resolve here.
            _dx=(md if md else 1)*0.02+0.2
            ax.text(md+_dx,0.045,f"mean ana {lib.mmss(md)}",transform=ax.get_xaxis_transform(),
                    rotation=0,fontsize=6.5,color=col,ha="left",va="bottom",zorder=6,
                    bbox=dict(boxstyle="round,pad=0.15",fc="white",ec=col,lw=0.6,alpha=0.9))
        ax.set_title(f"{title} (N={ncell})",fontsize=10,color=col); ax.set_xlim(left=0)
        if ylim: ax.set_ylim(*ylim)
        ax.set_xlabel(xlab_mode(is_un,mode))
    for j in range(len(FAM),len(af)): af[j].axis("off")   # DC removed -> unused panel off
    for ax in axes[:,0]: ax.set_ylabel(ylabel)
    fig.suptitle(f"{titlenoun} by group — trend ends at group MEDIAN time to anaphase{_metasfx}",x=.01,ha="left",fontweight="bold")
    _stamp_incl(fig,mode)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["batch","cohort","t_min","value"],dr,{"type":"faceted","metric":titlenoun,
      "x":("from metaphase onset (negative = before metaphase, retained)" if mode=="meta" else "from ablation (NEBD for unmodified)"),"clip":"anaphase onset"},SCRIPT,f"{titlenoun} split by group")
    # TREND-SCALED faceted companion (each panel fits its OWN trend; individual cells may run off-plot)
    figT,axesT=plt.subplots(2,3,figsize=(14,8),sharex=False,sharey=False); afT=list(axesT.flat)
    for i,(title,keys) in enumerate(FAM):
        axT=afT[i]; col=lib.PALETTE[keys[0]]; pa=[]; pa3=[]; anaxs=[]; is_un=keys==["unModified"]; ncell=0
        for b,(g,d) in b2.items():
            if g not in keys: continue
            rt=ref_trace(b,g,sorted(mtr.get(b,[])),mode)
            if rt is None: continue
            pts,ax_ana=rt; ncell+=1
            if PERCELL: axT.plot([q[0] for q in pts],[q[1] for q in pts],color=col,alpha=.2,lw=.8,zorder=1)
            pa.extend(pts); pa3.extend([(q[0],q[1],b) for q in pts])   # 2026-08-17: collected, not drawn
            if ax_ana is not None: anaxs.append(ax_ana)
        # USER 2026-08-10: a group's trend stops at that group's MEDIAN metaphase time (was the MEAN).
        md=float(np.median(anaxs)) if anaxs else None
        if pa and md and len(pa)>=5:
            _tstart=(max(-15.0, min((x for x,_ in pa), default=0.0)) if mode=="meta" else 0.0)
            # per-CELL trend, not pooled points (her 2026-08-25; see trendlib.trend_percell_mean_sem). Pooling
            # let the cohort membership change between neighbouring points and the line zigzagged from that
            # alone; interpolating each cell onto the shared grid inside its own measured range fixes it.
            bx,by,bs, _bn = trend_percell_mean_sem(pa3,md,start=_tstart)
            # 2026-08-25: says so on the figure when most of this line's change is the cohort
            # turning over rather than the cells changing (trendlib.warn_if_composition).
            warn_if_composition(ax, pa3,md,start=_tstart)   # USER 2026-08-05: trend covers pre-metaphase too
            if len(bx)>=2:
                sem_band(axT,bx,by,bs,col)                     # USER 2026-08-17: SEM band, not per-cell lines
                axT.plot(bx,by,color=col,lw=2.8,marker="o",ms=4,zorder=3); axT.axvline(md,color=col,ls=(0,(2,1.5)),lw=1.2)
                # the trend-scaled axes must fit the BAND too, or the shading is clipped at the panel edge
                _blo=[v-e for v,e in zip(by,bs)]; _bhi=[v+e for v,e in zip(by,bs)]
                my=(max(_bhi)-min(_blo))*0.25+(0.01 if ylim else 1); mx=(max(bx)-min(bx))*0.08+1
                axT.set_xlim(min(bx)-mx,max(bx)+mx); axT.set_ylim(min(_blo)-my,max(_bhi)+my)
        axT.set_title(f"{title} (N={ncell})",fontsize=10,color=col); axT.set_xlabel(xlab_mode(is_un,mode))
    for j in range(len(FAM),len(afT)): afT[j].axis("off")
    for axT in axesT[:,0]: axT.set_ylabel(ylabel)
    figT.suptitle(f"{titlenoun} by group — TREND-SCALED (each panel fits its trend; cells may run off-plot){_metasfx}",x=.01,ha="left",fontweight="bold")
    _stamp_incl(figT,mode)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname[:-4]}_trendscaled.png",bbox_inches="tight"); plt.close()
    # trend-scaled faceted companion plots the SAME cell traces (only axes differ) -> identical data CSV, per user rule
    lib.record_plot(fname[:-4]+"_trendscaled",["batch","cohort","t_min","value"],dr,{"type":"faceted TREND-SCALED (each panel fits its trend)","metric":titlenoun,
      "x":("from metaphase onset (negative = before metaphase, retained)" if mode=="meta" else "from ablation (NEBD for unmodified)"),"clip":"anaphase onset"},SCRIPT,f"{titlenoun} split by group (trend-scaled)")

# --- ablation/NEBD-referenced (existing) ---
# ── USER 2026-08-17: COLLAGEN vs EVERYTHING ELSE, AS ONE COMPARISON ──────────────────────────────────
# "For collagen plot, maybe do put collagen samples separate plots, but make it such that its still
#  plotted with all of the other samples but for this one plot all lines for the non-collagen groups as one
#  line that summarizes them all, and then the collagen line, so that the collagen line's different
#  behavior can be easily seen."
# Two lines only: every non-collagen cell POOLED into one summary trace, and collagen as its own. Both are
# the same binned mean + SEM band the rest of the family now uses, so the only thing that differs between
# them is the biology. Pooling is at the CELL level -- each non-collagen cell contributes equally, so a
# cohort with more cells does not silently dominate the summary.
# The collagen figure has only TWO series, so it needs the violin medians pooled the same two ways.
_CANON_MED_POOLED = metaphase_medians.medians_pooled_collagen_vs_rest()

def collagen_vs_pooled(mtr,ylabel,fname,titlenoun,ylim=None,mode="ablation"):
    fname=fname[:-4]+PCSFX+".png"
    fig,ax=plt.subplots(figsize=(9.0,5.2))
    SERIES=[("all other groups pooled",[k for k in coh if k!=COLLAGEN_KEY],"#6a6a6a"),
            ("collagen",[COLLAGEN_KEY],lib.PALETTE[COLLAGEN_KEY])]
    dr=[]; _any=False; _lo=[]; _hi=[]
    for label,keys,col in SERIES:
        p3=[]; ncell=0; anaxs=[]
        for b,(g,d) in b2.items():
            if g not in keys: continue
            rt=ref_trace(b,g,sorted(mtr.get(b,[])),mode)
            if rt is None: continue
            pts,ax_ana=rt; ncell+=1
            if PERCELL: ax.plot([q[0] for q in pts],[q[1] for q in pts],color=col,alpha=.12,lw=.7,zorder=1)
            p3.extend([(q[0],q[1],b) for q in pts])
            for t,v in pts: dr.append([b,label,round(t,2),round(v,3)])
            if ax_ana is not None: anaxs.append(ax_ana)
        if len(p3)<5: continue
        # 2026-08-19 items 1/5: metaphase-anchored -> trend runs 0 -> the canonical median (from the artboard-2
        # violin, pooled over the cells on that side of the split); abl2meta -> run-up window ending at 0.
        if mode=="abl2meta":
            md=0.0; _tstart=min((q[0] for q in p3),default=-1.0)
        elif mode=="meta":
            md=_CANON_MED_POOLED.get(label); _tstart=0.0
        else:
            md=float(np.median(anaxs)) if anaxs else None; _tstart=0.0
        if md is None: continue
        # per-CELL trend, not pooled points (her 2026-08-25; see trendlib.trend_percell_mean_sem). Pooling
        # let the cohort membership change between neighbouring points and the line zigzagged from that
        # alone; interpolating each cell onto the shared grid inside its own measured range fixes it.
        bx,by,bs, _bn = trend_percell_mean_sem(p3,md,start=_tstart)
        # 2026-08-25: says so on the figure when most of this line's change is the cohort
        # turning over rather than the cells changing (trendlib.warn_if_composition).
        warn_if_composition(ax, p3,md,start=_tstart)
        if mode=="meta":       bx,by,bs=anchor_trend(bx,by,bs,0.0,at_start=True)
        elif mode=="abl2meta": bx,by,bs=anchor_trend(bx,by,bs,0.0,at_start=False)
        if len(bx)<2: continue
        _any=True
        sem_band(ax,bx,by,bs,col)
        ax.plot(bx,by,color=col,lw=3.0,marker="o",ms=4,zorder=3,label=f"{label} (N={ncell})")
        if md and mode!="abl2meta": ax.axvline(md,color=col,ls=(0,(2,1.5)),lw=1.2)
        _lo+= [v-e for v,e in zip(by,bs)]; _hi+=[v+e for v,e in zip(by,bs)]
    if not _any: plt.close(); return
    if ylim: ax.set_ylim(*ylim)
    elif _lo: ax.set_ylim(min(_lo)-(max(_hi)-min(_lo))*0.12, max(_hi)+(max(_hi)-min(_lo))*0.12)
    if mode=="abl2meta": ax.set_xlim(right=0.0)
    else: ax.set_xlim(left=0)
    ax.set_xlabel("Time from metaphase onset (min)" if mode in ("meta","abl2meta") else "Time from ablation (min)")
    ax.set_ylabel(ylabel); ax.legend(fontsize=9)
    ax.set_title(f"{titlenoun} — collagen vs all other groups pooled (line = group mean, shaded = SEM)",
                 loc="left",fontweight="bold",fontsize=10)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["batch","series","t_min","value"],dr,
      {"type":"collagen vs pooled-others (mean +/- SEM)","metric":titlenoun,
       "pooling":"every non-collagen cell contributes one trace to a single summary line",
       "band":"SEM across cells within each time bin"},SCRIPT,
      f"{titlenoun} — collagen vs every other group pooled into one line")

collagen_vs_pooled(traces,"Roundness (4piA/P^2)","G1_roundness_collagen_vs_pooled.png","Cell roundness",(0,1.05))
collagen_vs_pooled(area_traces,"Cross-sectional area (um^2)","G1_area_collagen_vs_pooled.png","Cell cross-sectional area")
collagen_vs_pooled(traces,"Roundness (4piA/P^2)","G1_roundness_collagen_vs_pooled_meta.png","Cell roundness",(0,1.05),mode="meta")
collagen_vs_pooled(area_traces,"Cross-sectional area (um^2)","G1_area_collagen_vs_pooled_meta.png","Cell cross-sectional area",mode="meta")

combined(traces,"Roundness (4piA/P^2)","G1_roundness_combined.png","Cell roundness",(0,1.05))
combined(area_traces,"Cross-sectional area (um^2)","G1_area_combined.png","Cell cross-sectional area")
split_panels(traces,"Roundness (4piA/P^2)","G1_roundness_split.png","Cell roundness",(0,1.05))
split_panels(area_traces,"Cross-sectional area (um^2)","G1_area_split.png","Cell cross-sectional area")
# --- RA1: metaphase-onset -> anaphase versions (every cell referenced to its own Metaphase Start) ---
combined(rot_traces,"Cumulative plate rotation (deg)","G1_plate_rotation_combined.png","Plate rotation")
combined(cent_traces,"Cumulative centroid movement (um)","G1_centroid_movement_combined.png","Centroid movement")
split_panels(rot_traces,"Cumulative plate rotation (deg)","G1_plate_rotation_split.png","Plate rotation")
split_panels(cent_traces,"Cumulative centroid movement (um)","G1_centroid_movement_split.png","Centroid movement")

combined(traces,"Roundness (4piA/P^2)","G1_roundness_combined_meta.png","Cell roundness",(0,1.05),mode="meta")
combined(area_traces,"Cross-sectional area (um^2)","G1_area_combined_meta.png","Cell cross-sectional area",mode="meta")
split_panels(traces,"Roundness (4piA/P^2)","G1_roundness_split_meta.png","Cell roundness",(0,1.05),mode="meta")
split_panels(area_traces,"Cross-sectional area (um^2)","G1_area_split_meta.png","Cell cross-sectional area",mode="meta")

combined(rot_traces,"Cumulative plate rotation (deg)","G1_plate_rotation_combined_meta.png","Plate rotation",mode="meta")
combined(cent_traces,"Cumulative centroid movement (um)","G1_centroid_movement_combined_meta.png","Centroid movement",mode="meta")
split_panels(rot_traces,"Cumulative plate rotation (deg)","G1_plate_rotation_split_meta.png","Plate rotation",mode="meta")
split_panels(cent_traces,"Cumulative centroid movement (um)","G1_centroid_movement_split_meta.png","Centroid movement",mode="meta")

# ── USER 2026-08-19, to-do list 0819 1pm, FIGURE ITEM 1 ──────────────────────────────────────────────
# "Delta roundness/cross sectional area/plate rotation/centroid movement plots that have data before
#  metaphase onset (so are currently plotted as line plots referenced to a time of 0 as ablation), change
#  so they just plot from ablation to metaphase onset, but also adjust time calibration as metaphase should
#  be set at t=0, and times leading up to it negative. Then move these plots from the main plot collection
#  to the supplemental plot collection ... Including plots below and any additional of this family of plots
#  that dont start at metaphase but start at ablation"
#
# These are NEW figures, not replacements: the metaphase-onset -> anaphase versions stay on the main deck
# (that is what item 5's "these plots starting at metaphase onset" refers to), and these ablation -> metaphase
# ones go to META_FIGURES_20260813_supplemental on the matching artboard. All FOUR metrics get one, because
# she named all four and asked for "any additional of this family of plots that dont start at metaphase".
combined(traces,"Roundness (4piA/P^2)","G1_roundness_combined_abl2meta.png","Cell roundness",(0,1.05),mode="abl2meta")
combined(area_traces,"Cross-sectional area (um^2)","G1_area_combined_abl2meta.png","Cell cross-sectional area",mode="abl2meta")
combined(rot_traces,"Cumulative plate rotation (deg)","G1_plate_rotation_combined_abl2meta.png","Plate rotation",mode="abl2meta")
combined(cent_traces,"Cumulative centroid movement (um)","G1_centroid_movement_combined_abl2meta.png","Centroid movement",mode="abl2meta")
collagen_vs_pooled(traces,"Roundness (4piA/P^2)","G1_roundness_collagen_vs_pooled_abl2meta.png","Cell roundness",(0,1.05),mode="abl2meta")
collagen_vs_pooled(area_traces,"Cross-sectional area (um^2)","G1_area_collagen_vs_pooled_abl2meta.png","Cell cross-sectional area",mode="abl2meta")


# ===== E3: effect of CLOSING the (open polyline) outline on roundness =====
def _round_open_closed(pts):
    p=np.array(pts,float)
    if len(p)<3: return None,None
    x,y=p[:,0],p[:,1]
    A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per_open=float(np.sum(np.hypot(np.diff(x),np.diff(y))))
    per_closed=per_open+float(np.hypot(x[0]-x[-1],y[0]-y[-1]))
    def _r(per):
        if per==0: return None
        v=4*np.pi*A/per**2
        return v if 0<v<=1.2 else None
    return _r(per_open),_r(per_closed)
_op=[];_cl=[]
for r in rows[1:]:
    b=r[ix['batch']].strip()
    if b not in b2: continue
    try:
        t=float(r[ix['t_sec']])/60.0
        if abs(t)>600: continue
        ro,rc=_round_open_closed(json.loads(r[ix['points']]))
    except: continue
    if ro is not None: _op.append(ro)
    if rc is not None: _cl.append(rc)
print(f"E3 roundness OPEN  polyline: median={np.median(_op):.4f}  (N={len(_op)})")
print(f"E3 roundness CLOSED contour: median={np.median(_cl):.4f}  (N={len(_cl)})  [USED in all plots]")
print(f"E3 median delta (closed-open)={np.median(_cl)-np.median(_op):+.4f}")

lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print("roundness split + start-rounded done. traced cells:",len([b for b in traces if len(traces[b])>=2]))
