# 2026-08-16 (NOTES §1 rule 30): red marker on a GREEN fluorescence panel is the forbidden pair.
# Ablation-site circles are MAGENTA (255,0,255) BGR. Found by a pixel audit of the RENDERED figures
# after a first sweep missed these files.
#!/usr/bin/env python3
"""RETIRED 2026-08-03 (feedback item A / 2026-07-30 review item 28) -- DO NOT RUN.
This script's own CHANNEL LABEL FIX below (from an earlier deep-QA pass) already correctly identified
`20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52` as an eYFP-Cdc20 cell, not Mad1 -- but the shared
group5_mad1_examples.py builder was never updated to match and kept mislabelling it "eYFP-Mad1" until this
session (see her feedback + lib.is_mad1() docstring). Fixed at the source now: the batch is REMOVED from
group5_mad1_examples.py's TIMESTRIP_BATCHES (it belongs to the cdc20 cohort, not any Mad1 figure), and its
stale mislabelled PNG/SVG/PDF artifacts were retired to
`_retired/G5_mad1_timestrip_52_reassigned_cdc20_20260803/`. This dedicated one-off builder is kept for
provenance only -- running it would recreate a "Mad1 timestrip" figure for a cdc20 cell, which is exactly
the bug being fixed. If a properly-labelled cdc20 example of this cell is wanted later, it belongs in a
cdc20/group1-4 builder, not here.

Original docstring follows, unmodified, for reference:

Dedicated 1:1:1 builder for ONE figure:
   G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52  (Mad1-series ablation timestrip).

Rebuilds ONLY this cell's timestrip by compositing its source-movie frames per the provenance CSV
(data/<id>.csv -> batch -> *_frames.json -> Fluor/Phase mp4 + raw Fluor_Cropped.tif), using the SHARED
ts_render primitives + lib styling ONLY (no other figure's builder logic). Helper functions are ported
verbatim from group5_mad1_examples.py, pinned to this single batch (base, NON-aligned strip).

CHANNEL LABEL FIX (deep-QA, dim=provenance/units): this is the *Eyfpcdc2* line, i.e. the eYFP is fused to
Cdc20 (eYFP-Cdc20), NOT Mad1. The shared builder hardcodes the fluor label as "eYFP-Mad1" for EVERY Mad1-
series batch, which is wrong for this cell. The 488 fluor here reports Cdc20 localisation, so this dedicated
script labels the fluor channel "eYFP-Cdc20". (A cell cannot express eYFP on both Cdc20 and Mad1.) See
reference_mad1_if_channel_markers: ablation 488 = eYFP-Cdc20.

Honors $KTFIG_OUT (scratch override); default = the real group4/ path. In scratch mode a PNG-only savefig
wrapper is pre-installed so lib's Illustrator wrapper does NOT overwrite the fixed drive SVG/relink-PDF paths.
"""
import sys, os, glob, json, re
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, cv2, tifffile
from scipy.ndimage import gaussian_filter
import matplotlib; matplotlib.use("Agg")
from matplotlib.figure import Figure as _Fig
import lib, ts_render

ID = "G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52"
DATA_CSV = f"/Volumes/4 MB/ablation_plots/data/{ID}.csv"
FLUOR_LABEL = "eYFP-Cdc20"   # <-- Eyfpcdc2 line; corrected from the builder's hardcoded "eYFP-Mad1"
SCRATCH = bool(os.environ.get("KTFIG_OUT"))
OUT = os.environ.get("KTFIG_OUT", "/Volumes/4 MB/ablation_figures_20260625/group4"); os.makedirs(OUT, exist_ok=True)

# In scratch/verification mode, block lib's savefig wrapper (which ALSO writes a PDF to a FIXED drive path
# /Volumes/4 MB/.../_ai_relink/pdf/<base>.pdf and an illustrator/<base>.svg) from clobbering drive artifacts.
if SCRATCH and not getattr(_Fig.savefig, "_svgwrap", False):
    _origsave = _Fig.savefig
    def _png_only(self, fname, *a, **k):
        return _origsave(self, fname, *a, **k)   # write only what's requested (the scratch PNG)
    _png_only._svgwrap = True; _Fig.savefig = _png_only

# ---- provenance: the batch is read from this figure's own CSV (single-column `batch`) ----
def load_batch():
    import csv
    with open(DATA_CSV) as f:
        rows = [r for r in csv.DictReader(f) if r.get("batch")]
    assert len(rows) == 1, f"expected exactly one batch in {DATA_CSV}, got {len(rows)}"
    return rows[0]["batch"].strip()
BATCH = load_batch()

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except: return 0.062

def clean_title(s):
    s = re.sub(r'(?i)(pro)?(meta|ana)phase', '', s)
    return re.sub(r'_+', '_', s).strip('_ ')

# ---- render-dir index (same rule as the builder: first *_frames.json dir per basename, skip archives) ----
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
    raw = fj.get("ablation_events_local", [])
    t0 = float(raw[0]["epoch_ms"]) if raw else 0.0
    out = []
    for e in raw:
        try: out.append((e["x_px"] - roi.get("x", 0), e["y_px"] - roi.get("y", 0),
                         (float(e["epoch_ms"]) - t0) / 1000.0))
        except: pass
    return out
def refine_ablation_xy(b, ex, ey, te, sat=15000, R=55):
    d = render_dir(b)
    if not d: return ex, ey
    fp = f"{d}/{b}_Fluor_Cropped.tif"
    frs = role_frames(b, "ablation")
    if not frs or not os.path.isfile(fp): return ex, ey
    ts = np.array([f["t_sec"] for f in frs]); fi = int(np.argmin(np.abs(ts - te)))
    idx = frs[fi].get("fluor_tif_idx")
    if idx is None: return ex, ey
    try:
        with tifffile.TiffFile(fp) as tf:
            pl = tf.pages[min(int(idx), len(tf.pages)-1)].asarray().astype(np.float32)
    except Exception:
        return ex, ey
    H, W = pl.shape; xi, yi = int(round(ex)), int(round(ey))
    x0, x1 = max(0, xi-R), min(W, xi+R); y0, y1 = max(0, yi-R), min(H, yi+R)
    sub = pl[y0:y1, x0:x1]
    if sub.size == 0 or float(sub.max()) < sat: return ex, ey
    m = sub >= 0.5*sub.max(); ys, xs = np.where(m)
    return x0 + float(xs.mean()), y0 + float(ys.mean())

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
            cand = [i for i in idxs if 0 <= i < n] or [min(max(idxs[0], 0), n-1)]
            best, bv = cand[0], -1.0
            for i in cand:
                v = float(tf.pages[i].asarray().astype(np.float32).var())
                if v > bv: bv, best = v, i
            return tf.pages[best].asarray().astype(np.float32)
    except Exception:
        return None
def raw_fluor(b, role, t, tol=0.2, lo=None, hi=None):
    p = raw_fluor_plane(b, role, t, tol)
    return _stretch_green(p, lo=lo, hi=hi) if p is not None else None

HI_PCT = 99.7; LO_PCT = 65.0
def strip_fluor_limits(b, role, times, tol=0.2, lo_p=LO_PCT, hi_p=HI_PCT):
    planes = [raw_fluor_plane(b, role, t, tol) for t in times]
    valid = [p for p in planes if p is not None]
    if not valid: return None, None, planes
    allpx = np.concatenate([p.ravel() for p in valid])
    return float(np.percentile(allpx, lo_p)), float(np.percentile(allpx, hi_p)), planes

# ---- crop estimated from FLUORESCENCE / brightfield of the centred cell ----
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
        plane = (stk[min(idx, stk.shape[0]-1)] if stk.ndim == 3 else np.squeeze(stk)).astype(np.float32)
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
    r = fluor_crop(b, as_pts=True)
    if r is None: return None
    pts, W, H = r
    return ts_render.tight_square(pts, W, H, margin=margin, batch=b)

# ---- ablation portion (before / red-circle marked / after) + zoom close-ups ----
def clean_abl_times(tsa, ev_ts, t_center, win=1.6):
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

def ablation_portion(b, crop, aligned=False, sq=None):
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b); t_first = float(tsa.min())
    ev_ts = [te for (_, _, te) in evs]
    t_prim = float(ev_ts[0]) if ev_ts else t_first
    tb, tm, ta = clean_abl_times(tsa, ev_ts, t_prim)
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
    now_evs = [refine_ablation_xy(b, x, y, te) for (x, y, te) in evs if abs(te - tm) <= 3.0]
    if not now_evs and evs: now_evs = [refine_ablation_xy(b, evs[0][0], evs[0][1], evs[0][2])]
    mcrop = sq if aligned else crop
    abl_lo, abl_hi, _ = strip_fluor_limits(b, "ablation", [t for (_, t, _) in times])
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            fr = raw_fluor(b, "ablation", t, lo=abl_lo, hi=abl_hi) if key == "fluor" else None
            if fr is None:
                if cap is None: continue
                fr = grab(cap, tsa, t)
                if fr is None: continue
                fr = fr.copy()
            if mk:
                r = max(9, int(0.011 * fr.shape[1]))
                for (x, y) in now_evs: cv2.circle(fr, (int(round(x)), int(round(y))), r, (255, 0, 255), 2, cv2.LINE_AA)
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            wide[ci][key] = fr
        if cap: cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 5.0, chan_labels=("Phase", FLUOR_LABEL), fluor_only=True)
    if res: portions.append(("ablation", res[0], res[1]))
    HALF = ts_render.zoom_half_px(ps(b)) if aligned else 60; ZOOM = 3
    for ei, (ex, ey, te) in enumerate(evs[:2]):
        ex, ey = refine_ablation_xy(b, ex, ey, te)
        ztb, ztm, zta = clean_abl_times(tsa, ev_ts, te)
        zt = [("before", ztb, False), ("ablation", ztm, True), ("after", zta, False)]
        cu = [{"t": t, "phase": None, "fluor": None} for (_, t, _) in zt]
        for ch in ("Phase", "Fluor"):
            cap = movie(b, ch, "Ablation")
            key = "phase" if ch == "Phase" else "fluor"
            for ci, (tag, t, mk) in enumerate(zt):
                fr = raw_fluor(b, "ablation", t, lo=abl_lo, hi=abl_hi) if key == "fluor" else None
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
                    if mk: cv2.circle(sub, (xi-x0, yi-y0), 9, (255, 0, 255), 2, cv2.LINE_AA)
                    cu[ci][key] = cv2.resize(sub, (sub.shape[1]*ZOOM, sub.shape[0]*ZOOM), interpolation=cv2.INTER_NEAREST)
            if cap: cap.release()
        zeff = ps(b)*(2*HALF)/ts_render.ALIGN_N if aligned else ps(b)/ZOOM
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None],
                                 zeff, 2.0, chan_labels=("Phase", FLUOR_LABEL), fluor_only=True, show_fmt=False)
        if res: portions.append((f"ablation close-up {ei+1}", res[0], res[1]))
    return portions

def monitoring_portion(b, crop, ncols=6, aligned=False, sq=None):
    tsm = role_ts(b, "monitoring")
    if tsm is None or len(tsm) == 0: return None
    mcrop = sq if aligned else crop
    fluor_ts = [float(f["t_sec"]) for f in role_frames(b, "monitoring") if f.get("fluor_tif_idx") is not None]
    src = fluor_ts if fluor_ts else list(tsm)
    uniq = []; seen = set()
    for t in src:
        r = round(float(t), 1)
        if r in seen: continue
        seen.add(r); uniq.append(float(t))
    sel = [uniq[i] for i in np.linspace(0, len(uniq)-1, min(ncols, len(uniq))).astype(int)]
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
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b)*(sq[2]-sq[0])/ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 5.0, chan_labels=("Phase", FLUOR_LABEL), fluor_only=False)

# ================= build THIS batch's base (non-aligned) timestrip =================
def main():
    b = BATCH
    d = render_dir(b)
    assert d, f"no render dir for {b}"
    crop = fluor_tight_crop(b) or fluor_crop(b)
    portions = ablation_portion(b, crop)
    mon = monitoring_portion(b, crop)
    if mon: portions.append(("monitoring", mon[0], mon[1]))
    assert portions, f"no portions for {b}"
    ok = ts_render.emit(portions, f"{OUT}/{ID}", title=f"Mad1 timelapse — {clean_title(b)}")
    if not SCRATCH:
        lib.record_plot(ID, ["batch"], [[b]],
            {"type": "Mad1 example timestrip", "has_ablation": True,
             "crop": [int(v) for v in crop] if crop else None, "n_portions": len(portions),
             "fluor_channel": FLUOR_LABEL}, __file__, f"Mad1 timestrip example ({b})")
    print(f"{ID}: {len(portions)} portions {'ok' if ok else 'FAIL'} -> {OUT}/{ID}.png")

if __name__ == "__main__":
    main()
