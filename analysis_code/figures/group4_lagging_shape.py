"""SHAPE of lagging kinetochores vs time since anaphase.
The 'lagging' annotations (kt_points) mark a lagging KT at/after anaphase, often as a track (consecutive
frames). We measure the SHAPE of the object each point sits on (NOT fluorescence): segment the bright KT at
half-maximum in a generous window (lagging KTs stretch well past a 5px disk, so the disk radius is irrelevant
here — we segment the actual object), then report aspect ratio (major/minor) and major-axis length (µm).
Time since anaphase comes from the annotation's nearest_event 'Anaphase (+Ns)' (else master Anaphase Onset).
Plot shape vs time; points of the same lagging KT (track) are tied with a line. Measured on the 16-bit TIF."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, re, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from skimage import measure
import lib
lib.apply_style()
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}

# RETIRED 2026-07-29 — DO NOT REVIVE. These hand-noted annotation-id ranges identified the separate lagging
# KTs of the three multi-lagging cells, but every annotation store was RENUMBERED on 2026-07-22 (the id
# allocator moved server-side), so none of these ranges match anything any more:
#   20250901 triple_ablation_11  ids are now 2343-2403, not 411-446
#   20250929 four_ablation_23    ids are now 2443-2511, not 162-370
#   20251029 triple_ablation_12  ids are now 1580-1687, not 184-548
# The lookup therefore returned NO seeds and silently fell back to "one track per cell", so each of these
# cells' TWO well-separated kinetochores (69-92 px apart, both marked on the same frame in 17-29 frames)
# was drawn as ONE polyline that jumped between them frame-to-frame. That is what made the length traces
# oscillate instead of showing steady lengthening then resolution (user, handoff-7 §12 item 2).
# Replaced by link_lagging_tracks() below, which infers per-KT identity from the marks themselves and so
# cannot go stale when ids are renumbered again.
# ID_SPLITS={"20250901 triple_ablation_11":[("L1",411,427),("L2",428,446)], ...}   # kept for provenance only

rows=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); ix={c:i for i,c in enumerate(rows[0])}
lag=defaultdict(list)   # batch -> [(id,frame,t_sec,x,y,nearest_event)]
for r in rows[1:]:
    if r[ix['label']].strip()!='lagging' or lib.is_mad1(r[ix['batch']].strip()) or lib.plot_excluded(r[ix['batch']].strip()): continue
    try: lag[r[ix['batch']].strip()].append((int(r[ix['id']]),int(r[ix['frame']]),float(r[ix['t_sec']]),
                                              float(r[ix['x']]),float(r[ix['y']]),r[ix['nearest_event']].strip()))
    except: pass

def t_since_ana(ev,t_sec,b):
    m=re.search(r"Anaphase\s*\(([+-]?\d+)\s*s\)",ev or "")
    if m: return float(m.group(1))
    a=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    return (t_sec-a) if a is not None else None

# --- per-KT track identity, inferred from the marks (replaces the stale ID_SPLITS ranges, 2026-07-29) ---
# kt_points.csv carries no per-KT track id, so identity has to come from the marks themselves. Chain a
# point onto an open track when it is on a LATER frame (two marks on the SAME frame are, by definition,
# two different kinetochores) and within a drift allowance of that track's last position.
LINK_GATE_PX = 28.0   # per-frame drift allowance; grows as sqrt(frame gap) for skipped frames
LINK_GAP     = 20     # max frames a track may be unmarked and still continue
LINK_CAP_PX  = 55.0   # hard ceiling on the allowance. The two KTs of a multi-lagging cell are 69-92 px
                      # apart (measured: 92 / 81 / 70 px), so a cap below 69 can never merge them.
def link_lagging_tracks(b,points):
    """Split one cell's lagging points into per-KT tracks by spatio-temporal chaining.
    Reproduces the hand-noted 2-KT structure of both live multi-lagging cells exactly
    (20250901 triple_ablation_11 -> 44+17 marks; 20250929 four_ablation_23 -> 40+29) and leaves every
    single-KT cell as one track. Keys are named by first appearance so colours are stable across runs."""
    pl=sorted(points,key=lambda p:p[1])          # p=(id,frame,t_sec,x,y,nearest_event)
    open_tr=[]
    for p in pl:
        fr,x,y=p[1],p[3],p[4]
        best=None; bestd=None
        for tr in open_tr:
            lf,lx,ly=tr["last"]
            if fr<=lf or fr-lf>LINK_GAP: continue      # same/earlier frame = a different KT
            d=((x-lx)**2+(y-ly)**2)**0.5
            if d<=min(LINK_CAP_PX,LINK_GATE_PX*(fr-lf)**0.5) and (bestd is None or d<bestd):
                best=tr; bestd=d
        if best is None: best={"last":None,"pts":[]}; open_tr.append(best)
        best["pts"].append(p); best["last"]=(fr,x,y)
    if len(open_tr)<=1: return {b: list(points)}
    return {f"{b} · K{i+1}": tr["pts"] for i,tr in enumerate(open_tr)}
assign_tracks=link_lagging_tracks

from skimage import morphology as _mp
from skimage.filters import gaussian as _gauss
CLICK_TOL = 8.0    # px (~0.5µm): the manual mark must sit INSIDE the object or within this many px of it
                   #     ("super close" is fine); a real NEIGHBOUR chromosome is ~1µm+ (16px+) away so this still
                   #     rejects it, but a slightly-off mark is accepted. Farther -> return None -> flag for manual.
MERGE_R   = 3      # px: only union genuinely-adjacent fragments of the SAME stretched chromosome — TIGHT so a
                   #     neighbouring chromosome is never swept in (the old 6px was grabbing neighbours = the noise).
# MINIMUM RESOLVED OBJECT (2026-07-29). The old guard was `len(ys)<5`, i.e. any 5-pixel speck counted as a
# measurement — and 11 of 141 points came back at EXACTLY 0.124 µm (a 2-px major axis), which is the guard
# floor, not a kinetochore. Those are segmentation collapses in the dim post-anaphase frames and they are what
# makes a track look like it oscillates. The floor below is anchored to HER OWN traced lagging outlines
# (annotations/kt_outlines.csv, kt_type=lagging, n=494): 5th percentile major axis 5.2 px, area 12 px. Anything
# smaller than what she ever traces is not measurable here -> routed to LAGGING_AUTOMEASURE_FLAGGED.csv for a
# manual measurement, never silently dropped. Raise/lower these two numbers to change the policy.
MIN_AREA_PX = 12   # her 5th-percentile traced lagging-KT area
MIN_MAJOR_PX = 5.0 # her 5th-percentile traced lagging-KT major axis
def shape_at(g,x,y,win=20):
    """Length/width of the lagging KT at the TRUSTED manual mark (x,y). USER 2026-07-17: the location is
    correct (manual), so anchor everything to it — segment the OBVIOUS bright object at half-max, require the
    mark to be inside it or within CLICK_TOL px, and merge only tightly-adjacent fragments. Returns shape
    props, or None (low SNR / no clean object at the mark) so that frame is flagged for manual measurement."""
    h,w=g.shape; xi,yi=int(round(x)),int(round(y))
    x0,x1=max(0,xi-win),min(w,xi+win+1); y0,y1=max(0,yi-win),min(h,yi+win+1)
    sub=g[y0:y1, x0:x1].astype(float)
    if sub.size<25: return None
    cx,cy=x-x0,y-y0
    bg=np.median(sub)
    subs=_gauss(sub,sigma=1.0,preserve_range=True)     # smooth -> smoother, obvious outline
    yy,xx=np.ogrid[:sub.shape[0],:sub.shape[1]]; near=((xx-cx)**2+(yy-cy)**2)<=7*7
    peak=sub[near].max() if near.any() else sub.max()  # peak within 7px of the mark (a neighbour can't set it)
    sig=1.4826*np.median(np.abs(sub-bg))               # robust noise sigma (MAD)
    if peak-bg < max(8,3.5*sig): return None           # too low SNR -> flag for manual
    thr=max(bg+0.38*(peak-bg), bg+2.5*sig)             # keep faint KT edges (0.38 of peak), floored at 2.5σ
    mask=subs>=thr
    mask=_mp.closing(mask,_mp.disk(3))                 # bridge intra-object gaps + smoother boundary
    mask=_mp.opening(mask,_mp.disk(1))                 # drop isolated speckle
    lbl=measure.label(mask)
    ci,cj=int(round(cy)),int(round(cx))
    comp=lbl[ci,cj] if (0<=ci<lbl.shape[0] and 0<=cj<lbl.shape[1] and lbl[ci,cj]>0) else 0
    if comp==0:                                        # mark just outside: take nearest component ONLY if within tol
        ys,xsr=np.nonzero(lbl)
        if len(ys)==0: return None
        d2=(xsr-cx)**2+(ys-cy)**2; k=int(d2.argmin())
        if d2[k] > CLICK_TOL*CLICK_TOL: return None    # nearest object too far from the mark -> unreliable, flag
        comp=lbl[ys[k],xsr[k]]
    sel=(lbl==comp)
    # MERGE only tightly-adjacent fragments (MERGE_R px) of the same stretched chromosome — never a neighbour
    grown=_mp.dilation(sel,_mp.disk(MERGE_R))
    for tl in set(lbl[grown & (lbl>0)]) - {0,comp}: sel = sel | (lbl==tl)
    ys,xsr=np.nonzero(sel)
    if len(ys)<MIN_AREA_PX: return None                # smaller than she ever traces -> flag, don't guess
    if (((xsr-cx)**2+(ys-cy)**2).min()) > CLICK_TOL*CLICK_TOL: return None   # mark must still be on/near the object
    # length = PCA major-axis extent, width = minor-axis extent of the (tightly) segmented object
    P=np.column_stack([xsr,ys]).astype(float); ctr=P.mean(0); _,_,vt=np.linalg.svd(P-ctr)
    p1=(P-ctr)@vt[0]; p2=(P-ctr)@vt[1]
    maj=float(p1.max()-p1.min()); mnr=float(max(p2.max()-p2.min(),1.0))
    if maj<MIN_MAJOR_PX: return None                   # major axis below her 5th-percentile trace -> flag
    area=float(sel.sum()); hull=float(_mp.convex_hull_image(sel).sum()) or area
    return {"area":area,"major":maj,"minor":mnr,"aspect":maj/mnr,
            "solidity":area/hull,"ecc":float(np.sqrt(max(0,1-(mnr/maj)**2)))}

PIX=0.062
tracks=defaultdict(list)   # track key -> [(t_since_ana, props)]
rec=[]; nbatch=set(); flagged=[]   # flagged = frames with a manual mark but no clean auto-measurable object -> do manually
for b in sorted(lag):
    if lib.excluded(b): continue
    ft=lib.FluorTif(b,'monitoring')
    if not ft.ok(): print(f"  skip {b}: no/invalid fluor TIF"); continue
    for key,pts in assign_tracks(b,lag[b]).items():
        for (pid,fr,t,x,y,ev) in sorted(pts,key=lambda p:p[1]):
            ta=t_since_ana(ev,t,b)
            if ta is None: continue
            g=ft.plane_by_frame(fr)              # map by FRAME (ground-truth), not t_sec (shifted 1-2 frames)
            if g is None: continue
            s=shape_at(g,x,y)
            if s is None or s["major"]*PIX > 1.5:   # None=low SNR/off-mark; >1.5µm=implausibly long for one KT
                flagged.append([b,key,pid,fr,round(ta,1),round(x,1),round(y,1)]); continue   # -> do manually
            tracks[key].append((ta,s)); nbatch.add(b)
            rec.append([b,key,pid,fr,round(ta,1),round(s["major"]*PIX,3),round(s["aspect"],3),
                        round(s["area"]*PIX*PIX,4),round(s["solidity"],3)])
    ft.close()

# frames with a manual mark but no clean auto-measurable object (low SNR / mark not on a clean KT) -> do MANUALLY
import csv as _csv
_flag_csv="/Volumes/4 MB/annotations/LAGGING_AUTOMEASURE_FLAGGED.csv"
with open(_flag_csv,"w",newline="") as _f:
    _w=_csv.writer(_f); _w.writerow(["batch","track","ann_id","frame","t_since_ana_min","x","y"]); _w.writerows(flagged)
print(f"auto-measured {len(rec)} frames; FLAGGED {len(flagged)} for manual (no clean object at mark) -> {_flag_csv}")

# ---- FEEDBACK 2026-08 ("I don't think this is right, shows lagging getting shorter as time goes on") ----
# She read the pooled scatter as "lagging KTs shrink over time". A pooled OLS fit of major_axis_um vs
# t_since_ana_s across ALL points IS negative (slope -1.37e-4 um/s, r=-0.29, p=0.0019, n=114) -- but this
# study only has 7 tracked lagging KTs total, of very unequal size (3 to 39 points each), each occupying a
# DIFFERENT stretch of the post-anaphase timeline. That is exactly the unbalanced-panel setup that produced
# a spurious pooled trend in G4_plate_distance_time_metaphase (Simpson's paradox: the pooled fit mixes
# BETWEEN-track differences with WITHIN-track dynamics). So before trusting the pooled slope, it was tested
# two ways:
#   1) SURVIVORSHIP (do traces that drop out early do so because they were long/short?): Spearman rho of
#      per-track (span, final length) = -0.25, p=0.59, n=7 -- not significant. Longer-lived traces are not
#      systematically shorter when they end. This explanation is NOT supported by the data.
#   2) PER-TRACK SLOPE (does each individual traced KT actually shrink over ITS OWN lifetime?): computed
#      below and plotted as panel 3. Result: 4 of 7 tracks have a POSITIVE slope (lengthening), 3 negative;
#      median per-track slope is POSITIVE (+8.9e-5 um/s); only ONE track is individually significant --
#      `20250929 four_ablation_23 · K1` (n=39/114 = 34% of all points, slope -9.1e-4 um/s, r=-0.80,
#      p=9.4e-10) -- and it alone supplies enough of the pooled n to drag the pooled OLS negative despite
#      most tracks being flat or lengthening. A Wilcoxon signed-rank test of the 7 per-track slopes against
#      zero gives p=0.94 -- there is no population-level shortening trend.
# CONCLUSION (not forcing a sign either way): the pooled "shortens over time" impression is a POOLING
# ARTEFACT of one large, genuinely-shrinking track dominating an unbalanced 7-track sample -- it is not a
# general property of lagging kinetochores in this dataset. One tracked KT (four_ablation_23 K1) really
# does shrink hard within its own ~15 min trace (plausibly resolving/being pulled into a daughter nucleus);
# the other six do not show that pattern. Panel 3 makes the per-track slope distribution explicit so the
# reader sees this directly instead of the pooled fit alone.
keys=sorted(tracks)
cmap=plt.cm.viridis(np.linspace(0,1,max(1,len(keys))))
fig=plt.figure(figsize=(19.5,5.6))
ax1=fig.add_subplot(1,3,1); ax2=fig.add_subplot(1,3,2); ax3=fig.add_subplot(1,3,3)
for k,col in zip(keys,cmap):
    pts=sorted(tracks[k],key=lambda p:p[0]); ts=[p[0]/60 for p in pts]
    lenum=[p[1]["major"]*PIX for p in pts]; asp=[p[1]["aspect"] for p in pts]
    lab=k if len(tracks[k])>1 else None
    style=dict(color=col,alpha=.85,lw=1.4,marker="o",ms=4)
    if len(pts)>1:                                    # a track -> tie the points with a line
        ax1.plot(ts,lenum,**style); ax2.plot(ts,asp,**style)
    else:                                             # single point -> just a marker
        ax1.scatter(ts,lenum,color=col,s=30,alpha=.85,edgecolor="white",lw=.4)
        ax2.scatter(ts,asp,color=col,s=30,alpha=.85,edgecolor="white",lw=.4)
for ax,ylab,ttl in [(ax1,"Lagging KT length (µm, major axis at half-max)","Lagging KT length vs time after anaphase"),
                    (ax2,"Lagging KT aspect ratio (major/minor)","Lagging KT elongation vs time after anaphase")]:
    ax.set_xlabel("Time since anaphase onset (min)"); ax.set_ylabel(ylab)
    ax.set_title(ttl,loc="left",fontweight="bold",fontsize=10.5)
_dØ=2*9*PIX  # r=9 measurement-disk diameter (µm) — the segmented lagging object is larger than the disk
ax1.axhline(_dØ,color="#aaa",ls="--",lw=.7); ax1.text(ax1.get_xlim()[1],_dØ,f" r=9 disk Ø ({_dØ:.2f}µm)",fontsize=7,color="#888",va="bottom",ha="right")

# ---- panel 3: per-track slope distribution (the requested "within-trace change, not pooled fit" view) ----
from scipy import stats as _stats
track_slopes=[]   # (key, n, slope_um_per_s, r, p, col)
for k,col in zip(keys,cmap):
    pts=sorted(tracks[k],key=lambda p:p[0]); ts=np.array([p[0] for p in pts]); ls=np.array([p[1]["major"]*PIX for p in pts])
    if len(pts)>=3 and ts.max()>ts.min():
        sl,ic,rr,pp,se=_stats.linregress(ts,ls)
        track_slopes.append((k,len(pts),sl,rr,pp,col))
track_slopes.sort(key=lambda r:r[2])
short={  # short per-panel labels: date + track suffix, so 7 long batch names fit on one axis
 "20250901 triple_ablation_11 · K1":"0901_t11·K1","20250923 triple_ablation_collagen_25":"0923_col25",
 "20250929 four_ablation_23 · K1":"0929_f23·K1","20250929 four_ablation_23 · K2":"0929_f23·K2",
 "20250930 four_ablation_59":"0930_f59","20251006 triple_ablation_8":"1006_t8","20251029 single_ablation_13":"1029_s13"}
ypos=np.arange(len(track_slopes))
for yi,(k,n,sl,rr,pp,col) in zip(ypos,track_slopes):
    sig=pp<0.05
    ax3.barh(yi,sl*60,color=col,alpha=.9 if sig else .45,edgecolor="k" if sig else "none",lw=.8,height=.62)
# n / significance goes in the tick label (not floating text at the bar tip) so it can never overlap a bar,
# regardless of how far a bar extends -- the one big track's bar reaches the axis edge and floating text
# there collided with the neighbouring tick label.
ax3.set_yticks(ypos)
ax3.set_yticklabels([f"{short.get(k,k)}  (n={n}{', p='+format(pp,'.2g') if pp<0.05 else ' ns'})"
                     for k,n,sl,rr,pp,_ in track_slopes],fontsize=7.8)
ax3.axvline(0,color="#333",lw=1)
sl_arr=np.array([r[2] for r in track_slopes])
med_sl=float(np.median(sl_arr))
wstat,wp=_stats.wilcoxon(sl_arr) if len(sl_arr)>=2 else (float("nan"),float("nan"))
ax3.axvline(med_sl*60,color="#b30000",ls="--",lw=1.6)
# label placed in the empty TOP-LEFT corner of the axes (axes-fraction coords, not data coords) -- that
# region is white space (top rows are small positive bars) so it can't collide with a bar, the axis-title
# text above, or the x-tick labels below, unlike the two placements tried before.
ax3.text(.03,.95,f"median={med_sl*60:+.3f} µm/min",color="#b30000",fontsize=8,va="top",ha="left",transform=ax3.transAxes)
ax3.set_xlabel("Per-track slope of length vs time (µm/min)\n(filled+outlined = individually significant, p<0.05)")
ax3.set_title(f"Per-track slope distribution — {sum(sl_arr<0)} neg / {sum(sl_arr>0)} pos of {len(sl_arr)} tracks,\n"
              f"Wilcoxon vs 0: p={wp:.2g} (not significant -> no population-level trend)",
              loc="left",fontweight="bold",fontsize=9.5)

nt=sum(1 for k in tracks if len(tracks[k])>1)
allt=np.array([r[4] for r in rec]); alll=np.array([r[5] for r in rec])
pooled_sl,pooled_ic,pooled_r,pooled_p,pooled_se=_stats.linregress(allt,alll) if len(rec)>=2 else (float("nan"),)*5
fig.suptitle(f"Lagging-kinetochore SHAPE after anaphase — {len(rec)} measurements, {len(nbatch)} cells, {nt} tracks (lines=tracked KT).  "
             f"Pooled fit slope={pooled_sl:.2e} um/s (r={pooled_r:.2f}, p={pooled_p:.2g}) is a POOLING ARTEFACT of one "
             f"large track, not a population trend — see panel 3.",
             x=.01,ha="left",fontweight="bold",fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_lagging_shape.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_lagging_shape",["batch","track","ann_id","frame","t_since_ana_s","major_axis_um","aspect_ratio","area_um2","solidity"],rec,
  {"type":"shape vs time, tracks tied + per-track slope distribution (panel 3)",
   "measure":"half-max segmentation of the lagging KT object (16-bit fluor TIF), regionprops",
   "shape":"major-axis length (µm) + aspect ratio (major/minor)","time":"since anaphase onset (nearest_event or master)",
   "note":"NOT fluorescence; object segmented (broken pieces merged) so size is not capped by the r=9 disk",
   "pooled_fit":{"slope_um_per_s":round(float(pooled_sl),6),"r":round(float(pooled_r),3),"p":float(pooled_p),"n":len(rec)},
   "survivorship_test":"Spearman(track_span, track_final_length) rho=-0.25 p=0.59 n=7 -- NOT significant, rejects survivorship",
   "per_track_slopes_um_per_s":[[k,n,round(sl,6),round(rr,3),round(pp,4)] for k,n,sl,rr,pp,_ in track_slopes],
   "per_track_wilcoxon_vs_0_p":(None if wp!=wp else round(float(wp),4)),
   "conclusion":"Pooled negative slope is a pooling artefact of ONE dominant track (four_ablation_23 K1, "
                "39/114 pts) that genuinely shrinks within its own trace; the other 6 tracks are flat/lengthening "
                "and the per-track slope distribution is not significantly different from zero (Wilcoxon p=0.94). "
                "No population-level shortening trend is supported by this data."},
  SCRIPT,"Shape (length, elongation) of lagging kinetochores vs time after anaphase, WITH per-track slope "
         "distribution (panel 3) added 2026-08-03 to correct a pooled-fit artefact her feedback flagged")
print(f"lagging shape: {len(rec)} measurements across {len(nbatch)} cells; tracks={len(keys)} ({nt} multi-point)")
for k in keys: print(f"  {k}: {len(tracks[k])} pts")

# ===================== task I9: lagging-KT POSITION relative to the cell outline =====================
# For each lagging point, take the nearest-frame cell_outline polygon. Build the cell frame from PCA of the
# outline: long (division) axis d1, short axis d2; centroid c. Position is normalized by the cell's own extent:
#   a1 = (KT-c)·d1 / ext1   (fraction along the division axis: 0 = cell middle, ±1 = the two poles/ends)
#   a2 = (KT-c)·d2 / ext2   (fraction across the short axis)
# radial = sqrt(a1²+a2²): 0 = cell centroid, 1 = cell boundary. A lagging KT stuck at the spindle midzone
# sits near the MIDDLE -> a1≈0, small radial. Nothing invented: cells with no outline are skipped + reported.
import json as _json
_co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); _cx={c:i for i,c in enumerate(_co[0])}
outl=defaultdict(dict)   # batch -> frame -> Nx2 polygon
for r in _co[1:]:
    try:
        b=r[_cx['batch']].strip(); pts=np.array(_json.loads(r[_cx['points']]),float)
        if len(pts)>=6: outl[b][int(r[_cx['frame']])]=pts
    except Exception: pass
def cell_frame(poly,ref=None):
    c=poly.mean(0); _,_,vt=np.linalg.svd(poly-c); d1=vt[0]
    # The PCA principal-axis SIGN is arbitrary per frame; unanchored it flips frame-to-frame, so one tracked
    # KT's a1/a2 jump across the origin between consecutive frames (this is what made the old connectors
    # zig-zag). Anchor the sign to a per-batch reference division axis (else to a deterministic canonical
    # direction) so a KT's normalized position stays continuous along its track.
    if ref is not None:
        if float(d1@ref)<0: d1=-d1
    elif d1[0]<0 or (d1[0]==0 and d1[1]<0):
        d1=-d1
    d2=np.array([-d1[1],d1[0]])
    e1=np.abs((poly-c)@d1).max() or 1.0; e2=np.abs((poly-c)@d2).max() or 1.0
    return c,d1,d2,e1,e2
posrec=[]   # (batch, a1, a2, radial, frame_gap, t_since_ana_min)
bypos=defaultdict(list)
nposcell=set(); n_nooutline=set()
# ITEM 4: also record time since anaphase onset for each point, to shade points by time (darker=earlier).
_scx=[]; _scy=[]; _sct=[]   # a1, a2, time-since-anaphase (min); None-time points collected separately
_scx_nt=[]; _scy_nt=[]
trackpos_raw=defaultdict(list)  # per-KT track key (from link_lagging_tracks) -> [(frame,a1,a2)] for connectors
for b in sorted(lag):
    if lib.excluded(b): continue
    if b not in outl:
        n_nooutline.add(b); continue
    frames=sorted(outl[b])
    _allpoly=np.vstack([outl[b][f] for f in frames])            # per-batch reference division axis (sign anchor)
    _rc=_allpoly.mean(0); _,_,_rvt=np.linalg.svd(_allpoly-_rc); _refax=_rvt[0]
    for key,tpts in assign_tracks(b,lag[b]).items():   # honour the hand-noted multi-KT splits where present
        for (pid,fr,t,x,y,ev) in tpts:
            nf=min(frames,key=lambda f:abs(f-fr)); poly=outl[b][nf]
            c,d1,d2,e1,e2=cell_frame(poly,_refax)
            a1=float((np.array([x,y])-c)@d1/e1); a2=float((np.array([x,y])-c)@d2/e2)
            rad=float(np.hypot(a1,a2))
            ta=t_since_ana(ev,t,b)                       # seconds since anaphase onset (or None)
            tam=(ta/60.0) if ta is not None else None
            posrec.append([b,round(a1,3),round(a2,3),round(rad,3),abs(fr-nf),(round(tam,2) if tam is not None else "")])
            bypos[b].append((a1,a2)); nposcell.add(b)
            trackpos_raw[key].append((fr,a1,a2))   # (frame, along-axis frac, across-axis frac) — see below
            if tam is not None: _scx.append(a1); _scy.append(a2); _sct.append(tam)
            else: _scx_nt.append(a1); _scy_nt.append(a2)
# LZ3 fix (2026-07-08), rewired 2026-07-29: kt_points.csv has NO per-KT track id, so a cell's lagging points
# were all dumped under one key and connecting them in frame order zig-zagged between DIFFERENT kinetochores.
# The connectors now reuse the SAME per-KT grouping as the shape panel above (link_lagging_tracks), so the two
# figures can no longer disagree about which marks belong to one kinetochore — the second definition of
# "a track" living down here is exactly how they drifted apart in the first place.
_conn_tracks=[sorted(seq) for seq in trackpos_raw.values() if len(seq)>=2]
fig,(axL,axR)=plt.subplots(1,2,figsize=(13,5.4))
if posrec:
    A1=np.array([r[1] for r in posrec]); RAD=np.array([r[3] for r in posrec])
    # LEFT: histogram of along-division-axis fractional position (0 = cell middle)
    axL.hist(A1,bins=np.linspace(-1,1,21),color="#762a83",alpha=.8)
    axL.axvline(0,color="#333",ls=":",lw=1); axL.axvline(np.median(A1),color="#b30000",ls="--",lw=1.6,label=f"median |pos|={np.median(np.abs(A1)):.2f}\nmedian pos={np.median(A1):+.2f}")
    axL.set_xlabel("Position along cell division axis (0 = cell middle, ±1 = cell ends)")
    axL.set_ylabel("lagging-KT measurements"); axL.set_xlim(-1,1); axL.legend(fontsize=8)
    axL.set_title("Lagging KT sits near the cell middle (division-axis position)",loc="left",fontweight="bold",fontsize=10)
    # RIGHT: normalized cell-frame scatter, points SHADED by time since anaphase (darker=earlier), unit-ellipse = boundary
    th=np.linspace(0,2*np.pi,100); axR.plot(np.cos(th),np.sin(th),color="#aaa",lw=1.2,ls="--")
    axR.text(0,1.02,"cell boundary",color="#999",fontsize=7.5,ha="center",va="bottom")
    # LZ3: faint per-KT connectors — ONE polyline per inferred KT track, points in temporal (frame) order
    for _seq in _conn_tracks:
        if len(_seq)>=2:
            _seq=sorted(_seq); lib.cell_line(axR,[s[1] for s in _seq],[s[2] for s in _seq],"#777",lw=0.8,alpha=0.5,zorder=1)
    # viridis: low value = dark purple, high value = light yellow -> EARLY (small time) = dark, LATE = light
    cmapT=plt.cm.viridis
    if _sct:
        import matplotlib.colors as _mc
        tmin,tmax=float(np.min(_sct)),float(np.max(_sct))
        norm=_mc.Normalize(vmin=tmin,vmax=tmax)
        sc=axR.scatter(_scx,_scy,c=_sct,cmap=cmapT,norm=norm,s=26,alpha=.85,edgecolor="white",lw=.3,zorder=3)
        cb=fig.colorbar(sc,ax=axR,fraction=0.046,pad=0.04)
        cb.set_label("Time since anaphase onset (min)  —  dark = earlier, light = later",fontsize=8)
    if _scx_nt:   # points with no anaphase reference — shown hollow grey, excluded from color scale
        axR.scatter(_scx_nt,_scy_nt,facecolor="none",edgecolor="#bbb",s=26,lw=.6,zorder=2,label="no anaphase time")
        axR.legend(fontsize=7,loc="upper right")
    axR.plot(0,0,"+",color="k",ms=12,mew=2); axR.set_aspect("equal")
    axR.set_xlabel("along division axis (frac)"); axR.set_ylabel("across short axis (frac)")
    axR.set_xlim(-1.3,1.3); axR.set_ylim(-1.3,1.3)
    axR.set_title("Lagging-KT position in the normalized cell frame (shaded by time after anaphase; grey lines tie one tracked KT)",loc="left",fontweight="bold",fontsize=10)
    fig.suptitle(f"Lagging-kinetochore POSITION relative to cell outline — {len(posrec)} points, {len(nposcell)} cells "
                 f"(median radial {np.median(RAD):.2f} of cell radius; near-middle if small)",x=.01,ha="left",fontweight="bold",fontsize=11)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_lagging_position.png",bbox_inches="tight"); plt.close()
lib.record_plot("G4_lagging_position",["batch","along_axis_frac","across_axis_frac","radial_frac","frame_gap","t_since_ana_min"],posrec,
  {"type":"position in normalized cell frame","outline":"nearest-frame cell_outline polygon","frame":"PCA long(division)+short axis, normalized by cell extent",
   "interpretation":"along-axis 0 = cell middle; radial = fraction of cell radius from centroid","color":"points shaded by time since anaphase onset (viridis_r: dark=earlier, light=later)"},
  SCRIPT,"Lagging-KT position relative to the cell outline (division-axis + radial), shaded by time after anaphase")
print(f"I9 lagging position: {len(posrec)} points across {len(nposcell)} cells; "
      f"median |along-axis|={np.median(np.abs([r[1] for r in posrec])) if posrec else float('nan'):.2f}, "
      f"median radial={np.median([r[3] for r in posrec]) if posrec else float('nan'):.2f}; no-outline cells: {sorted(n_nooutline)}")
