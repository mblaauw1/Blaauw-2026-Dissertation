# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""polar-chromosome / sisterless-outcome TIMESTRIPS (editable text; ablation + zoom + monitoring).

07-07 feedback:
 T15 — the two existing polar strips (polar KT joins-plate / persists-to-anaphase) get an ABLATION strip +
       ablation ZOOM added; monitoring kept the same (exception to the length rule).
 T16 — two NEW strips added to the trio, full format (marked ablation, zoomed ablation, monitoring phase+fluor):
        (a) single ablation -> sisterless KT AT the metaphase plate the whole rest of mitosis;
        (b) a lagging KT flagged good/stretched.
 T1/T2/T5/T7 — one font, editable Illustrator text, red-circle-only markers, timestamps + scale bars.
 Ablation and monitoring share ONE crop (T4); close-up zooms are exempt.
"""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import glob, os, json, csv, numpy as np, cv2
from collections import defaultdict
import lib, ts_render
OUT="/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def ps(b):
    try: return float(mr.get(b,{}).get("Pixel Size (um)",""))
    except: return 0.062

STRIPS={
 "20250410 ptk_yfpcdc20_11":{"note":"Single sisterless-KT; polar KT joins the metaphase plate.","kind":"joins"},
 "20250403 ptk_yfpcdc20_22":{"note":"Single sisterless-KT; polar KT persists until anaphase.","kind":"persists"},
 # T16a: single ablation -> sisterless KT stays at the metaphase plate the whole rest of mitosis (no polar/lag).
 "20260416 single ablation_10":{"note":"Single ablation; sisterless KT at the metaphase plate the whole rest of mitosis.","kind":"plate_whole"},
 # T16b: single ablation -> good/stretched lagging KT.
 "20260416 single ablation_15":{"note":"Single ablation; lagging (stretched) kinetochore example.","kind":"lagging"},
}

oc=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ox={c:i for i,c in enumerate(oc[0])}
mon_outlines=defaultdict(list); abl_outlines=defaultdict(list)
for r in oc[1:]:
    ph=r[ox['phase']]
    if ph not in ('mon','abl'): continue
    try:
        _p=(float(r[ox['t_sec']]),np.array(json.loads(r[ox['points']]),np.int32))
        (abl_outlines if ph=='abl' else mon_outlines)[r[ox['batch']].strip()].append(_p)
    except: pass

_RDIR={}
for _fj in glob.glob("/Volumes/4 MB/**/*_frames.json",recursive=True):
    d=os.path.dirname(_fj)
    if "_ARCHIVED" in _fj or "backup" in _fj.lower(): continue
    _RDIR.setdefault(os.path.basename(d),d)
def render_dir(b): return _RDIR.get(b)
def fjson(b):
    d=render_dir(b)
    if d and os.path.isfile(f"{d}/{b}_frames.json"): return json.load(open(f"{d}/{b}_frames.json"))
    return None
def role_ts(b,role):
    fj=fjson(b)
    if not fj: return None
    ts=[f['t_sec'] for f in fj['frames'] if f['role']==role]
    return np.array(ts) if ts else None
def abl_events(b):
    fj=fjson(b)
    if not fj: return []
    roi=fj.get("roi") or {"x":0,"y":0}
    m=ts_render.manual_pre_abl_local(b)          # PREFER manual pre_abl marks (ground truth); no flash-refine
    if m: return m
    out=[]
    for e in fj.get("ablation_events_local",[]):
        try: out.append((e["x_px"]-roi.get("x",0),e["y_px"]-roi.get("y",0)))
        except: pass
    return out
def movie(b,ch,role):
    d=render_dir(b)
    if not d: return None
    mp4=f"{d}/{b}_{ch}_{role}.mp4"
    if not os.path.isfile(mp4): return None
    cap=cv2.VideoCapture(mp4)
    if int(cap.get(7))<1: cap.release(); return None
    return cap
def grab(cap,ts,t):
    fi=int(np.argmin(np.abs(ts-t))); cap.set(cv2.CAP_PROP_POS_FRAMES,fi); ok,fr=cap.read(); return fr if ok else None
def _is_dark(fr):
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    return float(np.percentile(g,99.5))<12

def phase_tif_frame(b,role,t):
    """Grayscale-BGR phase frame read from the raw *_Phase_Cropped.tif — fallback for when the rendered Phase
    movie is corrupt/0-frames (e.g. 20250410_11's Phase_Ablation.mp4 has no moov atom) so the ablation strip
    still gets a real brightfield row instead of dropping to eYFP-only."""
    d=render_dir(b)
    if not d: return None
    p=f"{d}/{b}_Phase_Cropped.tif"
    if not os.path.isfile(p): return None
    fj=fjson(b)
    if not fj: return None
    # Only frames that ACTUALLY have a phase tif page (phase_tif_idx is not None). During ablation the phase
    # channel is frequently NOT captured (e.g. 20250403_22: idx is None on all 46 ablation frames — the tif has
    # no plane for the ablation window), so fall back to the nearest-in-time frame of ANY role that DOES have a
    # page. That shows the cell's brightfield (pre/monitoring phase) instead of a black band.
    cand=[f for f in fj["frames"] if f["role"]==role and f.get("phase_tif_idx") is not None] \
         or [f for f in fj["frames"] if f.get("phase_tif_idx") is not None]
    if not cand: return None
    f=min(cand,key=lambda z:abs(z["t_sec"]-t)); idx=int(f["phase_tif_idx"])
    import tifffile
    with tifffile.TiffFile(p) as tf:
        idx=min(idx,len(tf.pages)-1); a=tf.pages[idx].asarray().astype(np.float32)
    lo,hi=np.percentile(a,1),np.percentile(a,99.5)
    if hi-lo<4: return None                    # flat page -> nothing to reveal
    g8=np.clip((a-lo)/max(hi-lo,1e-6)*255,0,255).astype(np.uint8)
    return cv2.cvtColor(g8,cv2.COLOR_GRAY2BGR)

def get_abl_frame(b,ch,cap,ts,t):
    """Grab an ablation-movie frame; for Phase, fall back to the raw Phase_Cropped.tif when the movie is dead
    (0-frame / no moov atom) OR when the decoded frame is essentially BLACK. 20250403_22's Phase_Ablation movie
    decodes fine but every frame renders all-black (rendering bug), so the `fr is None` test alone left the
    brightfield row black — also fall back on a dark frame so the cell shows."""
    fr=grab(cap,ts,t) if cap is not None else None
    if ch=="Phase" and (fr is None or _is_dark(fr)):
        alt=phase_tif_frame(b,"ablation",t)
        if alt is not None: fr=alt
    return fr

def crop_box(b):
    """ONE crop shared by the ablation AND monitoring portions (T4). Derive it from the FIRST ablation
    outline (bbox + margin) so the ablation strip is well framed; fall back to the monitoring-outline union
    only when there is no ablation outline."""
    abl=sorted(abl_outlines.get(b,[]),key=lambda p:abs(p[0]))
    if abl:
        pts=abl[0][1]; x0,y0=pts.min(0); x1,y1=pts.max(0); m=40
    else:
        outs=mon_outlines.get(b,[])
        if not outs: return None
        allp=np.vstack([p for _,p in outs]); x0,y0=allp.min(0); x1,y1=allp.max(0); m=24
    cap=movie(b,"Phase","Monitoring") or movie(b,"Phase","Ablation") or movie(b,"Fluor","Monitoring")
    if not cap: return None
    W=int(cap.get(3)); H=int(cap.get(4)); cap.release()
    return (max(0,int(x0-m)),max(0,int(y0-m)),min(W,int(x1+m)),min(H,int(y1+m)))

def std_crop(b):
    """TIGHT, exactly-square crop (ts_render.tight_square) sized to the cell's OWN manual-outline bbox (first
    ablation outline, fallback first monitoring outline) so the CELL FILLS the frame (~89%); forced square so a
    later resize is uniform (no non-uniform stretch). Reused for ALL ablation + monitoring frames. Replaces the
    old fixed 78µm window that left the cell loose. None if no outline / no movie."""
    abl=sorted(abl_outlines.get(b,[]),key=lambda p:abs(p[0])); mon=sorted(mon_outlines.get(b,[]),key=lambda p:p[0])
    ref=(abl[0][1] if abl else (mon[0][1] if mon else None))
    if ref is None: return None
    cap=movie(b,"Phase","Monitoring") or movie(b,"Phase","Ablation") or movie(b,"Fluor","Monitoring")
    if not cap: return None
    W=int(cap.get(3)); H=int(cap.get(4)); cap.release()
    return ts_render.tight_square(np.asarray(ref,float),W,H,batch=b)

def nonflash_t(b,role,t):
    """Step off a laser-shot frame (brightfield lamp off -> dark phase)."""
    ts=role_ts(b,role); cap=movie(b,"Phase",role)
    if ts is None or cap is None:
        if cap: cap.release()
        return t
    i=int(np.argmin(np.abs(ts-t))); guard=0
    while i>0 and guard<5:
        fr=grab(cap,ts,ts[i])
        if fr is None or not _is_dark(fr): break
        i-=1; guard+=1
    cap.release(); return float(ts[i])

def ablation_portion(b,crop,aligned=False,sq=None):
    """before / marked (red circles) / after, cropped; + one zoom close-up per event (cap 3).
    aligned=True: crop the main tiles to the fixed-physical `sq` window + resample to ts_render.ALIGN_N (square,
    consistent magnification across batches); the zoom uses a fixed-µm half so its physical window matches too."""
    tsa=role_ts(b,"ablation")
    if tsa is None or len(tsa)==0: return []
    evs=abl_events(b)
    t_first=float(tsa.min()); t_last=float(tsa.max())
    # mark frame near the first event time (~t of the ablation window start); non-flash
    tm=nonflash_t(b,"ablation",t_first)
    i=int(np.argmin(np.abs(tsa-tm))); tb=float(tsa[max(0,i-1)]); ta=float(tsa[min(len(tsa)-1,i+1)])
    if ta<=tm: ta=t_last
    times=[("before",tb,False),("ablation",tm,True),("after",ta,False)]
    mcrop=sq if aligned else crop
    wide=[{"t":t,"phase":None,"fluor":None,"phase_label":None} for (_,t,_) in times]
    R=None
    for ch in ("Phase","Fluor"):
        cap=movie(b,ch,"Ablation")
        if cap is None and ch=="Fluor": continue          # no fluor fallback; Phase falls back to the raw tif
        key="phase" if ch=="Phase" else "fluor"
        for ci,(tag,t,mk) in enumerate(times):
            fr=get_abl_frame(b,ch,cap,tsa,t)
            if fr is None: continue
            fr=fr.copy()
            if mk:
                r=R or max(9,int(0.011*fr.shape[1]))
                import group_timestrips as _G   # 2026-08-17: shared open-centre X marker, not a circle
                _G.draw_marks(fr, [(x, y, (255,0,255), "x", None) for (x,y) in evs])
            # 2026-08-17: these frames come straight from the pipeline MP4, which carries the burned-in
            # acquisition overlay. Exclude that band from the croppable rows (it used to be replicated,
            # which is the drag-trail smear she reported) -- nothing is fabricated, the window recentres.
            if mcrop: fr=ts_render.crop_pad(fr,mcrop,band=ts_render.BURNIN_PX).copy()
            wide[ci][key]=fr
        if cap is not None: cap.release()
    portions=[]
    mpan=[p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan=ts_render.resize_panels(mpan,ts_render.ALIGN_N)
        eff=ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff=ps(b)
    res=ts_render.assemble(mpan, eff, 10.0, fluor_only=True)   # FLUOR ONLY (drop phase)
    if res: portions.append(("ablation",res[0],res[1]))
    # close-ups: one per event (cap 3), zoom on the site
    HALF=ts_render.zoom_half_px(ps(b)) if aligned else 60; ZOOM=3
    zoom_portions=[]
    for ei,(ex,ey) in enumerate(evs[:3]):
        cu=[{"t":t,"phase":None,"fluor":None} for (_,t,_) in times]
        for ch in ("Phase","Fluor"):
            cap=movie(b,ch,"Ablation")
            if cap is None and ch=="Fluor": continue      # Phase falls back to the raw tif for the zoom too
            key="phase" if ch=="Phase" else "fluor"
            for ci,(tag,t,mk) in enumerate(times):
                fr=get_abl_frame(b,ch,cap,tsa,t)
                if fr is None: continue
                if aligned:
                    z=ts_render.zoom_to_square(fr,ex,ey,HALF,mk)
                    if z is not None: cu[ci][key]=z
                else:
                    xi,yi=int(round(ex)),int(round(ey)); h,wd=fr.shape[:2]
                    x0,y0=max(0,xi-HALF),max(0,yi-HALF); x1,y1=min(wd,xi+HALF),min(h,yi+HALF)
                    sub=fr[y0:y1,x0:x1].copy()
                    if sub.size==0: continue
                    if mk:
                        import group_timestrips as _G
                        _G.draw_marks(sub, [(xi-x0, yi-y0, (255,0,255), "x", None)])
                    cu[ci][key]=cv2.resize(sub,(sub.shape[1]*ZOOM,sub.shape[0]*ZOOM),interpolation=cv2.INTER_NEAREST)
            if cap is not None: cap.release()
        zeff=ps(b)*(2*HALF)/ts_render.ALIGN_N if aligned else ps(b)/ZOOM
        res=ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None], zeff, 2.0, fluor_only=True, show_fmt=False)   # FLUOR ONLY; no fmt label on close-ups
        if res: zoom_portions.append((f"ablation close-up {ei+1}",res[0],res[1]))
    return portions+zoom_portions

def monitoring_portion(b,crop,aligned=False,sq=None):
    """Up to 6 evenly-spaced monitoring frames (kept 'the same' per T15); metaphase/anaphase phase labels.
    aligned=True: crop to the fixed-physical `sq` window + resample to ts_render.ALIGN_N so the monitoring tiles
    share the main tile's square footprint / magnification."""
    outs=sorted(mon_outlines.get(b,[]),key=lambda x:x[0])
    tsm=role_ts(b,"monitoring")
    if not outs or tsm is None: return None
    mcrop=sq if aligned else crop
    idxs=np.linspace(0,len(outs)-1,min(6,len(outs))).astype(int)
    sel=[outs[i][0] for i in idxs]
    mt=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); at=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    def plab(t):
        if mt is not None and abs(t-mt)<=20: return "metaphase"
        if at is not None and abs(t-at)<=20: return "anaphase"
        return None
    panels=[{"t":t,"phase":None,"fluor":None,"phase_label":plab(t)} for t in sel]
    for ch in ("Phase","Fluor"):
        cap=movie(b,ch,"Monitoring")
        if not cap: continue
        key="phase" if ch=="Phase" else "fluor"
        for ci,t in enumerate(sel):
            fr=grab(cap,tsm,t)
            if fr is None: continue
            fr=fr.copy()
            if mcrop: fr=ts_render.crop_pad(fr,mcrop,band=ts_render.BURNIN_PX).copy()   # MP4 frame: overlay band excluded
            panels[ci][key]=fr
        cap.release()
    mpan=[p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan=ts_render.resize_panels(mpan,ts_render.ALIGN_N)
        eff=ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff=ps(b)
    res=ts_render.assemble(mpan, eff, 10.0, fluor_only=False)   # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")
    return res

for b,spec in STRIPS.items():
    d=render_dir(b)
    if not d: print(f"  skip {b}: no render dir"); continue
    crop=std_crop(b) or crop_box(b)                            # TIGHT square crop (cell fills the frame; no distortion)
    portions=ablation_portion(b,crop)
    mon=monitoring_portion(b,crop)
    if mon: portions.append(("monitoring",mon[0],mon[1]))
    if not portions: print(f"  skip {b}: no portions"); continue
    fn=f"{OUT}/G4_polar_timestrip_{b.replace(' ','_')}"
    ok=ts_render.emit(portions, fn, title=f"Polar timestrip — {spec['kind']} — {b}")
    lib.record_plot(f"G4_polar_timestrip_{b.replace(' ','_')}",["kind"],[[spec["kind"]]],
      {"type":"editable ablation+zoom+monitoring timestrip","kind":spec["kind"],"n_portions":len(portions)},
      SCRIPT,f"Polar-chromosome timestrip ({b})")
    print(f"polar timestrip {b} ({spec['kind']}): {len(portions)} portions {'ok' if ok else 'FAIL'}")
    # ALIGNED-CROP variant: main ablation + zoom + monitoring tiles share ONE fixed-physical (78µm) square
    # footprint so they stack in aligned columns and every batch renders at the SAME magnification.
    sq=std_crop(b)
    if sq is None:
        print(f"  {b}_aligned: SKIP (no outline)")
    else:
        pA=ablation_portion(b,crop,aligned=True,sq=sq)
        mA=monitoring_portion(b,crop,aligned=True,sq=sq)
        if mA: pA.append(("monitoring",mA[0],mA[1]))
        if pA:
            okA=ts_render.emit(pA, f"{fn}_aligned", title=f"Polar timestrip (aligned square crop) — {spec['kind']} — {b}")
            print(f"  {b}_aligned: {len(pA)} portions {'ok' if okA else 'FAIL'}")
            if okA:   # register the variant so it is staleness-checkable (2026-08-04)
                lib.record_plot(f"G4_polar_timestrip_{b.replace(' ','_')}_aligned",["kind"],[[spec["kind"]]],
                  {"type":"editable ablation+zoom+monitoring timestrip (aligned square crop)",
                   "variant_of":f"G4_polar_timestrip_{b.replace(' ','_')}","kind":spec["kind"],
                   "n_portions":len(pA),"crop":[int(v) for v in sq] if sq else None,
                   "geometry":"fixed-physical 78um square footprint shared by main/zoom/monitoring"},
                  SCRIPT,f"Polar-chromosome timestrip ({b}) — aligned square crop")
        else:
            print(f"  {b}_aligned: SKIP (no portions)")
