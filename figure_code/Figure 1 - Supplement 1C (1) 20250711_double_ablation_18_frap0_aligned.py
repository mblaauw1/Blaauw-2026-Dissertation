# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""FRAP time-strips — the frames measured over (ablation movie, phase+fluor), editable text.

07-07 feedback:
 T14 — show initial BLEACH then RECOVERY: prepend a PRE-ablation frame and append a LATER-recovery frame
       (temporally further than the frame right after ablation) with its own close-up crop.
 T1/T7 — one consistent font; timestamps + scalebar label same size; close-up scale bar reduced (2 µm).
 T2   — editable-text Illustrator output; ablation row + close-up row are independently-movable groups.
 T5   — ablation marker = red CIRCLE only.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, glob, json, os, numpy as np, cv2
from collections import defaultdict

# ── USAGE BANNER (2026-08-17) ───────────────────────────────────────────────────────────────────────────
# Same discoverability problem as group_timestrips.py: the modes live only in `os.environ.get` calls.
# Placed BEFORE `import lib, ts_render` so --help is instant and survives a broken heavy import.
USAGE = """\
group_frap_timestrips.py — FRAP time-strips (the frames measured over; ablation movie, phase+fluor)

  MODES (environment variables; unset = render EVERY batch that has pre_abl marks — ~106 cells, ~21 min)
    (none)                  full render of all eligible batches
    FRAP_CANDIDATES=1       render ONLY the FRAP_CANDS batches, compose the candidate sheet, then exit
    FRAP_ONLY="a|b"         pipe-separated batch names — targeted re-render/debug of just those cells

  NOTE ON RUNTIME: a full run takes ~20 min and is NOT hung. The cost is `avoid_grid_t`, which runs an FFT
  grid-score over +-4 frames per recovery timepoint to dodge the SLM targeting lattice. It writes output
  per batch as it goes, so progress is visible in group1/frap_timestrips/ — check there, and check it with
  `find ... -mmin -N`, NOT `find -newermt "-N minutes"`, which BSD/macOS find silently mis-parses.
"""
if any(a in ("-h", "--help", "help") for a in sys.argv[1:]):
    print(USAGE); sys.exit(0)

import lib, ts_render
OUT="/Volumes/4 MB/ablation_figures_20260625/group1/frap_timestrips"; os.makedirs(OUT,exist_ok=True)
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def ps(b):
    try: return float(mr.get(b,{}).get("Pixel Size (um)",""))
    except: return 0.062
CSV="/Volumes/4 MB/annotations/kt_points.csv"
rows=list(csv.reader(open(CSV))); ix={c:i for i,c in enumerate(rows[0])}
mark=defaultdict(dict); cyto=defaultdict(list)
for r in rows[1:]:
    if r[ix['type']]!='kt_point': continue
    b=r[ix['batch']].strip(); lab=r[ix['label']].strip()
    try: f=int(r[ix['frame']]); t=float(r[ix['t_sec']])
    except: continue
    if lab=='pre_abl':
        m=mark[b].setdefault(f,{}); m['t']=t
        try: m['xy']=(float(r[ix['x']]),float(r[ix['y']]))
        except: pass
    elif lab=='cytosol_bg': cyto[b].append((f,t))
# 2026-08-17: batch -> render-dir map. WAS glob.glob("/Volumes/4 MB/**/*_frames.json", recursive=True),
# which took >17 MINUTES and had produced no output at all when it was killed; the identical full-drive walk
# via os.walk takes 1.6s (`find` 3.9s) for the same 2157 files. Python's recursive `**` is pathological on
# this external volume — it re-scans directories as it descends. DO NOT depth-bound it as the "fix": 106 of
# those files live at depth>4 under rerender_3ch_20260703/, so a maxdepth search silently loses them.
#
# AND THE ORDERING WAS A REAL BUG, not just slowness. setdefault() is first-wins over glob's UNDEFINED
# traversal order, while 120 dir-basenames (4 of them in this script's 106-batch frap set) exist in TWO
# places at once: the canonical pipeline_session_output/<date>/<batch> and a superseded
# pipeline_session_output/<date>_premerge_<stamp>/<batch>. For 20260108 two_sisterless_kinetochores_14 the
# premerge copy's *_Ablation.mp4 are ZERO BYTES, so whichever one glob happened to reach first decided
# whether that cell rendered at all. Precedence is now explicit and deterministic.
def _rank(d):
    if "_premerge_" in d: return 3                      # superseded pre-merge intermediates
    if "/rerender_" in d: return 2                      # re-render experiments, not the canonical output
    if "/pipeline_session_output/" in d: return 0       # canonical
    return 1
_cand={}
for _root, _dirs, _files in os.walk("/Volumes/4 MB"):
    for _fn in _files:
        if _fn.endswith("_frames.json"):
            _cand.setdefault(os.path.basename(_root), []).append(_root)
            break                                       # one hit per directory is enough
_RDIR={b: sorted(set(v), key=lambda d: (_rank(d), d))[0] for b, v in _cand.items()}
def render_dir(b): return _RDIR.get(b)
def abl_sites(b):
    d=render_dir(b)
    if not d: return []
    fj=f"{d}/{b}_frames.json"
    if not os.path.isfile(fj): return []
    try: meta=json.load(open(fj))
    except Exception: return []
    roi=meta.get("roi") or {"x":0,"y":0}
    m=ts_render.manual_pre_abl_local(b)          # PREFER manual pre_abl marks (ground truth); no flash-refine
    if m: return m
    out=[]
    for e in meta.get("ablation_events_local",[]):
        try: out.append((e["x_px"]-roi.get("x",0), e["y_px"]-roi.get("y",0)))
        except Exception: pass
    return out
def movie(b,ch):
    d=render_dir(b)
    if not d: return None
    mp4=f"{d}/{b}_{ch}_Ablation.mp4"; fj=f"{d}/{b}_frames.json"
    if not os.path.isfile(mp4): return None
    cap=cv2.VideoCapture(mp4)
    if int(cap.get(7))==0: cap.release(); return None
    ts=[f['t_sec'] for f in json.load(open(fj))['frames'] if f['role']=='ablation']
    return cap,np.array(ts)
BURNIN_PX = 64      # acquisition overlay band burned into the rendered movies

def _drop_burnin(fr):
    """Blank the acquisition overlay burned into the movie pixels.

    USER 2026-08-10: "you dont need to put 'phase' or '488', etc, on any frame." group_timestrips got this
    fix, but THIS builder reads frames through its own grab(), so the FRAP strips still carried "488 (GFP)",
    the acquisition timestamp and its scale bar. Same treatment here: top/bottom BURNIN_PX rows of the FULL
    frame, before any crop, so a window away from the frame edge is untouched.
    """
    if fr is None or fr.shape[0] <= 2 * BURNIN_PX: return fr
    return ts_render.drop_burnin(fr, BURNIN_PX)   # shared implementation (replicates, not blanks)

def grab(cap,ts,t):
    fi=int(np.argmin(np.abs(ts-t))); cap.set(cv2.CAP_PROP_POS_FRAMES,fi); ok,fr=cap.read()
    return _drop_burnin(fr) if ok else None

# ---- SLM ablation-targeting-grid avoidance (2026-08-03) -------------------------------------------------
# Same bug group_timestrips.py's flash_idx/nonflash_forward were built for: the ablation SLM sometimes paints a
# dense REGULAR dot-lattice over the FLUOR frame for a few frames around the shot. group_frap_timestrips.py had
# no such guard, so a recovery/'late' timepoint could land squarely on a grid frame (all-lattice, no cell
# signal) -> found while comparing the two named FRAP candidates (both 20250901 triple_ablation_16 #0 and
# 20250409 ptk_yfpcdc20_6 #0 had exactly this on one panel). Fix: a local periodic-lattice FFT score (same
# method as group_timestrips._grid_score) evaluated in a small window around the requested time, snapping to
# the lowest-scoring (least grid-like) nearby frame instead of the raw requested one.
def _grid_score(fr):
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    g=g.astype(np.float32); g=g-g.mean(); h,w=g.shape
    F=np.abs(np.fft.fftshift(np.fft.fft2(g)))
    cy,cx=h//2,w//2; yy,xx=np.ogrid[:h,:w]; rr=np.hypot(yy-cy,xx-cx)
    ring=(rr>12)&(rr<min(h,w)//2); vals=F[ring]
    return float(vals.max()/(np.median(vals)+1e-6)) if vals.size else 0.0
def avoid_grid_t(b,t,window=4):
    """Return t, or the t of a nearby (±`window` frames) Fluor-Ablation frame with a lower grid-lattice score,
    if the requested frame itself looks grid-contaminated (score > max(2x local median, 55) — same threshold as
    group_timestrips.flash_idx). Falls back to the original t on any failure (never worse than doing nothing)."""
    try:
        mv=movie(b,"Fluor")
        if not mv: return t
        cap,tsc=mv
        i0=int(np.argmin(np.abs(tsc-t))); lo=max(0,i0-window); hi=min(len(tsc),i0+window+1)
        scores={}
        for i in range(lo,hi):
            cap.set(cv2.CAP_PROP_POS_FRAMES,i); ok,fr=cap.read()
            if ok: scores[i]=_grid_score(fr)
        cap.release()
        if i0 not in scores or len(scores)<2: return t
        local_med=float(np.median(list(scores.values())))
        if scores[i0]<=max(2.0*local_med,55.0): return t   # requested frame is clean -> keep it
        besti=min(scores,key=lambda i:scores[i])            # else snap to the least grid-like nearby frame
        return float(tsc[besti])
    except Exception:
        return t

HALF=48; ZOOM=3
# close-up scale bar: ~1/3 of the zoom frame, snapped to a conventional value (user 2026-08-04), replacing
# the fixed 2 um so the bar is proportionate to whatever the zoom window actually is.
CU_UM=ts_render.nice_scalebar_um(2*HALF*0.062)
# ===== FRAP CANDIDATES slide (task #14) — render >=4 candidate FRAP timestrips on ONE stacked image so the
# user can pick the best. Guarded: `FRAP_CANDIDATES=1 python3 group_frap_timestrips.py` renders ONLY the
# candidate batches (same FRAP code path, already tight-cropped via ts_render.tight_square) then composes +
# exits. Samples: the FRAP-comparison-plot cells + a couple more clean single-target cdc20 FRAP cells.
FRAP_CANDS=["20250411 ptk_yfpcdc20_13","20260417 ptk2 eyfp cdc20 ablation_18",
            "20250826 test_ablation_14","20250402 ptk_yfpcdc20_2","20250409 ptk_yfpcdc20_6"]
CAND_MODE=bool(os.environ.get("FRAP_CANDIDATES"))
_ONLY=[x for x in os.environ.get("FRAP_ONLY","").split("|") if x]   # debug/targeted re-render, e.g. one named batch
cand_out={}   # batch -> first rendered strip .png (one representative per cell for the composite)
n=0
for b in sorted(mark):
    if b not in cyto: continue
    if CAND_MODE and b not in FRAP_CANDS: continue
    if _ONLY and b not in _ONLY: continue
    mframes=sorted(mark[b])
    for si,F in enumerate(mframes):
        nxt=mframes[si+1] if si+1<len(mframes) else 1e9
        Ft=mark[b][F]['t']
        # 2026-08-03 (item 2, print-quality pass): this used to take the FIRST 11 marked recovery frames,
        # which for a densely-annotated cell put 11 (+pre+bleach+late = up to 14) columns on one strip --
        # checked visually at print size (20250402 ptk_yfpcdc20_13_frap0_aligned.png) and each panel got so
        # narrow the marker/timestamps were hard to read. Cap at MAXREC, subsampled EVENLY across the whole
        # recovery window (not just the earliest points) so the strip still reads as "bleach -> recovery",
        # not "bleach -> a cluster of near-identical early frames".
        # USER 2026-08-04: for the strip she picked for META (20250711 double ablation_18 #0) show frames
        # "through frames for 10s". The cap is on the DISPLAYED clock (t_sec, anchored to the ablation
        # event) -- i.e. keep every frame whose burned-in label is <= 0:10 -- NOT on time-since-bleach.
        # First attempt used (t - Ft) <= 10; because the bleach frame itself sits at -0:02 on that clock,
        # that silently cut everything past 0:08 and dropped the 0:10 frame she expected to see.
        # When a cap is set the LATE recovery panel is suppressed too: it is deliberately placed well past
        # the last recovery frame, so it would put a ~40s+ column on a strip meant to stop at 10s.
        FRAP_TMAX={"20250711 double ablation_18": 10.0}
        _tcap=FRAP_TMAX.get(b)
        _rec_all=[c[1] for c in sorted(cyto[b]) if F<c[0]<nxt]
        if _tcap is not None:
            _n0=len(_rec_all)
            _rec_all=[t for t in _rec_all if t<=_tcap+1e-6]
            print(f"  {b} #{si}: recovery frames capped at displayed t<={_tcap:.0f}s "
                  f"({_n0} -> {len(_rec_all)}; kept {[round(t,1) for t in _rec_all]})")
        MAXREC=6
        if len(_rec_all)>MAXREC:
            _idx=sorted(set(np.linspace(0,len(_rec_all)-1,MAXREC).round().astype(int)))
            rec=[_rec_all[i] for i in _idx]
        else:
            rec=_rec_all
        # ablation-site marker for THIS target (nearest frames.json event, else the pre_abl xy)
        _xy=mark[b][F].get('xy'); _sites=abl_sites(b)
        if _sites and _xy is not None:
            _sites=sorted(_sites,key=lambda s:(s[0]-_xy[0])**2+(s[1]-_xy[1])**2)
            _nx,_ny=_sites[0]; msites=[s for s in _sites if (s[0]-_nx)**2+(s[1]-_ny)**2<=40**2]
        elif _sites: msites=_sites
        elif _xy is not None: msites=[_xy]
        else: msites=[]
        _site=msites[0] if msites else (_xy if _xy is not None else None)
        # get ts array + build the timepoint list: PRE, BLEACH(=Ft), recovery..., LATE-recovery (T14)
        m0=movie(b,"Fluor") or movie(b,"Phase")
        if not m0: continue
        _,ts=m0; m0=None
        i_bleach=int(np.argmin(np.abs(ts-Ft)))
        pre_t=float(ts[max(0,i_bleach-1)])
        # avoid the SLM targeting-grid frame on every timepoint EXCEPT the bleach marker itself (that one is
        # the annotated ground-truth ablation frame -> keep it exactly, even if the shot briefly grids)
        pre_t=avoid_grid_t(b,pre_t)
        rec=[avoid_grid_t(b,t) for t in rec]
        times=[("pre",pre_t,False),("bleach",Ft,True)]+[("rec",t,False) for t in rec]
        last_rec=rec[-1] if rec else Ft
        # LATE recovery: temporally further than the frame right after ablation, clamped inside the movie
        step=(last_rec-Ft) if last_rec>Ft else 20.0
        t_late=min(float(ts.max()), last_rec+max(2*step,40.0))
        t_late=avoid_grid_t(b,t_late)
        if t_late>last_rec+1 and _tcap is None: times.append(("late",t_late,False))
        def zbox(fr,mark_it):
            if _site is None: h,wd=fr.shape[:2]; cx,cy=wd//2,h//2
            else: cx,cy=int(round(_site[0])),int(round(_site[1]))
            h,wd=fr.shape[:2]; x0,y0=max(0,cx-HALF),max(0,cy-HALF); x1,y1=min(wd,cx+HALF),min(h,cy+HALF)
            sub=fr[y0:y1,x0:x1].copy()
            if sub.size==0: return None
            if mark_it:
                import group_timestrips as _G   # 2026-08-17: shared open-centre X marker
                _G.draw_marks(sub, [(cx-x0, cy-y0, (255,0,255), "x", None)])
            return cv2.resize(sub,(sub.shape[1]*ZOOM,sub.shape[0]*ZOOM),interpolation=cv2.INTER_NEAREST)
        # TIGHT-SQUARE crop for the whole FRAP strip (consistent w/ the other timestrips): one fixed box from
        # brightfield cell detection, reused across all frames so the cell fills the frame + no distortion.
        # Detect the cell from BRIGHTFIELD, but fall back to FLUOR when the phase render is unusable.
        # 20250711 double ablation_18 has FIVE of its six movies written as 0-byte files (only
        # Fluor_Ablation survives), so movie(b,"Phase") returned None, _sqbox stayed None, and every
        # whole-cell tile silently rendered the FULL UNCROPPED FRAME. That is why her 10/5/4/5 trim did
        # nothing -- CROP_TRIM_UM lives inside tight_square, which was never reached -- and why the frame's
        # own edges (and the burn-in mask over them) showed as bands. Falling back keeps a real crop box.
        _sqbox=None; _mv0=movie(b,"Phase"); _src="phase"
        if not _mv0:
            _mv0=movie(b,"Fluor"); _src="fluor (phase render unreadable)"
        if _mv0:
            _cap0,_ts0=_mv0; _bf=grab(_cap0,_ts0,float(_ts0[0])); _cap0.release()
            if _bf is not None:
                if _src.startswith("phase"):
                    _pts=ts_render.brightfield_cell_bbox_pts(_bf)
                else:
                    _g=cv2.cvtColor(_bf,cv2.COLOR_BGR2GRAY).astype(np.float32)
                    _pts=ts_render.fluor_cell_bbox_pts(_g)
                _sqbox=ts_render.tight_square(_pts,_bf.shape[1],_bf.shape[0],batch=b)
                print(f"   FRAPBOX {b}: from {_src}; box={_sqbox} "
                      f"({(_sqbox[2]-_sqbox[0])*ps(b):.1f} um) frame={_bf.shape[1]}x{_bf.shape[0]} "
                      f"outside: top={max(0,-_sqbox[1])} bottom={max(0,_sqbox[3]-_bf.shape[0])} "
                      f"left={max(0,-_sqbox[0])} right={max(0,_sqbox[2]-_bf.shape[1])}")
        # gather frames per channel
        wide=[{"t":t,"phase":None,"fluor":None,"phase_label":None} for (_,t,_) in times]
        cu  =[{"t":t,"phase":None,"fluor":None} for (_,t,_) in times]
        for ch in ("Phase","Fluor"):
            mv=movie(b,ch)
            if not mv: continue
            cap,tsc=mv; key="phase" if ch=="Phase" else "fluor"
            for ci,(tag,t,mk) in enumerate(times):
                fr=grab(cap,tsc,t)
                if fr is None: continue
                full=fr.copy()
                if mk:
                    for (mx,my) in msites:
                        import group_timestrips as _G   # 2026-08-17: shared open-centre X marker
                        _G.draw_marks(full, [(mx, my, (255,0,255), "x", None)])
                wide[ci][key]=ts_render.crop_pad(full,_sqbox) if _sqbox else full   # scale-before-crop (edge-padded), fixed across frames
                z=zbox(fr,mk)
                if z is not None: cu[ci][key]=z
            cap.release()
        portions=[]
        rw=ts_render.assemble([p for p in wide if p["phase"] is not None or p["fluor"] is not None], ps(b), 10.0, chan_labels=("Phase","eYFP-Cdc20"), fluor_only=True)   # FLUOR ONLY (drop phase), ptk_yfpcdc20 label
        if rw: portions.append(("ablation",rw[0],rw[1]))
        rc=ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None], ps(b)/ZOOM, CU_UM, chan_labels=("Phase","eYFP-Cdc20"), fluor_only=True)   # FLUOR ONLY (drop phase), ptk_yfpcdc20 label
        if rc: portions.append(("ablation close-up",rc[0],rc[1]))
        if not portions: continue
        _pref=f"{OUT}/{b.replace(' ','_')}_frap{si}"
        ok=ts_render.emit(portions, _pref,
                          title=f"FRAP — frames measured over — {b} (#{si})")
        # ALIGNED variant (user 2026-07-14, "20250411 ...frap0 other version"): the tight ablation close-up
        # tiles share the SAME square page footprint (ALIGN_N) as the whole-cell tiles, so columns line up —
        # the aligned-square companion, matching the other timestrips' _aligned versions. (FRAP has no
        # monitoring row.) Uniform square resize (resize_panels pads-to-square first) -> no distortion.
        _ALIGN_N=420
        _wpan=[p for p in wide if p["phase"] is not None or p["fluor"] is not None]
        _cpan=[p for p in cu   if p["phase"] is not None or p["fluor"] is not None]
        if _wpan and _cpan:
            _ap=[]
            _wsq=ts_render.resize_panels(_wpan,_ALIGN_N); _csq=ts_render.resize_panels(_cpan,_ALIGN_N)
            _wpx=ps(b)*((_sqbox[2]-_sqbox[0])/_ALIGN_N) if _sqbox else ps(b)   # whole-cell tile µm/px after resize
            _cpx=ps(b)*((2*HALF)/_ALIGN_N)                                     # close-up tile µm/px after resize
            _ra=ts_render.assemble(_wsq,_wpx,10.0,chan_labels=("Phase","eYFP-Cdc20"),fluor_only=True)
            if _ra: _ap.append(("ablation",_ra[0],_ra[1]))
            _rca=ts_render.assemble(_csq,_cpx,CU_UM,chan_labels=("Phase","eYFP-Cdc20"),fluor_only=True,show_fmt=False)
            if _rca: _ap.append(("ablation close-up",_rca[0],_rca[1]))
            if _ap: ts_render.emit(_ap,f"{_pref}_aligned",title=f"FRAP (aligned square crop) — {b} (#{si})")
        if ok:
            n+=1
            cand_out.setdefault(b, _pref+".png")   # keep the first successful strip per cell
print(f"FRAP timestrips: {n}")
if CAND_MODE:
    import candidate_compose
    items=[(b, cand_out[b]) for b in FRAP_CANDS if b in cand_out]
    candidate_compose.compose(items, f"{OUT}/frap_candidates.png",
                              sup_title="FRAP candidates — pick one")
    sys.exit(0)
