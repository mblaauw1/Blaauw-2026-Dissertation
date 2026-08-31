"""cell fluorescence measured on the 16-bit FLUOR cropped TIF
(lib.FluorTif -> *_Fluor_Cropped.tif), NEVER the 8-bit MP4.

CF0 (measurement definition — user): cell fluorescence = the MEAN intensity inside the MANUAL OUTLINE.
That IS area-normalization (total signal / #pixels in the outline). There is NO distant-background
subtraction anymore — the user's definition is the raw outline mean, not (mean − median-outside-outline).

Two plots:
  (a) G4_fluor_vs_duration  (slide 44): fluorescence near metaphase  vs  metaphase duration (Meta->Ana, min)
  (b) G4_fluor_over_time    (slide 46): cell fluorescence over time, per cell + per-cohort trend

INTENSITY IS READ FROM THE FLUOR FRAME for BOTH plots (single measurement loop below):
    ft = lib.FluorTif(b,'monitoring')      # 16-bit FLUOR cropped TIF
    g  = ft.plane_by_frame(fr)             # the FLUOR plane for this outline's frame (ground-truth frame map)
    cv2.fillPoly(mask,[pts],255)           # the OUTLINE is filled on that FLUOR plane g
    vals = g[mask>0]                       # intensity sampled from the FLUOR plane only
    value = vals.mean()                    # CF0: area-normalized cell fluor = mean inside the manual outline (NO bg subtraction)
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, re, numpy as np, cv2, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
coh=lib.assign_cohorts(); b2={}
for k,lst in coh.items():
    for b,d in lst: b2.setdefault(b,(k,d))

# CF1: for the fluorescence-OVER-TIME plots, collapse the off-target/control cohorts into ONE group
# ('Off-Target/Control', which lib labels "All off-target"). CF3 (2026-07-07 feedback, literal): DROP the
# sparse 2-sisterless group in BOTH its on-target ("2-Sister") AND off-target ("2-Sister Controls") forms
# from these plots — the user asked to "remove the 2-sisterless off-target and on-target groups (too few
# samples)" from ALL cell-fluorescence-with-time plots, not merely fold the off-target one into the pooled
# group. So "2-Sister Controls" is EXCLUDED here (not absorbed into Off-Target/Control), matching what the
# vs-duration plot already does. These drops apply to the over-time / scaled / trend plots only — the
# vs-duration cohort scatter keeps its per-cohort colors (and independently excludes both 2-sis cohorts).
_FL_CTRL_COHORTS={"1-Sister Controls","3-Sister Controls"}    # 2-Sister Controls intentionally NOT here — it is dropped below, not merged
_FL_DROP_GROUPS={"2-Sister","2-Sister Controls"}              # CF3: drop 2-sisterless ON- and OFF-target from all fluor-time plots
def _fgrp(b):
    c=b2[b][0]
    return "Off-Target/Control" if c in _FL_CTRL_COHORTS else c
def _fdrop(b):
    return b2[b][0] in _FL_DROP_GROUPS

HI_CUT=120.0    # S44: a near-metaphase fluorescence > 120 a.u. is implausibly high -> EXCLUDE + review
LOW_CUT=1.0     # S46: a batch whose median fluorescence is < 1 a.u. has NO signal above background -> remove + review

# 2026-07-07 feedback (mirror of group4_movement.py LONG_SAMPLE): exactly one sample tracks/records to ~95-100
# min — a TEMPORAL outlier that stretches the x-axis of every fluorescence-OVER-TIME plot. Drop it from the
# over-time / trend / scaled-0-1 time-series plots ONLY (below). It is KEPT in the fluor-vs-DURATION plots
# (those are not time-stretched — x = metaphase duration, not elapsed time).
LONG_SAMPLE="20250401 ptk_yfpcdc20_28"

# ---------------- outlines (monitoring phase) by batch ----------------
rows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ix={c:i for i,c in enumerate(rows[0])}
obatch=defaultdict(list)
for r in rows[1:]:
    if r[ix['phase']]!='mon': continue
    b=r[ix['batch']].strip()
    try: ts=float(r[ix['t_sec']]); fr=int(r[ix['frame']]); pts=np.array(json.loads(r[ix['points']]),np.int32)
    except: continue
    obatch[b].append((ts,fr,pts))

# ---------------- measure on the FLUOR frame ----------------
# Completeness (S44): map every outline to its FLUOR plane by FRAME (the ground-truth path; t_sec is on a
# different clock for some batches). Integrity is guaranteed by FluorTif's own MP4-correlation validation
# (ok()==False if the cropped TIF doesn't match the render the outline was placed on), so we do NOT also
# reject a whole batch on a t_sec-timeline mismatch (that previously dropped ~17 valid April batches whose
# frames map perfectly in-range). We only skip an individual outline whose frame falls outside the stack.
meas=[]                                   # (batch, cohort, t_sec, fluor_value)
nb=0; drop_tif=[]; drop_frame=[]
calib=lib._frame_calib()
for b,outs in obatch.items():
    if b not in b2: continue
    if lib.excluded(b): continue          # global user-flagged outliers (lib.REVIEW_EXCLUDE) — guard the direct-outline iteration
    ft=lib.FluorTif(b,'monitoring')       # 16-bit FLUOR cropped TIF, validated vs render MP4
    if not ft.ok():
        lib.log_review("fluor",b,"no/invalid fluor TIF","skipped (no matching/validated fluor TIF)"); drop_tif.append(b); continue
    nfr=len(ft); got=0
    for ts,fr,pts in outs:
        fri=int(round(fr))
        if not (0<=fri<nfr or (b,'monitoring',fri) in calib):
            continue                      # this outline's frame is outside the fluor stack -> unmappable
        g=ft.plane_by_frame(fr)           # FLUOR plane for this outline's frame
        if g is None: continue
        mask=np.zeros(g.shape,np.uint8); cv2.fillPoly(mask,[pts],255)   # outline filled on the FLUOR plane
        vals=g[mask>0]                    # intensity read from the FLUOR plane only
        if len(vals)==0: continue
        # CF0: cell fluorescence = MEAN intensity inside the MANUAL OUTLINE (area-normalized: total signal / #px).
        # No distant-background subtraction — the user's definition is the raw outline mean, not (mean − outside-median).
        meas.append((b,b2[b][0],ts,float(vals.mean())))
        got+=1
    if got: nb+=1
    else:
        drop_frame.append(b); lib.log_review("fluor",b,f"{len(outs)} outlines","skipped (no outline frame maps into the fluor stack)")
    ft.close()
print(f"measured {len(meas)} outline-fluor points across {nb} batches "
      f"(dropped: {len(drop_tif)} no-TIF, {len(drop_frame)} no-mappable-frame)")
# CF0 RESCALE (2026-07-07): removing the distant-background subtraction made the area-normalized RAW
# mean-in-outline values ~hundreds-thousands, so the old ABSOLUTE outlier cutoffs (HI_CUT=120, LOW_CUT=1)
# rejected EVERY point and blanked all fluor plots. Recompute robust DATA-RELATIVE bounds (Q3+3*IQR / floor 0)
# from the actual measured distribution so only true outliers (e.g. saturation) are dropped.
_allf=np.array([m[3] for m in meas],float)
if len(_allf)>=5:
    # MEDIAN-RELATIVE bounds (the area-normalized means cluster tightly, so IQR bounds were far too aggressive
    # and clipped the bright metaphase-onset points off a degradation curve). Only catch true saturation
    # (>2.5x median) and no-signal (<0.2x median); keep the full real dynamic range in between.
    _med=float(np.median(_allf))
    HI_CUT=_med*2.5; LOW_CUT=_med*0.2
    print(f"CF0 rescale: median-relative fluor bounds -> LOW_CUT={LOW_CUT:.0f}, HI_CUT={HI_CUT:.0f} (median {_med:.0f})")

# ITEMS 2/3/5/6: exclude UNMODIFIED batches imaged at only ~1 z-stack/min (or slower). These slow-cadence
# acquisitions bleach far less, so they are not comparable to the frequent (~20 s) ablation-batch imaging
# in any fluorescence-vs-time / vs-duration plot. Detect via master 'Time Interval (s)' >= 45 s. Applies
# to the unmodified cohort only (ablation cohorts already image at ~20 s).
# CF1: "≤1 z-stack/min" == a time interval of >=60 s (1 stack per 60 s). The prior >=45 s threshold was
# slightly too aggressive vs the stated rule; use >=60 s. (In the current master no unmodified batch falls in
# [45,60), so the numeric result is unchanged — but the threshold now matches the definition.) NOTE: a blank
# Time Interval is treated as fast-cadence (kept); the plotted-count ceiling is set by outline+FLUOR-TIF
# availability (~18 unmodified batches have mon-outlines & pass cadence), NOT by this filter.
def _slow_unmod(b):
    if b not in b2 or b2[b][0]!="unModified": return False
    ti=(mr.get(b,{}).get("Time Interval (s)","") or "").strip()
    try: return float(ti)>=60.0
    except: return False
_slowset=sorted({m[0] for m in meas if _slow_unmod(m[0])})
for _b in _slowset:
    lib.log_review("fluor_cadence",_b,mr.get(_b,{}).get("Time Interval (s)",""),
        "unmodified imaged at <=1 z-stack/min (Time Interval >=60s) — excluded from all fluor plots (photobleaching not comparable to ~20s ablation batches)")
meas=[m for m in meas if not _slow_unmod(m[0])]
print(f"CF1 cadence exclusion: dropped {len(_slowset)} slow (>=60s interval) unmodified batches -> {_slowset}")

bym=defaultdict(list)
for b,c,ts,f in meas: bym[b].append((ts,f))
if LONG_SAMPLE in bym:
    lib.log_review("fluor_long_temporal_outlier",LONG_SAMPLE,"~95-100 min record",
        "records to ~95-100 min (>2x next-longest); EXCLUDED from all fluorescence OVER-TIME/trend/scaled plots (stretches x-axis) per feedback — KEPT in fluor-vs-duration plots")

# scope/flag any 0.031-um/px batch: 2x magnification spreads photons over ~4x pixels, so an
# area-normalized per-pixel mean reads ~4x LOW relative to the standard 0.062-um/px batches.
_n031=0
for b in bym:
    ps=(mr.get(b,{}).get("Pixel Size (um)","") or "").strip()
    if re.fullmatch(r'[0-9.]+',ps) and abs(float(ps)-0.031)<0.005:
        _n031+=1; lib.log_review("fluor_pixelsize",b,f"px={ps}",
            "0.031-um/px: per-pixel mean reads ~4x LOW vs 0.062-um/px batches — scope separately")
print(f"0.031-um/px batches among measured: {_n031}")

# ========================= (a) fluorescence near metaphase vs metaphase duration =========================
# y = cell fluorescence near metaphase (a.u.);  x = metaphase duration Meta->Ana (min)
# remove the 4-sisterless cohort; exclude any near-metaphase fluorescence > 120 a.u. (review).
by_c=defaultdict(list)                     # cohort -> [(dur_min, fluor)]
rows_a=[]
for b,pl in bym.items():
    c,dur=b2[b]
    if c in ("4-Sister","2-Sister","2-Sister Controls"): continue   # S44: 4-sis removed; CF3/l269: 2-sisterless (on+off-target) removed — too few samples, consistent with the over-time plots
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)",""))
    if meta is None or dur is None: continue
    ts,f=min(pl,key=lambda p:abs(p[0]-meta))      # outline closest to metaphase
    if f>HI_CUT:
        lib.log_review("fluor_vs_duration",b,f"{f:.1f}",
            f"fluorescence {f:.0f} > {HI_CUT:.0f} a.u. near metaphase ({c}) — EXCLUDED, review"); continue
    by_c[c].append((dur,f)); rows_a.append([b,c,round(dur,3),round(f,2)])

def _ancova_slopes(groups):
    """Homogeneity-of-slopes ANCOVA F-test: do the per-cohort trend lines have different slopes?
    Compares the full model (separate slope+intercept per cohort) vs the reduced model (common slope,
    separate intercepts). Returns (F, p, df1, df2, n_groups) or None."""
    G=[(np.asarray(x,float),np.asarray(y,float)) for x,y in groups if len(x)>=3]
    if len(G)<2: return None
    rss_full=0.0; df_full=0
    for x,y in G:
        m,bb=np.polyfit(x,y,1); r=y-(m*x+bb); rss_full+=float(r@r); df_full+=len(x)-2
    xs=np.concatenate([x for x,_ in G]); ys=np.concatenate([y for _,y in G])
    cols=[xs]; off=0
    for x,_ in G:
        d=np.zeros(len(xs)); d[off:off+len(x)]=1.0; cols.append(d); off+=len(x)
    X=np.column_stack(cols)
    beta,*_=np.linalg.lstsq(X,ys,rcond=None); rr=ys-X@beta; rss_red=float(rr@rr); df_red=len(ys)-X.shape[1]
    df1=df_red-df_full
    if df1<=0 or df_full<=0 or rss_full<=0: return None
    F=((rss_red-rss_full)/df1)/(rss_full/df_full)
    return F,float(stats.f.sf(F,df1,df_full)),df1,df_full,len(G)

ORDER=["unModified","1-Sister","1-Sister Controls","2-Sister","2-Sister Controls",
       "3-Sister","3-Sister Controls","Double Chromosome","Off-Target/Control"]
ckeys=[c for c in ORDER if c in by_c]+[c for c in by_c if c not in ORDER]

fig,ax=plt.subplots(figsize=(8.2,5.8))
allx=[];ally=[]
for c in ckeys:
    xy=by_c[c]; xs=[p[0] for p in xy]; ys=[p[1] for p in xy]; allx+=xs; ally+=ys
    ax.scatter(xs,ys,s=26,color=lib.PALETTE.get(c,"#999"),alpha=.8,edgecolor="white",lw=.4,zorder=2)
# CF6: OVERALL trend line ONLY (per-cohort subgroup trend lines dropped per user request).
nlines=0
if len(allx)>=5:
    allx=np.array(allx); ally=np.array(ally)
    m,bb=np.polyfit(allx,ally,1); xr=np.linspace(allx.min(),allx.max(),50)
    ax.plot(xr,m*xr+bb,"--",color="#111",lw=2.2,zorder=4); nlines+=1
    rho,p=stats.spearmanr(allx,ally)
    # CF6/X1: stats box in the (typically empty) top-right corner with an OPAQUE background so it never overlaps points.
    ax.text(.98,.98,f"overall Spearman rho={rho:.2f}, p={p:.3g}, N={len(allx)}",transform=ax.transAxes,
            va="top",ha="right",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec="#ccc",alpha=.95))
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=lib.PALETTE.get(c,"#888"),
          label=f"{lib.lbl(c).replace(chr(10),' ')} (N={len(by_c[c])})") for c in ckeys],fontsize=6.5,ncol=2)
ax.set_xlabel("Metaphase duration (min)")
# CF0: area-normalized = mean inside the manual outline (no background subtraction).
ax.set_ylabel("Cell fluorescence at metaphase (mean inside manual outline, area-normalized, a.u.)")
ax.set_title("Cell fluorescence at metaphase vs metaphase duration",loc="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_vs_duration.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_fluor_vs_duration",["batch","cohort","metaphase_duration_min","fluor_mean_au"],rows_a,
  {"type":"scatter + OVERALL linfit (Spearman); per-cohort trend lines dropped (CF6)",
   "source":"_Fluor_Cropped.tif (16-bit) mean inside outline polygon, on the FLUOR plane by frame",
   "x":"metaphase duration Meta->Ana (min)","y":"cell fluorescence at metaphase (mean inside outline, area-normalized, a.u.)",
   "excluded":f"4-Sister cohort removed; fluorescence>{HI_CUT:.0f} a.u. removed (review)"},
  SCRIPT,"Cell fluorescence at metaphase vs metaphase duration (CF6: overall trend only) — area-normalized version")

# ========================= (a-scaled) CF6 companion: fluor-at-metaphase vs duration, SCALED 0-1 =========================
# CF6 asks for a 0–1-scaled companion (the main plot above is the area-normalized a.u. version). Min–max scale
# the fluorescence axis across all plotted points; keep the overall trend only.
fig,ax=plt.subplots(figsize=(8.2,5.8))
_sx=[p[0] for c in ckeys for p in by_c[c]]; _sy=[p[1] for c in ckeys for p in by_c[c]]
if _sx:
    _lo=min(_sy); _rng=(max(_sy)-_lo) or 1.0
    for c in ckeys:
        xs=[p[0] for p in by_c[c]]; ys=[(p[1]-_lo)/_rng for p in by_c[c]]
        ax.scatter(xs,ys,s=26,color=lib.PALETTE.get(c,"#999"),alpha=.8,edgecolor="white",lw=.4,zorder=2)
    _allys=[(v-_lo)/_rng for v in _sy]
    if len(_sx)>=5:
        m,bb=np.polyfit(np.array(_sx),np.array(_allys),1); xr=np.linspace(min(_sx),max(_sx),50)
        ax.plot(xr,m*xr+bb,"--",color="#111",lw=2.2,zorder=4)
        rho,p=stats.spearmanr(_sx,_allys)
        ax.text(.98,.98,f"overall Spearman rho={rho:.2f}, p={p:.3g}, N={len(_sx)}",transform=ax.transAxes,
                va="top",ha="right",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec="#ccc",alpha=.95))
ax.legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=lib.PALETTE.get(c,"#888"),
          label=f"{lib.lbl(c).replace(chr(10),' ')} (N={len(by_c[c])})") for c in ckeys],fontsize=6.5,ncol=2)
ax.set_xlabel("Metaphase duration (min)")
ax.set_ylabel("Cell fluorescence at metaphase — min–max scaled 0–1")
ax.set_title("Cell fluorescence at metaphase vs duration — SCALED 0–1 (CF6 companion)",loc="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_vs_duration_scaled01.png",bbox_inches="tight"); plt.close()

# ===== (a-zoom) USER 2026-07-30: the _zoom companion, but 0-1 scaled with a trendline and legend =====
# Her note: "G4_fluor_vs_duration_zoom scale from 0-1, and add trendline and legend as in
# G4_fluor_vs_duration_scaled01". The generic make_zoom_companions version re-plotted the parent's raw a.u.
# axis with outliers trimmed and carried neither trendline nor legend, so it is built here instead and
# G4_fluor_vs_duration is on that script's SKIP_IDS list. Same 0-1 scaling as the figure above; the only
# difference is that the y-axis is fitted to the BULK, with the outliers drawn hollow on the trend rather
# than deleted - the standing convention for a _zoom companion.
fig,ax=plt.subplots(figsize=(8.2,5.8))
if _sx:
    # Scale to 0-1 over the BULK, not over everything. Min-max scaling the full set puts one extreme
    # cell at 1.0 and squashes every other point into the bottom tenth of the axis - which is what the
    # first attempt did, giving a "0-1" plot whose data all sat between 0.00 and 0.10. For a ZOOM
    # companion the bulk is the subject, so the outliers are identified first (Tukey, on the raw values),
    # the 0-1 range is set by the bulk, and the outliers are then drawn hollow, clamped to the axis.
    _q1r,_q3r=np.percentile(_sy,[25,75]); _iqrr=_q3r-_q1r
    _rawlo,_rawhi=_q1r-1.5*_iqrr,_q3r+1.5*_iqrr
    _bulk=[v for v in _sy if _rawlo<=v<=_rawhi] or _sy
    _lo2=min(_bulk); _rng2=(max(_bulk)-_lo2) or 1.0
    _sc={c:[(p[0],(p[1]-_lo2)/_rng2) for p in by_c[c]] for c in ckeys}
    _lohi=(0.0,1.0)
    nout=0
    for c in ckeys:
        ins=[(x,y) for x,y in _sc[c] if _lohi[0]<=y<=_lohi[1]]
        out=[(x,y) for x,y in _sc[c] if not (_lohi[0]<=y<=_lohi[1])]
        nout+=len(out)
        if ins: ax.scatter([q[0] for q in ins],[q[1] for q in ins],s=26,
                           color=lib.PALETTE.get(c,"#999"),alpha=.85,edgecolor="white",lw=.4,zorder=3)
        # 2026-08-04: hollow outlier markers REMOVED per feedback. The y-axis is already fitted to the
        # bulk, so out-of-range points are simply left out (the standing meaning of a zoom) rather than
        # clamped to the axis edge as hollow circles.
    _fx=[x for c in ckeys for x,_ in _sc[c]]; _fy=[y for c in ckeys for _,y in _sc[c]]
    # 2026-08-04: overall trend line + Spearman box REMOVED per feedback.
    ax.set_ylim(-0.04,1.04)
    ax.legend(handles=[Line2D([0],[0],marker="o",color="w",markerfacecolor=lib.PALETTE.get(c,"#888"),
              label=f"{lib.lbl(c).replace(chr(10),' ')} (N={len(by_c[c])})") for c in ckeys],fontsize=6.5,ncol=2)
    ax.set_xlabel("Metaphase duration (min)")
    ax.set_ylabel("Cell fluorescence at metaphase - min-max scaled 0-1")
    ax.set_title(f"Cell fluorescence at metaphase vs metaphase duration - SCALED 0-1, y-axis fitted to the bulk"
                 f" ({nout} outlier pt(s) omitted)",loc="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_vs_duration_zoom.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_fluor_vs_duration_zoom",["batch","cohort","metaphase_duration_min","fluor_scaled01"],
  [[r0[0],r0[1],r0[2],round((r0[3]-(min(_sy) if _sy else 0.0))/(((max(_sy)-min(_sy)) or 1.0) if _sy else 1.0),4)] for r0 in rows_a],
  {"type":"scatter; 0-1 scaled; y fitted to bulk; outliers omitted; no trend line",
   "companion_of":"G4_fluor_vs_duration",
   "user":"2026-08-04 - trend line and hollow outlier markers removed"},SCRIPT,
  "Cell fluorescence at metaphase vs metaphase duration - 0-1 scaled, y-axis fitted to the bulk")
_slo=min(_sy) if _sy else 0.0; _srng=((max(_sy)-_slo) or 1.0) if _sy else 1.0
lib.record_plot("G4_fluor_vs_duration_scaled01",["batch","cohort","metaphase_duration_min","fluor_scaled01"],
  [[r0[0],r0[1],r0[2],round((r0[3]-_slo)/_srng,4)] for r0 in rows_a],
  {"type":"scatter + overall linfit; fluorescence min-max scaled 0-1","companion_of":"G4_fluor_vs_duration",
   "x":"metaphase duration (min)","y":"fluor at metaphase, min-max scaled 0-1"},SCRIPT,
  "Cell fluorescence at metaphase vs duration — scaled 0-1 (CF6 companion)")

# ========================= (b) fluorescence over time =========================
low=[b for b in bym if np.median([f for _,f in bym[b]])<LOW_CUT]
for b in low:
    ps=(mr.get(b,{}).get("Pixel Size (um)","") or "").strip()
    is031=bool(re.fullmatch(r'[0-9.]+',ps)) and abs(float(ps)-0.031)<0.005
    flag=" *** FLAG 0.031-um/px (per-pixel mean ~4x low)" if is031 else ""
    med=float(np.median([f for _,f in bym[b]]))
    print(f"   LOW {b!r}  median_fluor={med:.1f}  pixel_size={ps or 'BLANK'}{flag}")
    lib.log_review("fluor_over_time",b,f"median {med:.1f}; pixel_size={ps or 'BLANK'}",
        "no detectable signal above background (median < 1 a.u.) — removed from plot; review"+flag)
print(f"FL: {len(low)} no-signal batch(es) removed from over-time plot")

# #11a: drop extreme high-fluorescence outlier points (the 2-Sisterless ~148 spike the user flagged) + log for review
_FL_HI=HI_CUT   # CF0 rescale: use the data-relative high bound (was hardcoded 120, stale for area-normalized scale)
_fl_out=sorted({b for b,pl in bym.items() if b not in low for ts,f in pl if f>_FL_HI})
for b in _fl_out:
    _hv=max(f for ts,f in bym[b] if f>_FL_HI)
    lib.log_review("fluor_over_time_outlier",b,f"{_hv:.0f} a.u.",f"fluorescence point > {_FL_HI:.0f} a.u. (clear outlier) removed from over-time plot; review")
# #11b: per-cohort MEDIAN anaphase time (render-reference min) to cap each cohort trend
_flcap={}
for b in bym:
    if b in low: continue
    _an=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    if _an is not None: _flcap.setdefault(b2[b][0],[]).append(_an/60.0)
_flcap={g:float(np.median(v)) for g,v in _flcap.items() if v}   # MEDIAN, per user 2026-08-10
_allcap=max(_flcap.values()) if _flcap else None
fig,ax=plt.subplots(figsize=(9,5.2)); rows_b=[]
grp_pts=defaultdict(list); grp_pts3=defaultdict(list); grp_n=defaultdict(set)
for b,pl in bym.items():
    if b in low or _fdrop(b) or b==LONG_SAMPLE: continue           # CF3: drop sparse 2-sisterless on-target; LONG_SAMPLE: ~95min temporal outlier
    pl=sorted([(ts,f) for ts,f in pl if f<=_FL_HI]); g=_fgrp(b)     # CF1: all off-target as ONE group; #11a drop >120 a.u.
    if not pl: continue
    # USER 2026-08-17: per-cell traces are no longer drawn (fit + SEM band replaces them); PERCELL=1 brings
    # the retired look back for the "repeated figures" copy. Points are still collected either way.
    lib.cell_line(ax,[p[0]/60 for p in pl],[p[1] for p in pl],lib.PALETTE.get(g,"#999"),alpha=.18,lw=.8,zorder=1)
    for ts,f in pl: rows_b.append([b,g,round(ts,2),round(f,2)]); grp_pts[g].append((ts/60,f)); grp_pts3[g].append((ts/60,f,b)); grp_n[g].add(b)
ORDER_T=["unModified","1-Sister","3-Sister","4-Sister","Off-Target/Control"]  # CF1/CF3: merged 1+3 off-target; 2-Sister on+off-target dropped; Double-Chromosome globally excluded
def _binmed(P,cap=None):
    P=np.array(sorted(P)); bx=[];by=[]
    for lo in np.arange(0,P[:,0].max()+5,5):
        if cap is not None and lo+2.5>cap: break                     # #11b: stop trend at avg anaphase
        m=(P[:,0]>=lo)&(P[:,0]<lo+5)
        if m.sum()>=3: bx.append(lo+2.5); by.append(np.median(P[m,1]))
    return bx,by
_trends={}
for g in [x for x in ORDER_T if x in grp_pts]+[x for x in grp_pts if x not in ORDER_T]:
    bx,by=_binmed(grp_pts[g],_flcap.get(g))
    if len(bx)>=2:
        # SEM band on the SAME bins the trend uses, computed across CELLS (never across points)
        _cap=_flcap.get(g); _p3=[p for p in grp_pts3[g] if (_cap is None or p[0]<=_cap)]
        _sx,_sy,_ss=lib.binned_mean_sem(_p3,nb=max(2,len(bx)),lo=(bx[0]-2.5),hi=(bx[-1]+2.5))
        if _sx and any(v>0 for v in _ss):
            ax.fill_between(_sx,[v-e for v,e in zip(_sy,_ss)],[v+e for v,e in zip(_sy,_ss)],
                            color=lib.PALETTE.get(g,"#888"),alpha=.22,lw=0,zorder=2)
        ax.plot(bx,by,color=lib.PALETTE.get(g,"#888"),lw=2.6,marker="o",ms=4,zorder=3,
                label=f"{lib.lbl(g).replace(chr(10),' ')} (N={len(grp_n[g])})")
        _trends[g]=(bx,by,lib.PALETTE.get(g,"#888"))
allP=[p for P in grp_pts.values() for p in P]
if len(allP)>=5:
    abx,aby=_binmed(allP,_allcap); ax.plot(abx,aby,"--",color="#111",lw=2.2,zorder=4,label="all data")
# stats between the cohort lines: Kruskal-Wallis on per-cell median fluorescence across cohorts
kw=[[np.median([f for _,f in bym[b]]) for b in grp_n[g]] for g in grp_n]
kw=[v for v in kw if len(v)>=3]
if len(kw)>=2:
    H,pk=stats.kruskal(*kw)
    ax.text(.98,.60,f"Kruskal–Wallis across cohorts\n(per-cell median): H={H:.1f}, p={pk:.3g}",
            transform=ax.transAxes,va="top",ha="right",fontsize=8.5,bbox=dict(boxstyle="round",fc="white",ec="#ccc",alpha=.9))
# CF3: x was labelled "render reference" (unclear) — it is the monitoring-movie timeline (0 = movie start).
ax.set_xlabel("Time from movie start (min)"); ax.set_ylabel("Cell fluorescence (mean inside manual outline, area-normalized, a.u.)")
ax.set_title("Cell fluorescence over time — per-cohort binned-median trend (trend capped at each cohort's MEDIAN anaphase)",loc="left",fontweight="bold",fontsize=10.5)
ax.legend(fontsize=7,ncol=2)
ax.text(.02,.02,"unmodified batches imaged at ≤1 z-stack/min excluded (ITEM 2)",transform=ax.transAxes,va="bottom",fontsize=7,color="#777")
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_over_time.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_fluor_over_time",["batch","cohort","t_sec","fluor_mean_au"],rows_b,
  {"type":"per-cell line + per-cohort binned-median + Kruskal-Wallis",
   "source":"_Fluor_Cropped.tif (16-bit) mean inside outline, on the FLUOR plane by frame",
   "excluded":f"median fluorescence < {LOW_CUT:.0f} a.u. removed; single points > {_FL_HI:.0f} a.u. (outliers) removed; CF3: 2-Sister on+off-target dropped; CF1: off-target merged",
   "trend_cap":"each cohort trend ends at that cohort's MEDIAN anaphase (min from movie start)"},SCRIPT,
  "Cell fluorescence over time (area-normalized mean in outline), per cell + per-cohort trend")
# =============== METAPHASE-ONSET infrastructure (ITEMS 2/3/4) ===============
# Per-batch metaphase onset (s) and per-GROUP MEDIAN metaphase duration (Meta->Ana, min) used to cap trends.
_meta={b:lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")) for b in bym}
_metadur={}
for b in bym:
    if b in low: continue
    _d,_ok=lib.mitotic_duration_min(mr.get(b,{}) or {"Batch Name":b})
    if _ok: _metadur.setdefault(b2[b][0],[]).append(_d)
# USER 2026-08-10: cap each group's trend at that group's MEDIAN metaphase duration (was the MEAN,
# which sits past the median and let every trend overrun).
_metadur={g:float(np.median(v)) for g,v in _metadur.items() if v}
def _mseries(b):
    """per-cell series aligned to metaphase onset: [((ts-meta)/60, f)] for ts>=meta (drop pre-metaphase, >HI)."""
    m=_meta.get(b)
    if m is None: return None
    S=sorted(((ts-m)/60.0,f) for ts,f in bym[b] if ts>=m and f<=_FL_HI)
    return S or None

# ---- CF5 RETIRED: metaphase-onset a.u. over-time plot (G4_fluor_over_time_metaphase) ----
# The user retired this plot ("doesn't make sense to me and visually doesn't make sense. Retire it").
# We still COMPUTE the per-group metaphase-onset trends (_mtrends_au) because the TREND-SCALED companion
# below reuses them, but we DO NOT render or record the a.u. figure into the deck.
# >>> ORCHESTRATOR: also delete the deck reference in build_pdfs_feedback.py:
#        insert_after(10,"G4_fluor_over_time.png","group4/G4_fluor_over_time_metaphase.png",...)
#     (e.g. add  remove(10,"G4_fluor_over_time_metaphase.png")  so the deck doesn't point at a missing PNG).
mgrp=defaultdict(list); mgn=defaultdict(set); _nmeta_skip=0; _meta_rows=[]
for b in bym:
    if b in low or _fdrop(b) or b==LONG_SAMPLE: continue   # CF3 drop 2-sis; CF1 off-target merged; LONG_SAMPLE: ~95min temporal outlier
    S=_mseries(b)
    if not S:
        if _meta.get(b) is None: _nmeta_skip+=1
        continue
    g=_fgrp(b)
    for x,f in S: mgrp[g].append((x,f)); mgn[g].add(b); _meta_rows.append([b,g,round(x,3),round(f,2)])
_mtrends_au={}
for g in [x for x in ORDER_T if x in mgrp]+[x for x in mgrp if x not in ORDER_T]:
    bx,by=_binmed(mgrp[g],_metadur.get(g))            # cap each trend at that group's MEAN metaphase duration
    if len(bx)>=2:
        _mtrends_au[g]=(bx,by,lib.PALETTE.get(g,"#888"))
print(f"CF5: G4_fluor_over_time_metaphase (a.u.) RETIRED — not rendered; computed {len(_mtrends_au)} group trends for the trend-scaled companion ({_nmeta_skip} batches lacked Metaphase Start)")
# CF5: the a.u. metaphase-onset figure is retired (PNG kept + still placed in the deck). Record its plotted
# per-cell data (metaphase-onset a.u. series + per-group binned-median trends) so every placed plot has a CSV.
lib.record_plot("G4_fluor_over_time_metaphase",["batch","cohort","t_min_from_meta","fluor_mean_au"],_meta_rows,
  {"type":"per-cell line (a.u.) from metaphase onset + per-cohort binned-median (RETIRED figure; PNG still placed)",
   "source":"_Fluor_Cropped.tif mean inside outline","x":"time since Metaphase Start (points at/after metaphase)",
   "excluded":f"median<{LOW_CUT:.0f} a.u.; points>{_FL_HI:.0f} a.u.; CF3 2-Sister on+off-target dropped; CF1 off-target merged; LONG_SAMPLE dropped",
   "companion_of":"G4_fluor_over_time"},SCRIPT,"Cell fluorescence from metaphase onset (a.u., retired figure data)")

# ---- ITEM 4: TREND-SCALED companion, now metaphase-onset + per-group start-normalized to 1 + trend to mean metaphase duration ----
figT,axT=plt.subplots(figsize=(9,5.2)); _tx=[];_ty=[]; _mtrends_norm={}; _ts_rows=[]; _ts_p3={}
for g,(bx,by,col) in _mtrends_au.items():
    if by[0]>0: _mtrends_norm[g]=(bx,[max(0.0,v/by[0]) for v in by],col)     # scale so each group's trend starts at 1
for b in bym:                                                                 # faint per-cell lines, each normalized to its own metaphase-onset start
    if b in low or _fdrop(b) or b==LONG_SAMPLE: continue                      # CF3: drop sparse 2-sisterless on-target; LONG_SAMPLE: ~95min temporal outlier
    S=_mseries(b)
    if not S: continue
    f0=S[0][1]
    if f0<=0.5: continue
    g=_fgrp(b)                                                                # CF1: all off-target as ONE group
    lib.cell_line(axT,[p[0] for p in S],[max(0.0,p[1]/f0) for p in S],lib.PALETTE.get(g,"#999"),alpha=.15,lw=.7,zorder=1)
    for p in S:
        _ts_rows.append([b,g,round(p[0],3),round(max(0.0,p[1]/f0),4)])
        _ts_p3.setdefault(g,[]).append((p[0],max(0.0,p[1]/f0),b))   # for the SEM band (across cells)
for g,(bx,byn,col) in _mtrends_norm.items():
    _sx,_sy,_ss=lib.binned_mean_sem(_ts_p3.get(g,[]),nb=max(2,len(bx)),lo=min(bx),hi=max(bx))
    if _sx and any(v>0 for v in _ss):
        axT.fill_between(_sx,[v-e for v,e in zip(_sy,_ss)],[v+e for v,e in zip(_sy,_ss)],color=col,alpha=.22,lw=0,zorder=4)
        _ty+=[v-e for v,e in zip(_sy,_ss)]+[v+e for v,e in zip(_sy,_ss)]
    axT.plot(bx,byn,color=col,lw=2.7,marker="o",ms=4,zorder=5,label=f"{lib.lbl(g).replace(chr(10),' ')} (N={len(mgn[g])})"); _tx+=list(bx); _ty+=list(byn)
axT.axvline(0,color="#333",ls=":",lw=.8); axT.axhline(1.0,color="#bbb",ls=":",lw=.8,zorder=0)
if _tx:
    _mx=(max(_tx)-min(_tx))*0.05+1; _ylo=max(0.0,min(_ty)-(max(_ty)-min(_ty))*0.15-0.05)
    axT.set_xlim(-_mx*0.4,max(_tx)+_mx); axT.set_ylim(_ylo,max(_ty)*1.12+0.05)
axT.set_xlabel("Time from metaphase onset (min)"); axT.set_ylabel("Cell fluorescence (normalized: each group starts at 1)")
axT.legend(fontsize=7,ncol=2)
axT.set_title("Fluorescence from metaphase onset — TREND-SCALED (per-group start=1; trend to mean metaphase duration)",loc="left",fontweight="bold",fontsize=9.3)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_over_time_trendscaled.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_fluor_over_time_trendscaled",["batch","cohort","t_min_from_meta","fluor_norm_own_start1"],_ts_rows,
  {"type":"per-cell line (each normalized to its own metaphase-onset start) + per-group start=1 trend, TREND-SCALED",
   "source":"_Fluor_Cropped.tif mean inside outline","x":"time from metaphase onset (min)",
   "excluded":f"median<{LOW_CUT:.0f} a.u.; points>{_FL_HI:.0f} a.u.; f0<=0.5 dropped; CF3 2-Sister on+off-target dropped; CF1 off-target merged; LONG_SAMPLE dropped",
   "companion_of":"G4_fluor_over_time"},SCRIPT,"Fluorescence from metaphase onset — trend-scaled (per-cell start=1)")
print("ITEM 4 trend-scaled (metaphase-onset, start=1, capped at mean metaphase dur) -> G4_fluor_over_time_trendscaled.png")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")

# ========================= (b-scaled) fluorescence over time — ITEM 3: EVERY group starts at 1, floor 0 =========================
# ITEM 3 replaces the old GLOBAL min-max (which left only some groups near a starting value of 1). Now EVERY
# group is normalized so its trend starts at 1.0 (divide the group's binned-median trend by its first bin);
# individual cells are each normalized to their own first value; all values floored at 0. Two versions:
#   (main)      x = render-reference time (0 = movie start)
#   (metaphase) x = time from metaphase onset (each group re-normalized to 1 at metaphase onset) — ITEM 3 companion
def _draw_scaled01(series_of, cap_of, xlab, ttl, fname, order_keys):
    """series_of(b) -> [(x_min,f)] per cell; cap_of(g) -> trend cap (min) or None.
    SCALING FIX (2026-07-08): the per-GROUP trend is the binned median of the PER-CELL start-normalized
    ratios (each cell divided by its OWN first value), NOT the binned median of RAW fluorescence divided by
    the first bin. The old raw-then-divide trend was dominated by which cells populate each time bin (bright
    vs dim) and by cells with only a few post-metaphase frames landing solely in the first bin — so for the
    metaphase-ONSET series the real (small, ~1-2%) eYFP-Cdc20 degradation cancelled against the cell-
    composition change and the trend collapsed to a FLAT 1.0. Normalizing each cell to itself FIRST removes
    the brightness/composition artifact, so the trend reflects the true mean degradation, and the metaphase-
    onset version now drops at least as much as the movie-start version (verified: ~1.2-1.6% vs ~0.2-0.6%)."""
    fig,ax=plt.subplots(figsize=(9,5.2)); rows=[]
    gpn=defaultdict(list); gn=defaultdict(set); cells_ser={}
    for b in bym:
        if b in low or _fdrop(b) or b==LONG_SAMPLE: continue   # CF3: drop sparse 2-sisterless on-target; LONG_SAMPLE: ~95min temporal outlier
        S=series_of(b)
        if not S: continue
        f0=S[0][1]
        if f0<=0.5: continue                                   # need a real baseline to normalize this cell to 1
        g=_fgrp(b)                                             # CF1: all off-target as ONE group
        Sn=[(x,max(0.0,f/f0)) for x,f in S]                    # normalize each cell to its OWN start=1 (floor 0) BEFORE aggregating
        cells_ser[b]=(g,Sn)
        for x,y in Sn: gpn[g].append((x,y)); gn[g].add(b)
    # per-group trend = binned median of the per-cell start-normalized ratios -> true mean degradation
    g01={}
    for g in [x for x in order_keys if x in gpn]+[x for x in gpn if x not in order_keys]:
        bx,by=_binmed(gpn[g],cap_of(g))
        if len(bx)>=2: g01[g]=(bx,[max(0.0,v) for v in by])
    # faint per-cell lines (already normalized to their own start value)
    _p3={}
    for b,(g,Sn) in cells_ser.items():
        lib.cell_line(ax,[x for x,_ in Sn],[y for _,y in Sn],lib.PALETTE.get(g,"#999"),alpha=.18,lw=.8,zorder=1)
        for x,y in Sn:
            rows.append([b,g,round(x,3),round(y,4)]); _p3.setdefault(g,[]).append((x,y,b))
    for g,(bx,byn) in g01.items():
        _sx,_sy,_ss=lib.binned_mean_sem(_p3.get(g,[]),nb=max(2,len(bx)),lo=min(bx),hi=max(bx))
        if _sx and any(v>0 for v in _ss):
            ax.fill_between(_sx,[v-e for v,e in zip(_sy,_ss)],[v+e for v,e in zip(_sy,_ss)],
                            color=lib.PALETTE.get(g,"#888"),alpha=.22,lw=0,zorder=2)
        ax.plot(bx,byn,color=lib.PALETTE.get(g,"#888"),lw=2.6,marker="o",ms=4,zorder=3,
                label=f"{lib.lbl(g).replace(chr(10),' ')} (N={len(gn[g])})")
    ax.axhline(1.0,color="#bbb",ls=":",lw=.8,zorder=0)
    # Y-AXIS: the whole-outline mean degrades only ~1-2%, so a 0–1.15 axis renders every trend as flat. Zoom
    # to the per-GROUP start-normalized trend range (with a sane minimum span) so the real drop is legible
    # without exaggerating per-cell noise; the faint per-cell ratios beyond the range are simply clipped.
    # SCALING FIX (2026-07-09): drive the y-limits from the GROUP-MEAN trends (the bold lines) ONLY, with a
    # small pad from their own spread — NOT from the faint per-cell outlier traces (which span ~0.90-1.00 and
    # previously, via the max(0.12,...) minimum-span floor, crushed all four group means into the top ~2% of
    # the axis). Per-cell ratios outside this range are simply clipped by the axes.
    _tv=[v for _,byn in g01.values() for v in byn]
    if _tv:
        _lo,_hi=min(_tv),max(_tv)
        _pad=max((_hi-_lo)*0.18,0.004)            # pad from the group-mean spread, floor 0.4% so ties don't collapse
        _ylo,_yhi=_lo-_pad,_hi+_pad
        if _yhi-_ylo<0.02:                        # sane minimum span so near-identical trends aren't over-zoomed to noise
            _c=(_ylo+_yhi)/2.0; _ylo,_yhi=_c-0.01,_c+0.01
        ax.set_ylim(_ylo,_yhi)
    else:
        ax.set_ylim(0,1.15)
    ax.set_xlabel(xlab); ax.set_ylabel("Cell fluorescence (normalized: each group starts at 1, floor 0)")
    ax.set_title(ttl,loc="left",fontweight="bold",fontsize=9.8)
    ax.legend(fontsize=7,ncol=2)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}",bbox_inches="tight"); plt.close()
    lib.record_plot(fname[:-4],["batch","cohort","x","fluor_norm_start1"],rows,
      {"type":"per-cell line + per-group binned-median of per-cell start-normalized ratios (start=1, floor 0)","companion_of":"G4_fluor_over_time",
       "excluded":"slow-cadence unmodified (>=60s) + median<1 a.u. + points>120 a.u.; CF3: 2-Sister on+off-target dropped; CF1: off-target merged"},SCRIPT,ttl)
    print(f"{fname}: {len(g01)} group trends (per-cell start-normalized, binned median) -> {fname}")
# (main) render-reference time
_draw_scaled01(lambda b: sorted([(ts/60,f) for ts,f in bym[b] if f<=_FL_HI]),
               lambda g: None,
               "Time from movie start (min)",
               "Cell fluorescence over time — every group normalized to starting value 1 (floor 0)",
               "G4_fluor_over_time_scaled01.png", ORDER_T)
# (metaphase companion) ITEM 3 second part: start at metaphase onset, re-normalize each group to 1 there, cap trend at mean metaphase dur
_draw_scaled01(_mseries, lambda g: _metadur.get(g),
               "Time from metaphase onset (min)",
               "Cell fluorescence from metaphase onset — every group normalized to 1 at metaphase onset (floor 0)",
               "G4_fluor_over_time_scaled01_metaphase.png", ORDER_T)

# ========================= unmodified-only fluorescence vs duration =========================
fig,ax=plt.subplots(figsize=(6.6,5))
ux=[];uy=[]
for b,c,dur,f in rows_a:
    if c=="unModified": ux.append(dur); uy.append(f)
ax.scatter(ux,uy,s=30,color=lib.PALETTE["unModified"],alpha=.85,edgecolor="white",lw=.4)
if len(ux)>=5:
    rho,pp=stats.spearmanr(ux,uy); m,bb=np.polyfit(ux,uy,1); xr=np.linspace(min(ux),max(ux),40)
    ax.plot(xr,m*xr+bb,"--",color="#333",lw=1.3)
    ax.text(.98,.97,f"Spearman rho={rho:.2f}, p={pp:.3g}, N={len(ux)}",transform=ax.transAxes,va="top",ha="right",fontsize=9,
            bbox=dict(boxstyle="round",fc="white",ec="#ccc",alpha=.95))   # CF6/X1: opaque box, no point overlap
ax.set_xlabel("Metaphase duration (min)")
# CF0: area-normalized = mean inside the manual outline (no background subtraction).
ax.set_ylabel("Cell fluorescence at metaphase (mean inside manual outline, area-normalized, a.u.)")
ax.set_title("Fluorescence vs duration — unmodified only",loc="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_fluor_vs_duration_unmodified.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_fluor_vs_duration_unmodified",["metaphase_duration_min","fluor_mean_au"],
  [[round(a,3),round(b,2)] for a,b in zip(ux,uy)],{"type":"scatter","cohort":"unmodified only",
   "x":"metaphase duration (min)","y":"fluor at metaphase (mean inside outline, area-normalized, a.u.)"},SCRIPT,"Fluor vs duration, unmodified only")
print("fluor-vs-duration N:",len(rows_a),"| trend lines:",nlines,"| trajectory batches:",len(bym),"| unmodified N:",len(ux))
