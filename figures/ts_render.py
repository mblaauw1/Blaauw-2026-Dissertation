# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""Shared timestrip render primitives — ONE consistent font, editable-text Illustrator output.

Used by group_timestrips.py, group_frap_timestrips.py, group4_polar_timestrips.py.

Design (07-07 feedback T1/T2/T7):
 * A timestrip is a list of PORTIONS (ablation strip, each ablation close-up, monitoring strip).
 * Each portion is a raster mosaic (phase row over fluor row) built by `assemble()` with NO text burned in
   (only the image, the magenta ablation X marks, and the white scalebar BAR are drawn into the raster).
 * `emit()` writes:
     <prefix>_notext.png  — the raster (scalebar BAR kept, NO text) for manual Illustrator labelling  [T7b]
     <prefix>.png         — the WITH-text version, rendered in matplotlib so ALL text is one font/size    [T1/T7a]
     illustrator/<prefix>.svg (+ _ai_relink pdf) via lib's savefig wrapper — text SELECTABLE/EDITABLE and
                            each PORTION is its own <g> group (own matplotlib axes) => movable independently [T2]
 * timestamp & scalebar-label share FS_MAIN (same size, T7). channel labels share it too (T1).
"""
import os, numpy as np, cv2, csv as _csv
import lib

# ---- ablation-marker source: PREFER manual pre_abl marks over the PAS aim point; NO fluor-flash refine ----
# (user 2026-07-20: manual markings are ground-truth for the KT; the flash-refine landed on cytoplasm/noise.)
_PRE_ABL_CACHE = None
def manual_pre_abl_local(batch):
    """Manual pre_abl kinetochore marks for `batch` as [(x,y), ...] in CROPPED/video-pixel space (the same space
    the timestrip markers use). [] if the batch has no manual pre_abl annotation. Read once from kt_points.csv."""
    global _PRE_ABL_CACHE
    if _PRE_ABL_CACHE is None:
        _PRE_ABL_CACHE = {}
        p = "/Volumes/4 MB/annotations/kt_points.csv"
        if os.path.isfile(p):
            for r in _csv.DictReader(open(p)):
                if (r.get("label") or "").strip() == "pre_abl":
                    try: _PRE_ABL_CACHE.setdefault(r["batch"].strip(), []).append((float(r["x"]), float(r["y"])))
                    except Exception: pass
    return list(_PRE_ABL_CACHE.get(batch, []))

TILE_OUT_PX_FWD = 380.0   # kept equal to TILE_OUT_PX below; the font size is derived from it
# one consistent font everywhere (matplotlib family from lib.apply_style: Helvetica/Arial/DejaVu)
# USER 2026-08-10: "the text is waaaaaay too small, please make A TON bigger."
# A tile is TILE_OUT_PX/220 in wide (=1.73 in), so the old fixed 12 pt was under 10% of a frame and shrank to
# nothing once a 10-column strip was placed on a board. Sizing it FROM the tile keeps it right on every strip
# instead of being correct only at one column count: 0.30 * tile width, i.e. ~37 pt at the current geometry.
# 0.30 of the tile (37 pt) was too much -- USER: "that text size is too big lol / it takes up the whole
# frame". 0.18 gives ~22 pt: clearly bigger than the original 12 pt but back inside the frame.
FS_FRAC = 0.18          # label height as a fraction of one frame's width -- the SAME on every strip
FS_MAIN = TILE_OUT_PX_FWD / 220.0 * 72.0 * FS_FRAC   # nominal value; emit() recomputes per strip
FS_PHASE = FS_MAIN
SEP = 4         # separator WIDTH between frames within a row
# USER 2026-08-19 (all-figures item 4), on the unmodified-cell strip: "the style of the timestrip needs to
# match the style used for monitoring timestrips elsewhere (such as, but not limited to, using white and not
# grey between the frames)". The separator was value 20 -- near-black, which reads as a dark rule between
# tiles and, on the fluorescence rows, is nearly invisible against the frame so the tiles run together.
# White is the journal norm and is what she asked for; it is applied to EVERY strip family, not just the one
# she pointed at, per NOTES §1 rule 4 (apply feedback to every instance of a type).
SEP_VAL = 255
GAP = 20        # gap between stacked portions

# A SPACER panel: a blank tile that holds a COLUMN POSITION without showing an image.
# USER 2026-08-19 (all-figures item 3): "for the ablation timestrips, if it includes both a zoom line and a
# line above that with whole-cell frames for the frames with the ablation targets, the whole-cell frame needs
# to be aligned above the corresponding zoom frame that its timepoint matches (instead of just in a line with
# the other ablation whole-cell frames; its confusing)."
# The whole-cell row has ONE tile per ablation and the zoom row has THREE, so the rows never lined up. Rather
# than re-laying the finished raster (which would leave the burned-in scalebar and every text coordinate
# behind), the whole-cell row is now BUILT at the zoom row's column count, with blank spacers either side of
# each whole-cell tile. assemble() then derives widths, separators, scalebar and text geometry correctly by
# itself, because as far as it is concerned this is just a row with more panels.
def spacer_panel(like, chans=("fluor",)):
    """A white tile the same size as `like`'s rendered channel, carrying no timestamp and no label."""
    ref = None
    for c in ("fluor", "phase"):
        if like is not None and like.get(c) is not None: ref = like[c]; break
    if ref is None: return None
    blank = np.full(ref.shape, SEP_VAL, np.uint8)
    out = {"t": None, "phase_label": None, "spacer": True}
    for c in chans: out[c] = blank.copy()
    return out

def mmss(t, force_h=False):
    """Timestamp label. USER 2026-08-05: "the timestamps for this timestrip start out as just MM:SS and
    then become HH:MM:SS which means the first few are inconsistent with how the timestamp units are
    specified to be HH:MM:SS" — the per-frame switch below used to be decided by EACH timestamp's own
    value, while the format INDICATOR under the first frame is decided by the strip's MAXIMUM. Any strip
    that crosses an hour therefore declared HH:MM:SS and still drew its early frames as MM:SS.
    `force_h` lets the caller impose ONE format on the whole strip, so the frames and the indicator agree."""
    s=int(round(t)); sign='-' if s<0 else ''; s=abs(s)
    if force_h or s>=3600:
        return f"{sign}{s//3600}:{(s%3600)//60:02d}:{s%60:02d}"
    return f"{sign}{s//60}:{s%60:02d}"

_NICE_UM = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 5.0, 10.0, 20.0, 50.0]
def nice_scalebar_um(frame_um, frac=1/3.0):
    """A scale bar about `frac` of the frame width, snapped to a conventional value.

    USER 2026-08-04, for the ablation zooms: "it should be about 1/3 the length of the frame, so its not too
    long and not too short, so if 1um is too long or too short then use some other value like .75um or
    1.5um." Rather than hard-coding a guess per zoom size, pick the value from the conventional ladder that
    lands closest to a third of the frame — which gives 1 um on the small zooms and steps up sensibly when a
    zoom window is wider."""
    if not frame_um or frame_um <= 0: return 1.0
    target = frame_um * frac
    return min(_NICE_UM, key=lambda v: abs(v - target))


def assemble(panels, pxs, scalebar_um, chan_labels=("Phase","eYFP-Cdc20"), fluor_only=False, show_fmt=True):
    """panels: list of dicts {'phase':bgr|None,'fluor':bgr|None,'t':sec|None,'phase_label':str|None}.
    Returns (raster_bgr_no_text, geom) or None. geom['texts'] = [(x,y,text,ha,va,kind)] in raster px coords.
    fluor_only=True DROPS the phase/brightfield row entirely (ablation-format strips are FLUOR ONLY)."""
    panels=[p for p in panels if p is not None]
    # UNIVERSAL FRAME CAPTURE. build_panel only covers group_timestrips; the Mad1 / Hec1 / drug builders
    # construct their panels themselves, so their strips had no recorded frames. EVERY builder goes
    # through assemble(), and each panel already carries its timepoint, so log here instead.
    try:
        for _p in panels:
            _t=_p.get('t')
            if _t is not None: PANEL_LOG.append(("panel", float(_t)))
    except Exception:
        pass
    if fluor_only:   # ablation-format timestrips render FLUOR ONLY — no phase/brightfield panel is rendered
        panels=[{**p,'phase':None} for p in panels]
    chans=[c for c in ('phase','fluor') if any(p.get(c) is not None for p in panels)]
    if not chans or not panels: return None
    # drop panels that carry NO rendered channel (e.g. a frame that only had phase, now dropped by fluor_only)
    panels=[p for p in panels if any(p.get(c) is not None for c in chans)]
    if not panels: return None
    H=min(p[c].shape[0] for p in panels for c in chans if p.get(c) is not None)
    widths=[]
    for p in panels:
        ref=p.get('phase') if p.get('phase') is not None else p.get('fluor')
        widths.append(max(1,int(round(ref.shape[1]*H/ref.shape[0]))))
    rows={}; xoff=[]; totalw=0
    for c in chans:
        ims=[]; xs=[]; x=0
        for i,p in enumerate(panels):
            w=widths[i]; fr=p.get(c)
            fr=cv2.resize(fr,(w,H)) if fr is not None else np.zeros((H,w,3),np.uint8)
            xs.append(x); ims.append(fr); ims.append(np.full((H,SEP,3),SEP_VAL,np.uint8)); x+=w+SEP
        rows[c]=np.hstack(ims[:-1])
        if c==chans[0]: xoff=xs; totalw=x-SEP
    midsep=np.full((SEP,totalw,3),SEP_VAL,np.uint8)
    stacked=[]
    for i,c in enumerate(chans):
        stacked.append(rows[c])
        if i<len(chans)-1: stacked.append(midsep)
    raster=np.vstack(stacked)
    row_h=H
    # scalebar BAR bottom-right of the bottom row (kept in BOTH versions)
    barlen=max(3,int(round(scalebar_um/pxs)))
    bar_th=12                                      # THICKER still (8 -> 12), user 2026-08-04: the bar has to read
                                                   # as a deliberate scale bar, not a hairline
    # The bar belongs at the right edge of the last REAL frame. A row that carries spacer tiles (the
    # whole-cell ablation row, aligned over its zoom columns -- item 3, 2026-08-19) ends in white, and the
    # bar was being drawn white-on-white out there with its label stranded beside it.
    _last_real=len(panels)-1
    while _last_real>0 and panels[_last_real].get("spacer"): _last_real-=1
    _right = (xoff[_last_real]+widths[_last_real]) if _last_real < len(xoff) else totalw
    bx1=min(totalw,_right)-8; bx0=max(2,bx1-barlen); by=raster.shape[0]-8
    cv2.rectangle(raster,(bx0,by-bar_th),(bx1,by),(255,255,255),-1)
    # ---- text geometry (rendered later in matplotlib; NOT burned into raster) ----
    texts=[]
    # time-format label (MM:SS / HH:MM:SS) printed as a 2nd line under the LEFTMOST timestamped frame only
    _tvals=[p['t'] for p in panels if p.get('t') is not None]
    _useh=bool(_tvals) and max(abs(v) for v in _tvals)>=3600
    _fmt="HH:MM:SS" if _useh else "MM:SS"   # ONE format for the whole strip; every frame below uses it
    _first_ts=True
    for i,p in enumerate(panels):
        cx0=xoff[i]; w=widths[i]
        if p.get('t') is not None:
            _lbl=mmss(p['t'], force_h=_useh)
            if _first_ts and show_fmt: _lbl=f"{_lbl}\n{_fmt}"   # 2nd line = the time format (same font); main strips only
            _first_ts=False
            texts.append((cx0+5,6,_lbl,'left','top','time'))
        # 2026-08-17: optional PER-COLUMN caption (e.g. the roundness value under each traced frame). Added so
        # the traced_cell strip could stop hand-stacking its own cv2 caption band -- that band was a fixed 30px
        # holding ~40px text, so it sliced the value in half and bled into the next column. Placed BOTTOM-LEFT
        # of the FIRST row: timestamps own the top-left, the scale bar owns the bottom-right of the LAST row,
        # so a caption can never collide with either. Purely additive -- panels without 'caption' are unchanged.
        if p.get('caption'):
            texts.append((cx0+5,row_h-6,str(p['caption']),'left','bottom','time'))
        # NOTE: on-frame mitotic-stage / descriptor text (prometa/meta/ana/cytokinesis, start/mid/late,
        # unaligned/biorientation/anaphase onset) is INTENTIONALLY NOT drawn (user feedback: remove stage
        # text from timestrip frames). phase_label is still accepted for back-compat but never rendered;
        # KEEP only the timestamp, time-format line, channel label, and scalebar.
    # USER 2026-08-10: "you dont need to put 'phase' or '488', etc, on any frame." The channel is obvious
    # from the image and stated in the caption, so the label is no longer drawn. chan_labels stays in the
    # signature because every builder passes it; it is simply not rendered.
    _ = chan_labels
    # scalebar label centred just above the bar
    # USER 2026-08-10: "the text over the timestrip looks a little strange because the u is overlappng the
    # bar in a really embelished way." Two causes, both fixed: the label sat only 6 px above a 5-px-thick bar
    # so a descender-less micro sign still touched it, and U+00B5 MICRO SIGN picks up a decorative glyph in
    # this face. Use U+03BC GREEK SMALL LETTER MU, which the text faces draw plainly, and give real clearance.
    um=scalebar_um; lab=(f"{um:g} \u03bcm")
    # right-anchored to the bar's right end, not centred on it: the bar sits 8 px from the panel edge, so a
    # label wider than the bar ran off the image and was clipped mid-word ("2.5 µr"). 2026-08-04.
    texts.append((bx1, by-int(round(FS_MAIN*0.9)), lab,'right','bottom','scale'))
    geom={"w":raster.shape[1],"h":raster.shape[0],"texts":texts}
    return raster, geom

def resize_panels(panels, N, mark_r=None):
    """Square-aligned helper: resample every panel's phase/fluor tile to exactly NxN px (square footprint).
    Downscale uses INTER_AREA, upscale INTER_CUBIC. Returns NEW panel dicts (originals untouched). Used by the
    `square_aligned` timestrip variant so main/monitoring/zoom tiles all share one square page footprint."""
    out=[]
    for p in panels:
        if p is None: out.append(None); continue
        q=dict(p)
        for k in ('phase','fluor'):
            im=q.get(k)
            if im is not None and im.size:
                h,w=im.shape[:2]
                if h!=w:
                    # 2026-08-17 (§1 rule 29): CENTRE-CROP the LONGER side instead of ZERO-PADDING the shorter
                    # one. Squaring by padding wrote a literal black band down/across every `_aligned` tile —
                    # the second source of black bars on these strips, and the one that survived the
                    # drop_burnin fix (3-sisterless_aligned still showed bands of mean 1.7 and 0.1 on a render
                    # made minutes after it). Her rule is explicit: "take some off of the side of the frame ...
                    # so the black bar isnt needed." Cropping still NEVER stretches — the kept window is square,
                    # so the later resize to NxN stays uniform — and no pixel is fabricated; we simply show a
                    # slightly narrower field on the long axis rather than inventing black to fill it.
                    s=min(h,w)
                    y0=(h-s)//2; x0=(w-s)//2
                    im=im[y0:y0+s, x0:x0+s]
                interp=cv2.INTER_AREA if im.shape[0]>N else cv2.INTER_CUBIC
                q[k]=cv2.resize(im,(N,N),interpolation=interp)   # square -> square: uniform scale, no distortion
        out.append(q)
    return out

# ---- CROSS-BATCH aligned-crop standard (07-07 feedback) ------------------------------------------------
# One FIXED physical window shared by EVERY ablation timestrip so all cells render at the SAME magnification
# with the SAME scale-bar length, regardless of pixel size (0.062 vs 0.031 µm/px). Used by the `_aligned`
# variants in group_timestrips / group4_polar_timestrips / group5_mad1_examples.
STD_MAIN_UM = 78.0            # main-tile square window (µm). Clamped to the frame short side (65.5µm on the
                             #  1248x1056 0.062µm/px acquisitions) -> uniform across those batches.
# USER 2026-08-19: "the zooms for ablations can universally have more zoom (make sure page footprint still
# the same but the zoom ROI can be smaller (not full-cell frames though)". So the WINDOW shrinks and the tile
# does not: `zoom_to_square` always upscales its crop to ALIGN_N, so the printed tile is the same size on the
# artboard and only the magnification changes. 4.34 -> 3.00 µm half = a 6.0 µm window, 1.45x more zoom.
# This is the ONE constant every zoom/close-up row reads (group_timestrips, group4_polar, group5_mad1,
# group_drug_ablation), so the change is uniform across every strip family, which is what "universally" means.
# It also shrinks the box drawn on the whole-cell frame (group_timestrips ~line 1480), correctly: that box
# advertises the zoom region and must follow it. Whole-cell/monitoring crops are untouched.
STD_ZOOM_HALF_UM = 3.00      # µm half-width -> 6.0 µm zoom window (was 70*0.062 = 4.34 µm -> 8.7 µm)
# USER 2026-08-06: box footprint must be the SAME on every strip. figw was a fixed 10in, so at 220 dpi
# every strip came out 2200 px wide however many columns it had: 8 columns gave 275 px per box, 4 gave 550.
# Box size — and so apparent font size — tracked the column count. Fix the TILE and let the page grow.
TILE_OUT_PX = 380.0          # output px per box at 220 dpi, identical across strips

def stroke_px(img_or_w, out_px=6.0):
    """Stroke width in SOURCE pixels that lands at `out_px` in the FINAL tile.

    USER 2026-08-20 (artboard 8, item 4): "for frames/timestrips/etc that have a manual annotation
    overlay, the lines/marks/ etc need to be shown with much thicker lines on the figures for an
    audience so they can easily see what is being talked about".

    WHY A HELPER AND NOT A BIGGER CONSTANT. Every panel is resampled to a fixed output tile
    (TILE_OUT_PX / ALIGN_N) before it is assembled, so a stroke measured in SOURCE pixels does not
    survive: 5 px drawn on a 700 px crop lands at ~2.7 px on the page, while the same 5 px drawn on a
    300 px crop lands at ~6 px. That is why the marks read thin on the wide strips and uneven between
    strips. Scaling the stroke by the crop width fixes both at once -- every mark is the same weight on
    the printed page no matter how tight its crop -- and it keeps working when a crop is retuned later.
    """
    w = float(getattr(img_or_w, "shape", [0, img_or_w])[1]) if hasattr(img_or_w, "shape") else float(img_or_w)
    return max(2, int(round(out_px * w / TILE_OUT_PX)))

ALIGN_N = 420                # NxN display footprint for EVERY aligned tile (main + zoom + monitoring).

# ---- PER-BATCH manual crop nudge (art-direction knob) --------------------------------------------------
# batch name -> (dx, dy, scale_mult). dx/dy shift the crop-box CENTRE in ORIGINAL-frame px (+dx=right, +dy=down)
# so the box hugs the cell instead of the auto-centroid; scale_mult<1 SHRINKS the box (tighter framing / more
# zoom), >1 loosens. Box SIZE + the uniform-scale rules are otherwise unchanged — ONLY where the box sits.
# Tuned by eye per cell; the auto default (0,0,1.0) frames the rest fine.
# PER-BATCH absolute crop SHRINK, in microns taken off EVERY side (side -= 2*value).
# USER 2026-08-10: "for ... 20260417 ptk2 eyfp cdc20 ablation_1, i need you to make the whole-cell crops
# about 10um shorter on all sides". CROP_OFFSETS' scale_mult is a RATIO, so the same multiplier removes a
# different number of microns from every cell; she asked in microns, so this is in microns.
# PER-BATCH ASYMMETRIC trim, microns off (top, right, bottom, left).
# USER 2026-08-10: "the FRAP (aligned square crop) - 20250711 double ablation_18 (#0) timestrip: i need you
# to crop the whole-cell frame by ... 10um off the top, 5um off each side, and 4um off the bottom ... i still
# want it to fit the footprint of the alignment so adjust as needed."
# Trimming unequally makes the window non-square, which the aligned layout cannot use, so after applying her
# four numbers the largest SQUARE inside the trimmed rectangle is taken, centred on it. Her asymmetry
# therefore lands as a re-CENTRING (10 off the top vs 4 off the bottom shifts the view down by 3 um) plus an
# overall tightening, which is the honest way to honour both the trim and "fit the footprint".
CROP_TRIM_UM = {
 # USER 2026-08-10, 20260303 Mad1_Ptk_Eyfpmad1_ablation_10: "for all of the whole cell frames, take off about 5um from the lft ad right
 # sides, and then 10um from the bottom (should keep the aligned ratio)". 5+5 off the width and 10 off
 # the height are equal reductions, so the window stays square by itself -- the aligned ratio is kept
 # with no forced re-squaring -- and dropping 10 from the bottom re-centres the view 5 um UP.
 "20260303 Mad1_Ptk_Eyfpmad1_ablation_10": (0.0, 5.0, 10.0, 5.0),   # (top, right, bottom, left)
 # USER 2026-08-10, 20250402 ptk_yfpcdc20_22: "crop all of the frames by thaking off 15um from the top and 15um from the
 # right side". Equal amounts off one vertical and one horizontal edge, so the window stays square on
 # its own and the trim lands purely as a 7.5 um shift left + 7.5 um down plus a 15 um size reduction.
 "20250402 ptk_yfpcdc20_22": (15.0, 15.0, 0.0, 0.0),   # (top, right, bottom, left)
 "20250711 double ablation_18": (10.0, 5.0, 4.0, 5.0),
}

CROP_SHRINK_UM = {
 # She named the strip "2-sisterless ablation (aligned square crop)", and that strip IS ablation_19 --
 # its rebuilt registry carries her ablation-2 frames 39/42/111. There is no 2-sisterless strip for
 # ablation_1 (that batch is only referenced as a 3-sisterless exclusion), so the strip she named is
 # the instruction and the trailing digits were the slip.
 "20260417 ptk2 eyfp cdc20 ablation_19": 10.0,
}

CROP_OFFSETS = {
 # USER 2026-08-10: "for 3-sisterless-20260417 ptk2 eyfp cdc20 ablaiton_18 ... move the ROI for the
 # whole cell frames down about 3um". 3 um / 0.062 um-per-px = 48 px, +dy = down. Position only;
 # box size and scale are untouched.
 "20260417 ptk2 eyfp cdc20 ablation_18": (0, 48, 1.0),
 "20260304 Mad1_timelapse_2_xy10": (37, 94, 0.33),   # auto-bbox grabbed neighbour cells -> recentre on THE Mad1 cell (650,562) + tighten hard (off top+left bg) so it fills ~90%
 "20260304 Mad1_timelapse_1_xy6":  (26, -20, 0.88),  # up+right + tighter all sides (bottom+left come in most)
 "20260310 ptk2_eyfp_mad1_14":     (-289, 118, 0.92),  # brightfield detect landed ~290px RIGHT of the real fluor cell -> recentre onto the pole cell (375,630) + slight tighten (tall cell fills ~90% vertically)
 # hec1 xy4: old (-55,-37,0.7) box sat LEFT of the KTs (dots at x657-916) -> move RIGHT+UP + LOOSEN so the KT
 # ring (y~440) and the green cell body (749,630) are both in view across all 3 frames.
 "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy4": (234, -30, 1.0),   # sm 1.6->1.0 (2026-07-10): fixed-px rad cap now sizes the box uniformly; keep the position nudge only
 # hec1 xy6: old default box was 118px = far too tight -> only frame-1 KTs shown. Green cell is stationary at
 # (892,560); centre there and WIDEN so the cell stays framed across all frames (Hec1 dots genuinely fade by
 # mid/late anaphase — a physical limit, not fixable by cropping; box is anchored to keep the cell in view).
 "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy6": (18, 25, 1.0),   # sm 3.45->1.0 (2026-07-10): fixed-px rad cap now sizes the box uniformly; keep the position nudge only
}

_PXCACHE = {}
def _batch_px(batch, default=0.062):
    """Pixel size for a batch, for knobs specified in MICRONS rather than pixels."""
    if batch in _PXCACHE: return _PXCACHE[batch]
    v = default
    try:
        rows, _ = lib.load_master()
        for r in rows:
            if r.get("Batch Name") == batch:
                v = float(r.get("Pixel Size (um)", "") or default); break
    except Exception:
        pass
    _PXCACHE[batch] = v
    return v

def tight_square(pts, W, H, margin=1.12, batch=None):
    """UNIFORM-SCALE-BEFORE-CROP square window (x0,y0,x1,y1) around a detected cell bbox. This is the crop-box
    half of the scale-before-crop primitive: it sizes a square window = max(bbox_w,bbox_h)*margin (so the CELL
    fills ~1/margin ≈ 89% of the box — cell fills the frame, small breathing room, edges not clipped) and
    CENTRES it on the cell (bbox
    centre, + any per-batch CROP_OFFSETS nudge). The box is NOT clamped/shrunk to the frame and is NOT shifted to
    stay inside it — so a cell bigger than the frame, or near an edge, still gets a full square window; the box
    may extend past the frame and `crop_pad` edge-pads the overflow. Downstream (`crop_pad` + `resize_panels`, or
    the height-fit assemble) then uniformly scales that square to NxN => the cell always fits at a CONSISTENT
    fill, no clipping, no distortion. Forced EXACTLY square so the later resize is uniform."""
    x0b,y0b=float(pts[:,0].min()),float(pts[:,1].min()); x1b,y1b=float(pts[:,0].max()),float(pts[:,1].max())
    cx=(x0b+x1b)/2.0; cy=(y0b+y1b)/2.0
    dx,dy,sm=CROP_OFFSETS.get(batch,(0.0,0.0,1.0)) if batch else (0.0,0.0,1.0)
    cx+=dx; cy+=dy
    side=max(x1b-x0b, y1b-y0b)*margin*sm
    _shr=CROP_SHRINK_UM.get(batch) if batch else None
    if _shr:
        _px=_batch_px(batch)
        side=max(24.0, side - 2.0*_shr/_px)      # never shrink below a usable box
    _trim=CROP_TRIM_UM.get(batch) if batch else None
    if _trim:
        _px=_batch_px(batch)
        _t,_r,_b,_l=[v/_px for v in _trim]
        _w=side-(_l+_r); _h=side-(_t+_b)
        cx+=(_l-_r)/2.0; cy+=(_t-_b)/2.0         # unequal trim re-centres the window
        side=max(24.0, min(_w,_h))               # largest square inside the trimmed rect: keeps the footprint
    half=side/2.0
    x0=int(round(cx-half)); y0=int(round(cy-half)); x1=int(round(cx+half)); y1=int(round(cy+half))
    s=min(x1-x0, y1-y0); x1=x0+s; y1=y0+s   # force EXACTLY square (kill off-by-one from rounding)
    return (x0,y0,x1,y1)

BURNIN_PX = 64      # acquisition overlay band burned into the rendered movies (top and bottom)

def drop_burnin(fr, band=None):
    """Blank the acquisition overlay burned into the movie pixels (channel name, timestamp, scale bar).

    USER 2026-08-10: "you dont need to put 'phase' or '488', etc, on any frame." Those are PIXELS in the
    rendered movies, so no drawing change removes them. Every builder that reads movie frames should call
    this before cropping -- it lives here because three separate builders each had their own frame reader
    and each needed the same fix (group_timestrips, group_frap_timestrips, and the custom strip builders).
    Only the top/bottom band of the FULL frame is touched, so a crop away from the frame edge is untouched.

    Blanking the band to BLACK removed the text but replaced it with a hard black bar wherever a crop
    reached the frame edge (visible on the FRAP and lagging strips). The band is therefore REPLICATED from
    the nearest clean row instead: the overlay disappears, and the edge stays continuous with the image.

    2026-08-17 — THE REPLICATED ROW IS NOW FOUND, NOT ASSUMED. `BURNIN_PX` (64) is a GUESS at the band
    height, and on some renders the real overlay is TALLER, so row `-b-1` was still INSIDE the black band and
    this function faithfully replicated BLACK across the bottom 64 rows -- a rule-29 black bar produced by the
    very code meant to prevent one. It hides from a full-width check because the band is dark only across the
    overlay's own x-range; it is what put a black bar under every tile of the traced_cell strip on artboard 4
    (exactly 64 rows deep -- the tell). So walk inward to the first row that is actually CLEAN and replicate
    THAT. The search is capped so a genuinely dark frame (an all-black brightfield during the ablation shot)
    cannot send it across the image; if nothing clean is found the original row is used, i.e. never worse.

    2026-08-17 (SECOND FIX, and it RETIRES the replication above) — USER: "some timestrips have the
    distorted lines on the edges that almost look like if the frames were dragged and could leave a trail."
    That trail IS this function. Replicating one row across 64 rows writes 64 IDENTICAL rows of real image
    texture, which reads exactly like a drag smear wherever a crop reaches a frame edge. A scan of the 149
    rendered strips found the signature on 44 of them (worst: 58 replicated rows on the hec1 strip, 57 on
    nf9_double-chromosome). BOTH earlier flavours were wrong for the same underlying reason: they FABRICATE
    pixels to fill a region the crop should never have entered.

    THE BAND IS NOT PART OF THE IMAGE — SO TREAT IT AS OUTSIDE THE FRAME. `crop_pad` now clamps every crop
    into the usable rows, so the overlay can never appear and nothing is invented; a crop that wanted those
    rows is recentred (or zoomed, per the 2026-08-17 ROI rule) exactly as it already is at a real frame edge.
    This function therefore returns the frame UNCHANGED and, critically, THE SAME SIZE — mark coordinates
    come from the annotations in full-frame px and are drawn before cropping, so trimming here would shift
    every mark by `band` px. Callers that consume a frame WHOLE (no crop_pad) should call `trim_burnin`.
    """
    return fr

def usable_band(fr, band=None):
    """(top, bottom) row limits of `fr` that carry real image, i.e. the frame minus the acquisition overlay.
    `band` may be an int (same at top and bottom) or a (top, bottom) pair for a per-batch bottom overlay.
    Degrades to the whole frame when the frame is too short to spare the band, so a small crop source can
    never be reduced to nothing."""
    if fr is None: return 0, 0
    # EXPLICIT OPT-IN. The overlay band exists only in the pipeline's rendered MP4s; the TIF planes several
    # builders crop through the same primitive carry no overlay at all, and silently excluding 64 rows from
    # those would throw away real image. So `band=None` means "this frame has no overlay".
    if band is None: return 0, fr.shape[0]
    bt, bb = (band, band) if np.isscalar(band) else band
    bt = BURNIN_PX if bt is None else int(bt)
    bb = BURNIN_PX if bb is None else int(bb)
    H = fr.shape[0]
    if H <= 3 * (bt + bb): return 0, H          # frame too short to spare it -> keep everything
    return bt, H - bb

def trim_burnin(fr, band=None):
    """Physically REMOVE the overlay band. Honest (nothing fabricated) but it CHANGES the frame height, so it
    is only for frames consumed whole, after any marks have been drawn — never at read time."""
    if fr is None: return fr
    t, b = usable_band(fr, band)
    return fr[t:b]

def crop_pad(fr, box, band=None):
    """Crop `box`=(x0,y0,x1,y1) out of `fr`, SLIDING the box inside the frame rather than filling any part
    (instead of clipping the cell). Returns EXACTLY (y1-y0)x(x1-x0) px — so when `box` is square a later resize
    to NxN is uniform and never distorts. This is the applier half of the scale-before-crop primitive: pair it
    with `tight_square` (which may hand back an out-of-frame square window) so a cell that doesn't fit the frame
    is framed at a consistent fill via padding rather than being clipped. A plain in-frame box behaves exactly
    like `fr[y0:y1,x0:x1]`, so it is a safe drop-in for the old slicing everywhere."""
    x0,y0,x1,y1=int(round(box[0])),int(round(box[1])),int(round(box[2])),int(round(box[3]))
    # ── 2026-08-17: THE ACQUISITION OVERLAY BAND IS OUTSIDE THE FRAME ─────────────────────────────
    # `drop_burnin` used to fabricate those rows (black, then a replicated row) and the replication is
    # what she saw as "distorted lines on the edges ... like if the frames were dragged and could leave
    # a trail". Nothing is fabricated any more: the band is simply not croppable, so every rule below —
    # slide back inside, or shrink around the requested centre — operates on the USABLE rows and a crop
    # that reached the overlay is recentred instead of smeared. Coordinates stay FULL-FRAME for the
    # caller (marks are drawn before cropping); only this function knows about the offset.
    _t,_b = usable_band(fr, band)
    if _t or _b != fr.shape[0]:
        fr = fr[_t:_b]
        y0 -= _t; y1 -= _t
    H,W=fr.shape[:2]
    xs0,ys0=max(0,x0),max(0,y0); xs1,ys1=min(W,x1),min(H,y1)
    if xs1<=xs0 or ys1<=ys0:                 # box entirely outside the frame -> black tile of the right size
        shp=(y1-y0,x1-x0,fr.shape[2]) if fr.ndim==3 else (y1-y0,x1-x0)
        return np.zeros(shp,fr.dtype)
    # ── NOTES §1 rule 29 (user 2026-08-16) ────────────────────────────────────────────────────────
    # "you have a black bar taking up space in the frame instead of having it be the whole image ... you
    # should be able to take some off of the side of the frame to both achieve the crop i want and restore
    # proportions so the black bar isnt needed."  BOTH fill flavours are banned: BORDER_CONSTANT prints the
    # black bar, BORDER_REPLICATE smears the edge (the documented cause of the ptk2_eyfp_mad1_14 horizontal
    # banding). So instead of filling the overflow:
    #   1. if the requested box FITS in the frame, SLIDE it back inside — same size, same magnification,
    #      slightly recentred, nothing invented;
    #   2. if the box is genuinely LARGER than the frame, shrink it to the largest window of the same
    #      aspect that does fit, centred on the requested centre, then resize up to the requested output
    #      size. That is "take some off the side and restore proportions" — the aspect and the exact
    #      returned dimensions are preserved (callers rely on that for a uniform later resize), and no
    #      pixel is fabricated.
    bw, bh = x1 - x0, y1 - y0
    if bw <= W and bh <= H:
        nx0 = min(max(0, x0), W - bw); ny0 = min(max(0, y0), H - bh)
        return fr[ny0:ny0 + bh, nx0:nx0 + bw]
    sc = min(W / float(bw), H / float(bh))              # box bigger than the frame in at least one axis
    cw, ch = max(1, int(bw * sc)), max(1, int(bh * sc))
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    nx0 = int(round(min(max(0, cx - cw / 2.0), W - cw)))
    ny0 = int(round(min(max(0, cy - ch / 2.0), H - ch)))
    sub = fr[ny0:ny0 + ch, nx0:nx0 + cw]
    if sub.size == 0: return np.zeros((bh, bw, fr.shape[2]) if fr.ndim == 3 else (bh, bw), fr.dtype)
    return cv2.resize(sub, (bw, bh), interpolation=cv2.INTER_LINEAR)

def scale_crop(fr, bbox_pts, N, fill=0.8, batch=None):
    """Standalone UNIFORM-scale-before-crop primitive: given a frame + a detected cell bbox (4x2 pts, full-frame
    px) + a fixed box size N + a target fill fraction, UNIFORMLY scale the frame by
    s = min((N*fill)/bbox_w, (N*fill)/bbox_h)  (a SINGLE scale factor -> NEVER distorts), then crop the fixed
    NxN box centred on the scaled cell centroid (+CROP_OFFSETS nudge, scaled), edge-padding overflow. Guarantees
    the cell fits at ~`fill` of the box regardless of its size. Used where the caller can't route through the
    tight_square+resize_panels box pipeline (e.g. the height-fit hec1 strip)."""
    pts=np.asarray(bbox_pts,float)
    x0b,y0b=float(pts[:,0].min()),float(pts[:,1].min()); x1b,y1b=float(pts[:,0].max()),float(pts[:,1].max())
    bw=max(1.0,x1b-x0b); bh=max(1.0,y1b-y0b)
    dx,dy,sm=CROP_OFFSETS.get(batch,(0.0,0.0,1.0)) if batch else (0.0,0.0,1.0)
    s=min((N*fill)/bw,(N*fill)/bh)/max(sm,1e-6)        # scale_mult<1 -> zoom in more
    interp=cv2.INTER_AREA if s<1 else cv2.INTER_CUBIC
    scaled=cv2.resize(fr,(max(1,int(round(fr.shape[1]*s))),max(1,int(round(fr.shape[0]*s)))),interpolation=interp)
    cx=((x0b+x1b)/2.0+dx)*s; cy=((y0b+y1b)/2.0+dy)*s
    x0=int(round(cx-N/2.0)); y0=int(round(cy-N/2.0))
    return crop_pad(scaled,(x0,y0,x0+N,y0+N))

def fluor_cell_bbox_pts(plane, central=0.42):
    """RELIABLE cell-body bbox for outline-less cells (colcemid/noc/ZM/Mad1) — replaces the fragile OTSU-blob
    detector that collapsed to a ~20px box on diffuse cells and over-zoomed tight_square into pure noise.
    Method: robust INTENSITY CENTROID of the bright signal in the central window, then RADIUS = the disk about
    that centroid holding ~85% of the bright mass. The radius is CLAMPED to [0.24, 0.46] x the short frame dim,
    so the resulting crop can NEVER collapse to a noise-sized patch, nor blow past the frame — while still
    adapting: a compact cell gives a tighter crop, a diffuse one a looser (but honest) one. Returns 4x2 pts."""
    from scipy.ndimage import gaussian_filter
    a=plane.astype(np.float32); H,W=a.shape
    sm=gaussian_filter(a,8.0)
    cy0,cx0=H//2,W//2; ry,rx=int(H*central),int(W*central)
    ys,xs=np.mgrid[cy0-ry:cy0+ry, cx0-rx:cx0+rx].astype(np.float32)
    win=sm[cy0-ry:cy0+ry, cx0-rx:cx0+rx]
    w=np.clip(win-np.percentile(win,70),0,None)          # bright-signal weight (top ~30% of the central window)
    short=min(H,W)
    if w.sum()<=0:
        cx,cy,rad=float(cx0),float(cy0),0.34*short
    else:
        cx=float((xs*w).sum()/w.sum()); cy=float((ys*w).sum()/w.sum())   # intensity centroid = cell centre
        d=np.hypot(xs-cx,ys-cy).ravel(); wr=w.ravel(); order=np.argsort(d)
        cum=np.cumsum(wr[order]); rad=float(d[order][min(np.searchsorted(cum,0.72*cum[-1]),len(d)-1)])  # 72% mass -> tighter on the cell body
    rad=min(max(rad,0.19*short),0.46*short)              # FLOOR (no noise-zoom) + relaxed CEIL (bigger cells not cut off)
    return np.array([[cx-rad,cy-rad],[cx+rad,cy-rad],[cx+rad,cy+rad],[cx-rad,cy+rad]],float)

def brightfield_cell_bbox_pts(bf, central=0.42):
    """Cell bbox from a BRIGHTFIELD frame — for outline-less cells whose FLUOR is too diffuse to delineate.
    A mitotic/arrested cell is REFRACTILE + internally TEXTURED (chromosomes, bright rim) against smoother
    background, so use LOCAL STD (texture) as the 'signal' and reuse the robust centroid + clamped-radius
    estimator (fluor_cell_bbox_pts)."""
    from scipy.ndimage import uniform_filter
    a=bf.astype(np.float32) if bf.ndim==2 else cv2.cvtColor(bf,cv2.COLOR_BGR2GRAY).astype(np.float32)
    m=uniform_filter(a,15); m2=uniform_filter(a*a,15)
    tex=np.sqrt(np.clip(m2-m*m,0,None))        # local std = texture map; the cell body lights up, background stays low
    return fluor_cell_bbox_pts(tex, central=central)

def std_square_crop(cx, cy, W, H, pxs, um=STD_MAIN_UM):
    """Fixed PHYSICAL square window (`um`) centred on full-frame px centroid (cx,cy). Side = um/pxs, clamped to
    the frame so it never exceeds bounds; shifted (not shrunk) to stay in-frame. Same physical size => same
    magnification across batches. Returns (x0,y0,x1,y1)."""
    side=min(um/pxs, W, H); half=side/2.0
    x0=int(round(cx-half)); y0=int(round(cy-half)); x1=int(round(cx+half)); y1=int(round(cy+half))
    if x0<0: x1-=x0; x0=0
    if y0<0: y1-=y0; y0=0
    if x1>W: x0-=(x1-W); x1=W
    if y1>H: y0-=(y1-H); y1=H
    return (max(0,x0),max(0,y0),x1,y1)

def zoom_half_px(pxs):
    """Fixed-PHYSICAL zoom half-window in px for this batch (const µm across batches => same physical zoom)."""
    return max(8,int(round(STD_ZOOM_HALF_UM/pxs)))

def zoom_to_square(fr, x, y, half, mark, N=ALIGN_N):
    """Crop a fixed 2*half px box around (x,y) (CLAMPED inside the frame, never padded; rule 29), optional magenta X marker, upscale to
    NxN. `half` should come from zoom_half_px(pxs) so the physical zoom window is identical across batches."""
    xi,yi=int(round(x)),int(round(y)); h,wd=fr.shape[:2]; box=2*half
    x0,y0=xi-half,yi-half
    # NOTES §1 rule 29 (user 2026-08-16): no black bars. A box overhanging the frame used to be pasted onto
    # a zeros canvas, printing a black band; SLIDE it back inside instead — same size, same magnification,
    # slightly recentred. Only a frame genuinely smaller than the box is trimmed rather than filled.
    if wd >= box and h >= box:
        x0 = min(max(0, x0), wd - box); y0 = min(max(0, y0), h - box)
        canvas = fr[y0:y0+box, x0:x0+box].copy()
    else:
        x0 = max(0, min(x0, max(0, wd - box))); y0 = max(0, min(y0, max(0, h - box)))
        canvas = fr[y0:min(h, y0+box), x0:min(wd, x0+box)].copy()
    if canvas.size == 0: return None
    # clamping moves the point off the tile centre, so the marker must follow it
    # USER 2026-08-17: the ablation marker is an open-centre X, not a circle -- see draw_x below. This is
    # the CLOSE-UP tile every strip family routes through, so fixing it here is what makes the zoom rows
    # match their whole-cell rows instead of each builder having to be patched.
    if mark: draw_x(canvas, xi-x0, yi-y0, r=max(4,int(round(9*box/140.0))))
    return cv2.resize(canvas,(N,N),interpolation=cv2.INTER_NEAREST)

# FRAME REGISTRY (2026-08-10). Nothing recorded which frames a published strip actually shows, so the
# timestrip-setup slides had to say "auto-selected by the builder's default rule" — not acceptable, and not
# necessary: every builder routes its panels through build_panel, which appends (batch, role, t_sec) here.
# emit() dumps whatever accumulated for this figure and clears, so each strip lands with its real times.
PANEL_LOG = []


def emit(portions, out_prefix, title=None, max_w=4600, max_h=3000):
    """portions: list of (portion_name, raster, geom). Writes _notext.png (cv2) + .png (matplotlib editable)."""
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    lib.apply_style()   # installs the savefig SVG/PDF wrapper -> illustrator/<name>.svg with editable text
    portions=[p for p in portions if p is not None and p[1] is not None]
    if not portions: return False
    W=max(r.shape[1] for _,r,_ in portions)
    # ---- WITHOUT-text raster (scalebar bar kept) ----
    stack=[]
    for i,(_,r,_) in enumerate(portions):
        # pad with the SEPARATOR colour, never zeros: a black pad is exactly the "black bar taking up space
        # in the frame" she banned (NOTES rule 29). With item 3's spacer columns the ablation and zoom
        # portions now come out the same width anyway, so this is a backstop, not the normal path.
        r2=np.pad(r,((0,0),(0,W-r.shape[1]),(0,0)),constant_values=SEP_VAL) if r.shape[1]<W else r
        stack.append(r2)
        if i<len(portions)-1: stack.append(np.full((GAP,W,3),20,np.uint8))
    notext=np.vstack(stack)
    s=min(max_w/notext.shape[1],max_h/notext.shape[0],1.0)
    nt=cv2.resize(notext,(int(notext.shape[1]*s),int(notext.shape[0]*s)),interpolation=cv2.INTER_AREA) if s<1 else notext
    cv2.imwrite(out_prefix+"_notext.png",nt)
    try:
        import json as _j, collections as _c
        if PANEL_LOG:
            byrole=_c.defaultdict(list); batch=None; times=[]
            for _e in PANEL_LOG:
                if len(_e)==3:
                    _b,_r,_t=_e; batch=batch or _b; byrole[_r].append(round(float(_t),2))
                else:
                    times.append(round(float(_e[1]),2))
            out={"batch": batch, "title": title,
                 "ablation": byrole.get("Ablation",[]), "monitoring": byrole.get("Monitoring",[])}
            if times and not (out["ablation"] or out["monitoring"]):
                out["times"]=sorted(set(times))       # builders that bypass build_panel: times only
            _j.dump(out, open(out_prefix+"_frames.json","w"), indent=1)
        del PANEL_LOG[:]
    except Exception as _e:
        print(f"  (frame registry not written for {out_prefix}: {_e})")
    # ---- WITH-text editable version (one matplotlib axes per portion = one movable SVG group) ----
    heights=[r.shape[0] for _,r,_ in portions]
    Htot=sum(heights)+GAP*(len(portions)-1)
    _ncols = max(1, int(round(W / float(ALIGN_N))))
    figw = max(6.0, _ncols * TILE_OUT_PX / 220.0)     # constant box size; page width follows the columns
    # USER 2026-08-11: "the text size seems to differ with respect to which timestrip its on. it should be the
    # same relative size on all of the aligned frames ... so that when all of the timestrips are expanded the
    # text will be the same size". FS_MAIN is a fixed POINT size, which is only the intended fraction of a
    # frame while the column width equals TILE_OUT_PX. The max(6.0, ...) floor breaks that: a 2-3 column strip
    # is stretched to a 6 in page, its frames render 2-3 in wide instead of 1.73, and the same 22.4 pt reads
    # 10-16% of a frame instead of 18%. Deriving the size from the ACTUAL column width makes it a constant
    # FRACTION OF THE FRAME on every strip, which is what stays equal when they are scaled to a common size.
    _col_in = figw / max(1, _ncols)
    _fs_main = _col_in * 72.0 * FS_FRAC
    _fs_phase = _fs_main
    figh=figw*Htot/W
    # title band: tall enough that a (short, single-line) title sits ENTIRELY above the frame grid with clear
    # air — the frames start at `avail`, the title text occupies ~0.2in starting 0.18in below the top, so a
    # 0.5in band leaves >0.1in clearance and NEVER overlaps the first frame row. (Grown from 0.32in, which let
    # even one title line kiss the top frames.) Callers must pass a SHORT title (no long descriptive subtitle).
    title_h=0.5 if title else 0.0
    fig=plt.figure(figsize=(figw,figh+title_h))
    avail=figh/(figh+title_h)
    if title:
        # SHRINK-TO-FIT title. The size was fixed, so a narrow strip clipped its title at both ends (the
        # 4-panel lagging strip rendered "gging-stretch-rebound - ... metaphase_"). Estimate the drawn width
        # and scale down only when it would overrun; wide strips keep FS_MAIN+2 exactly as before.
        _fs=_fs_main+2
        _est=len(title)*0.60*_fs/72.0          # ~0.60 em average glyph advance for this face
        if _est>figw*0.96: _fs=max(5.0,_fs*figw*0.96/_est)
        fig.text(0.5,1-0.18/(figh+title_h),title,ha='center',va='top',fontsize=_fs)
    top=avail
    # USER 2026-08-04: "Fix labels for scalebars/timestamps/etc as they look weird right now / not consistent
    # with literature. Should be the same size font as they are now, and in white text."
    # The dark rounded pill behind every label was the un-literature-like part. Published micrographs carry
    # plain white text directly on the image. Legibility on bright backgrounds is kept with a thin black
    # OUTLINE on the glyphs instead of a filled box — and, unlike converting text to paths, a stroke leaves
    # the SVG text editable in Illustrator (T2).
    import matplotlib.patheffects as _pe
    _txt_fx=[_pe.withStroke(linewidth=max(2.0, _fs_main*0.16), foreground='black')]
    bbox=None
    for pname,r,geom in portions:
        fh=r.shape[0]/Htot*avail
        aw=r.shape[1]/W
        ax=fig.add_axes([0.0, top-fh, aw, fh])
        ax.imshow(cv2.cvtColor(r,cv2.COLOR_BGR2RGB),extent=[0,r.shape[1],r.shape[0],0],aspect='auto',
                  interpolation='nearest')
        ax.set_xlim(0,r.shape[1]); ax.set_ylim(r.shape[0],0); ax.axis('off')
        ax.set_gid("portion__"+pname.replace(' ','_'))
        for (tx,ty,txt,ha,va,kind) in geom["texts"]:
            fs=_fs_phase if kind=='phase' else _fs_main
            ax.text(tx,ty,txt,color='white',fontsize=fs,ha=ha,va=va,zorder=5,
                    fontweight='bold',bbox=bbox,gid=f"{kind}_label",path_effects=_txt_fx)
        top-=(fh+GAP/Htot*avail)
    fig.savefig(out_prefix+".png",dpi=220)
    plt.close(fig)
    return True

# ---- ablation marker ----
# 2026-08-17: an open-centre X replaces the circle everywhere. Her words: "instead of big bulky circles, a
# more streamlined, sleek figure ... like a + symbol where the center is at the point of ablation, or
# another shape if something else is more common in literature". The literature check settled it on the X:
# in laser-ablation mitosis figures the ablation SITE is marked with an X (the Dumont-lab k-fibre
# convention) or a lightning glyph, while circles and arrowheads are reserved for STRUCTURES -- which is
# also why the circle was ambiguous here, since this project circles KINETOCHORES. MAGENTA, never red
# (rule 30: no red on the green fluorescence panels). The centre is left OPEN so the glyph points at the
# ablation site without covering it.
def draw_x(img,x,y,color=(255,0,255),r=None):
    if r is None: r=max(9,int(0.011*img.shape[1]))
    xi,yi=int(round(x)),int(round(y))
    g=max(2,int(round(r*0.55))); L=int(round(r*1.9)); th=max(2,int(round(r*0.20)))
    for sx,sy in ((-1,-1),(1,1),(-1,1),(1,-1)):
        cv2.line(img,(xi+sx*g,yi+sy*g),(xi+sx*L,yi+sy*L),color,th,cv2.LINE_AA)

def draw_circle(img,x,y,color=(255,0,255),r=None):
    """Kept as a thin alias so any caller still asking for the old marker gets the NEW one -- there must
    not be two ablation markers alive in the project at once."""
    draw_x(img,x,y,color=color,r=r)
