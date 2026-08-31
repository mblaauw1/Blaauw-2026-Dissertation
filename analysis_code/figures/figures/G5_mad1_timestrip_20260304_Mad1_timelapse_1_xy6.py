#!/usr/bin/env python3
"""Standalone 1:1:1 builder for ONE figure: G5_mad1_timestrip_20260304_Mad1_timelapse_1_xy6.

Mad1 timelapse example TIMESTRIP (monitoring-only; this batch has NO ablation). Phase (top) over
eYFP-Mad1 fluor (bottom); up to 6 evenly-spaced monitoring timepoints across mitosis, fluor read from
the RAW in-focus plane with ONE shared lo/hi exposure over the whole strip (uniform exposure).
Ported verbatim from group5_mad1_examples.py (monitoring_portion + fluor-crop helpers), PINNED to the
batch read from data/<id>.csv. Imports ONLY lib (styling) + ts_render (timestrip primitives). Honors
KTFIG_OUT for scratch verification (default = the real group4/ path).
"""
import sys, os; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import glob, csv, json, re, numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter
import lib, ts_render

FIGID = "G5_mad1_timestrip_20260304_Mad1_timelapse_1_xy6"
DATACSV = f"/Volumes/4 MB/ablation_plots/data/{FIGID}.csv"
# batch from the figure's own provenance CSV (column `batch`)
with open(DATACSV) as f:
    BATCH = next(csv.DictReader(f))["batch"].strip()
NOTE = "Mad1 through mitosis"
OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except: return 0.062

def clean_title(s):
    s = re.sub(r'(?i)(pro)?(meta|ana)phase', '', s)
    return re.sub(r'_+', '_', s).strip('_ ')

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

GAMMA = 0.6
def _stretch_green(plane, lo_p=50, hi_p=99.8, gamma=GAMMA, lo=None, hi=None):
    a = plane.astype(np.float32)
    if lo is None: lo = np.percentile(a, lo_p)
    if hi is None: hi = np.percentile(a, hi_p)
    n = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    if gamma != 1.0: n = np.power(n, gamma)
    g8 = (n * 255).astype(np.uint8)
    green = np.zeros((*g8.shape, 3), np.uint8); green[..., 1] = g8
    return green
def raw_fluor_plane(b, role, t, tol=0.2):
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
            cand = [i for i in idxs if 0 <= i < n] or [min(max(idxs[0], 0), n - 1)]
            best, bv = cand[0], -1.0
            for i in cand:
                v = float(tf.pages[i].asarray().astype(np.float32).var())
                if v > bv: bv, best = v, i
            return tf.pages[best].asarray().astype(np.float32)
    except Exception:
        return None
HI_PCT = 99.7; LO_PCT = 65.0
def strip_fluor_limits(b, role, times, tol=0.2, lo_p=LO_PCT, hi_p=HI_PCT):
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes

def fluor_crop(b, as_pts=False):
    fj = fjson(b); d = render_dir(b)
    if not fj or not d: return None
    fr0 = (role_frames(b, "ablation") or role_frames(b, "monitoring"))
    if not fr0: return None
    fr0 = fr0[0]
    fpath = f"{d}/{b}_Fluor_Cropped.tif"
    plane = None
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
    return None
def fluor_tight_crop(b, margin=1.12):
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)
def std_crop(b): return fluor_tight_crop(b)

def monitoring_portion(b, crop, ncols=6):
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return None
    mcrop = crop
    fluor_ts = [float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None]
    src = fluor_ts if fluor_ts else list(tsm)
    uniq = []; seen = set()
    for t in src:
        r = round(float(t), 1)
        if r in seen: continue
        seen.add(r); uniq.append(float(t))
    sel = [uniq[i] for i in np.linspace(0, len(uniq) - 1, min(ncols, len(uniq))).astype(int)]
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", ""))
    at = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    def plab(t):
        if mt is not None and abs(t - mt) <= 30: return "metaphase"
        if at is not None and abs(t - at) <= 30: return "anaphase"
        return None
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": plab(t)} for t in sel]
    cap = movie(b, "Phase", "Monitoring")
    if cap:
        for ci, t in enumerate(sel):
            fr = grab(cap, tsm, t)
            if fr is None: continue
            fr = fr.copy()
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            panels[ci]["phase"] = fr
        cap.release()
    capf = movie(b, "Fluor", "Monitoring")
    mon_lo, mon_hi, mplanes = strip_fluor_limits(b, "monitoring", sel)
    for ci, t in enumerate(sel):
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
    eff = ps(b)
    return ts_render.assemble(mpan, eff, 5.0, chan_labels=("Phase", "eYFP-Mad1"), fluor_only=False)

b = BATCH
d = render_dir(b)
assert d, f"no render dir for {b}"
crop = fluor_tight_crop(b) or fluor_crop(b)
mon = monitoring_portion(b, crop)
assert mon, f"no monitoring portion for {b}"
portions = [("monitoring", mon[0], mon[1])]
stem = f"G5_mad1_timestrip_{b.replace(' ', '_')}"
ok = ts_render.emit(portions, f"{OUT}/{stem}", title=f"Mad1 timelapse — {clean_title(b)}")
print(f"mad1 timestrip {b}: {len(portions)} portions {'ok' if ok else 'FAIL'} -> {OUT}/{stem}.png")
