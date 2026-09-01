# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""Time-strip generator — phase(top) + fluor(bottom) rows, scale bars.
Ablation markers come from frames.json `ablation_events_local` (universal: every ablation
batch has them, incl. off-target). render_xy = (x_px-roi.x, y_px-roi.y) at scale 1.0.
Selection REQUIRES all 4 movies readable (=> both channels) AND >=1 ablation event."""
import sys; sys.path.insert(0,"/Volumes/4 MB/ablation_figures_20260625")
import csv, glob, json, os, numpy as np, cv2
from collections import defaultdict

# ── USAGE BANNER (2026-08-17) ───────────────────────────────────────────────────────────────────────────
# This script has FIVE separate modes, each selected by an ENVIRONMENT VARIABLE, and each ending in
# sys.exit(0) — so they cannot be combined and must be invoked one at a time. None of that was discoverable
# without grepping for `os.environ.get`, which is how a full re-render came to be run as "just run the
# script" and silently covered only the default mode. `--help` now prints the whole map.
# Placed BEFORE `import lib, ts_render` so --help is instant and works even if a heavy import is broken.
USAGE = """\
group_timestrips.py — timestrip generator (phase top row / fluor bottom row, scale bars)

  RUN ONE MODE AT A TIME. Each guarded mode calls sys.exit(0), so setting two does NOT run both.

  MODES (environment variables; unset = the DEFAULT mode)
    (none)                  DEFAULT: the per-category example strips (CATS loop) + the traced_cell strip
    TRACED_ONLY=1           DEFAULT mode, but SKIP the category strips -- rebuild traced_cell alone
    NF9=1                   the NF9 named-figure strips
    NF10=1                  the NF10 named-figure strips
    TYPE_CANDIDATES=1       per-type candidate contact sheets, for picking a representative cell
    UNMANIP_CANDIDATES=1    unmanipulated-control candidate sheet

  NARROWING (optional, combine with the mode above)
    CAT_ONLY=a,b            DEFAULT mode only — restrict the CATS loop to these categories
    NF9_ONLY=substr         NF9 only  — substring filter, so one strip can be re-rendered alone
    NF10_ONLY=substr        NF10 only — same
    CAND_CAT_ONLY=a,b       TYPE_CANDIDATES only — restrict to these categories
    VARIANT=<name>          pick a per-batch timing variant from NF9_VARIANTS
    ALT_BEFORE=1            v2 render: step further back for the 'before' ablation frame

  RE-RENDER EVERYTHING (the five modes, in order):
    python3 group_timestrips.py
    for v in NF9 NF10 TYPE_CANDIDATES UNMANIP_CANDIDATES; do env $v=1 python3 group_timestrips.py; done

  RELATED: derived art does NOT rebuild itself — after re-rendering, also run
    python3 custom_split_strip_pieces_20260817.py nf9_   (and nf10_)   # the movable __piece* files
    python3 custom_ab5_excerpts_20260817.py                            # the artboard-5 deck excerpts
"""
if any(a in ("-h", "--help", "help") for a in sys.argv[1:]):
    print(USAGE); sys.exit(0)

import lib, ts_render
OUT="/Volumes/4 MB/ablation_figures_20260625/group1/timestrips2"; os.makedirs(OUT,exist_ok=True); SCRIPT=__file__
REVDIR="/Volumes/4 MB/ablation_figures_20260625/_review"; os.makedirs(REVDIR,exist_ok=True)
def flag_reprocess(b,reason):
    """Append a batch needing reprocessing (weird phase/488 overlay, phase-green/fluor-gray channel swap)."""
    lib.log_review("timestrip_reprocess",b,"",reason)
data,_=lib.load_master(); mr={r["Batch Name"]:r for r in data}
def ps(b):
    # authoritative source = frames.json pixel_size_um (per _READ_FIRST_DATA_MAP.md); master col + 0.062 are fallbacks
    try:
        j=fjson(b)
        if j and j.get("pixel_size_um"): return float(j["pixel_size_um"])
    except Exception: pass
    try: return float(mr.get(b,{}).get("Pixel Size (um)",""))
    except Exception: return 0.062

_RDIR={}
for _fj in glob.glob("/Volumes/4 MB/**/*_frames.json",recursive=True):
    _RDIR.setdefault(os.path.basename(os.path.dirname(_fj)),os.path.dirname(_fj))
def render_dir(b): return _RDIR.get(b)
def fjson(b):
    d=render_dir(b)
    if not d: return None
    p=f"{d}/{b}_frames.json"
    return json.load(open(p)) if os.path.isfile(p) else None

_SWAP={}
def channels_swapped(b):
    """Detect the off-target rendering bug: phase rendered GREEN (fluor colourisation) and fluor rendered
    GRAY (phase colourisation). If so the _Phase_/_Fluor_ files are swapped — read the other one."""
    if b in _SWAP: return _SWAP[b]
    d=render_dir(b); sw=False
    if d:
        try:
            pc=cv2.VideoCapture(f"{d}/{b}_Phase_Monitoring.mp4"); o1,pf=pc.read(); pc.release()
            fc=cv2.VideoCapture(f"{d}/{b}_Fluor_Monitoring.mp4"); o2,ff=fc.read(); fc.release()
            if o1 and o2:
                def greenish(fr): bm,gm,rm=fr[...,0].mean(),fr[...,1].mean(),fr[...,2].mean(); return gm>max(rm,bm)*1.4+2
                def grayish(fr): bm,gm,rm=fr[...,0].mean(),fr[...,1].mean(),fr[...,2].mean(); return abs(gm-rm)<8 and abs(gm-bm)<8
                if greenish(pf) and grayish(ff): sw=True       # _Phase_ is green, _Fluor_ is gray -> swapped
        except Exception: pass
    _SWAP[b]=sw; return sw

def movie(b,ch,role):  # ch: Phase/Fluor ; role: Ablation/Monitoring
    d=render_dir(b)
    if not d: return None
    if channels_swapped(b): ch="Fluor" if ch=="Phase" else "Phase"   # read the correctly-colourised file
    mp4=f"{d}/{b}_{ch}_{role}.mp4"; fj=f"{d}/{b}_frames.json"
    if not os.path.isfile(mp4) or not os.path.isfile(fj): return None
    # 2026-08-17: 944 `*_Phase_Ablation.mp4` files on this drive are ZERO BYTES, and they are NOT corrupt —
    # there is simply no phase channel during ablation. Sampled 25 of them: 20 have no ablation frames at
    # all, 5 have ablation frames of which NONE carries a `phase_tif_idx`. That matches §1 rule 5 (ablation
    # portion is fluor-only; monitoring is phase+fluor), so the pipeline opens the writer, writes nothing,
    # and leaves an empty container. Handing that to cv2 produced "moov atom not found" on every strip
    # build — noise that reads like data loss and hid real failures. Skip empties quietly instead.
    try:
        if os.path.getsize(mp4) < 1024: return None
    except OSError:
        return None
    cap=cv2.VideoCapture(mp4)
    if int(cap.get(7))<1: cap.release(); return None
    ts=[f['t_sec'] for f in json.load(open(fj))['frames'] if f['role']==('ablation' if role=='Ablation' else 'monitoring')]
    if not ts: cap.release(); return None
    return cap,np.array(ts)

_OKCACHE={}
def movies_ok(b):
    """all 4 movies present AND readable (frame count>0) — guarantees both channels, no corrupt files."""
    if b in _OKCACHE: return _OKCACHE[b]
    d=render_dir(b); ok=False
    if d:
        ok=True
        for ch in ("Phase","Fluor"):
            for role in ("Ablation","Monitoring"):
                f=f"{d}/{b}_{ch}_{role}.mp4"
                if not os.path.isfile(f): ok=False; break
                c=cv2.VideoCapture(f); n=int(c.get(7)); c.release()
                if n<1: ok=False; break
            if not ok: break
    _OKCACHE[b]=ok; return ok

def abl_events_render(b):
    """ablation (x,y) in rendered-movie pixel space, from frames.json."""
    fj=fjson(b)
    if not fj: return []
    roi=fj.get("roi") or {"x":0,"y":0}
    m=ts_render.manual_pre_abl_local(b)          # PREFER manual pre_abl marks (ground truth); no flash-refine
    if m: return m
    out=[]
    for e in fj.get("ablation_events_local",[]):
        try: out.append((e["x_px"]-roi.get("x",0), e["y_px"]-roi.get("y",0)))
        except: pass
    return out
def abl_window(b):
    """(first_abl_t, last_abl_t) t_sec spanning the ablation-movie frames."""
    fj=fjson(b)
    if not fj: return None
    ts=[f['t_sec'] for f in fj['frames'] if f['role']=='ablation']
    return (min(ts),max(ts)) if ts else None

def brightest_abl_t(b,trange=None):
    """t_sec of the BRIGHTEST phase ablation frame within trange — used for off-target strips so the
    'abl'/'post' panels skip the black laser-flash frames (brightfield is briefly off during the shot)."""
    m=movie(b,"Phase","Ablation")
    if not m: return None
    cap,ts=m; lo,hi=(trange if trange else (float(ts.min()),float(ts.max())))
    best=None; bestv=-1.0
    for i,t in enumerate(ts):
        if t<lo-1e-6 or t>hi+1e-6: continue
        cap.set(cv2.CAP_PROP_POS_FRAMES,i); ok,fr=cap.read()
        if ok and fr.mean()>bestv: bestv=float(fr.mean()); best=float(t)
    cap.release(); return best
BURNIN_PX = 64      # the acquisition overlay band at the top/bottom of every rendered movie frame

def _drop_burnin(fr):
    """Blank the acquisition overlay burned into the rendered movies.

    USER 2026-08-10: "you dont need to put 'phase' or '488', etc, on any frame." Removing the labels
    ts_render DREW was only half of it -- the movies themselves carry "488 (GFP)" / "BRIGHTFIELD", plus
    "z=05" and "best slice", burned into the top band, and an acquisition scale bar in the bottom band.
    Those are pixels, so no drawing change could remove them.

    Only the top and bottom BURNIN_PX rows are cleared, and only ever from the full frame BEFORE cropping,
    so a tile whose crop sits away from the frame edge is untouched. ts_render draws its own timestamp and
    scale bar, so nothing informative is lost.

    2026-08-17 — NOW DELEGATES TO `ts_render.drop_burnin`; this was a DUPLICATE that had been left behind on
    the old `= 0` behaviour. It set the bands to literal BLACK, so every strip from this builder whose crop
    reached a frame edge got a hard black bar — §1 rule 29, and the documented reason ts_render's copy was
    rewritten to REPLICATE the nearest clean row instead. This one never received that fix, which is what put
    a 34-64 px black bar under every tile of the traced_cell strip on artboard 4. One implementation only:
    ts_render's also now SEARCHES for a row that is genuinely clean, because BURNIN_PX is a guess at the band
    height and replicating a row that is itself still inside the overlay just re-draws the black.
    """
    return ts_render.drop_burnin(fr, BURNIN_PX)

def grab(cap,ts,t):
    fi=int(np.argmin(np.abs(ts-t))); cap.set(cv2.CAP_PROP_POS_FRAMES,fi); ok,fr=cap.read()
    return _drop_burnin(fr) if ok else None
def _is_dark(fr):
    """True if a Phase frame carries essentially no brightfield (e.g. the ablation-movie brightfield lamp was
    off during the shot -> all-black). Gates the 488 fallback so normal grey brightfield is never touched."""
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    return float(np.percentile(g,99.5))<12
def _stretch_bgr(fr):
    """Percentile contrast-stretch to grayscale-BGR; None if there is no signal to reveal."""
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    lo,hi=float(np.percentile(g,2)),float(np.percentile(g,99.5))
    if hi-lo<4: return None
    return cv2.cvtColor(np.clip((g.astype(np.float32)-lo)*255.0/(hi-lo),0,255).astype(np.uint8),cv2.COLOR_GRAY2BGR)
def phase_frame(b,role,cap,ts,t):
    """Phase frame at t WITH the dark-ablation fallback: if the brightfield frame is all-black, first try to
    reveal any faint phase (stretch); else substitute the 488/Fluor frame at the same t rendered as a grayscale
    structural reference, so the phase row isn't a black band. Returns a BGR frame or None (normal brightfield
    is returned untouched)."""
    fr=grab(cap,ts,t)
    if fr is None or not _is_dark(fr): return fr
    st=_stretch_bgr(fr)
    if st is not None: return st
    mf=movie(b,"Fluor",role)
    if mf:
        cap2,ts2=mf; ff=grab(cap2,ts2,t); cap2.release()
        sf=_stretch_bgr(ff) if ff is not None else None
        if sf is not None: return sf
    return fr
# 2026-08-17: these two are used ONLY by the traced_cell strip (~lines 1836/1844) and both drew text that was
# CLIPPED OFF THE TILE — which is why traced_cell.png on artboard 4 showed half-height timestamps. cv2 places
# text by its BASELINE: at fontScale 2.17 the cap height is ~48 px, so a baseline hard-coded at y=22 put the
# glyph tops at y=-26, above the image. Size and position now derive from the tile, so text always fits.
# NOTE — "um", NOT "µm", ON PURPOSE: cv2.putText/FONT_HERSHEY_SIMPLEX is ASCII-ONLY and renders any non-ASCII
# as a literal "?" (verified by rendering), so U+03BC here would draw "10 ?m". The matplotlib strips built by
# ts_render.emit DO carry a real "10 µm"; this legacy cv2 strip cannot, and must not be "fixed" to try.
def _fs_for(img, frac=0.045):
    """fontScale whose cap height is ~`frac` of the tile height, plus the (height, baseline) it occupies."""
    s = max(0.4, (img.shape[0]*frac)/22.0)      # HERSHEY_SIMPLEX cap height ~= 22 px per unit of scale
    (tw,th),bl = cv2.getTextSize("Ag", cv2.FONT_HERSHEY_SIMPLEX, s, 2)
    return s, th, bl
def scalebar(img,pxs,um=10):
    h,w=img.shape[:2]; L=int(um/pxs)
    s,th,bl=_fs_for(img)
    cv2.rectangle(img,(w-L-12,h-20),(w-12,h-12),(255,255,255),-1)   # thicker bar (8px)
    txt=f"{um} um"
    (tw,_),_b = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, s, 2)
    x=max(4, min(w-tw-8, w-L-12))               # never run off the left or right edge
    cv2.putText(img,txt,(x,h-24-bl),cv2.FONT_HERSHEY_SIMPLEX, s, (255,255,255), 2,cv2.LINE_AA)
def label(img,txt):
    s,th,bl=_fs_for(img)
    cv2.putText(img,txt,(6,8+th),cv2.FONT_HERSHEY_SIMPLEX, s, (255,255,255), 2,cv2.LINE_AA)
def event_label(img,txt):
    """Event label (metaphase/anaphase) — BENEATH the burned-in timestamp, same small font as the scale bar.
    Only a real mitotic EVENT (metaphase/anaphase) is burned in; ablation-frame captions ('abl1','post',
    'mon start',…) are NOT, so nothing overlaps the timestamp. A thin black shadow keeps the white word
    legible over bright brightfield."""
    if not txt: return
    t=txt.strip().lower()
    if not (t.startswith("metaphase") or t.startswith("anaphase") or t.startswith("cytokinesis") or t.startswith("prometaphase")): return
    word=txt.split()[0]   # event word only (the time is already in the burned-in stamp)
    org=(6,92)            # clearly beneath BOTH lines of the burned-in stamp (time + 'HH:MM:SS')
    cv2.putText(img,word,org,cv2.FONT_HERSHEY_SIMPLEX,1.80,(0,0,0),3,cv2.LINE_AA)
    cv2.putText(img,word,org,cv2.FONT_HERSHEY_SIMPLEX, 1.80, (255,255,255), 2,cv2.LINE_AA)
def draw_marks(img,marks):
    """draw radius-9 markers. Each mark = (x,y) [red ablation] or (x,y,color) [e.g. green KT].
    T5: ablation markers are a red CIRCLE ONLY — no crosshair."""
    if not marks: return
    R=max(9,int(0.011*img.shape[1]))   # honor r=9, but keep visible after downscale
    for m in marks:
        x,y=int(round(m[0])),int(round(m[1])); color=m[2] if len(m)>2 else (255,0,255)
        # USER 2026-08-16: "just include the whole-cell frame ONCE per ablation and put a little box on it
        # to show where the zoom-in frame looks at." A mark tagged "box" with a HALF-WIDTH IN SOURCE PIXELS
        # draws that rectangle instead of the circle, so the whole-cell tile advertises exactly the region
        # the close-up row shows. The half-width is the SAME `half` the zoom crop uses, passed in by the
        # caller — never a hand-picked rectangle.
        if len(m) > 4 and m[3] == "box":
            h=int(round(m[4]))
            cv2.rectangle(img,(x-h,y-h),(x+h,y+h),color,2,cv2.LINE_AA)
            continue
        # ── USER 2026-08-17: SLEEKER ABLATION MARKER, AND EVERY TARGET OF A GROUP ON ONE FRAME ──────
        # "instead of big bulky circles, a more streamlined, sleek figure can be used to mark the ablation
        #  position, like a + symbol where the center is at the point of ablation, or another shape if
        #  something else is more common in literature (so before committing to a new shape, look across
        #  literature)."
        # LITERATURE CHECK (done, 2026-08-17): in laser-ablation mitosis figures the ablation SITE is marked
        # with an X (the Dumont-lab k-fibre ablation convention) or a lightning glyph; circles and arrowheads
        # are reserved for STRUCTURES (kinetochores, MT minus ends). So the X is both sleeker than the circle
        # AND the convention already used for this exact measurement -- and it stops the marker colliding with
        # the circles this project uses for kinetochores. It is drawn MAGENTA, never red: rule 30 forbids
        # red on the green fluorescence panels.
        # The centre is left OPEN (a gap of R/2) so the glyph points at the ablation site without covering it.
        if len(m) > 3 and m[3] == "x":
            g=max(2,int(round(R*0.55))); L=int(round(R*1.9)); th=max(2,int(round(R*0.20)))
            for sx,sy in ((-1,-1),(1,1),(-1,1),(1,-1)):
                cv2.line(img,(x+sx*g,y+sy*g),(x+sx*L,y+sy*L),color,th,cv2.LINE_AA)
            # ATTEMPT INDEX, when the group was shot more than once. NOT a colour difference (she ruled that
            # out) and not a second glyph: one small numeral beside the X, so every target reads as the same
            # kind of thing and the numeral says only WHICH attempt put it there.
            n=m[4] if len(m)>4 else None
            if n:
                # sized FROM the marker (cap height ~2.4R), because tiles are downscaled hard when a
                # 10-column strip lands on a board -- a fixed small font vanishes there (the 2026-08-10 lesson)
                fs=max(0.6,R*0.11); tk=max(2,int(round(R*0.18)))
                org=(x+L+max(3,R//3), y-max(3,R//3))
                cv2.putText(img,str(n),org,cv2.FONT_HERSHEY_SIMPLEX,fs,(0,0,0),tk+2,cv2.LINE_AA)
                cv2.putText(img,str(n),org,cv2.FONT_HERSHEY_SIMPLEX,fs,color,tk,cv2.LINE_AA)
            continue
        cv2.circle(img,(x,y),R,color,2,cv2.LINE_AA)

# ── ABLATION-ATTEMPT GROUPING (her, 2026-08-17) ────────────────────────────────────────────────────
# "there will be multiple ablation targets that seem to be in this same location and thus part of the
#  'group' but over many different timepoints, or ablation attempts. I need you to place all of the targets
#  for a group on that one ablation 'frame'."
# HOW MANY GROUPS IS NOT GUESSED FROM THE MARKS -- it is the master's `# Sisterless KTs`, which is this
# project's definition of the ablation number (never the filename, never `# Unique Targets`). MEASURED
# 2026-08-17: of 87 annotated batches only 8 carry more pre_abl marks than targeted kinetochores, so this
# collapses exactly the strips she is describing and leaves every other strip's geometry untouched.
# Grouping itself is single-linkage on (x, y): repeat attempts at one kinetochore are the closest marks
# there are, and merging the closest pair until `k` clusters remain is deterministic (no random seeding).
def abl_target_count(b):
    """`# Sisterless KTs` for batch b, i.e. how many DISTINCT kinetochores were targeted. None if unknown."""
    try:
        rows,_=lib.load_master()
    except Exception:
        return None
    for r in rows:
        if (r.get("Batch Name") or "").strip()==b:
            try: return int(float(r.get("# Sisterless KTs","")))
            except Exception: return None
    return None

def group_pre_marks(pre,k):
    """Split [(t,x,y), ...] into `k` spatial groups, each returned sorted by time (attempt order).
    k<=0 or k>=len(pre) -> one group per mark, i.e. exactly the previous behaviour."""
    if not pre: return []
    if not k or k<=0 or k>=len(pre): return [[p] for p in sorted(pre)]
    cl=[[p] for p in pre]
    def cen(c): return (sum(q[1] for q in c)/len(c), sum(q[2] for q in c)/len(c))
    while len(cl)>k:
        best=None
        for i in range(len(cl)):
            for j in range(i+1,len(cl)):
                (ax,ay),(bx,by)=cen(cl[i]),cen(cl[j])
                d=(ax-bx)**2+(ay-by)**2
                if best is None or d<best[0]: best=(d,i,j)
        _,i,j=best
        cl[i]=cl[i]+cl[j]; cl.pop(j)
    cl=[sorted(c) for c in cl]
    cl.sort(key=lambda c:c[0][0])          # groups ordered by their FIRST attempt
    return cl

# 2026-08-03 (her item: the 3-sisterless strip has "a thin band of scale-bar text at the panel bottoms").
# MEASURED cause, not guessed: the pipeline's Phase/Fluor mp4s carry the microscope's own burned-in scale
# bar in their bottom rows (on 20251104 ablations_5 the overlay is bright across rows 1016-1040 of a
# 1056-row frame). It only reaches the strip when the square crop window runs to the frame's bottom edge,
# which happens for THIS cell because its outline is 1002 px wide but only 540 tall -> tight_square makes a
# 1002 px box spanning y=207..1208 and OVERHANGS the frame by 152 px; crop_pad edge-replicates those last
# rows, which is the streaky part of the band, with the burned-in bar sitting just above it.
# The fix is PER-BATCH and applied to the SOURCE FRAME, never to the crop geometry: blank the burned-in
# rows, so the bar disappears AND the replicated overhang becomes a clean uniform margin instead of
# streaks. tight_square/crop_pad are deliberately untouched -- 1-sisterless (20260420 ...ablation_20) and
# 2-sisterless have ZERO overhang and must keep their exact current framing.
BURNIN_BOTTOM_PX={"20251104 ablations_5":44}

def _render_panel(b,role,t,txt,marks,ch,outline,crop):
    m=movie(b,ch,role)
    if not m: return None
    cap,ts=m; fr=phase_frame(b,role,cap,ts,t) if ch=="Phase" else grab(cap,ts,t); cap.release()
    if fr is None: return None
    # 2026-08-17: the per-batch bottom overlay is now handled the same way as the standard band — it is
    # EXCLUDED from the croppable rows rather than overwritten with a replicated row (which is what she saw
    # as a drag trail). Nothing is drawn over the source frame any more; the band is simply not reachable.
    _bn=max(int(BURNIN_BOTTOM_PX.get(b,0)), ts_render.BURNIN_PX)
    _band=(ts_render.BURNIN_PX, _bn)
    # (The old code here replicated the nearest clean row over `fr[-_bn:]`, which was the previous remedy for
    # `fr[-_bn:]=0`. Both wrote invented pixels into the tile; the band is now excluded from cropping instead.)
    # outline: None -> none ; ndarray -> that polygon ; "auto" -> nearest manual outline for this role+t
    _out=outline
    if isinstance(outline,str) and outline=="auto": _out=outline_for(b,role,t)
    if _out is not None and not isinstance(_out,str):
        cv2.polylines(fr,[np.asarray(_out).astype(np.int32)],True,(80,220,255),2)
    draw_marks(fr,marks)
    # marks are drawn in FULL-FRAME coordinates first, so the band exclusion happens only now:
    #   cropped  -> crop_pad clamps the window into the usable rows (never smears, never pads)
    #   uncropped-> trim the band off outright, which is safe here because the marks are already pixels
    fr=ts_render.crop_pad(fr,crop,band=_band).copy() if crop else ts_render.trim_burnin(fr,_band)
    return fr   # T6: NO burned-in event/phase text — phase labels are added as editable matplotlib text
def phase_word(txt):
    """Leading phase word (metaphase/anaphase/…) for the editable top-corner label; None otherwise (T8)."""
    if not txt: return None
    w=txt.split()[0].lower()
    return w if w in ("metaphase","anaphase","prometaphase","cytokinesis","prophase") else None

def _grid_score(fr):
    """Periodic-lattice score for the SLM ablation-targeting grid (T11): strongest mid-frequency peak in the
    2-D FFT divided by the background magnitude. A dense regular dot-lattice (the grid) gives a sharp peak far
    above DC -> a high score; cell fluorescence + shot-noise (no periodicity) stays low. This is the robust
    replacement for a raw bright-spot count, which fails here because fluor shot-noise floods the mean+3σ local
    maxima on EVERY frame (~1000-2500 'spots' on clean and grid frames alike, no separation)."""
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY) if fr.ndim==3 else fr
    g=g.astype(np.float32); g=g-g.mean()
    h,w=g.shape
    F=np.abs(np.fft.fftshift(np.fft.fft2(g)))
    cy,cx=h//2,w//2; yy,xx=np.ogrid[:h,:w]; rr=np.hypot(yy-cy,xx-cx)
    ring=(rr>12)&(rr<min(h,w)//2); vals=F[ring]
    if vals.size==0: return 0.0
    return float(vals.max()/(np.median(vals)+1e-6))

_FLASH={}
def flash_idx(b):
    """Cache (flash_frame_indices, t_sec_array) for a batch's ablation movie. A laser-shot frame has the
    brightfield lamp OFF -> the PHASE frame is essentially black (reliable signature, incl. the speckle-bloom
    shot frames whose fluor is sparse-on-dark, not a bright outlier). Also flag fluor brightness outliers AND
    the SLM targeting-grid frames (dense regular dot-lattice on the FLUOR channel, detected independently of
    phase so a batch with a FINE phase movie but a grid-only fluor frame is still caught).
    Used to keep flash/shot/grid frames OFF the strips (T11)."""
    if b in _FLASH: return _FLASH[b]
    res=set(); ts=None
    mp=movie(b,"Phase","Ablation")
    if mp:
        cap,ts=mp; dark=set()
        for i in range(len(ts)):
            cap.set(cv2.CAP_PROP_POS_FRAMES,i); ok,fr=cap.read()
            if ok and _is_dark(fr): dark.add(i)   # brightfield lamp off during the shot
        cap.release()
        if len(dark)<=max(1,len(ts)//2): res|=dark   # guard: a wholly-dark-rendered movie isn't 'all flash'
    mf=movie(b,"Fluor","Ablation")
    if mf:
        cap,ts2=mf; means=[]; gscore=[]
        for i in range(len(ts2)):
            cap.set(cv2.CAP_PROP_POS_FRAMES,i); ok,fr=cap.read()
            means.append(float(fr.mean()) if ok else np.nan)
            gscore.append(_grid_score(fr) if ok else np.nan)   # SLM targeting-grid detector
        cap.release()
        if ts is None: ts=ts2
        arr=np.array(means,float); med=np.nanmedian(arr) if np.isfinite(arr).any() else np.nan
        if np.isfinite(med):
            for i,mv in enumerate(means):
                if np.isfinite(mv) and mv>1.6*med+3: res.add(i)
        # SLM targeting-grid frames (fixes the double-chromosome frame-3 grid): the ablation SLM paints a dense
        # REGULAR lattice of small bright dots over the FLUOR frame. It does NOT raise the whole-frame mean ~60%
        # (the mean threshold above is blind to it), so flag by the periodic-lattice FFT score instead — grid
        # frames spike to ~90-250 vs ~25-50 on clean frames. Threshold = >3x the per-movie median (absolute floor
        # 70). Adding these indices lets nonflash_forward step the 'after' panel past the grid to a clean frame.
        garr=np.array(gscore,float); gmed=np.nanmedian(garr) if np.isfinite(garr).any() else np.nan
        if np.isfinite(gmed):
            grid={i for i,sc in enumerate(gscore) if np.isfinite(sc) and sc>max(2.0*gmed,55.0)}  # 2x/55 catches the FADING grid (e.g. t=19s score 90 vs clean 25-31); 3x/70 missed it. guard below caps runaway.
            if len(grid)<=max(1,len(gscore)//2): res|=grid   # guard: never flag a whole (uniformly periodic) movie
    _FLASH[b]=(res,ts); return _FLASH[b]
def nonflash_t(b,t):
    """T11: if t falls on a laser-flash frame, step back to the nearest earlier NON-flash frame (keep marker)."""
    fs,ts=flash_idx(b)
    if not fs or ts is None or len(ts)==0: return t
    i=int(np.argmin(np.abs(ts-t))); guard=0
    while i in fs and i>0 and guard<5: i-=1; guard+=1
    return float(ts[i])
def nonflash_forward(b,t):
    """For the AFTER frame: step FORWARD past any laser-flash / SLM-targeting-grid frame to the next CLEAN
    frame (the grid clears within a few frames). flash_idx already flags these bright-fluor grid frames; the
    backward nonflash_t would land back on the ablation moment, so 'after' must step forward instead."""
    fs,ts=flash_idx(b)
    if not fs or ts is None or len(ts)==0: return t
    i=int(np.argmin(np.abs(ts-t))); guard=0
    while i in fs and i<len(ts)-1 and guard<10: i+=1; guard+=1
    return float(ts[i])

def build_panel(b,role,t,marks,crop,phase_label=None,disp_t=None):
    try: ts_render.PANEL_LOG.append((b, role, t))     # frame registry — see ts_render.emit
    except Exception: pass
    """One timestrip column -> {'phase','fluor','t','phase_label'} (no burned text). marks in full-frame px."""
    dt=disp_t if disp_t is not None else t
    # per-FRAME ROI nudge (ROI_UM_FRAMES): shifts only the columns she named, both channel rows together
    if crop and b in ROI_UM_FRAMES:
        _m=movie(b,"Phase",role) or movie(b,"Phase","Monitoring")
        if _m:
            _c,_=_m; _W=int(_c.get(3)); _H=int(_c.get(4)); _c.release()
            crop=apply_roi_um_frame(b,crop,t,_W,_H)
    # outline-centred ROI (her first choice where she has traced the cell) -- board 5 item 4
    if crop and b in ROI_OUTLINE_CENTRED:
        _m2=movie(b,"Phase",role) or movie(b,"Phase","Monitoring")
        if _m2:
            _c2,_=_m2; _W2=int(_c2.get(3)); _H2=int(_c2.get(4)); _c2.release()
            crop=recentre_on_outline(b,crop,t,_W2,_H2)
    ph=_render_panel(b,role,dt,"",marks,"Phase",None,crop)
    fl=_render_panel(b,role,dt,"",marks,"Fluor",None,crop)
    if ph is None and fl is None: return None
    # NF10_LABEL_SHIFT moves only the DRAWN timestamp (`t`); `dt` above is what is actually fetched, so
    # the strip still shows her chosen frames, relabelled onto the clock she asked for.
    return {"phase":ph,"fluor":fl,"t":t+NF10_LABEL_SHIFT.get(b,0.0),"phase_label":phase_label}

def closeup_portions(b,pxs,specs,zoom=3,half=None,scalebar_um=None):
    """One movable PORTION per ablation target (T2): before / marked (red circle only) / after, zoomed.
    T3: small (2 µm) scale bar since the crop is only ~2*half*px_um wide. Returns [(name,raster,geom)].
    half defaults to a FIXED-physical zoom window (ts_render.zoom_half_px) so the zoom shows the same µm
    region on 0.031 as on 0.062 µm/px batches (=70px on 0.062, so existing output is unchanged)."""
    if not specs: return []
    if half is None: half=ts_render.zoom_half_px(pxs)
    # USER 2026-08-04: the zoom bar should be ~1/3 of the zoom frame, snapped to a conventional value,
    # rather than a fixed 2 um regardless of how wide the zoom window actually is.
    if scalebar_um is None: scalebar_um=ts_render.nice_scalebar_um(2.0*half*pxs)
    def zbox(fr,x,y,mark):
        xi,yi=int(round(x)),int(round(y)); h,wd=fr.shape[:2]
        x0,y0=max(0,xi-half),max(0,yi-half); x1,y1=min(wd,xi+half),min(h,yi+half)
        sub=fr[y0:y1,x0:x1].copy()
        if sub.size==0: return None
        if mark: cv2.circle(sub,(xi-x0,yi-y0),9,(255,0,255),2,cv2.LINE_AA)   # circle only (T5)
        return cv2.resize(sub,(sub.shape[1]*zoom,sub.shape[0]*zoom),interpolation=cv2.INTER_NEAREST)
    T=len(specs)
    grid=[[{"t":None,"phase":None,"fluor":None} for _ in range(3)] for _ in range(T)]
    for ch in ("Phase","Fluor"):
        m=movie(b,ch,"Ablation")
        if not m: continue
        cap,ts=m; key="phase" if ch=="Phase" else "fluor"
        for ti,(tb,tm,ta,x,y) in enumerate(specs):
            # T11: display every close-up frame on a non-flash frame (keep the marker on the middle one)
            for pi,(_req,tt,mk) in enumerate(((tb,nonflash_t(b,tb),False),(tm,nonflash_t(b,tm),True),
                                              (ta,nonflash_t(b,ta),False))):
                fr=phase_frame(b,"Ablation",cap,ts,tt) if ch=="Phase" else grab(cap,ts,tt)
                # NF10_LABEL_SHIFT: the zoom row is built HERE, not through build_panel, so without this
                # the close-ups keep the raw clock while the whole-cell row above them is relabelled
                # (ablation_13: whole-cell -0:18/-0:06/0:27 over zooms reading 0:24/0:36/1:09).
                # Label with the REQUESTED time (`_req`), not the fetched non-flash frame (`tt`): the
                # whole-cell row above labels the requested time, so using `tt` here printed -0:06/-0:03
                # under a row reading -0:05/-0:02 for the very same frames (seen on two_sisterless_14).
                grid[ti][pi]["t"]=_req+NF10_LABEL_SHIFT.get(b,0.0)
                if fr is not None:
                    z=zbox(fr,x,y,mk)
                    if z is not None: grid[ti][pi][key]=z
        cap.release()
    out=[]
    for ti in range(T):
        panels=[p for p in grid[ti] if p["phase"] is not None or p["fluor"] is not None]
        if not panels: continue
        res=ts_render.assemble(panels,pxs/zoom,scalebar_um,chan_labels=("Phase",fluor_label_for(b)),fluor_only=True,show_fmt=False)   # FLUOR ONLY; no fmt label; correct molecule label (was defaulting to eYFP-Cdc20 on mad1 cells)
        if res: out.append((f"ablation close-up {ti+1}",res[0],res[1]))
    return out

def pad_monitoring(b,n_abl,mon):
    """T9: pad the monitoring panel list up to the ablation panel count by inserting evenly-spaced in-between
    frames (never past cytokinesis; keep existing labelled frames). If monitoring already >= ablation, no-op."""
    M=len(mon)
    if M>=n_abl or M<1: return mon
    ts=sorted(p[1] for p in mon); tmin,tmax=ts[0],ts[-1]
    ct=lib.parse_time(mr.get(b,{}).get("Cytokinesis Onset (s)",""))
    if ct is not None: tmax=min(tmax,ct)
    if tmax<=tmin: return mon
    need=n_abl-M; grid=np.linspace(tmin,tmax,n_abl+2)[1:-1]
    exist=[p[1] for p in mon]; added=[]
    for g in grid:
        if len(added)>=need: break
        if all(abs(g-e)>8 for e in exist+added): added.append(float(g))
    newpan=[("Monitoring",g,"",None) for g in added]
    return sorted(mon+newpan,key=lambda p:p[1])

def fluor_label_for(b):
    """Molecule label for the eYFP fluor channel, by Cell Type (journal-standard). cdc20 cells = eYFP-Cdc20;
    mad1 and hec1-halo+mad1 cells = eYFP-Mad1 (the eYFP tag is on Mad1). 2026-07-11 (user): fixes the wrong
    'eYFP-Cdc20' label on non-cdc20 wide timestrips + z-scans."""
    ct=(mr.get(b,{}).get("Cell Type","") or "").lower()
    return "eYFP-Cdc20" if "cdc20" in ct else "eYFP-Mad1"
def make_strip(b,panels,out_prefix,closeup_specs=None,outline=None,crop="tight",title=None,do_closeups=True,square_aligned=False,fluor_label=None):
    """Editable timestrip: ablation portion, per-target close-up portions, monitoring portion — each an
    independently-movable group (T2). NO caption bars / on-frame phase text (T6). Writes out_prefix.png
    (editable text) + out_prefix_notext.png (bars only). `out_prefix` has NO extension.
    square_aligned=True: main ablation + monitoring + zoom tiles ALL render at the same NxN square footprint
    (square outline-crop for main/monitoring; zoom region unchanged but upscaled) so the zoom row stacks in
    aligned columns under the main row. Returns False (skips) if the batch has no manual outline."""
    pxs=ps(b)
    fl=fluor_label or fluor_label_for(b)   # correct fluor molecule label by Cell Type (eYFP-Cdc20 / eYFP-Mad1)
    if square_aligned:
        abl=[p for p in panels if p[0].lower()=="ablation"]
        mon=[p for p in panels if p[0].lower()=="monitoring"]
        mon=pad_monitoring(b,len(abl),mon); mon=sorted(mon,key=lambda p:p[1])
        # PER-PORTION TRAJECTORY-FITTED crop (combines fitted + fixed-square): the box is the union of the
        # cell's bbox over THAT portion's frames, tight_square'd so the cell FILLS the tile (~89%). Unioning
        # over frames keeps a moving/dividing cell (esp. in MONITORING) fully framed — no cut-off, no dead
        # space. Falls back to the whole-strip square_crop if a portion can't be fit.
        base=square_crop(b)
        if base is None: print(f"  {b}: no outline -> skip aligned variant"); return False
        sq_abl=portion_box(b,"Ablation",[t for (_,t,_,_) in abl]) or base
        sq_mon=portion_box(b,"Monitoring",[t for (_,t,_,_) in mon]) or base
        # (MON_USE_ABL_BOX 2026-07-14, user) some batches have monitoring cell-outlines traced on the WRONG
        # (neighbour) cell, so the monitoring crop lands off the targeted cell. For those, reuse the ablation-
        # portion crop window (centred on the actually-targeted cell) for monitoring too. Safe for off-target/
        # interphase cells that don't migrate far. e.g. 20251104 ablations_17 (mon outlines ~300px off target).
        if b in MON_USE_ABL_BOX: sq_mon=sq_abl
        eff_abl=pxs*(sq_abl[2]-sq_abl[0])/ALIGN_N; eff_mon=pxs*(sq_mon[2]-sq_mon[0])/ALIGN_N
        portions=[]
        # ── USER 2026-08-19, all-figures item 3 ──────────────────────────────────────────────────────
        # The zoom row is built FIRST now, because the whole-cell row above it has to be laid out at the
        # ZOOM row's column count so each whole-cell tile lands directly above the zoom frame whose
        # timepoint it matches. Blank spacer tiles hold the other columns; assemble() then works out
        # widths, separators, scalebar and every text position from the row it is actually given.
        zp=zeff=zinfo=None
        if do_closeups and closeup_specs:
            zp,zeff,zinfo=aligned_closeup_panels(b,closeup_specs,half=ts_render.zoom_half_px(pxs))   # ONE combined zoom row -> columns line up with main; fixed-µm zoom (consistent across batches)
        if abl:
            ap=[build_panel(b,"Ablation",t,marks,sq_abl,disp_t=nonflash_t(b,t)) for (_,t,txt,marks) in abl]
            ap=uniform_fluor_stretch(ts_render.resize_panels([p for p in ap if p],ALIGN_N))
            if zp and zinfo and zinfo["marked_col"] and len(ap)>=1 and zinfo["n_cols"]>len(ap):
                _slots=[None]*zinfo["n_cols"]
                _mc=zinfo["marked_col"]
                for _ti,_panel in enumerate(ap):
                    _col=_mc.get(_ti)
                    if _col is None or _col>=len(_slots): continue
                    _slots[_col]=_panel
                _ref=next((q for q in ap if q), None)
                _row=[q if q is not None else ts_render.spacer_panel(_ref) for q in _slots]
                _row=[q for q in _row if q is not None]
                if len(_row)==len(_slots):
                    ap=_row
                    print(f"   {b}: whole-cell row aligned over its zoom columns ({len(ap)} slots)")
            res=ts_render.assemble(ap,eff_abl,10.0,chan_labels=("Phase",fl),fluor_only=True)   # FLUOR ONLY (drop phase)
            if res: portions.append(("ablation",res[0],res[1]))
        if do_closeups and closeup_specs:
            if zp:
                zp=uniform_fluor_stretch(zp)
                res=ts_render.assemble(zp,zeff,ts_render.nice_scalebar_um(zp[0]["fluor"].shape[1]*zeff if zp and zp[0].get("fluor") is not None else 8.7),chan_labels=("Phase",fl),fluor_only=True,show_fmt=False)   # FLUOR ONLY; no fmt label on close-ups
                if res: portions.append(("ablation close-ups",res[0],res[1]))
        if mon:
            mp=[build_panel(b,"Monitoring",t,marks,sq_mon,phase_label=phase_word(txt)) for (_,t,txt,marks) in mon]
            mp=uniform_fluor_stretch(ts_render.resize_panels([p for p in mp if p],ALIGN_N))
            res=ts_render.assemble(mp,eff_mon,10.0,chan_labels=("Phase",fl),fluor_only=False)   # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")
            if res: portions.append(("monitoring",res[0],res[1]))
        if not portions: print(f"  {b}: no frames (aligned)"); return False
        return ts_render.emit(portions,out_prefix,title=title)
    if crop=="tight": crop=tight_crop(b)
    abl=[p for p in panels if p[0].lower()=="ablation"]
    mon=[p for p in panels if p[0].lower()=="monitoring"]
    mon=pad_monitoring(b,len(abl),mon)
    mon=sorted(mon,key=lambda p:p[1])   # CHRONOLOGICAL: guards against an anaphase frame being placed before
                                        # metaphase when the master event times are out of order (mislabel)
    portions=[]
    if abl:
        # T11: every ablation frame is shown on a non-flash frame (keeps laser-flash blooms off the strip)
        ap=uniform_fluor_stretch([p for p in [build_panel(b,"Ablation",t,marks,crop,disp_t=nonflash_t(b,t)) for (_,t,txt,marks) in abl] if p])
        res=ts_render.assemble(ap,pxs,10.0,chan_labels=("Phase",fl),fluor_only=True)   # FLUOR ONLY (drop phase)
        if res: portions.append(("ablation",res[0],res[1]))
    if do_closeups and closeup_specs:
        portions+=closeup_portions(b,pxs,closeup_specs)
    if mon:
        mp=uniform_fluor_stretch([p for p in [build_panel(b,"Monitoring",t,marks,crop,phase_label=phase_word(txt)) for (_,t,txt,marks) in mon] if p])
        res=ts_render.assemble(mp,pxs,10.0,chan_labels=("Phase",fl),fluor_only=False)   # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")
        if res: portions.append(("monitoring",res[0],res[1]))
    if not portions: print(f"  {b}: no frames"); return False
    # FRAME MANIFEST (2026-08-10, non-destructive). The strips are the only record of which frames a
    # published timestrip actually shows, and nothing wrote that down -- so the timestrip-setup slides
    # could not list "frames currently used" for any strip whose times are computed rather than named in
    # NF10_*. `abl`/`mon` here ARE the chosen panels, so dump them beside the figure. Read by
    # dataops/collect_timestrip_frames_20260810.py; nothing else consumes it and no pixel changes.
    try:
        import json as _json
        _man = {"batch": b, "title": title,
                "ablation":  [round(float(t), 2) for (_, t, _txt, _m) in abl],
                "monitoring":[round(float(t), 2) for (_, t, _txt, _m) in mon]}
        with open(out_prefix + "_frames.json", "w") as _f:
            _json.dump(_man, _f, indent=1)
    except Exception as _e:
        print(f"  (frame manifest not written for {b}: {_e})")
    return ts_render.emit(portions,out_prefix,title=title)

# ---- manually-drawn cell outlines (used on EVERY timestrip now, + to define the tight crop) ----
# cell_outlines.csv carries BOTH ablation-phase ('abl') and monitoring-phase ('mon') hand-drawn outlines.
co=list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ox={c:i for i,c in enumerate(co[0])}
mon_outlines=defaultdict(list); abl_outlines=defaultdict(list)
for r in co[1:]:
    ph=r[ox['phase']]
    if ph in ('mon','abl'):
        try:
            _pts=np.array(json.loads(r[ox['points']]),float)
            (abl_outlines if ph=='abl' else mon_outlines)[r[ox['batch']].strip()].append((float(r[ox['t_sec']]),_pts))
        except: pass

def outline_for(b, role, t):
    """Nearest-in-time manually-drawn outline for a frame (points in full-movie px coords).
    Prefers the frame's own role pool; falls back to the other role (both movies share the crop/ROI)."""
    same = abl_outlines.get(b,[]) if role=="Ablation" else mon_outlines.get(b,[])
    other= mon_outlines.get(b,[]) if role=="Ablation" else abl_outlines.get(b,[])
    pool = same or other
    if not pool: return None
    return min(pool,key=lambda p:abs(p[0]-t))[1]

# ── USER 2026-08-06: per-cell ROI art-direction, in MICRONS ────────────────────────────────────────
# She specifies these in µm ("move the roi ... to the right by about 25um", "lose about 3um on each side"),
# so they are stored in µm and converted per batch with that batch's own pixel size — 0.062 vs 0.031 µm/px
# batches otherwise get silently different shifts. CROP_TRIM above is fractional and stays for the two
# cells already tuned that way; anything new goes here.
#
#   key   : batch, or (batch, "Ablation"|"Monitoring") to adjust only that portion
#   value : (dx_um, dy_um, trim_um)   dx>0 moves the window RIGHT, dy>0 moves it DOWN
#                                     (image rows increase downward, so "up 5µm" is dy = -5)
#                                     trim shrinks every side by that many µm, applied AFTER the move
# PER-FRAME ROI shift, in µm. ROI_UM below moves a whole portion, which cannot express "these two
# columns only". USER 2026-08-06: "by shift the second frame, i actually mean two frames now that youve
# added some more frames - the frames labeled 21:04 and 25:04 (both phase and flour)" — i.e. first
# alignment and metaphase onset on the control, and nothing else. Applied to BOTH channel rows because the
# crop window is shared by phase and fluor, which is what she wants here.
#   {batch: [(t_from_s, t_to_s, dx_um, dy_um), ...]}
ROI_UM_FRAMES = {
    # "finally, shift down just the roi for the first frame of monitoring by 10um". The first
    # monitoring column is t=121.0 s (from this strip's frame registry), windowed tightly so the
    # other eight monitoring columns are untouched. +dy = down.
    "20250402 ptk_yfpcdc20_22": [(119.0, 123.0, 0.0, 10.0)],
    # USER 2026-08-10: "for the post frame for ablation 2 in that batch, shift the roi down about
    #  5um and to the left about 2.5um". POST of ablation 2 is t=111.0 s (the strip registry
    #  confirms the ablation row is -8.23, -5.23, 27.77, 39.0, 42.0, 111.0). Window it tightly so
    #  only that column moves. +dy = down, -dx = left.
    "20260417 ptk2 eyfp cdc20 ablation_19": [(109.0, 113.0, -2.5, 5.0)],
    "20250320 ptk_yfpcdc20__1_xy3": [(1200.0, 1560.0, 25.0, 0.0)],   # covers 21:04 (1264s) and 25:04 (1504s)
    # USER 2026-08-16, the "chromosomes hidden in the plate from metaphase onset" strip: "i need the roi for
    # the first and second monitoring frames moved up by about 25um". Its first two monitoring columns are
    # t=379.0 s and t=621.0 s (from this strip's own frame registry), each windowed tightly so the remaining
    # monitoring columns are untouched. -dy = UP. Applied AFTER the 5 um trim below, which is what creates
    # the headroom for a move this large (see NOTES item [21]: trim first, then move, then confirm the
    # BOXSIZE line reports applied == asked rather than CLAMPED).
    # MEASURED: after the 5 um trim this strip has only **3.7 um of headroom** above the monitoring box
    # (BOXSIZE reports box top y=59px). A 25 um move therefore cannot be honoured — it walks the window off
    # the frame, and the black band that produced is exactly what rule 29 forbids. Moved by the headroom
    # that actually exists instead of half-applying hers silently. To get the full 25 um the box must first
    # be trimmed much harder, which would cut into the cell.
    # CORRECTED 2026-08-17: the "chromosomes hidden in the plate from metaphase onset" strip is
    # 20260420 ptk2 eyfp cdc20 1 ablation_11, NOT four_ablation_59. Established by reading the four burned-in
    # timestamps off her artboard-5 excerpt (10:50, 17:23, 30:23, 35:23) and matching them against every
    # strip's frame registry: this batch is 3.5 s off in total, the next candidate 147 s. Her first two
    # monitoring columns are t=650 s and t=1043 s. -dy = UP.
    "20260420 ptk2 eyfp cdc20 1 ablation_11": [(648.0, 652.0, 0.0, -25.0), (1041.0, 1045.0, 0.0, -25.0)],
}


# USER 2026-08-20 (artboard 5, item 4): "the ROI for those two frames can be adjusted -- do you have
# outlines for this cell on these frames, because if so, just use that outline centroid to center the ROI on
# the cell each frame. else, for frames at the first time point 10:50, shift up the roi by approx 5 um. For
# the frames at timepoint 17.20, shift the roi up by about 20um."
# She has 10 cell outlines on this cell, so the FIRST branch applies -- her own marks, not a hand-tuned
# nudge, and it recentres EVERY column rather than the two she happened to notice.
ROI_OUTLINE_CENTRED = {"20260420 ptk2 eyfp cdc20 1 ablation_11"}
_OUTL_CENTROIDS = {}


def outline_centroid_at(b, t):
    """Her cell-outline centroid at time t, in full-frame px.

    Linearly interpolated between the two outlines that bracket t, and clamped to the nearest outline
    outside the traced range. Interpolating rather than snapping matters here: her outlines on this cell sit
    up to ~170 s from the panel times, and snapping would jump the ROI to where the cell was minutes earlier.
    Returns None if she traced no outline on this cell -- in which case the caller leaves the box alone
    rather than guessing where the cell is."""
    if b not in _OUTL_CENTROIDS:
        pts = []
        try:
            for r in csv.DictReader(open("/Volumes/4 MB/annotations/cell_outlines.csv", newline="",
                                         encoding="utf-8", errors="replace")):
                if (r.get("batch") or "").strip() != b: continue
                P = (r.get("points") or "").strip()
                if not P: continue
                try:
                    A = np.array(json.loads(P), float)
                    pts.append((float(r["t_sec"]), float(A[:, 0].mean()), float(A[:, 1].mean())))
                except Exception:
                    continue
        except Exception:
            pass
        _OUTL_CENTROIDS[b] = sorted(pts)
    P = _OUTL_CENTROIDS.get(b) or []
    if not P: return None
    t = float(t)
    if t <= P[0][0]:  return (P[0][1], P[0][2])
    if t >= P[-1][0]: return (P[-1][1], P[-1][2])
    for i in range(1, len(P)):
        if P[i][0] >= t:
            (t0, x0, y0), (t1, x1, y1) = P[i-1], P[i]
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return (x0 + f * (x1 - x0), y0 + f * (y1 - y0))
    return (P[-1][1], P[-1][2])


def recentre_on_outline(b, box, t, W=None, H=None):
    """Recentre `box` on her outline centroid for this frame, keeping its size."""
    c = outline_centroid_at(b, t)
    if c is None or not box: return box
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    nx0 = int(round(c[0] - w / 2.0)); ny0 = int(round(c[1] - h / 2.0))
    nx1, ny1 = nx0 + w, ny0 + h
    if W is not None:
        if nx0 < 0: nx1 -= nx0; nx0 = 0
        if nx1 > W: nx0 -= (nx1 - W); nx1 = W
    if H is not None:
        if ny0 < 0: ny1 -= ny0; ny0 = 0
        if ny1 > H: ny0 -= (ny1 - H); ny1 = H
    return (int(nx0), int(ny0), int(nx1), int(ny1))


def apply_roi_um_frame(b, box, t, W=None, H=None):
    """Shift `box` for THIS panel's timepoint only, leaving every other column where it is."""
    for (t0, t1, dx_um, dy_um) in ROI_UM_FRAMES.get(b, []):
        if t is not None and t0 <= float(t) <= t1:
            px = ps(b) or 0.062
            dx = int(round(dx_um / px)); dy = int(round(dy_um / px))
            x0, y0, x1, y1 = box
            x0 += dx; x1 += dx; y0 += dy; y1 += dy
            if W is not None:
                if x0 < 0: x1 -= x0; x0 = 0
                if x1 > W: x0 -= (x1 - W); x1 = W
            if H is not None:
                if y0 < 0: y1 -= y0; y0 = 0
                if y1 > H: y0 -= (y1 - H); y1 = H
            return (int(x0), int(y0), int(x1), int(y1))
    return box


ROI_UM = {
    # USER 2026-08-16, same strip: "i need the rois adjusted to take off about 5um from all sides (zoom in)".
    # (dx, dy, trim) — trim is applied per side, and apply_roi_um refuses a trim that would leave under
    # 40 px, so it degrades to no trim rather than to an unusable sliver.
    "20260420 ptk2 eyfp cdc20 1 ablation_11": (0.0, 0.0, 5.0),   # CORRECTED target, see above
    # USER 2026-08-10, off-target 20250402 ptk_yfpcdc20_22: "for the ablaion whole cell frame shift the roi up just about
    #  5um. then for the monitoring frames, shift the roi to the right about 8um." (-dy = up, +dx = right)
    ("20250402 ptk_yfpcdc20_22", "Ablation"):   (0.0, -5.0, 0.0),
    ("20250402 ptk_yfpcdc20_22", "Monitoring"): (8.0,  0.0, 0.0),
    # unmanipulated control: second set of frames right 25µm, then 3µm off each side
    # "move the roi for the SECOND SET of frames to the right by about 25um? leave others in the same
    # spot" — the 25µm move is HELD BACK pending her pointing at which columns she means. This strip is a
    # single monitoring portion, so a per-portion shift would move EVERY column, which is the opposite of
    # "leave others in the same spot"; and the panel list has since changed from 4 columns to 6
    # (NEBD -> cytokinesis), so whichever set she meant no longer sits where it did. The 3µm trim she
    # asked for IS applied.
    ("20250320 ptk_yfpcdc20__1_xy3", "Monitoring"): (0.0, 0.0, 3.0),
    ("20250320 ptk_yfpcdc20__1_xy3", "Ablation"):   (0.0, 0.0, 3.0),
    # 1-sisterless: whole-cell right 15µm, then 10µm off all sides
    "20250411 ptk_yfpcdc20_11":                     (15.0, 0.0, 10.0),
    # 1-sisterless: 10µm off all sides
    "20250930 four_ablation_59":                    (0.0,  0.0, 10.0),
    # 3-sisterless: 7µm off all sides
    "20260417 ptk2 eyfp cdc20 ablation_18":         (0.0,  0.0, 7.0),
    # double-chromosome: ablation up+right 5µm, monitoring right 5µm, then 7µm off all sides
    # USER 2026-08-10: "shift the roi up about 10um for the ablation frames and 15um for the monitoring
    #  frames", and "the whole cell frames for the ablaiton row are more zoomed out ... i like the
    #  magnification used in the monitoring rows".
    #  The shifts are RELATIVE to what she was looking at, which already carried dy -5/0, so they become
    #  -15 and -15. The trim is computed, not guessed: pre-trim the ablation box is 59.5 um and the
    #  monitoring box 43.7 um, and monitoring already trims 7.0/side -> final 29.7 um; matching that
    #  needs (59.5-29.7)/2 = 14.9 um/side on ablation. An earlier attempt put these values in a SECOND
    #  copy of these keys higher up the dict, where the later original silently won -- hence editing
    #  the originals here instead.
    # USER 2026-08-11: "shift the roi for the whole cell ablaiton frames up about 10um. same for the
    #  monitoring." Again relative to what she was looking at, which carried -15, so both become -25.
    #  2026-08-11 (third pass): "shift the roi for the whole cell frames (ablaiton and monitorign) ...
    #  up by 15um" -> -25 becomes -40 on both.
    ("20260420 ptk2 eyfp cdc20 1 ablation_71", "Ablation"):   (5.0, -40.0, 14.9),
    ("20260420 ptk2 eyfp cdc20 1 ablation_71", "Monitoring"): (5.0, -40.0,  7.0),
    # off-target: all frames left 5µm, then 10µm off all sides
    "20250901 triple_ablation_32":                  (-5.0, 0.0, 10.0),
}


def roi_um_for(b, role=None):
    """(dx_um, dy_um, trim_um) for this batch/portion, or None. A (batch, role) entry wins over a
    batch-wide one, so a cell can move its ablation and monitoring windows differently."""
    if role is not None and (b, role) in ROI_UM: return ROI_UM[(b, role)]
    return ROI_UM.get(b)


def apply_roi_um(b, box, role=None, W=None, H=None):
    """Move then shrink `box` per ROI_UM, in µm converted with this batch's pixel size.

    Shifting is clamped to the frame so a window cannot walk off the edge and start edge-padding; the trim
    is refused if it would leave less than 40 px, so an over-generous trim degrades to no trim rather than
    to an unusable sliver."""
    adj = roi_um_for(b, role)
    if not box or not adj: return box
    dx_um, dy_um, trim_um = adj
    px = ps(b) or 0.062
    dx = int(round(dx_um / px)); dy = int(round(dy_um / px)); tr = int(round(trim_um / px))
    x0, y0, x1, y1 = box
    # TRIM FIRST, then move, then clamp. The old order moved and clamped the UNTRIMMED box, so a window whose
    # pre-trim box hung off the frame was pinned at the edge even when the actual (trimmed) window had room:
    # on 20260420 ...ablation_71 the pre-trim boxes start at y=-44 and y=-109, so every "shift up" she asked
    # for was clamped away -- and even nudged back DOWN -- while the trimmed window had 196 px of frame above
    # it. Trimming first makes the clamp test the window that is actually rendered. Entries with trim=0 are
    # unaffected, and for trim>0 this can only ALLOW movement the old order wrongly refused.
    if tr and (x1 - x0) - 2 * tr >= 40 and (y1 - y0) - 2 * tr >= 40:
        x0 += tr; y0 += tr; x1 -= tr; y1 -= tr
    # ── HER RULE, 2026-08-17 ───────────────────────────────────────────────────────────────────────
    # "if i tell you to move an roi by a certain amount but you cant because of the total imaged frame,
    #  then adjust the roi otherwise (by zooming in) so that what would have been in the center after the
    #  desired roi shift is in the center after the zoom."
    # The old behaviour SLID the window back inside the frame, which silently delivered a different centre
    # from the one she asked for (on 20250930 four_ablation_59 a 25 um move had only 3.7 um of headroom, so
    # 21 um of her instruction simply vanished). Now the requested CENTRE is honoured exactly and the BOX
    # SHRINKS to the largest square centred there that still fits the frame — the shift becomes a zoom, and
    # what she wanted centred IS centred. Nothing is ever padded, so rule 29 continues to hold.
    cx = (x0 + x1) / 2.0 + dx
    cy = (y0 + y1) / 2.0 + dy
    half = min((x1 - x0), (y1 - y0)) / 2.0
    if W is not None and H is not None:
        fit = min(cx, W - cx, cy, H - cy)          # largest half-size that keeps that centre centred
        if fit < half:
            if fit >= 20:                           # a usable window remains -> zoom in around her centre
                half = fit
            else:                                   # her centre is essentially on the frame edge; fall back
                cx = min(max(cx, half), W - half)   # to sliding, which at least keeps a usable window
                cy = min(max(cy, half), H - half)
    x0, y0, x1, y1 = cx - half, cy - half, cx + half, cy + half
    return (int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1)))


_CROP_CACHE={}
# Per-cell asymmetric fine-trim of the auto crop (user art-direction). Fractions of the auto-crop
# width/height to shave off each edge: (left, top, right, bottom).
CROP_TRIM={
 "20250411 ptk_yfpcdc20_11":(0.14,0.12,0.0,0.12),        # 1-sisterless: tighter left/top/bottom, keep right
 "20250411 ptk_yfpcdc20_16_xy2":(0.12,0.0,0.12,0.14),    # control: tighter left/right/bottom, keep top
}
def tight_crop(b, apply_trim=True):
    """VERY TIGHT square crop for a whole timestrip, derived from the FIRST ablation outline (falls back to
    the first monitoring outline / the 488 channel when the ablation-phase movie is dark). The crop is CENTRED
    on the outline's centroid and sized from a ROBUST cell radius (75th-percentile point distance, so thin
    spread 'arms' are ignored and get clipped) — so the cell fills ~half the frame even for elongated cells.
    The crop side is clamped to [0.42, 0.68] x the short frame dimension. Reused for ALL frames of the batch
    (ablation + monitoring share the 1248x1056 ROI). Returns (x0,y0,x1,y1) or None.
    apply_trim=False returns the pure SQUARE box (before the per-cell asymmetric CROP_TRIM) — used by the
    square-aligned variant, which needs a genuinely square footprint for main+monitoring tiles."""
    key=(b,apply_trim)
    if key in _CROP_CACHE: return _CROP_CACHE[key]
    cand = sorted(abl_outlines.get(b,[]), key=lambda p:abs(p[0])) + sorted(mon_outlines.get(b,[]), key=lambda p:p[0])
    if not cand:
        _CROP_CACHE[key]=None; return None
    m=movie(b,"Phase","Ablation") or movie(b,"Phase","Monitoring")
    if not m: _CROP_CACHE[key]=None; return None
    cap,_=m; W=int(cap.get(3)); H=int(cap.get(4)); cap.release()
    # reference outline = first (ablation-first, then monitoring) that is COMPACT enough to represent the cell
    # body — skip frame-spanning outlines (e.g. a rough 488 trace) whose centroid mis-locates the cell.
    def compact(p): return np.ptp(p[1][:,0])<0.78*W and np.ptp(p[1][:,1])<0.78*H
    ref=next((p for p in cand if compact(p)), None) \
        or min(cand,key=lambda p:np.ptp(p[1][:,0])*np.ptp(p[1][:,1]))
    pts=ref[1]
    cx,cy=float(pts[:,0].mean()),float(pts[:,1].mean())       # centroid (robust vs bbox for spread cells)
    r=float(np.percentile(np.hypot(pts[:,0]-cx,pts[:,1]-cy),75))
    side=2.0*r*1.15                                            # cell body + small margin; far arms clip
    side=min(max(side,0.42*min(W,H)),0.68*min(W,H))           # keep it genuinely tight
    half=side/2.0
    x0=int(round(cx-half)); y0=int(round(cy-half)); x1=int(round(cx+half)); y1=int(round(cy+half))
    # shift (don't shrink) if the box runs off an edge, so it stays `side` wide
    if x0<0: x1-=x0; x0=0
    if y0<0: y1-=y0; y0=0
    if x1>W: x0-=(x1-W); x1=W
    if y1>H: y0-=(y1-H); y1=H
    x0=max(0,x0); y0=max(0,y0)
    crop=(x0,y0,x1,y1) if (x1-x0>=20 and y1-y0>=20) else None
    tr=CROP_TRIM.get(b)                                       # per-cell asymmetric fine-trim
    if apply_trim and tr and crop:
        cx0,cy0,cx1,cy1=crop; cw=cx1-cx0; ch=cy1-cy0; l,t,rr,bm=tr
        crop=(int(round(cx0+l*cw)),int(round(cy0+t*ch)),int(round(cx1-rr*cw)),int(round(cy1-bm*ch)))
    crop = apply_roi_um(b, crop, W=W, H=H)               # USER 2026-08-06 µm move/trim
    _CROP_CACHE[key]=crop; return crop

# ---- square-aligned variant (user feedback): main ablation + monitoring + zoom tiles all render at the SAME
# square footprint so the zoom row stacks in aligned columns under the main row. -----------------------------
ALIGN_N=420   # NxN page footprint for EVERY tile. =2*half*3 -> the ablation zoom stays the current 3x upscale
              # (region UNCHANGED, just bigger); the main square crop (side ~440-720px) DOWNSCALES to it (sharp).
# Per-batch TIGHT whole-cell crop: box = union outline bbox + this many microns on every side.
# Only batches listed here change; everything else keeps the union-bbox framing.
TIGHT_CROP_UM = {
    # USER 2026-08-10 asked for "about 5um on all sides" here and that shipped; on 2026-08-16 she asked for
    # "a previously-discussed zoom" on the polar strip, i.e. tighter still. 3.0 um keeps the whole cell in
    # frame (the box is the MEDIAN per-frame outline extent + 2x this margin) while cutting the empty field
    # the 5 um box still carried.
    "20250402 ptk_yfpcdc20_2": 3.0,     # user 2026-08-10 (5um) -> 2026-08-16 tighter (3um)
}
ALIGNED_MARGIN=1.0   # aligned whole-cell base tiles: cell FILLS the tile (was 1.12/~89%); user 2026-07-14
                     # "more zoomed in for both ablation and monitoring". 1.0 = union bbox exactly (no clip).
MON_USE_ABL_BOX={"20251104 ablations_17"}   # monitoring outlines on WRONG (neighbour) cell -> reuse the
                                            # ablation crop window so monitoring frames the actually-targeted cell.
def square_crop(b):
    """FIXED-physical square window (ts_render.STD_MAIN_UM = 78µm) centred on the cell's manual-outline
    centroid — so EVERY aligned ablation timestrip's main tile shows the SAME physical µm window (identical
    magnification + scale-bar length across batches, handling 0.062 vs 0.031 µm/px). Replaces the old per-cell
    bbox crop (which magnified each cell differently). One box reused for EVERY ablation + monitoring frame of
    the strip. Centroid = first ablation outline, falling back to the first monitoring outline; a frame-spanning
    rough trace is skipped in favour of a compact body outline. Clamped to the frame (78µm exceeds the 1248x1056
    0.062µm/px frame -> clamps to the 1056px/65.5µm short side, uniformly across those batches). None if the
    batch has no manual outline or no readable movie."""
    m=movie(b,"Phase","Ablation") or movie(b,"Phase","Monitoring")
    if not m: return None
    cap,cts=m; W=int(cap.get(3)); H=int(cap.get(4))
    cand=sorted(abl_outlines.get(b,[]),key=lambda p:abs(p[0]))+sorted(mon_outlines.get(b,[]),key=lambda p:p[0])
    if not cand:
        # NO manual outline (e.g. unmanipulated / colcemid / drug / mad1 cells) -> BRIGHTFIELD cell detection.
        # Detect the cell on the FIRST, MIDDLE and LAST frames and UNION the bboxes, so the ONE fixed box covers
        # the cell's whole trajectory (a drifting/migrating cell stays in-frame across every timepoint instead of
        # exiting the box on the later frames — the unmanipulated control drifts a lot). tight_square then adds
        # the breathing-room margin; crop_pad edge-pads any overflow.
        boxes=[]
        if cts is not None and len(cts):
            for k in np.unique(np.linspace(0,len(cts)-1,3).astype(int)):
                bf=grab(cap,cts,float(cts[int(k)]))
                if bf is not None: boxes.append(ts_render.brightfield_cell_bbox_pts(bf))
        cap.release()
        if not boxes: return None
        allp=np.vstack(boxes)
        pts=np.array([[allp[:,0].min(),allp[:,1].min()],[allp[:,0].max(),allp[:,1].min()],
                      [allp[:,0].max(),allp[:,1].max()],[allp[:,0].min(),allp[:,1].max()]],float)
        return apply_roi_um(b, ts_render.tight_square(pts,W,H,batch=b), W=W, H=H)
    cap.release()
    def compact(p): return np.ptp(p[1][:,0])<0.78*W and np.ptp(p[1][:,1])<0.78*H
    ref=next((p for p in cand if compact(p)),None) or min(cand,key=lambda p:np.ptp(p[1][:,0])*np.ptp(p[1][:,1]))
    _box = ts_render.tight_square(ref[1],W,H,batch=b)   # scale-before-crop window sized to THIS cell's bbox -> cell fills the frame; squared -> no distortion
    return apply_roi_um(b, _box, W=W, H=H)               # USER 2026-08-06 µm move/trim

def portion_box(b, role, times=None):
    """TRAJECTORY-FITTED square crop for ONE portion (role='Ablation'|'Monitoring'): union the cell's bbox over
    THAT portion's frames — ALL manual outlines for the role if present, else brightfield-detect on the portion's
    first/mid/last frames — then tight_square so the cell FILLS the tile (~89%). Unioning over frames means a
    cell that moves/migrates/divides (especially in monitoring) stays fully framed: no cut-off, no dead space.
    Returns None if no outline + no readable movie (caller falls back to the whole-strip square_crop)."""
    outs = abl_outlines.get(b,[]) if role=="Ablation" else mon_outlines.get(b,[])
    m = movie(b,"Phase",role) or movie(b,"Phase","Ablation") or movie(b,"Phase","Monitoring")
    if not m: return None
    cap,cts=m; W=int(cap.get(3)); H=int(cap.get(4))
    pts_all=[]
    if outs:
        for (_t,pts) in outs: pts_all.append(np.asarray(pts,float))   # union ALL outlines of this portion
    else:
        sel=[]
        if times and cts is not None and len(cts):
            ts=sorted(float(t) for t in times); sel=[ts[0],ts[len(ts)//2],ts[-1]]
        elif cts is not None and len(cts):
            sel=[float(cts[int(k)]) for k in np.unique(np.linspace(0,len(cts)-1,3).astype(int))]
        for t in sel:
            bf=grab(cap,cts,t)
            if bf is not None: pts_all.append(ts_render.brightfield_cell_bbox_pts(bf))
    cap.release()
    if not pts_all: return None
    allp=np.vstack(pts_all)
    # USER 2026-08-10: "for 1 sisterless-persistent-polar-20250402 ptk_yfpcdc20_2 timestrip, could you make
    # the crop tighter for the whole-cell frames? about 5um on all sides".
    #
    # The square is normally sized to the UNION of every outline across the portion, so a cell that travels
    # gets a box covering its whole excursion -- correct for keeping one fixed window, but on this cell it
    # leaves a lot of empty field. TIGHT_CROP_UM instead sizes the box to the union bbox PLUS a fixed margin
    # in microns on each side, which is what "about 5um on all sides" means literally. Per batch, so no other
    # strip's framing moves.
    _tight = TIGHT_CROP_UM.get(b)
    if _tight is not None:
        # "TIGHTER, about 5um on all sides" = around the CELL, not around its whole journey. Padding the
        # union bbox made the box LOOSER, which is the opposite of what she asked: the union already spans
        # every position the cell visits in this portion, so on a cell that travels it is far larger than the
        # cell. The side is therefore the MEDIAN per-frame outline extent + 2*margin, centred on the union
        # centre -- one fixed window (so magnification is still constant across the strip, which the aligned
        # layout requires) but sized to the cell rather than to its excursion.
        _pad = _tight / ps(b)
        _ext = [max(a[:,0].max()-a[:,0].min(), a[:,1].max()-a[:,1].min()) for a in pts_all]
        _side = float(np.median(_ext)) + 2.0*_pad
        _cx = (allp[:,0].min()+allp[:,0].max())/2.0
        _cy = (allp[:,1].min()+allp[:,1].max())/2.0
        _h = _side/2.0
        corners=np.array([[_cx-_h,_cy-_h],[_cx+_h,_cy-_h],[_cx+_h,_cy+_h],[_cx-_h,_cy+_h]],float)
        print(f"   {b}: tight crop {_side*ps(b):.1f} um "
              f"(cell {np.median(_ext)*ps(b):.1f} um + {_tight:.0f} um each side)")
    else:
        corners=np.array([[allp[:,0].min(),allp[:,1].min()],[allp[:,0].max(),allp[:,1].min()],
                          [allp[:,0].max(),allp[:,1].max()],[allp[:,0].min(),allp[:,1].max()]],float)
    # ALIGNED whole-cell tiles: tighter margin than the 1.12 default so the cell FILLS the tile more (user
    # 2026-07-14: "whole-cell frames can be more zoomed in for both ablation and monitoring" — 2/3-sisterless,
    # double-chromosome, off-target, etc). 1.0 = the union bbox exactly (max zoom w/o clipping; union already
    # frames the cell across the whole portion trajectory, so no single frame is cut off).
    _box = ts_render.tight_square(corners,W,H,batch=b,margin=ALIGNED_MARGIN)
    _after = apply_roi_um(b, _box, role=role, W=W, H=H)
    _req = (roi_um_for(b, role) or (0.0, 0.0, 0.0))[1]
    _tr_px = (roi_um_for(b, role) or (0.0, 0.0, 0.0))[2] / (ps(b) or 0.062)
    _got = (_after[1] - _box[1] - _tr_px) * (ps(b) or 0.062)   # isolate the shift from the trim
    print(f"   BOXSIZE {b} role={role}: {(_box[2]-_box[0])*ps(b):.1f} -> {(_after[2]-_after[0])*ps(b):.1f} um; "
          f"box top y={_box[1]:.0f}px (headroom above = {max(0.0,_box[1])*ps(b):.1f} um); "
          f"dy asked {_req:+.1f} um, applied {_got:+.1f} um"
          + ("   <== CLAMPED at the frame edge" if abs(_got-_req) > 0.6 else ""))
    return apply_roi_um(b, _box, role=role, W=W, H=H)   # USER 2026-08-06 per-portion µm move/trim

# USER 2026-08-10: "in the zoom ablation row, you repeat 13 twice, and just this one special time, we're
# going to manually modify the set of frames in this zoom row to take out one of the ons from 13s (it doesnt
# matter which, theyre the same)."
# Cause: with two targets the zoom row is target1(before,marked,after) + target2(before,marked,after), and
# here target1's AFTER and target2's BEFORE are the same frame (13 s) -- so the same image appears twice.
# Per batch, and only for the batches listed, a panel whose timestamp equals the previous kept panel's is
# dropped. Deliberately NOT global: on other strips two targets sharing a frame is worth showing twice,
# once per target.
ZOOM_DEDUP_T = {"20260420 ptk2 eyfp cdc20 1 ablation_71"}

# USER 2026-08-16: "for on-target ablation timestrips, what we're going to try now is that for the whole-cell
# row for the ablation portion, just include the whole-cell frame ONCE per ablation and put a little box on
# it to show where the zoom-in frame looks at ... so wont be an additional change for single ablation
# timestrips but will be for double or triple, etc." She called it "what we're going to try", so it is a
# switch: flip it off to get the old before/marker/after whole-cell row back. It only affects the ON-TARGET
# branch (the one with KT markers); off-target strips render no zoom row at all and are untouched.
ONE_PANEL_PER_ABL = True

# PER-ZOOM-PANEL ROI nudge, microns: {batch: {(target_index, slot_index): (dx_um, dy_um)}}
# slot_index 0=before, 1=marked, 2=after; +dx right, +dy down.
# USER 2026-08-11: "for the 2-sisterless aligned, can you move the roi for the last zoom frame of ablation
# (not whole cell) down about 5um". The zoom crop is centred per TARGET, so every existing knob would have
# moved all three of that target's columns; this addresses one column.
# 2-sisterless is ablation_19 with 2 targets -> 6 zoom columns, so the LAST is target 1, slot 2 (its "after",
# the 1:51 frame).
ZOOM_PANEL_SHIFT_UM = {
    "20260417 ptk2 eyfp cdc20 ablation_19": {(1, 2): (0.0, 5.0)},
}

def aligned_closeup_panels(b, specs, N=ALIGN_N, half=70):
    """Flat list of ZOOM panels (before/marked/after per target, in the same order as the ablation row) each
    resampled to NxN. The displayed REGION is UNCHANGED (the same 2*half box already used) — only upscaled so it
    fills the same square footprint as the main tiles. Returns (panels, eff_pxs) with eff_pxs = the per-pixel
    size of an N-tile (for the 2 µm scale bar)."""
    if not specs: return [],None
    box=2*half
    _zsh = ZOOM_PANEL_SHIFT_UM.get(b, {})
    def zbox(fr,x,y,mark,ti=None,pi=None):
        _d = _zsh.get((ti,pi))
        if _d:
            _px = ps(b) or 0.062
            x = x + _d[0]/_px; y = y + _d[1]/_px
        xi,yi=int(round(x)),int(round(y)); h,wd=fr.shape[:2]
        x0,y0=xi-half,yi-half
        # NOTES §1 rule 29 (user 2026-08-16): "you have a black bar taking up space in the frame instead of
        # having it be the whole image ... you should be able to take some off of the side of the frame to
        # both achieve the crop i want and restore proportions so the black bar isnt needed." The old code
        # pasted a partial crop onto a ZEROS canvas, so a box overhanging the frame edge printed a black
        # band. Instead SLIDE the box back inside the frame: same box size, same magnification, slightly
        # recentred, no fill. Only if the frame is genuinely smaller than the box does anything get padded,
        # and then it is trimmed to the frame rather than filled.
        if wd >= box and h >= box:
            x0 = min(max(0, x0), wd - box); y0 = min(max(0, y0), h - box)
            canvas = fr[y0:y0+box, x0:x0+box].copy()
        else:                                                # frame smaller than the box: trim, don't fill
            x0 = max(0, min(x0, max(0, wd - box))); y0 = max(0, min(y0, max(0, h - box)))
            canvas = fr[y0:min(h, y0+box), x0:min(wd, x0+box)].copy()
        if canvas.size == 0: return None
        # the mark is no longer guaranteed to sit at the tile centre once the box has been clamped
        # USER 2026-08-19 (all-figures item 6): "The instructions i told you to implement on ablation
        # timestrips re: the box on whole-cell frames and using x markers for ablation instead of circles:
        # not implemented consistently across all applicable timestrips on all boards."
        # THIS was the inconsistency: the whole-cell row was switched to the X on 2026-08-17 (draw_marks
        # below), but the ZOOM row is built here, not through draw_marks, and kept the old circle -- so a
        # single strip showed an X on top and a circle underneath. Same helper for both now.
        if mark: ts_render.draw_x(canvas,xi-x0,yi-y0,r=max(4,int(round(9*box/140.0))))
        return cv2.resize(canvas,(N,N),interpolation=cv2.INTER_NEAREST)
    T=len(specs)
    grid=[[{"t":None,"phase":None,"fluor":None} for _ in range(3)] for _ in range(T)]
    for ch in ("Phase","Fluor"):
        m=movie(b,ch,"Ablation")
        if not m: continue
        cap,ts=m; key="phase" if ch=="Phase" else "fluor"
        for ti,(tb,tm,ta,x,y) in enumerate(specs):
            for pi,(_req,tt,mk) in enumerate(((tb,nonflash_t(b,tb),False),(tm,nonflash_t(b,tm),True),
                                              (ta,nonflash_t(b,ta),False))):
                fr=phase_frame(b,"Ablation",cap,ts,tt) if ch=="Phase" else grab(cap,ts,tt)
                # NF10_LABEL_SHIFT: the zoom row is built HERE, not through build_panel, so without this
                # the close-ups keep the raw clock while the whole-cell row above them is relabelled
                # (ablation_13: whole-cell -0:18/-0:06/0:27 over zooms reading 0:24/0:36/1:09).
                # Label with the REQUESTED time (`_req`), not the fetched non-flash frame (`tt`): the
                # whole-cell row above labels the requested time, so using `tt` here printed -0:06/-0:03
                # under a row reading -0:05/-0:02 for the very same frames (seen on two_sisterless_14).
                grid[ti][pi]["t"]=_req+NF10_LABEL_SHIFT.get(b,0.0)
                if fr is not None:
                    z=zbox(fr,x,y,mk,ti,pi)
                    if z is not None: grid[ti][pi][key]=z
        cap.release()
    panels=[grid[ti][pi] for ti in range(T) for pi in range(3)
            if grid[ti][pi]["phase"] is not None or grid[ti][pi]["fluor"] is not None]
    if b in ZOOM_DEDUP_T:
        _ded=[]
        for _p in panels:
            if _ded and _p.get("t") is not None and _ded[-1].get("t") is not None \
               and abs(float(_p["t"])-float(_ded[-1]["t"]))<0.5:
                print(f"   {b}: zoom row - dropped duplicate column at {_p['t']:.0f}s")
                continue
            _ded.append(_p)
        panels=_ded
    # USER 2026-08-19 (all-figures item 3): the whole-cell row has to sit above the zoom frame whose
    # TIMEPOINT it matches. Return, for each target, the index of its MARKED zoom column (the shot frame --
    # the same frame the whole-cell tile shows), so `make_strip` can build the row above at the zoom row's
    # column count with the whole-cell tile in exactly that slot. Computed from the panels that SURVIVED
    # (a missing frame or a ZOOM_DEDUP_T drop changes the column count), never assumed to be 3 per target.
    marked_col = {}
    _seen = {}
    for _idx, _pn in enumerate(panels):
        _key = id(_pn)
        for _ti in range(T):
            for _pi in range(3):
                if grid[_ti][_pi] is _pn:
                    _seen[(_ti, _pi)] = _idx
    for _ti in range(T):
        if (_ti, 1) in _seen:      # the middle panel of the triple is the marked/ablation frame
            marked_col[_ti] = _seen[(_ti, 1)]
        else:                      # marked frame missing -> fall back to that target's first surviving column
            _c = [_seen[(_ti, _pi)] for _pi in range(3) if (_ti, _pi) in _seen]
            if _c: marked_col[_ti] = _c[0]
    eff_pxs=ps(b)*box/N
    return panels, eff_pxs, {"n_cols": len(panels), "marked_col": marked_col}

_ABLTS={}
def abl_ts(b):
    """cached t_sec array of the ablation frames, for before/after neighbour lookup.

    2026-08-06: this read the timestamps out of the Phase_Ablation MOVIE, so any batch whose movie is an
    empty stub returned None — and frame_before/frame_after then silently returned the SAME time they were
    given. On 20250411 that made the ablation "before" panel identical to the marker frame even though four
    real frames precede it (-14.4, -11.4, -8.4, -5.4 s), which is what produced the duplicated column.
    frames.json records the same timestamps and does not depend on the movie encoding, so fall back to it."""
    if b in _ABLTS: return _ABLTS[b]
    m=movie(b,"Phase","Ablation"); ts=m[1] if m else None
    if m: m[0].release()
    if ts is None or len(ts)==0:
        rt=role_ts(b,"Ablation")
        ts=np.asarray(rt,float) if rt else None
    _ABLTS[b]=ts; return ts
def frame_before(b,t):
    ts=abl_ts(b)
    if ts is None or len(ts)==0: return t
    i=int(np.argmin(np.abs(ts-t))); return float(ts[max(0,i-1)])
def frame_after(b,t):
    ts=abl_ts(b)
    if ts is None or len(ts)==0: return t
    i=int(np.argmin(np.abs(ts-t))); return float(ts[min(len(ts)-1,i+1)])

# ---- KT ablation markers (pre/post) — frames the before/after-ablation KT markers were placed on ----
_kt=list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv"))); _kx={c:i for i,c in enumerate(_kt[0])}
KT_MARKS=defaultdict(lambda:defaultdict(list))
for _r in _kt[1:]:
    _lab=_r[_kx['label']].strip()
    if _lab in ("pre_abl","post_abl"):
        try: KT_MARKS[_r[_kx['batch']].strip()][_lab].append((float(_r[_kx['t_sec']]),float(_r[_kx['x']]),float(_r[_kx['y']])))
        except: pass
GREEN=(80,235,80)

def role_ts(b, role):
    """sorted t_sec array of the movie frames for a role ('Ablation'/'Monitoring'), from frames.json."""
    fj=fjson(b)
    if not fj: return []
    r='ablation' if role=='Ablation' else 'monitoring'
    return sorted(f['t_sec'] for f in fj.get('frames',[]) if f.get('role')==r)
# ── USER 2026-08-06: keep the duplicated "before" frame so the whole-cell row matches the zoom ────
# When the ablation lands on the FIRST ablation frame, frame_before() returns that same frame, and
# dedup_frames drops the unmarked "before" panel as a repeat. The ZOOM row is built from `specs`, which is
# never deduped, so it kept all three. Result: whole-cell 2 panels vs zoom 3, which is what she saw on
# 20250411 ("just make the first frame repeat twice and mark the second one" — so the rows align).
# Listed per batch rather than changed globally: for every other cell the dedup is doing its job.
KEEP_DUP_BEFORE = {"20250411 ptk_yfpcdc20_11",
                   # NF10 2026-08-06: ablation_11 is the same case — its KT marker sits at -1.9 s, before
                   # the FIRST ablation frame (its Pre movies are 258-byte stubs), so no earlier frame
                   # exists and the unmarked "before" panel was dropped as a repeat, leaving a 2-panel
                   # whole-cell row under a 3-panel zoom row.
                   "20260420 ptk2 eyfp cdc20 1 ablation_11"}

# Cells whose monitoring row should run NEBD -> cytokinesis at ~5 min spacing (her 2026-08-06 request for
# the single-ablation strips, matching how thoroughly the 3-sisterless strip covers that window).
DENSE_MONITORING = {"20250930 four_ablation_59", "20250411 ptk_yfpcdc20_11",
                    "20260417 ptk2 eyfp cdc20 ablation_18"}
DENSE_STEP_S = 300.0

# ── USER 2026-08-06: alternate ablation-frame choices, rendered as separate versions ───────────────
# On the 3-sisterless strip "you use the frame at 0:21 twice in the zoom versions, once as the follow-up
# frame after the first ablation and again as the frame of ablation for the second ablation" — true: abl1's
# AFTER and abl2's MARKER both resolve to t=21.4 s. She asked for three versions that break the tie in
# different ways. Overrides are keyed (target_index, slot) with slot in {before, marker, after}; the value
# is an absolute time in seconds on the ablation clock.
NF9_VARIANTS = {
    "20260417 ptk2 eyfp cdc20 ablation_18": {
        "v1": {(0, "after"):  15.0},                         # 0:15 as abl1's follow-up
        "v2": {(0, "after"):  12.0},                         # 0:12 as abl1's follow-up
        "v3": {(1, "before"): 24.0, (1, "marker"): 27.0},     # 0:24 / 0:27 for abl2's pre + marked frames
    },
}



# ===== NF10 (user 2026-08-06): six strips she specified frame-by-frame ==============================
# "ive given you, for many frames that are part of the build, specific time points to retrieve them
# from, so you dont have to do this yourself. else build as normal."
# Every time below is HER number, on the clock that batch's frames.json actually uses - verified per
# batch before being written here (ablation_13 is the one whose ablation movie is NOT zeroed on the
# shot: its ablation lands at t=42 s, which is exactly why she asked for the -42 s label shift).

# batch -> {(target_index, slot): absolute time on that batch's ablation clock}. slot in before/marker/after.
NF10_ABL_TIMES = {
    # USER 2026-08-10: "i need to change the frames we pick for ablation 2. pre will be 39 seconds,
    #  marked will be 42s, and post can be 1:51". Ablation 2 => index 1. The clip runs -20..115 s on a
    #  3 s grid offset by 0.8 s, so these land on the frames at 39.8 / 42.8 / 111.8 s.
    "20260417 ptk2 eyfp cdc20 ablation_19": {(1, "before"): 39.0, (1, "marker"): 42.0, (1, "after"): 111.0},
    # "Use 00:00:24 for pre and 00:00:36 for labeling, and 00:01:09 for post. BUT, label these as if the
    #  ablation frame (00:00:42) is 0s, so the labeled frame will be -3s, and so on."
    # MARKER = 39.0, not 36.0. Her three numbers cannot all hold at once, and the data says which one slipped:
    # the laser flash is at t_sec 42.0 (mean-brightness spike, idx 14) so "ablation frame = 00:00:42" is
    # right, and the frame reading -3 s on that clock is 39.0, not 36.0 (which reads -6). Her stated OUTPUT
    # (-3s) and her stated ablation time both point at 39; only the "00:00:36" input is off by one frame.
    # It also matches how she specified every other strip - metaphase_82 marks -5 s with the shot at 0, i.e.
    # she marks the LAST FRAME BEFORE the shot. Do not "flag" this back to her; it is answered.
    "20260420 ptk2 eyfp cdc20 1 ablation_13": {(0, "before"): 24.0, (0, "marker"): 39.0, (0, "after"): 69.0},
    # "for ablation frames use -11s for pre, -5 for marking the ablation, and 18s for after."
    "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_82": {(0, "before"): -11.0, (0, "marker"): -5.0, (0, "after"): 18.0},
    # "for ablation 1 frames use -5s for pre, -2 for marking, and 00:00:36 for after. for ablation 2
    #  frames use 45s for pre, 48s for marking, and 00:01:00 for after."
    "20260108 two_sisterless_kinetochores_14": {(0, "before"): -5.0, (0, "marker"): -2.0, (0, "after"): 36.0,
                                                (1, "before"): 45.0, (1, "marker"): 48.0, (1, "after"): 60.0},
    # --- second batch, user 2026-08-06 ---
    # "persistent polar ... use -6s for pre, -3 for marking the ablation, and 17s for after"
    "20250402 ptk_yfpcdc20_2":  {(0, "before"): -6.0, (0, "marker"): -3.0, (0, "after"): 17.0},
    # "persistent polar ... -6s for pre, -3 for marking the ablation, and 32s for after"
    "20250402 ptk_yfpcdc20_7":  {(0, "before"): -6.0, (0, "marker"): -3.0, (0, "after"): 32.0},
    # "completely switching poles, for supplemental ... -5s for pre, -2 for marking, and 15s as the after"
    "20250417 ptk_yfpcdc20_3":  {(0, "before"): -5.0, (0, "marker"): -2.0, (0, "after"): 15.0},
    # "the off-target timestrip (so all ablations, put them on -3s). Use -6s for pre and 14s for post."
    # This batch has NO manual KT marks and 2 PAS events, so it takes the marker-less branch, which draws
    # EVERY site on the single marker frame — which is exactly "all ablations, put them on -3s".
    "20250402 ptk_yfpcdc20_22": {(0, "before"): -6.0, (0, "marker"): -3.0, (0, "after"): 14.0},
}

# How many ablation targets to draw close-ups for. metaphase_82 has NO manual KT marks but 4 PAS events at
# essentially one site, so the marker-less code path would emit 4 near-identical zooms; she specified one.
NF10_MAX_TARGETS = {"20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_82": 1}

# Explicit monitoring frames, used INSTEAD of the automatic selection. (time, label-or-None).
NF10_MON_TIMES = {
    # USER 2026-08-20 (artboard 5, item 5): "There are three sets of 'main' timestrips on this board ... One
    # strip has many more frames than the others so increase the number of frames in the other 2 to match
    # the number of frames of the currently long one. Add frames from between metaphase onset to anaphase
    # onset (maybe one additional one from prometaphase if desired)."
    # The long one is `nf9_1-sisterless__20250411_ptk_yfpcdc20_11` at 7 monitoring columns; this strip had 4.
    # Her existing four are kept exactly (10:49 prometaphase, 17:20 = metaphase onset, 30:23 = anaphase
    # onset, 35:23 after). The three added sit BETWEEN metaphase and anaphase onset as she asked, chosen as
    # the real monitoring frames nearest even thirds of that window (30 frames were available there).
    "20260420 ptk2 eyfp cdc20 1 ablation_11":
        [(649.0, None), (1040.0, None), (1240.0, None), (1471.0, None),
         (1631.0, None), (1823.0, None), (2123.0, None)],
    # "Use frames for monitoring at 00:03:35, 00:05:43, 00:06:15, 00:09:26, Last frame at 00:12:06."
    "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_82":
        [(215.0, None), (343.0, None), (375.0, None), (566.0, None), (726.0, None)],
    # "use 00:02:01 as first congression, 00:18:21 as start of metaphase, 00:29:21 as anaphase onset, and
    #  just have 34:21 be the last frame ... include some additional frames between events so there arent
    #  any gaps larger than 5 mins (no need to include an additional one between anaphase and the end frame)".
    # Her event times, NOT the master's (the master has metaphase 21:01 / anaphase 32:01 for this batch);
    # fills at 300 s keep every inter-event gap under 5 min, and the anaphase->end gap is deliberately open.
    # USER 2026-08-16: "the off-target - 20250402 ptk_yfpcdc20_22 has too many monitoring frames. cut out
    # 29:21, and 12:01-18:21." Her three named times land exactly on entries below, so the range is
    # inclusive of its endpoints: 721.0 (12:01), 1021.0 (17:01), 1101.0 (18:21) and 1761.0 (29:21) go.
    # NOTE, deliberate: that removes the two EVENT-labelled panels her 2026-08-10 spec asked for
    # (metaphase 18:21, anaphase 29:21). The labels are NOT moved onto neighbouring frames -- 23:21 is not
    # when metaphase started, and a label naming a time that is not the event would be wrong data. The
    # newer instruction wins; the strip simply no longer carries those two markers.
    # USER 2026-08-19 (all-figures item 13): "Include one or two more frames (covering the big time gap of
    # 7-23 mins) in the monitoring timestrip for the off-target timestrip."
    # Her 2026-08-16 instruction had cut 12:01-18:21 out of this strip, which is what OPENED that 16-minute
    # hole. Both instructions are honoured: the two new frames sit in the gap but OUTSIDE the window she
    # deleted -- 09:31 (between 07:01 and the 12:01 cut) and 20:51 (between the 18:21 cut and 23:21). The
    # largest remaining gap on the strip drops from 16.3 min to 5.0 min.
    "20250402 ptk_yfpcdc20_22":
        [(121.0, "first congression"), (421.0, None), (571.0, None), (1251.0, None),
         (1401.0, None), (1701.0, None), (2061.0, None)],
    # USER 2026-08-16: "for the 1-sisterless-persistent-polar timestrip back on artboard 1, add a few more
    # frames of monitoring." It had only FOUR, from the automatic sparse branch (prometaphase / metaphase /
    # anaphase / +5min), leaving two ~10-minute holes: ablation(+17s) -> prometaphase(10:54), and
    # prometaphase -> metaphase(21:11). Three fills at ~5-minute spacing close both while keeping her four
    # event panels exactly where they were.
    "20250402 ptk_yfpcdc20_2":
        [(300.0, None), (653.8, "prometaphase"), (950.0, None), (1271.0, "metaphase"),
         (1430.0, None), (1586.0, "anaphase"), (1886.0, "+5min")],
}

# A final monitoring frame she named explicitly; anything later is dropped so the strip ends there.
NF10_MON_LAST = {
    "20260420 ptk2 eyfp cdc20 1 ablation_13": (2599.0, "cytokinesis"),   # "No cytokinesis event time
                                                                          # specified so use the frame at
                                                                          # original time 00:43:19"
    "20260108 two_sisterless_kinetochores_14": (3564.0, None),            # "Last frame 00:59:24."
}

# Shift applied to every TIMESTAMP DRAWN on the strip (not to which frame is fetched). ablation_13:
# "label these as if the ablation frame (00:00:42) is 0s ... and then for the monitoring movie timestamps
# ... subtract 42s so theyre on the same time adjustment as the ablation frames".
NF10_LABEL_SHIFT = {"20260420 ptk2 eyfp cdc20 1 ablation_13": -42.0}

# Fluorescence-ONLY lagging strips: "for the ones i specify as for lagging, just make a flourescence
# timestrip, and just with the frames i specify."

# 2026-08-16: `_hms(minutes)` multiplies its argument by 60. Every call in this module passes a t_sec,
# so the burned label read the SECONDS as MINUTES -- the persistent-polar strip showed "metaphase 1271:00"
# where 1271 s is 21:11. All 20 call sites here take seconds, so they go through this converter instead.
def _hms(t_sec):
    return lib.mmss(float(t_sec) / 60.0)

NF10_LAGGING = [
    ("lagging-fractured", "20260108 two_sisterless_kinetochores_14",
     ("list", [3003.3, 3183.2, 3363.2, 3564.1, 3744.1, 3924.1, 4143.2, 4323.2, 4503.2, 4567.1, 4571.8, 4577.3])),            # "Just fluorescence of Frames 01:02:03 through 01:16:13"
    # USER 2026-08-20 (artboard 5, item 3): "could you add one frame of the cell in metaphase and then the
    # frame of anaphase onset, and then maybe one more thats halfway between the frame at anaphase onset and
    # the current first frame of the strip", and item 8.1: "mirror the frame pattern of this fractured
    # lagging timestrip when adding frames".
    #   metaphase      -> 175.3 s. Master gives Metaphase Start 00:00:31, but the cell's FIRST monitoring
    #                     frame is 175.3 s, which is inside metaphase (31 s -> anaphase 663 s). Snapped to a
    #                     real frame rather than inventing one.
    #   anaphase onset -> 663.1 s (master 00:11:03, exact frame present)
    #   halfway        -> 792.8 s, midway between anaphase onset and her original first frame (922.0)
    # The result mirrors the fractured strip's shape: spaced frames leading in, then her tight cluster on
    # the stretch-and-rebound itself.
    ("lagging-stretch-rebound", "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52",
     ("list", [175.3, 663.1, 792.8, 922.0, 954.0, 987.0, 1019.0])),   # was the last four only

    # USER 2026-08-16: "id like a few more options to choose from so generate a few more of these."
    # There was no candidate POOL — only the two hand-specified entries above — so one was built: all 33
    # cells carrying `lagging` traces in kt_outlines, ranked by trace count and by continuity (traced
    # frames / frame span), which is what makes a stretch-and-rebound readable. These are the top five with
    # a recorded anaphase; each window is that cell's own first-to-last lagging trace, in t_sec.
    # CANDIDATES ONLY — she picks one and the rest come off the board.
    # 12 EVENLY-SPACED frames each, not the whole range: the richest cell has 203 traced timepoints and a
    # strip of 203 panels is unreadable (and was I/O-bound slow to render off the exFAT drive). Twelve
    # matches the density of her own hand-specified entries and still shows stretch and rebound.
    ("lagging-cand-triple_ablation_26",   "20251029 triple_ablation_26",
     ("list", [992.9, 1440.0, 1835.5, 2254.7, 2648.3, 3040.3, 3586.5, 3979.5, 4434.1, 5712.0, 6101.0, 6533.7])),    # 215 traces, continuity 0.80 — much the richest
    ("lagging-cand-four_ablation_23",     "20250929 four_ablation_23",
     ("list", [1291.0, 1451.0, 1631.1, 1831.0, 2051.1, 2210.9, 2457.8, 2597.9, 2737.8, 2877.8, 3017.8, 3157.8])),   # 129 traces, continuity 0.80
    ("lagging-cand-two_sisterless_14",    "20260108 two_sisterless_kinetochores_14",
     ("list", [3003.3, 3183.2, 3363.2, 3564.1, 3744.1, 3924.1, 4143.2, 4323.2, 4503.2, 4567.1, 4571.8, 4577.3])),   # 85 traces, continuity 1.00 — every frame traced
    ("lagging-cand-four_ablation_59",     "20250930 four_ablation_59",
     ("list", [1537.1, 1658.6, 1810.1, 1961.9, 2112.8, 2263.3, 2413.3, 2563.7, 2714.2, 2895.3, 3046.6, 3198.0])),   # 66 traces, continuity 0.98
    ("lagging-cand-single_ablation_15",   "20260416 single ablation_15",
     ("list", [1126.4, 1266.4, 1366.4, 1546.3, 1646.4, 1746.4, 1846.3, 1946.3, 2046.3, 2146.3, 2246.3, 2346.4])),   # 90 traces, continuity 0.89
]

# Ablation strips she named. ablation_11 gets NO explicit frames -> "build as a normal ablation timestrip".
NF10_CELLS = [
    ("1-sisterless",            "20260420 ptk2 eyfp cdc20 1 ablation_11"),
    ("1-sisterless-congressing", "20260420 ptk2 eyfp cdc20 1 ablation_13"),
    ("metaphase-ablation",      "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_82"),
    ("2-sisterless",            "20260108 two_sisterless_kinetochores_14"),
    # --- second batch, user 2026-08-06 ---
    ("1-sisterless-persistent-polar", "20250402 ptk_yfpcdc20_2"),
    ("1-sisterless-persistent-polar", "20250402 ptk_yfpcdc20_7"),
    ("1-sisterless-pole-switch",      "20250417 ptk_yfpcdc20_3"),
    ("off-target",                    "20250402 ptk_yfpcdc20_22"),
    # --- 2026-08-09: the outstanding backlog item "build timestrip for 20250925 triple_ablation_13
    # (chromosome flips pole to pole)". Filed under pole-switch because that is exactly the behaviour,
    # and the 3-sisterless prefix keeps it distinct from the 1-sisterless pole-switch strip above.
    # Master confirms: # Sisterless KTs = 3, Metaphase 00:06:56, Anaphase 00:43:16, render dir present.
    ("3-sisterless-pole-switch",      "20250925 triple_ablation_13"),
]


def variant_override(b, i, slot, default):
    """The time she specified for target i's `slot`, else the active VARIANT's, else `default`.

    NF10 times are NOT env-guarded: they are the frames she chose for these strips, so they apply on every
    render of that batch, not only under a VARIANT."""
    _nf10 = NF10_ABL_TIMES.get(b, {})
    if (i, slot) in _nf10: return float(_nf10[(i, slot)])
    v = os.environ.get("VARIANT", "")
    if not v: return default
    return NF9_VARIANTS.get(b, {}).get(v, {}).get((i, slot), default)

# ALT_BEFORE: render a SECOND version of a strip whose ablation "before" panel is a genuinely earlier
# frame instead of a repeat of the marker frame. Her v2 request for the same cell: "instead of showing the
# same frame of -0:02 twice, you show first a frame before that, then -0:02 marked with the ablation, and
# then 0:46". `n` is how many ablation frames to step back.
ALT_BEFORE_STEPS = {"20250411 ptk_yfpcdc20_11": 1}


def frame_back(b, t, n=1):
    """The ablation frame n steps before t (clamped at the start of the movie)."""
    ts = abl_ts(b)
    if ts is None or len(ts) == 0: return t
    i = int(np.argmin(np.abs(ts - t)))
    return float(ts[max(0, i - n)])


def dedup_frames(b, role, panels, keep_marked=True):
    """2026-07-13: drop panels that resolve to the SAME nearest movie frame as another — kills the 'same frame
    shown many times' repeats (sparse monitoring, before==marker when the ablation is on the first frame). A
    MARKED (ablation-✕) panel wins its frame, so an unmarked 'before' sharing the marker's frame is dropped, not
    the marker. Display order preserved."""
    if role == "Ablation" and b in KEEP_DUP_BEFORE:
        return panels                      # deliberate duplicate so the rows align (see KEEP_DUP_BEFORE)
    ts=role_ts(b,role)
    if not ts: return panels
    ta=np.asarray(ts)
    def fidx(p): return int(np.argmin(np.abs(ta-p[1])))
    marked_frames={fidx(p) for p in panels if keep_marked and len(p)>3 and p[3]}
    kept=[]; used=set()
    for p in panels:
        fi=fidx(p); marked=keep_marked and len(p)>3 and p[3]
        if marked:
            if fi not in used: kept.append(p); used.add(fi)
            continue
        if fi in used or fi in marked_frames: continue   # unmarked frame already taken (or owned by a marker)
        kept.append(p); used.add(fi)
    return kept
def uniform_fluor_stretch(panels):
    """2026-07-13: UNIFORM per-portion contrast stretch on the fluor row — ONE percentile mapping ([p2,p99.5] of
    the pooled fluor pixels) applied to EVERY frame of the portion (honors 'uniform brightness/contrast per
    strip-type', no per-frame auto-normalization). Normalizes over-bright/saturated AND dim fluor consistently."""
    fls=[p['fluor'] for p in panels if p and p.get('fluor') is not None]
    if len(fls)<1: return panels
    g=np.concatenate([(f.max(2) if f.ndim==3 else f).reshape(-1) for f in fls]).astype(np.float32)
    gp=g[g>2]
    if gp.size<50: return panels
    lo=float(np.percentile(gp,2)); med=float(np.percentile(gp,50)); hi=float(np.percentile(gp,99.5))
    if hi-lo<8: return panels
    # 2026-07-13 CONSERVATIVE: only touch clearly-bad exposure; leave good frames AND noise-only frames alone
    # (a naive [p2,p99.5] stretch amplified pure-noise low-signal fluor, e.g. noc_washout, to full-green noise).
    over_bright = med>110                       # predominantly bright/saturated -> pull it down
    dim_signal  = (hi > 3.0*max(1.0,med)) and hi>25   # a real bright tail (puncta/cell) exists, worth revealing
    if not (over_bright or dim_signal): return panels
    sc=min(255.0/(hi-lo), 2.5)                  # cap gain so a low-SNR frame can't be blown up
    for p in panels:
        if p and p.get('fluor') is not None:
            p['fluor']=np.clip((p['fluor'].astype(np.float32)-lo)*sc,0,255).astype(np.uint8)
    return panels

# ===== category strips =====
dbl=lib.double_chromosome_batches()
# Monitoring frames to OMIT from a specific cell's strip, batch -> [t_sec]. Her call, per figure; kept as a
# declared table so the reason is visible and the drop survives every re-render.
DROP_MON_T = {
    "20250930 four_ablation_59": [2779.0, 3079.0],   # 46:19 and 51:19 -- her 2026-08-20 artboard-9 note
}


def cat_panels(b):
    """Pre/post panels use the actual KT-marker frames (green KT circle); a middle 'ablation'
    panel adds the red ablation-event mark. If no KT markers (e.g. off-target), fall back to the
    ablation-movie portion so the ablation is still shown. Then monitoring metaphase/anaphase."""
    # S3/S4: for EACH ablation, duplicate the ablation frame — first clean, second with the
    # ablation marker drawn ONLY on that copy (and only this ablation's target); the post-ablation
    # frame carries NO marker. S7: monitoring runs through anaphase + 5 min.
    MAGENTA=(255,0,255)   # was MAGENTA; see rule 30
    pre=sorted(KT_MARKS[b].get("pre_abl",[])); post=sorted(KT_MARKS[b].get("post_abl",[])); pan=[]; specs=[]
    w=abl_window(b)
    if w and pre:   # drop stray KT annotations placed OUTSIDE the ablation movie (e.g. late tracking marks
        _f=[p for p in pre if w[0]-30 <= p[0] <= w[1]+30]   # mislabeled pre_abl) -> markers match real ablations
        if _f: pre=_f   # 2026-07-13: only apply the window filter if it keeps >=1 mark; never let it EMPTY the
                        # manual marks (that silently fell back to PAS-log markers = "markers not from my annotations")
    # 2026-08-17: group repeat attempts at the SAME kinetochore before capping, so the cap counts targeted
    # kinetochores (what the reader is counting) rather than laser shots.
    #
    # 🔴 GROUP THE UNFILTERED MARKS. The window filter above drops any mark whose TIME falls outside the
    # ablation clip -- which is exactly where the later attempts at an already-targeted kinetochore live
    # (on 20250404 ptk_yfpcdc20_16, 9 of the 10 attempts are outside it). Grouping the filtered list
    # therefore produced groups of ONE and silently defeated the whole point of her request. Verified by
    # printing the marks per panel: 1 mark where there should have been 10.
    # The window still decides WHICH FRAME is shown -- a frame can only come from the ablation clip -- but
    # every target of the group is drawn on it, which is what she asked for.
    _pre_all=sorted(KT_MARKS[b].get("pre_abl",[]))
    _grp=group_pre_marks(_pre_all,abl_target_count(b))
    def _panel_t(g):
        """The frame this group is shown on: its earliest attempt that is inside the ablation clip."""
        if not w: return g[0][0]
        _in=[q for q in g if w[0]-30 <= q[0] <= w[1]+30]
        return (_in[0][0] if _in else max(w[0], g[0][0]))
    _grp=[g for g in _grp if g]
    _grp.sort(key=_panel_t)
    if len(_grp)>4: _grp=_grp[:4]   # keep strips readable: at most 4 ablation triples (full set is in the movie)
    # each group contributes ONE whole-cell panel, at that group's own in-window frame, centred on its
    # FIRST attempt (the zoom row still tracks that position)
    pre=[(_panel_t(g), g[0][1], g[0][2]) for g in _grp]
    if pre:
        # per target: BEFORE (frame before the marker) -> MARKER (red ✕) -> AFTER (post) — three DISTINCT
        # timepoints; the close-up row mirrors these exact frames zoomed in on each site.
        _altn=int(os.environ.get("ALT_BEFORE","0") or 0)   # v2 render: step further back for "before"
        for i,(t,x,y) in enumerate(pre):
            if _altn:
                tb=frame_back(b,t,_altn*ALT_BEFORE_STEPS.get(b,1))   # v2: a genuinely earlier frame
            elif b in KEEP_DUP_BEFORE:
                tb=t          # v1: deliberately repeat the marker frame, unmarked (her explicit request)
            else:
                tb=frame_before(b,t)
            if post:   # after = the post_abl marking NEAREST this target in space (then time)
                pp=min(post,key=lambda q:(q[1]-x)**2+(q[2]-y)**2+((q[0]-t)/30.0)**2); ta=pp[0]
            else:
                ta=frame_after(b,t)
            if ta<=t: ta=frame_after(b,t)
            ta=nonflash_forward(b,ta)   # skip the SLM-targeting-grid flash -> a CLEAN post-shot frame (fixes double-chromosome frame-3 grid)
            if i==len(pre)-1 and w and ta<w[1]: ta=nonflash_forward(b,w[1])   # last target: settle on the final ablation frame (also clean)
            tb=variant_override(b,i,"before",tb)      # USER 2026-08-06 alternate-frame versions
            t =variant_override(b,i,"marker",t)
            ta=variant_override(b,i,"after",ta)
            # ── USER 2026-08-16, ON-TARGET ABLATION STRIPS ──────────────────────────────────────
            # "for the whole-cell row for the ablation portion, just include the whole-cell frame ONCE per
            #  ablation and put a little box on it to show where the zoom-in frame looks at."
            # ONE whole-cell panel per target (the marker frame, which is the one that shows the shot),
            # carrying a rectangle at the close-up region. The zoom row is untouched — it still gets its
            # before/marker/after triple from `specs`.
            # THIS ALSO DISSOLVES THE 2026-08-14b MISALIGNMENT rather than patching it: the whole-cell row
            # is now `n_targets` long BY CONSTRUCTION, so it can no longer disagree with anything, and
            # `dedup_frames` has nothing to drop. Do NOT reintroduce KEEP_DUP_BEFORE for these strips.
            if ONE_PANEL_PER_ABL:
                _hb = ts_render.zoom_half_px(ps(b))       # the SAME half-width the close-up crop uses
                # ALL of this group's targets go on this one frame (2026-08-17). The numeral is drawn only
                # when the group really was shot more than once, so single-attempt strips gain no clutter;
                # attempt 1 is the frame being shown, so the later ones are the ones that need explaining.
                _mem = _grp[i]
                _marks = [(x, y, MAGENTA, "box", _hb)]
                for _k, (_tt, _xx, _yy) in enumerate(_mem):
                    _marks.append((_xx, _yy, MAGENTA, "x", (_k + 1) if len(_mem) > 1 else None))
                pan.append(("Ablation", t, f"abl{i+1}", _marks))
            else:
                pan.append(("Ablation",tb,f"abl{i+1} before",None))            # frame BEFORE the shot, clean
                pan.append(("Ablation",t, f"abl{i+1} ✕",[(x,y,MAGENTA,"x",None)]))  # marker frame (this target), X glyph
                pan.append(("Ablation",ta,f"abl{i+1} after",None))             # frame AFTER, clean
            specs.append((tb,t,ta,x,y))
    else:   # no KT markers (off-target) -> ablation-movie portion; before / marked / after around the shot
        if w:
            t0,t1=w; abl=abl_events_render(b)
            tm=brightest_abl_t(b,(t0,t1)) or (t0+t1)/2        # marker frame (skip the black laser-flash frame)
            tb=frame_before(b,tm); ta=frame_after(b,tm)
            if ta<=tm: ta=(brightest_abl_t(b,(tm,t1)) if t1>tm+1e-6 else t1) or t1
            # NF10: her explicit before/marker/after apply here as well as in the KT-marker branch above
            tb=variant_override(b,0,"before",tb)
            tm=variant_override(b,0,"marker",tm)
            ta=variant_override(b,0,"after",ta)
            pan.append(("Ablation",tb,"before",None))
            pan.append(("Ablation",tm,"✕",[(x,y,MAGENTA,"x",None) for (x,y) in abl]))   # ALL sites on the marker frame, X glyph
            pan.append(("Ablation",ta,"after",None))
            _cap=NF10_MAX_TARGETS.get(b,4)
            for (x,y) in abl[:_cap]: specs.append((tb,tm,ta,x,y))               # one close-up triple per site
    pan=dedup_frames(b,"Ablation",pan)   # 2026-07-13: drop 'before'==marker repeats (ablation on the first frame) etc.
    # ── ROW ALIGNMENT, 2026-08-14: DO NOT "fix" this by keeping every target's triple in the whole-cell row.
    # The zoom row is NOT always 3 panels per target — `aligned_closeup_panels` runs its own ZOOM_DEDUP_T
    # pass — so "main row shorter than 3*n_targets" is NOT evidence of a misaligned strip. Tested that way on
    # 2026-08-14 it produced a FALSE POSITIVE on `20260420 ...ablation_71`, whose two rows were already 5 and
    # 5; restoring the deduped panel made the whole-cell row 6 against a zoom row of 5, i.e. it BROKE a strip
    # that was correct. The only valid test is the rendered image: count the columns in row 1 against row 2.
    # Genuinely misaligned as of 2026-08-14 (verified by eye, both 8 vs 9): `20260417 ...ablation_18` and
    # `20250925 triple_ablation_13` — see NOTES §14 2026-08-14b for why neither existing per-batch mechanism
    # fixes them and what the real fix (mirror the zoom row off the SURVIVING main panels) would take.
    mt=lib.parse_time(mr.get(b,{}).get("Metaphase Start (s)","")); at=lib.parse_time(mr.get(b,{}).get("Anaphase Onset (s)",""))
    if mt is not None and at is not None and at<mt:   # inconsistent times -> label would read anaphase BEFORE
        flag_reprocess(b,f"anaphase onset ({_hms(at)}) is before metaphase start ({_hms(mt)}) in the master — check event times")
    # ---- MONITORING FRAME SELECTION (2026-07-13 rework: long-span ~2hr sampling + always-include + dedup) ----
    _tr=mon_trange(b); mon=[]
    if _tr:
        t0,t1=_tr; span=t1-t0
        LONG=3*3600.0   # >3 hr monitoring span (colcemid / mitotic arrest) -> the old start/mid/end left 1-7 hr gaps
        if span>LONG:
            # sample about every 2 hr across the whole span (+ metaphase/anaphase if recorded)
            step=2*3600.0; n=max(2,int(round(span/step)))
            for k in range(n+1): mon.append(("Monitoring", t0+span*k/n, None, None))
            if mt is not None: mon.append(("Monitoring", mt, f"metaphase {_hms(mt)}", None))
            if at is not None: mon.append(("Monitoring", at, f"anaphase {_hms(at)}", None))
        else:
            # USER 2026-08-06, for the cells she named: start at NEBD and carry on to CYTOKINESIS with a
            # frame roughly every 5 minutes, tightening around the events — "increase the number of
            # monitoring frames in the single ablation cells ... such that they cover the time region until
            # cytokinesis as thoroughly as this timestrip (a frame approx every 5 mins unless an event
            # occurs, then sooner)". Every time comes from a master column; nothing is guessed.
            if b in DENSE_MONITORING:
                nb=lib.parse_time(mr.get(b,{}).get("NEB Time (s)",""))
                fa=lib.parse_time(mr.get(b,{}).get("First Congression (s)",""))
                ct=lib.parse_time(mr.get(b,{}).get("Cytokinesis Onset (s)",""))
                ev=[(nb,"NEBD"),(fa,"first alignment"),(mt,"metaphase onset"),
                    (at,"anaphase"),(ct,"cytokinesis")]
                ev=[(t,lab) for t,lab in ev if t is not None and t0-60<=t<=t1+60]
                for t,lab in ev: mon.append(("Monitoring", t, f"{lab} {_hms(t)}", None))
                # USER 2026-08-06 asked for "a frame at the end for the start of cytokinesis" on the
                # 3-sisterless cell. Its `Cytokinesis Onset (s)` is empty, and that is CORRECT — her own
                # Notes for the batch read "video stops before cytokinesis onset", and the recording indeed
                # ends 10.3 min after anaphase. So there is no cytokinesis frame to show. The closest true
                # thing is the LAST recorded frame, labelled as the end of the recording rather than as an
                # event that was never captured. Added for any dense-monitoring cell whose recording runs
                # on past the last named event.
                _lastev=max([t for t,_ in ev], default=t0)
                if t1 - _lastev > DENSE_STEP_S*0.8:
                    _ck=lib.parse_time(mr.get(b,{}).get("Cytokinesis Onset (s)",""))
                    if _ck is None:
                        mon.append(("Monitoring", t1, f"end of recording {_hms(t1)}", None))
                # fill the gaps between named events at ~5 min, so nothing is left uncovered
                start=min([t for t,_ in ev], default=t0); end=max([t for t,_ in ev], default=t1)
                end=max(end, t1 if (t1-_lastev > DENSE_STEP_S*0.8) else end)
                k=start+DENSE_STEP_S
                while k < end-30:
                    if all(abs(k-t)>DENSE_STEP_S*0.6 for t,_ in ev):
                        mon.append(("Monitoring", k, None, None))
                    k += DENSE_STEP_S
            else:
                if mt is not None and t0<mt: mon.append(("Monitoring", t0+(mt-t0)*0.5, "prometaphase", None))
                if mt is not None: mon.append(("Monitoring", mt, f"metaphase {_hms(mt)}", None))
                if at is not None:
                    mon.append(("Monitoring", at, f"anaphase {_hms(at)}", None))
                    if at+300 <= t1+60: mon.append(("Monitoring", at+300, f"+5min {_hms(at+300)}", None))
            if mt is None and at is None:   # no event times -> even start/mid/end coverage
                mon += [("Monitoring", t0, "mon start", None), ("Monitoring", (t0+t1)/2, "mon mid", None), ("Monitoring", t1, "mon end", None)]
        mon = sorted(mon, key=lambda p: p[1])
        mon = dedup_frames(b, "Monitoring", mon)   # collapse any that hit the SAME movie frame (no repeats)
    # ---- NF10 (user 2026-08-06): monitoring frames she named, overriding the automatic selection ----
    _sh=NF10_LABEL_SHIFT.get(b,0.0)
    if b in NF10_MON_TIMES:
        mon=[("Monitoring",float(_t),(f"{_lab} {_hms(_t+_sh)}" if _lab else None),None)
             for _t,_lab in NF10_MON_TIMES[b]]
        mon=dedup_frames(b,"Monitoring",sorted(mon,key=lambda p:p[1]))
    if b in NF10_MON_LAST:
        _lt,_llab=NF10_MON_LAST[b]
        mon=[p for p in mon if p[1] < _lt-15.0]          # she named the LAST frame; nothing runs past it
        mon.append(("Monitoring",float(_lt),(f"{_llab} {_hms(_lt+_sh)}" if _llab else None),None))
        mon=dedup_frames(b,"Monitoring",sorted(mon,key=lambda p:p[1]))
    pan += mon
    # 🔴 HER 2026-08-20 REQUEST, per cell: *"for the monitoring timestrip on this artboard: no need for the
    # frames at 46:19 and 51:19"* (artboard 9, `nf9_1-sisterless__20250930_four_ablation_59`). Dropped HERE,
    # in the generator, rather than by trimming the rendered PNG -- a raster edit dies on the next rebuild,
    # and the frame would silently come back. Times are matched with a tolerance because the panel time is
    # the requested time, not necessarily the exact movie frame time.
    _drop = DROP_MON_T.get(b) or []
    if _drop:
        _before = len(pan)
        pan = [q for q in pan
               if not (q[0] == "Monitoring" and any(abs(q[1] - d) <= 2.0 for d in _drop))]
        if len(pan) != _before:
            print(f"    [drop] {b}: removed {_before - len(pan)} monitoring frame(s) at "
                  + ", ".join(_hms(d) for d in _drop))
    return pan, specs

import random; rng=random.Random(7)
# Curated cells: the user marked timestrip cells in the dedicated slideshow via these master columns.
# Prefer them when picking each category's cell (timestrip_frames.csv is empty -> frames stay auto-derived).
CURATED={r["Batch Name"] for r in data
         if r.get("use_as_example","").strip().lower()=="yes" or r.get("timestrip_candidate","").strip().lower()=="yes"}
CATS={
 "1-sisterless":lambda b:mr.get(b,{}).get("On-Target / Off-Target")=="On-target" and mr.get(b,{}).get("# Sisterless KTs")=="1" and b not in dbl and not lib.is_drug(b),
 "2-sisterless":lambda b:mr.get(b,{}).get("On-Target / Off-Target")=="On-target" and mr.get(b,{}).get("# Sisterless KTs")=="2" and b not in dbl and not lib.is_drug(b),
 "3-sisterless":lambda b:mr.get(b,{}).get("On-Target / Off-Target")=="On-target" and mr.get(b,{}).get("# Sisterless KTs")=="3" and b not in dbl and not lib.is_drug(b),
 "off-target":lambda b:mr.get(b,{}).get("On-Target / Off-Target")=="Off-target" and not lib.is_drug(b),
 "double-chromosome":lambda b:b in dbl,
 "unmanipulated-control":lambda b:mr.get(b,{}).get("On-Target / Off-Target")=="Unmodified",
}
def valid_abl(b):   # all 4 movies readable AND has ablation events
    return movies_ok(b) and len(abl_events_render(b))>0
def mon_ok(b):      # control: only monitoring phase+fluor need be readable
    return movie(b,"Phase","Monitoring") is not None and movie(b,"Fluor","Monitoring") is not None
def mon_trange(b):
    fj=fjson(b)
    if not fj: return None
    ts=[f['t_sec'] for f in fj['frames'] if f['role']=='monitoring']
    return (min(ts),max(ts)) if ts else None
# user-specified cells (override random selection)
PINNED={
 # unmanipulated-control: user disliked BOTH 16_xy1 and 16_xy2's anaphase -> switch to a different cell.
 # 20250320 ptk_yfpcdc20__1_xy2: single eYFP-Cdc20 cell, full mitosis with recorded metaphase + anaphase +
 # cytokinesis; sibling positions _xy3/_xy4/_xy5 available as backups if its anaphase doesn't read cleanly.
 # 2026-08-03 (her explicit pick, from the UNMANIP_CANDIDATES page) — SWITCHED from
 # 20250320 ptk_yfpcdc20__1_xy2 to 20250321 ptk_yfpcdc20__2_xy1 (different day/dish; she flagged it
 # "good localization"). PAS-log check: 0 ablation_events_local + stub (257-byte) Ablation mp4s ->
 # genuinely never ablated; master "On-Target / Off-Target"=Unmodified agrees (cross-check only).
 "unmanipulated-control":"20250321 ptk_yfpcdc20__2_xy1",
 # 1-sisterless: T10 — the prior pick (four_ablation_57) drifts offscreen; use a single-target 1-sisterless
 # curated example (example=Y, timestrip=Y) whose cell stays framed.
 "1-sisterless":"20250411 ptk_yfpcdc20_11",
 # off-target: 2026-08-03 (her explicit pick) — SWITCHED from 20251104 ablations_17 to
 # 20250901 triple_ablation_32 (she named this batch directly for the off-target timestrip).
 # PAS-log check (frames.json ablation_events_local): 12 real ablation events present -> genuinely
 # an ablation batch, off-target per master "On-Target / Off-Target"=Off-target (cross-check only).
 "off-target":"20250901 triple_ablation_32",
 # double-chromosome: cell with 'both kinetochores on one chromosome destroyed' AND 2 pre_abl KT markers,
 # so the SAME per-target triple logic (clean/marked/post) as 1/2/3-sisterless draws BOTH kinetochores.
 "double-chromosome":"20260420 ptk2 eyfp cdc20 1 ablation_73",
 # PIN the 3-sisterless cell the user reviewed so the marker/last-frame fixes land on THAT cell
 # (selection is otherwise non-deterministic across runs due to transient movie-decode failures).
 # 2-sisterless: SWAPPED off 20251104 ablations_1 — its last 3 monitoring frames looked like a different
 # cell — to a curated 2-sisterless example.
 "2-sisterless":"20260417 ptk2 eyfp cdc20 ablation_19",
 "3-sisterless":"20251104 ablations_5",
}
# S5: avoid the current 3-sisterless pick (weird phase/488 overlays — flag for reprocess).
# B4: drop 20251104 ablations_13 (the double-chromosome cell the user asked to REPLACE).
# B7: drop 20250423 _39_xy3 (control cell to replace again). Selector then prefers a CURATED cell.
TS_EXCLUDE={"3-sisterless":{"20260417 ptk2 eyfp cdc20 ablation_1"},
            "double-chromosome":{"20251104 ablations_13","20251029 single_ablation_8"},
            "unmanipulated-control":{"20250423 ptk_yfpcdc20_39_xy3","20250321 ptk_yfpcdc20__1_xy1","20250411 ptk_yfpcdc20_16_xy2"},
            "off-target":{"20260417 ptk2 eyfp cdc20 ablation_17"},
            "1-sisterless":{"20250930 four_ablation_57"},   # T10: drifts offscreen
            "2-sisterless":{"20251104 ablations_1"}}   # last 3 monitoring frames looked like a different cell
# S5/S6: batches dropped from the timestrip picks because they need re-rendering — record them so the
# pipeline can reprocess (weird phase/488 overlay; phase rendered GREEN + fluor GRAY = channel swap).
flag_reprocess("20260417 ptk2 eyfp cdc20 ablation_1","weird phase/488 overlay on the rendered movie — picked a different 3-sisterless cell; re-render")
flag_reprocess("20260420 ptk2 eyfp cdc20 1 ablation_73","double-chromosome timestrip: Fluor_Ablation movie carries a persistent SLM ablation-grid overlay on ALL post-shot frames -> no clean post-ablation frame for the 'after' panels (T11). Re-render WITHOUT the targeting-grid overlay.")
# ===== UNMANIPULATED CANDIDATES slide (task #12) — render >=4 DIFFERENT good unmodified cells as timestrips
# on ONE stacked image so the user can pick the best. Guarded: `UNMANIP_CANDIDATES=1 python3 group_timestrips.py`
# renders ONLY the candidates (via the SAME unmanipulated-control code path: square-aligned make_strip, tight
# crop through ts_render.tight_square) then composes + exits — it does NOT run the heavy main selection loop.
UNMANIP_CANDIDATES=[
 # 20250320 ptk_yfpcdc20__1 series: single eYFP-Cdc20 unmodified cells, full mitosis with recorded
 # metaphase+anaphase+cytokinesis + good localization (dish 1). NOT the disliked _16_xy1/_xy2.
 "20250320 ptk_yfpcdc20__1_xy2",
 "20250320 ptk_yfpcdc20__1_xy3",
 "20250320 ptk_yfpcdc20__1_xy4",
 "20250320 ptk_yfpcdc20__1_xy5",
 "20250320 ptk_yfpcdc20__1_xy1",   # same day, different cell
 "20250321 ptk_yfpcdc20__2_xy1",   # different day, flagged good localization
]
def render_unmanip(pick, out_prefix):
    """Render ONE unmodified cell as the unmanipulated-control timestrip (prometa->meta->ana->cyto),
    tight-square cropped via the primitive (square_aligned -> square_crop -> ts_render.tight_square),
    falling back to the default tight crop. Returns True on success."""
    tr=mon_trange(pick)
    if not (mon_ok(pick) and tr): return False
    t0,t1=tr
    mt=lib.parse_time(mr.get(pick,{}).get("Metaphase Start (s)",""))
    at=lib.parse_time(mr.get(pick,{}).get("Anaphase Onset (s)",""))
    ct=lib.parse_time(mr.get(pick,{}).get("Cytokinesis Onset (s)",""))
    # USER 2026-08-06: "i dont think that one of those frames shows metaphase onset. can you include a frame
    # at the time of metaphase onset? and also for first alignment ... use for the first frame the frame at
    # the time of nuclear envelope breakdown. (and then maybe one like a minute before then too)".
    # Every one of these is a master column, so the panel list is now built from the recorded event times
    # rather than from a 50%-of-the-way-to-metaphase guess: NEBD-1min, NEBD, first alignment (the master's
    # "First Congression"), metaphase onset, anaphase onset, cytokinesis.
    nb=lib.parse_time(mr.get(pick,{}).get("NEB Time (s)",""))
    fa=lib.parse_time(mr.get(pick,{}).get("First Congression (s)",""))
    pan=[]
    if nb is not None and nb-60.0>=t0: pan.append(("Monitoring",nb-60.0,"before NEBD",None))
    if nb is not None: pan.append(("Monitoring",nb,f"NEBD {_hms(nb)}",None))
    if fa is not None: pan.append(("Monitoring",fa,f"first alignment {_hms(fa)}",None))
    if mt is not None: pan.append(("Monitoring",mt,f"metaphase onset {_hms(mt)}",None))
    if at is not None: pan.append(("Monitoring",at,f"anaphase {_hms(at)}",None))
    if ct is not None: pan.append(("Monitoring",ct,f"cytokinesis {_hms(ct)}",None))
    elif at is None: pan.append(("Monitoring",t1,"end",None))
    if not pan and mt is not None: pan.append(("Monitoring",mt,f"metaphase {_hms(mt)}",None))
    pan=dedup_frames(pick,"Monitoring",pan)   # two events landing on one frame -> show it once
    ok=make_strip(pick,pan,out_prefix,title=f"Unmanipulated control — {pick}",square_aligned=True)
    if not ok: ok=make_strip(pick,pan,out_prefix,title=f"Unmanipulated control — {pick}")
    render_unmanip.last_pan=pan   # so callers can record_plot the panel list (it is built here, not passed in)
    return ok
if os.environ.get("UNMANIP_CANDIDATES"):
    import candidate_compose
    cdir=f"{OUT}/_cand"; os.makedirs(cdir,exist_ok=True)
    items=[]
    for b in UNMANIP_CANDIDATES:
        if not render_dir(b): print(f"  cand {b}: no render dir -> skip"); continue
        pref=f"{cdir}/{b.replace(' ','_')}"
        ok=render_unmanip(b,pref)
        print(f"  cand {b}: {'ok' if ok else 'FAIL'}")
        if ok: items.append((b, pref+".png"))
    candidate_compose.compose(items, f"{OUT}/unmanipulated_candidates.png",
                              sup_title="Unmanipulated control candidates — pick one")
    sys.exit(0)

# ===== NF9 (user 2026-08-04): six SPECIFIC cells she named for the NEW-FIGURES deck. These are her picks,
# not the selector's — so they get their OWN plot_ids (nf9_*) and do NOT touch the category strips already
# placed on META/supplemental. Two of the six are 1-sisterless (different cells), which PINNED cannot express
# (one entry per category), hence an explicit list rather than a PINNED override. Guard: NF9=1.
NF9_CELLS=[
 ("unmanipulated-control","20250320 ptk_yfpcdc20__1_xy3"),
 ("1-sisterless",         "20250411 ptk_yfpcdc20_11"),
 ("double-chromosome",    "20260420 ptk2 eyfp cdc20 1 ablation_71"),
 ("3-sisterless",         "20260417 ptk2 eyfp cdc20 ablation_18"),
 ("1-sisterless",         "20250930 four_ablation_59"),
 ("off-target",           "20250901 triple_ablation_32"),
]
if os.environ.get("NF9"):
    _nf9_only=os.environ.get("NF9_ONLY","")   # substring filter, so one strip can be re-rendered alone
    for cat,b in NF9_CELLS:
        _v=os.environ.get("VARIANT","")
        pid=f"nf9_{cat}__{b.replace(' ','_')}" + (f"_{_v}" if _v else "")
        pref=f"{OUT}/{pid}"
        if _nf9_only and _nf9_only not in pid: continue
        if not render_dir(b): print(f"  NF9 {pid}: no render dir -> SKIP"); continue
        try:
            if cat=="unmanipulated-control":
                ok=render_unmanip(b,pref); pan=getattr(render_unmanip,"last_pan",[])
            else:
                pan,specs=cat_panels(b)
                _noclose=(cat=="off-target")   # T12: no ablation close-ups for off-target strips
                # square-aligned is the current standard (one square footprint, columns aligned);
                # fall back to the default tight crop for cells with no manual outline.
                ok=make_strip(b,pan,pref,closeup_specs=specs,title=f"{cat} — {b}",
                              do_closeups=not _noclose,square_aligned=True)
                if not ok:
                    ok=make_strip(b,pan,pref,closeup_specs=specs,title=f"{cat} — {b}",
                                  do_closeups=not _noclose)
        except Exception as e:
            ok=False; print(f"  NF9 {pid}: EXC {type(e).__name__}: {e}")
        print(f"  NF9 {pid}: {'ok' if ok else 'FAIL'}")
        if ok:
            d=render_dir(b) or ""
            rows=[[cat,b,role,round(float(t),1),(txt or ""),(len(marks) if marks else 0)]
                  for (role,t,txt,marks) in pan]
            lib.record_plot(pid,["category","batch","role","t_sec","panel_label","n_marks"],rows,
                {"type":"NF9 requested timestrip","batch":b,"category":cat,"n_panels":len(pan),
                 "render_dir":d,"pixel_um":ps(b),"n_ablation_events":len(abl_events_render(b))},
                SCRIPT if 'SCRIPT' in globals() else __file__,
                f"{cat} timestrip ({b}) — cell requested by user 2026-08-04",
                source=[f"{d}/{b}_frames.json"] if d else None, key_column="batch")
    sys.exit(0)


# 12, not 10: every hand-specified lagging strip carries exactly 12 frames, so a 10-wide wrap left a
# 2-tile orphan row and ts_render padded it to full width -- a white band across most of the strip, and
# the whole-cell row ended up separated from its own zoom row. At 12 each strip is one whole-cell row
# immediately above its matching zoom row, with no padding at all.
LAG_ROW = 12    # frames per row on a fluorescence-only lagging strip


def lagging_times(b, spec):
    """The monitoring frame times for a fluorescence-only lagging strip, from her spec.

    'range' takes every recorded monitoring frame in the window; near-simultaneous frames (<5 s apart -
    this batch records short bursts) collapse to one so the strip does not show the same moment repeatedly."""
    ts = role_ts(b, "Monitoring")
    if spec[0] == "list":
        return [min(ts, key=lambda z: abs(z - t)) for t in spec[1]] if ts else list(spec[1])
    _t0, _t1 = spec[1], spec[2]
    win = [t for t in ts if _t0 - 1.0 <= t <= _t1 + 1.0]
    out = []
    for t in win:
        if not out or t - out[-1] >= 5.0: out.append(t)
    return out


def _lagging_centroids(b, _label=None):
    """{t_sec: (x, y)} for HER traced kinetochore outlines on this cell, in full-frame pixels.

    LABEL FALLBACK, 2026-08-21. Her board-5 item 8 asked for zoom frames on the lagging kinetochore of the
    rebound strip, and the zoom row silently never appeared: `20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52`
    has SEVEN traced outlines and every one is labelled `polar`, not `lagging` -- it is a METAPHASE ablation,
    so the kinetochore she traced through anaphase kept the label it had before. Requiring the literal
    "lagging" label threw her own marks away. Prefer `lagging` where it exists; otherwise fall back to
    whatever single label this cell does carry, which is her mark either way (NOTES: manual markings are
    authoritative). The times land on the strip's own frames -- 954.9 / 987.1 / 1019.6 against frames
    954.0 / 987.0 / 1019.0 -- which is the anaphase stretch she is pointing at.
    """
    if _label is None:
        _have = set()
        try:
            for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_outlines.csv", newline="",
                                        encoding="utf-8", errors="replace")):
                if (r.get("batch") or "").strip() == b:
                    _have.add((r.get("label") or "").strip())
        except Exception:
            pass
        _label = "lagging" if "lagging" in _have else (sorted(_have)[0] if len(_have) == 1 else "lagging")
    out = {}
    try:
        import json as _json
        for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_outlines.csv", newline="",
                                    encoding="utf-8", errors="replace")):
            if (r.get("batch") or "").strip() != b: continue
            if (r.get("label") or "").strip() != _label: continue
            pts = (r.get("points") or "").strip()
            if not pts: continue
            try:
                P = np.array(_json.loads(pts), float)
                out[float(r["t_sec"])] = (float(P[:, 0].mean()), float(P[:, 1].mean()))
            except Exception:
                continue
    except Exception:
        pass
    return out


def render_lagging(b, times, out_prefix, title):
    """Fluorescence-ONLY strip over the given monitoring times, plus a ZOOM row where she has traced the
    lagging kinetochore.

    USER 2026-08-20 (artboard 5, item 8.1): "i said adding zoom frames, not replacing the whole-cell frames
    with the zooms. Perhaps a translucent box could be placed on the whole cell image to indicate where the
    zoom roi is, for relevant frames (and i say translucent so that both the square outline can be seen, as
    well as still being able to see everything in the timestrip itself)."

    The zoom is centred on HER OWN `lagging` outline for that frame -- never on an auto-detected spot. A cell
    with no lagging outline gets no zoom row at all rather than a guessed one; that is reported, because the
    fix is a tracing job, not a code change."""
    if not times: print(f"  {b}: no lagging frames"); return False
    box = portion_box(b, "Monitoring", times) or square_crop(b)
    if box is None: print(f"  {b}: no outline -> cannot crop lagging strip"); return False
    pxs = ps(b); eff = pxs * (box[2] - box[0]) / ALIGN_N
    pan = [build_panel(b, "Monitoring", t, None, box) for t in times]
    pan = uniform_fluor_stretch(ts_render.resize_panels([p for p in pan if p], ALIGN_N))

    # ---- zoom ROIs from her lagging outlines -------------------------------------------------------
    _lag = _lagging_centroids(b)
    _half = ts_render.zoom_half_px(pxs)                 # the standard KT zoom window, in source px
    _zoom_pan = []
    if _lag:
        _sc = float(ALIGN_N) / float(box[2] - box[0])   # source px -> assembled tile px
        for _i, _t in enumerate(times):
            _tb = min(_lag, key=lambda z: abs(z - _t))
            if abs(_tb - _t) > 30.0:                    # no traced lagging KT near this frame
                _zoom_pan.append(None); continue
            _cx, _cy = _lag[_tb]
            _zb = (int(round(_cx - _half)), int(round(_cy - _half)),
                   int(round(_cx + _half)), int(round(_cy + _half)))
            _zp = build_panel(b, "Monitoring", _t, None, _zb)
            _zoom_pan.append(_zp)
            # translucent square on the WHOLE-CELL tile showing where that zoom looks
            if _i < len(pan) and pan[_i]:
                for _k in ("fluor", "phase"):
                    _im = pan[_i].get(_k)
                    if _im is None: continue
                    _x0 = int(round((_zb[0] - box[0]) * _sc)); _y0 = int(round((_zb[1] - box[1]) * _sc))
                    _x1 = int(round((_zb[2] - box[0]) * _sc)); _y1 = int(round((_zb[3] - box[1]) * _sc))
                    _ov = _im.copy()
                    cv2.rectangle(_ov, (_x0, _y0), (_x1, _y1), (255, 255, 255),
                                  ts_render.stroke_px(_im), cv2.LINE_AA)
                    cv2.addWeighted(_ov, 0.55, _im, 0.45, 0, _im)   # translucent: box visible, cell visible
    # WRAP onto several rows. A single row of every frame in her window came out 30 tiles / 11400 px wide,
    # where the cell is a few pixels across and nothing is readable. emit() stacks portions vertically, so
    # each chunk becomes one row of the same strip. Short strips (<= LAG_ROW) are unaffected: one row.
    rows = [pan[i:i + LAG_ROW] for i in range(0, len(pan), LAG_ROW)]
    portions = []
    for ri, row in enumerate(rows):
        res = ts_render.assemble(row, eff, 10.0, chan_labels=("Phase", fluor_label_for(b)), fluor_only=True)
        if res: portions.append((f"lagging row {ri+1}", res[0], res[1]))
    if _zoom_pan and any(_zoom_pan):
        _zp = uniform_fluor_stretch(ts_render.resize_panels([q for q in _zoom_pan if q], ALIGN_N))
        _zeff = pxs * (2 * _half) / ALIGN_N
        for _ri in range(0, len(_zp), LAG_ROW):
            _res = ts_render.assemble(_zp[_ri:_ri + LAG_ROW], _zeff, 2.0,
                                      chan_labels=("Phase", fluor_label_for(b)), fluor_only=True)
            if _res: portions.append((f"lagging zoom row {_ri // LAG_ROW + 1}", _res[0], _res[1]))
        print(f"   {b}: zoom row from {sum(1 for q in _zoom_pan if q)}/{len(times)} traced lagging frames")
    elif not _lag:
        print(f"   {b}: NO `lagging` outlines -> no zoom row (needs tracing, not code)")
    if not portions: print(f"  {b}: assemble failed"); return False
    return ts_render.emit(portions, out_prefix, title=title)


if os.environ.get("NF10"):
    _only = os.environ.get("NF10_ONLY", "")
    for cat, b in NF10_CELLS:
        pid = f"nf10_{cat}__{b.replace(' ', '_')}"
        if _only and _only not in pid: continue
        if not render_dir(b): print(f"  NF10 {pid}: no render dir -> SKIP"); continue
        pref = f"{OUT}/{pid}"
        try:
            pan, specs = cat_panels(b)
            _noclose = cat.startswith("off-target")      # off-target strips carry no ablation close-up row (T12)
            ok = make_strip(b, pan, pref, closeup_specs=specs, title=f"{cat} — {b}",
                            do_closeups=not _noclose, square_aligned=True)
            if not ok:
                ok = make_strip(b, pan, pref, closeup_specs=specs, title=f"{cat} — {b}",
                                do_closeups=not _noclose)
        except Exception as e:
            ok = False; pan = []
            print(f"  NF10 {pid}: EXC {type(e).__name__}: {e}")
        print(f"  NF10 {pid}: {'ok' if ok else 'FAIL'}  ({len(pan)} panels)")
        if ok:
            d = render_dir(b) or ""
            rows = [[cat, b, role, round(float(t), 1), (txt or ""), (len(marks) if marks else 0)]
                    for (role, t, txt, marks) in pan]
            lib.record_plot(pid, ["category", "batch", "role", "t_sec", "panel_label", "n_marks"], rows,
                {"type": "NF10 requested timestrip", "batch": b, "category": cat, "n_panels": len(pan),
                 "render_dir": d, "pixel_um": ps(b), "label_shift_s": NF10_LABEL_SHIFT.get(b, 0.0),
                 "explicit_ablation_times": bool(NF10_ABL_TIMES.get(b)),
                 "explicit_monitoring_times": bool(NF10_MON_TIMES.get(b))},
                SCRIPT if 'SCRIPT' in globals() else __file__,
                # 2026-08-09: this caption used to assert "specified by user" for EVERY strip, but the
                # 3-sisterless-pole-switch entry was filed under a category *I* inferred from her backlog
                # note "chromosome flips pole to pole" -- the CELL is hers, the category label is not.
                # Say which is which rather than crediting her with a choice she did not make.
                (f"{cat} timestrip ({b}) — cell specified by user 2026-08-06; frames per the standard "
                 f"ablation-timestrip rule"
                 if b != "20250925 triple_ablation_13" else
                 f"{cat} timestrip ({b}) — cell requested by user (backlog: 'chromosome flips pole to "
                 f"pole'); the '{cat}' category label was assigned by Claude, not specified by her"),
                source=[f"{d}/{b}_frames.json"] if d else None, key_column="batch")
    for cat, b, spec in NF10_LAGGING:
        pid = f"nf10_{cat}__{b.replace(' ', '_')}"
        if _only and _only not in pid: continue
        if not render_dir(b): print(f"  NF10 {pid}: no render dir -> SKIP"); continue
        pref = f"{OUT}/{pid}"
        times = lagging_times(b, spec)
        try:
            ok = render_lagging(b, times, pref, title=f"{cat} — {b}")
        except Exception as e:
            ok = False; print(f"  NF10 {pid}: EXC {type(e).__name__}: {e}")
        print(f"  NF10 {pid}: {'ok' if ok else 'FAIL'}  ({len(times)} fluor frames)")
        if ok:
            d = render_dir(b) or ""
            lib.record_plot(pid, ["category", "batch", "role", "t_sec"],
                [[cat, b, "Monitoring", round(float(t), 1)] for t in times],
                {"type": "NF10 lagging timestrip (fluorescence only)", "batch": b, "category": cat,
                 "n_panels": len(times), "render_dir": d, "pixel_um": ps(b), "fluor_only": True},
                SCRIPT if 'SCRIPT' in globals() else __file__,
                f"{cat} fluorescence timestrip ({b}) — frames specified by user 2026-08-06",
                source=[f"{d}/{b}_frames.json"] if d else None, key_column="batch")
    sys.exit(0)


# ===== PER-TYPE CANDIDATES (user 2026-07-15: "multiple cells of a type on one artframe so I could pick the best").
# Renders EVERY user-marked candidate cell (use_as_example/timestrip_candidate = CURATED) of each ablation type via
# the SAME cat_panels->make_strip path as the chosen strip, then stacks them (<=6/page, paginated) into
# <type>_candidates.png — mirroring the unmanipulated/FRAP candidate composites. Guard: TYPE_CANDIDATES=1.
if os.environ.get("TYPE_CANDIDATES"):
    import candidate_compose
    cdir=f"{OUT}/_cand"; os.makedirs(cdir,exist_ok=True)
    _only=[c for c in os.environ.get("CAND_CAT_ONLY","").split(",") if c]
    def _sheet_excluded(b):
        """CONTACT SHEETS FOLLOW THE TIMESTRIP CLASS: exempt from the METAPHASE and PROPHASE rules
        (user 2026-08-07, "contact sheets are also exempt from the metaphase and prophase rules").
        A candidate sheet exists so she can SEE the cells and choose; silently dropping metaphase and
        prophase ablations from it hides exactly the cells she might want to pick.

        Everything else plot_excluded() enforces still applies -- master Exclude=Yes, REVIEW_EXCLUDE,
        drug, and 4-sisterless. Drug is kept deliberately: drugged cells have their own builder
        (group_drug_ablation_timestrips.py) and the CATS lambdas above assume undrugged, but
        "double-chromosome" carries no is_drug guard of its own, so dropping it here would leak
        drugged cells onto that one sheet."""
        return lib.timestrip_excluded(b) or lib.is_drug(b) or lib.is_four_sisterless(b)

    def _cands(cat):
        fn=CATS[cat]
        return sorted({b for b in mr if fn(b) and b in CURATED and render_dir(b)
                       and not _sheet_excluded(b) and b not in TS_EXCLUDE.get(cat,set())})
    def _polar():
        return sorted({b for b in mr if (mr[b].get("Polar Chromosomes","") or "").strip().lower()=="yes"
                       and b in CURATED and render_dir(b) and not lib.is_drug(b) and not _sheet_excluded(b) and b not in dbl})
    JOBS=[(c,_cands(c)) for c in ("1-sisterless","2-sisterless","3-sisterless","off-target","double-chromosome")]
    JOBS.append(("polar",_polar()))
    for cat,cells in JOBS:
        if _only and cat not in _only: continue
        _noclose=(cat=="off-target"); items=[]
        for b in cells:
            pref=f"{cdir}/{cat}__{b.replace(' ','_')}"
            try:
                _pan,_specs=cat_panels(b)
                ok=make_strip(b,_pan,pref,closeup_specs=_specs,title=f"{cat} — {b}",do_closeups=not _noclose)
            except Exception as e:
                ok=False; print(f"  {cat} {b}: EXC {type(e).__name__}: {e}")
            print(f"  {cat} {b}: {'ok' if ok else 'FAIL'}")
            if ok: items.append((b,pref+".png"))
        pages=[items[i:i+6] for i in range(0,len(items),6)]
        for pi,pg in enumerate(pages):
            suf="" if pi==0 else f"_{pi+1}"
            candidate_compose.compose(pg, f"{OUT}/{cat}_candidates{suf}.png",
                sup_title=f"{cat} candidates{(' (page '+str(pi+1)+')') if len(pages)>1 else ''} - pick one")
        print(f"== {cat}: {len(items)} rendered -> {len(pages)} page(s)")
    sys.exit(0)

# 2026-08-03: this script never called record_plot, so the category strips' plot spreadsheets
# (data/1-sisterless.csv etc.) had not been rewritten since 2026-07-09 -- and the cell each strip shows
# is chosen HERE, from a shuffled candidate list. data/1-sisterless.csv still names
# "20250411 ptk_yfpcdc20_11" while the figure has been showing "20260420 ptk2 eyfp cdc20 1 ablation_20":
# the recorded source was simply wrong, and the mtime-based "is this figure stale?" check was blind to a
# family of placed figures because nothing ever touched their CSV. Record the pick and its panel list.
def record_category(cat,pick,pan,plot_id=None,aligned=False):
    """Register a category timestrip. `plot_id`/`aligned` let the _aligned VARIANT register itself.

    2026-08-04: only the parent was ever recorded, so every `<cat>_aligned` entry in PLOT_SETTINGS came
    from the retroactive registration script and carried `mtimes_at_registration` instead of
    `hashes_at_build` — which by design cannot prove the figure is in sync with its sources. The aligned
    variant is a real figure on the deck, so it records itself here and becomes staleness-checkable."""
    d=render_dir(pick) or ""
    pid=plot_id or cat
    rows=[[cat,pick,role,round(float(t),1),(txt or ""),(len(marks) if marks else 0)]
          for (role,t,txt,marks) in pan]
    lib.record_plot(pid,["category","batch","role","t_sec","panel_label","n_marks"],rows,
        {"type":"category timestrip"+(" (aligned square crop)" if aligned else ""),
         "batch":pick,"n_panels":len(pan),
         "render_dir":d,"pixel_um":ps(pick),
         "n_ablation_events":len(abl_events_render(pick)),
         **({"variant_of":cat,"crop":"one square footprint across main/zoom/monitoring tiles"}
            if aligned else {"aligned_variant":ALIGNED_STATUS.get(cat)})},
        SCRIPT if 'SCRIPT' in globals() else __file__,
        f"{cat} example timestrip ({pick})"+(" — aligned square crop" if aligned else ""),
        source=[f"{d}/{pick}_frames.json"] if d else None, key_column="batch")

chosen={}; ALIGNED_STATUS={}
_CAT_ONLY=[c for c in os.environ.get("CAT_ONLY","").split(",") if c]
# TRACED_ONLY=1 -> skip the per-category example strips and go straight to the traced_cell strip at the
# end of this file. Added 2026-08-18: traced_cell is the ONLY figure produced by default mode that the
# decks link individually, and rebuilding it meant re-rendering every category strip -- the same scope
# expansion flagged on 08-04 and again on 08-17. Its PUBLICATION twin had gone stale for exactly this
# reason (nobody wanted to pay for a full default run to refresh one figure).
_TRACED_ONLY=bool(os.environ.get("TRACED_ONLY"))
for cat,fn in CATS.items():
    if _TRACED_ONLY: break
    if _CAT_ONLY and cat not in _CAT_ONLY: continue
    cands=[b for b in mr if fn(b) and render_dir(b) and b not in TS_EXCLUDE.get(cat,set())]
    rng.shuffle(cands)
    cands.sort(key=lambda b: 0 if b in CURATED else 1)   # prefer user-curated timestrip cells
    if cat in PINNED and render_dir(PINNED[cat]): cands=[PINNED[cat]]+[c for c in cands if c!=PINNED[cat]]
    if cat=="unmanipulated-control":
        pick=next((b for b in cands if mon_ok(b) and mon_trange(b)),None)
        if not pick: print(f"  {cat}: none with readable monitoring channels"); continue
        chosen[cat]=pick
        t0,t1=mon_trange(pick); mt=lib.parse_time(mr.get(pick,{}).get("Metaphase Start (s)","")); at=lib.parse_time(mr.get(pick,{}).get("Anaphase Onset (s)",""))
        ct=lib.parse_time(mr.get(pick,{}).get("Cytokinesis Onset (s)",""))
        # feedback: DROP the 00:00:01 'start' frame; show prometaphase->metaphase->anaphase->cytokinesis.
        pan=[]
        if mt is not None and t0<mt: pan.append(("Monitoring",t0+(mt-t0)*0.5,"prometaphase",None))
        if mt is not None: pan.append(("Monitoring",mt,f"metaphase {_hms(mt)}",None))
        if at is not None: pan.append(("Monitoring",at,f"anaphase {_hms(at)}",None))
        if ct is not None: pan.append(("Monitoring",ct,f"cytokinesis {_hms(ct)}",None))
        elif at is None: pan.append(("Monitoring",t1,"end",None))
        # TIGHT-square crop for consistency with every other timestrip (cell fills the frame; no distortion).
        # square_aligned routes through square_crop -> ts_render.tight_square (needs an outline). Fall back to the
        # default tight crop only if the control has no manual outline.
        ok=make_strip(pick,pan,f"{OUT}/{cat}",title=f"Unmanipulated control — {pick}",square_aligned=True)
        if not ok: ok=make_strip(pick,pan,f"{OUT}/{cat}",title=f"Unmanipulated control — {pick}")
        print(f"  {cat}: {pick} {'ok' if ok else 'FAIL'}")
        record_category(cat,pick,pan)
        continue
    # pinned cells used even if they lack ablation_events (off-target shows the ablation-movie portion)
    pick=next((b for b in cands if (b in PINNED.values() and movies_ok(b)) or valid_abl(b)),None)
    if not pick: print(f"  {cat}: NONE with 4 readable movies + ablation events"); continue
    chosen[cat]=pick
    _pan,_specs=cat_panels(pick)
    _noclose=(cat=="off-target")   # T12: no ablation close-ups for off-target strips
    ok=make_strip(pick,_pan,f"{OUT}/{cat}",closeup_specs=_specs,title=f"{cat} ablation — {pick}",do_closeups=not _noclose)
    print(f"  {cat}: {pick}  ({len(abl_events_render(pick))} abl events) {'ok' if ok else 'FAIL'}")
    record_category(cat,pick,_pan)
    # SQUARE-ALIGNED variant (user feedback): main + zoom + monitoring tiles at ONE square footprint, columns aligned
    okA=make_strip(pick,_pan,f"{OUT}/{cat}_aligned",closeup_specs=_specs,
                   title=f"{cat} ablation (aligned square crop) — {pick}",do_closeups=not _noclose,square_aligned=True)
    ALIGNED_STATUS[cat]=("ok" if okA else "SKIP (no outline)")
    print(f"  {cat}_aligned: {ALIGNED_STATUS[cat]}")
    if okA:
        record_category(cat,pick,_pan,plot_id=f"{cat}_aligned",aligned=True)   # 2026-08-04: make it checkable
json.dump(chosen,open(f"{OUT}/_chosen.json","w"),indent=1)
# S6: any chosen cell whose phase is rendered GREEN and fluor GRAY has the _Phase_/_Fluor_ files swapped
# (we read the correctly-colourised file to render, but the SOURCE still needs re-processing).
for _cat,_b in chosen.items():
    if channels_swapped(_b): flag_reprocess(_b,"phase rendered GREEN + fluor GRAY: _Phase_/_Fluor_ channels swapped — re-render")

# ===== traced strip: outline on BOTH phase+fluor, DEFAULT crop (full pipeline frame), scale bars =====
# different cell than before (exclude ablations_1 AND the prior pick four_ablation_62); full frame so the
# burned-in 'Brightfield' label stays in view and the crop matches the pipeline's default region.
# S8: THICKER outline + the cell ROUNDNESS value printed beneath each frame-set (column).
TRACE_TH=5   # outline stroke (was 2) — easier to see
def poly_roundness(pts):
    """4*pi*Area / Perimeter^2 of the (closed) outline polygon — same metric as the roundness plot."""
    p=np.array(pts,float)
    if len(p)<3: return None
    x,y=p[:,0],p[:,1]
    A=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
    per=np.sum(np.hypot(np.diff(np.append(x,x[0])),np.diff(np.append(y,y[0]))))
    if per==0: return None
    r=4*np.pi*A/per**2
    return r if 0<r<=1.2 else None
_TRACED_EXCLUDE={"20251104 ablations_1","20250930 four_ablation_62"}
traced_cands=[b for b in mon_outlines if len(mon_outlines[b])>=4 and movies_ok(b) and b not in _TRACED_EXCLUDE]
if traced_cands:
    tb=sorted(traced_cands,key=lambda b:-len(mon_outlines[b]))[0]
    # sort on t_sec ONLY. Entries are (t_sec, pts); a bare sorted() compares the tuples, so two outlines
    # sharing a t_sec fall through to comparing the numpy point arrays and raise
    # "operands could not be broadcast together with shapes (119,2) (152,2)". Same-t_sec outlines are
    # normal — a fractured kinetochore is traced as several polygons on one frame. Lines 431/482 already
    # key on p[0]; this one did not. Fixed 2026-07-29.
    outs=sorted(mon_outlines[tb],key=lambda p:p[0])
    pxs=ps(tb)
    # TIGHT-square crop (ts_render.tight_square via square_crop) so the traced cell fills the frame like every
    # other timestrip; ONE box reused for all frames; the outline is shifted into the crop -> no distortion.
    sq=square_crop(tb)
    capP=movie(tb,"Phase","Monitoring"); capF=movie(tb,"Fluor","Monitoring")
    # 2026-08-17 (§1 rule 29, NO BLACK PANELS): the 5 timepoints used to be picked by linspace over ALL
    # outlines, then any channel with no frame at that t was stacked in as `np.zeros_like(ref)` — a solid
    # BLACK tile. The Fluor monitoring movie is SHORTER than the Phase one here, so the last three columns
    # of `traced_cell.png` were black boxes on the live deck (artboard 4). Restrict the choice to the span
    # both channels actually cover, so every tile drawn is real data. Clamp, never pad.
    def _tspan(cap_ts):
        if not cap_ts: return None
        _ts=cap_ts[1]
        return (float(np.min(_ts)), float(np.max(_ts))) if len(_ts) else None
    _spans=[s for s in (_tspan(capP), _tspan(capF)) if s]
    if _spans:
        _lo=max(s[0] for s in _spans); _hi=min(s[1] for s in _spans)
        _ok=[o for o in outs if _lo-1e-6 <= o[0] <= _hi+1e-6]
        if len(_ok) >= 2: outs=_ok
        else: print(f"  traced {tb}: channels overlap on <2 outlines — keeping full range")
    idxs=np.linspace(0,len(outs)-1,min(5,len(outs))).astype(int); sel=[outs[i] for i in sorted(set(idxs))]
    # ─────────────────────────────────────────────────────────────────────────────────────────────────────
    # 2026-08-17 — STANDARDISED. Her instruction: "for the one timestrip thats consistently a problem, just
    # standardize it." This block used to hand-stack its own raster and burn its own text with cv2.putText,
    # which is why it was the ONLY strip that ever went wrong: black placeholder tiles, timestamps clipped
    # off the tile, a caption band sliced in half and bleeding into the next column, five scale bars, and
    # "10um" because cv2/HERSHEY is ASCII-only. It now goes through ts_render.assemble + ts_render.emit like
    # EVERY other timestrip, which gives it for free:
    #   * matplotlib text -> a real "10 µm", correct sizes, nothing clipped, EDITABLE text in the SVG
    #   * the `_notext.png` variant and the `_frames.json` sidecar every other strip has
    #   * automatic PNG->SVG->PDF mirroring through lib.apply_style, so the deck link updates itself
    #     (this strip previously needed its PDF regenerated BY HAND after every render)
    #   * the shared SEP/gap, scale-bar and timestamp conventions, so it matches the others on the page
    # The per-column roundness value is passed as the new `caption` panel key (see ts_render.assemble).
    # The cv2 `scalebar()`/`label()`/`_fs_for()` helpers now have NO caller and are left only for reference.
    panels=[]
    for _ci,(t,pts) in enumerate(sel):
        rd=poly_roundness(pts)
        d={'t':t,'caption':(f"roundness {rd:.3f}" if rd is not None else "roundness n/a")}
        for ch,cap_ts,key in (("Phase",capP,'phase'),("Fluor",capF,'fluor')):
            fr=grab(*cap_ts,t) if cap_ts else None
            if fr is None: continue
            fr=fr.copy(); dpts=pts
            if sq: x0,y0,x1,y1=sq; fr=ts_render.crop_pad(fr,sq).copy(); dpts=pts-np.array([x0,y0])
            cv2.polylines(fr,[dpts.astype(np.int32)],True,(80,220,255),ts_render.stroke_px(fr))   # outline on BOTH channels
            d[key]=fr
        # §1 rule 29 — never a black tile: assemble() fills a missing channel with zeros, so a column that
        # lacks one is dropped outright rather than rendered as a black box (the artboard-4 defect).
        if not any(d.get(k) is not None for k in ('phase','fluor')):
            continue
        if capP and capF and (d.get('phase') is None or d.get('fluor') is None):
            print(f"  traced {tb}: t={t:.0f}s missing a channel — column dropped (no black tile)")
            continue
        panels.append(d)
    if capP: capP[0].release()
    if capF: capF[0].release()
    if panels:
        _res=ts_render.assemble(panels, pxs, ts_render.nice_scalebar_um(panels[0].get('phase',panels[0].get('fluor')).shape[1]*pxs))
        if _res:
            _raster,_geom=_res
            ts_render.emit([("traced", _raster, _geom)], f"{OUT}/traced_cell",
                           title=f"cell shape through mitosis — {tb}")
            print(f"  traced: {tb}  ({len(panels)} columns, standardised via ts_render)")
        else:
            print(f"  traced {tb}: assemble() returned nothing — strip not written")
# ---- flush reprocess flags to _review/timestrip_reprocess.csv (dedup) ----
_rp=[(m,b,v,r) for (m,b,v,r) in lib.REVIEW if m=="timestrip_reprocess"]
with open(f"{REVDIR}/timestrip_reprocess.csv","w",newline="") as _f:
    _w=csv.writer(_f); _w.writerow(["metric","batch","value","reason"]); _seen=set()
    for m,b,v,r in _rp:
        if (b,r) in _seen: continue
        _seen.add((b,r)); _w.writerow([m,b,v,r])
print(f"reprocess-flagged batches: {len({b for _,b,_,_ in _rp})} -> {REVDIR}/timestrip_reprocess.csv")
print("aligned-variant status:", ALIGNED_STATUS)
print("timestrips2 done")
