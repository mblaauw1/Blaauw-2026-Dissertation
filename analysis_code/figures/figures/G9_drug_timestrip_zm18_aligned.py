# 2026-08-16 (NOTES §1 rule 30): red marker on a GREEN fluorescence panel is the forbidden pair.
# Ablation-site circles are MAGENTA (255,0,255) BGR. Found by a pixel audit of the RENDERED figures
# after a first sweep missed these files.
#!/usr/bin/env python3
"""Standalone 1:1:1 rebuild of ONE figure: G9_drug_timestrip_noc_aligned.

The ALIGNED-CROP variant of the ZM (Aurora-B inhibitor) drug-control ablation timestrip for batch
"20260422 Zm_ablation_2um_25" (3 ablated kinetochores / 3-sisterless, 3 spatially-distinct targets;
cell stays a rounded mitotic mass in prolonged arrest — no anaphase across the ~65 min monitor).

Aligned = ablation strip (before / marked-with-MAGENTA-CIRCLE / after; FLUOR-ONLY per 07-09 feedback) +
one ablation ZOOM close-up per DISTINCT target + monitoring strip (phase + fluor), ALL cropped to ONE
fixed square footprint (ts_render.tight_square on the FLUOR/brightfield-estimated cell bbox — this cell
has NO manual outline) and resampled to ts_render.ALIGN_N so every tile shares one magnification and
stacks in aligned columns. Monitoring fluor uses ONE shared lo/hi (uniform exposure across the strip).

Ported from group_drug_ablation_timestrips.py (the `_aligned` block only), pinned to this one batch.
Imports ONLY ts_render primitives + lib styling — never another figure's builder. Ablation markers come
from frames.json ablation_events_local (render_xy = x_px - roi.x). Honors $KTFIG_OUT for the output dir.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, glob, json, numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter
import lib, ts_render

STEM  = "G9_drug_timestrip_zm18"
BATCH = "20260422 Zm_ablation_2um_18"
ID    = f"{STEM}_aligned"
OUT   = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)

# ---- HER FRAMES, given 2026-08-10 -----------------------------------------------------------------
# "first ablation: pre -7s, target -1, post 7s / Second ablation: pre 10s, target 10s, post 34s /
#  Third ablation: pre 40s, target 43s, post 01:13"
#
# The ablation clip runs -14..85 s on a 3 s grid, so every time she gave lands on a real frame (-7 -> -8,
# -1 -> -2, the rest exact). The SECOND ablation is the one that needed resolving: she wrote pre and target
# both as 10 s. The clip decides it. There is no bright flash here; instead the PHASE frames DARKEN while
# the laser fires -- mean 121 vs a 155 baseline -- at 1, 4 / 13, 16, 19 / 46, 49. So each shot begins at
# 1, 13 and 46, and her three "target" times (-2, 10, 43) are each THE LAST FRAME BEFORE THE SHOT, which is
# how she marks them. The pre for ablation 2 therefore has to be 7 s, the only frame before 10, and that is
# why 10 got written twice. 7 s doubles as ablation 1's post; it is one frame serving both, not an error.
ABL_LIMS = (None, None)
ABL_SPEC = [(-8.0, -2.0, 7.0),     # abl 1: shot at 1 s
            (7.0, 10.0, 34.0),     # abl 2: shot at 13 s
            (40.0, 43.0, 73.0)]    # abl 3: shot at 46 s
# "Monitoring 10:10, 18:01, 21:27, 23:44, 26:34, 29:25, 32:48, 36:47, 40:12, 00:49:17, 01:31:23"
MON_TIMES = [610.0, 1081.0, 1287.0, 1424.0, 1594.0, 1765.0, 1968.0, 2207.0, 2412.0, 2957.0, 5483.0]
# 23:44 is also this batch's master Metaphase Start, so that column is labelled metaphase.

def snap(ts, t):
    """Nearest real frame time -- never invent a timestamp the clip does not have."""
    import numpy as _np
    return float(ts[int(_np.argmin(_np.abs(_np.asarray(ts) - t)))])

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except Exception: return 0.062

def _find_render_dir(b):
    for fj in glob.glob("/Volumes/4 MB/**/%s_frames.json" % b, recursive=True):
        if "_ARCHIVED" in fj or "backup" in fj.lower(): continue
        return os.path.dirname(fj)
    return None
RDIR = _find_render_dir(BATCH)

def fjson(b):
    if RDIR and os.path.isfile(f"{RDIR}/{b}_frames.json"): return json.load(open(f"{RDIR}/{b}_frames.json"))
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
    roi = fj.get("roi") or {"x": 0, "y": 0}; out = []
    for e in fj.get("ablation_events_local", []):
        try: out.append((e["x_px"] - roi.get("x", 0), e["y_px"] - roi.get("y", 0)))
        except Exception: pass
    return out
def cluster_events(evs, thr=20.0):
    cl = []
    for (x, y) in evs:
        for c in cl:
            if (c["cx"] - x) ** 2 + (c["cy"] - y) ** 2 <= thr * thr:
                c["pts"].append((x, y)); c["cx"] = np.mean([p[0] for p in c["pts"]]); c["cy"] = np.mean([p[1] for p in c["pts"]]); break
        else:
            cl.append({"pts": [(x, y)], "cx": x, "cy": y})
    return [(c["cx"], c["cy"]) for c in cl]

def movie(b, ch, role):
    if not RDIR: return None
    mp4 = f"{RDIR}/{b}_{ch}_{role}.mp4"
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

# ---- flash / SLM-grid handling ----
_FLASH = {}
def flash_idx(b):
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
    cap = movie(b, "Phase", "Ablation"); ts = role_ts(b, "ablation")
    if cap is None or ts is None: return None
    best, bv = None, -1.0
    for i, t in enumerate(ts):
        if t < lo - 1e-6 or t > hi + 1e-6: continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = cap.read()
        if ok and fr.mean() > bv: bv = float(fr.mean()); best = float(t)
    cap.release(); return best
def phase_ablation_frame(cap, ts, t, b):
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

# ---- crop estimated from FLUORESCENCE / brightfield (no manual outline) ----
def fluor_crop(b, as_pts=False):
    fj = fjson(b)
    if not fj or not RDIR: return None
    fr0 = (role_frames(b, "ablation") or role_frames(b, "monitoring"))
    if not fr0: return None
    fr0 = fr0[0]
    fpath = f"{RDIR}/{b}_Fluor_Cropped.tif"; plane = None
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
    if as_pts:
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
def std_crop(b, margin=1.12):
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)

# ---- uniform-exposure eYFP monitoring fluor ----
def _stretch_green(plane, lo_p=30, hi_p=99.7, gamma=0.9, lo=None, hi=None):
    a = plane.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)
    g8 = (n * 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8
    return green
def raw_fluor_plane(b, role, t, tol=0.2):
    fp = f"{RDIR}/{b}_Fluor_Cropped.tif" if RDIR else None
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
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes


# ---- FRAMING ---------------------------------------------------------------------------------------
# The two clips do NOT share a frame. frames.json shows the ablation coming from
# Zm_ablation_2um_18_MMStack_Pos0 and ALL 363 monitoring frames from Zm_ablation_2um_24_MMStack_Pos5 --
# the ablation acquisition and the later multi-position monitoring sweep. The cell therefore sits at
# ~(490,520) during ablation and ~(900-1100, 610-750) during monitoring, about 31 um apart, and it drifts
# further over the 219 min monitor. One shared square cannot hold both: the first build used a single
# 795 px auto-detected box and produced a row of diagonal bands with the cell sliding out of frame.
#
# So each row is centred on the cell IN ITS OWN CLIP, at ONE fixed box size, which is what actually matters
# for comparability -- every tile is the same number of microns across, and both clips are 0.062 um/px at
# 2x2 binning per source_files. The ablation row centres on her ablation events; the monitoring row tracks
# the cell per timepoint.
BOX = 420                      # px = 26.0 um across, on a ~200 px (12.6 um) chromosome mass

def _square_at(cx, cy, W, H, box=None):
    box = box or BOX
    h = box // 2
    x0 = int(round(cx - h)); y0 = int(round(cy - h))
    x0 = max(0, min(W - box, x0)); y0 = max(0, min(H - box, y0))
    return (x0, y0, x0 + box, y0 + box)

def abl_square(b):
    """Centred on the mean of her ablation events -- the ablated cell, by definition."""
    ev = abl_events(b)
    if not ev: return None
    cx = float(np.mean([e[0] for e in ev])); cy = float(np.mean([e[1] for e in ev]))
    cap = movie(b, "Fluor", "Ablation")
    if cap is None: return None
    W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
    return _square_at(cx, cy, W, H)

def _blob_centres(fr, pct=99.0, ksig=3.0, minarea=800):
    """Bright blobs, with the burned-in timestamp / scale-bar overlays rejected. Those sit hard against a
    frame edge and are wide-and-flat (e.g. 156x28 at (1133,1033)); a mitotic cell is neither."""
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sm = gaussian_filter(g, 5.0)
    thr = sm > max(np.percentile(sm, pct), sm.mean() + ksig * sm.std())
    nlab, lbl, st, cent = cv2.connectedComponentsWithStats(thr.astype(np.uint8), 8)
    H, W = g.shape
    out = []
    for k in range(1, nlab):
        a = st[k, cv2.CC_STAT_AREA]
        if a < minarea: continue
        x, y, w, h = st[k, 0], st[k, 1], st[k, 2], st[k, 3]
        cx, cy = float(cent[k][0]), float(cent[k][1])
        if x <= 6 or y <= 6 or x + w >= W - 6 or y + h >= H - 6: continue   # touching an edge => overlay
        if w > 3.0 * h: continue                                            # wide flat text bar
        out.append((a, cx, cy))
    return sorted(out, reverse=True)

def mon_squares(b, times):
    """One square per monitoring timepoint, tracking the cell; holds the last good centre when the cell
    dims too far to segment (which it does late in the arrest) rather than jumping to an artefact."""
    cap = movie(b, "Fluor", "Monitoring")
    tsm = role_ts(b, "monitoring")
    if cap is None or tsm is None: return None
    W = int(cap.get(3)); H = int(cap.get(4))
    prev = None; sqs = []
    for t in times:
        fr = grab(cap, tsm, t)
        # eYFP dims through the arrest, so the late frames need a looser threshold; without this the
        # last two timepoints found nothing, held a stale centre, and the cell slid out of frame.
        cands = []
        if fr is not None:
            for (pct, ksig, minarea) in ((99.0, 3.0, 800), (98.0, 2.0, 400), (96.0, 1.5, 250)):
                cands = _blob_centres(fr, pct, ksig, minarea)
                if cands: break
        if cands:
            if prev is None:
                _a, cx, cy = cands[0]
            else:
                cx, cy = min(((c[1], c[2]) for c in cands),
                             key=lambda p: (p[0] - prev[0]) ** 2 + (p[1] - prev[1]) ** 2)
            # A ZM-arrested cell does not teleport. Across the 42 min gap to the last timepoint the nearest
            # blob was 519 px (32 um) away -- a different object, not this cell -- which framed the final
            # panel on background. Beyond MAXJUMP the previous centre is kept instead.
            MAXJUMP = 250.0
            if prev is not None and ((cx - prev[0]) ** 2 + (cy - prev[1]) ** 2) > MAXJUMP ** 2:
                print(f"   mon t={t:.0f}s: nearest blob {((cx-prev[0])**2+(cy-prev[1])**2)**0.5:.0f}px away "
                      f"-> rejected, holding previous centre")
            else:
                prev = (cx, cy)
        if prev is None: prev = (W / 2.0, H / 2.0)
        sqs.append(_square_at(prev[0], prev[1], W, H))
    cap.release()
    return sqs

# ---- ablation portion (aligned) ----
def ablation_portion(b, sq):
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b); centroids = cluster_events(evs)
    global ABL_LIMS
    _t_all = [snap(tsa, t) for grp in ABL_SPEC for t in grp]
    _lo, _hi, _ = strip_fluor_limits(b, "ablation", _t_all)
    ABL_LIMS = (_lo, _hi)
    times = []
    for ai, (tpre, ttgt, tpost) in enumerate(ABL_SPEC, start=1):
        times.append((f"abl{ai} pre", snap(tsa, tpre), False))
        times.append((f"abl{ai} target", snap(tsa, ttgt), True))
        times.append((f"abl{ai} post", snap(tsa, tpost), False))
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        if not cap: continue
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            fr = phase_ablation_frame(cap, tsa, t, b) if ch == "Phase" else grab(cap, tsa, t)
            if ch == "Fluor":
                # The rendered mp4 carries its own contrast stretch, which on this clip is blown out to a
                # flat saturated green. Re-derive from the raw TIF with ONE lo/hi shared across the row so
                # the nine columns stay comparable to each other.
                _pl = raw_fluor_plane(b, "ablation", t)
                if _pl is not None:
                    fr = _stretch_green(_pl, lo=ABL_LIMS[0], hi=ABL_LIMS[1])
            if fr is None: continue
            fr = fr.copy()
            if mk:
                r = max(9, int(0.011 * fr.shape[1]))
                for (x, y) in evs: cv2.circle(fr, (int(round(x)), int(round(y))), r, (255, 0, 255), 2, cv2.LINE_AA)
            fr = ts_render.crop_pad(fr, sq).copy()
            wide[ci][key] = fr
        cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=True)
    if res: portions.append(("ablation", res[0], res[1]))
    HALF = ts_render.zoom_half_px(ps(b))
    for ei, (ex, ey) in enumerate(centroids[:4]):
        cu = [{"t": t, "phase": None, "fluor": None} for (_, t, _) in times]
        for ch in ("Phase", "Fluor"):
            cap = movie(b, ch, "Ablation")
            if not cap: continue
            key = "phase" if ch == "Phase" else "fluor"
            for ci, (tag, t, mk) in enumerate(times):
                fr = phase_ablation_frame(cap, tsa, t, b) if ch == "Phase" else grab(cap, tsa, t)
                if fr is None: continue
                z = ts_render.zoom_to_square(fr, ex, ey, HALF, mk)
                if z is not None: cu[ci][key] = z
            cap.release()
        zeff = ps(b) * (2 * HALF) / ts_render.ALIGN_N
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None],
                                 zeff, 2.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=True, show_fmt=False)
        if res: portions.append((f"ablation close-up {ei + 1}", res[0], res[1]))
    return portions

# ---- monitoring portion (aligned; phase + fluor, uniform exposure) ----
def mon_spec(b):
    """Her 11 monitoring timepoints, verbatim. The auto selection this replaces picked 4-5 frames off
    metaphase/anaphase columns in the master, which is not what she asked for here."""
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return []
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", ""))
    out = []
    for t in MON_TIMES:
        lab = "metaphase" if (mt is not None and abs(t - mt) < 1.0) else None
        out.append((snap(tsm, t), lab))
    return out

def monitoring_portion(b, sq):
    SQS = mon_squares(b, [t for (t, _l) in mon_spec(b)]) or None
    spec = mon_spec(b)
    if not spec: return None
    tsm = role_ts(b, "monitoring")
    fluor_ts = np.array([float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None])
    if fluor_ts.size:
        spec = [(float(fluor_ts[int(np.argmin(np.abs(fluor_ts - t)))]), lab) for (t, lab) in spec]
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": lab} for (t, lab) in spec]
    capp = movie(b, "Phase", "Monitoring")
    if capp:
        for ci, (t, lab) in enumerate(spec):
            fr = grab(capp, tsm, t)
            if fr is None: continue
            fr = ts_render.crop_pad(fr.copy(), (SQS[ci] if SQS else sq)).copy()
            panels[ci]["phase"] = fr
        capp.release()
    capf = movie(b, "Fluor", "Monitoring")
    mon_lo, mon_hi, mplanes = strip_fluor_limits(b, "monitoring", [t for (t, _l) in spec])
    for ci, (t, lab) in enumerate(spec):
        p = mplanes[ci]
        gf = _stretch_green(p, lo=mon_lo, hi=mon_hi) if p is not None else None
        if gf is None and capf is not None:
            fr = grab(capf, tsm, t)
            if fr is not None: gf = fr.copy()
        if gf is None: continue
        gf = ts_render.crop_pad(gf, (SQS[ci] if SQS else sq)).copy()
        panels[ci]["fluor"] = gf
    if capf: capf.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * BOX / ts_render.ALIGN_N
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=False)

def main():
    if not RDIR:
        print(f"FAIL {ID}: no render dir for {BATCH}"); return
    sq = abl_square(BATCH) or std_crop(BATCH)
    if sq is None:
        print(f"FAIL {ID}: no crop"); return
    print(f"   ablation square {sq} ({(sq[2]-sq[0])*ps(BATCH):.1f} um across)")
    pA = ablation_portion(BATCH, sq)
    mA = monitoring_portion(BATCH, sq)
    if mA: pA.append(("monitoring", mA[0], mA[1]))
    if not pA:
        print(f"FAIL {ID}: no portions"); return
    ok = ts_render.emit(pA, f"{OUT}/{ID}", title=f"Drug-control ablation (aligned square crop) — {BATCH}")
    print(f"{ID}: {len(pA)} portions ({len(abl_events(BATCH))} abl events, "
          f"{len(cluster_events(abl_events(BATCH)))} targets) -> {OUT}/{ID}.png {'ok' if ok else 'FAIL'}")

if __name__ == "__main__":
    main()
