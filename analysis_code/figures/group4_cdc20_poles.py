"""#3 — eYFP-Cdc20 intensity is increased near poles.
Measure Cdc20 (eYFP = fluor) intensity at POLAR kinetochores (near the spindle pole) vs at the
METAPHASE-PLATE kinetochores (pre_abl, before ablation). Radius-9 disk on the FLUOR movie, total
intensity SUM, background-subtracted with a radius-9 cytosol disk (same size). Pools across batches.
All data on 4 MB (kt_points + pipeline_session_output renders)."""
import sys, os, csv, glob, json, numpy as np, cv2
sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625"); import lib
import matplotlib.pyplot as plt
from scipy import stats
from collections import defaultdict
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; SCRIPT=__file__
import os as _osR; OUT=_osR.environ.get("KT_SWEEP_OUT",OUT); _osR.makedirs(OUT,exist_ok=True)
R=int(__import__("os").environ.get("KT_R","9"))   # radius r=9 disk — CONSISTENT with every other cdc20 plot + feedback text (was 8)
# render index (4 MB only)
RD={}
for fj in glob.glob("/Volumes/4 MB/pipeline_session_output/*/*/*_frames.json"):
    RD.setdefault(os.path.basename(os.path.dirname(fj)),os.path.dirname(fj))
data,_=lib.load_master_plots(); mr={r["Batch Name"]:r for r in data}
def rdir(b):
    dp=(mr.get(b,{}) or {}).get("Drive Path","").strip()
    return dp if dp and os.path.isdir(dp) else RD.get(b)
# kt_points
kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); kx={c:i for i,c in enumerate(kt[0])}
pts=defaultdict(lambda: defaultdict(list))   # batch -> label -> [(frame,t,x,y)]
for r in kt[1:]:
    if lib.is_mad1(r[kx['batch']].strip()) or lib.plot_excluded(r[kx['batch']].strip()): continue
    if lib.is_misplaced_id(r[kx['id']]): continue
    try: pts[r[kx['batch']].strip()][r[kx['label']].strip()].append((int(r[kx['frame']]),float(r[kx['t_sec']]),float(r[kx['x']]),float(r[kx['y']])))
    except: pass

# ---- PLATE-KT REFERENCE, ITEM C (2026-08-03 user): "expand plate kt group so its ~800 like polar kt
# group - ideally each polar kt would have a matching plate kt point from same frame." The OLD plate
# source (kt_points pre_abl) is on the ABLATION movie while polar is on the MONITORING movie -> never
# same-frame comparable (see the removed cross-movie note below). Her manual traced kt_outlines
# label=="paired" rows ARE on the monitoring movie (phase='mon', channel='fluor' — verified in the CSV),
# covering 28 cells / 3008 traced polygons, so they can be frame-matched to polar circles for real. The
# polygon centroid (area centroid, not vertex mean — lib.polygon_centroid) is treated as the plate KT
# position; no snap needed since it is a traced outline, not an imprecise click.
kto=list(csv.reader(open("/Volumes/4 MB/annotations/kt_outlines.csv"))); kox={c:i for i,c in enumerate(kto[0])}
paired_outlines=defaultdict(list)   # batch -> [(frame,t_sec,cx,cy)]
for r in kto[1:]:
    if r[kox['label']].strip()!='paired': continue
    b=r[kox['batch']].strip()
    if lib.is_mad1(b) or lib.plot_excluded(b): continue
    try:
        cx,cy=lib.polygon_centroid(json.loads(r[kox['points']]))
        paired_outlines[b].append((int(r[kox['frame']]),float(r[kox['t_sec']]),float(cx),float(cy)))
    except Exception: pass
def disk_sum(fr,x,y):
    """total intensity SUM in radius-R disk (grayscale)."""
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    h,w=g.shape; m=np.zeros((h,w),np.uint8); cv2.circle(m,(int(round(x)),int(round(y))),R,1,-1)
    return float(g[m>0].sum())
def measure(b,label,role):
    """bg-subtracted total-intensity-sum at each labelled point, on the 16-bit cropped fluor TIF."""
    P=pts[b].get(label,[]); bg=pts[b].get("cytosol_bg",[])
    if not P: return []
    ft=lib.FluorTif(b,role.lower())              # role: 'monitoring' (polar) or 'ablation' (pre_abl)
    if not ft.ok(): return []
    if not bg: ft.close(); return []
    out=[]
    for (f,t,x,y) in P:
        fr=ft.plane_by_frame(f)                  # map by FRAME (ground-truth index), NOT t_sec
        if fr is None: continue
        bf,bt,bx,by=min(bg,key=lambda c:abs(c[0]-f)); cval=lib.disk_sum(fr,bx,by,R)   # cytosol bg on the KT's frame (nearest-frame mark, no snap)
        if cval is None: continue
        sx,sy=lib.snap_to_peak(fr,x,y)         # polar / pre_abl are intact KTs -> snap to punctum
        if lib.is_saturated(fr,sx,sy,R) or lib.is_saturated(fr,bx,by,R):   # clipped pixel -> unquantifiable, exclude
            lib.log_review("kt_saturated",b,f"{label} f{f}","KT/cytosol disk hits camera saturation — EXCLUDED (clipped)"); continue
        out.append((t,max(0.0,lib.disk_sum(fr,sx,sy,R)-cval)))   # FLOOR at 0: fluorescence can't be negative
    ft.close()
    return out
def measure_plate_matched(b,target_pts):
    """Plate/paired-KT reference, FRAME-MATCHED to each polar KT's frame wherever possible (ITEM C,
    2026-08-03). Primary source: manual traced kt_outlines paired-label polygon centroid, measured
    IDENTICALLY to polar (Sigma r=R disk, same-frame cytosol_bg-subtracted) on the SAME Monitoring movie
    -> genuinely same-frame comparable, unlike the old cross-movie pre_abl reference. For each polar KT's
    frame, use the nearest available paired-outline frame IN THAT BATCH (gap=0 -> exact same-frame match).
    Only ONE batch among the 11 polar-annotated batches has no traced paired outline at all (verified
    2026-08-03: 10/11 overlap, 465/624 = 74% of in-overlap polar points land on an EXACT frame match,
    median gap 0, mean gap 2.6 frames) -- for that single batch we fall back to the old pre_abl (Ablation
    movie) measurement so its polar KTs are not simply dropped from the plate group; those points are
    tagged not-frame-matched, cross-movie in `rec`. Returns [(t,v,matched_exact,frame_gap)]."""
    P=paired_outlines.get(b,[]); bg=pts[b].get("cytosol_bg",[])
    out=[]
    if P and bg:
        ft=lib.FluorTif(b,'monitoring')
        if ft.ok():
            for (f,t,x,y) in target_pts:
                pf,pt,cx,cy=min(P,key=lambda c:abs(c[0]-f)); gap=abs(pf-f)
                fr=ft.plane_by_frame(pf)
                if fr is None: continue
                bf,bt,bx,by=min(bg,key=lambda c:abs(c[0]-pf)); cval=lib.disk_sum(fr,bx,by,R)
                if cval is None: continue
                if lib.is_saturated(fr,cx,cy,R) or lib.is_saturated(fr,bx,by,R):
                    lib.log_review("kt_saturated",b,f"plate(paired outline) f{pf}","KT/cytosol disk hits camera saturation — EXCLUDED (clipped)"); continue
                out.append((t,max(0.0,lib.disk_sum(fr,cx,cy,R)-cval),gap==0,gap))
            ft.close()
    if out: return out
    # 2026-08-09 — FALLBACK REMOVED (user rule). This used to fall back to `pre_abl` when a batch had no
    # traced paired outline. That is the ABLATION TARGET pair, marked on the ABLATION clip; the plate group
    # is UNTARGETED kinetochores on the MONITORING clip. Her rule: "only use it in the plots that its
    # specific to, and do not mix it in with untargeted" data. Pooling the two is not a scale mismatch to
    # correct for -- they are different kinetochores, and mixing them silently moved the plate group toward
    # target-pair values on every batch that lacked a traced paired outline.
    # A batch with no traced paired outline now contributes NOTHING to the plate group and is logged, so
    # the gap is visible as a smaller N rather than hidden behind a substituted measurement.
    lib.log_review("plate_no_paired_outline", b, f"{len(target_pts)} polar pts",
        "no traced kt_outlines paired data — EXCLUDED from the plate group (was: substituted pre_abl, the "
        "ablation TARGET pair on the Ablation movie, which is not comparable to untargeted plate KTs)")
    return []
polar=[]; plate=[]; rec=[]; polar_tv=[]; plate_tv=[]   # (batch,t,v) for the chronological plot
n_exact_match=0; n_plate_total=0
for b in pts:
    if lib.excluded(b): continue
    pv=measure(b,"polar","Monitoring")                     # polar KTs near pole (monitoring)
    qv=measure_plate_matched(b,pts[b].get("polar",[]))      # plate/paired KTs, frame-matched to polar (ITEM C)
    for t,v in pv: polar.append(v); rec.append([b,"polar",round(v,1)]); polar_tv.append((b,t,v))
    for t,v,matched,gap in qv:
        plate.append(v); n_plate_total+=1; n_exact_match+=int(matched)
        rec.append([b,"plate",round(v,1)])   # location kept as plain "plate" (matches the 2-group violin/zoom grouping); match quality is in the print above + settings.plate_source, not per-row
        plate_tv.append((b,t,v))
polar=np.array([v for v in polar if v>0]); plate=np.array([v for v in plate if v>0])
print(f"Cdc20 plate-KT (ITEM C): N={n_plate_total}, {n_exact_match} ({100*n_exact_match/max(1,n_plate_total):.0f}%) exact same-frame matches to a polar KT"
      f" (target ~800, matching polar N; top-30% trim REMOVED — plate is now measured identically to polar on the same Monitoring movie, so the old cross-movie-scale trim no longer applies)")
fig,ax=plt.subplots(figsize=(6.2,5.4))
groups=[("Polar KT\n(near pole)",polar,lib.PALETTE.get("3-Sister","#762a83")),("Plate KT\n(metaphase plate)",plate,"#6e6e6e")]
_dmax=max([max(d) for _,d,_ in groups if len(d)]+[1.0])   # LZ6: for label headroom above the violins
for i,(lab,d,col) in enumerate(groups):
    lib.journal_violin(ax,d,i,col,width=.8,alpha=.3)   # scale=width (uniform max half-width), cut=0, N<6 points-only
    ax.scatter(np.full(len(d),i)+(np.random.RandomState(i).rand(len(d))-.5)*.22,d,s=lib.VIOLIN_DOT_S,color=col,alpha=.5,edgecolor="white",lw=.2,zorder=3)
    ax.hlines(np.median(d),i-.3,i+.3,color=col,lw=2.4)
    ax.text(i,max(d)+_dmax*0.02,f"med {np.median(d):,.0f}\nN={len(d)}",ha="center",va="bottom",fontsize=8)  # LZ6: label lifted above the violin (was at 98th pctile, over the body)
ax.set_ylim(top=_dmax*1.20)   # LZ6: headroom so the per-violin med/N labels clear the violins
p=stats.mannwhitneyu(polar,plate,alternative="greater").pvalue if len(polar)>=2 and len(plate)>=2 else float('nan')
ax.set_xticks([0,1]); ax.set_xticklabels([g[0] for g in groups])
# ITEM C (2026-08-03): plate KT is now her traced kt_outlines "paired" centroid, frame-matched to the
# polar KT it's plotted against wherever her tracing allows it (was: TrackMate/pre_abl, top-30%-trimmed
# to fix a cross-movie scale mismatch that no longer exists now both groups share one movie + method).
ax.set_xlabel(f"Plate KT: traced kt_outline (paired), frame-matched to a polar KT ({n_exact_match}/{n_plate_total} = {100*n_exact_match/max(1,n_plate_total):.0f}% exact same-frame)",fontsize=8,color="#444")
ax.set_ylabel(f"eYFP-Cdc20 intensity (Σ in r={R} disk, bg-subtracted)")
ax.set_title(f"eYFP-Cdc20 intensity increased near poles\nMann–Whitney (polar>plate) p={p:.2g}",loc="left",fontweight="bold",fontsize=10)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_cdc20_intensity_near_poles.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_cdc20_intensity_near_poles",["batch","location","intensity_sum_bgsub"],rec,
  {"type":"violin polar vs plate","measure":f"total intensity sum in r={R} fluor disk, local-background (annulus) subtracted","stat":"Mann-Whitney greater",
   "plate_source":"kt_outlines paired-label polygon centroid, frame-matched to polar (ITEM C 2026-08-03); pre_abl/Ablation-movie fallback only for the one batch with no traced paired outline"},
  SCRIPT,"eYFP-Cdc20 intensity at polar (near-pole) vs plate kinetochores")
print(f"Cdc20-near-poles: polar N={len(polar)} (med {np.median(polar):.0f}) | plate N={len(plate)} (med {np.median(plate):.0f}) | p={p:.2g}")

# ---- chronological view (slide 53) — ITEM A fix (2026-08-03 user question) --------------------------
# Her question: "manual or trackmate? ... 0 should be start of metaphase and should not go past anaphase
# onset." ANSWER: already MANUAL (kt_points 'polar' label, lib.snap_to_peak — the current, most-recent
# centroid snap; see lib.snap_to_peak docstring, validated 2026-07-29 against her kt_outlines). Never
# TrackMate. What was NOT yet true: x was minutes from the ablation-anchored master t_sec=0 (whole-movie,
# unwindowed). Fixed here: each cell's points are now clipped to [Metaphase Start, Anaphase Onset] and
# x is recomputed as (t - Metaphase Start)/60, so x=0 IS metaphase start and nothing plots past anaphase
# onset. A cell missing either master event time is dropped (never given an assumed time), same
# convention as make_window_companions_20260729.py's meta_to_ana window.
# NOTE for ITEM B (G4_cdc20_intensity_chronological_win_meta_to_ana, built by a script this worker does
# not own): that companion was created BEFORE this fix specifically to give a meta->ana-windowed view of
# this plot's data. Now that the parent itself is windowed to meta->ana, the companion is a near-exact
# duplicate of the parent (same rows, same window) and should be considered for retirement by whoever
# owns make_window_companions_20260729.py. It will also need re-pointing: its filter compares this plot's
# recorded t_min against ABSOLUTE master event times, and t_min recorded below is now METAPHASE-RELATIVE
# (0 at Metaphase Start), not absolute -- the two are no longer on the same clock.
figC,axC=plt.subplots(figsize=(9,5.2))
_meta_win={}; _win_dropped=[]
for b in {bb for bb,_,_ in polar_tv}:
    r=mr.get(b,{})
    m=lib.parse_time(r.get("Metaphase Start (s)","")); a=lib.parse_time(r.get("Anaphase Onset (s)",""))
    if m is not None and a is not None and a>m: _meta_win[b]=(m,a)
    else:
        _win_dropped.append(b)
        lib.log_review("cdc20_chrono_window",b,f"meta={r.get('Metaphase Start (s)','')!r} ana={r.get('Anaphase Onset (s)','')!r}",
            "missing/invalid Metaphase Start or Anaphase Onset -- cell dropped from the metaphase-onset-to-anaphase chronological plot")
bybatch=defaultdict(list)
for b,t,v in polar_tv:
    w=_meta_win.get(b)
    if w is None: continue
    m,a=w
    if t<m or t>a: continue           # 0 = Metaphase Start; nothing plotted past Anaphase Onset
    bybatch[b].append(((t-m)/60.0,v))
print(f"Cdc20 chronological (ITEM A): {len(bybatch)} cells windowed to Metaphase Start->Anaphase Onset "
      f"({len(_win_dropped)} cells dropped, missing a master event time) -> {sum(len(v) for v in bybatch.values())} polar pts (was {len(polar_tv)} whole-movie)")
first=True
for b,pts2 in bybatch.items():
    pts2=sorted(pts2)
    axC.plot([p[0] for p in pts2],[p[1] for p in pts2],color=lib.PALETTE.get("3-Sister","#762a83"),alpha=.5,lw=1,marker="o",ms=3,label=("polar KT (monitoring movie)" if first else None)); first=False
_pol_all=np.array([v for pts2 in bybatch.values() for _,v in pts2],float)
if len(plate):                                  # plate = paired-outline KT reference (ITEM C: frame-matched where possible)
    _pmed=float(np.median(plate)); axC.axhline(_pmed,color="#6e6e6e",ls="--",lw=1.6,label=f"plate KT median (traced paired outline): {_pmed:,.0f} (N={len(plate)})")
if len(_pol_all):
    axC.set_ylim(0,np.percentile(_pol_all,99)*1.15)
    axC.text(.985,.55,f"polar KT median {np.median(_pol_all):,.0f} (N={len(_pol_all)})",
             transform=axC.transAxes,ha="right",va="center",fontsize=8,color="#333")
axC.axvline(0,color="#333",ls=":",lw=.9)
axC.set_xlabel("Time from Metaphase Start (min) -- window ends at Anaphase Onset (per cell)")
axC.set_ylabel(f"eYFP-Cdc20 intensity at polar KT (Σ r={R} disk, bg-subtracted)")
axC.legend(fontsize=8,loc="upper left")
axC.set_title("Polar-KT eYFP-Cdc20 intensity, Metaphase Start to Anaphase Onset (per cell)\n"
              "manual: kt_points 'polar' label, current snap_to_peak centroid snap — never TrackMate",loc="left",fontweight="bold",fontsize=9.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_cdc20_intensity_chronological.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_cdc20_intensity_chronological",["batch","group","t_min","intensity"],
  [[b,"polar",round(x,2),round(v,1)] for b,pts2 in bybatch.items() for x,v in pts2]+[[b,"plate",round(t/60,2),round(v,1)] for b,t,v in plate_tv],
  {"type":"polar intensity, Metaphase Start->Anaphase Onset per cell, t_min RELATIVE to Metaphase Start; plate median reference (unwindowed)",
   "source":"MANUAL kt_points 'polar' label, snap_to_peak (current centroid snap) — never TrackMate",
   "window":"[Metaphase Start, Anaphase Onset] per cell; cells missing either event dropped",
   "note":f"{len(_win_dropped)} cells dropped for missing event time; plate reference is now the frame-matched traced-outline value (ITEM C), same Monitoring movie as polar"},
  SCRIPT,"Polar-KT Cdc20 intensity, Metaphase Start to Anaphase Onset (per cell) + plate reference")

# 2026-08-03: this script previously never flushed its lib.log_review() calls to disk (no other script's
# process sees this module-level buffer) -- the new ITEM A/C review entries (saturated plate matches, the
# no-paired-outline fallback batch, cells dropped from the metaphase window) were being silently lost.
# Match the convention already used in group4_fluor.py and write them out.
lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review.csv")
