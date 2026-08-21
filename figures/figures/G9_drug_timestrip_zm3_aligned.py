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

STEM  = "G9_drug_timestrip_zm3"
BATCH = "20260422 Zm_ablation_2um_25"
ID    = f"{STEM}_aligned"
OUT   = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)

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
def cluster_events(evs, thr=45.0):
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

# ---- ablation portion (aligned) ----
def ablation_portion(b, sq):
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b); centroids = cluster_events(evs)
    t_first, t_last = float(tsa.min()), float(tsa.max())
    tb = nonflash_t(b, t_first)
    tm = brightest_abl_t(b, t_first, t_last) or (t_first + t_last) / 2.0
    ta = nonflash_forward(b, t_last)
    if ta <= tm: ta = nonflash_forward(b, t_last)
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
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
        if ct is not None and ct > at:
            spec.append((min(ct, tmax), "cytokinesis"))
        else:
            spec.append((min(at + 180, tmax), None))
        return spec
    sel = np.linspace(tmin, tmax, 5)
    return [(float(t), None) for t in sel]

def monitoring_portion(b, sq):
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
            fr = ts_render.crop_pad(fr.copy(), sq).copy()
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
        gf = ts_render.crop_pad(gf, sq).copy()
        panels[ci]["fluor"] = gf
    if capf: capf.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, chan_labels=("Phase", "eYFP-Cdc20"), fluor_only=False)

def main():
    if not RDIR:
        print(f"FAIL {ID}: no render dir for {BATCH}"); return
    sq = std_crop(BATCH)
    if sq is None:
        print(f"FAIL {ID}: no fluor crop"); return
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
