# 2026-08-16 (NOTES §1 rule 30): red marker on a GREEN fluorescence panel is the forbidden pair.
# Ablation-site circles are MAGENTA (255,0,255) BGR. Found by a pixel audit of the RENDERED figures
# after a first sweep missed these files.
"""Group 9 / Drug controls — FULL ablation TIMESTRIPS for two drug-treated ablation cells.

Same standards + shared infrastructure as group_timestrips.py / group5_mad1_examples.py:
 * shared ts_render module (ONE consistent font, editable-SVG text, timestamps, channel labels,
   scale bars, red-CIRCLE ablation markers, 2 µm zoom scalebars) — T1/T2/T5/T7.
 * the standardized 78 µm main crop (ts_render.STD_MAIN_UM / std_square_crop) for the `_aligned`
   variant so magnification + scale-bar length match every other ablation timestrip.
 * forward-skip flash handling (flash_idx / nonflash_forward) replicated from group_timestrips so the
   'after' panel steps past the black laser-flash / SLM-grid frame to a CLEAN frame.
 * ablation markers come from frames.json `ablation_events_local` (render_xy = x_px-roi.x, y_px-roi.y).

These two eYFP-Cdc20 PtK cells WITH ablations follow the FULL ablation-timestrip format:
   ablation strip (before / ablation-with-red-CIRCLE marker / after) + ablation ZOOM close-up(s)
   + monitoring strip, phase (top) + fluor (bottom).
They have NO manual outline -> the crop is estimated from the eYFP fluorescence of the centred cell
(ts_render.STD_MAIN_UM window), like group5_mad1_examples.fluor_crop.

Emits, per timestrip: <name>.png, <name>_notext.png, illustrator/<name>.svg (via ts_render.emit),
and an <name>_aligned.png square-tile variant.
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

# ---- the two curated, comment-flagged drug-ablation cells ----
# (stem, batch, caption). Caption names drug + dose + ablation count + fate.
BATCHES = [
    ("G9_drug_timestrip_zm", "20260422 Zm_ablation_2um_31",
     "ZM (Aurora-B inhibitor) — 3 ablated kinetochores (3-sisterless); two chromosomes polar until anaphase (~32:26), cell proceeds to cytokinesis (~41:06)"),
    ("G9_drug_timestrip_zm3", "20260422 Zm_ablation_2um_25",
     "ZM (Aurora-B inhibitor) — 3 ablated kinetochores (3-sisterless), 3 spatially-distinct targets; cell stays a rounded mitotic mass in prolonged arrest (no anaphase across the ~65 min monitor)"),
    # 2026-08-17: zm18 was placed on META but this builder never listed it, so it had no publication twin
    # and could not be re-rendered. The batch and its render dir both exist; the caption is taken from the
    # master row (3 sisterless KTs, metaphase 23:44, anaphase 29:25, cytokinesis 43:36) plus her own Notes.
    ("G9_drug_timestrip_zm18", "20260422 Zm_ablation_2um_18",
     "ZM (Aurora-B inhibitor) — 3 ablated kinetochores (3-sisterless); metaphase 23:44, anaphase 29:25 "
     "(5:41 metaphase), cytokinesis 43:36. Her note: chromosomes remain disorganised, so metaphase onset is hard to call"),
    ("G9_drug_timestrip_noc", "20260416 ptk2 eyfp cdc20 ablation plus low dose noc_15",
     "Low-dose nocodazole — 1 ablation; cell had NOT reached anaphase by 1:18:00 (mitotic arrest)"),
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
def abl_events(b):
    fj = fjson(b)
    if not fj: return []
    roi = fj.get("roi") or {"x": 0, "y": 0}
    m = ts_render.manual_pre_abl_local(b)        # PREFER manual pre_abl marks (ground truth); no flash-refine
    if m: return m
    out = []
    for e in fj.get("ablation_events_local", []):
        try: out.append((e["x_px"] - roi.get("x", 0), e["y_px"] - roi.get("y", 0)))
        except: pass
    return out
def cluster_events(evs, thr=45.0):
    """Greedy-cluster ablation shots into DISTINCT targets (one zoom close-up per target). Repeated shots at
    one KT collapse to one cluster; returns centroids in first-appearance order."""
    cl = []
    for (x, y) in evs:
        for c in cl:
            if (c["cx"] - x) ** 2 + (c["cy"] - y) ** 2 <= thr * thr:
                c["pts"].append((x, y)); c["cx"] = np.mean([p[0] for p in c["pts"]]); c["cy"] = np.mean([p[1] for p in c["pts"]]); break
        else:
            cl.append({"pts": [(x, y)], "cx": x, "cy": y})
    return [(c["cx"], c["cy"]) for c in cl]

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
def _is_dark(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
    return float(np.percentile(g, 99.5)) < 12
def _stretch_bgr(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
    lo, hi = float(np.percentile(g, 2)), float(np.percentile(g, 99.5))
    if hi - lo < 4: return None
    return cv2.cvtColor(np.clip((g.astype(np.float32) - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

# ---- flash / SLM-grid handling (replicated from group_timestrips: keep flash frames OFF the strips) ----
_FLASH = {}
def flash_idx(b):
    """(flash_frame_indices, t_sec_array) for the ablation movie. A laser-shot frame has brightfield OFF ->
    the PHASE frame is essentially black; also flag fluor brightness outliers. Used by nonflash_* to step the
    'after' panel to a CLEAN frame."""
    if b in _FLASH: return _FLASH[b]
    res = set(); ts = None
    capp = movie(b, "Phase", "Ablation"); tsp = role_ts(b, "ablation")
    if capp is not None and tsp is not None:
        ts = tsp; dark = set()
        for i in range(len(tsp)):
            capp.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = capp.read()
            if ok and _is_dark(fr): dark.add(i)
        capp.release()
        if len(dark) <= max(1, len(tsp) // 2): res |= dark
    capf = movie(b, "Fluor", "Ablation")
    if capf is not None:
        tsf = role_ts(b, "ablation"); means = []
        for i in range(len(tsf) if tsf is not None else 0):
            capf.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = capf.read()
            means.append(float(fr.mean()) if ok else np.nan)
        capf.release()
        if ts is None: ts = tsf
        arr = np.array(means, float); med = np.nanmedian(arr) if np.isfinite(arr).any() else np.nan
        if np.isfinite(med):
            for i, mv in enumerate(means):
                if np.isfinite(mv) and mv > 1.6 * med + 3: res.add(i)
    _FLASH[b] = (res, ts); return _FLASH[b]
def nonflash_t(b, t):
    fs, ts = flash_idx(b)
    if not fs or ts is None or len(ts) == 0: return t
    i = int(np.argmin(np.abs(ts - t))); guard = 0
    while i in fs and i > 0 and guard < 5: i -= 1; guard += 1
    return float(ts[i])
def nonflash_forward(b, t):
    fs, ts = flash_idx(b)
    if not fs or ts is None or len(ts) == 0: return t
    i = int(np.argmin(np.abs(ts - t))); guard = 0
    while i in fs and i < len(ts) - 1 and guard < 10: i += 1; guard += 1
    return float(ts[i])
def brightest_abl_t(b, lo, hi):
    """t_sec of the BRIGHTEST (normal-brightfield) phase ablation frame in [lo,hi] — the marker frame, so the
    magenta circles land on a frame where brightfield is ON (not the black laser-flash frame)."""
    cap = movie(b, "Phase", "Ablation"); ts = role_ts(b, "ablation")
    if cap is None or ts is None: return None
    best, bv = None, -1.0
    for i, t in enumerate(ts):
        if t < lo - 1e-6 or t > hi + 1e-6: continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = cap.read()
        if ok and fr.mean() > bv: bv = float(fr.mean()); best = float(t)
    cap.release(); return best

def phase_ablation_frame(cap, ts, t, b):
    """Phase ablation frame with the dark-frame fallback (reveal faint phase; else substitute stretched 488)."""
    fr = grab(cap, ts, t)
    if fr is None or not _is_dark(fr): return fr
    st = _stretch_bgr(fr)
    if st is not None: return st
    capf = movie(b, "Fluor", "Ablation")
    if capf is not None:
        ff = grab(capf, ts, t); capf.release()
        sf = _stretch_bgr(ff) if ff is not None else None
        if sf is not None: return sf
    return fr

# ---- crop estimated from FLUORESCENCE (centred cell), like group5_mad1_examples ----
def fluor_crop(b, as_pts=False):
    """as_pts=True -> return (bbox_corner_pts, W, H) of the ESTIMATED cell blob (NO added margin) for
    ts_render.tight_square (TIGHT, exactly-square, undistorted crop that fills the frame)."""
    fj = fjson(b); d = render_dir(b)
    if not fj or not d: return None
    fr0 = (role_frames(b, "ablation") or role_frames(b, "monitoring"))
    if not fr0: return None
    fr0 = fr0[0]
    fpath = f"{d}/{b}_Fluor_Cropped.tif"; plane = None
    if os.path.isfile(fpath):
        stk = tifffile.imread(fpath); idx = int(fr0["fluor_tif_idx"])
        plane = (stk[min(idx, stk.shape[0] - 1)] if stk.ndim == 3 else np.squeeze(stk)).astype(np.float32)
    else:
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
    cy, cx = H // 2, W // 2; ry, rx = int(H * 0.32), int(W * 0.32)
    mask = np.zeros_like(sm, bool); mask[cy - ry:cy + ry, cx - rx:cx + rx] = True
    thr = (sm > np.percentile(sm[mask], 96)) & mask
    n, lbl, stats, cent = cv2.connectedComponentsWithStats(thr.astype(np.uint8), 8)
    best, bd = None, 1e18
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 40: continue
        dd = (cent[i][0] - cx) ** 2 + (cent[i][1] - cy) ** 2
        if dd < bd: bd, best = dd, i
    if best is None:
        hw = min(H, W) // 3
        return (cx - hw, cy - hw, cx + hw, cy + hw)
    x, y, w, h = stats[best, 0], stats[best, 1], stats[best, 2], stats[best, 3]
    m = 55
    return (max(0, x - m), max(0, y - m), min(W, x + w + m), min(H, y + h + m))
def fluor_tight_crop(b, margin=1.12):
    """UNIFORM-scale-before-crop square window from the FLUOR-estimated cell blob (ts_render.tight_square,
    margin=1.12 -> cell fills ~89% of the frame, small breathing room, no clipped edges); forced square so the
    later resize is uniform (no distortion). Reused for ALL frames."""
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)
def body_crop(b):
    """Consistent-size SQUARE crop for the NON-aligned main + monitoring tiles: centred on the fluor-crop
    centroid but with the side CLAMPED to [0.34, 0.55]·(short frame side) — so the cell fills a comparable
    fraction of every drug strip (the raw fluor blob crop varies wildly: 122 px vs 242 px), keeping the main
    ablation + monitoring tiles balanced against the fixed 3× zoom close-ups. Mirrors tight_crop's clamping."""
    fc = fluor_crop(b)
    if fc is None: return None
    cap = (movie(b, "Fluor", "Ablation") or movie(b, "Fluor", "Monitoring")
           or movie(b, "Phase", "Ablation") or movie(b, "Phase", "Monitoring"))
    if not cap: return fc
    W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
    cx = (fc[0] + fc[2]) / 2.0; cy = (fc[1] + fc[3]) / 2.0
    side = max(fc[2] - fc[0], fc[3] - fc[1]) * 1.3
    side = min(max(side, 0.34 * min(W, H)), 0.55 * min(W, H))
    half = side / 2.0
    x0, y0, x1, y1 = int(round(cx - half)), int(round(cy - half)), int(round(cx + half)), int(round(cy + half))
    if x0 < 0: x1 -= x0; x0 = 0
    if y0 < 0: y1 -= y0; y0 = 0
    if x1 > W: x0 -= (x1 - W); x1 = W
    if y1 > H: y0 -= (y1 - H); y1 = H
    return (max(0, x0), max(0, y0), x1, y1)
def std_crop(b):
    """TIGHT square crop (ts_render.tight_square) sized to THIS cell's FLUOR-estimated bbox -> the cell fills the
    frame (replaces the old 78µm window that left the cell loose); exactly square -> uniform resize, no distortion.
    Reused for ALL ablation + monitoring frames."""
    return fluor_tight_crop(b)

# ---- raw per-frame-stretched eYFP monitoring plane (fixes black late-frame fluor as eYFP-Cdc20 degrades) ----
def _stretch_green(plane, lo_p=30, hi_p=99.7, gamma=0.9, lo=None, hi=None):
    """eYFP-Cdc20 -> green BGR. UNIFORM-EXPOSURE: pass explicit lo/hi (computed ONCE over the whole monitoring
    strip) so every frame shares ONE fixed mapping (no per-frame auto-normalisation). lo/hi=None -> per-frame."""
    a = plane.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)
    g8 = (n * 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8
    return green
def raw_fluor_plane(b, role, t, tol=0.2):
    """Selected in-focus RAW eYFP-Cdc20 fluor plane (float32) for a `role` timepoint, NO stretch."""
    d = render_dir(b); fp = f"{d}/{b}_Fluor_Cropped.tif" if d else None
    if not fp or not os.path.isfile(fp): return None
    same = [f for f in role_frames(b, role) if abs(float(f["t_sec"]) - t) <= tol]
    if not same: return None
    idxs = [int(f["fluor_tif_idx"]) for f in same if f.get("fluor_tif_idx") is not None]
    if not idxs: return None
    try:
        with tifffile.TiffFile(fp) as tf:
            n = len(tf.pages)
            cand = [i for i in idxs if 0 <= i < n] or [min(max(idxs[0], 0), n - 1)]
            best, bv = cand[0], -1.0
            for i in cand:
                v = float(tf.pages[i].asarray().astype(np.float32).var())
                if v > bv: bv, best = v, i
            return tf.pages[best].asarray().astype(np.float32)
    except Exception:
        return None
def strip_fluor_limits(b, role, times, tol=0.2, lo_p=30, hi_p=99.7):
    """ONE (lo,hi) mapping for a whole strip-type: percentiles pooled over ALL its raw planes -> applied
    identically to every frame. Returns (lo, hi, planes) with planes aligned to `times` (cached, no re-read)."""
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes
def raw_fluor_monitor(b, t, lo=None, hi=None):
    p = raw_fluor_plane(b, "monitoring", t)
    return _stretch_green(p, lo=lo, hi=hi) if p is not None else None

# ---- ablation portion: before / marked (magenta circles) / after + one zoom per distinct target ----
def ablation_portion(b, crop, aligned=False, sq=None):
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b); centroids = cluster_events(evs)
    t_first, t_last = float(tsa.min()), float(tsa.max())
    tb = nonflash_t(b, t_first)                               # before: first (clean) ablation frame
    tm = brightest_abl_t(b, t_first, t_last) or (t_first + t_last) / 2.0  # marked: normal-brightfield frame
    ta = nonflash_forward(b, t_last)                          # after: last (clean) ablation frame
    if ta <= tm: ta = nonflash_forward(b, t_last)
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
    mcrop = sq if aligned else crop
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        if not cap: continue
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            fr = phase_ablation_frame(cap, tsa, t, b) if ch == "Phase" else grab(cap, tsa, t)
            if fr is None: continue
            fr = fr.copy()
            if mk:
                r = max(9, int(0.011 * fr.shape[1]))
                # USER 2026-08-17: the ablation marker is a sleek open-centre X, not a bulky circle
                # (the Dumont-lab k-fibre convention; circles/arrowheads mark STRUCTURES). Drawn by the
                # shared helper so the drug strips match the nf9/nf10 strips exactly.
                import group_timestrips as _G
                _G.draw_marks(fr, [(x, y, (255, 0, 255), "x", None) for (x, y) in evs])
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            wide[ci][key] = fr
        cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=True)
    if res: portions.append(("ablation", res[0], res[1]))
    # zoom close-up per DISTINCT target (before / marked / after), magenta circle on the middle panel only
    HALF = ts_render.zoom_half_px(ps(b)) if aligned else 60; ZOOM = 3
    for ei, (ex, ey) in enumerate(centroids[:4]):
        cu = [{"t": t, "phase": None, "fluor": None} for (_, t, _) in times]
        for ch in ("Phase", "Fluor"):
            cap = movie(b, ch, "Ablation")
            if not cap: continue
            key = "phase" if ch == "Phase" else "fluor"
            for ci, (tag, t, mk) in enumerate(times):
                fr = phase_ablation_frame(cap, tsa, t, b) if ch == "Phase" else grab(cap, tsa, t)
                if fr is None: continue
                if aligned:
                    z = ts_render.zoom_to_square(fr, ex, ey, HALF, mk)
                    if z is not None: cu[ci][key] = z
                else:
                    xi, yi = int(round(ex)), int(round(ey)); h, wd = fr.shape[:2]
                    x0, y0 = max(0, xi - HALF), max(0, yi - HALF); x1, y1 = min(wd, xi + HALF), min(h, yi + HALF)
                    sub = fr[y0:y1, x0:x1].copy()
                    if sub.size == 0: continue
                    if mk:
                        import group_timestrips as _G
                        _G.draw_marks(sub, [(xi - x0, yi - y0, (255, 0, 255), "x", None)])
                    cu[ci][key] = cv2.resize(sub, (sub.shape[1] * ZOOM, sub.shape[0] * ZOOM), interpolation=cv2.INTER_NEAREST)
            cap.release()
        zeff = ps(b) * (2 * HALF) / ts_render.ALIGN_N if aligned else ps(b) / ZOOM
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None],
                                 zeff, 2.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=True, show_fmt=False)
        if res: portions.append((f"ablation close-up {ei + 1}", res[0], res[1]))
    return portions

# ---- monitoring portion: master-event panels (meta/ana/+min) or, if no anaphase, sustained-arrest sampling ----
def mon_spec(b):
    """(t_sec, phase_label) monitoring panels. WITH anaphase -> prometaphase/metaphase/anaphase/+3min (capped
    at anaphase+min, none past exit). NO anaphase (arrest) -> evenly sample the monitoring window to show the
    cell stays in mitosis; timestamps convey the long arrest."""
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return []
    tmin, tmax = float(tsm.min()), float(tsm.max())
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", ""))
    at = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    ct = lib.parse_time(mr.get(b, {}).get("Cytokinesis Onset (s)", ""))
    if at is not None:
        spec = []
        if mt is not None and tmin < mt:
            spec.append((max(tmin, mt - (mt - tmin) * 0.5), "prometaphase"))
        if mt is not None: spec.append((mt, "metaphase"))
        spec.append((at, "anaphase"))
        if ct is not None and ct > at:                      # fate: reaches cytokinesis (divides)
            spec.append((min(ct, tmax), "cytokinesis"))
        else:
            spec.append((min(at + 180, tmax), None))        # else ~3 min past anaphase
        return spec
    # arrest: no anaphase -> show sustained mitosis across the whole monitoring window
    sel = np.linspace(tmin, tmax, 5)
    return [(float(t), None) for t in sel]

def monitoring_portion(b, crop, aligned=False, sq=None):
    spec = mon_spec(b)
    if not spec: return None
    tsm = role_ts(b, "monitoring")
    mcrop = sq if aligned else crop
    # SNAP each requested time to the nearest monitoring frame that HAS a raw fluor page, so no frame falls back
    # to the baked mp4 (which bypasses the shared lo/hi and breaks the uniform exposure). Keep the label.
    fluor_ts = np.array([float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None])
    if fluor_ts.size:
        spec = [(float(fluor_ts[int(np.argmin(np.abs(fluor_ts - t)))]), lab) for (t, lab) in spec]
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": lab} for (t, lab) in spec]
    capp = movie(b, "Phase", "Monitoring")
    if capp:
        for ci, (t, lab) in enumerate(spec):
            fr = grab(capp, tsm, t)
            if fr is None: continue
            fr = fr.copy()
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            panels[ci]["phase"] = fr
        capp.release()
    capf = movie(b, "Fluor", "Monitoring")
    # ONE shared lo/hi over the WHOLE monitoring strip -> uniform exposure (no blown/black frames)
    mon_lo, mon_hi, mplanes = strip_fluor_limits(b, "monitoring", [t for (t, _l) in spec])
    for ci, (t, lab) in enumerate(spec):
        p = mplanes[ci]
        gf = _stretch_green(p, lo=mon_lo, hi=mon_hi) if p is not None else None
        if gf is None and capf is not None:
            fr = grab(capf, tsm, t)
            if fr is not None: gf = fr.copy()
        if gf is None: continue
        if mcrop: gf = ts_render.crop_pad(gf, mcrop).copy()
        panels[ci]["fluor"] = gf
    if capf: capf.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=False)  # MONITORING = PHASE + FLUOR (user: "monitoring in phase and fluor")

# ================= build =================
made = []
for stem, b, note in BATCHES:
    d = render_dir(b)
    if not d: print(f"  skip {b}: no render dir"); continue
    crop = std_crop(b) or body_crop(b)                         # TIGHT square crop (cell fills the frame; no distortion)
    portions = ablation_portion(b, crop)
    mon = monitoring_portion(b, crop)
    if mon: portions.append(("monitoring", mon[0], mon[1]))
    if not portions: print(f"  skip {b}: no portions"); continue
    ok = ts_render.emit(portions, f"{OUT}/{stem}", title=f"Drug-control ablation — {b}")
    made.append(stem + ".png")
    print(f"{stem}: {b} -> {len(portions)} portions ({len(abl_events(b))} abl events, "
          f"{len(cluster_events(abl_events(b)))} targets) {'ok' if ok else 'FAIL'}")
    lib.record_plot(stem, ["batch"], [[b]],
        {"type": "drug-control ablation timestrip", "note": note,
         "n_abl_events": len(abl_events(b)), "n_targets": len(cluster_events(abl_events(b))),
         "crop": [int(v) for v in crop] if crop else None, "n_portions": len(portions)},
        SCRIPT, f"Drug-control ablation timestrip ({b})")
    # aligned-crop variant (fixed-physical 78 µm main window + consistent zoom)
    sq = std_crop(b)
    if sq is None:
        print(f"  {stem}_aligned: SKIP (no fluor crop)")
    else:
        pA = ablation_portion(b, crop, aligned=True, sq=sq)
        mA = monitoring_portion(b, crop, aligned=True, sq=sq)
        if mA: pA.append(("monitoring", mA[0], mA[1]))
        if pA:
            okA = ts_render.emit(pA, f"{OUT}/{stem}_aligned", title=f"Drug-control ablation (aligned square crop) — {b}")
            made.append(stem + "_aligned.png")
            print(f"  {stem}_aligned: {len(pA)} portions {'ok' if okA else 'FAIL'}")
            if okA:   # register the variant so it is staleness-checkable (2026-08-04)
                lib.record_plot(stem + "_aligned", ["batch"], [[b]],
                    {"type": "drug-control ablation timestrip (aligned square crop)",
                     "variant_of": stem, "note": note,
                     "n_abl_events": len(abl_events(b)), "n_targets": len(cluster_events(abl_events(b))),
                     "crop": [int(v) for v in sq] if sq else None, "n_portions": len(pA),
                     "geometry": "fixed-physical 78um square footprint + constant zoom"},
                    SCRIPT, f"Drug-control ablation timestrip ({b}) — aligned square crop")
        else:
            print(f"  {stem}_aligned: SKIP (no portions)")

print("TIMESTRIP PNGs:", made)
