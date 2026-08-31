"""movement tracking: oscillation, KT-to-plate distance over time, velocity, KT intensity."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, json, glob, os, numpy as np, cv2, matplotlib.pyplot as plt
from collections import defaultdict
import lib

# ---- MIXED-SOURCE STAMP — RETIRED 2026-08-04 ----------------------------------------------------
# Was needed while the plate/control kinetochore came from TrackMate and the polar KT from manual
# marks. Both series are now MANUAL (polar = kt_points marks, plate = `paired` kt_outlines centroids),
# so the figures satisfy the one-source-per-plot rule and the red stamp would now be WRONG. The
# helper is kept (unused) so the history is legible and re-stamping is one call away if a mixed
# source ever comes back.
def _mixed_source_note(fig, text="MIXED SOURCE — polar/sisterless KT = MANUAL marks; plate/control KT = TrackMate tracking (user-approved 2026-07-22)"):
    try:
        fig.text(0.005, 0.002, text, fontsize=7.2, color="#b30000", ha="left", va="bottom")
    except Exception:
        pass


lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
import os as _osR; OUT=_osR.environ.get("KT_SWEEP_OUT",OUT); _osR.makedirs(OUT,exist_ok=True)
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
coh=lib.assign_cohorts(); b2={b:k for k,lst in coh.items() for b,_ in lst}
def ps(b):
    try: return float(mr.get(b,{}).get("Pixel Size (um)",""))
    except: return 0.062
# ---- O1/O10: displacement normalized to a fixed 20s interval (real inter-frame time varies batch-to-batch;
# frames.json t_sec is baked into every kt_points row, so use the ACTUAL elapsed time, not the frame count) ----
INTERVAL=20.0
def disp20(dx_um,dy_um,dt):
    """Straight-line displacement (µm) rate-scaled to a 20s interval: estimate the move over 20s from the
    measured step assuming constant velocity across the gap (O1: 'do your best to estimate based on the
    movement between the two timepoints the 20s interval falls between'). None if dt<=0."""
    if dt<=0: return None
    return np.hypot(dx_um,dy_um)*(INTERVAL/dt)
def segments20(pts_um):
    """O10 effective-vs-total helper. pts_um = sorted [(t_sec,x_um,y_um)]. Group consecutive points into
    ~20s segments; per segment return (effective, total, t_mid) both rate-scaled to 20s where
    effective = net endpoint displacement (ignores back-and-forth) and total = summed sub-step path length."""
    pts=sorted(pts_um); out=[]; i=0; n=len(pts)
    while i<n-1:
        j=i; tot=0.0
        while j<n-1 and (pts[j+1][0]-pts[i][0])<INTERVAL*1.5:
            tot+=np.hypot(pts[j+1][1]-pts[j][1],pts[j+1][2]-pts[j][2]); j+=1
            if (pts[j][0]-pts[i][0])>=INTERVAL: break
        if j==i:
            j=i+1; tot=np.hypot(pts[j][1]-pts[i][1],pts[j][2]-pts[i][2])
        dt=pts[j][0]-pts[i][0]
        if dt>0:
            eff=np.hypot(pts[j][1]-pts[i][1],pts[j][2]-pts[i][2]); sc=INTERVAL/dt
            out.append((eff*sc,tot*sc,0.5*(pts[i][0]+pts[j][0])))
        i=j
    return out
abl_t=defaultdict(list)   # populated after the kt_points load below
def first_abl(b):
    """First-ablation time in the SAME elapsed-seconds coordinate as the KT tracks: the min t_sec of the
    ablation-marker annotations (pre/post_abl). NOTE: the master 'First Ablation (s)' column is NOT usable
    here — it mixes absolute Unix-epoch timestamps (~1.7e9 s) with elapsed seconds, which would offset
    lines by ~30M minutes. None if the batch has no ablation marks (e.g. unmodified)."""
    return min(abl_t[b]) if abl_t.get(b) else None

# KT tracks
rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
trk=defaultdict(lambda: defaultdict(list))
for r in rows[1:]:
    lab=r[ix['label']].strip()
    if lab not in ("polar","sisterless","paired_kt","cytosol_bg"): continue
    if lib.is_mad1(r[ix['batch']].strip()) or lib.plot_excluded(r[ix['batch']].strip()): continue
    if lib.is_misplaced_id(r[ix['id']]): continue
    try: trk[r[ix['batch']].strip()][lab].append((int(r[ix['frame']]),float(r[ix['t_sec']]),float(r[ix['x']]),float(r[ix['y']])))
    except: pass
for r in rows[1:]:                              # first-ablation time (elapsed t_sec) from ablation-marker annotations
    lab=r[ix['label']].strip()
    if lab in ('pre_abl','pre_abl_pair','post_abl','post_abl_pair') and not lib.is_mad1(r[ix['batch']].strip()):
        try: abl_t[r[ix['batch']].strip()].append(float(r[ix['t_sec']]))
        except: pass
def cyto_at(b,frame,t):
    """O3: background pair for a KT at (frame,t). PREFER a cytosol_bg mark on the SAME frame; else the
    nearest in time. NOTE (troubleshoot finding): cytosol_bg is SPARSE in the data (median ~2 marks/cell,
    not one-per-frame), so most polar frames fall back to nearest-in-time — see the cyto_sparsity_diag log."""
    c=trk[b].get('cytosol_bg',[])
    if not c: return None
    same=[p for p in c if p[0]==frame]
    if same: return min(same,key=lambda p:abs(p[1]-t))
    return min(c,key=lambda p:abs(p[1]-t))
def cyto_near(b,t):   # legacy nearest-in-time (kept for callers without a frame)
    c=trk[b].get('cytosol_bg',[])
    return min(c,key=lambda p:abs(p[1]-t)) if c else None
def sister(b):
    a=trk[b].get('polar',[]); c=trk[b].get('sisterless',[])
    return sorted(a if len(a)>=len(c) else c)
usable=[b for b in trk if len(sister(b))>=5]
# ---- GLOBAL exclusions for the Group-4 movement plots (feedback 2026-07-06) ----
# ITEM 6: exactly one sample (20250401 ptk_yfpcdc20_28) tracks to ~95 min — a temporal outlier that
# stretches the x-axis of every time plot; remove it from ALL these plots and flag for investigation.
LONG_SAMPLE="20250401 ptk_yfpcdc20_28"
if LONG_SAMPLE in usable:
    lib.log_review("long_temporal_outlier",LONG_SAMPLE,"~95 min track","track stretches to ~95 min from start (>2x the next-longest); EXCLUDED from oscillation / plate-distance / KT-intensity plots per feedback — investigate why the track runs so long")
# ITEMS 1/2/3: drop unassigned-cohort cells (no cohort in assign_cohorts — e.g. 20250711 double ablation_4,
# a globally-excluded double-chromosome cell). Don't plot them; flag for the review list.
for b in [b for b in usable if b2.get(b) is None]:
    lib.log_review("kt_movement_unassigned",b,"no cohort","unassigned-cohort cell (double-chromosome / not in any baseline cohort) EXCLUDED from Group-4 movement plots — investigate & assign a cohort or confirm exclusion")
usable=[b for b in usable if b2.get(b) is not None and b!=LONG_SAMPLE and not lib.excluded(b)]   # + global REVIEW_EXCLUDE outlier (20260107 …_5)
# ITEM 2 investigation: some polar-KT cells DO have paired 'control' kinetochore annotations (label
# paired_kt) that are NOT being plotted — flag them so the intensity plots can add a control comparison.
_paired_cells=sorted(b for b in usable if trk.get(b,{}).get('paired_kt'))
for b in _paired_cells:
    lib.log_review("kt_intensity_has_paired_control",b,f"{len(trk[b]['paired_kt'])} paired_kt pts","this polar-KT cell HAS paired control-KT annotations that the intensity plots currently ignore — add a per-cell control (sister/plate KT) comparison")
# ---- O3 TROUBLESHOOT (background subtraction / 3-sisterless lower value): audit cytosol_bg pairing.
# The bg is subtracted from a cytosol_bg mark, IDEALLY one on the SAME frame as each polar mark. Audit how
# often that actually holds. Finding (data): cytosol_bg is SPARSE (median ~2 marks/cell), so for most polar
# frames the nearest cytosol_bg is many seconds away and the SAME sparse bg gets reused across the track —
# which biases per-frame intensities and can make a whole cohort (e.g. 3-sisterless) read low if its cytosol
# marks happen to sit on brighter-background frames. Flag every cell whose polar frames lack a same-frame
# cytosol_bg or whose nearest bg is >45s away, per cohort, so the user can add per-frame cytosol marks. ----
for b in usable:
    pol=sister(b); cy=trk.get(b,{}).get('cytosol_bg',[])
    if not pol: continue
    if not cy:
        lib.log_review("cyto_sparsity_diag",b,f"cohort={b2.get(b)} cyto=0","NO cytosol_bg marks — KT intensity has NO valid per-cell background; excluded from bg-subtracted intensity"); continue
    _cyf=set(p[0] for p in pol) & set(c[0] for c in cy)          # polar frames with a same-frame cytosol mark
    _samefrac=len(_cyf)/len(set(p[0] for p in pol))
    _gaps=[min(abs(p[1]-c[1]) for c in cy) for p in pol]; _medgap=float(np.median(_gaps))
    if _samefrac<0.5 or _medgap>45:
        lib.log_review("cyto_sparsity_diag",b,f"cohort={b2.get(b)} cyto={len(cy)} same-frame={_samefrac:.0%} med-gap={_medgap:.0f}s",
            "sparse cytosol_bg: most polar frames have NO same-frame background pair (nearest bg reused across the track) — unreliable per-frame subtraction; add per-frame cytosol_bg marks (esp. review 3-sisterless cohort)")

# plates: batch -> frame(int) -> polyline
plates=defaultdict(dict)
mp=list(csv.reader(open("/Volumes/4 MB/annotations/meta_plates.csv"))); jx={c:i for i,c in enumerate(mp[0])}
for r in mp[1:]:
    b=r[jx['batch']].strip()
    try: plates[b][int(r[jx['frame']])]=np.array(json.loads(r[jx['points']]),float)
    except: pass
def plate_at(b,f):
    """Metaphase-plate polyline for frame f. Prefer the EXACT frame; else fall back to the NEAREST plate frame.
    2026-07-11 (user): the metaphase plate is a FIXED spatial reference (the division midline). Some cells have
    the plate drawn only during metaphase while the polar KT is tracked post-anaphase on DIFFERENT frames (e.g.
    20250411 ptk_yfpcdc20_11: plate f24-75, polar f78-114, ZERO same-frame overlap) — the exact-frame-only match
    dropped the whole cell. Nearest-frame recovers it against the fixed metaphase plate. Exact still preferred, so
    cells whose plate IS tracked per-frame are unchanged."""
    pm=plates.get(b)
    if not pm: return None
    if f in pm: return pm[f]
    return pm[min(pm,key=lambda k:abs(k-f))]
def pt_poly(p,poly):
    p=np.array(p,float); d=1e18
    for i in range(len(poly)-1):
        a,bb=poly[i],poly[i+1]; ab=bb-a; L=np.dot(ab,ab)
        t=0 if L<1e-9 else np.clip(np.dot(p-a,ab)/L,0,1)
        d=min(d,np.hypot(*(a+t*ab-p)))
    return d

# ---------- 1. Oscillation (displacement per 20s interval, µm) ----------
# O1: was per-FRAME displacement; now normalized to a fixed 20s interval using the actual t_sec gap.
osc=[]; osc_b=[]; osc_eff=[]; osc_eff_b=[]; osc_eff_t=[]   # osc_eff = O10 effective (net) companion
# osc_eff_t holds each segment's own time (2026-07-29): the recorded table used to carry only
# (track, displacement), so there was no time axis to restrict and the plot could not be windowed.
for b in usable:
    # KT IDENTITY (2026-08-04): sister(b) pools EVERY polar/sisterless mark in the cell, and a triple cell
    # carries up to 6 at once — so stepping through it in time order measured the gap BETWEEN kinetochores,
    # not the motion of one. (The old `if f1==f0` guard only hid the same-frame case.) Split per KT first.
    _meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)",""))   # for user-flagged per-point exclusion (t_min from metaphase)
    for tr in lib.link_kt_tracks(sister(b),ps(b)):
        for (f0,t0,x0,y0),(f1,t1,x1,y1) in zip(tr,tr[1:]):
            if f1==f0: continue
            d=disp20((x1-x0)*ps(b),(y1-y0)*ps(b),t1-t0)   # 20s-normalized per-step displacement
            if d is None: continue
            if lib.osc_point_excluded(b,(0.5*(t0+t1)-(_meta or 0))/60): continue   # user-flagged oscillation outlier — REMOVED everywhere
            osc.append(d); osc_b.append(b)
        for (e,_tot,_tm) in segments20([(t,x*ps(b),y*ps(b)) for (f,t,x,y) in tr]):   # O10 effective (net endpoint / 20s)
            if lib.osc_point_excluded(b,(_tm-(_meta or 0))/60): continue   # user-flagged oscillation outlier — REMOVED everywhere
            osc_eff.append(e); osc_eff_b.append(b); osc_eff_t.append(_tm)
# exclude implausible per-20s steps (the ~25µm outlier + 10-17µm cluster the user flagged) — tracking glitches.
PLATE_OSC_HI=3.0   # plate-KT ceiling (USER 2026-08-05)
OSC_HI=8.0; _kp=[i for i in range(len(osc)) if osc[i]<=OSC_HI]
_exb=sorted(set(osc_b[i] for i in range(len(osc)) if osc[i]>OSC_HI))
for b in _exb: lib.log_review("oscillation_outlier",b,f"step>{OSC_HI}µm/frame","implausible displacement EXCLUDED (tracking glitch); review")
osc=[osc[i] for i in _kp]; osc_b=[osc_b[i] for i in _kp]
OSC_EXCLUDE_BATCHES=set(_exb)|{LONG_SAMPLE}   # propagate the same exclusions (+ ITEM 6 long sample) to slides 60 & 61
# --- plate-aligned per-frame displacement from MANUAL paired outlines (plate KTs traced AFTER metaphase start) ---
# user request (slide 34): overlay typical plate-aligned frame displacement as a comparison to the polar KTs.
# Plate KTs = the MANUAL paired-outline runs with the fullest traces between metaphase and anaphase that stay closest
# to the drawn meta_plate line (same selection as group4_tracking_dist.py); step = consecutive-frame move (µm).
# --- plate-control KTs from MANUAL outlines (USER 2026-08-04) ------------------------------------
# "the snapped circles and/or kinetochore outlines, and any other manual annotations ive made should
# automatically override anything generated by trackmate". This file's plate/control series used to
# come from TrackMate spot CSVs; it now comes from the manually traced `paired` kinetochore outlines
# in kt_outlines.csv — one polygon per KT per frame, the polygon centroid IS the KT position. Same
# conversion group4_tracking_dist.py took on 2026-08-03, so the two files agree on the plate group.
PLATE_CTRL_MAX_UM=15.0                 # a plate KT sits AT the plate by definition; further = tracing artefact
# IDENTITY MATTERS HERE. A cell carries up to 4 `paired` outlines PER FRAME (one per plate KT), so grouping
# raw kt_outlines rows by frame-adjacency chains DIFFERENT kinetochores together and every "displacement"
# becomes the gap between two KTs — which inflated the plate violin to a 1.90 µm median (2026-08-04, caught
# on the first render). The linked file below already resolves each outline to a track_id, so one track =
# one kinetochore followed through time, which is what a displacement series requires.
_PAIRED_TRACKS=defaultdict(lambda: defaultdict(list))   # batch -> track_id -> [(t_sec, x_px, y_px)]
try:
    for _r in csv.DictReader(open("/Volumes/4 MB/annotations/KT_OUTLINE_TRACKS_20260723.csv")):
        if lib.is_prophase_ablation(_r.get("batch","")): continue   # prophase excluded (no prophase group)
        if (_r.get("label") or "").strip()!="paired": continue
        _b=_r["batch"].strip()
        if lib.is_mad1(_b): continue
        try: _PAIRED_TRACKS[_b][_r["track_id"]].append((float(_r["t_sec"]),float(_r["cx_px"]),float(_r["cy_px"])))
        except Exception: continue
except Exception: pass
for _b in _PAIRED_TRACKS:
    for _t in _PAIRED_TRACKS[_b]: _PAIRED_TRACKS[_b][_t].sort()
print(f"manual paired-KT tracks (plate controls): {len(_PAIRED_TRACKS)} cells, "
      f"{sum(len(v) for v in _PAIRED_TRACKS.values())} tracks, "
      f"{sum(len(s) for v in _PAIRED_TRACKS.values() for s in v.values())} outlines")
def _plate_axis(b):
    fr=plates.get(b)
    if not fr: return None
    pts=list(fr.values())[-1]        # ITEM 7: use the LAST meta_plate row (matches group4_tracking_dist so the plate group agrees)
    if len(pts)<2: return None
    c=pts.mean(axis=0); v=pts[-1]-pts[0]; nrm=np.hypot(*v)
    if nrm<1e-6: return None
    d=v/nrm; return c,np.array([-d[1],d[0]])            # (center, unit-normal) for distance projection
def _load_tracks(b):
    """Plate-control KT traces for a batch as {run_id: [(t_sec, x_px, y_px), ...]}.

    MANUAL SOURCE (2026-08-04): built from the traced `paired` kinetochore outlines, not TrackMate — one
    track per kinetochore, taken from the linked KT_OUTLINE_TRACKS file so consecutive points are the SAME
    KT at successive times (see the identity note above). Tracks shorter than 3 points are dropped: they
    can't give a displacement distribution. Returns the same shape the TrackMate loader did, so every
    selection/consumer below — fullest tracks nearest the plate, top 3 — is unchanged."""
    return {tid:sp for tid,sp in _PAIRED_TRACKS.get(b,{}).items() if len(sp)>=3}
osc_pla=[]; osc_pla_b=[]; _pla_dropped=[]
for b in plates:
    if b in OSC_EXCLUDE_BATCHES or b2.get(b) is None: continue   # ITEM 7: also drop unassigned cohort from the plate group (matches tracking)
    ax_=_plate_axis(b); tr=_load_tracks(b)
    if ax_ is None or not tr: continue
    c,nrml=ax_
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); ana=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    if meta is None: continue
    hi=ana if (ana is not None and ana>meta) else meta+1e9
    def _nspan(sp): return sum(1 for t,x,y in sp if meta<=t<=hi)
    def _mdist(sp):
        dd=[abs(np.dot(np.array([x,y])-c,nrml))*ps(b) for t,x,y in sp if meta<=t<=hi]; return np.median(dd) if dd else 1e9
    span_med=np.median([_nspan(s) for s in tr.values()]) or 1
    full=[(tid,sp) for tid,sp in tr.items() if _nspan(sp)>=max(3,span_med)]
    for tid,sp in sorted(full,key=lambda kv:_mdist(kv[1]))[:3]:      # plate KTs = fullest traces closest to the plate
        ss=[s for s in sorted(sp) if meta<=s[0]<=hi]
        # a plate/paired control KT sits AT the plate by definition — a traced polygon that lands far off
        # it is a tracing artefact, not a plate KT (same screen as group4_tracking_dist, 2026-08-03)
        _far=[s for s in ss if abs(np.dot(np.array([s[1],s[2]])-c,nrml))*ps(b)>PLATE_CTRL_MAX_UM]
        if _far:
            lib.log_review("plate_ctrl_far_from_plate",b,f"{len(_far)}/{len(ss)} pts",
                           f"manual paired-KT control point >{PLATE_CTRL_MAX_UM:g} µm from the drawn plate — dropped from the oscillation plate group")
            ss=[s for s in ss if s not in _far]
        for (t0,x0,y0),(t1,x1,y1) in zip(ss,ss[1:]):
            if t1>t0:
                d=disp20((x1-x0)*ps(b),(y1-y0)*ps(b),t1-t0)   # O1: 20s-normalized plate-KT step
                # USER 2026-08-05: "remove the outliers past 3um for the plate kt". A plate-resident
                # kinetochore does not translate 3 µm in 20 s; anything above that is a tracing artefact
                # in the paired outline (a polygon drawn on the wrong dot, or a frame where the KT is out
                # of plane), not motion. Separate from the polar cap (OSC_HI=8) on purpose — the polar KT
                # genuinely does make large excursions, so the two series get different ceilings.
                if d is not None and d<=PLATE_OSC_HI: osc_pla.append(d); osc_pla_b.append(b)
                elif d is not None: _pla_dropped.append((b,d))

fig,ax=plt.subplots(figsize=(7.5,5)); rowsO=[]
# ITEM 1: the polar-KT pool spans MULTIPLE ablation groups -> code the scatter markers by cohort so the
# groups are distinguishable (violin body = aggregate; each dot colored by its cell's cohort).
_polcohs=sorted(set(b2.get(b) for b in osc_b),key=lambda g:(g is None,g))
# --- group 0: polar kinetochore (per-cohort colored markers) ---
if osc:
    for bd in ax.violinplot([osc],positions=[0],widths=.7,showextrema=False)['bodies']:
        bd.set_facecolor("#762a83"); bd.set_alpha(.22); bd.set_edgecolor("#762a83")
    _jit=(np.random.RandomState(0).rand(len(osc))-.5)*.18
    for gcoh in _polcohs:
        idx=np.array([j for j in range(len(osc)) if b2.get(osc_b[j])==gcoh],dtype=int)
        if len(idx): ax.scatter(idx*0+_jit[idx],[osc[j] for j in idx],s=11,color=lib.PALETTE.get(gcoh,"#888"),alpha=.6,edgecolor="none")
    ax.hlines(np.median(osc),-.3,.3,color="#762a83",lw=2.2)                                 # median (solid)
    ax.hlines(np.mean(osc),-.24,.24,color="#762a83",lw=1.3,ls=(0,(2,1.5)))                  # mean (dashed)
    ax.text(0,max(osc)*1.02,f"x̄ {np.mean(osc):.2f}µm\nmed {np.median(osc):.2f}µm\nN={len(osc)}",ha="center",va="bottom",fontsize=7.5)
    for x in osc: rowsO.append(["polar kinetochore",round(x,4)])
# --- group 1: plate KT (manual paired outlines), single colour ---
if osc_pla:
    for bd in ax.violinplot([osc_pla],positions=[1],widths=.7,showextrema=False)['bodies']:
        bd.set_facecolor("#1b5e20"); bd.set_alpha(.3); bd.set_edgecolor("#1b5e20")
    ax.scatter(np.full(len(osc_pla),1)+(np.random.RandomState(1).rand(len(osc_pla))-.5)*.18,osc_pla,s=lib.VIOLIN_DOT_S,color="#1b5e20",alpha=.5,edgecolor="none")
    ax.hlines(np.median(osc_pla),1-.3,1+.3,color="#1b5e20",lw=2.2)
    ax.hlines(np.mean(osc_pla),1-.24,1+.24,color="#1b5e20",lw=1.3,ls=(0,(2,1.5)))
    ax.text(1,max(osc_pla)*1.02,f"x̄ {np.mean(osc_pla):.2f}µm\nmed {np.median(osc_pla):.2f}µm\nN={len(osc_pla)}",ha="center",va="bottom",fontsize=7.5)
    for x in osc_pla: rowsO.append(["plate KT (manual paired outlines)",round(x,4)])
if osc and osc_pla and len(osc)>=2 and len(osc_pla)>=2:
    from scipy import stats as _stO
    try:
        _pO=_stO.mannwhitneyu(osc,osc_pla,alternative="two-sided").pvalue
        ax.text(.5,.02,f"polar vs plate: Mann–Whitney p={_pO:.2g}",transform=ax.transAxes,ha="center",fontsize=8,color="#333")
    except Exception: pass
ax.set_xticks([0,1]); ax.set_xticklabels(["polar kinetochore","plate KT (manual paired outlines)"],fontsize=9.5); ax.set_ylabel("Displacement per 20s interval (µm)")
from matplotlib.lines import Line2D as _L0
from matplotlib.patches import Patch as _P0
# O2: dropped the "polar:" prefix (redundant with the x-axis label; green cohort colour was reading as 'plate')
_coh_handles=[_L0([0],[0],marker="o",ls="none",color=lib.PALETTE.get(g,"#888"),label=f"{lib.lbl(g).splitlines()[0]} (N={sum(1 for bb in osc_b if b2.get(bb)==g)})") for g in _polcohs]
ax.legend(handles=_coh_handles+[_P0(facecolor="#1b5e20",alpha=.3,edgecolor="#1b5e20",label="plate KT (manual paired outlines, after metaphase)"),
                   _L0([0],[0],color="#444",lw=2.2,label="median"),
                   _L0([0],[0],color="#444",lw=1.3,ls=(0,(2,1.5)),label="mean")],fontsize=7.5,loc="upper right")
ax.set_title("Kinetochore oscillation — displacement per 20s interval: polar (by cohort) vs plate-aligned (manual paired outlines)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_oscillation.png",bbox_inches="tight"); plt.close()
print(f"oscillation: polar N={len(osc)} steps | plate-tracking N={len(osc_pla)} steps ({len(set(osc_pla_b))} cells)")
lib.record_plot("G4_oscillation",["track","disp_um_per_20s"],rowsO,
  {"type":"violin polar vs plate","track":"polar (annotation) + plate-control (MANUAL paired kt_outlines centroids, post-metaphase)","y":"displacement per 20s interval (rate-scaled from actual t_sec gap)"},SCRIPT,"Polar vs plate-aligned displacement per 20s interval")

# ---------- 1b. O10 — EFFECTIVE (net endpoint) displacement per 20s, the OTHER method (companion to G4_oscillation) ----------
# G4_oscillation above sums straight-line steps (≈ TOTAL path per interval). This companion uses the
# net endpoint-to-endpoint displacement over each ~20s segment (ignores back-and-forth motion).
_effkeep=[i for i in range(len(osc_eff)) if osc_eff[i]<=OSC_HI and osc_eff_b[i] not in OSC_EXCLUDE_BATCHES]
osc_eff_t=[osc_eff_t[i] for i in _effkeep]; osc_eff_b=[osc_eff_b[i] for i in _effkeep]
osc_eff=[osc_eff[i] for i in _effkeep]
figE,axE=plt.subplots(figsize=(6.2,5)); rowsE=[]
if osc_eff:
    for bd in axE.violinplot([osc_eff],positions=[0],widths=.7,showextrema=False)['bodies']:
        bd.set_facecolor("#762a83"); bd.set_alpha(.25); bd.set_edgecolor("#762a83")
    axE.scatter(np.zeros(len(osc_eff))+(np.random.RandomState(0).rand(len(osc_eff))-.5)*.18,osc_eff,s=lib.VIOLIN_DOT_S,color="#762a83",alpha=.5,edgecolor="none")
    axE.hlines(np.median(osc_eff),-.3,.3,color="#762a83",lw=2.2); axE.hlines(np.mean(osc_eff),-.24,.24,color="#762a83",lw=1.3,ls=(0,(2,1.5)))
    axE.text(0,max(osc_eff)*1.02,f"x̄ {np.mean(osc_eff):.2f}µm\nmed {np.median(osc_eff):.2f}µm\nN={len(osc_eff)}",ha="center",va="bottom",fontsize=8)
    rowsE=[["polar kinetochore (effective/net per 20s)",round(x,4)] for x in osc_eff]
axE.set_xticks([0]); axE.set_xticklabels(["polar kinetochore"]); axE.set_ylabel("Effective (net) displacement per 20s interval (µm)")
axE.set_title("Kinetochore oscillation — EFFECTIVE (net endpoint) displacement per 20s (O10 companion to G4_oscillation)\nnet start to end move per ~20s segment; ignores back-and-forth (vs the per-step/total-path G4_oscillation)",loc="left",fontweight="bold",fontsize=9)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_oscillation_effective.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_oscillation_effective",["batch","t_sec","effective_disp_um_per_20s"],
  [[bb,round(tt,2),round(ee,4)] for bb,tt,ee in zip(osc_eff_b,osc_eff_t,osc_eff)],
  {"type":"violin (effective/net per 20s)","method":"net endpoint displacement per ~20s segment (O10 'other method')","companion_of":"G4_oscillation"},SCRIPT,"Effective (net) displacement per 20s — O10 companion")
print(f"O10 effective companion: polar N={len(osc_eff)} segments -> G4_oscillation_effective.png")

# ---------- 2. Plate distance over time + 3. velocity ----------
fig,ax=plt.subplots(figsize=(9,5.2)); rowsP=[]; vel=[]; vd=[]; _bygP=defaultdict(list); _bygP3=defaultdict(list)
plotted=[]   # (batch, cohort) for cells that get a line -> x-axis metaphase/anaphase tics
for b in usable:
    if b not in plates: continue
    if b in OSC_EXCLUDE_BATCHES: continue                       # propagate oscillation exclusions (slide 61)
    g=b2.get(b)
    if g is None:                                               # unassigned cohort (N=1) — don't plot, log
        lib.log_review("plate_distance_unassigned",b,"no cohort","unassigned-cohort cell EXCLUDED; needs a cohort"); continue
    # KT IDENTITY (2026-08-04): one series PER KINETOCHORE — pooling them drew one line zig-zagging
    # between up to 6 different KTs (see lib.link_kt_tracks).
    series=[]
    for _kt in lib.link_kt_tracks(sister(b),ps(b)):
        for f,t,x,y in _kt:
            pl=plate_at(b,f)
            if pl is None: continue
            d=pt_poly((x,y),pl)*ps(b); series.append((t/60.0,d)); rowsP.append([b,round(t/60,2),round(d,3)])
    series=sorted(series)
    if len(series)>=2:
        # USER 2026-08-17: no per-sample spaghetti on multi-sample line plots -- fit + SEM band below.
        lib.cell_line(ax,[s[0] for s in series],[s[1] for s in series],lib.PALETTE.get(g,"#888"),alpha=.5,lw=1.0,marker="o",ms=2)
        plotted.append((b,g))
        for (t0,d0),(t1,d1) in zip(series,series[1:]):
            if t1>t0:
                _v=(d1-d0)/(t1-t0); vel.append((g,_v)); vd.append(((d0+d1)/2.0,_v))   # (cohort, signed velocity); also (distance, velocity)
        for s in series: _bygP[g].append(s); _bygP3[g].append((s[0],s[1],b))
# per-group AVERAGE anaphase time (elapsed min) -> cap the trend there (#11b)
_anacap={}
for _b,_g in plotted:
    _an=lib.parse_time(mr.get(_b,{}).get("Anaphase Onset (s)",""))
    if _an is not None: _anacap.setdefault(_g,[]).append(_an/60.0)
_anacap={_g:float(np.median(_v)) for _g,_v in _anacap.items() if _v}  # USER 2026-08-10: MEDIAN, not mean
# per-group binned-median TREND lines (capped at the group's avg anaphase)
_trends={}   # g -> (gx,gy,color) for the trendline-scaled companion (#11c)
for g,pp in _bygP.items():
    a=np.array(sorted(pp))
    if len(a)<5: continue
    _cap=_anacap.get(g,a[:,0].max())
    gx=[];gy=[]
    for lo in np.arange(0,a[:,0].max()+4,4):
        if lo+2>_cap: break                                    # #11b: stop trend at the group's avg anaphase
        m=(a[:,0]>=lo)&(a[:,0]<lo+4)
        if m.sum()>=3: gx.append(lo+2); gy.append(np.median(a[m,1]))
    if len(gx)>=2:
        _sx,_sy,_ss=lib.binned_mean_sem(_bygP3.get(g,[]),nb=max(2,len(gx)),lo=min(gx)-2,hi=max(gx)+2)
        if _sx and any(v>0 for v in _ss):
            ax.fill_between(_sx,[v-e for v,e in zip(_sy,_ss)],[v+e for v,e in zip(_sy,_ss)],
                            color=lib.PALETTE.get(g,"#888"),alpha=.22,lw=0,zorder=4)   # SEM across cells
        ax.plot(gx,gy,color=lib.PALETTE.get(g,"#888"),lw=3,zorder=5); _trends[g]=(gx,gy,lib.PALETTE.get(g,"#888"))
# ---- ITEM 5 FIX: the old "floating dashed tics at ~y=0" were per-cell metaphase/anaphase marks drawn as
# short stubs near the axis, which read as dashes hovering at a random height. Replace with ONE clean
# FULL-HEIGHT vertical line PER COHORT at that cohort's average metaphase (dotted) and average anaphase
# (dashed), colored by cohort and explained in the legend -> unambiguous, spans the whole plot.
_metacap={}
for _b,_g in plotted:
    _ms=lib.parse_time(mr.get(_b,{}).get("Metaphase Start (s)",""))
    if _ms is not None: _metacap.setdefault(_g,[]).append(_ms/60.0)
_metacap={_g:float(np.median(_v)) for _g,_v in _metacap.items() if _v}  # USER 2026-08-10: MEDIAN, not mean
_xlo,_xhi=ax.get_xlim()
for g in sorted(set(list(_metacap)+list(_anacap))):
    col=lib.PALETTE.get(g,"#888")
    if g in _metacap and _xlo<=_metacap[g]<=_xhi:
        ax.axvline(_metacap[g],color=col,lw=1.3,ls=(0,(1,1.5)),alpha=.8,zorder=3)         # avg metaphase (dotted, full height)
    if g in _anacap and _xlo<=_anacap[g]<=_xhi:
        ax.axvline(_anacap[g],color=col,lw=1.6,ls=(0,(5,2)),alpha=.9,zorder=3)            # avg anaphase (dashed, full height)
# O5: x here is the raw movie-elapsed t_sec/60 (from movie start) — NOT anchored to ablation or metaphase.
# A metaphase-onset companion (x = t - Metaphase Start) is built below (G4_plate_distance_time_metaphase).
ax.set_xlabel("Time (min, from movie start)"); ax.set_ylabel("KT distance to metaphase plate (µm)")
gsP=sorted(_bygP.keys())
_npd={}
for r in rowsP: _npd.setdefault(b2.get(r[0]),set()).add(r[0])
from matplotlib.lines import Line2D
_h=[Line2D([0],[0],color=lib.PALETTE.get(g,"#888"),lw=2,label=f"{lib.lbl(g).splitlines()[0]} (N={len(_npd.get(g,[]))}; bold=trend)") for g in gsP]
_h+=[Line2D([0],[0],color="#555",lw=1.3,ls=(0,(1,1.5)),label="cohort avg metaphase (dotted)"),
     Line2D([0],[0],color="#555",lw=1.6,ls=(0,(5,2)),label="cohort avg anaphase (dashed)")]
ax.legend(handles=_h,fontsize=7,ncol=2,title="cohort (vertical lines = per-cohort avg event times)")
ax.set_title(f"Polar/sisterless-kinetochore distance to metaphase plate over time (N={len(set(r[0] for r in rowsP))} cells)",loc="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_plate_distance_time",["batch","t_min","plate_dist_um"],rowsP,
  {"type":"per-cell line","source":"KT track vs meta_plate polyline (perp distance)","x":"time from MOVIE START (raw t_sec/60)"},SCRIPT,"KT-to-plate distance over time")
# ---- O5: METAPHASE-ONSET companion (x = time since Metaphase Start; only points at/after metaphase) ----
figM,axM=plt.subplots(figsize=(9,5.2)); rowsPm=[]; _bygPm=defaultdict(list); _bygPm3=defaultdict(list); _plottedM=[]
_cellPm=defaultdict(dict)   # cohort -> batch -> series, for the within-cell trend (see the note below)
for b in usable:
    if b not in plates or b in OSC_EXCLUDE_BATCHES: continue
    g=b2.get(b)
    if g is None: continue
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)",""))
    if meta is None:
        lib.log_review("plate_distance_meta_no_metaphase",b,"","no Metaphase Start — cannot anchor metaphase-onset distance plot"); continue
    # KT IDENTITY (2026-08-04): one series PER KINETOCHORE (see lib.link_kt_tracks).
    series=[]
    for _kt in lib.link_kt_tracks(sister(b),ps(b)):
        for f,t,x,y in _kt:
            pl=plate_at(b,f)
            if pl is None or t<meta: continue
            d=pt_poly((x,y),pl)*ps(b); series.append(((t-meta)/60.0,d)); rowsPm.append([b,round((t-meta)/60,2),round(d,3)])
    series=sorted(series)
    if len(series)>=2:
        lib.cell_line(axM,[s[0] for s in series],[s[1] for s in series],lib.PALETTE.get(g,"#888"),alpha=.5,lw=1.0,marker="o",ms=2)
        _plottedM.append((b,g))
        for s in series: _bygPm[g].append(s); _bygPm3[g].append((s[0],s[1],b))
        _cellPm[g][b]=series      # keep cell identity: the pooled trend below is composition-biased without it
# per-cohort avg anaphase (min after metaphase) -> cap trend + full-height dashed marker
_anacapM={}
for _b,_g in _plottedM:
    _ms=lib.parse_time(mr.get(_b,{}).get("Metaphase Start (s)","")); _an=lib.parse_time(mr.get(_b,{}).get("Anaphase Onset (s)",""))
    if _ms is not None and _an is not None and _an>_ms: _anacapM.setdefault(_g,[]).append((_an-_ms)/60.0)
_anacapM={_g:float(np.median(_v)) for _g,_v in _anacapM.items() if _v}  # USER 2026-08-10: MEDIAN, not mean
# USER 2026-08-03: "something about how the trendlines are made or data is plotted or somethign isnt correct
# as the trendlines should have a generally negative slope."
# She is right, and the cause is the TREND ESTIMATOR, not the data. The old trend took a BETWEEN-CELL median of
# the raw distance in each 4-min bin. Cells enter metaphase with very different baseline distances and their
# tracks end at different times (33 cells at t=0, 24 by 10 min, 9 by 20 min), so each bin is a median over a
# DIFFERENT set of cells. As low-baseline cells drop out the pooled median climbs even though the individual
# cells are approaching the plate - Simpson's paradox from an unbalanced panel.
# Verified before changing anything: per-cell linear slopes are 19 negative vs 14 positive, median
# -0.042 um/min, i.e. cells DO move plate-ward. (The obvious survivorship story - cells that reach the plate
# stop being tracked - was tested and REJECTED: track duration vs final distance gives Spearman rho=-0.02,
# p=0.9, and cells ending near the plate actually last longer, 20.6 vs 16.7 min.)
# Fix: estimate the trend WITHIN cells. Centre each cell on its own first value, take the median change across
# the cells present in each bin, then re-anchor to the group's mean baseline so the y-axis still reads as an
# absolute distance. The trend then reflects how a kinetochore moves, not which kinetochores remain.
_slopetxt=[]
for g,pp in _bygPm.items():
    a=np.array(sorted(pp))
    if len(a)<5: continue
    _cap=_anacapM.get(g,a[:,0].max())
    _cells={b:np.array(s) for b,s in _cellPm.get(g,{}).items() if len(s)>=2}
    if not _cells: continue
    _base={b:float(S[0,1]) for b,S in _cells.items()}          # each cell's own first post-metaphase distance
    _anchor=float(np.mean(list(_base.values())))
    gx=[];gy=[]
    for lo in np.arange(0,a[:,0].max()+4,4):
        if lo+2>_cap: break
        _d=[float(np.median(S[(S[:,0]>=lo)&(S[:,0]<lo+4),1]))-_base[b]
            for b,S in _cells.items() if ((S[:,0]>=lo)&(S[:,0]<lo+4)).sum()>=1]
        if len(_d)>=3: gx.append(lo+2); gy.append(_anchor+float(np.median(_d)))
    if len(gx)>=2:
        _sx,_sy,_ss=lib.binned_mean_sem(_bygPm3.get(g,[]),nb=max(2,len(gx)),lo=min(gx)-2,hi=max(gx)+2)
        if _sx and any(v>0 for v in _ss):
            axM.fill_between(_sx,[v-e for v,e in zip(_sy,_ss)],[v+e for v,e in zip(_sy,_ss)],
                             color=lib.PALETTE.get(g,"#888"),alpha=.22,lw=0,zorder=4)
        axM.plot(gx,gy,color=lib.PALETTE.get(g,"#888"),lw=3,zorder=5)
    _sl=[float(np.polyfit(S[:,0],S[:,1],1)[0]) for S in _cells.values()
         if len(S)>=5 and S[:,0].max()-S[:,0].min()>2]
    if _sl:
        _slopetxt.append(f"{lib.lbl(g).splitlines()[0]}: median per-cell slope {np.median(_sl):+.3f} µm/min "
                         f"({sum(1 for s in _sl if s<0)}/{len(_sl)} cells negative)")
_xloM,_xhiM=axM.get_xlim()
for g,av in _anacapM.items():
    if _xloM<=av<=_xhiM: axM.axvline(av,color=lib.PALETTE.get(g,"#888"),lw=1.6,ls=(0,(5,2)),alpha=.9,zorder=3)
axM.axvline(0,color="#333",ls=":",lw=.9)
_npdm={}
for r in rowsPm: _npdm.setdefault(b2.get(r[0]),set()).add(r[0])
_hm=[Line2D([0],[0],color=lib.PALETTE.get(g,"#888"),lw=2,label=f"{lib.lbl(g).splitlines()[0]} (N={len(_npdm.get(g,[]))}; bold=trend)") for g in sorted(_bygPm.keys())]
_hm+=[Line2D([0],[0],color="#555",lw=1.6,ls=(0,(5,2)),label="cohort avg anaphase (dashed)")]
axM.legend(handles=_hm,fontsize=7,ncol=2,title="cohort")
axM.set_xlabel("Time since metaphase onset (min; 0 = Metaphase Start)"); axM.set_ylabel("KT distance to metaphase plate (µm)")
axM.set_title(f"KT distance to metaphase plate — from METAPHASE ONSET (O5 companion; N={len(set(r[0] for r in rowsPm))} cells)",loc="left",fontweight="bold",fontsize=10)
figM.text(0.005,-0.02,
          "Bold trend = WITHIN-CELL change: each cell is centred on its own first post-metaphase distance, the\n"
          "median change across the cells present in each 4-min bin is taken, then re-anchored to the cohort's mean\n"
          "baseline, so the axis still reads as an absolute distance. A plain between-cell median per bin rises here\n"
          "purely because the set of tracked cells changes over time (33 cells at t=0, 24 by 10 min, 9 by 20 min),\n"
          "not because kinetochores move away from the plate.\n"
          + "\n".join(_slopetxt),
          fontsize=6.8,color="#444",ha="left",va="top",linespacing=1.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time_metaphase.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_plate_distance_time_metaphase",["batch","t_min_from_meta","plate_dist_um"],rowsPm,
  {"type":"per-cell line","x":"time since Metaphase Start (only points at/after metaphase)","companion_of":"G4_plate_distance_time"},SCRIPT,"KT-to-plate distance from metaphase onset (O5 companion)")
print(f"O5 metaphase-onset companion: {len(set(r[0] for r in rowsPm))} cells -> G4_plate_distance_time_metaphase.png")
# ---- #11c: trendline-SCALED companion (axes fit the trend lines; individual cells may run off-plot) ----
if _trends:
    # USER 2026-08-03: "combine 2,3 sisterless into one group. Use linear trendlines."
    # Applies to THIS trend-scaled companion only; the parent G4_plate_distance_time keeps its own grouping
    # and its binned-median trends.
    _MERGE={"2-Sister":"2/3-Sister","3-Sister":"2/3-Sister"}
    _mg=lambda g:_MERGE.get(g,g)
    _MCOL={"2/3-Sister":lib.PALETTE.get("3-Sister","#8c564b")}
    _gcol=lambda g:_MCOL.get(g) or lib.PALETTE.get(g,"#888")
    _cell=defaultdict(list)
    for r in rowsP: _cell[r[0]].append((r[1],r[2]))
    figT,axT=plt.subplots(figsize=(9,5.2))
    for b,ser in _cell.items():
        g=_mg(b2.get(b)); ser=sorted(ser)
        if len(ser)>=2: lib.cell_line(axT,[s[0] for s in ser],[s[1] for s in ser],_gcol(g),alpha=.35,lw=1.0,zorder=1)
    # LINEAR fit per merged group, capped at that group's average anaphase like the binned trends were
    _gpts=defaultdict(list); _gcells=defaultdict(set)
    for r in rowsP:
        g=_mg(b2.get(r[0]) or "?")
        _gpts[g].append((r[1],r[2])); _gcells[g].add(r[0])
    _tx=[];_ty=[];_hT=[]
    for g in sorted(_gpts):
        _caps=[_anacap[k] for k in (_MERGE if g=="2/3-Sister" else [g]) if k in _anacap] if g=="2/3-Sister" \
              else ([_anacap[g]] if g in _anacap else [])
        P=np.array(sorted(_gpts[g]))
        if _caps: P=P[P[:,0]<=float(np.median(_caps))]  # USER 2026-08-10: MEDIAN, not mean
        if len(P)<5 or P[:,0].max()-P[:,0].min()<1e-9: continue
        m,c0=np.polyfit(P[:,0],P[:,1],1)
        gx=np.linspace(P[:,0].min(),P[:,0].max(),60); gy=m*gx+c0
        axT.plot(gx,gy,color=_gcol(g),lw=3,zorder=5)
        _tx+=list(gx); _ty+=list(gy)
        _hT.append(Line2D([0],[0],color=_gcol(g),lw=3,
                          label=f"{g} — linear fit, slope {m:+.3f} µm/min (N={len(P)} pts, {len(_gcells[g])} cells)"))
    if _tx:
        _mx=(max(_tx)-min(_tx))*0.05+1; _my=(max(_ty)-min(_ty))*0.12+0.5
        axT.set_xlim(min(_tx)-_mx,max(_tx)+_mx); axT.set_ylim(min(_ty)-_my,max(_ty)+_my)
    axT.set_xlabel("Time (min)"); axT.set_ylabel("KT distance to metaphase plate (µm)")
    axT.legend(handles=_hT,fontsize=7,ncol=1,title="cohort (2- and 3-sisterless combined)")
    axT.set_title("KT distance to metaphase plate — TREND-SCALED (linear fits; 2- and 3-sisterless combined; individual cells may run off-plot)",loc="left",fontweight="bold",fontsize=9.2)
    plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time_trendscaled.png",bbox_inches="tight"); plt.close()
    # trend-scaled companion replots the SAME per-cell data (rowsP) with axes fit to the trends -> identical data CSV
    lib.record_plot("G4_plate_distance_time_trendscaled",["batch","t_min","plate_dist_um"],rowsP,
      {"type":"per-cell line, TREND-SCALED (axes fit trend lines)","source":"KT track vs meta_plate polyline (perp distance)",
       "x":"time from MOVIE START (raw t_sec/60)","companion_of":"G4_plate_distance_time"},SCRIPT,"KT-to-plate distance over time (trend-scaled)")
    print("plate-distance trend-scaled companion -> G4_plate_distance_time_trendscaled.png")

# ---- ITEM 5b: ROUNDNESS iteration of the plate-distance plot ----
# Companion that incorporates CELL ROUNDNESS: for every KT timepoint we look up the cell's outline nearest
# in time (cell_outlines.csv) and compute its circularity (4πA/perimeter², 1.0 = perfect circle), then
# colour each point by that roundness. This shows whether polar-KT distance-to-plate co-varies with how
# round vs deformed the cell is at that moment. (No master roundness column exists, so we compute it from
# the drawn cell-outline polygons.)
_outl=defaultdict(list)   # batch -> [(t_min, circularity)]
try:
    _orows=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); _oi={c:i for i,c in enumerate(_orows[0])}
    for _r in _orows[1:]:
        try:
            _p=np.array(json.loads(_r[_oi['points']]),float)
            if len(_p)<3: continue
            _x=_p[:,0]; _y=_p[:,1]
            _A=0.5*abs(np.dot(_x,np.roll(_y,-1))-np.dot(_y,np.roll(_x,-1)))
            _per=float(np.sum(np.hypot(np.diff(_x,append=_x[0]),np.diff(_y,append=_y[0]))))
            if _per<=0: continue
            _circ=min(1.0,4*np.pi*_A/(_per*_per))
            _outl[_r[_oi['batch']].strip()].append((float(_r[_oi['t_sec']])/60.0,_circ))
        except Exception: pass
except Exception: pass
# USER 2026-07-16: cell shape trends differ AFTER anaphase, so these roundness plots must NOT use outlines with
# t > Anaphase Onset. This is an IN-MEMORY filter only — cell_outlines.csv is untouched (post-anaphase outlines are
# preserved for other plots). Where outlines bracket anaphase, INTERPOLATE a roundness value exactly AT anaphase so
# the trajectory reaches anaphase onset instead of stopping at the last pre-anaphase outline.
def _ana_b(b):
    v=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    return v/60.0 if v is not None else None
for _b in list(_outl):
    _a=_ana_b(_b)
    if _a is None: continue                                   # no anaphase recorded -> keep all (nothing to clip to)
    _o=sorted(_outl[_b])
    _pre=[(t,c) for t,c in _o if t<=_a+1e-6]
    _post=[(t,c) for t,c in _o if t>_a+1e-6]
    if _pre and _post and _pre[-1][0] < _a-1e-6:              # bracket anaphase -> interpolate roundness AT anaphase
        (t0,c0),(t1,c1)=_pre[-1],_post[0]
        _pre.append((_a, c0+(c1-c0)*(_a-t0)/(t1-t0)))
    _outl[_b]=_pre                                            # outlines clipped at anaphase (+ the anaphase point)
def _round_at(b,tmin):
    # 2026-07-11 (user): roundness looked "binned" — snapping each KT timepoint to the NEAREST outline made every
    # point near one outline inherit that single roundness value (vertical stripes). Cells only have a few hand-
    # drawn outlines, so INTERPOLATE roundness linearly between outline times -> a continuous per-timepoint value
    # (the cell's shape genuinely changes smoothly between outlines). np.interp clamps outside the outline range.
    _a=_ana_b(b)
    if _a is not None and tmin>_a+1e-6: return None            # no roundness past anaphase onset (USER 2026-07-16)
    o=_outl.get(b)
    if not o: return None
    if len(o)==1: return o[0][1]
    o=sorted(o)
    return float(np.interp(tmin,[p[0] for p in o],[p[1] for p in o]))
_RX=[];_RY=[];_RC=[];_RB=[]
for r in rowsP:
    _c=_round_at(r[0],r[1])
    # record the BATCH alongside the point (2026-07-29). Without it these two companions could not be
    # windowed to a per-cell mitotic interval - there was no key to look up that cell's metaphase and
    # anaphase onset - so make_window_companions rejected both for "needs a time and a batch column".
    if _c is not None: _RX.append(r[1]); _RY.append(r[2]); _RC.append(_c); _RB.append(r[0])
figR,axR=plt.subplots(figsize=(9,5.2))
# faint per-cell connecting lines for context
_cellR=defaultdict(list)
for r in rowsP: _cellR[r[0]].append((r[1],r[2]))
for b,ser in _cellR.items():
    ser=sorted(ser)
    if len(ser)>=2: axR.plot([s[0] for s in ser],[s[1] for s in ser],color="#cccccc",alpha=.6,lw=.8,zorder=1)
if _RX:
    _sc=axR.scatter(_RX,_RY,c=_RC,cmap="viridis",vmin=min(_RC),vmax=max(_RC),s=22,alpha=.85,edgecolor="none",zorder=3)
    _cb=figR.colorbar(_sc,ax=axR); _cb.set_label("cell roundness (circularity: 4πA/P², 1=circle)")
axR.set_xlabel("Time (min)"); axR.set_ylabel("KT distance to metaphase plate (µm)")
axR.set_title(f"KT distance to metaphase plate over time — colored by CELL ROUNDNESS ({len(set(b for b in _cellR if _outl.get(b)))} cells with outlines)",loc="left",fontweight="bold",fontsize=9.8)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_plate_distance_time_roundness.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_plate_distance_time_roundness",["batch","t_min","plate_dist_um","cell_roundness"],[[bb,round(a,2),round(b,3),round(c,4)] for bb,a,b,c in zip(_RB,_RX,_RY,_RC)],
  {"type":"per-point scatter colored by roundness","roundness":"circularity 4πA/P² from cell_outlines.csv polygon nearest in time","companion_of":"G4_plate_distance_time"},SCRIPT,"KT-to-plate distance over time, colored by cell roundness")
print(f"roundness companion: {len(_RX)} KT points with a matched cell outline -> G4_plate_distance_time_roundness.png")
# ---- O6: alternative (non-line) visualization — distance vs roundness directly (x=roundness, y=distance,
# colored by time). Avoids the hard-to-follow per-cell line tracing the user flagged. ----
figR2,axR2=plt.subplots(figsize=(7,5))
if _RX:
    _sc2=axR2.scatter(_RC,_RY,c=_RX,cmap="plasma",s=22,alpha=.8,edgecolor="none")
    _cb2=figR2.colorbar(_sc2,ax=axR2); _cb2.set_label("time (min, from movie start)")
    if len(_RC)>=5 and np.ptp(_RC)>0:
        _m2,_b2=np.polyfit(_RC,_RY,1); _xr2=np.linspace(min(_RC),max(_RC),20)
        axR2.plot(_xr2,_m2*_xr2+_b2,"--",color="#333",lw=1.6,label=f"trend (slope {_m2:.1f} µm per unit roundness)"); axR2.legend(fontsize=8)
axR2.set_xlabel("Cell roundness (circularity 4πA/P², 1=circle)"); axR2.set_ylabel("KT distance to metaphase plate (µm)")
axR2.set_title("KT-to-plate distance vs cell roundness (O6 alt view; colored by time — not a per-cell line)",loc="left",fontweight="bold",fontsize=9.8)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_distance_vs_roundness.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_distance_vs_roundness",["batch","cell_roundness","plate_dist_um","t_min"],[[bb,round(c,4),round(y,3),round(x,2)] for bb,x,y,c in zip(_RB,_RX,_RY,_RC)],
  {"type":"scatter x=roundness y=distance color=time","companion_of":"G4_plate_distance_time_roundness"},SCRIPT,"KT-to-plate distance vs roundness (O6 alt viz)")
print(f"O6 distance-vs-roundness alt viz: {len(_RX)} pts -> G4_distance_vs_roundness.png")

# audio S55: exclude the ~80 µm/min velocity outlier the user flagged (tracking glitch wrecking the scale)
for g,v in vel:
    if abs(v)>40: lib.log_review("velocity_outlier_excluded","movement",f"{v:.1f} um/min","~80 µm/min velocity outlier EXCLUDED per audio S55")
vel=[(g,v) for g,v in vel if abs(v)<=40]
_velv=[v for g,v in vel]
# ITEM 4: this pools MULTIPLE ablation groups -> code the histogram by cohort (stacked, colored).
_velgs=sorted(set(g for g,_ in vel),key=lambda g:(g is None,g))
fig,ax=plt.subplots(figsize=(6.8,4.6))
if vel:
    _bins=np.linspace(min(_velv),max(_velv),25)
    ax.hist([[v for gg,v in vel if gg==g] for g in _velgs],bins=_bins,stacked=True,
            color=[lib.PALETTE.get(g,"#888") for g in _velgs],label=[f"{lib.lbl(g).splitlines()[0]} (N={sum(1 for gg,_ in vel if gg==g)})" for g in _velgs],alpha=.9)
ax.axvline(np.median(_velv),color="#b30000",ls="--",lw=1.5,label=f"median {np.median(_velv):.2f} µm/min")
ax.axvline(0,color="#333",lw=.8,ls=":")
ax.set_xlabel("Velocity relative to plate (µm/min)\n+ = away from plate / toward pole   ·   − = toward plate"); ax.set_ylabel("count")
ax.legend(fontsize=7.5,title="ablation group")
ax.set_title(f"Polar/sisterless-KT velocity relative to metaphase plate, by ablation group (N={len(_velv)} steps)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_velocity.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_velocity",["cohort","velocity_um_per_min"],[[g,round(v,4)] for g,v in vel],
  {"type":"stacked histogram by cohort","source":"d(plate distance)/dt","sign":"+ = away from plate (toward pole), − = toward plate"},SCRIPT,"KT velocity relative to plate, by ablation group")
# velocity vs distance-from-plate (slide 63 request)
vd=[(d,v) for d,v in vd if abs(v)<=40]
fig,ax=plt.subplots(figsize=(7,5))
if vd:
    _d=[p[0] for p in vd]; _v=[p[1] for p in vd]
    ax.scatter(_d,_v,s=14,color="#2166ac",alpha=.5,edgecolor="none")
    ax.axhline(0,color="#999",lw=.8,ls=":")
    if len(_d)>=5:
        _m,_b=np.polyfit(_d,_v,1); _xr=np.linspace(min(_d),max(_d),20); ax.plot(_xr,_m*_xr+_b,"--",color="#b30000",lw=1.6,label=f"trend (slope {_m:.2f})"); ax.legend(fontsize=8)
# ITEM 10: sign convention — v = d(distance-to-plate)/dt, so POSITIVE = distance increasing = moving AWAY
# from the plate (toward the pole); NEGATIVE = moving back toward the plate.
ax.set_xlabel("Distance to metaphase plate (µm)"); ax.set_ylabel("Velocity vs plate (µm/min; + = toward pole, − = toward plate)")
ax.set_title(f"Polar/sisterless-KT velocity vs distance from plate (N={len(vd)} steps)",loc="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_velocity_vs_distance.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_velocity_vs_distance",["dist_um","velocity_um_per_min"],[[round(d,3),round(v,4)] for d,v in vd],
  {"type":"scatter+trend","x":"distance to plate","y":"signed velocity"},SCRIPT,"KT velocity vs distance from plate")

# ===== 2026-07-11 (user): (A) also plot the PAIRED (plate-resident sister) KT velocity for comparison, and
# (B) a version with velocity on X and TIME UNTIL ANAPHASE ONSET on Y. Same signed metric as G4_velocity:
# v = d(distance-to-plate)/dt (µm/min), + = away from plate/toward pole. Paired KTs sit ON the plate so their
# velocity relative to it should cluster near 0 — the comparison baseline for the moving polar/sisterless KTs.
def _vel_steps(b, track):
    """[(midtime_sec, signed velocity µm/min)] from a KT track's distance-to-(metaphase)plate over time."""
    ser=[]
    for f,t,x,y in sorted(track):
        pl=plate_at(b,f)
        if pl is None: continue
        ser.append((t, pt_poly((x,y),pl)*ps(b)))
    ser=sorted(ser); out=[]
    for (t0,d0),(t1,d1) in zip(ser,ser[1:]):
        if t1>t0: out.append(((t0+t1)/2.0,(d1-d0)/((t1-t0)/60.0)))
    return out
VEL_CAP=40.0   # same S55 glitch cap as G4_velocity (the ~80 µm/min tracking outlier is a glitch, excluded)
_velrich=[]    # (kind, cohort, velocity, midtime_sec, batch)
for b in usable:
    if b not in plates or b in OSC_EXCLUDE_BATCHES or b2.get(b) is None: continue
    g=b2[b]
    for _kt in lib.link_kt_tracks(sister(b),ps(b)):      # KT IDENTITY: velocity is per kinetochore
        for mt,v in _vel_steps(b, _kt):
            if abs(v)<=VEL_CAP: _velrich.append(("polar",g,v,mt,b))
    for mt,v in _vel_steps(b, trk[b].get('paired_kt',[])):
        if abs(v)<=VEL_CAP: _velrich.append(("paired",g,v,mt,b))
_pol=[r for r in _velrich if r[0]=="polar"]; _pair=[r for r in _velrich if r[0]=="paired"]
# (A) polar vs paired velocity distributions overlaid
figV,axV=plt.subplots(figsize=(7.6,5)); _vb=np.linspace(-VEL_CAP,VEL_CAP,41)
if _pol: axV.hist([r[2] for r in _pol],bins=_vb,color="#2166ac",alpha=.6,label=f"polar/sisterless KT (N={len(_pol)})")
if _pair: axV.hist([r[2] for r in _pair],bins=_vb,color="#d95f02",alpha=.6,label=f"paired KT on plate (N={len(_pair)})")
axV.axvline(0,color="#999",lw=.8,ls=":")
# ITEM 2 (2026-08-03, her M2-04 "mean/median of both groups"): the overlaid histograms carried the median in
# the legend text only, and no mean at all, and nothing marked ON the plot. Add explicit vlines for BOTH mean
# and median, BOTH groups (solid = median, dashed = mean, per-group color matches the histogram color).
# NOTE: an earlier version of this fix put each value as rotated text right next to its own vline -- but
# polar's mean/median (-0.31 / -0.03) and paired's mean/median (-5.67 / -5.81) each sit within a fraction of
# a µm/min of one another on an 80-unit-wide axis, so the two rotated labels physically overlapped. Fixed by
# reporting the numbers ONCE each, in a static stats box (upper left, out of the histogram's own data), same
# convention as kt_stats boxes elsewhere in the deck -- the vlines still mark the exact locations on-plot.
_stat_lines=[]
for _rr,_col,_lab in [(_pol,"#2166ac","polar/sisterless"),(_pair,"#d95f02","paired (plate)")]:
    if not _rr: continue
    _vv=[r[2] for r in _rr]; _med=float(np.median(_vv)); _mean=float(np.mean(_vv))
    axV.axvline(_med,color=_col,lw=2.0,ls="-",zorder=5)
    axV.axvline(_mean,color=_col,lw=1.6,ls="--",zorder=5)
    _stat_lines.append(f"{_lab}: mean {_mean:+.2f}  median {_med:+.2f}")
axV.text(.02,.98,"\n".join(_stat_lines),transform=axV.transAxes,ha="left",va="top",fontsize=7.6,
         family="monospace",bbox=dict(boxstyle="round,pad=0.3",fc="white",ec="#bbb",alpha=0.9),zorder=10)
axV.set_xlabel("Velocity relative to plate (µm/min)\n+ = away from plate / toward pole   ·   − = toward plate")
axV.set_ylabel("count")
_leg_handles=list(axV.get_legend_handles_labels()[0])
_leg_handles+=[Line2D([0],[0],color="#444",lw=2.0,ls="-",label="median"),
               Line2D([0],[0],color="#444",lw=1.6,ls="--",label="mean")]
axV.legend(handles=_leg_handles,fontsize=8,loc="upper right")
axV.set_title(f"KT velocity relative to plate — polar/sisterless vs paired (plate) KT ({len(set(r[4] for r in _velrich))} cells)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_velocity_paired_comparison.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_velocity_paired_comparison",["kind","cohort","velocity_um_per_min","t_sec","batch"],
  [[k,g,round(v,4),round(mt,1),b] for (k,g,v,mt,b) in _velrich],
  {"type":"overlaid histograms polar vs paired","sign":"+ = away from plate","cap":"|v|<=40 (S55 glitch cap)"},SCRIPT,
  "Polar/sisterless vs paired (plate) KT velocity relative to plate")
# (B) velocity (x) vs time UNTIL anaphase onset (y)
figT,axT=plt.subplots(figsize=(7.6,5.8)); _rowsT=[]
for kind,col,mrk,lab in [("polar","#2166ac","o","polar/sisterless"),("paired","#d95f02","s","paired (plate)")]:
    xs=[];ys=[]
    for (k,g,v,mt,b) in _velrich:
        if k!=kind: continue
        at=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
        if at is None: continue
        xs.append(v); ys.append((at-mt)/60.0); _rowsT.append([kind,b,round(v,4),round((at-mt)/60.0,3)])
    if xs: axT.scatter(xs,ys,s=16,color=col,alpha=.55,edgecolor="none",marker=mrk,label=f"{lab} KT (N={len(xs)})")
axT.axvline(0,color="#999",lw=.8,ls=":"); axT.axhline(0,color="#b30000",lw=1.0,ls="--")
axT.text(axT.get_xlim()[1],0," anaphase onset",fontsize=7,color="#b30000",va="bottom",ha="right")
axT.set_xlabel("Velocity relative to plate (µm/min;  + = away from plate,  − = toward plate)")
axT.set_ylabel("Time until anaphase onset (min;  + = before anaphase)"); axT.legend(fontsize=8)
axT.set_title(f"KT velocity vs time until anaphase onset — polar vs paired (N={len(_rowsT)} steps)",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_velocity_vs_time_to_anaphase.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_velocity_vs_time_to_anaphase",["kind","batch","velocity_um_per_min","min_until_anaphase"],_rowsT,
  {"type":"scatter velocity vs time-until-anaphase","y":"anaphase_onset - step_time (min)","sign":"+ before anaphase / away from plate"},SCRIPT,
  "KT velocity vs time until anaphase onset (polar vs paired)")
print(f"velocity paired-comparison: polar {len(_pol)} steps / paired {len(_pair)} steps; time-to-anaphase {len(_rowsT)} rows")

# ---------- 4. KT intensity over time (fluor at KT position) — 16-bit cropped TIF ----------
# s64: t=0 = each cell's FIRST ABLATION (offset every line by its own first-ablation time); cap the trend
# line where the sample count drops off; flag any series extending past 80 min for review.
fig,ax=plt.subplots(figsize=(9,5)); rowsI=[]; R=int(__import__("os").environ.get("KT_R","9"))   # standard r=9
_no_abl=[]; ctrl_rows=[]; _ctrl_labeled=False; _ctrl_cells=set(); _DIFF=[]   # _DIFF: O3 same-frame (polar − paired plate) intensity
def _kt_val(g,x,y,cb):                                        # snapped KT disk Σ minus marked cytosol disk (same method as polar)
    cval=lib.disk_sum(g,cb[2],cb[3],R)
    if cval is None: return None
    sx,sy=lib.snap_to_peak(g,x,y)
    if lib.is_saturated(g,sx,sy,R) or lib.is_saturated(g,cb[2],cb[3],R): return None
    return max(0.0,lib.disk_sum(g,sx,sy,R)-cval)
for b in usable:
    tr=sister(b)
    fa=first_abl(b)
    if fa is None:                                           # cannot place on a first-ablation t=0 axis
        _no_abl.append(b);
        lib.log_review("kt_intensity_no_first_abl",b,"","no 'First Ablation (s)' in master — excluded from t=0(first-ablation) intensity plot"); continue
    ft=lib.FluorTif(b,'monitoring')                          # 16-bit cropped fluor TIF (validated vs MP4)
    if not ft.ok(): continue
    series=[]; _polf={}; _ctrlf={}                            # O3: per-FRAME values for the same-frame diff plot
    for f,t,x,y in tr:
        g=ft.plane_by_frame(f)                                   # map by FRAME (ground-truth), not t_sec (shifted)
        if g is None: continue
        cb=cyto_at(b,f,t)                                     # O3: same-frame cytosol_bg preferred, else nearest-in-time
        if cb is None: continue
        val=_kt_val(g,x,y,cb)                                 # bg-subtracted, snapped, saturation-guarded
        if val is None: continue
        tm=(t-fa)/60.0                                        # minutes since this cell's first ablation
        series.append((tm,val)); rowsI.append([b,round(tm,2),round(val,1)]); _polf[f]=(tm,val)
    # paired control (plate/sister) KT — same cell, same movie, same method — as a per-cell comparison trace
    cseries=[]
    for f,t,x,y in sorted(trk[b].get('paired_kt',[])):
        g=ft.plane_by_frame(f)
        if g is None: continue
        cb=cyto_at(b,f,t)
        if cb is None: continue
        val=_kt_val(g,x,y,cb)
        if val is None: continue
        tm=(t-fa)/60.0; cseries.append((tm,val)); ctrl_rows.append([b,round(tm,2),round(val,1)]); _ctrlf[f]=(tm,val)
    # O3 diff plot data: per SAME frame, polar minus paired-plate intensity (only frames present in both)
    for f in set(_polf)&set(_ctrlf):
        _tm,_pv=_polf[f]; _cv=_ctrlf[f][1]; _DIFF.append((b,_tm,_pv-_cv))
    ft.close()
    series=sorted(series); cseries=sorted(cseries)
    if series and series[-1][0]>80:                          # s64: check the >80 min sample
        lib.log_review("kt_intensity_over_80min",b,f"{series[-1][0]:.0f} min","KT-intensity series extends past 80 min after first ablation — verify")
    if len(series)>=2: ax.plot([s[0] for s in series],[s[1] for s in series],color=lib.PALETTE.get(b2.get(b),"#888"),alpha=.7,lw=1.2,marker="o",ms=2.5)
    if len(cseries)>=2:                                       # control trace: teal dashed square, distinct from polar
        _ctrl_cells.add(b)
        ax.plot([s[0] for s in cseries],[s[1] for s in cseries],color="#00838f",alpha=.85,lw=1.4,ls=(0,(4,2)),marker="s",ms=2.8,
                label=("paired control KT (plate/sister, same cell)" if not _ctrl_labeled else None),zorder=6)
        _ctrl_labeled=True
bygI=defaultdict(list); _ncell=defaultdict(set)
for _b,_t,_f in [(r[0],r[1],r[2]) for r in rowsI]: bygI[b2.get(_b)].append((_t,_f,_b)); _ncell[b2.get(_b)].add(_b)
# #11b: per-group avg anaphase time referenced to first ablation (this plot's t=0) -> cap the trend
_ktcap={}
for _b in set(r[0] for r in rowsI):
    _fa=first_abl(_b); _an=lib.parse_time(mr.get(_b,{}).get("Anaphase Onset (s)",""))
    if _fa is not None and _an is not None: _ktcap.setdefault(b2.get(_b),[]).append((_an-_fa)/60.0)
_ktcap={_g:float(np.median(_v)) for _g,_v in _ktcap.items() if _v}  # USER 2026-08-10: MEDIAN, not mean
for _g,_pts in bygI.items():
    if _g is None: continue
    _a=sorted(_pts)
    if len(_a)<5: continue
    _ts=np.array([p[0] for p in _a]); _vs=np.array([p[1] for p in _a])
    _bins=np.linspace(_ts.min(),_ts.max(),8); _idx=np.digitize(_ts,_bins); _bx=[];_by=[]
    for _k in range(1,len(_bins)+1):
        _m=_idx==_k
        _ncb=len({_a[j][2] for j in np.where(_m)[0]})         # distinct cells contributing to this bin
        if _m.sum()>=3 and _ncb>=2: _bx.append(_ts[_m].mean()); _by.append(_vs[_m].mean())   # cap: need >=2 cells
    _cap=_ktcap.get(_g)
    if _cap is not None:                                       # #11b: stop trend at group's avg anaphase
        _kp=[i for i in range(len(_bx)) if _bx[i]<=_cap]; _bx=[_bx[i] for i in _kp]; _by=[_by[i] for i in _kp]
    if len(_bx)>=2: ax.plot(_bx,_by,color=lib.PALETTE.get(_g,"#888"),lw=3,zorder=5,label=f"{lib.lbl(_g).splitlines()[0]} (avg, N={len(_ncell[_g])})")   # S56: N per group
# ITEM 2: unassigned-cohort cells are no longer plotted (dropped up-front, logged to review) — no gray legend line.
ax.axvline(0,color="#333",ls=":",lw=.9)
ax.legend(fontsize=7,ncol=2)
ax.set_xlabel("Time since first ablation (min; t=0 = first ablation)"); ax.set_ylabel(f"Polar/sisterless-KT eYFP intensity (Σ r={R} disk, bg-subtracted)")
ax.set_title(f"Polar/sisterless-kinetochore eYFP intensity vs time since first ablation (N={len(set(r[0] for r in rowsI))} cells; trend capped to ≥2 cells/bin)\nteal dashed = paired control (plate/sister) KT in the same cell — available for {len(_ctrl_cells)} cell(s)",loc="left",fontweight="bold",fontsize=9.2)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_time.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_kt_intensity_time",["batch","t_min_since_first_abl","kt_fluor_au"],rowsI,
  {"type":"per-cell line","source":f"16-bit _Fluor_Cropped.tif Σ in r={R} disk at snapped KT minus marked cytosol","time":"t=0 = first ablation (per-cell offset)","trend":"binned mean, capped to ≥2 cells/bin & avg anaphase"},SCRIPT,"Polar/sisterless-KT intensity vs time since first ablation")

# ---- #11c: trendline-SCALED companion (axes fit the capped per-group trends; individual cells may run off-plot) ----
_ktrend={}
for _g,_pts in bygI.items():
    if _g is None: continue
    _a=sorted(_pts)
    if len(_a)<5: continue
    _ts=np.array([p[0] for p in _a]); _vs=np.array([p[1] for p in _a])
    _bins=np.linspace(_ts.min(),_ts.max(),8); _idx=np.digitize(_ts,_bins); _bx=[];_by=[]
    for _k in range(1,len(_bins)+1):
        _m=_idx==_k; _ncb=len({_a[j][2] for j in np.where(_m)[0]})
        if _m.sum()>=3 and _ncb>=2: _bx.append(_ts[_m].mean()); _by.append(_vs[_m].mean())
    _cap=_ktcap.get(_g)
    if _cap is not None: _kp=[i for i in range(len(_bx)) if _bx[i]<=_cap]; _bx=[_bx[i] for i in _kp]; _by=[_by[i] for i in _kp]
    if len(_bx)>=2: _ktrend[_g]=(_bx,_by)
if _ktrend:
    figT,axT=plt.subplots(figsize=(9,5)); _cellI=defaultdict(list)
    for r in rowsI: _cellI[r[0]].append((r[1],r[2]))
    for _b,ser in _cellI.items():
        ser=sorted(ser)
        if len(ser)>=2: axT.plot([s[0] for s in ser],[s[1] for s in ser],color=lib.PALETTE.get(b2.get(_b),"#888"),alpha=.35,lw=1.0,zorder=1)
    _tx=[];_ty=[]
    for _g,(bx,by) in _ktrend.items():
        axT.plot(bx,by,color=lib.PALETTE.get(_g,"#888"),lw=3,zorder=5); _tx+=bx; _ty+=by
    if _tx:
        _mx=(max(_tx)-min(_tx))*0.06+1; _my=(max(_ty)-min(_ty))*0.12+1
        axT.set_xlim(min(_tx)-_mx,max(_tx)+_mx); axT.set_ylim(min(_ty)-_my,max(_ty)+_my)
    axT.axvline(0,color="#333",ls=":",lw=.9); axT.set_xlabel("Time since first ablation (min)"); axT.set_ylabel(f"Polar/sisterless-KT eYFP intensity (Σ r={R} disk, bg-subtracted)")
    axT.set_title("KT eYFP intensity vs time — TREND-SCALED (axes fit trend lines; individual cells may run off-plot)",loc="left",fontweight="bold",fontsize=9.5)
    plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_time_trendscaled.png",bbox_inches="tight"); plt.close()
    # trend-scaled companion replots the SAME per-cell data (rowsI) with axes fit to the trends -> identical data CSV
    lib.record_plot("G4_kt_intensity_time_trendscaled",["batch","t_min_since_first_abl","kt_fluor_au"],rowsI,
      {"type":"per-cell line, TREND-SCALED (axes fit trend lines)","source":f"16-bit _Fluor_Cropped.tif Σ in r={R} disk at snapped KT minus marked cytosol",
       "time":"t=0 = first ablation (per-cell offset)","companion_of":"G4_kt_intensity_time"},SCRIPT,"Polar/sisterless-KT intensity vs time (trend-scaled)")
    print("kt-intensity trend-scaled companion -> G4_kt_intensity_time_trendscaled.png")

# ---------- 4b. KT intensity over time, PER-CELL normalized to t=0 (companion) ----------
# Companion to G4_kt_intensity_time: each cell's KT intensity divided by its OWN value at t=0 (first
# ablation; the sample nearest t=0), so every cell STARTS at 1.0 and the recovery shapes are directly
# comparable across cells (unlike a global min-max rescale, which is just a linear relabel of the a.u. axis).
_bycell=defaultdict(list)
for _b,_t,_v in [(r[0],r[1],r[2]) for r in rowsI]: _bycell[_b].append((_t,_v))
fig,ax=plt.subplots(figsize=(9,5)); rowsIs=[]; _norm={}
for _b,series in _bycell.items():
    series=sorted(series)
    base=min(series,key=lambda s:abs(s[0]))[1]              # value at the sample nearest t=0 (first ablation)
    if base is None or base==0 or not np.isfinite(base): continue   # can't normalize to a zero/invalid baseline
    _norm[_b]=base
    if len(series)>=2: ax.plot([s[0] for s in series],[s[1]/base for s in series],color=lib.PALETTE.get(b2.get(_b),"#888"),alpha=.7,lw=1.2,marker="o",ms=2.5)
_bygS=defaultdict(list); _ncellS=defaultdict(set)
for r in rowsI:
    if r[0] not in _norm: continue
    _q=r[2]/_norm[r[0]]
    _bygS[b2.get(r[0])].append((r[1],_q,r[0])); _ncellS[b2.get(r[0])].add(r[0]); rowsIs.append([r[0],round(r[1],2),round(_q,4)])
for _g,_pts in _bygS.items():
    if _g is None: continue
    _a=sorted(_pts)
    if len(_a)<5: continue
    _ts=np.array([p[0] for p in _a]); _vs=np.array([p[1] for p in _a])
    _bins=np.linspace(_ts.min(),_ts.max(),8); _idx=np.digitize(_ts,_bins); _bx=[];_by=[]
    for _k in range(1,len(_bins)+1):
        _m=_idx==_k
        _ncb=len({_a[j][2] for j in np.where(_m)[0]})
        if _m.sum()>=3 and _ncb>=2: _bx.append(_ts[_m].mean()); _by.append(_vs[_m].mean())
    _cap=_ktcap.get(_g)                                        # #11b: cap t=0-normalized trend at avg anaphase too
    if _cap is not None:
        _kp=[i for i in range(len(_bx)) if _bx[i]<=_cap]; _bx=[_bx[i] for i in _kp]; _by=[_by[i] for i in _kp]
    if len(_bx)>=2: ax.plot(_bx,_by,color=lib.PALETTE.get(_g,"#888"),lw=3,zorder=5,label=f"{lib.lbl(_g).splitlines()[0]} (avg, N={len(_ncellS[_g])})")
ax.axhline(1,color="#999",ls="--",lw=1,zorder=1); ax.axvline(0,color="#333",ls=":",lw=.9); ax.legend(fontsize=7,ncol=2,loc="upper right")
ax.set_xlabel("Time since first ablation (min; t=0 = first ablation)"); ax.set_ylabel("Polar/sisterless-KT eYFP intensity (normalized to t=0)")
ax.set_title("Polar/sisterless-KT eYFP intensity vs time since first ablation — per-cell normalized to t=0 (companion)",loc="left",fontweight="bold",fontsize=9.5)
# ITEM 3: on-figure explanation of what "normalized to t=0" means and its relation to background.
_para=('"Normalized to t=0" (per cell): each cell\'s KT intensity is DIVIDED by its own value at t=0 (the\n'
       'sample nearest its first ablation), so every cell starts at 1.0 and the curves show FRACTIONAL change\n'
       '(fold-change) over time — this removes cell-to-cell differences in absolute brightness so recovery\n'
       'SHAPES are comparable. It is a ratio, NOT the same as background subtraction: the underlying values\n'
       'are ALREADY background-subtracted first (KT disk Σ minus the marked cytosol disk in the same frame);\n'
       'this step then rescales those bg-subtracted values relative to each cell\'s starting level.')
ax.text(0.0,-0.16,_para,transform=ax.transAxes,fontsize=6.3,va="top",ha="left",   # moved BELOW the axes so it no longer sits on the data
        bbox=dict(boxstyle="round,pad=0.4",fc="#f7f7f7",ec="#bbbbbb",alpha=.92),zorder=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_time_scaled01.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_kt_intensity_time_scaled01",["batch","t_min_since_first_abl","kt_fluor_norm_t0"],rowsIs,
  {"type":"per-cell line + per-group binned mean, PER-CELL NORMALIZED to t=0","companion_of":"G4_kt_intensity_time",
   "scaling":"each cell divided by its own value at the sample nearest t=0 (first ablation) -> every cell starts at 1"},SCRIPT,
  "Polar/sisterless-KT intensity vs time since first ablation, per-cell normalized to t=0 (companion)")
print(f"KT-intensity per-cell-t0 companion: {len(_norm)} cells -> G4_kt_intensity_time_scaled01.png")
# ---------- 4c. KT eYFP intensity DIFFERENCE — MANUAL polar vs MANUAL paired-PLATE reference ----------
# REWORK (2026-07-07): the OLD version needed a manual same-frame 'paired_kt' mark, which exists for only ~1
# cell — so the old plot spanned ~1 cell. NEW version borrows the plate reference KT from the manual paired outlines (the same
# plate-control selection as group4_tracking_dist / the oscillation plate group) but MEASURES IT IDENTICALLY
# to the manual polar KT, so both KTs are measured OUR disk way and the comparison is measurement-consistent:
#   Polar  KT: manual polar/sisterless mark -> snap to punctum, Σ r=9 disk on the 16-bit fluor TIF, minus the
#              SAME-frame cytosol_bg disk (nearest cytosol_bg mark), floored at 0  [== _kt_val()].
#   Plate  KT: on the SAME polar frame, take the manual paired-KT outline centroid NEAREST IN TIME (a KT sitting at
#              the metaphase plate); measure it the IDENTICAL way on the SAME plane with the SAME cytosol_bg.
#              The plate KT need NOT be the same KT frame-to-frame — any plate spot near that time is a valid
#              plate reference. Then per polar frame record polar, plate, and polar − plate.
# Covers the cells that have BOTH manual polar marks AND manual paired plate outlines, with the SAME exclusions as the
# other Group-4 time-series: lib.excluded/REVIEW_EXCLUDE, the ~95-min LONG_SAMPLE, AND unassigned-cohort
# cells (standing rule 2026-07-08: don't plot the unassigned cohort — flag them instead).
def _plate_spots_for(b):
    """Selected plate-control KT spots [(t_sec,x_px,y_px)] for a batch: the fullest MANUAL paired-KT outline
    runs between metaphase and anaphase that stay closest to the drawn meta_plate line (identical selection
    to the oscillation plate group / group4_tracking_dist). These are the KTs sitting AT the metaphase
    plate. Source is kt_outlines label `paired` (manual overrides TrackMate, user 2026-08-04)."""
    ax_=_plate_axis(b); tr=_load_tracks(b)
    if ax_ is None or not tr: return []
    c,nrml=ax_
    meta=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); ana=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    if meta is None: return []
    hi=ana if (ana is not None and ana>meta) else meta+1e9
    def _nspan(sp): return sum(1 for t,x,y in sp if meta<=t<=hi)
    def _mdist(sp):
        dd=[abs(np.dot(np.array([x,y])-c,nrml))*ps(b) for t,x,y in sp if meta<=t<=hi]
        return np.median(dd) if dd else 1e9
    span_med=np.median([_nspan(s) for s in tr.values()]) or 1
    full=[(tid,sp) for tid,sp in tr.items() if _nspan(sp)>=max(3,span_med)]
    out=[]
    for tid,sp in sorted(full,key=lambda kv:_mdist(kv[1]))[:3]:      # 3 fullest tracks closest to the plate
        for (t,x,y) in sp:
            if meta<=t<=hi: out.append((t,x,y))
    return sorted(out)
_TOL_PLATE=120.0    # s: a polar frame is paired only to a plate spot within ~this window (else no plate ref)
_DT=[]              # (batch, t_min, polar_au, plate_au, diff_au) per polar frame
_cellPP=defaultdict(lambda:[[],[]])   # batch -> [polar_vals, plate_vals] for the paired per-cell summary
_diff_base=[b for b in trk if len(sister(b))>=5 and trk[b].get('cytosol_bg') and not lib.is_mad1(b) and not lib.excluded(b) and b!=LONG_SAMPLE]  # drop the ~95-min temporal outlier from these time-series diff plots
for _ub in sorted(b for b in _diff_base if b2.get(b) is None):   # standing rule: don't plot the unassigned cohort — flag it
    lib.log_review("kt_diff_unassigned_excluded",_ub,"no cohort","unassigned-cohort cell EXCLUDED from polar−plate diff time-series (standing rule: don't plot unassigned cohort) — assign a cohort or confirm exclusion")
_diff_cells=[b for b in _diff_base if b2.get(b) is not None]
_dcov=set(); _skip_noplate=[]; _skip_farplate=0; _skip_meas=0
for b in sorted(_diff_cells):
    psp=_plate_spots_for(b)
    if not psp:
        _skip_noplate.append(b); lib.log_review("kt_diff_no_plate_track",b,"","no manual paired-KT plate-control spots (no paired outlines / no meta_plate / no metaphase) — cell excluded from polar−plate diff"); continue
    fa=first_abl(b)
    ft=lib.FluorTif(b,'monitoring')                          # ONE FluorTif open per batch
    if not ft.ok(): ft.close(); continue
    _pt=np.array([s[0] for s in psp])
    for f,t,x,y in sister(b):
        g=ft.plane_by_frame(f)                               # polar KT maps by FRAME (ground-truth), not t_sec
        if g is None: continue
        cb=cyto_at(b,f,t)                                    # same-frame cytosol_bg preferred (else nearest-in-time)
        if cb is None: continue
        pol=_kt_val(g,x,y,cb)                                # manual polar KT, our disk way
        if pol is None: _skip_meas+=1; continue
        j=int(np.argmin(np.abs(_pt-t)))                      # plate spot nearest IN TIME to this polar frame
        pt_t,px,py=psp[j]
        if abs(pt_t-t)>_TOL_PLATE: _skip_farplate+=1; continue   # no plate KT near this frame -> no plate reference
        pla=_kt_val(g,px,py,cb)                              # plate KT, measured IDENTICALLY (same plane, same cytosol)
        if pla is None: _skip_meas+=1; continue
        tm=((t-fa)/60.0) if fa is not None else (t/60.0)
        _DT.append((b,tm,pol,pla,pol-pla)); _cellPP[b][0].append(pol); _cellPP[b][1].append(pla); _dcov.add(b)
    ft.close()
rowsD=[[b,round(tm,2),round(pol,1),round(pla,1),round(dv,1)] for (b,tm,pol,pla,dv) in _DT]
# ---- plot 4c: per-cell polar − plate over time + per-cohort binned-median trend ----
figD,axD=plt.subplots(figsize=(9.4,5.4))
_byD=defaultdict(list); _byGdiff=defaultdict(list)
for b,tm,pol,pla,dv in _DT: _byD[b].append((tm,dv)); _byGdiff[b2.get(b)].append((tm,dv))
for b,ser in _byD.items():
    ser=sorted(ser)
    if len(ser)>=2: axD.plot([s[0] for s in ser],[s[1] for s in ser],color=lib.PALETTE.get(b2.get(b),"#888"),alpha=.55,lw=1.0,marker="o",ms=2)
    elif len(ser)==1: axD.scatter([ser[0][0]],[ser[0][1]],color=lib.PALETTE.get(b2.get(b),"#888"),s=16)
for g,pp in _byGdiff.items():                                # per-cohort binned-median trend (>=2 cells/bin)
    if g is None: continue
    a=np.array(sorted(pp))
    if len(a)<5: continue
    _cells_in=defaultdict(set)
    for (bb,tm,pol,pla,dv) in _DT:
        if b2.get(bb)==g: _cells_in[int(tm//4)].add(bb)
    gx=[];gy=[]
    for lo in np.arange(np.floor(a[:,0].min()/4)*4,a[:,0].max()+4,4):
        m=(a[:,0]>=lo)&(a[:,0]<lo+4)
        if m.sum()>=3 and len(_cells_in[int((lo+2)//4)])>=2: gx.append(lo+2); gy.append(np.median(a[m,1]))
    if len(gx)>=2: axD.plot(gx,gy,color=lib.PALETTE.get(g,"#888"),lw=3,zorder=6)
axD.axhline(0,color="#999",ls="--",lw=1); axD.axvline(0,color="#333",ls=":",lw=.9)
axD.set_xlabel("Time since first ablation (min; t=0 = first ablation)")
axD.set_ylabel(f"eYFP intensity: polar − plate KT (Σ r={R} disk, bg-subtracted)")
_gsD=sorted([g for g in _byGdiff if g is not None],key=lambda g:lib.lbl(g))
_ncellD=defaultdict(set)
for b in _dcov: _ncellD[b2.get(b)].add(b)
from matplotlib.lines import Line2D as _LD
_hD=[_LD([0],[0],color=lib.PALETTE.get(g,"#888"),lw=2,label=f"{lib.lbl(g).splitlines()[0]} (N={len(_ncellD.get(g,[]))}; bold=cohort median)") for g in _gsD]
if None in _byGdiff: _hD.append(_LD([0],[0],color="#888",lw=2,label=f"unassigned cohort (N={len(_ncellD.get(None,[]))})"))
axD.legend(handles=_hD,fontsize=6.6,ncol=2,loc="upper right")
_medD=np.median([d for *_,d in _DT]) if _DT else float("nan")
axD.set_title(f"Polar − plate kinetochore eYFP-Cdc20 intensity vs time ({len(_dcov)} cells; median diff {_medD:,.0f} a.u.)\n"
              f"MANUAL polar KT vs MANUAL paired-outline PLATE KT, both measured identically (Σ r={R} disk, same-frame cytosol_bg-subtracted); plate KT may differ frame-to-frame; +'ve = polar brighter",
              loc="left",fontweight="bold",fontsize=8.8)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_kt_intensity_diff.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_kt_intensity_diff",["batch","t_min_since_first_abl","polar_au","plate_au","diff_au"],rowsD,
  {"type":"per-cell line (polar − plate) + per-cohort binned-median trend",
   "polar":"MANUAL polar/sisterless mark, snapped Σ r=%d disk, same-frame cytosol_bg-subtracted, floor 0"%R,
   "plate":"MANUAL paired-KT outline centroid NEAREST IN TIME to the polar frame (fullest runs closest to meta_plate), measured IDENTICALLY on the same plane with the same cytosol_bg; plate KT may differ frame-to-frame",
   "pairing_tolerance_s":_TOL_PLATE,"x":"t=0 = first ablation (per-cell offset)"},SCRIPT,
  "Polar − manual-paired-plate KT eYFP-Cdc20 intensity difference over time (identical r=9 disk measurement)")
print(f"4c diff plot: {len(_dcov)} cells, {len(_DT)} polar frames paired -> G4_kt_intensity_diff.png "
      f"(skipped: no-plate-track {len(_skip_noplate)} cells, far-plate {_skip_farplate} frames, unmeasurable {_skip_meas} frames)")
# ---------- 4d. PAIRED polar-vs-plate KT intensity (per cell) — shows polar > plate ----------
# Per-cell MEDIAN polar vs MEDIAN plate intensity (both our identical r=9 disk measurement), one dumbbell per
# cell; paired Wilcoxon signed-rank tests whether polar > plate across cells.
figPP,axPP=plt.subplots(figsize=(6.0,5.6)); rowsPP=[]
_pol_c=[]; _pla_c=[]; _pp_b=[]
for b,(pv,qv) in _cellPP.items():
    if not pv or not qv: continue
    mp_,mq_=float(np.median(pv)),float(np.median(qv)); _pol_c.append(mp_); _pla_c.append(mq_); _pp_b.append(b)
    rowsPP.append([b,round(mq_,1),round(mp_,1),len(pv)])
if _pol_c:
    _pol_c=np.array(_pol_c); _pla_c=np.array(_pla_c); _rng=np.random.RandomState(0)
    for mq_,mp_,b in zip(_pla_c,_pol_c,_pp_b):
        axPP.plot([0,1],[mq_,mp_],color=(lib.PALETTE.get(b2.get(b),"#888") if mp_>mq_ else "#cccccc"),alpha=.5,lw=1.0,zorder=1)
    axPP.scatter(np.zeros(len(_pla_c))+(_rng.rand(len(_pla_c))-.5)*.10,_pla_c,s=26,color="#1b5e20",alpha=.75,zorder=3)
    axPP.scatter(np.ones(len(_pol_c))+(_rng.rand(len(_pol_c))-.5)*.10,_pol_c,s=26,color="#762a83",alpha=.75,zorder=3)
    axPP.hlines(np.median(_pla_c),-.2,.2,color="#1b5e20",lw=2.6,zorder=4); axPP.hlines(np.median(_pol_c),.8,1.2,color="#762a83",lw=2.6,zorder=4)
    _fracPP=float(np.mean(_pol_c>_pla_c))
    try:
        from scipy import stats as _stPP; _W,_pPP=_stPP.wilcoxon(_pol_c,_pla_c,alternative="greater"); _pwr=f"Wilcoxon (polar>plate, paired per cell) p={_pPP:.2g}"
    except Exception: _pwr="Wilcoxon n/a"
    _fracFr=float(np.mean([d>0 for *_,d in _DT])) if _DT else 0
    axPP.set_title(f"eYFP-Cdc20 — polar vs plate KT, paired per cell (N={len(_pol_c)})\n{_pwr}; polar brighter in {_fracPP*100:.0f}% of cells and {_fracFr*100:.0f}% of {len(_DT)} frames (med polar {np.median(_pol_c):,.0f} vs plate {np.median(_pla_c):,.0f} a.u.)\nMANUAL polar KT vs MANUAL paired-outline plate KT, identical Σ r={R} disk bg-subtracted measurement",loc="left",fontweight="bold",fontsize=8.4)
else:
    axPP.set_title("polar vs plate KT (paired) — no cells",loc="left",fontsize=9)
axPP.set_xticks([0,1]); axPP.set_xticklabels(["plate KT\n(manual paired outline)","polar KT\n(manual)"]); axPP.set_ylabel(f"eYFP-Cdc20 intensity (Σ r={R} disk, bg-subtracted)")
plt.tight_layout(); plt.close()
# ---------------------------------------------------------------------------------------------
# PLOT 186 IS NO LONGER WRITTEN HERE (disabled 2026-07-29).
# This block builds the MIXED-SOURCE version: manual polar KT vs a TRACKMATE-positioned plate KT,
# both measured as a fixed Sigma r=9 disk. User 2026-07-28 superseded it:
#     "update it so it's all manual data from kinetochore outlines instead of the current circle
#      regions and trackmate data."
# rebuild_186_outline_intensity.py now owns the plot_id G4_kt_intensity_polar_vs_plate and measures
# INSIDE her traced outlines on both sides, with a per-frame cytosol background and time-matched pairs.
# Both scripts used to savefig + record_plot the SAME id, so whichever ran last won: on 2026-07-29 this
# one ran later and silently replaced the outline figure (p=3e-05, 77%) with the retired mixed-source
# numbers, and PLOT_SETTINGS recorded the wrong provenance with it. Ordering alone is too fragile a
# guard, so the write is removed rather than resequenced. The computation above is left intact - it
# still feeds _DT / rowsPP used by the panels below.
print(f"4d paired plot: {len(_pol_c)} cells computed; figure NOT written "
      f"(plot 186 is owned by rebuild_186_outline_intensity.py — outline-derived, user 2026-07-28)")
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
print(f"  plate-KT >|{PLATE_OSC_HI}| µm/20s removed: {len(_pla_dropped)} point(s) from {len(set(x[0] for x in _pla_dropped))} cell(s)")
print(f"movement: usable tracks {len(usable)}, plate cells {len(set(r[0] for r in rowsP))}, osc steps {len(osc)}, intensity cells {len(set(r[0] for r in rowsI))}")
