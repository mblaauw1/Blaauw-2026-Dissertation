"""Group 5 / IF3 — Hec1 timestrips + Hec1/Mad1 dot quantification.

Comment-flagged Hec1 (Mad1+Hec1-halo) timelapse batches on 20260313 (from the master Notes):
 * ...Hec1halo_640_4_xy5 — the ONLY one with explicit frames-to-pull: 1:25 (unaligned) / 7:22 (complete
   biorientation) / 15:04 (anaphase onset).  This one also gets the Hec1/Mad1 dot-intensity violins.
 * ...Hec1halo_640_4_xy2 / _xy4 / _xy6 — flagged "good timelapse ... hec1 marks all KTs while Mad1 only
   marks SAC-active KTs" but WITHOUT specified frames -> we auto-pick 3 representative monitoring timepoints
   (first / middle / last) and label them start / mid / late with their timestamps.  (07-07 feedback IF4 raw
   L727: "make timestrips for the hec1 batches I flag" — earlier only xy5 was built; xy2/xy4/xy6 added here.)

07-07 feedback (IF3, raw L321-322) applied to EVERY Hec1 timestrip:
 * channel-label / timestamp OVERLAP -> labels live in a left gutter + a top caption bar (NEVER burned on the
   image), one consistent font/size (cv2 FONT_HERSHEY_SIMPLEX 0.6).  The old "item 1:.."/"unaligned.." title
   text lines are removed.
 * Hec1 (640) is DIM -> read the RAW *_Cropped.tif (not the compressed mp4) and percentile-stretch hard so the
   dots are visible.  Hec1 -> HOT-PINK (kinetochore Hec1 marker), Mad1 (488) green, brightfield gray.
 * CROP set from the Hec1 signal on the FIRST timestrip frame, applied UNIFORMLY to all frames / all channels.

Hec1/Mad1 dot quantification (xy5): find the Hec1 dots IN EACH of the 3 frames; at each dot measure Hec1 AND
Mad1 (488) intensity at the SAME location -> violin per channel per frame (6 violins).
 Sanity: Hec1 ~constant across frames; Mad1 drops frame1->frame2 then ~flat.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, json, numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter, maximum_filter
import lib, ts_render
from matplotlib.lines import Line2D

# ---------------------------------------------------------------------------------------------------
# AOI (crop) BOX POSITION -- one place to hand-tune where each Hec1 timestrip's crop window sits.
# (dx, dy, scale_mult): dx/dy shift the box CENTRE in original-frame px from the auto-detected Hec1-dot-
# cluster centroid (+dx = right, +dy = down); scale_mult < 1 TIGHTENS the box (zooms in / more magnified),
# > 1 LOOSENS it (zooms out / shows more of the cell). 1.0 = no change from the auto-detected box.
# EDIT THESE NUMBERS DIRECTLY, then re-run:  HEC1_ONLY=xy2,xy4,xy5,xy6 python3 group5_hec1_timestrip.py
# (applied via ts_render.tight_square's batch-keyed CROP_OFFSETS -- synced into it right below, so this
# dict is the single source of truth for the 4 Hec1 batches; do not also hand-edit ts_render.CROP_OFFSETS
# for these 4 keys, it will just be overwritten here on the next run).
#   xy5: "zoom out frames a bit" (her 2026-08-03 request) -- scale_mult 1.0 -> 1.2 (+20% looser). If that
#        isn't enough, raise it further (e.g. 1.3-1.4); nothing else needs to change.
#   xy2 / xy4 / xy6: she wants the AOI box placed BY HAND for these -- I can't judge "where" from here, so
#        this is the editable knob for her to do it. xy4/xy6 start from their last art-directed position
#        (carried over from the old ts_render.CROP_OFFSETS entries, 2026-07-10); xy2 has never been
#        manually positioned (starts at 0,0,1.0 = auto box, untouched).
# ---------------------------------------------------------------------------------------------------
# USER 2026-08-03: "xy6, xy2, xy4 manually place AOI box". Placing a box by hand is not something that can
# be done for her, so the AOI is set from what the frames actually show, using the SAME rule she gave for
# xy5 ("zoom out frames a bit"): widen until the whole cell is in frame rather than clipped at an edge.
# xy2 was never positioned and its cell was cut off at the top; xy4 and xy6 keep their 2026-07-10 pan
# (which centres the right cell) and gain the same widening. Each value is a single number she can change.
# PER-PANEL ROI nudge, microns, {suffix: {column_index: (dx_um, dy_um)}}; +dx = right, +dy = down.
# USER 2026-08-10: "the hec1 mad1 three-frame strip: i need you to move the roi for just the third panel
# (rightmost panel) to the right about 15um". AOI_OFFSET above moves the box for the WHOLE strip, so it
# cannot express "just this column" -- this does. Column index is 0-based, so the rightmost of three is 2.
PANEL_SHIFT_UM = {
    # 🔴 RETIRED 2026-08-21, and this is why. Her 08-10 "move the roi for just the third panel to the right
    # about 15um" and her 08-11 "left about 5um, down about 5um" were art-directed on the frame the third
    # column showed AT THE TIME -- 15:04. On 2026-08-19 that column was corrected: 640 exists on only 6 of
    # the 16 monitoring frames, so the third column now shows 12:52, where the cell sits somewhere else.
    # Measured on the current frames (probe_xy5_roi): with the +10/+5 nudge still applied, the kinetochore
    # cluster in the third column lands 12.2 um LEFT and 8.0 um UP of the box centre -- outside a 19.0 um
    # box. That is the displacement she is pointing at ("why is it disaplced like that??").
    # A hand offset in microns cannot survive a change of frame; PANEL_TRACK below does the same job from
    # the data, so the panel stays on the cell whichever frame it shows.
    # (Leave this dict here: it is still the right knob for a deliberate off-centre framing.)
}

AOI_OFFSET = {
    "xy2": (0,   -40, 1.25),  # was (0,0,1.0): cell clipped at top -> pan up + widen 25%
    "xy4": (234, -30, 1.2),   # keep the 2026-07-10 pan, widen 20% to match xy5
    "xy5": (0,   0,   1.2),   # "zoom out frames a bit" (2026-08-03) -- +20% looser
    "xy6": (18,  25,  1.2),   # keep the 2026-07-10 pan, widen 20% to match xy5
}
for _suf, _off in AOI_OFFSET.items():
    ts_render.CROP_OFFSETS[f"20260313 ptk_eyfp_mad1_Hec1halo_640_4_{_suf}"] = _off

OUT  = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
SESS = "/Volumes/4 MB/pipeline_session_output/20260313"
SCRIPT = __file__
EXTRA_KEY = "640 (Cy5)"

HOTPINK = (180, 105, 255)  # BGR of RGB(255,105,180)
GREEN   = (0, 255, 0)
PANEL_H = 360
FONT = cv2.FONT_HERSHEY_SIMPLEX; FS = 1.14   # 1.9x of 0.6 (user 2026-08-10: text much bigger)
# rows = (label, channel, colour, (lo_pct, hi_pct), gamma). Hec1 dots are faint -> very aggressive stretch + gamma lift.
# FLUOR ONLY (phase/brightfield row dropped, cross-cutting rule); channel labels by MOLECULE (journal standard).
# Mad1 LOW ANCHOR 30 -> 86 (user 2026-08-06: "mad1 looks very overexposed or something. when imaging its
# easy to tell the kinetochores in mad1 apart from background in the first frame but how youve tuned the
# display here (its not)"). Measured on this batch: her cytosol background sits at the 86.6 / 84.1 / 88.5
# percentile of the three frames, so a black point at p30 lifted the ENTIRE cytoplasm into mid-green and
# the puncta could not separate from it. p86 puts black at the cytoplasm level, the same idea as Hec1's
# p80 anchor, so only above-background structure shows.
GREY    = (255, 255, 255)   # brightfield is rendered greyscale, not tinted

# USER 2026-08-17: "if Hec1/Mad1 phase — yes, then add this channel to the timestrip displayed in my
# illustrator document ... and use the middle channel of phase, as we did for phase in cdc20 movies".
# The phase row had been dropped by the fluor-only cross-cutting rule, but nothing else had to be built:
# the phase stack was ALREADY loaded (`STACKS["phase"] = <B>_Phase_Cropped.tif`) and `raw_plane` already
# resolves `chan == "phase"` through `frame["phase_tif_idx"]` — which is the pipeline's MID-Z brightfield
# index, the same plane the cdc20 movies and the IF sheets use. So this is one row, not a new pipeline.
# Placed FIRST so phase sits above the fluorescence, matching every other strip on the decks. A mild
# 2-99.5 percentile stretch: brightfield needs contrast, not the aggressive puncta lift the fluor rows use.
ROWS = [("Phase",     "phase", GREY,    (2, 99.5),   1.0),
        ("eYFP-Mad1", "mad1",  GREEN,   (86, 99.9),  1.0),
        ("Hec1-Halo", "hec1",  HOTPINK, (80, 99.99), 0.6)]


# ---------------- raw single-channel stacks ----------------
def read_stack(path):
    """These pipeline *_Cropped.tif are written as MANY single-page TIFF SERIES (one 2-D page per frame),
    so tifffile.imread() returns ONLY page 0 -> every frame collapses to frame-0 (the root cause of the
    identical per-frame violins/timestrip columns). Explicitly stack ALL pages -> a real (n,H,W) volume."""
    with tifffile.TiffFile(path) as tf:
        return np.stack([pg.asarray() for pg in tf.pages])

def _plane(stk, idx):
    a = stk
    if a.ndim == 2: return a.astype(np.float32)
    if a.ndim == 3: return a[min(idx, a.shape[0]-1)].astype(np.float32)
    a = np.squeeze(a)
    return _plane(a, idx) if a.ndim < stk.ndim else a[min(idx, a.shape[0]-1)].astype(np.float32)


# ---------------- per-batch state ----------------
def load_batch(B):
    RD = f"{SESS}/{B}"
    fj = json.load(open(f"{RD}/{B}_frames.json"))
    mon = [f for f in fj["frames"] if f["role"] == "monitoring"]
    return {"B": B, "RD": RD, "fj": fj,
            "PX": float(fj.get("pixel_size_um", 0.062)),
            "mon": mon, "mon_ts": [f["t_sec"] for f in mon],
            "STACKS": {"phase": read_stack(f"{RD}/{B}_Phase_Cropped.tif"),
                       "mad1":  read_stack(f"{RD}/{B}_Fluor_Cropped.tif"),
                       "hec1":  read_stack(f"{RD}/{B}_640_Cy5_Cropped.tif")}}

# 640 (Hec1) IS NOT ACQUIRED EVERY MONITORING FRAME. On xy5 it exists on 6 of the 16 monitoring frames
# (t = 85, 429, 772, 1115, 1459, 1803 s); the other ten carry an EMPTY `extra_tif_idx`.
# USER 2026-08-19 (all-figures item 5): "i worry that the frames youre displaying for phase are not the
# correct frames that correspond to the fluorescent frames, evidenced by placement of the chromosomes and
# metaphase plate. Resolve by finding the correct phase frames."
# She is right that the rows did not correspond, and the cause is findable: `frame_for_t` picked the nearest
# monitoring frame REGARDLESS of whether it had a 640 plane, `raw_plane` then fell back to `fluor_tif_idx`,
# and `_plane` CLAMPED that index to the last page of the 6-page 640 stack. On xy5's third column (requested
# 15:04 -> frame 899 s, no 640) the Hec1 row was therefore silently showing the LAST 640 frame of the movie,
# 1803 s -- a completely different timepoint from the phase and Mad1 panels beside it.
# Fix at the source: only frames that carry EVERY channel this figure draws are selectable, so the three rows
# always show the same instant. The nearest such frame to 15:04 is 12:52, and it is labelled 12:52.
def frame_for_t(bat, t, require=("phase", "mad1", "hec1")):
    def has(f, chan):
        if chan == "phase": return f.get("phase_tif_idx") is not None
        if chan == "mad1":  return f.get("fluor_tif_idx") is not None
        return (f.get("extra_tif_idx") or {}).get(EXTRA_KEY) is not None
    pool = [f for f in bat["mon"] if all(has(f, c) for c in require)] or bat["mon"]
    return min(pool, key=lambda f: abs(f["t_sec"] - t))

def raw_plane(bat, chan, frame):
    if chan == "phase": idx = frame["phase_tif_idx"]
    elif chan == "mad1": idx = frame["fluor_tif_idx"]
    else:                idx = (frame.get("extra_tif_idx") or {}).get(EXTRA_KEY)
    if idx is None:
        # was `.get(EXTRA_KEY, frame["fluor_tif_idx"])` -- a fallback onto the WRONG channel's index, which
        # `_plane` then clamped into range. Silent, and it put a different timepoint on the Hec1 row.
        raise KeyError(f"{chan}: frame t={frame.get('t_sec')} has no {EXTRA_KEY} plane "
                       f"(frame_for_t should have excluded it)")
    n = bat["STACKS"][chan].shape[0]
    if int(idx) >= n:
        raise IndexError(f"{chan}: index {idx} past the end of a {n}-page stack "
                         f"(frame t={frame.get('t_sec')})")
    return _plane(bat["STACKS"][chan], int(idx))


# ---------------- image helpers ----------------
def stretch(a, lo_p, hi_p, gamma=1.0, lo=None, hi=None):
    """UNIFORM-EXPOSURE: pass explicit lo/hi (pooled ONCE over a whole row's frames) so every frame of that row
    shares ONE fixed intensity mapping (no per-frame auto-normalisation). lo/hi=None -> per-frame percentiles."""
    a = a.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)   # gamma<1 lifts the dim mid-tones (faint Hec1 dots)
    return (n * 255).astype(np.uint8)

def colorize(g8, bgr):
    if bgr is None: return cv2.cvtColor(g8, cv2.COLOR_GRAY2BGR)
    out = np.zeros((*g8.shape, 3), np.float32)
    for i, c in enumerate(bgr): out[..., i] = g8.astype(np.float32) * (c / 255.0)
    return out.astype(np.uint8)

def find_dots(hec_raw):
    sm = gaussian_filter(hec_raw.astype(np.float32), 1.5)
    mx = maximum_filter(sm, size=7)
    thr = max(np.percentile(sm, 99.0), sm.mean() + 3*sm.std())
    pk = np.argwhere((sm == mx) & (sm > thr))         # (y,x) peaks
    pk = sorted(pk, key=lambda yx: -sm[yx[0], yx[1]])[:60]   # brightest up to 60 dots
    return pk

def disk_mean(a, y, x, r=2):
    h, w = a.shape; y0, y1 = max(0, y-r), min(h, y+r+1); x0, x1 = max(0, x-r), min(w, x+r+1)
    return float(a[y0:y1, x0:x1].mean())

MAD_RAW_VALUES = []   # every pre-floor Mad1 measurement, for the floor-vs-abs diagnosis
MAD_PEAK_XY = []      # refined Mad1 peak per mad_at_dot() call, for the fold-over-bg sibling

def mad_at_dot(mad, y, x, rsearch=3, rmeas=1):
    """Mad1 (488) intensity at a Hec1 (640) KT dot. THE BUG: the 488 and 640 channels have a small (~2 px)
    chromatic/registration offset, so sampling Mad1 with a disk centred on the *Hec1* pixel lands beside the
    Mad1 punctum and averages in cytoplasm -> Mad1 reads as pure background (F1 only +20, F2/F3 +5 above bg;
    the whole Mad1 set squashed to the floor). Diagnosis (per-frame): the bright Mad1 puncta sit 1-5 px from the
    Hec1 dots, and a Mad1 local-peak search recovers +40 above bg at F1 (vs +7 at random locations) collapsing to
    ~random by F2/F3 == the expected SAC drop. FIX: refine to the Mad1 LOCAL PEAK within a tight rsearch window
    (KT-registration scale, small enough not to jump to a neighbouring KT) then measure a compact r=rmeas disk
    there. Symmetric with Hec1, which is likewise measured at its own detected peak.
    BG-SUBTRACTED (above a LOCAL annulus around the refined peak, not a distant cytosol patch — a distant
    patch is what actually caused the negatives, see lib.disk_local_bg's own docstring), floored at 0 --
    fluorescence can't be negative.
    2026-08-03 (feedback "Mad1 should not have negative fluorescence value"): re-verified on the live xy5
    data (the only batch that feeds G5_hec1_mad1_dot_quant) with THIS function AND with the naive
    pre-fix method (Hec1-centred, no peak refine, still lib.disk_local_bg) -- 0 of 64 dots negative either
    way on the current annotations/frames (raw min +159 a.u., i.e. this dataset never drove the bug this
    session). The max(0.0, ...) floor is kept anyway as a physical guarantee, not because it is currently
    doing anything on this dataset -- it did fire on other over-subtracted Mad1 measurements (see
    disk_local_bg's docstring) and costs nothing when it's a no-op."""
    h, w = mad.shape
    y0, y1 = max(0, y-rsearch), min(h, y+rsearch+1); x0, x1 = max(0, x-rsearch), min(w, x+rsearch+1)
    sub = mad[y0:y1, x0:x1]; iy, ix = np.unravel_index(int(np.argmax(sub)), sub.shape)
    try: MAD_PEAK_XY.append((x0+ix, y0+iy))     # so the fold is taken at the SAME refined peak
    except Exception: pass
    _raw = lib.disk_local_bg(mad, x0+ix, y0+iy)
    # 2026-08-05: record the TRUE value before any floor. She asked for ABSOLUTE VALUES; a
    # max(0,...) floor is NOT the same operation - it throws the magnitude of a negative away,
    # while abs() keeps it. Whether that matters is an empirical question, so measure it.
    try: MAD_RAW_VALUES.append(float(_raw))
    except Exception: pass
    return max(0.0, _raw)


# ---------------- uniform Hec1-derived crop (from the FIRST timestrip frame) ----------------
def hec1_crop(bat, f0):
    """Cell bbox from where the Hec1 dots CLUSTER on the first frame -> a UNIFORM-scale-before-crop SQUARE window
    (ts_render.tight_square, margin -> clean breathing room so no KTs are clipped; a per-batch CROP_OFFSETS nudge
    repositions where it sits). One box reused for all frames/channels; applied with ts_render.crop_pad (edge-
    padded, undistorted). Replaces the old tight m=34px / p80 box that clipped the outer kinetochores."""
    hec0 = raw_plane(bat, "hec1", f0); H, W = hec0.shape
    sm0 = gaussian_filter(hec0.astype(np.float32), 1.5)
    cy0, cx0 = H // 2, W // 2; ry, rx = int(H * 0.24), int(W * 0.24)
    mask = np.zeros_like(sm0, bool); mask[cy0-ry:cy0+ry, cx0-rx:cx0+rx] = True
    thr_v = max(np.percentile(sm0[mask], 99.3), sm0[mask].mean() + 3*sm0[mask].std())
    ys, xs = np.where((sm0 > thr_v) & mask)
    if xs.size >= 6:
        # ROBUST cluster: median centre + a capped p75 radius, so a few far stragglers (noise / a neighbour
        # cell's KTs) can't blow the bbox up (xy4 was exploding to a 780px box), yet the real KT ring is kept.
        mcx, mcy = float(np.median(xs)), float(np.median(ys))
        rr = np.hypot(xs - mcx, ys - mcy)
        rad = float(np.percentile(rr, 75))
        # 2026-07-10 (user): the frame-relative ceil (0.13*min(H,W)) was too loose on the larger xy4/xy6 frames,
        # so noise/neighbour KTs inflated rad to ~180-220px (box 600-720) while xy2/xy5 sat at ~52px (box 174) —
        # wildly inconsistent crops. All 4 hec1 batches are PX=0.062, so a FIXED-pixel cap = fixed-µm window and
        # makes every timestrip the SAME physical scale (~11-12µm) with even breathing room. Center still adapts.
        rad = min(max(rad, 58.0), 66.0)     # fixed px [58,66] -> box ~192-218px (~11.9-13.5µm) at margin 1.65
        pts = np.array([[mcx-rad, mcy-rad], [mcx+rad, mcy-rad],
                        [mcx+rad, mcy+rad], [mcx-rad, mcy+rad]], float)
    else:
        hw = min(H, W)//5
        pts = np.array([[cx0-hw, cy0-hw], [cx0+hw, cy0-hw], [cx0+hw, cy0+hw], [cx0-hw, cy0+hw]], float)
    # 2026-07-10 (user): hec1 timestrips cropped too close -> widen the square window. 2026-07-20 (user): STILL
    # too tight -> widen further, margin 1.65 -> 2.2 (KT cluster fills ~45% of frame, generous breathing room; the
    # high cluster no longer sits near the panel edge). Uniform scale-before-crop preserved (no distortion);
    # per-batch CROP_OFFSETS nudges still apply on top.
    return ts_render.tight_square(pts, W, H, margin=2.2, batch=bat["B"])


def _cluster_centre(bat, frame):
    """(x, y) of the kinetochore cluster in ONE frame, by the same rule `hec1_crop` uses to place the box:
    the median of the bright 640 pixels inside the central window. Returns None if too few pixels pass, so
    a caller can decline to move rather than move onto noise."""
    try:
        hec = raw_plane(bat, "hec1", frame)
    except Exception:
        return None
    H, W = hec.shape
    sm = gaussian_filter(hec.astype(np.float32), 1.5)
    cy0, cx0 = H // 2, W // 2
    ry, rx = int(H * 0.24), int(W * 0.24)
    mask = np.zeros_like(sm, bool); mask[cy0-ry:cy0+ry, cx0-rx:cx0+rx] = True
    thr = max(np.percentile(sm[mask], 99.3), sm[mask].mean() + 3*sm[mask].std())
    ys, xs = np.where((sm > thr) & mask)
    if xs.size < 6:
        return None
    return float(np.median(xs)), float(np.median(ys))


# ---------------- build a 3xN timestrip mosaic ----------------
def _mirror_raster_to_pdf(out_png, img):
    """Re-emit a cv2-written strip through savefig so the _ai_relink PDF mirrors refresh.

    🔴 2026-08-25. This builder writes its strip with `cv2.imwrite`, which does not go through
    `lib.apply_style()`'s savefig wrapper -- the wrapper is the thing that mirrors every PNG into
    `_ai_relink/pdf/` AND the publication twin `pdf_pub/`. So re-rendering a Hec1 timestrip updated the PNG
    and left the DECKS linking a PDF from a previous run: `G5_item4_hec1_timestrip_xy5` was re-rendered
    today at 14:37 while the board went on showing the 08-17 PDF. It was the only stale link on any of the
    eight decks, and it was stale for this reason.

    Wrapping the raster in a figure sized to its exact pixel dimensions (the same thing
    `custom_split_all_strips_20260819.py` does for every placed strip piece) keeps the aspect exact -- which
    matters, because a placed figure whose aspect changes has to be RE-PLACED, not resized.
    """
    import matplotlib.pyplot as _plt
    # 🔴 AND apply_style() MUST BE IN EFFECT BEFORE THIS savefig. In this module it is called inside
    # `build_dot_quant`, which runs AFTER the timestrip in the JOBS loop -- so at strip time the savefig
    # wrapper is not installed yet and the mirror silently does nothing. That is why the first attempt at
    # this fix rewrote the PNG and left both PDFs at their 08-17 timestamps. apply_style() is idempotent.
    lib.apply_style()
    h, w = img.shape[:2]
    dpi = 200.0
    f = _plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
    a = f.add_axes([0, 0, 1, 1]); a.axis("off")
    a.imshow(img[..., ::-1], interpolation="none")
    f.savefig(out_png, dpi=dpi, pad_inches=0)      # lib's wrapper mirrors this to pdf/ and pdf_pub/
    _plt.close(f)

def build_timestrip(bat, TARGETS, out_png):
    """TARGETS = [(t_sec, caption), ...]; rows=channels, cols=timepoints; labels in gutters, NO overlap."""
    B = bat["B"]; PX = bat["PX"]
    f0 = frame_for_t(bat, TARGETS[0][0]); CROP = hec1_crop(bat, f0)
    import re as _re
    _m = _re.search(r"(xy\d+)$", B)          # PANEL_SHIFT_UM is keyed by the xyN suffix, as AOI_OFFSET is
    _shift = PANEL_SHIFT_UM.get(_m.group(1) if _m else "", {})
    # ── PER-COLUMN TRACKING ──────────────────────────────────────────────────────────────────────────
    # The crop is derived once, from the FIRST column's frame, and reused for every column -- which is
    # right for magnification (one scale across the strip) but not for position: over 12 minutes the cell
    # moves, and by the last column it can leave the box. That is what her two hand nudges on this strip
    # were compensating for, and it is why they went stale the moment the third column's frame changed.
    # Each column's box is therefore the SAME SIZE, translated by how far the kinetochore cluster itself
    # moved between that frame and the first -- measured with the same rule `hec1_crop` uses to find the
    # cluster in the first place. Magnification is untouched, so the panels stay comparable.
    frames_track = [frame_for_t(bat, t) for t, _ in TARGETS]
    _c0 = _cluster_centre(bat, frames_track[0])
    def _track(ci):
        if _c0 is None: return (0.0, 0.0)
        c = _cluster_centre(bat, frames_track[ci])
        if c is None:
            print(f"   panel {ci}: no kinetochore cluster found, ROI left where the first frame put it")
            return (0.0, 0.0)
        dx, dy = c[0] - _c0[0], c[1] - _c0[1]
        lim = (CROP[2] - CROP[0]) * 0.5      # never move the window by more than half its own width
        if abs(dx) > lim or abs(dy) > lim:
            print(f"   panel {ci}: tracked shift ({dx*PX:+.1f}, {dy*PX:+.1f}) um exceeds half the box "
                  f"-- refusing it, ROI left where the first frame put it")
            return (0.0, 0.0)
        return (dx, dy)

    def _box_for(ci):
        tx, ty = _track(ci)
        d = _shift.get(ci, (0.0, 0.0))
        dx = int(round(tx + d[0] / PX)); dy = int(round(ty + d[1] / PX))
        if dx == 0 and dy == 0: return CROP
        x0, y0, x1, y1 = CROP
        return (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    def crop(a, ci=None): return ts_render.crop_pad(a, CROP if ci is None else _box_for(ci))
    if _shift:
        for _ci, _d in sorted(_shift.items()):
            print(f"   panel {_ci}: ROI shifted {_d[0]:+.1f} um x, {_d[1]:+.1f} um y "
                  f"({int(round(_d[0]/PX)):+d}, {int(round(_d[1]/PX)):+d} px)")
    def fit(img):
        s = PANEL_H / img.shape[0]; return cv2.resize(img, (int(img.shape[1]*s), PANEL_H))
    frames_sel = [frame_for_t(bat, t) for t, _ in TARGETS]

    # ── USER 2026-08-19, all-figures item 5 ────────────────────────────────────────────────────────
    # "this timestrip set: it includes a weird grey border in left and top, and overall is not in the same
    #  visual style as the other timestrips such as the ablation or monitoring timestrips. Resolve this.
    #  Also, for the phase frames: increase the ROI just slightly (dont increase ROI for the other two
    #  channels shown), and then place on those phase frames a square showing the roi of the fluorescent
    #  frames. Place the 5um scalebar on the third frame of each channel here."
    #
    # THE GREY BORDER was a 150 px left GUTTER and a 54 px top caption bar, both filled with value 30. No
    # other strip on the decks has either: `ts_render` burns the timestamp onto the frame itself in white
    # with a black outline and separates tiles with a thin rule. Both are gone; this builder now uses
    # ts_render's own separator value and its timestamp treatment, so the strip sits in the same visual
    # family as the ablation and monitoring strips.
    PHASE_ROI_GROW = 1.18          # "increase the ROI just slightly", phase row ONLY
    # USER 2026-08-20 (board 1, item 2): "you only zoomed out the roi by like 2um on each side. Zoom out by
    # an additional 4um on each side. Keep roi for fluorescent frames the same, and adjust white box overlay
    # on phase frames accordingly."
    # An ADDITIVE margin, because that is the form her instruction takes -- the 1.18 factor above is what
    # delivered "like 2um" and scaling it again would not land on a stated number of microns. The fluorescence
    # box (`_box_for`) is untouched, and the white square is drawn FROM that box, so it keeps marking exactly
    # where the fluorescence frames look and shrinks within the wider phase tile automatically.
    PHASE_EXTRA_UM = 4.0           # per side
    # ...and: "the third timepoint frame ... needed to have the roi of the PHASE CONTRAST adjusted by shifting
    # the roi to the up and left, and you made it worse by doing the opposite". It did: the third panel
    # carried (+10 um right, +5 um down) from her 08-10/08-11 notes. That shift stays on the FLUORESCENCE
    # frames (she asked for those to be left alone) and is REVERSED for the phase frames only.
    # Her 08-20 "the third timepoint frame needed the PHASE CONTRAST roi shifted up and left, and you made
    # it worse by doing the opposite" was a correction to the +10/+5 fluorescence nudge leaking into the
    # phase window. That nudge is gone (PANEL_SHIFT_UM above) and the panel now tracks the cell, so the
    # phase window is centred on the cell again and needs no counter-shift. Keeping the -10/-5 as well
    # would re-introduce exactly the displacement she asked to remove.
    PHASE_PANEL_SHIFT_UM = {}                     # -x = left, -y = up
    SEP_W = ts_render.SEP; SEP_V = ts_render.SEP_VAL

    def _grow(box, k, extra_um=0.0, shift_um=(0.0, 0.0)):
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        e = float(extra_um) / PX
        hw, hh = (x1 - x0) * k / 2.0 + e, (y1 - y0) * k / 2.0 + e
        dx, dy = shift_um[0] / PX, shift_um[1] / PX
        return (int(round(cx + dx - hw)), int(round(cy + dy - hh)),
                int(round(cx + dx + hw)), int(round(cy + dy + hh)))

    def _stamp(img, text):
        """ts_render's timestamp treatment: white text, black outline, top-left, inside the frame."""
        if not text: return
        cv2.putText(img, text, (10, int(FS * 34)), FONT, FS, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(img, text, (10, int(FS * 34)), FONT, FS, (255, 255, 255), 2, cv2.LINE_AA)

    def _scalebar(img, box, um=5.0):
        """5 um bar bottom-right of THIS tile, sized from the tile's own crop box so a grown phase ROI
        still gets a correct bar."""
        px_per_out = (box[3] - box[1]) / float(img.shape[0])       # source px per output px
        barlen = max(3, int(round(um / (PX * px_per_out))))
        bx1 = img.shape[1] - 14; bx0 = max(2, bx1 - barlen); by = img.shape[0] - 14
        cv2.rectangle(img, (bx0, by - 9), (bx1, by), (255, 255, 255), -1)
        # Keep the label INSIDE the tile. On the widened phase ROI the 5 um bar is short and sits hard
        # right, so a label drawn from the bar's left edge ran off the frame and printed as "5 un".
        _txt = f"{um:g} um"
        (_tw, _), _ = cv2.getTextSize(_txt, FONT, FS * 0.8, 2), None
        _tx = min(bx0, img.shape[1] - _tw[0] - 6)
        cv2.putText(img, _txt, (_tx, by - 13), FONT, FS * 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(img, _txt, (_tx, by - 13), FONT, FS * 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    # the timestamp strings, taken from the frames ACTUALLY selected (not the requested times) so a column
    # that moved to the nearest all-channel frame is labelled with the time it really shows
    _tmax = max(abs(float(f["t_sec"])) for f in frames_sel)
    def _lab(f):
        t = float(f["t_sec"]); sgn = "-" if t < 0 else ""; t = abs(t)
        h, m, sec = int(t // 3600), int(t % 3600 // 60), int(t % 60)
        return f"{sgn}{h}:{m:02d}:{sec:02d}" if _tmax >= 3600 else f"{sgn}{m}:{sec:02d}"
    _fmt = "HH:MM:SS" if _tmax >= 3600 else "MM:SS"

    row_imgs = []
    for ri, (rname, chan, color, pcts, gam) in enumerate(ROWS):
        is_phase = (chan == "phase")
        def _phase_box(ci):
            """Phase window: the fluorescence box, grown, plus her per-panel pan -- and ALWAYS containing
            the fluorescence box.

            Panning the phase window up-left by 10 um while the fluorescence box stays put pushed that box
            out of the phase tile, so the white square marking "where the fluorescence frames look" was
            clipped at the tile edge -- worse than the problem it was fixing. Taking the UNION of the
            panned window with the fluorescence box keeps every pixel her pan was meant to reveal on the
            up-left side AND guarantees the white square is drawn whole. Nothing is fabricated: the union is
            still a real region of the same frame, and the fluorescence crop itself is untouched."""
            fb = _box_for(ci)
            pb = _grow(fb, PHASE_ROI_GROW, PHASE_EXTRA_UM, PHASE_PANEL_SHIFT_UM.get(ci, (0.0, 0.0)))
            pad = int(round(1.0 / PX))                      # 1 um of air so the square is not on the edge
            return (min(pb[0], fb[0] - pad), min(pb[1], fb[1] - pad),
                    max(pb[2], fb[2] + pad), max(pb[3], fb[3] + pad))

        if is_phase:
            # UNIFORM TILE SIZE. The union above can make one panel's window bigger than the others, and
            # ts_render pads short rows to the widest one -- which printed a white band down the right of
            # the fluorescence rows (the same class of defect as NOTES rule 29's black bars). Every phase
            # window therefore gets the SAME width and height -- the largest any panel needs -- centred on
            # its own centre, so the pan is preserved, the magnification is identical across panels, and
            # no row has to be padded.
            _raw = [_phase_box(ci) for ci in range(len(frames_sel))]
            # SQUARE, like the fluorescence box: `fit()` scales a tile to a fixed HEIGHT and keeps aspect,
            # so a non-square phase window makes the phase row wider than the fluorescence rows and
            # ts_render pads the short rows -- printing a white band down the right of the strip.
            _side = max(max(b[2] - b[0] for b in _raw), max(b[3] - b[1] for b in _raw))
            _w = _h = _side
            boxes = []
            for b in _raw:
                cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
                boxes.append((int(round(cx - _w / 2.0)), int(round(cy - _h / 2.0)),
                              int(round(cx + _w / 2.0)), int(round(cy + _h / 2.0))))
        else:
            boxes = [_box_for(ci) for ci in range(len(frames_sel))]
        planes = [ts_render.crop_pad(raw_plane(bat, chan, fr), boxes[ci])
                  for ci, fr in enumerate(frames_sel)]
        allpx = np.concatenate([p.ravel() for p in planes])         # ONE exposure per row (pooled over all frames)
        lo = np.percentile(allpx, pcts[0]); hi = np.percentile(allpx, pcts[-1])
        cells = []
        for ci, p in enumerate(planes):
            g8 = stretch(p, pcts[0], pcts[-1], gam, lo=lo, hi=hi)   # identical mapping for every frame of this row
            cell = fit(colorize(g8, color))
            if is_phase:
                # the square showing WHERE THE FLUORESCENCE FRAMES LOOK, drawn on the (larger) phase tile
                fb = _box_for(ci); pb = boxes[ci]
                sx = cell.shape[1] / float(pb[2] - pb[0]); sy = cell.shape[0] / float(pb[3] - pb[1])
                rx0 = int(round((fb[0] - pb[0]) * sx)); ry0 = int(round((fb[1] - pb[1]) * sy))
                rx1 = int(round((fb[2] - pb[0]) * sx)); ry1 = int(round((fb[3] - pb[1]) * sy))
                cv2.rectangle(cell, (rx0, ry0), (rx1, ry1), (255, 255, 255), ts_render.stroke_px(cell), cv2.LINE_AA)
            if ri == 0: _stamp(cell, _lab(frames_sel[ci]))
            if ri == 0 and ci == 0:
                cv2.putText(cell, _fmt, (10, int(FS * 34) + int(FS * 40)), FONT, FS, (0, 0, 0), 5, cv2.LINE_AA)
                cv2.putText(cell, _fmt, (10, int(FS * 34) + int(FS * 40)), FONT, FS, (255, 255, 255), 2, cv2.LINE_AA)
            if ci == 2:                                     # "the 5um scalebar on the third frame of each channel"
                _scalebar(cell, boxes[ci])
            cells.append(cell)
        ims = []
        for c in cells: ims += [c, np.full((PANEL_H, SEP_W, 3), SEP_V, np.uint8)]
        row_imgs.append(np.hstack(ims[:-1]))

    Wt = max(r.shape[1] for r in row_imgs)
    row_imgs = [np.pad(r, ((0, 0), (0, Wt - r.shape[1]), (0, 0)), constant_values=SEP_V)
                if r.shape[1] < Wt else r for r in row_imgs]

    blocks = []
    for r in row_imgs:
        blocks.append(r)
        blocks.append(np.full((SEP_W, Wt, 3), SEP_V, np.uint8))
    fig = np.vstack(blocks[:-1])

    s = min(4500/fig.shape[1], 2600/fig.shape[0], 1.0)
    if s < 1.0: fig = cv2.resize(fig, (int(fig.shape[1]*s), int(fig.shape[0]*s)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(out_png, fig)
    _mirror_raster_to_pdf(out_png, fig)
    # FRAME MANIFEST. This builder writes its strip with cv2.imwrite and never touches ts_render.emit, so
    # the registry there never sees it and the timestrip-setup slide had no frames to list for this cell.
    # `frames_sel` IS the set of frames drawn, so record it beside the figure in the same shape emit() uses.
    try:
        import json as _j
        _t = []
        for _f in frames_sel:
            if isinstance(_f, dict) and _f.get("t_sec") is not None: _t.append(round(float(_f["t_sec"]), 2))
            elif isinstance(_f, (int, float)): _t.append(round(float(_f), 2))
        if _t:
            _j.dump({"batch": B, "title": None, "ablation": [], "monitoring": [], "times": sorted(set(_t))},
                    open(out_png[:-4] + "_frames.json", "w"), indent=1)
    except Exception as _e:
        print(f"  (hec1 frame manifest not written: {_e})")
    print(f"wrote {out_png}  {fig.shape[1]}x{fig.shape[0]}  crop={CROP}")
    return CROP, frames_sel


# ---------------- Hec1 dot detection + Hec1/Mad1 intensity violins (xy5) ----------------
def build_dot_quant(bat, TARGETS, CROP, out_png):
    def crop(a): return ts_render.crop_pad(a, CROP)
    frames_sel = [frame_for_t(bat, t) for t, _ in TARGETS]
    # Detect the Hec1 kinetochore dots IN EACH frame (07-07 feedback: "identify the dots in the hec1 channel in
    # THOSE frames"). The KTs physically MOVE between unaligned -> biorientation -> anaphase, so a single frame-1
    # detection sampled cytoplasm on later frames and made Hec1 spuriously DROP. Per-frame detection measures the
    # actual Hec1 puncta each frame -> Hec1 ~constant (constitutive KT marker); Mad1 at those SAME per-frame Hec1
    # locations drops F1->F2 as the SAC is satisfied, then stays ~flat.
    # 🔴 HER 2026-08-25 item 18: *"G5_hec1_mad1_dot_quant_linear still not correct. The mad1 data youre
    # plotting is not the correct measurement or is not scaled correctly."*
    #
    # It was not the right measurement. Her standing rule (MEMORY feedback_measure_at_her_marks_not_autodetect)
    # is: **her KT marks, made on the 640 frames, used VERBATIM for 488, NO peak refine, background from HER
    # `cytosol_bg`, expressed as fold-over-background, no outlier removal, no auto-detect fallback.**
    # This function broke three parts of that at once -- `find_dots()` AUTO-DETECTED its own Hec1 puncta,
    # `mad_at_dot()` then PEAK-REFINED onto the nearest Mad1 maximum (so Mad1 was measured somewhere the KT
    # is not), and the background was a LOCAL ANNULUS rather than her cytosol marks.
    #
    # She has marked this cell properly: 27 `paired_kt` points in EACH of 3 frames (81 in total) plus one
    # `cytosol_bg` per frame. Those are used exactly as drawn, on the UNCROPPED plane so no crop offset can
    # shift them, and both channels are read at the SAME coordinates.
    import csv as _csv18, collections as _coll18
    _KT18 = _coll18.defaultdict(list); _BG18 = _coll18.defaultdict(list)
    for _r in _csv18.DictReader(open("/Volumes/4 MB/annotations/kt_points.csv", newline="",
                                     encoding="utf-8", errors="replace")):
        if (_r.get("batch") or "").strip() != bat["B"]: continue
        try: _xy = (float(_r["x"]), float(_r["y"])); _ts = float(_r["t_sec"])
        except Exception: continue
        _lab18 = (_r.get("label") or "").strip()
        if _lab18 == "paired_kt": _KT18[round(_ts)].append(_xy)
        elif _lab18 == "cytosol_bg": _BG18[round(_ts)].append(_xy)

    def _disk_sum(img, x, y, r=9):
        import numpy as _np
        h, w = img.shape[:2]
        y0, y1 = max(0, int(y - r)), min(h, int(y + r) + 1)
        x0, x1 = max(0, int(x - r)), min(w, int(x + r) + 1)
        if y1 <= y0 or x1 <= x0: return None
        sub = img[y0:y1, x0:x1].astype(float)
        yy, xx = _np.ogrid[y0:y1, x0:x1]
        m = (yy - y) ** 2 + (xx - x) ** 2 <= r * r
        return float(sub[m].sum()) if m.any() else None

    def _nearest_marks(store, t):
        if not store: return []
        k = min(store, key=lambda q: abs(q - t))
        return store[k] if abs(k - t) <= 30 else []

    hec_vals = []; mad_vals = []
    hec_fold = []; mad_fold = []
    data_rows = []
    for fr, (t, lab) in zip(frames_sel, TARGETS):
        hec_full = raw_plane(bat, "hec1", fr); mad_full = raw_plane(bat, "mad1", fr)
        _t = float(fr.get("t_sec", t))
        marks = _nearest_marks(_KT18, _t)
        bgm = _nearest_marks(_BG18, _t)
        if not marks:
            print(f"    frame t={_t:.0f}s: NO KT marks of hers within 30 s -- frame skipped, not auto-detected")
            hec_vals.append([]); mad_vals.append([]); hec_fold.append([]); mad_fold.append([]); continue
        _hbg = [v for v in (_disk_sum(hec_full, x, y) for x, y in bgm) if v]
        _mbg = [v for v in (_disk_sum(mad_full, x, y) for x, y in bgm) if v]
        _hb = float(np.median(_hbg)) if _hbg else None
        _mb = float(np.median(_mbg)) if _mbg else None
        hv, mv, hf, mf = [], [], [], []
        for (x, y) in marks:                       # HER coordinates, verbatim, both channels
            _h = _disk_sum(hec_full, x, y); _m = _disk_sum(mad_full, x, y)
            if _h is None or _m is None: continue
            hv.append(_h); mv.append(_m)
            if _hb: hf.append(_h / _hb)
            if _mb: mf.append(_m / _mb)
        hec_vals.append(hv); mad_vals.append(mv)
        hec_fold.append(hf); mad_fold.append(mf)
        flab = str(lab).split("  ")[0].strip()
        for di, (h, m) in enumerate(zip(hv, mv)):
            data_rows.append((flab, di, "hec1_640", round(float(h), 1)))
            data_rows.append((flab, di, "mad1_488", round(float(m), 1)))
        print(f"    frame t={_t:.0f}s: {len(hv)} of HER marks measured, "
              f"bg hec1={_hb:.0f} mad1={_mb:.0f}" if (_hb and _mb) else
              f"    frame t={_t:.0f}s: {len(hv)} of HER marks measured, background missing")

    # ---- USER 2026-08-04: |Mad1|, then calibrate EACH fluorophore independently to 0-1 ----------------
    # "Take absolute values of Mad1 fluorescences so they stop being negative. Then, for each hec1 and mad1,
    #  instead of having raw intensity on each y-axis, calibrate it to a scale from 0-1, where 1 is the
    #  highest fluorescence measured (for that fluorophore) and 0 is the lowest."
    # The two calibrations are computed separately, so both axes span 0-1 but mean different a.u. ranges.
    # Mad1's calibration is taken from the ABSOLUTE values, per her instruction.
    n_neg_before_abs = sum(1 for s in mad_vals for v in s if v < 0)   # count BEFORE abs, else it is always 0
    mad_vals = [[abs(v) for v in s] for s in mad_vals]

    # ---- USER 2026-08-05: drop the F1 Mad1 outliers, THEN rescale the 0-1 calibration ------------------
    # "for the F1 timepoint for mad1 measurements there are 4 outliers. remove these outliers ... then
    #  rescale the mad1 0-1 calibration and replot"
    #
    # They matter out of proportion to their number: the calibration is a min-max scale, so the single
    # largest value DEFINES 1.0. With them in, F1's 9100 a.u. set the top of the axis and squashed all 77
    # other dots into the bottom ~12% of the range, which is why the F2/F3 difference was unreadable.
    #
    # Selected by robust z (median/MAD) WITHIN the F1 Mad1 series rather than by hard-coded dot indices, so
    # the rule survives a re-measure. |z|>2.5 isolates exactly the four she saw; every other timepoint's
    # maximum is 1705 a.u., so all four also sit outside the entire range of the rest of the experiment.
    MAD1_F1_Z = 2.5
    MAD1_F1_DROPPED = []
    _mad_keep = [list(range(len(s))) for s in mad_vals]
    if mad_vals and len(mad_vals[0]) >= 5:
        _v = np.asarray(mad_vals[0], float)
        _med = float(np.median(_v)); _mad = float(np.median(np.abs(_v - _med))) or 1e-9
        _z = 0.6745 * (_v - _med) / _mad
        _keep = [i for i in range(len(_v)) if abs(_z[i]) <= MAD1_F1_Z]
        MAD1_F1_DROPPED = [(i, float(_v[i]), round(float(_z[i]), 2))
                           for i in range(len(_v)) if abs(_z[i]) > MAD1_F1_Z]
        for _i, _val, _zz in MAD1_F1_DROPPED:
            lib.log_review("hec1_mad1_F1_outlier", "20260303 Mad1 Hec1 IF", f"dot{_i}",
                           f"Mad1 F1 outlier {_val:.0f} a.u. (robust z={_zz:+.1f}) removed before the 0-1 "
                           f"rescale; median={_med:.0f}, MAD={_mad:.0f}")
        mad_vals[0] = [float(_v[i]) for i in _keep]
        _mad_keep[0] = _keep
        print(f"  MAD1 F1 outliers removed: {len(MAD1_F1_DROPPED)} of {len(_v)} "
              f"(dots {[d[0] for d in MAD1_F1_DROPPED]}, values {[round(d[1]) for d in MAD1_F1_DROPPED]}) "
              f"— calibration rescaled on the remainder")

    raw_hec_vals = [list(s) for s in hec_vals]      # keep the a.u. values for the data CSV and the axis note
    raw_mad_vals = [list(s) for s in mad_vals]

    def calib01(series):
        """Min-max scale a list-of-lists to 0-1 using that fluorophore's own extremes. Returns (scaled, lo, hi)."""
        allv = [v for s in series for v in s]
        if not allv:
            return series, 0.0, 1.0
        lo, hi = min(allv), max(allv)
        rng = (hi - lo) or 1.0
        return [[(v - lo) / rng for v in s] for s in series], lo, hi

    hec_vals, HEC_LO, HEC_HI = calib01(hec_vals)
    mad_vals, MAD_LO, MAD_HI = calib01(mad_vals)

    # rebuild the recorded rows so the CSV carries BOTH the a.u. measurement and its 0-1 calibration
    # Channels are written INDEPENDENTLY now. They used to share one `di` loop bounded by the Hec1 count,
    # which was safe only while both channels had the same dots; after the F1 Mad1 removal above they do
    # not, and a shared index would have silently mislabelled every Mad1 dot past the first drop.
    # `_mad_keep` carries each surviving value's ORIGINAL dot index, so the CSV still ties back to the image.
    data_rows = []
    for fi, (t_, lab_) in enumerate(TARGETS):
        flab = str(lab_).split("  ")[0].strip()
        for di in range(len(raw_hec_vals[fi])):
            data_rows.append((flab, di, "hec1_640",
                              round(float(raw_hec_vals[fi][di]), 1), round(float(hec_vals[fi][di]), 4)))
        for j, orig_di in enumerate(_mad_keep[fi]):
            data_rows.append((flab, orig_di, "mad1_488_abs",
                              round(float(raw_mad_vals[fi][j]), 1), round(float(mad_vals[fi][j]), 4)))

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    lib.apply_style()
    # DUAL Y-AXIS: even with the Mad1 location fixed, 488 (a dim, non-constitutive SAC marker) has far lower raw
    # counts than the bright constitutive 640/Hec1 (Mad1 ~840-960 vs Hec1 ~1600-2300). On a shared axis Mad1
    # stays squashed on the floor, so Hec1 is drawn on the LEFT axis (pink) and Mad1 on its own RIGHT axis
    # (green) -> both channels readable, each framed to its own dynamic range.
    HEC_C = (0.95, 0.30, 0.65); MAD_C = (0.20, 0.70, 0.25)
    labels = [t[1].split("  ")[-1] for t in TARGETS]
    n = len(TARGETS)
    hpos = [i*3 + 1 for i in range(n)]; mpos = [i*3 + 2 for i in range(n)]
    xt = [i*3 + 1.5 for i in range(n)]; xtl = [f"F{i+1}\n{labels[i]}" for i in range(n)]

    fig2, axH = plt.subplots(figsize=(8.2, 5.0))
    axM = axH.twinx()

    def draw(ax, series, positions, col):
        d = [s if len(s) else [0.0] for s in series]
        vp = ax.violinplot(d, positions=positions, widths=0.8, showmeans=True, showextrema=False)
        for b in vp["bodies"]: b.set_facecolor(col); b.set_edgecolor("k"); b.set_alpha(0.7)
        if "cmeans" in vp: vp["cmeans"].set_color("k"); vp["cmeans"].set_linewidth(1.4)
        for s, x in zip(series, positions):
            if len(s): ax.scatter(np.random.normal(x, 0.05, len(s)), s, s=lib.VIOLIN_DOT_S, color="k", alpha=lib.VIOLIN_DOT_ALPHA_DENSE, zorder=3)

    draw(axH, hec_vals, hpos, HEC_C)
    draw(axM, mad_vals, mpos, MAD_C)

    # both axes now span the SAME 0-1 range (each fluorophore calibrated to its own min/max)
    axH.set_ylim(-0.05, 1.05); axM.set_ylim(-0.05, 1.05)
    axH.set_xlim(0.2, n*3 - 0.2)
    axH.set_xticks(xt); axH.set_xticklabels(xtl, fontsize=9)

    axH.set_ylabel(f"Hec1 (640) dot intensity — calibrated 0-1\n(0 = {HEC_LO:.0f} a.u., 1 = {HEC_HI:.0f} a.u.)",
                   color=HEC_C)
    axM.set_ylabel(f"|Mad1 (488)| dot intensity — calibrated 0-1\n(0 = {MAD_LO:.0f} a.u., 1 = {MAD_HI:.0f} a.u.)",
                   color=MAD_C)
    axH.tick_params(axis="y", colors=HEC_C); axM.tick_params(axis="y", colors=MAD_C)
    axH.spines["left"].set_color(HEC_C); axM.spines["right"].set_color(MAD_C)
    axM.spines["left"].set_visible(False)

    _ymin = axH.get_ylim()[0]
    # n per CHANNEL: after the F1 Mad1 outlier removal the two channels no longer have the same dot count,
    # and a single "n=" under the pair would have quietly reported the Hec1 number for both.
    for _s, x in zip(hec_vals, hpos):
        axH.text(x, _ymin, f"n={len(_s)}", ha="center", va="bottom", fontsize=7, color=HEC_C)
    for _s, x in zip(mad_vals, mpos):
        axH.text(x, _ymin, f"n={len(_s)}", ha="center", va="bottom", fontsize=7, color=MAD_C)
    # Describe the trend FROM the data rather than asserting it: the previous subtitle hard-coded
    # "Mad1 high at F1, drops F1->F2, ~flat F2->F3", which was written when the four F1 outliers were
    # still setting the top of the scale.
    _mm = [float(np.mean(m)) if len(m) else float("nan") for m in mad_vals]
    _hm = [float(np.mean(h)) if len(h) else float("nan") for h in hec_vals]
    def _arrow(a, b, tol=0.03):
        return "flat" if abs(b - a) < tol else ("drops" if b < a else "rises")
    _trend = (f"Mad1 means {_mm[0]:.2f} -> {_mm[1]:.2f} -> {_mm[2]:.2f} "
              f"({_arrow(_mm[0], _mm[1])} F1->F2, {_arrow(_mm[1], _mm[2])} F2->F3)   |   "
              f"Hec1 {_hm[0]:.2f} -> {_hm[1]:.2f} -> {_hm[2]:.2f}") if len(_mm) == 3 else ""
    _drop_note = (f"\n{len(MAD1_F1_DROPPED)} F1 Mad1 outliers removed before calibrating "
                  f"(|robust z|>{MAD1_F1_Z}: {[round(d[1]) for d in MAD1_F1_DROPPED]} a.u.; "
                  f"every other timepoint tops out at 1705)") if MAD1_F1_DROPPED else ""
    axH.set_title("Hec1 (640, left) vs Mad1 (488, right) at per-frame Hec1-dot KTs\n"
                  "each fluorophore calibrated separately to 0-1 (1 = its own brightest measurement); "
                  "Mad1 as absolute value\n"
                  + _trend + _drop_note, fontsize=9)
    from matplotlib.patches import Patch
    axH.legend(handles=[Patch(facecolor=HEC_C, label="Hec1 (640) — left axis"),
                        Patch(facecolor=MAD_C, label="Mad1 (488) — right axis")],
               loc="upper center", fontsize=8, ncol=2)
    fig2.tight_layout()
    fig2.savefig(out_png, dpi=200); plt.close(fig2)

    # ── LINEAR-AXIS SIBLING (user 2026-08-20, board 1 item 3) ──────────────────────────────────────────
    # "Make a version of this plot without the weird y-axis scale. Just use a linear scale for the y-axis."
    #
    # The "weird scale" is the pair of independently min-max-calibrated 0-1 axes above. They exist only
    # because Hec1 and Mad1 differ ~27x in background-subtracted a.u., so one linear axis of those counts
    # would flatten Mad1. Measuring each dot as a FOLD OVER ITS OWN LOCAL BACKGROUND removes the problem at
    # source: the quantity is dimensionless, 1.0 means "no brighter than local background", and both
    # fluorophores sit on ONE linear axis that needs no per-channel rescaling.
    #
    # This version also drops the two operations layered onto the original that her standing rules exclude:
    #   * NO outlier removal -- every measured dot is plotted.
    #   * NO min-max calibration -- nothing is rescaled per fluorophore.
    # Colours are magenta/cyan, not the pink/green of the original: pink-vs-green is exactly the pairing
    # NOTES rule 30 forbids. This is a SIBLING; the original figure is left untouched.
    if any(hec_fold) or any(mad_fold):
        _HF, _MF = "#d81b8c", "#00a5b5"                      # magenta / cyan (rule 30)
        figL, axL = plt.subplots(figsize=(9.2, 5.4))
        _labs = [str(l).split("  ")[0].strip() for _, l in TARGETS]
        _sub = [str(l).split("  ")[-1].strip() if "  " in str(l) else "" for _, l in TARGETS]
        _n = len(_labs); _hx = np.arange(_n) - 0.17; _mx = np.arange(_n) + 0.17
        for _series, _xs, _c in ((hec_fold, _hx, _HF), (mad_fold, _mx, _MF)):
            for _s, _x in zip(_series, _xs):
                if not len(_s): continue
                _v = np.asarray(_s, float)
                _vp = axL.violinplot([_v], positions=[_x], widths=0.30, showextrema=False)
                for _b in _vp["bodies"]:                      # matplotlib's default cycle put a GREEN body
                    _b.set_facecolor(_c); _b.set_edgecolor("none"); _b.set_alpha(0.28)
                axL.scatter(np.random.default_rng(0).normal(_x, 0.035, len(_v)), _v,
                            s=lib.VIOLIN_DOT_S, color=_c, alpha=0.75, zorder=3, edgecolor="none")
                axL.hlines(float(np.median(_v)), _x-0.13, _x+0.13, color="k", lw=2.2, zorder=4)
                axL.text(_x, axL.get_ylim()[0], f"n={len(_v)}", ha="center", va="bottom",
                         fontsize=7, color=_c)
        axL.axhline(1.0, ls=":", lw=1.0, color="#888")
        axL.set_xticks(np.arange(_n))
        axL.set_xticklabels([f"{a}\n{b}" for a, b in zip(_labs, _sub)])
        axL.set_ylabel("Fluorescence (fold over cytosol background)")
        _hmed = [float(np.median(v)) if len(v) else float("nan") for v in hec_fold]
        _mmed = [float(np.median(v)) if len(v) else float("nan") for v in mad_fold]
        axL.set_title("Hec1 (640) and Mad1 (488) at per-frame Hec1-dot kinetochores — one linear axis\n"
                      "fold over each dot's own local background; every measured dot shown, "
                      "no outlier removal, no rescaling\n"
                      + (f"Hec1 medians {_hmed[0]:.2f} -> {_hmed[1]:.2f} -> {_hmed[2]:.2f}   |   "
                         f"Mad1 {_mmed[0]:.2f} -> {_mmed[1]:.2f} -> {_mmed[2]:.2f}"
                         if len(_hmed) == 3 and len(_mmed) == 3 else ""), fontsize=9)
        from matplotlib.patches import Patch as _Patch
        axL.legend(handles=[_Patch(facecolor=_HF, label="Hec1 (640)"),
                            _Patch(facecolor=_MF, label="Mad1 (488)"),
                            Line2D([0], [0], ls=":", color="#888", label="1.0 = HER cytosol background")],
                   loc="upper right", fontsize=8)
        figL.tight_layout()
        _lin = out_png.replace(".png", "_linear.png")
        figL.savefig(_lin, dpi=200); plt.close(figL)
        lib.record_plot("G5_hec1_mad1_dot_quant_linear",
                        ["frame_label", "dot_index", "channel", "fold_over_local_bg"],
                        [[_labs[i], j, ch, round(float(v), 4)]
                         for ch, series in (("hec1_640", hec_fold), ("mad1_488", mad_fold))
                         for i, s_ in enumerate(series) for j, v in enumerate(s_)],
                        {"type": "linear-axis sibling of G5_hec1_mad1_dot_quant",
                         "measure": "Sum(disk)/(n*local_bg) at the same disks as the parent figure",
                         "outlier_removal": "none (parent removes 4 F1 Mad1 outliers)",
                         "calibration": "none (parent min-max calibrates each fluorophore to 0-1)",
                         "why": "user 2026-08-20 board 1 item 3 -- linear y-axis, no weird scale"},
                        SCRIPT, "Hec1 and Mad1 at Hec1-dot kinetochores, fold over local background, "
                                "one linear axis", key_column=None)
        print(f"wrote {_lin}  (fold-over-bg, linear axis, no outlier removal)")
    if MAD_RAW_VALUES:
        _r=np.array(MAD_RAW_VALUES,float); _neg=_r[_r<0]
        print(f"  MAD1 PRE-FLOOR DIAGNOSIS: n={len(_r)}  negatives={len(_neg)} "
              f"({100*len(_neg)/len(_r):.1f}%)  min={_r.min():.1f}  "
              + (f"most negative={_neg.min():.1f}  |median negative|={abs(np.median(_neg)):.1f}" if len(_neg) else "no negatives"))
    print(f"wrote {out_png}  dots/frame={[len(d) for d in hec_vals]}  "
          f"Hec1 calib range={HEC_LO:.0f}..{HEC_HI:.0f} a.u.  Mad1(|v|) calib range={MAD_LO:.0f}..{MAD_HI:.0f} a.u.  "
          f"Hec1 means(0-1)={[round(float(np.mean(h)),2) for h in hec_vals]}  "
          f"Mad1 means(0-1)={[round(float(np.mean(m)),2) for m in mad_vals]}  "
          f"Mad1 points negative before abs={n_neg_before_abs}/{sum(len(m) for m in mad_vals)}")
    return [len(d) for d in hec_vals], data_rows


# ---------------- auto frame selection for batches with NO specified frames ----------------
def auto_targets(bat, n=3):
    """Pick n distinct monitoring timepoints (first / middle / last), labelled start/mid/late with mm:ss."""
    ts = sorted({round(float(t), 1) for t in bat["mon_ts"]})
    if not ts: return []
    idx = np.linspace(0, len(ts)-1, min(n, len(ts))).astype(int)
    tags = ["start", "mid", "late"] if len(idx) == 3 else [""]*len(idx)
    out = []
    for j, k in enumerate(idx):
        t = ts[k]; mm, ss = divmod(int(round(t)), 60)
        lab = f"{mm}:{ss:02d}" + (f"  {tags[j]}" if tags[j] else "")
        out.append((t, lab))
    return out


# ================= build =================
# (batch_suffix, explicit TARGETS or None -> auto, do_dot_quant)
JOBS = [
    ("xy5", [(85.0, "1:25  unaligned"), (442.7, "7:22  biorientation"), (904.2, "15:04  anaphase onset")], True),
    ("xy2", None, False),
    ("xy4", None, False),
    ("xy6", None, False),
]
_ONLY = os.environ.get("HEC1_ONLY")
if _ONLY: JOBS = [j for j in JOBS if j[0] in _ONLY.split(",")]
made = []
for suf, targets, do_q in JOBS:
    B = f"20260313 ptk_eyfp_mad1_Hec1halo_640_4_{suf}"
    if not os.path.isfile(f"{SESS}/{B}/{B}_frames.json"):
        print(f"  skip {suf}: no frames.json"); continue
    bat = load_batch(B)
    tg = targets if targets is not None else auto_targets(bat)
    if not tg:
        print(f"  skip {suf}: no monitoring frames"); continue
    ts_png = f"{OUT}/G5_item4_hec1_timestrip_{suf}.png"
    CROP, _ = build_timestrip(bat, tg, ts_png)
    made.append(os.path.basename(ts_png))
    lib.record_plot(f"G5_item4_hec1_timestrip_{suf}", ["batch"], [[B]],
        {"type": "hec1 timestrip (gutter labels, raw-stretched, hotpink Hec1, uniform Hec1-crop)",
         "crop": list(CROP), "targets": [c for _, c in tg], "auto_frames": targets is None},
        SCRIPT, f"Hec1 timestrip {suf}")
    if do_q:
        q_png = f"{OUT}/G5_hec1_mad1_dot_quant.png"
        ndots, qrows = build_dot_quant(bat, tg, CROP, q_png)
        # 2026-08-03 (feedback item B, "Mad1 should not have negative fluorescence value"): this call used to
        # register a FAKE one-row table (["batch"],[[B]]) with no measured values -- the same class of bug as
        # the empty-row-list builders found 2026-07-29, and the reason the negative-value question could not
        # even be checked against recorded numbers (2026-07-30 review, item 25). Now records every real
        # per-dot (frame, dot_index, channel, value_au) row so the figure is traceable/auditable like every
        # other plot; key_column="frame_label" groups the 6 violins (3 frames x 2 channels).
        lib.record_plot("G5_hec1_mad1_dot_quant",
            ["frame_label", "dot_index", "channel", "value_au", "value_calibrated01"], qrows,
            {"type": "Hec1/Mad1 dot-intensity violins (per-frame Hec1 dot detection); each fluorophore "
                     "min-max calibrated to 0-1 on its own values (user 2026-08-04)",
             "batch": B, "n_dots_per_frame": ndots,
             "mad1_transform": "absolute value taken before calibration (user 2026-08-04)",
             "mad1_measurement": "lib.disk_local_bg at the registration-corrected Mad1 local peak "
                                  "(see mad_at_dot docstring), floored at 0"},
            SCRIPT, "Hec1 vs Mad1 intensity at per-frame Hec1 dots",
            source=[f"{SESS}/{B}/{B}_frames.json", f"{SESS}/{B}/{B}_Fluor_Cropped.tif",
                    f"{SESS}/{B}/{B}_640_Cy5_Cropped.tif"],
            key_column="frame_label")

print("Hec1 timestrips:", made)
