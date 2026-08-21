"""Group 3 / drug-control — mitotic-SLIPPAGE exhaustion-control TIMESTRIPS (monitoring only).

These are eYFP-Cdc20 PtK cells treated with colcemid / nocodazole (the mitotic-slippage / SAC-exhaustion
controls). They are NON-ablation cells, so each is a MONITORING-ONLY timestrip: phase (top) over eYFP fluor
(bottom), a handful of timepoints showing the cell through the prolonged/arrested mitosis and its eventual
fate (here: eventual anaphase / division after a long arrest).

Built on the SAME shared editable ts_render module as the ablation / Mad1 timestrips (one consistent font,
editable-SVG text, timestamps, channel labels, scale bar) — this is the monitoring-only pattern lifted from
group5_mad1_examples.py so the standards match ALL other timestrips:
 * NO manual outline -> crop is ESTIMATED from the eYFP fluorescence of the CENTRED cell (fluor_crop), and the
   `_aligned` variant uses the shared 78µm physical window (ts_render.STD_MAIN_UM / std_square_crop) so
   magnification + scale-bar length match every other aligned timestrip.
 * FLUOR read from the RAW per-frame-stretched in-focus plane (_stretch_green / raw_fluor_monitor) so LATE
   frames are not crushed to black.
 * Timepoint selection is FOCUSED on the arrest->fate story: evenly spaced from the first monitoring frame to
   ~15 min past the recorded anaphase onset (clamped to the movie) — NOT over the full multi-hour post-division
   tail — so the columns read start / prolonged-arrest / mid-arrest / exit(anaphase-division).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import glob, os, json, numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter
import lib, ts_render

OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except: return 0.062

CHAN = ("Phase", "eYFP-Cdc20")
POST_ANA_S = 900.0   # extend the story window ~15 min past anaphase onset to show the division outcome

# --- curated, comment-flagged slippage / exhaustion-control examples (monitoring only) ---
#   Notes verified in the live master; both are the best-flagged cell for their drug and both COMPLETE DIVISION
#   after a prolonged arrest (an anaphase onset is recorded for each).
TIMESTRIP_BATCHES = [
    ("20251002 colcemid_2_xy9",
     "Colcemid — prolonged mitotic arrest, then eventual anaphase / division (slippage-then-division control)"),
    ("20251021 no_ablations_nocodazole_1_xy11",
     "Nocodazole — in metaphase at imaging start; prolonged metaphase arrest, then eventual division"),
]

# ---- render-dir index (same as the other timestrip scripts) ----
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

def _stretch_green(plane, lo_p=30, hi_p=99.7, gamma=0.9, lo=None, hi=None):
    """eYFP (488) -> green BGR. UNIFORM-EXPOSURE: pass explicit lo/hi (pooled ONCE over the whole monitoring
    strip) so every frame shares ONE fixed mapping (no per-frame auto-normalisation). lo/hi=None -> per-frame."""
    a = plane.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)
    g8 = (n * 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8    # BGR green
    return green

def raw_fluor_plane(b, role, t, tol=0.15):
    """Selected in-focus RAW eYFP (488) fluor plane (float32), NO stretch. When several frames share ONE t_sec
    (a trailing z-stack) pick the IN-FOCUS = max-variance page, not the first (often dark)."""
    d = render_dir(b)
    fp = f"{d}/{b}_Fluor_Cropped.tif" if d else None
    if not fp or not os.path.isfile(fp): return None
    same = [f for f in role_frames(b, role) if abs(float(f["t_sec"]) - t) <= tol]
    if not same: return None
    idxs = [int(f["fluor_tif_idx"]) for f in same if f.get("fluor_tif_idx") is not None]
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

def strip_fluor_limits(b, role, times, tol=0.15, lo_p=30, hi_p=99.7):
    """ONE (lo,hi) mapping for a whole strip-type: percentiles pooled over ALL its raw planes -> applied
    identically to every frame. Returns (lo, hi, planes) with planes aligned to `times` (cached, no re-read)."""
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes

# ---- crop estimated from FLUORESCENCE of the centred cell (raw Cropped tif) ----
def fluor_crop(b, as_pts=False):
    """as_pts=True -> return (bbox_corner_pts, W, H) of the ESTIMATED cell blob (NO added margin) for
    ts_render.tight_square (TIGHT, exactly-square, undistorted crop that fills the frame)."""
    fj = fjson(b); d = render_dir(b)
    if not fj or not d: return None
    fr0 = role_frames(b, "monitoring")
    if not fr0: return None
    fr0 = fr0[0]
    fpath = f"{d}/{b}_Fluor_Cropped.tif"
    plane = None
    if os.path.isfile(fpath):
        stk = tifffile.imread(fpath); idx = int(fr0["fluor_tif_idx"])
        plane = (stk[min(idx, stk.shape[0]-1)] if stk.ndim == 3 else np.squeeze(stk)).astype(np.float32)
    else:
        cap = movie(b, "Fluor", "Monitoring")
        if not cap: return None
        ts = role_ts(b, "monitoring")
        f = grab(cap, ts, float(ts[0])); cap.release()
        if f is None: return None
        plane = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
    H, W = plane.shape
    if as_pts:   # BRIGHTFIELD-based cell detection (fluor too diffuse on these cells): texture of the refractile
        for R, r in (("Monitoring", "monitoring"), ("Ablation", "ablation")):   # mitotic cell delineates it best
            cap = movie(b, "Phase", R)
            if not cap: continue
            mts = role_ts(b, r)
            bf = grab(cap, mts, float(mts[0])) if mts is not None and len(mts) else None; cap.release()
            if bf is not None: return (ts_render.brightfield_cell_bbox_pts(bf), W, H)
        return (ts_render.fluor_cell_bbox_pts(plane), W, H)   # fallback: fluor if no readable brightfield
    lo, hi = np.percentile(plane, 40), np.percentile(plane, 99.7)
    g8 = np.clip((plane - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    sm = gaussian_filter(g8.astype(np.float32), 3.0)
    cy, cx = H // 2, W // 2; ry, rx = int(H * 0.32), int(W * 0.32)   # central window (cell of interest centred)
    mask = np.zeros_like(sm, bool); mask[cy-ry:cy+ry, cx-rx:cx+rx] = True
    thr = (sm > np.percentile(sm[mask], 96)) & mask
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

def fluor_tight_crop(b, margin=1.12):
    """UNIFORM-scale-before-crop square window from the FLUOR-estimated cell blob (ts_render.tight_square,
    margin=1.12 -> cell fills ~89% of the frame, small breathing room, no clipped edges); forced square so the
    later resize is uniform (no distortion). Reused for ALL frames."""
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)

def std_crop(b):
    """TIGHT square crop (ts_render.tight_square) sized to THIS cell's FLUOR-estimated bbox -> the cell fills the
    frame (replaces the old 78µm window that left the cell filling only ~35%). Reused for ALL frames."""
    return fluor_tight_crop(b)

# ---- monitoring portion: story window (start -> ~15 min past anaphase), fluor per-frame-stretched ----

# ---- MONITORING WINDOW THAT FOLLOWS THE CELL (USER 2026-08-05) ----------------------------------
# "can you sense where the cell is in each frame (using phase or fluorescence or both) and then make sure
# that the ROI for the timestrip is centered on it? ... once you center on the cell, zoom in a bit, maybe
# 5um on each side or so."
# std_crop() estimates ONE window from the FIRST frame and reuses it for every panel, so a cell that
# translates over a multi-hour arrest walks off-centre. Here the window keeps a FIXED SIZE (so the uniform
# resize and the scale bar stay valid) and is re-centred per panel, then tightened by TIGHTEN_UM per side.
# No ablation exists in these batches, so the track is seeded from the initial crop centre (correct while
# the cell is still centred at t0) and then followed by template matching on EVERY monitoring frame —
# adjacent frames are seconds apart, so appearance barely changes between them.
MONITOR_FOLLOW = {"20251021 no_ablations_nocodazole_1_xy11"}
TIGHTEN_UM     = 5.0     # per side, after centring

def follow_centres(b, seed, half):
    """Where is the cell in each monitoring frame?

    USER 2026-08-05: "you made it much worse than what it was before ... don't just simply revert to the
    original. try again so tis actually what i want."

    The version she rejected tracked by TEMPLATE MATCHING on phase contrast, seeded from the first frame's
    crop centre. Two failure modes, both of which compound:
      * the template was re-cut at whatever position won each frame, so one bad match permanently moved
        the tracker onto a neighbour cell or a piece of debris, and it never recovered;
      * the accept threshold (0.30 correlation) is low enough that a bad match still counted as a hit.
    Over a multi-hour nocodazole arrest, in phase contrast where every rounded cell looks alike, that is
    close to a random walk.

    This version does NOT track. It DETECTS, independently in every frame, from the FLUOR channel: the
    arrested cell is full of eYFP-Cdc20 and reads as a single bright blob against a dark field, which is a
    far stronger signal than its phase-contrast outline. Per frame:
      1. smooth, threshold at a high percentile of that frame's own intensity,
      2. take connected components and keep cell-sized ones,
      3. choose the one nearest the previous accepted centre (continuity, but only as a tie-break —
         detection does not depend on it),
      4. if nothing plausible is found, hold the previous centre rather than jump.
    Because each frame is measured from scratch, a bad frame costs one frame instead of the rest of the run.
    Finally the centres are median-smoothed over +/-2 frames so a single noisy detection cannot visibly
    jerk the ROI between adjacent panels.
    """
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return {}
    pxs = ps(b) or 0.062
    # a mitotic PtK cell is roughly 20-45 um across; convert to an area window in px^2
    amin = (np.pi * (8.0 / pxs) ** 2) * 0.25
    amax = (np.pi * (30.0 / pxs) ** 2) * 2.0
    raw = {}; prev = seed
    for t in [float(x) for x in tsm]:
        pl = raw_fluor_plane(b, "monitoring", t)
        if pl is None:
            raw[t] = prev; continue
        g = cv2.GaussianBlur(pl.astype(np.float32), (0, 0), 3.0)
        thr = float(np.percentile(g, 99.0))
        lo = float(np.percentile(g, 50.0))
        # CONTRAST GATE. This is a Cdc20 degradation experiment: by the late frames the reporter is largely
        # gone, so the "cell" is barely brighter than background and the blob detector starts locking onto
        # noise — which is what made the final panel drift. Score the frame's own contrast against its own
        # background spread; below ~3 sigma there is no cell to find, so record NO detection (None) rather
        # than a confident wrong one. Gaps are interpolated from the frames either side afterwards.
        _bgsd = float(np.std(g[g <= np.percentile(g, 80.0)])) or 1e-6
        if not np.isfinite(thr) or thr <= lo or (thr - lo) / _bgsd < 3.0:
            raw[t] = None; continue
        # halfway between the field median and the bright tail: catches the whole cell, not just the
        # brightest kinetochore cluster inside it
        m = (g >= (lo + thr) / 2.0).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        n, lab, st_, cen = cv2.connectedComponentsWithStats(m, 8)
        best = None; bestd = None
        for i in range(1, n):
            area = st_[i, cv2.CC_STAT_AREA]
            if not (amin <= area <= amax): continue
            cx, cy = float(cen[i][0]), float(cen[i][1])
            d = 0.0 if prev is None else ((cx - prev[0]) ** 2 + (cy - prev[1]) ** 2) ** 0.5
            if bestd is None or d < bestd: bestd, best = d, (cx, cy)
        raw[t] = best                      # may be None: no plausible cell-sized component this frame
        if best is not None: prev = best
    ts_sorted = sorted(raw)
    good = [t for t in ts_sorted if raw[t] is not None]
    if not good:
        return {t: seed for t in ts_sorted}
    # INTERPOLATE across the ungated frames, so a run of late low-signal frames follows the cell's actual
    # path between its last and next confident positions instead of freezing or wandering.
    gx = np.array(good, float)
    fx = np.array([raw[t][0] for t in good], float)
    fy = np.array([raw[t][1] for t in good], float)
    filled = {t: (float(np.interp(t, gx, fx)), float(np.interp(t, gx, fy))) for t in ts_sorted}
    # temporal median smoothing (+/-2 frames) so one noisy detection cannot jerk the ROI between panels
    out = {}
    for i, t in enumerate(ts_sorted):
        win = [filled[ts_sorted[j]] for j in range(max(0, i - 2), min(len(ts_sorted), i + 3))]
        out[t] = (float(np.median([w[0] for w in win])), float(np.median([w[1] for w in win])))
    print(f"    follow_centres({b[-28:]}): cell detected in {len(good)}/{len(ts_sorted)} monitoring frames; "
          f"{len(ts_sorted)-len(good)} low-signal frame(s) interpolated (Cdc20 degrades late in this movie)")
    return out


def tracked_boxes(b, sel, base):
    if not base: return [None]*len(sel)
    x0,y0,x1,y1 = base
    w = x1-x0; h = y1-y0
    tighten = int(round(TIGHTEN_UM / (ps(b) or 0.062)))     # px to remove PER SIDE
    nw = max(40, w - 2*tighten); nh = max(40, h - 2*tighten)
    cen = follow_centres(b, ((x0+x1)/2.0, (y0+y1)/2.0), w/2.0)
    if not cen: return [base]*len(sel)
    ts = sorted(cen); out = []
    for t in sel:
        cx, cy = cen[min(ts, key=lambda z: abs(z-t))]
        nx0 = int(round(cx - nw/2.0)); ny0 = int(round(cy - nh/2.0))
        out.append((nx0, ny0, nx0+nw, ny0+nh))
    return out


def monitoring_portion(b, crop, ncols=6, aligned=False, sq=None):
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return None
    mcrop = sq if aligned else crop
    # dedupe to unique timestamps (a trailing z-stack shares one t_sec). Require a RAW fluor page so no frame
    # falls back to the baked mp4 (which bypasses the shared lo/hi and breaks the uniform exposure).
    fluor_ts = [float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None]
    src = fluor_ts if fluor_ts else list(tsm)
    uniq = []; seen = set()
    for t in src:
        r = round(float(t), 1)
        if r in seen: continue
        seen.add(r); uniq.append(float(t))
    # FOCUS the story window on start -> ~15 min past anaphase (clamped), not the full multi-hour tail
    at = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", ""))
    t0 = uniq[0]; t1 = uniq[-1]
    if at is not None:
        t1 = min(uniq[-1], float(at) + POST_ANA_S)
    win = [t for t in uniq if t0 <= t <= t1] or uniq
    sel = [win[i] for i in np.linspace(0, len(win)-1, min(ncols, len(win))).astype(int)]
    def plab(t):
        if mt is not None and abs(t - mt) <= 60: return "metaphase"
        if at is not None and abs(t - at) <= 120: return "anaphase"
        return None
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": plab(t)} for t in sel]
    # PHASE from the rendered mp4
    boxes = (tracked_boxes(b, sel, mcrop) if (b in MONITOR_FOLLOW and mcrop) else [mcrop]*len(sel))
    cap = movie(b, "Phase", "Monitoring")
    if cap:
        for ci, t in enumerate(sel):
            fr = grab(cap, tsm, t)
            if fr is None: continue
            fr = fr.copy()
            if boxes[ci]: fr = ts_render.crop_pad(fr, boxes[ci]).copy()
            panels[ci]["phase"] = fr
        cap.release()
    # FLUOR from RAW in-focus plane, stretched with ONE shared lo/hi over the WHOLE monitoring strip (uniform
    # exposure -> no blown/black frames); fall back to mp4 if a plane is missing.
    capf = movie(b, "Fluor", "Monitoring")
    mon_lo, mon_hi, mplanes = strip_fluor_limits(b, "monitoring", sel)
    for ci, t in enumerate(sel):
        p = mplanes[ci]
        gf = _stretch_green(p, lo=mon_lo, hi=mon_hi) if p is not None else None
        if gf is None and capf is not None:
            fr = grab(capf, tsm, t)
            if fr is not None: gf = fr.copy()
        if gf is None: continue
        if boxes[ci]: gf = ts_render.crop_pad(gf, boxes[ci]).copy()   # same window as the phase tile
        panels[ci]["fluor"] = gf
    if capf: capf.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b)*((boxes[0][2]-boxes[0][0]) if boxes and boxes[0] else (sq[2]-sq[0]))/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, chan_labels=CHAN, fluor_only=False)   # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")

# ================= build the per-batch timestrips =================
made = []
for b, note in TIMESTRIP_BATCHES:
    d = render_dir(b)
    if not d: print(f"  skip {b}: no render dir"); continue
    drug = "colcemid" if "colcemid" in b.lower() else ("nocodazole" if "nocodazole" in b.lower() else "drug")
    stem = f"G3_slippage_timestrip_{drug}"
    # Crop = FIXED 78µm physical window (ts_render.STD_MAIN_UM) centred on the FLUOR-estimated cell centroid
    # (no manual outline). The MAIN strip uses that window at native resolution; the _aligned variant resamples
    # the SAME window to square ALIGN_N tiles. Both share one magnification/scale-bar with every other timestrip.
    # Fall back to the raw fluor_crop box only if the standard window can't be computed.
    sq = std_crop(b)
    crop = sq if sq is not None else fluor_crop(b)
    mon = monitoring_portion(b, crop)
    if not mon: print(f"  skip {b}: no monitoring portion"); continue
    ok = ts_render.emit([("monitoring", mon[0], mon[1])], f"{OUT}/{stem}",
                        title=f"{drug.capitalize()} slippage — {b}")
    made.append(stem + ".png")
    lib.record_plot(stem, ["batch"], [[b]],
        {"type": "slippage/exhaustion-control monitoring timestrip", "drug": drug,
         "crop": [int(v) for v in crop] if crop else None, "note": note},
        SCRIPT, f"Mitotic-slippage control timestrip ({b})")
    print(f"slippage timestrip {b}: {'ok' if ok else 'FAIL'}")
    # ALIGNED-CROP variant — same fixed 78µm window, resampled to square ALIGN_N tiles (shared square footprint)
    if sq is None:
        print(f"  {stem}_aligned: SKIP (no fluor crop)")
    else:
        mA = monitoring_portion(b, crop, aligned=True, sq=sq)
        if mA:
            okA = ts_render.emit([("monitoring", mA[0], mA[1])], f"{OUT}/{stem}_aligned",
                                 title=f"{drug.capitalize()} slippage (aligned) — {b}")
            made.append(stem + "_aligned.png")
            print(f"  {stem}_aligned: {'ok' if okA else 'FAIL'}")
            if okA:   # register the variant so it is staleness-checkable (2026-08-04)
                lib.record_plot(stem + "_aligned", ["batch"], [[b]],
                    {"type": "slippage/exhaustion-control monitoring timestrip (aligned square crop)",
                     "variant_of": stem, "drug": drug,
                     "crop": [int(v) for v in sq] if sq else None, "note": note,
                     "geometry": "fixed 78um window resampled to square ALIGN_N tiles"},
                    SCRIPT, f"Mitotic-slippage control timestrip ({b}) — aligned square crop")
        else:
            print(f"  {stem}_aligned: SKIP (no portion)")

print("SLIPPAGE TIMESTRIP PNGs:", made)
