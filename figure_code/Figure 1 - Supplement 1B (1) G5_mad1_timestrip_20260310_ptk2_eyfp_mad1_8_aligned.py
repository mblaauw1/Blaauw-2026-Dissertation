# NOTES §1 rule 30 (user 2026-08-16): a RED marker on a GREEN fluorescence panel is the exact
# red/green pair that ~8%% of men cannot separate. Ablation-site markers are now MAGENTA
# (255,0,255) BGR, the standard accessible complement to green, unchanged in shape and width.
"""Group 5 / IF4 — Mad1 timelapse example TIMESTRIPS (one slide/batch) + Mad1 z-stack MIP grid.

07-07 feedback (IF4, raw L329):
 * Mad1 timelapse batches flagged "good for example / timestrips" in Notes/annotation_notes (may be marked
   Exclude=Yes -> that's fine here) -> ONE timestrip slide per batch.
     - batches WITH ablations follow the ablation-timestrip format (ablation strip w/ red-CIRCLE site markers +
       ablation zoom + monitoring), via the shared editable ts_render module (T1/T2/T5/T7).
     - batches with NO ablation -> monitoring strip only (phase top / Mad1 fluor bottom).
 * these cells have NO manual outlines -> the crop is ESTIMATED from the cell shape in FLUORESCENCE at the start
   of ablation (or the first monitoring frame): the cell of interest is CENTRED; bright neighbours are ignored.
 * Mad1 z-stacks flagged as good examples -> MAX-INTENSITY PROJECTIONS placed together on ONE grid slide.

Selection is driven off the live master (Notes / annotation_notes) but pinned to a curated set so the deck
placement is deterministic; see TIMESTRIP_BATCHES / ZSTACK_BATCHES below.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import glob, os, json, re, numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter
import lib, ts_render

def clean_title(s):
    """Strip banned mitotic-STAGE words (prometaphase/metaphase/anaphase) from a batch string so they never
    appear in a rendered timestrip TITLE (user rule: no stage words in titles). A batch like
    '..._ablation_1metaphase_52' -> '..._ablation_1_52'. Collapses the underscores left behind."""
    s = re.sub(r'(?i)(pro)?(meta|ana)phase', '', s)
    return re.sub(r'_+', '_', s).strip('_ ')

OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except: return 0.062

# --- curated, comment-flagged Mad1 examples (Notes say "good for example/timestrips") ---
# 2026-08-03 (feedback item A / 2026-07-30 review item 28): "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52"
# REMOVED from this list -- confirmed a cdc20 cell mislabelled as Mad1 (master Cell Type = "eYFP cdc20"; the
# batch name's own "Eyfpcdc2" says cdc20; the "Mad1_Ptk_" prefix is just that day's SESSION-folder name, shared
# with 76 genuinely-cdc20 batches; her annotation Notes describe sisterless/lagging-KT cdc20-style behaviour,
# not Mad1 signal loss). It was pulled into this Mad1 timestrip builder by the same bug fixed at the source in
# lib.is_mad1() (see that function's docstring) -- removing it here as well so the curated example list agrees
# with the classifier and it can never be re-selected as a Mad1 example. Not replaced with a cdc20-timestrip
# entry here; that belongs in a cdc20/group1-4 builder, out of this file's scope.
# "20260310 ptk2_eyfp_mad1_14" was flagged in the SAME feedback but the master Cell Type ("eYFP mad1") and her
# own Notes ("mad1 localization on remaining kinetochore until anaphase") both say Mad1, and the 2026-07-30
# review already asked her to confirm before changing it -- she has not yet answered, so it is LEFT IN pending
# that confirmation, not silently removed. See lib.is_mad1() docstring and this session's report.
TIMESTRIP_BATCHES = [
    # non-ablation "whole of mitosis" Mad1 examples (monitoring only)
    ("20260304 Mad1_timelapse_2_xy1",  "Mad1 through mitosis (minimal bleaching)"),
    ("20260304 Mad1_timelapse_2_xy10", "Mad1 through mitosis; natural polar chromosome retains Mad1"),
    ("20260304 Mad1_timelapse_1_xy6",  "Mad1 through mitosis"),
    # ablation examples (follow ablation-timestrip format)
    ("20260310 ptk2_eyfp_mad1_14",     "Targeted chromosome stays at pole with Mad1 until anaphase"),
    ("20260303 Mad1_Ptk_Eyfpmad1_ablation_10", "Blind ablation (Mad1 had left KTs)"),
    # ---- 2026-08-03 (item 1a, Board M3 "circle back... more mad1 ablation timestrips") ----------------------
    # Enumerated EVERY batch where master Cell Type contains "mad1" (lib.is_mad1(), the POST-CLASSIFIER-FIX
    # source of truth -- NOT a name substring), Exclude != Yes, and the batch name contains "ablation". Of 245
    # Cell-Type-Mad1 rows that narrowed to 15 candidates; PAS log (frames.json ablation_events_local, never the
    # filename) confirmed a REAL ablation (>0 events) for 13 of them -- 2 name-says-ablation batches
    # (`20251209 mad1_1_ablation_9`, `20260312 ptk_eyfp_mad1_ablation_22`) have ZERO logged ablation events and
    # are monitoring-only acquisitions; NOT built as ablation timestrips (see report). Of the 13 PAS-confirmed,
    # 2 (`ptk2_eyfp_mad1_14`, `Eyfpmad1_ablation_10`) were already above; `20251209 mad1_1_ablation_1` has
    # neither On-Target/Off-Target nor # Sisterless KTs characterized in the master (an annotation gap, not a
    # data problem) so it is left OUT here pending that characterization rather than guessed at. The remaining
    # 8 below are the full set actually available; every note is a direct paraphrase of HER OWN master Notes/
    # annotation_notes for that batch, not an inferred claim, and negative/blind-ablation results are included
    # deliberately (a blind ablation showing NO Mad1 change is the specificity control for the ones that do).
    # STILL OUT, but the 2026-08-03 REASON WAS WRONG and is corrected here (2026-08-07).
    # Old note claimed "the phase movie genuinely lacks frames ... the source data is too sparse". FALSE.
    # Every phase page exists and has real content (9 pages, std 31-47, max ~1900). The blank panels were
    # TWO separate bugs, both now fixed:
    #   (1) 8 of 9 monitoring frames sat on wrong timestamps (359 s gaps vs the real 180 s cadence);
    #   (2) grab() seeked by POSITION in the FULL 22-frame monitoring list against a 9-frame phase movie,
    #       so every request >= 9 failed the read -> black. Fixed by chan_ts()/grab_ch().
    # It renders cleanly now. It is STILL left out for a DIFFERENT, honest reason: the cell walks out of
    # the ROI (in frame at 6:47 and 7:02, at the edge by 13:03, gone by 19:02) and this batch has ZERO
    # manual annotations, so nothing can drive the crop. Give it a few manual cell outlines / KT marks and
    # it becomes a usable 8th Mad1 ablation timestrip -- the underlying data is fine.
    # The G5_mad1_timestrip_20251209_mad1_1_ablation_4[_aligned].png on disk are orphans -- do not place.
    ("20260304 Mad1_ablation_10", "On-target (2 sisterless KTs); Mad1 briefly seen on one non-plate KT (her Notes); polar+lagging both yes"),
    ("20260304 Mad1_ablation_17", "On-target (1 sisterless KT); Mad1 at the polar kinetochore after ablation (her Notes); ablation itself is messy"),
    ("20260304 Mad1_ablation_8",  "On-target (1 sisterless KT); Mad1 signal seen on the lagging chromosome, not stretched (her Notes)"),
    ("20260310 ptk2_eyfp_mad1_8", "On-target (1 sisterless KT); Mad1 signal appears then disappears on the targeted KT (her Notes) -- possible transient/satisfied checkpoint"),
    ("20260303 Mad1_Ptk_Eyfpmad1_ablation_1", "Targeted chromosome oscillates at the pole; her Notes: signal only 'barely' relocalizes, may be hard to quantify"),
    ("20260304 Mad1_ablation_13", "BLIND ablation (on-target, 1 sisterless KT): her Notes say NO visible Mad1 relocalization -- specificity control"),
    ("20260304 Mad1_ablation_19", "BLIND ablation: her Notes say NO Mad1 localization seen; ablation success itself unprovable -- specificity control"),
]
ZSTACK_BATCHES = [
    ("20260302 Mad1_Ptk_FullVolume_17", "Near-metaphase; Mad1 on chromosome off the plate"),
    ("20260313 ptk_eyfp_mad1_Hec1halo_640_1", "KTs marked by Hec1 + Mad1"),
]

# ---- render-dir index ----
_RDIR = {}
for _fj in glob.glob("/Volumes/4 MB/**/*_frames.json", recursive=True):
    d = os.path.dirname(_fj)
    if "_ARCHIVED" in _fj or "backup" in _fj.lower(): continue
    _RDIR.setdefault(os.path.basename(d), d)
def render_dir(b): return _RDIR.get(b)
def fjson(b):
    d = render_dir(b)
    if d and os.path.isfile(f"{d}/{b}_frames.json"): return json.load(open(f"{d}/{b}_frames.json"))
    return None
def role_frames(b, role):
    fj = fjson(b)
    return [f for f in fj["frames"] if f["role"] == role] if fj else []
def role_ts(b, role):
    fr = role_frames(b, role)
    return np.array([f["t_sec"] for f in fr]) if fr else None
# ---- MANUAL ANNOTATIONS BEAT THE ESTIMATES (user, standing rule; re-raised 2026-08-06) --------------
# Her open feedback on the non-Hec1 Mad1 timestrips was (a) the whole-cell ROI is wrong/unchanged and
# (b) the ablation-zoom red marker sits on cytoplasmic noise instead of the kinetochore. This file's
# header asserts "these cells have NO manual outlines", which is no longer true: 20260310 ptk2_eyfp_mad1_14
# now has 26 hand-drawn MONITORING cell outlines and a manual pre_abl KT mark. The estimate was being used
# anyway, which is exactly the "unchanged despite per-batch instructions" complaint.
import csv as _csv
_csv.field_size_limit(10 ** 9)
_MAN_OUT = None
_MAN_KT = None


def manual_outline_pts(b, phase=None):
    """Hand-drawn cell-outline points for a batch, as an Nx2 array in cropped-movie pixels (the same space
    the estimated crop uses). `phase` filters 'mon'/'abl'; None takes both. Empty -> None."""
    global _MAN_OUT
    if _MAN_OUT is None:
        _MAN_OUT = {}
        rows = list(_csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv")))
        ix = {c: i for i, c in enumerate(rows[0])}
        for r in rows[1:]:
            try:
                pts = np.array(json.loads(r[ix["points"]]), float)
                if pts.size: _MAN_OUT.setdefault((r[ix["batch"]].strip(), r[ix["phase"]].strip()), []).append(pts)
            except Exception:
                pass
    got = []
    for (bb, ph), v in _MAN_OUT.items():
        if bb == b and (phase is None or ph == phase): got.extend(v)
    return np.vstack(got) if got else None


def manual_pre_abl(b):
    """Her hand-placed pre-ablation KT marks as [(x, y, t_sec)] in cropped-movie pixels, or []."""
    global _MAN_KT
    if _MAN_KT is None:
        _MAN_KT = {}
        rows = list(_csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
        ix = {c: i for i, c in enumerate(rows[0])}
        for r in rows[1:]:
            if r[ix["label"]].strip() != "pre_abl": continue
            try:
                _MAN_KT.setdefault(r[ix["batch"]].strip(), []).append(
                    (float(r[ix["x"]]), float(r[ix["y"]]), float(r[ix["t_sec"]])))
            except Exception:
                pass
    seen, out = set(), []
    for x, y, t in sorted(_MAN_KT.get(b, [])):        # de-duplicate identical repeats
        k = (round(x, 1), round(y, 1))
        if k in seen: continue
        seen.add(k); out.append((x, y, t))
    return out


def abl_events(b):
    """Ablation events as (x_local, y_local, t_sec) in the CROPPED frame's coordinate space.
    Coord map (x_px - roi.x, y_px - roi.y) matches the pipeline (process.py draw_ablation_marker: the
    sidecar x_px/y_px are FULL-image coords despite the '_local' key name). t_sec is derived per event as
    (epoch_ms - events[0].epoch_ms)/1000 -> the SAME anchored timebase as the frames' t_sec (the pipeline
    anchors frame t_sec so the first ablation event sits at ~0), so an event can be matched to the frame in
    which the KT is actually AT that pixel. Marking/zooming on the true event time (not the first
    ablation-role frame, which is ~17s of pre-ablation baseline) is what puts the ring ON the ablated KT."""
    # MANUAL FIRST: a hand-placed pre_abl mark IS the kinetochore, so it defines both the red circle and
    # the zoom centre. The PointAndShoot aim point carries a registration offset vs the fluor camera, which
    # is what put the marker on cytoplasmic noise on the dim Mad1 cells.
    _man = manual_pre_abl(b)
    if _man:
        return [(x, y, t) for x, y, t in _man]
    fj = fjson(b)
    if not fj: return []
    roi = fj.get("roi") or {"x": 0, "y": 0}
    raw = fj.get("ablation_events_local", [])
    t0 = float(raw[0]["epoch_ms"]) if raw else 0.0
    out = []
    for e in raw:
        try: out.append((e["x_px"] - roi.get("x", 0), e["y_px"] - roi.get("y", 0),
                         (float(e["epoch_ms"]) - t0) / 1000.0))
        except: pass
    return out
def refine_ablation_xy(b, ex, ey, te, sat=15000, R=55):
    """Refine an ablation-event coord (ex,ey local) to the TRUE ablation site = centroid of the saturated laser
    FLASH in the raw fluor plane AT the event time. The PointAndShoot-logged x_px/y_px carry a small (up to
    ~30px) registration offset vs the fluor camera, so the raw event coord lands a hair OFF the spot the laser
    actually hit; the saturated flash (>>any real fluor signal) is ground-truth for where the beam landed in
    fluor-image space. Bounded search (±R px) so it can never wander to a far pixel; falls back to (ex,ey) when
    no saturated flash is present (dim cells whose flash shows only in brightfield, e.g. eyfpmad1_ablation_10)."""
    # DROPPED 2026-07-20 (user): the fluor-flash refine snapped the marker to the brightest saturated blob within
    # ±R px, which for dim Mad1 cells is a bloomed/scattered flash or cytoplasmic hot-pixel OFFSET from the true KT
    # (landed 24-31px = 1.5-2µm off the kinetochore). Use the PointAndShoot AIM point (the logged coord) directly.
    # (Where a manual pre_abl mark exists it should be preferred upstream — the true manual-over-auto ground truth.)
    return ex, ey

def movie(b, ch, role):
    d = render_dir(b)
    if not d: return None
    mp4 = f"{d}/{b}_{ch}_{role}.mp4"
    if not os.path.isfile(mp4) or os.path.getsize(mp4) < 1000: return None
    cap = cv2.VideoCapture(mp4)
    if int(cap.get(7)) < 1: cap.release(); return None
    return cap
def grab(cap, ts, t):
    fi = int(np.argmin(np.abs(ts - t))); cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, fr = cap.read()
    return fr if ok else None
def chan_ts(b, role, key):
    """Times of the frames that ACTUALLY EXIST in one channel's movie.

    THE BUG THIS FIXES: grab() seeks by POSITION in whatever ts it is handed. Handing it the full
    monitoring list is wrong whenever a channel has fewer frames than that list -- a channel acquired at
    reduced cadence, or a monitoring stream with a z-stack appended (all its planes share one t_sec but
    only the phase/fluor pages that exist get written to that channel's mp4). Every index past the movie's
    frame count then fails the read and the panel comes out BLACK.

    20251209 mad1_1_ablation_4 is the worked example: 22 monitoring frames (13 z-stack planes at 6:46 +
    9 real timepoints) but Phase_Monitoring.mp4 has only 9 frames. Requests for 7:02..31:02 landed on
    indices 13..21, all >= 9, all black -- which was misread for months as "the source data is too sparse
    for a clean timestrip" and cost this batch its figure. The phase pages were there the whole time
    (std 31-47, max ~1900).

    Returns None if the channel has no frames, so callers can fall back."""
    fr = role_frames(b, role)
    if not fr: return None
    ts = [f["t_sec"] for f in fr if f.get(key) is not None]
    return np.array(ts) if ts else None


def grab_ch(b, role, key, cap, t):
    """grab() against ONE channel's own frame list. Returns None (-> blank panel) rather than snapping to a
    far-away frame, so a genuinely missing timepoint stays honestly empty instead of showing the wrong one."""
    ts = chan_ts(b, role, key)
    if ts is None or not len(ts): return None
    d = np.abs(ts - t); i = int(np.argmin(d))
    if len(ts) > 1:
        gaps = np.diff(np.unique(ts))
        if len(gaps) and d[i] > float(np.median(gaps)) * 0.5: return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, fr = cap.read()
    return fr if ok else None


def _is_dark(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
    return float(np.percentile(g, 99.5)) < 12

# Uniform display gamma applied IDENTICALLY to every frame of a strip-type. Mad1 timelapses fade ~3x from a
# bright first frame (prophase, Mad1 on all KTs) to dim late frames (metaphase/anaphase, Mad1 mostly gone), so a
# purely-linear white point either blows frame 1 or crushes the late frames. A mild gamma < 1 lifts the low/mid
# tones (late-frame puncta become visible) while a high-enough white point keeps frame 1 bright-with-gradient
# rather than a solid saturated blob. It is a SINGLE constant applied uniformly -> exposure stays uniform.
GAMMA = 0.6

def _stretch_green(plane, lo_p=50, hi_p=99.8, gamma=GAMMA, lo=None, hi=None):
    """Robust stretch of a raw fluor plane -> green BGR. UNIFORM-EXPOSURE (coordinator feedback): pass explicit
    lo/hi (computed ONCE over a whole strip-type) so EVERY frame of that type shares ONE fixed intensity
    mapping — fixes the Mad1 monitoring bug where one diffuse frame blew to solid green and the rest crushed to
    black under per-frame auto-normalisation. lo/hi=None falls back to this frame's own percentiles.
    Base percentiles (07-08): lo_p 50 pins diffuse background/haze to black; hi_p 99.8 keeps only the brightest
    puncta near saturation so Mad1 STRUCTURE reads instead of a blown-out flat green. A mild UNIFORM gamma
    (GAMMA<1) lifts the late (dim) frames into visibility without lowering the white point -> frame 1 keeps a
    gradient instead of clipping to a solid blob. Same gamma on every frame keeps the exposure uniform."""
    a = plane.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)
    g8 = (n * 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8    # BGR green
    return green

def raw_fluor_plane(b, role, t, tol=0.2):
    """Selected RAW Mad1 (488) fluor plane (float32) for a `role` timepoint t, NO stretch. When several frames
    share ~ONE t_sec (a trailing z-stack, e.g. _1_xy6's 4068.2s block) pick the IN-FOCUS page = the max-variance
    plane, not the first (often a dark out-of-focus slice) -> late frames aren't black."""
    d = render_dir(b)
    fp = f"{d}/{b}_Fluor_Cropped.tif" if d else None
    if not fp or not os.path.isfile(fp): return None
    same = [f for f in role_frames(b, role) if abs(float(f["t_sec"]) - t) <= tol]
    if not same: return None
    idxs = [int(f["fluor_tif_idx"]) for f in same if f.get("fluor_tif_idx") is not None]   # fluor_tif_idx can be present-but-None
    if not idxs: return None
    try:
        with tifffile.TiffFile(fp) as tf:
            n = len(tf.pages)
            cand = [i for i in idxs if 0 <= i < n] or [min(max(idxs[0], 0), n-1)]
            best, bv = cand[0], -1.0
            for i in cand:
                v = float(tf.pages[i].asarray().astype(np.float32).var())
                if v > bv: bv, best = v, i
            return tf.pages[best].asarray().astype(np.float32)
    except Exception:
        return None

def raw_fluor(b, role, t, tol=0.2, lo=None, hi=None):
    """Raw Mad1 (488) fluor panel, stretched with the strip-type's SHARED lo/hi (see _stretch_green)."""
    p = raw_fluor_plane(b, role, t, tol)
    return _stretch_green(p, lo=lo, hi=hi) if p is not None else None

# ---- ONE robust (lo,hi) exposure per strip-type (tunable) ----
# On long Mad1 timelapses the FIRST frame is far brighter than later monitoring frames. Pooling pixels over ALL
# frames and taking the near-MAX (old hi_p=99.8) let frame 1's brightest specks dominate the white point, so the
# later frames crushed to near-black. Use a ROBUST high percentile (HI_PCT) so the bulk of frame 1 is preserved
# (its brightest tips may clip only at the very tip) while later frames LIFT into visibility. LO_PCT stays at the
# background/haze anchor (median) so diffuse Mad1 haze pins to black instead of a green wash.
HI_PCT = 99.7    # robust white point: pooled top-0.3% (NOT the max). Kept high enough that the bright first
                 # frame retains a gradient (only its brightest specks clip) rather than clipping to a solid
                 # blob; the late-frame lift is done by GAMMA below, not by crushing the white point.
LO_PCT = 65.0    # low anchor above the pooled median: pins diffuse background/haze to black so GAMMA doesn't
                 # raise a green wash. Late-frame Mad1 puncta sit above this and stay visible.

# 2026-08-03 (her item: "...20260310 ptk2_eyfp_mad1_14... are showing cdc20 cells, not mad1"). The
# ASSIGNMENT is not wrong -- all twelve cells imaged on 20260310 are eYFP mad1 in the master, there is no
# cdc20 on that plate, her own Notes for this batch read "mad1 localization on remaining kinetochore until
# anaphase", and the monitoring row does show a persistent KT dot. What is wrong is the RENDER: this cell
# has an unusually bright diffuse nucleoplasmic pool, so at LO_PCT=65 the pool fills the frame and the KT
# punctum washes out, giving the bright-fill-with-dark-chromosome-silhouettes look that reads as Cdc20.
# Per-batch stretch override (same pattern as MONITOR_TMAX / ABL_SHOW_PHASE): raise the low anchor so the
# diffuse pool goes to black and the puncta stand out. Purely a display change -- no measurement uses it.
FLUOR_STRETCH_PCT = {"20260310 ptk2_eyfp_mad1_14": (88.0, 99.9)}

def strip_fluor_limits(b, role, times, tol=0.2, lo_p=None, hi_p=None):
    _ov = FLUOR_STRETCH_PCT.get(b)
    if lo_p is None: lo_p = _ov[0] if _ov else LO_PCT
    if hi_p is None: hi_p = _ov[1] if _ov else HI_PCT
    """ONE (lo,hi) intensity mapping for a whole strip-type: percentiles pooled over ALL its selected raw
    planes (frame 1 INCLUDED -> not excluded, not middle-frames-only) -> applied identically to every frame of
    that type. hi = HI_PCT (robust high percentile, NOT the max) so a bright first frame doesn't crush the rest;
    lo = LO_PCT low anchor. Returns (lo, hi, planes) with planes aligned to `times` (cached so callers don't
    re-read the tif). Same robust mapping is computed independently for the ablation and monitoring strip-types."""
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes

def raw_fluor_monitor(b, t):
    return raw_fluor(b, "monitoring", t)

# ---- crop estimated from FLUORESCENCE (raw Cropped tif) of the cell centred in the frame ----
def fluor_crop(b, as_pts=False):
    """Estimate a tight square-ish crop from the centred cell in the first fluor frame (raw tif preferred).
    as_pts=True -> return (bbox_corner_pts, W, H) of the ESTIMATED cell blob (NO added margin) so the caller can
    feed the points to ts_render.tight_square for a TIGHT, exactly-square, undistorted crop that fills the frame."""
    fj = fjson(b); d = render_dir(b)
    if not fj or not d: return None
    # first frame: prefer ablation-start, else first monitoring
    fr0 = (role_frames(b, "ablation") or role_frames(b, "monitoring"))
    if not fr0: return None
    fr0 = fr0[0]
    fpath = f"{d}/{b}_Fluor_Cropped.tif"
    plane = None
    if os.path.isfile(fpath):
        stk = tifffile.imread(fpath); idx = int(fr0["fluor_tif_idx"])
        plane = (stk[min(idx, stk.shape[0]-1)] if stk.ndim == 3 else np.squeeze(stk)).astype(np.float32)
    else:                                   # fall back to the rendered fluor movie frame
        cap = movie(b, "Fluor", "Ablation") or movie(b, "Fluor", "Monitoring")
        if not cap: return None
        ts = role_ts(b, "ablation"); ts = ts if ts is not None else role_ts(b, "monitoring")
        f = grab(cap, ts, float(ts[0])); cap.release()
        if f is None: return None
        plane = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = plane.shape
    if as_pts:   # BRIGHTFIELD-based cell detection (fluor too diffuse): texture of the refractile mitotic cell
        for R, r in (("Ablation", "ablation"), ("Monitoring", "monitoring")):
            cap = movie(b, "Phase", R)
            if not cap: continue
            mts = role_ts(b, r)
            bf = grab(cap, mts, float(mts[0])) if mts is not None and len(mts) else None; cap.release()
            if bf is not None: return (ts_render.brightfield_cell_bbox_pts(bf), W, H)
        return (ts_render.fluor_cell_bbox_pts(plane), W, H)
    lo, hi = np.percentile(plane, 40), np.percentile(plane, 99.7)
    g8 = np.clip((plane - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    sm = gaussian_filter(g8.astype(np.float32), 3.0)
    cy, cx = H // 2, W // 2; ry, rx = int(H * 0.32), int(W * 0.32)  # central window (cell of interest centred)
    mask = np.zeros_like(sm, bool); mask[cy-ry:cy+ry, cx-rx:cx+rx] = True
    thr = (sm > np.percentile(sm[mask], 96)) & mask
    # keep the connected blob nearest the centre
    n, lbl, stats, cent = cv2.connectedComponentsWithStats(thr.astype(np.uint8), 8)
    best, bd = None, 1e18
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 40: continue
        dd = (cent[i][0]-cx)**2 + (cent[i][1]-cy)**2
        if dd < bd: bd, best = dd, i
    if best is None:
        hw = min(H, W)//3
        return (cx-hw, cy-hw, cx+hw, cy+hw)
    x, y, w, h = stats[best, 0], stats[best, 1], stats[best, 2], stats[best, 3]
    m = 55
    return (max(0, x-m), max(0, y-m), min(W, x+w+m), min(H, y+h+m))

# Uniform tight margin (matches slippage/drug) — the shared ts_render.fluor_cell_bbox_pts estimator already
# sizes to the cell body, so the CELL fills ~1/margin of the exactly-square (no-distortion) crop.
def fluor_tight_crop(b, margin=1.12):
    """UNIFORM-scale-before-crop square window from the FLUOR/brightfield-estimated cell blob
    (ts_render.tight_square, margin=1.12 -> cell fills ~89% of the frame, small breathing room, no clipped
    edges; a per-batch CROP_OFFSETS nudge repositions where it sits). Reused for ALL frames of the batch."""
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)

def manual_tight_crop(b, margin=1.12):
    """Square crop built from her HAND-DRAWN cell outline (monitoring preferred, else any phase).
    Same tight_square primitive as the estimate, so framing/fill behaviour is identical - only the source
    of the cell bbox changes, from a fluorescence guess to her tracing."""
    pts = manual_outline_pts(b, "mon")
    if pts is None: pts = manual_outline_pts(b)
    if pts is None: return None
    cap = movie(b, "Fluor", "Monitoring") or movie(b, "Fluor", "Ablation")
    if cap is None: return None
    # movie() in THIS module returns a bare cv2.VideoCapture (group_timestrips' returns a (cap, ts) tuple)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)


def std_crop(b):
    """TIGHT square crop (ts_render.tight_square) sized to THIS cell's FLUOR-estimated bbox -> cell fills the
    frame; forced exactly square so the aligned resize is uniform (no non-uniform stretch). Shared by main +
    monitoring tiles of a batch. None if the fluor crop / movie is unavailable."""
    # NOT manual_tight_crop() here. Her outlines are traced on the MONITORING frames, so their union is
    # centred on where the cell travels during monitoring - which is not where it sits during the ablation.
    # Using it for this shared crop pushed the ablation panels of ptk2_eyfp_mad1_14 almost entirely off
    # frame (verified in the 12:11 render: near-black ablation row, cell against the right edge).
    # Her tracing IS used for monitoring, per-frame, via manual_centres() in follow_centres().
    return fluor_tight_crop(b)

# ---- ablation portion (before / red-circle marked / after) + zoom close-ups (like polar strips) ----
def nonflash_t(b, role, t):
    ts = role_ts(b, role); cap = movie(b, "Phase", role)
    if ts is None or cap is None:
        if cap: cap.release()
        return t
    i = int(np.argmin(np.abs(ts - t))); guard = 0
    while i > 0 and guard < 5:
        fr = grab(cap, ts, ts[i])
        if fr is None or not _is_dark(fr): break
        i -= 1; guard += 1
    cap.release(); return float(ts[i])

def clean_abl_times(tsa, ev_ts, t_center, win=1.6):
    """(before, during, after) ablation-frame times straddling t_center, skipping the FLASH frames. An
    ablation-laser frame (saturated brightfield moiré / grid) is exactly the frame COINCIDENT with an event,
    so any frame within `win` seconds of an event time is treated as a flash and skipped. `during` = the
    nearest CLEAN frame to t_center (the marker still sits on the targeted KT), `before`/`after` = its clean
    neighbours -> a before/ablation/after triptych with no blown-out flash panel."""
    tsa = np.asarray(tsa, float)
    if len(ev_ts):
        d = np.min(np.abs(tsa[:, None] - np.asarray(ev_ts, float)[None, :]), axis=1)
        clean = np.where(d >= win)[0]
    else:
        clean = np.arange(len(tsa))
    if len(clean) == 0: clean = np.arange(len(tsa))
    ci = int(clean[int(np.argmin(np.abs(tsa[clean] - t_center)))])
    pos = int(np.searchsorted(clean, ci))
    bi = int(clean[max(0, pos-1)]); ai = int(clean[min(len(clean)-1, pos+1)])
    return float(tsa[bi]), float(tsa[ci]), float(tsa[ai])

def ablation_portion(b, crop, aligned=False, sq=None, show_phase=False):
    """aligned=True: crop main tiles to the fixed-physical `sq` window + resample to ts_render.ALIGN_N (square,
    consistent magnification across batches); the zoom uses a fixed-µm half so its physical window matches too.
    show_phase=True: emit the ablation rows as PHASE + FLUOR instead of fluor-only (see ABL_SHOW_PHASE)."""
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b); t_first, t_last = float(tsa.min()), float(tsa.max())
    # ABLATION MOMENT = time of the first ablation EVENT (its t_sec ~= 0 in the anchored timebase), NOT the
    # first ablation-ROLE frame (t_first ~= -17s = pre-ablation baseline). The old t_first choice marked/zoomed
    # a frame taken ~17s BEFORE the KT reached the ablation site -> the ring sat on empty cytoplasm and the
    # zoom cropped the wrong spot. Anchoring on the event time puts the frame where the KT is actually AT (x,y).
    ev_ts = [te for (_, _, te) in evs]
    t_prim = float(ev_ts[0]) if ev_ts else t_first
    tb, tm, ta = clean_abl_times(tsa, ev_ts, t_prim)
    _aft = ABL_AFTER_SEC.get(b)           # ITEMS 13/32: "after" should be a real elapsed time, not the next frame
    if _aft:
        _clean = [t for t in tsa if all(abs(t - e) >= 1.6 for e in ev_ts)] if len(ev_ts) else list(tsa)
        _later = [t for t in _clean if t >= t_prim + _aft]
        if _later: ta = float(min(_later))
        elif _clean: ta = float(max(_clean))
        print(f"    {b}: 'after' tile at {ta - t_prim:+.1f}s from ablation (target {_aft:.0f}s)")
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
    # A long targeted ablation logs the KT at MANY positions as it travels to the pole; drawing every event
    # on one frame scatters rings across the whole trajectory. Mark only the events at THIS instant so the
    # ring(s) land on the KT where it sits in the displayed frame.
    # refine each event to the TRUE ablation site (saturated laser flash) so the ring sits on the real target,
    # not the ~registration-offset PointAndShoot pixel (which drifts a hair off the ablated KT).
    _cap = ABL_MAX_EVENTS.get(b)          # ITEMS 13/32: one targeted KT -> one ablation line
    now_evs = [refine_ablation_xy(b, x, y, te) for (x, y, te) in evs if abs(te - tm) <= 3.0]
    if not now_evs and evs: now_evs = [refine_ablation_xy(b, evs[0][0], evs[0][1], evs[0][2])]
    if _cap: now_evs = now_evs[:_cap]
    mcrop = sq if aligned else crop
    # ONE fixed intensity mapping for the WHOLE ablation strip-type (main + zoom) — no per-frame normalisation.
    abl_lo, abl_hi, _ = strip_fluor_limits(b, "ablation", [t for (_, t, _) in times])
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            # FLUOR from the RAW plane, stretched with the strip-type's SHARED lo/hi (uniform exposure).
            fr = raw_fluor(b, "ablation", t, lo=abl_lo, hi=abl_hi) if key == "fluor" else None
            if fr is None:
                if cap is None: continue
                fr = grab(cap, tsa, t)
                if fr is None: continue
                fr = fr.copy()
            if mk:
                r = max(9, int(0.011 * fr.shape[1]))
                import group_timestrips as _G   # 2026-08-17: shared open-centre X marker, not a circle
                _G.draw_marks(fr, [(x, y, (255,0,255), "x", None) for (x, y) in now_evs])
            # MP4-sourced ablation frame -> exclude the burned-in overlay band from the crop (2026-08-17)
            if mcrop: fr = ts_render.crop_pad(fr, mcrop, band=ts_render.BURNIN_PX).copy()
            wide[ci][key] = fr
        if cap: cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Mad1"), fluor_only=not show_phase)   # 10 um on whole-cell frames (user 2026-08-04)
    if res: portions.append(("ablation", res[0], res[1]))
    HALF = ts_render.zoom_half_px(ps(b)) if aligned else 60; ZOOM = 3
    # USER 2026-08-05: "just keep the second zoom strip shown right now and no need to include the first one
    # (so there will just be one zoom ablation strip)". Read as the general rule it is: ONE zoom strip per
    # ablation timestrip, and when two are available it is the SECOND that is kept. Defaulting to the LAST
    # index expresses that and stays correct for batches already capped to a single event by ABL_MAX_EVENTS
    # (there the only strip is #1, so "the last" is the one strip that exists).
    # WHY ONE STRIP IS THE RIGHT DEFAULT *HERE* specifically: `evs` is ablation EVENTS (individual pulses),
    # not distinct targets. group_timestrips.py and group_drug_ablation_timestrips.py cluster shots into
    # distinct targets first and emit one close-up PER TARGET — this builder never did, so repeated shots at
    # a single kinetochore produced a duplicate zoom row of the same place. Item 15 measured exactly that for
    # ablation_8: 4 bursts / 13 pulses all within 0.76 um = ONE target. Every Mad1 batch in TIMESTRIP_BATCHES
    # is single-target, so one strip is both what she asked for and what the data supports. If a genuinely
    # two-target Mad1 batch is ever added, this needs the clustering the other two builders use, not a
    # different index — leaving the note here rather than pre-building for a case that does not exist.
    _evs = evs[:(ABL_MAX_EVENTS.get(b) or 2)]
    _keep = ABL_ZOOM_KEEP.get(b, (len(_evs),) if _evs else ())   # 1-based; per-batch entry overrides
    _nkeep = 0
    for ei, (ex, ey, te) in enumerate(_evs):
        if (ei + 1) not in _keep: continue
        # ITEMS 13/32: the zoom close-up picked its own before/during/after triptych and so still showed the
        # next clean frame (~7 s). Push its "after" out to the same target elapsed time as the main row.
        # centre the close-up on the TRUE ablation site (saturated-flash refinement of the event coord) AND
        # sample CLEAN frames straddling its time (flash frames skipped), so the ablated KT is genuinely at
        # (ex,ey) in the shown frame and the moiré flash never fills the zoom.
        ex, ey = refine_ablation_xy(b, ex, ey, te)
        ztb, ztm, zta = clean_abl_times(tsa, ev_ts, te)
        if ABL_AFTER_SEC.get(b):        # ITEMS 13/32: same target elapsed "after" as the main row
            _zc = [t for t in tsa if all(abs(t - e) >= 1.6 for e in ev_ts)] if len(ev_ts) else list(tsa)
            _zl = [t for t in _zc if t >= te + ABL_AFTER_SEC[b]]
            zta = float(min(_zl)) if _zl else (float(max(_zc)) if _zc else zta)
        zt = [("before", ztb, False), ("ablation", ztm, True), ("after", zta, False)]
        cu = [{"t": t, "phase": None, "fluor": None} for (_, t, _) in zt]
        for ch in ("Phase", "Fluor"):
            cap = movie(b, ch, "Ablation")
            key = "phase" if ch == "Phase" else "fluor"
            for ci, (tag, t, mk) in enumerate(zt):
                fr = raw_fluor(b, "ablation", t, lo=abl_lo, hi=abl_hi) if key == "fluor" else None   # shared ablation exposure
                if fr is None:
                    if cap is None: continue
                    fr = grab(cap, tsa, t)
                    if fr is None: continue
                if aligned:
                    z = ts_render.zoom_to_square(fr, ex, ey, HALF, mk)
                    if z is not None: cu[ci][key] = z
                else:
                    xi, yi = int(round(ex)), int(round(ey)); h, wd = fr.shape[:2]
                    x0, y0 = max(0, xi-HALF), max(0, yi-HALF); x1, y1 = min(wd, xi+HALF), min(h, yi+HALF)
                    sub = fr[y0:y1, x0:x1].copy()
                    if sub.size == 0: continue
                    if mk:
                        import group_timestrips as _G
                        _G.draw_marks(sub, [(xi-x0, yi-y0, (255,0,255), "x", None)])
                    cu[ci][key] = cv2.resize(sub, (sub.shape[1]*ZOOM, sub.shape[0]*ZOOM), interpolation=cv2.INTER_NEAREST)
            if cap: cap.release()
        zeff = ps(b)*(2*HALF)/ts_render.ALIGN_N if aligned else ps(b)/ZOOM
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None],
                                 zeff, ts_render.nice_scalebar_um(2*HALF*ps(b)),
                                 chan_labels=("Phase", "eYFP-Mad1"), fluor_only=not show_phase, show_fmt=False)
        if res:
            # Numbered only when more than one is actually emitted — with the default single strip a label of
            # "ablation close-up 2" would read as though a first one were missing from the figure.
            _nkeep += 1
            portions.append(("ablation close-up" if len(_keep) < 2 else f"ablation close-up {_nkeep}",
                             res[0], res[1]))
    return portions

# ---- MONITORING CROP THAT FOLLOWS THE CELL (USER 2026-08-05) ------------------------------------
# "the crop used in the timestrip creation for that imaging strip cuts off the cell as it moves through
# monitoring". std_crop() estimates ONE window from the FIRST frame and reuses it for every panel, so a
# cell that translates during monitoring walks out of the window and gets clipped.
# For the batches listed here the monitoring row instead uses a window of the SAME SIZE re-centred on the
# cell in each panel. Size/squareness/physical extent are UNCHANGED, so the uniform resize, the aligned
# ALIGN_N footprint and the µm/px scale bar (eff) all stay exactly as before — only WHERE the window sits
# moves. Detection reuses the same brightfield texture estimator the fixed crop uses, but with a wide
# central window (the cell is no longer centred, which is the whole problem) and seeded from the previous
# panel so it tracks one cell rather than jumping to a neighbour.
# NAME COLLISION AVOIDED: `MONITOR_TRACK` already exists further down (an earlier one-shot approach that
# re-centres the window ONCE for the whole row by template-matching the ablation-phase crop into a
# mid-monitoring frame; it is currently an empty set because the cell's appearance changes too much
# between phases for the match to score). That one was defined AFTER this point in the file, so reusing
# the name silently overwrote this set and the follow did nothing. Different problem, different knob:
# this one re-centres EVERY PANEL, which is what a cell that drifts DURING monitoring needs.
# 2026-08-06 (user): "ive given feedback on the mad1 timestrips ... over the last few days, and it has not
# been implemented. especially regarding moving the ROI of the whole-cell frames". The follow WORKED, but it
# was gated to the single batch it was developed on, so every other Mad1 strip kept the fixed window and the
# cell still walked out of it (ablation_8 clipped by 24:18, ablation_10 and ptk2_eyfp_mad1_8 both drifting).
# That is the recurring "apply the feedback to EVERYTHING of a type" failure, not a new request.
# Following is therefore the DEFAULT now; MONITOR_NOFOLLOW opts an individual batch back out.
MONITOR_NOFOLLOW = set()
def monitor_follows(b):
    """Per-panel cell-following window for the monitoring row — on unless the batch is opted out.

    Requires PAS ablation events. The seed derived from them is the whole reason this works (without it the
    blob estimator repeatedly locked onto a brighter NEIGHBOURING cell — documented at length in this file),
    so a batch with no logged ablation keeps the fixed window rather than tracking blind."""
    return b not in MONITOR_NOFOLLOW and bool(abl_events(b))

TRACK_MAX_STEP_UM = 12.0        # a bigger jump between panels is a mis-detection, not the cell moving

def _bbox_centre(fr, central=None):
    """Cell centre in a full frame. `central` widens the estimator's search window — but the estimator
    RETURNS NONE when it is opened up too far (verified 2026-08-05: central=0.92 -> None on every
    monitoring frame of ptk2_eyfp_mad1_14, which silently sent every panel back to the fixed crop and
    looked exactly like the tracking not working). So try the estimator's own default first and widen only
    as a fallback, taking the first value that actually resolves a cell."""
    for c in ([central] if central else []) + [0.42, 0.55, 0.70]:
        if c is None: continue
        try:
            pts = ts_render.brightfield_cell_bbox_pts(fr, central=c)
        except Exception:
            continue
        if pts is None or len(pts) < 1: continue
        return ((float(pts[:, 0].min()) + float(pts[:, 0].max())) / 2.0,
                (float(pts[:, 1].min()) + float(pts[:, 1].max())) / 2.0)
    return None

_MAN_BYFRAME = None


def manual_centres(b):
    """{t_sec: (cx, cy)} from HER per-frame monitoring cell outlines — the centre of each traced shape.

    Better than the template tracker wherever it exists: it is her own tracing of THIS cell on THAT frame,
    so it cannot lock onto a brighter neighbour (the documented failure mode) and needs no seed. Used as the
    follow track when available; the tracker stays as the fallback for batches with no outlines.
    Returns {} when she has not traced the batch."""
    global _MAN_BYFRAME
    if _MAN_BYFRAME is None:
        _MAN_BYFRAME = {}
        rows = list(_csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv")))
        ix = {c: i for i, c in enumerate(rows[0])}
        for r in rows[1:]:
            if r[ix["phase"]].strip() != "mon": continue
            try:
                pts = np.array(json.loads(r[ix["points"]]), float)
                if not pts.size: continue
                t = float(r[ix["t_sec"]])
                c = ((float(pts[:, 0].min()) + float(pts[:, 0].max())) / 2.0,
                     (float(pts[:, 1].min()) + float(pts[:, 1].max())) / 2.0)
                _MAN_BYFRAME.setdefault(r[ix["batch"]].strip(), {})[t] = c
            except Exception:
                pass
    return dict(_MAN_BYFRAME.get(b, {}))


_MAN_KTA = None
# Labels that mark a KINETOCHORE (i.e. a point INSIDE the target cell). cytosol_bg is deliberately
# excluded: it marks BACKGROUND, chosen away from the chromosomes, so it would bias the centre outward.
KT_ANCHOR_LABELS = ("paired_kt", "sisterless", "polar", "lagging", "pre_abl", "post_abl")


_MAN_PLATE = None


def manual_plate_anchors(b):
    """{t_sec: (cx, cy)} from her metaphase-plate marks — the midpoint of each traced plate line."""
    global _MAN_PLATE
    if _MAN_PLATE is None:
        _MAN_PLATE = {}
        p = "/Volumes/4 MB/annotations/meta_plates.csv"
        if os.path.isfile(p):
            rows = list(_csv.reader(open(p)))
            ix = {c: i for i, c in enumerate(rows[0])}
            acc = {}
            for r in rows[1:]:
                try:
                    pts = None
                    if "points" in ix and r[ix["points"]].strip():
                        pts = np.array(json.loads(r[ix["points"]]), float)
                    elif all(k in ix for k in ("x", "y")):
                        pts = np.array([[float(r[ix["x"]]), float(r[ix["y"]])]], float)
                    if pts is None or not pts.size: continue
                    c = (float(pts[:, 0].mean()), float(pts[:, 1].mean()))
                    acc.setdefault(r[ix["batch"]].strip(), {}).setdefault(float(r[ix["t_sec"]]), []).append(c)
                except Exception:
                    pass
            for bb, byt in acc.items():
                _MAN_PLATE[bb] = {t: (float(np.mean([p[0] for p in v])), float(np.mean([p[1] for p in v])))
                                  for t, v in byt.items()}
    return dict(_MAN_PLATE.get(b, {}))


def manual_kt_anchors(b):
    """{t_sec: (cx, cy)} — the mean of her kinetochore marks on each frame.

    USER 2026-08-06: "for the batches without outlines, using kinetochore markers can be helpful to help
    you identify the cell and determine the ROI." Exactly the anchor the tracker lacks: a marked
    kinetochore is unambiguously INSIDE the targeted cell, so it settles the identity question that makes
    the blob/template estimator lock onto a brighter neighbour (ablation_8 walking into the bright band by
    24:18). Sparse is fine - the panel loop takes the nearest anchor in time.
    """
    global _MAN_KTA
    if _MAN_KTA is None:
        _MAN_KTA = {}
        rows = list(_csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
        ix = {c: i for i, c in enumerate(rows[0])}
        acc = {}
        for r in rows[1:]:
            if r[ix["label"]].strip() not in KT_ANCHOR_LABELS: continue
            try:
                acc.setdefault(r[ix["batch"]].strip(), {}).setdefault(float(r[ix["t_sec"]]), []).append(
                    (float(r[ix["x"]]), float(r[ix["y"]])))
            except Exception:
                pass
        for bb, byt in acc.items():
            _MAN_KTA[bb] = {t: (float(np.mean([p[0] for p in v])), float(np.mean([p[1] for p in v])))
                            for t, v in byt.items()}
    return dict(_MAN_KTA.get(b, {}))


def follow_centres(b, half):
    """{t_sec: (cx,cy)} of the TARGET cell through the whole monitoring movie.

    Two things make this work where the earlier attempts did not (both verified on
    20260310 ptk2_eyfp_mad1_14, 2026-08-05):
      * SEEDED FROM THE ABLATION COORDINATES. The blob/centroid estimator has no idea which cell is the
        subject and repeatedly locked onto the brighter NEIGHBOURING cells (documented in this file, and
        reproduced again here). The PAS ablation events are ground truth for which cell was targeted.
      * TRACKED ON EVERY MONITORING FRAME, not on the 6 displayed columns. Adjacent frames are seconds
        apart so the cell barely changes between them; the displayed columns are minutes apart, across
        which a rounding/dividing cell changes appearance completely and template matching fails.
    Matching is restricted to a neighbourhood of the previous centre, so it cannot jump to another cell.
    """
    # MANUAL FIRST: if she traced the cell on the monitoring frames, follow HER outlines.
    _man = manual_centres(b)
    if _man:
        print(f"  {b}: following {len(_man)} MANUAL monitoring outlines (tracker not used)", flush=True)
        return _man
    # No outlines -> her KINETOCHORE marks, then her METAPHASE PLATE marks, identify the cell and set the
    # ROI (user 2026-08-06: "ive made metaphase plate marks on the three batches"). A plate mark is a line
    # drawn across the metaphase plate, so its midpoint is inside the target cell — the same anchor a KT
    # mark gives, for cells where she has not marked kinetochores.
    _kta = manual_kt_anchors(b) or manual_plate_anchors(b)
    if _kta:
        print(f"  {b}: following {len(_kta)} MANUAL kinetochore-mark frames (tracker not used)", flush=True)
        return _kta
    tsm = role_ts(b, "monitoring")
    cap = movie(b, "Phase", "Monitoring")
    if tsm is None or cap is None:
        if cap: cap.release()
        return {}
    evs = abl_events(b)          # (x_local, y_local, t_sec) in the CROPPED frame's coordinate space
    seed = (float(np.mean([e[0] for e in evs])), float(np.mean([e[1] for e in evs]))) if evs else None
    T = max(24, int(round(half * 0.8)))          # template half-size
    SR = max(30, int(round(half * 0.6)))         # search radius per step
    out = {}; prev = seed; tmpl = None
    for t in [float(x) for x in tsm]:
        fr = grab_ch(b, "monitoring", "phase_tif_idx", cap, t)
        if fr is None: fr = grab(cap, tsm, t)
        if fr is None: continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
        H, W = g.shape[:2]
        if prev is None: prev = (W / 2.0, H / 2.0)
        cx, cy = prev
        if tmpl is not None:
            x0 = int(max(0, cx - T - SR)); x1 = int(min(W, cx + T + SR))
            y0 = int(max(0, cy - T - SR)); y1 = int(min(H, cy + T + SR))
            sub = g[y0:y1, x0:x1]
            if sub.shape[0] > tmpl.shape[0] and sub.shape[1] > tmpl.shape[1]:
                r = cv2.matchTemplate(sub, tmpl, cv2.TM_CCOEFF_NORMED)
                _, mx, _, loc = cv2.minMaxLoc(r)
                if mx >= 0.30:                    # weak match -> hold position rather than wander
                    ncx = x0 + loc[0] + tmpl.shape[1] / 2.0
                    ncy = y0 + loc[1] + tmpl.shape[0] / 2.0
                    # TRACK_MAX_STEP_UM was declared when this was written but never actually enforced. With
                    # following gated to one hand-checked batch that did not matter; now that it is on for
                    # every ablation batch it does — one bad match would drag the window off the cell for the
                    # whole rest of the row. Adjacent monitoring frames are seconds apart, so a step larger
                    # than this is a mis-detection: hold position instead of jumping.
                    if np.hypot(ncx - cx, ncy - cy) <= TRACK_MAX_STEP_UM / max(ps(b), 1e-9):
                        cx, cy = ncx, ncy
        tx0 = int(max(0, cx - T)); tx1 = int(min(W, cx + T))
        ty0 = int(max(0, cy - T)); ty1 = int(min(H, cy + T))
        if tx1 - tx0 > 8 and ty1 - ty0 > 8:
            tmpl = g[ty0:ty1, tx0:tx1].copy()
        prev = (cx, cy); out[t] = (cx, cy)
    cap.release()
    return out


def tracked_boxes(b, sel, base):
    """Same-size-as-`base` square window per DISPLAYED timepoint, re-centred on the tracked cell."""
    if not base: return [None] * len(sel)
    x0, y0, x1, y1 = base
    w, h = x1 - x0, y1 - y0
    cen = follow_centres(b, w / 2.0)
    if not cen:
        return [base] * len(sel)
    ts = sorted(cen)
    # CLAMPED to the frame, same rule shift_square already follows. A tracked centre near an edge puts part
    # of the window outside the image, where crop_pad edge-replicates — the striped banding this file
    # documents at length from the earlier fixed-shift attempts. The window keeps its size and slides back
    # inside instead, so the panel stays a real image and the footprint stays consistent across columns.
    wh = frame_wh(b)
    out = []
    for t in sel:
        # INTERPOLATE between anchors instead of snapping to the nearest one. Her manual anchors are
        # sparse (Mad1_ablation_8 has 3 plate marks across a 99-2273 s strip), so nearest-neighbour gave
        # the first two panels the same 855 s centre and the last three the same 1538 s centre — the cell
        # then walked out of frame between them, which is exactly the drift she reported. A linear
        # interpolation follows the cell's path between marks and holds the end value beyond them.
        if len(ts) >= 2 and ts[0] <= t <= ts[-1]:
            j = 0
            while j + 1 < len(ts) and ts[j + 1] < t: j += 1
            t0, t1 = ts[j], ts[min(j + 1, len(ts) - 1)]
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            c0, c1 = cen[t0], cen[t1]
            cx = c0[0] + (c1[0] - c0[0]) * f
            cy = c0[1] + (c1[1] - c0[1]) * f
        else:
            tt = min(ts, key=lambda z: abs(z - t))
            cx, cy = cen[tt]
        nx0 = int(round(cx - w / 2.0)); ny0 = int(round(cy - h / 2.0))
        if wh:
            W, H = wh
            nx0 = max(0, min(nx0, W - w))
            ny0 = max(0, min(ny0, H - h))
        out.append((nx0, ny0, nx0 + w, ny0 + h))
    return out


def monitoring_portion(b, crop, ncols=6, aligned=False, sq=None, tmax=None):
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return None
    mcrop = sq if aligned else crop
    # pick DISTINCT timepoints: some batches append a trailing z-stack whose frames all share ONE t_sec
    # (e.g. _1_xy6 has 34 frames all at 4068.2s) -> selecting by raw index repeated the same "67:48" frame
    # and landed on dark out-of-focus z-planes. Dedupe to unique timestamps (first occurrence) first.
    # ALSO require a RAW fluor page (fluor_tif_idx not None): a monitoring frame with no fluor plane would fall
    # back to the baked mp4, which bypasses the strip's shared lo/hi and reads over-bright/blown -> breaks the
    # uniform exposure. Restricting sel to fluor-page timepoints keeps EVERY frame on the one raw mapping.
    fluor_ts = [float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None]
    src = fluor_ts if fluor_ts else list(tsm)   # fall back to all monitoring times only if none carry a fluor page
    uniq = []; seen = set()
    for t in src:
        r = round(float(t), 1)
        if r in seen: continue
        seen.add(r); uniq.append(float(t))
    # 2026-08-03 (feedback item D): "...Eyfpmad1_ablation_10_aligned does not need frames past 13:45 in
    # monitoring" -- trim the CANDIDATE frame list (real per-frame t_sec from frames.json, not an
    # interpolated time) to t_sec <= tmax BEFORE the evenly-spaced ncols selection, so every remaining
    # column is still a genuine annotated frame and the spacing re-fits the shorter window instead of
    # leaving blank trailing columns.
    if tmax is not None:
        trimmed = [t for t in uniq if t <= tmax]
        if trimmed: uniq = trimmed
    sel = [uniq[i] for i in np.linspace(0, len(uniq)-1, min(ncols, len(uniq))).astype(int)]
    # USER 2026-08-05: drop named columns by their burned-in MM:SS caption (a frame showing the wrong cell).
    _drop = MONITOR_DROP_MMSS.get(b)
    if _drop:
        def _mmss(t):
            mm, ss = divmod(int(round(t)), 60)
            return f"{mm}:{ss:02d}"
        kept = [t for t in sel if _mmss(t) not in _drop]
        if kept and len(kept) < len(sel):
            print(f"  {b}: dropped monitoring column(s) "
                  f"{sorted({_mmss(t) for t in sel if _mmss(t) in _drop})} (user 2026-08-05)")
            sel = kept
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", ""))
    at = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    def plab(t):
        if mt is not None and abs(t - mt) <= 30: return "metaphase"
        if at is not None and abs(t - at) <= 30: return "anaphase"
        return None
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": plab(t)} for t in sel]
    # PHASE from the rendered mp4 (unchanged)
    # Frames are grabbed UNCROPPED first so the cell can be located in each one; with tracking off this is
    # the same fixed `mcrop` for every panel as before.
    raw = [None] * len(sel)
    cap = movie(b, "Phase", "Monitoring")
    if cap:
        for ci, t in enumerate(sel):
            fr = grab_ch(b, "monitoring", "phase_tif_idx", cap, t)
            if fr is None: fr = grab(cap, tsm, t)
            if fr is not None: raw[ci] = fr.copy()
        cap.release()
    boxes = (tracked_boxes(b, sel, mcrop) if (mcrop and monitor_follows(b))
             else [mcrop] * len(sel))
    for ci, fr in enumerate(raw):
        if fr is None: continue
        if boxes[ci]: fr = ts_render.crop_pad(fr, boxes[ci]).copy()
        panels[ci]["phase"] = fr
    # FLUOR from the RAW in-focus plane, stretched with ONE shared lo/hi over the WHOLE monitoring strip
    # (uniform exposure -> no blown-green/black frames); fall back to mp4 if a plane is missing.
    capf = movie(b, "Fluor", "Monitoring")
    mon_lo, mon_hi, mplanes = strip_fluor_limits(b, "monitoring", sel)
    for ci, t in enumerate(sel):
        p = mplanes[ci]
        gf = _stretch_green(p, lo=mon_lo, hi=mon_hi) if p is not None else None
        if gf is None and capf is not None:
            fr = grab_ch(b, "monitoring", "fluor_tif_idx", capf, t)
            if fr is None: fr = grab(capf, tsm, t)
            if fr is not None: gf = fr.copy()
        if gf is None: continue
        if boxes[ci]: gf = ts_render.crop_pad(gf, boxes[ci]).copy()   # same per-panel window as the phase tile
        panels[ci]["fluor"] = gf
    if capf: capf.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Mad1"), fluor_only=False)   # 10 um on whole-cell frames (user 2026-08-04)  # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")

# 2026-08-03 (feedback item D): per-batch MONITORING trim, ALIGNED variant only (her wording named only
# "..._ablation_10_aligned"; the base/non-aligned variant is left untouched). 825.0 s = 13:45 MM:SS, the
# same clock the frame captions burn (mm,ss = divmod(int(round(t)),60)) -- so this is the last real
# annotated frame at-or-before the displayed "13:45", not an interpolated cut.
MONITOR_TMAX = {"20260303 Mad1_Ptk_Eyfpmad1_ablation_10": 825.0}

# 2026-08-03 (feedback item D, second half): "Ablation in fluorescence is kind of useless for this one,
# maybe include the phase version of the ablation frames too." The ablation rows are fluor-only EVERYWHERE
# by an earlier standing instruction ("drop phase"), so this is a PER-BATCH override, not a global change,
# and — like MONITOR_TMAX — it applies to the ALIGNED variant only, which is the one she named.
# The phase frames come from the pipeline's Phase movie, whose channel identity is metadata-derived:
# this batch's *_frames.json carries ch_names=['488 (GFP)','Brightfield'], phase_ch=1, fluor_ch=0.
ABL_SHOW_PHASE = {"20260303 Mad1_Ptk_Eyfpmad1_ablation_10"}

# ── ITEMS 13 & 32 (user 2026-08-04) — per-batch timestrip corrections ─────────────────────────────
# ITEM 13  `20260304 Mad1_ablation_10`: "there is just one targeted kinetochore so there should just be one
#          ablation line, but the 'after' frame should be further out time-wise than 7s. Try 30s? Also, the
#          cell isn't centered in the monitoring timestrip. the area of interest should be more to the left.
#          once moved to the left about 20um, then the area of interest can also be tightened (but not for
#          close-up ablation; that one is fine)."
# ITEM 32  `20260310 ptk2_eyfp_mad1_8`: "shift area of interest for whole cell frames to the left by 30um.
#          Also, there are two timestrips for zoom ablations but there's just one ablated kinetochore so just
#          reduce to one strip and make the 'after' frame later than 6 seconds, try 25 seconds or so."
#
# ABL_MAX_EVENTS caps BOTH the red circles drawn on the ablation frame and the number of zoom close-up
# strips, because both are driven off the same `evs` list — that is why one targeted KT was producing two
# lines and two strips.
ABL_MAX_EVENTS = {"20260304 Mad1_ablation_10": 1,
                  "20260310 ptk2_eyfp_mad1_8": 1}

# USER 2026-08-05 (`20260303 Mad1_Ptk_Eyfpmad1_ablation_10`): "for ablation timestrip zoom-ins, just keep
# the second zoom strip shown right now and no need to include the first one (so there will just be one
# zoom ablation strip)."
# Deliberately NOT done with ABL_MAX_EVENTS: that caps `evs` itself, so it would also delete the second red
# ablation circle from the whole-cell frame AND it keeps the FIRST n events — the opposite of the one she
# wants. This selects WHICH zoom strips to emit, 1-based, and leaves the ablation frame untouched.
# 2026-08-06: this is now the DEFAULT for every ablation batch (see ablation_portion) rather than a single
# entry. It was gated to the one batch she happened to name, so ablation_8 and ptk2_eyfp_mad1_14 kept
# emitting two identical zoom strips for another day — the same "apply it to everything of a type" miss as
# MONITOR_FOLLOW. The entry below is left in place as an explicit per-batch record; it now agrees with the
# default, and the dict remains the way to override a batch that needs a different strip.
ABL_ZOOM_KEEP = {"20260303 Mad1_Ptk_Eyfpmad1_ablation_10": (2,)}

# USER 2026-08-05: "theres a flourescence frame in the monitoring strip at time 4:19 thats not the correct
# cell, so can you just remove this frame and the corresponding phase frame from the monitoring timestrip?"
# Keyed by the MM:SS caption the strip actually burns in, so it matches what she read off the figure. The
# drop happens AFTER the evenly-spaced column selection, so the remaining columns keep their original
# timepoints and the strip is simply one column shorter (re-selecting would silently substitute a
# different frame instead of removing the bad one).
MONITOR_DROP_MMSS = {"20260303 Mad1_Ptk_Eyfpmad1_ablation_10": {"4:19"}}
# ABL_AFTER_SEC: the "after" tile was simply the NEXT clean ablation frame, which lands ~6-7 s post-ablation.
# Target a real elapsed time instead — the nearest clean frame at or after (ablation + N seconds).
ABL_AFTER_SEC  = {
                  # USER 2026-08-16: "for 20260310 ptk2_eyfp_mad1_14, ive requested before for the timestrip
                  # ablation frames to be different frames as right now the ones used dont properly show
                  # ablation, yet youve not updated them. update them." Her earlier request was never
                  # written down anywhere on this project, which is exactly why it was dropped — it is
                  # recorded here now, at the table that implements it. The default "after" tile is simply
                  # the next clean frame, ~6-7 s post-ablation, too early for the result to be visible;
                  # mad1_8 was already given 20 s for the same reason. 20 s is a target this movie can
                  # actually meet (see the 2026-08-05 note below: a target past the end of the ablation
                  # phase silently falls back to the LAST frame).
                  "20260310 ptk2_eyfp_mad1_14": 20.0,
                  "20260304 Mad1_ablation_10": 30.0,
                  # 2026-08-05 (user): 25 s -> 20 s. That movie's ablation phase ends at ~+21 s, so a 25 s
                  # target had nothing at or after it and silently fell back to the last frame. 20 s is a
                  # target the data can actually meet.
                  "20260310 ptk2_eyfp_mad1_8": 20.0}
# Crop nudges in MICRONS (converted to px per batch via its own pixel size). Negative x = move LEFT.
# MONITOR_* applies to the monitoring strip ONLY (item 13 explicitly keeps the close-up ablation as-is);
# WHOLECELL_* applies to every whole-cell tile, ablation main + monitoring (item 32's wording).
# ITEM 13, MEASURED. She asked for the monitoring AOI "more to the left ... about 20um", but the geometry
# does not allow it and the direction is opposite to what centres the cell:
#   * the crop derived from the ABLATION frame is (69,207,811,949) — x0=69 in a 1248-px frame, so only
#     69 px (4.3 um) of leftward room exists at all; -20 um pushed the window off-frame and crop_pad
#     edge-replicated it, which is what produced the horizontal banding.
#   * measuring the cell itself: ablation-phase centroid (433,477) matches the crop centre (440,578), but the
#     MONITORING-phase centroid is (575,385) — the cell sits ~135 px RIGHT and ~193 px UP during monitoring.
# To actually centre the cell (her stated goal) the AOI has to move RIGHT ~8 um and UP ~12 um.
# REVERTED 2026-08-04. Two attempts both moved the cell OUT of frame:
#   -20 um left  -> x0 = -198 in a 1248-px frame; crop_pad edge-replicated -> horizontal banding
#   +8.4 um right / -12 um up (from a 99th-percentile centroid) -> window left the cell behind; that
#       centroid was locking onto the brighter NEIGHBOURING cell, not the target.
# The monitoring window is therefore left exactly as it was until the intended direction is confirmed.
# Geometry constraint worth knowing: the crop starts at x0=69 in a 1248-px frame, so at most 4.3 um of
# leftward movement is physically available — a 20 um left shift cannot be honoured.
#
# 2026-08-04 (second pass, her item 7 "none of the mad1 timestrips appear updated"): the reason the two
# nudged strips look unchanged is that BOTH requested shifts were larger than the room that exists, so
# shift_square clamped them to ~4 um and ~22 um of the 20 um and 30 um asked - a change too small to see.
# Shifting a fixed window was the wrong tool: the cell MOVES between the ablation and monitoring phases,
# so the window has to FOLLOW it. MONITOR_TRACK does that by locating the ablation-phase crop's own phase
# image inside each monitoring frame by normalised cross-correlation. Matching on appearance is what makes
# this work where the earlier attempt failed - a 99th-percentile centroid locked onto the brighter
# NEIGHBOURING cell, whereas template matching keys on the target cell's actual texture.
# MEASURED AND LOOKED AT, 2026-08-04. Both phases share ONE field of view and the crop box sits at the same
# coordinates in each, so nothing is mis-registered. Two findings, from the frames themselves:
#   * template matching scores only 0.05-0.06 here because the cell's APPEARANCE changes completely between
#     phases (spread, condensed chromosomes during ablation -> a rounded metaphase cell during monitoring).
#     There is no texture to match, so the guard correctly refuses to move the window. Not a code failure.
#   * MEASURED FROM THE RAW ACQUISITION, 2026-08-05 (5 MB drive mounted). Final answer, after I got this
#     wrong in both directions:
#       - The raw is /Volumes/5 MB/20260304/Mad1_ablation_10/Mad1_ablation_10_MMStack_Pos0.ome.tif,
#         2048x1152 px. The pipeline ROI is x=415,y=53,w=1248,h=1056.
#       - I briefly concluded from those numbers that 415 px = 25.7 um of unused image sat to the left and
#         that only a missing raw file blocked the shift. THAT WAS WRONG: the 2048-wide sensor frame is
#         mostly DARK BORDER. Measuring the illuminated field by column intensity, real signal spans
#         x=388..1726 (1339 px = 83.0 um).
#       - So the ROI at x=415 already starts 27 px (1.7 um) from the left edge of the ILLUMINATED FIELD,
#         with 64 px (4.0 um) spare on the right. A 20 um left shift does not exist to be had.
#     THE CELL GENUINELY EXTENDS BEYOND THE MICROSCOPE'S FIELD AT THIS STAGE POSITION. No crop setting and
#     no re-processing recovers it; it would need re-acquisition at a different stage position.
#     The most that is available: widen the crop from 1248 px (77.4 um) to the full 1339 px (83.0 um) of
#     illuminated field - about 5.6 um more total width, not a 20 um pan.
#     ALSO NOTED while reading the raw: tifffile reports the MMStack is missing files - 62 of 100
#     timepoints present. Flag for the raw-restore/truncation list; it does not affect this conclusion.
MONITOR_TRACK      = set()
# ITEM 13c. She asked for ~20 um left on the monitoring AOI; measured on the strip's OWN crop
# (render x0=69) only 4.3 um exists, and she accepted that on 2026-08-05. The request is left at -20 um so
# the intent is on record; shift_square clamps it to the 4.3 um the frame actually allows and says so in
# the run log. This was briefly emptied while the template-tracking approach was being tried, which meant
# NO shift was applied at all - restored 2026-08-05.
MONITOR_SHIFT_UM   = {"20260304 Mad1_ablation_10": (-20.0, 0.0),
                      # USER 2026-08-11: "move the roi for the monitoring frames up about 15um"
                      # 2026-08-11 (second pass): "up by 10um" again -> -15 becomes -25
                      "20260303 Mad1_Ptk_Eyfpmad1_ablation_10": (0.0, -25.0)}
MONITOR_TIGHTEN    = {}   # tightening deferred until the centring direction is settled
# RESTORED 2026-08-05 after she caught my error. I had emptied this on a measurement of the WRONG BOX.
# There are THREE coordinate spaces here and they must not be conflated:
#   raw sensor (2048x1152, illuminated field ~83 um) -> pipeline render (1248x1056, cut at raw x=415)
#   -> TIMESTRIP CROP (a tight square inside the render, and THIS is what the figure shows).
# I measured the pipeline ROI against the illuminated field and reported ~2 um of pan. That is the room
# for the RENDER, not for the strip. Measured on the strip's own crop:
#   20260310 ptk2_eyfp_mad1_8 : square crop starts at render x=362 -> 362 px = 22.4 um of pan available
#                               (24.5 um if the render is also re-cut from raw). She asked for 30 um, so
#                               the clamp delivers 22.4 um - a large, clearly visible move, NOT a no-op.
#   20260304 Mad1_ablation_10 : square crop starts at render x=69 -> only 4.3 um (6.0 um from raw), so
#                               its 20 um request really is out of reach. Different batch, different answer.
WHOLECELL_SHIFT_UM = {"20260310 ptk2_eyfp_mad1_8": (-30.0, 0.0)}
# ABLATION-ONLY whole-cell shift, microns (-dx = left, -dy = up). WHOLECELL_SHIFT_UM moves the
# ablation AND monitoring tiles together and MONITOR_SHIFT_UM moves only monitoring, so until now
# there was no way to move just the ablation whole-cell frames.
# USER 2026-08-10: "for the ablation whole-cell frames, move the roi to the left about 10um and up
# about 5um" -- for 20260303 Mad1_Ptk_Eyfpmad1_ablation_10.
# USER 2026-08-11: "for the ablaiton whole cell frames move the roi down by about 15um" -- relative to the
# render she is looking at, which carried -5, so it becomes +10 (down).
ABLATION_SHIFT_UM = {"20260303 Mad1_Ptk_Eyfpmad1_ablation_10": (-10.0, 0.0)}   # 2026-08-11: up 10 from +10


def track_square_into_monitoring(b, sq):
    """Return `sq` moved to wherever the ablation-phase crop's contents ended up during MONITORING.

    Cuts the ablation-phase phase image inside `sq` as a template, then finds its best normalised
    cross-correlation match in a mid-monitoring phase frame and re-centres the box there. Same size box,
    clamped to the frame. Returns `sq` unchanged if any input is missing or the match is weak, so a failed
    track can never silently move the window somewhere arbitrary."""
    if sq is None: return sq
    try:
        ta = role_ts(b, "ablation"); tm = role_ts(b, "monitoring")
        capA = movie(b, "Phase", "ablation"); capM = movie(b, "Phase", "monitoring")
        if ta is None or tm is None or capA is None or capM is None:
            if capA: capA.release()
            if capM: capM.release()
            return sq
        frA = grab(capA, ta, float(ta[len(ta) // 2]))
        frM = grab(capM, tm, float(tm[len(tm) // 2]))
        capA.release(); capM.release()
        if frA is None or frM is None: return sq
        x0, y0, x1, y1 = [int(v) for v in sq]

        def _gray(fr):
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
            if g.dtype != np.uint8:
                g = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            return cv2.createCLAHE(2.0, (8, 8)).apply(g)   # equalise: the two phases differ in exposure

        # Phase carries cell texture, fluor carries cell shape - try both, and try an inset template
        # (the cell centre is more distinctive than the box edges, which include neighbours).
        cands = [("phase", frA, frM)]
        capAf = movie(b, "Fluor", "ablation"); capMf = movie(b, "Fluor", "monitoring")
        if capAf is not None and capMf is not None:
            fA = grab(capAf, ta, float(ta[len(ta) // 2])); fM = grab(capMf, tm, float(tm[len(tm) // 2]))
            if fA is not None and fM is not None: cands.append(("fluor", fA, fM))
        if capAf: capAf.release()
        if capMf: capMf.release()

        best = (0.0, None, None)   # (corr, top-left, template size)
        for chan, srcA, srcM in cands:
            gA, gM = _gray(srcA), _gray(srcM)
            for inset in (0.0, 0.20):
                w, h = x1 - x0, y1 - y0
                ix0 = max(0, int(x0 + w * inset)); iy0 = max(0, int(y0 + h * inset))
                ix1 = min(gA.shape[1], int(x1 - w * inset)); iy1 = min(gA.shape[0], int(y1 - h * inset))
                tpl = gA[iy0:iy1, ix0:ix1]
                if tpl.size == 0 or tpl.shape[0] >= gM.shape[0] or tpl.shape[1] >= gM.shape[1]:
                    continue
                res = cv2.matchTemplate(gM, tpl, cv2.TM_CCOEFF_NORMED)
                _mn, mx, _ml, mloc = cv2.minMaxLoc(res)
                print(f"    {b}: track candidate {chan} inset={inset:.2f} corr={mx:.2f}")
                if mx > best[0]:
                    # convert the inset match back to the FULL box's top-left
                    best = (mx, (mloc[0] - (ix0 - x0), mloc[1] - (iy0 - y0)), None)
        mx, tl, _ = best
        if tl is None or mx < 0.30:
            print(f"    {b}: monitoring track REJECTED (best correlation {mx:.2f} < 0.30) — window left as-is")
            return sq
        nx0, ny0 = float(tl[0]), float(tl[1])
        nx1, ny1 = nx0 + (x1 - x0), ny0 + (y1 - y0)
        _psb = ps(b) or 0.062
        print(f"    {b}: monitoring track corr={mx:.2f}  moved "
              f"{((nx0 + nx1) / 2 - (x0 + x1) / 2) * _psb:+.1f} um in x, "
              f"{((ny0 + ny1) / 2 - (y0 + y1) / 2) * _psb:+.1f} um in y")
        return (int(round(nx0)), int(round(ny0)), int(round(nx1)), int(round(ny1)))
    except Exception as e:
        print(f"    {b}: monitoring track failed ({type(e).__name__}: {e}) — window left as-is")
        return sq

def frame_wh(b):
    """(width, height) of this batch's cropped frames, from the master Crop ROI."""
    v = (mr.get(b, {}).get("Crop ROI (x,y,w,h)", "") or "").strip()
    try:
        p = [int(float(x)) for x in v.split(",")]
        if len(p) >= 4 and p[2] > 0 and p[3] > 0: return p[2], p[3]
    except Exception: pass
    return None


def shift_square(sq, b, dxy_um, tighten=1.0):
    """Translate (and optionally tighten) a square crop box by a distance in MICRONS.

    CLAMPED to the frame (2026-08-04). Both requested shifts exceeded the room available and pushed the
    window off the image, where crop_pad edge-replicates and produces horizontal banding:
      item 13  monitoring, -20 um asked: crop starts at x0=69  -> only  4.3 um available
      item 32  whole cell, -30 um asked: crop starts at x0=362 -> only 22.4 um available
    The shift is therefore applied up to the frame edge and the shortfall is reported, rather than
    silently rendering a striped, edge-padded strip."""
    if sq is None: return None
    x0, y0, x1, y1 = sq
    _ps = ps(b) or 0.062
    dx = (dxy_um[0] / _ps); dy = (dxy_um[1] / _ps)
    cx = (x0 + x1) / 2.0 + dx; cy = (y0 + y1) / 2.0 + dy
    half = ((x1 - x0) / 2.0) * float(tighten)
    nx0, ny0 = cx - half, cy - half
    nx1, ny1 = cx + half, cy + half
    wh = frame_wh(b)
    if wh:
        W, H = wh
        if nx0 < 0:   nx1 -= nx0; nx0 = 0.0
        if ny0 < 0:   ny1 -= ny0; ny0 = 0.0
        if nx1 > W:   nx0 -= (nx1 - W); nx1 = float(W)
        if ny1 > H:   ny0 -= (ny1 - H); ny1 = float(H)
        nx0 = max(0.0, nx0); ny0 = max(0.0, ny0)
        got_um = ((nx0 + nx1) / 2.0 - (x0 + x1) / 2.0) * _ps
        if abs(got_um - dxy_um[0]) > 0.5:
            print(f"    {b}: requested {dxy_um[0]:+.1f} um in x, frame allows {got_um:+.1f} um "
                  f"(crop clamped to stay inside {W}x{H}; no edge padding)")
    return (int(round(nx0)), int(round(ny0)), int(round(nx1)), int(round(ny1)))

# ================= build the per-batch timestrips =================
# fast-iteration filter: MAD1_ONLY=substr[,substr] renders only matching batches (and skips the z-stack grid).
_ONLY = os.environ.get("MAD1_ONLY")
if _ONLY:
    _keys = [k for k in _ONLY.split(",") if k]
    TIMESTRIP_BATCHES = [t for t in TIMESTRIP_BATCHES if any(k in t[0] for k in _keys)]
    ZSTACK_BATCHES = []
made = []
for b, note in TIMESTRIP_BATCHES:
    d = render_dir(b)
    if not d: print(f"  skip {b}: no render dir"); continue
    crop = fluor_tight_crop(b) or fluor_crop(b)                 # TIGHT square crop (cell fills the frame; no distortion)
    portions = ablation_portion(b, crop)                       # empty for non-ablation batches
    mon = monitoring_portion(b, crop)
    if mon: portions.append(("monitoring", mon[0], mon[1]))
    if not portions: print(f"  skip {b}: no portions"); continue
    stem = f"G5_mad1_timestrip_{b.replace(' ', '_')}"
    ok = ts_render.emit(portions, f"{OUT}/{stem}", title=f"Mad1 timelapse — {clean_title(b)}"+(" [EXCLUDED]" if lib.timestrip_excluded(b) else ""))
    made.append(stem + ".png")
    lib.record_plot(stem, ["batch"], [[b]],
        {"type": "Mad1 example timestrip", "has_ablation": bool(role_ts(b, "ablation") is not None),
         "crop": [int(v) for v in crop] if crop else None, "n_portions": len(portions), "note": note},
        SCRIPT, f"Mad1 timestrip example ({b})")
    print(f"mad1 timestrip {b}: {len(portions)} portions {'ok' if ok else 'FAIL'}")
    # ALIGNED-CROP variant — ONLY for ABLATION batches (fixed-physical 78µm main window + consistent zoom, so
    # magnification matches every other aligned ablation timestrip). Centroid from the fluor crop (no outlines).
    if role_ts(b, "ablation") is not None:
        sq = std_crop(b)
        if sq is None:
            print(f"  {b}_aligned: SKIP (no fluor crop)")
        else:
            # ITEMS 13/32: crop nudges. WHOLECELL_SHIFT_UM moves every whole-cell tile (ablation main +
            # monitoring); MONITOR_SHIFT_UM/MONITOR_TIGHTEN move and tighten the MONITORING strip only, so
            # the close-up ablation window is left exactly as it was (item 13 asked for that explicitly).
            _sq_all = shift_square(sq, b, WHOLECELL_SHIFT_UM[b]) if b in WHOLECELL_SHIFT_UM else sq
            _sq_mon = _sq_all
            if b in MONITOR_TRACK:
                _sq_mon = track_square_into_monitoring(b, _sq_all)     # follow the cell (item 7, 2026-08-04)
            elif b in MONITOR_SHIFT_UM or b in MONITOR_TIGHTEN:
                _sq_mon = shift_square(_sq_all, b, MONITOR_SHIFT_UM.get(b, (0.0, 0.0)),
                                       MONITOR_TIGHTEN.get(b, 1.0))
            if _sq_all is not sq or _sq_mon is not _sq_all:
                print(f"    {b}: crop sq={sq} -> wholecell={_sq_all} monitoring={_sq_mon}")
            _sq_abl = shift_square(_sq_all, b, ABLATION_SHIFT_UM[b]) if b in ABLATION_SHIFT_UM else _sq_all
            if _sq_abl is not _sq_all:
                print(f"    {b}: ablation-only crop {_sq_all} -> {_sq_abl}")
            pA = ablation_portion(b, crop, aligned=True, sq=_sq_abl, show_phase=(b in ABL_SHOW_PHASE))
            mA = monitoring_portion(b, crop, aligned=True, sq=_sq_mon, tmax=MONITOR_TMAX.get(b))
            if mA: pA.append(("monitoring", mA[0], mA[1]))
            if pA:
                okA = ts_render.emit(pA, f"{OUT}/{stem}_aligned", title=f"Mad1 timelapse (aligned) — {clean_title(b)}"+(" [EXCLUDED]" if lib.timestrip_excluded(b) else ""))
                made.append(stem + "_aligned.png")
                print(f"  {b}_aligned: {len(pA)} portions {'ok' if okA else 'FAIL'}")
                # 2026-08-04: the aligned variant is a real placed figure but was never registered, so its
                # PLOT_SETTINGS entry came from the retroactive registration script and carried
                # `mtimes_at_registration` — which by design cannot prove the figure is in sync with its
                # sources. Register it like the parent so it becomes staleness-checkable.
                if okA:
                    lib.record_plot(stem + "_aligned", ["batch"], [[b]],
                        {"type": "Mad1 example timestrip (aligned square crop)",
                         "variant_of": stem,
                         "has_ablation": bool(role_ts(b, "ablation") is not None),
                         "crop": [int(v) for v in _sq_all] if _sq_all else None,
                         "n_portions": len(pA), "note": note,
                         "geometry": "fixed-physical 78um main window + constant zoom, one square footprint"},
                        SCRIPT, f"Mad1 timestrip example ({b}) — aligned square crop")
            else:
                print(f"  {b}_aligned: SKIP (no portions)")

# ================= Mad1 z-stack MIP grid (one slide) =================
def read_stack(path):
    """The *_Cropped.tif are written as MANY single-page TIFF SERIES, so tifffile.imread() returns ONLY
    page 0 (one z-plane) -> the old MIP was a single out-of-focus plane = 'green noise'. Stack ALL pages."""
    with tifffile.TiffFile(path) as tf:
        return np.stack([pg.asarray() for pg in tf.pages])

def zstack_mip(b):
    """TRUE max-intensity projection of the Mad1 (488) z-stack; background-subtracted so the in-focus cell
    pops instead of the out-of-focus haze, strongly stretched, green-colourised, cropped to the cell."""
    d = render_dir(b)
    if not d: return None
    fpath = f"{d}/{b}_Fluor_Cropped.tif"
    if os.path.isfile(fpath):
        vol = read_stack(fpath).astype(np.float32)                 # (n_z, H, W)
        if vol.ndim == 2: vol = vol[None]
    else:
        cap = movie(b, "Fluor", "Monitoring")
        if not cap: return None
        n = int(cap.get(7)); acc = None
        for k in range(n):
            cap.set(cv2.CAP_PROP_POS_FRAMES, k); ok, fr = cap.read()
            if not ok: continue
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
            acc = g if acc is None else np.maximum(acc, g)
        cap.release()
        if acc is None: return None
        vol = acc[None]
    if vol.size == 0: return None
    if vol.shape[0] > 1:
        med = np.median(vol, axis=0)                                # static background / out-of-focus haze
        mip = np.clip(vol - med, 0, None).max(axis=0)               # in-focus Mad1 signal pops
    else:
        mip = vol[0]
    mip = gaussian_filter(mip, 1.0)                                 # denoise speckle
    H, W = mip.shape
    # --- CONSISTENT SQUARE crop centred on the cell (07-08): a FIXED-size square window (same physical
    # footprint for every batch) centred on the intensity centroid of the MIP -> every tile is the same
    # square, none blows out wide / collapses / lands black. (The old variable percentile-bbox crop gave a
    # very wide FullVolume tile, a tiny/off Hec1 tile, and let a dim batch crop to near-black.) ---
    sm = gaussian_filter(mip, 6.0)
    cy0, cx0 = H // 2, W // 2; ry, rx = int(H * 0.42), int(W * 0.42)
    ys, xs = np.mgrid[cy0-ry:cy0+ry, cx0-rx:cx0+rx].astype(np.float32)
    win = sm[cy0-ry:cy0+ry, cx0-rx:cx0+rx]
    w = np.clip(win - np.percentile(win, 80), 0, None)             # top ~20% bright signal = the cell
    if w.sum() > 0:
        cx = float((xs * w).sum() / w.sum()); cy = float((ys * w).sum() / w.sum())
    else:
        cx, cy = float(cx0), float(cy0)
    side = int(min(H, W) * 0.5); x0 = int(round(cx - side/2)); y0 = int(round(cy - side/2))
    pl, pt = max(0, -x0), max(0, -y0); pr, pb = max(0, x0+side-W), max(0, y0+side-H)
    xs0, ys0 = max(0, x0), max(0, y0); xs1, ys1 = min(W, x0+side), min(H, y0+side)
    crop = mip[ys0:ys1, xs0:xs1]
    if pl or pt or pr or pb: crop = cv2.copyMakeBorder(crop, pt, pb, pl, pr, cv2.BORDER_CONSTANT, value=0)
    # ROBUST stretch on the CROP itself: lo=66th pctile pins the diffuse background/haze to black (no green
    # noise); hi=99.6th keeps the brightest Mad1 puncta just under saturation; neutral gamma -> structure,
    # not a blown-out flat green. Crop-local percentiles keep the exposure consistent across batches.
    lo, hi = np.percentile(crop, 66), np.percentile(crop, 99.6)
    g8 = np.clip((crop - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8   # BGR green, square
    return green

PANEL_H = 460
zpanels = []
for b, note in ZSTACK_BATCHES:
    img = zstack_mip(b)
    if img is None: print(f"  skip zstack {b}: no MIP"); continue
    s = PANEL_H / img.shape[0]; img = cv2.resize(img, (int(img.shape[1]*s), PANEL_H))
    cap = np.full((30, img.shape[1], 3), 30, np.uint8)
    cv2.putText(cap, b, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 235, 235), 1, cv2.LINE_AA)
    zpanels.append(np.vstack([cap, img]))
zgrid_png = None
if zpanels:
    Wt = max(p.shape[1] for p in zpanels)
    zpanels = [np.pad(p, ((0, 0), (0, Wt-p.shape[1]), (0, 0))) for p in zpanels]
    ims = []
    for p in zpanels: ims += [p, np.full((p.shape[0], 10, 3), 18, np.uint8)]
    grid = np.hstack(ims[:-1])
    title = np.full((34, grid.shape[1], 3), 18, np.uint8)
    cv2.putText(title, "Mad1 z-stack examples - max-intensity projections (488 / Mad1)",
                (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 1, cv2.LINE_AA)
    grid = np.vstack([title, grid])
    s = min(4500/grid.shape[1], 2600/grid.shape[0], 1.0)
    if s < 1.0: grid = cv2.resize(grid, (int(grid.shape[1]*s), int(grid.shape[0]*s)), interpolation=cv2.INTER_AREA)
    zgrid_png = f"{OUT}/G5_mad1_zstack_mips.png"; cv2.imwrite(zgrid_png, grid)
    lib.record_plot("G5_mad1_zstack_mips", ["batch"], [[b] for b, _ in ZSTACK_BATCHES],
        {"type": "Mad1 z-stack MIP grid", "batches": [b for b, _ in ZSTACK_BATCHES]},
        SCRIPT, "Mad1 z-stack example MIPs (one slide)")
    print(f"wrote {zgrid_png}  ({len(zpanels)} panels)")

print("TIMESTRIP PNGs:", made)
print("ZSTACK PNG:", zgrid_png)

