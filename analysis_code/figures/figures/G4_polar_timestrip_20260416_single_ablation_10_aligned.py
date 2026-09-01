# 2026-08-16 (NOTES §1 rule 30): red marker on a GREEN fluorescence panel is the forbidden pair.
# Ablation-site circles are MAGENTA (255,0,255) BGR. Found by a pixel audit of the RENDERED figures
# after a first sweep missed these files.
#!/usr/bin/env python3
"""Standalone 1:1:1 rebuild of ONE figure: G4_polar_timestrip_20260416_single_ablation_10_aligned (single ablation; sisterless KT at the metaphase plate the whole rest of mitosis; ALIGNED square-crop variant).

Polar-chromosome sisterless timestrip (single sisterless-KT; polar KT persists until anaphase).
Composites the source-movie frames of batch "20250403 ptk_yfpcdc20_22" (render dir ->
*_frames.json -> Phase/Fluor Ablation+Monitoring mp4s) into an ablation strip (before / marked
red-CIRCLE / after) + one ablation zoom close-up per event + a monitoring strip, phase(top)+fluor.

Ported (pinned to this single batch, NON-aligned base variant) from group4_polar_timestrips.py;
imports ONLY the shared ts_render primitives + lib styling — no other figure's builder/logic.
Ablation markers come from frames.json ablation_events_local (render_xy = x_px-roi.x). Honors
KTFIG_OUT to redirect output to a scratch dir for verification (default = the real group4/ path);
in scratch mode a local savefig guard writes the editable SVG next to the scratch PNG and SKIPS the
fixed real _ai_relink/pdf so no real artifact is touched.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import glob, os, json, numpy as np, cv2
from collections import defaultdict
import lib, ts_render

BATCH = "20260416 single ablation_10"
KIND = "plate_whole"
ID = "G4_polar_timestrip_20260416_single_ablation_10_aligned"
ALIGNED = True

FIG = "/Volumes/4 MB/ablation_figures_20260625"
OUT = os.environ.get("KTFIG_OUT", f"{FIG}/group4"); os.makedirs(OUT, exist_ok=True)
SCRATCH = bool(os.environ.get("KTFIG_OUT"))

# --- scratch-only savefig guard: write PNG + editable SVG next to it, but NOT the fixed real relink PDF ---
if SCRATCH:
    from matplotlib.figure import Figure as _Fig
    _orig = _Fig.savefig
    def _wrap(self, fname, *a, **k):
        r = _orig(self, fname, *a, **k)
        try:
            if isinstance(fname, str) and fname.lower().endswith(".png"):
                _base = os.path.basename(fname)[:-4]; _k = {kk: vv for kk, vv in k.items() if kk != "dpi"}
                ad = os.path.join(os.path.dirname(fname), "illustrator"); os.makedirs(ad, exist_ok=True)
                _orig(self, os.path.join(ad, _base + ".svg"), *a, **_k)
        except Exception: pass
        return r
    _wrap._svgwrap = True; _Fig.savefig = _wrap   # marked so lib.apply_style() won't re-wrap (skips relink pdf)

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", ""))
    except: return 0.062

# ---- manual cell outlines (abl / mon) for the crop box ----
oc = list(__import__("csv").reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ox = {c: i for i, c in enumerate(oc[0])}
mon_outlines = defaultdict(list); abl_outlines = defaultdict(list)
for r in oc[1:]:
    ph = r[ox['phase']]
    if ph not in ('mon', 'abl'): continue
    try:
        _p = (float(r[ox['t_sec']]), np.array(json.loads(r[ox['points']]), np.int32))
        (abl_outlines if ph == 'abl' else mon_outlines)[r[ox['batch']].strip()].append(_p)
    except: pass

# ---- render-dir index -> frames.json -> role timestamps / ablation events / movie frames ----
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
def role_ts(b, role):
    fj = fjson(b)
    if not fj: return None
    ts = [f['t_sec'] for f in fj['frames'] if f['role'] == role]
    return np.array(ts) if ts else None
def abl_events(b):
    fj = fjson(b)
    if not fj: return []
    roi = fj.get("roi") or {"x": 0, "y": 0}; out = []
    for e in fj.get("ablation_events_local", []):
        try: out.append((e["x_px"] - roi.get("x", 0), e["y_px"] - roi.get("y", 0)))
        except: pass
    return out
def movie(b, ch, role):
    d = render_dir(b)
    if not d: return None
    mp4 = f"{d}/{b}_{ch}_{role}.mp4"
    if not os.path.isfile(mp4): return None
    cap = cv2.VideoCapture(mp4)
    if int(cap.get(7)) < 1: cap.release(); return None
    return cap
def grab(cap, ts, t):
    fi = int(np.argmin(np.abs(ts - t))); cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, fr = cap.read(); return fr if ok else None
def _is_dark(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
    return float(np.percentile(g, 99.5)) < 12

def phase_tif_frame(b, role, t):
    d = render_dir(b)
    if not d: return None
    p = f"{d}/{b}_Phase_Cropped.tif"
    if not os.path.isfile(p): return None
    fj = fjson(b)
    if not fj: return None
    cand = [f for f in fj["frames"] if f["role"] == role and f.get("phase_tif_idx") is not None] \
        or [f for f in fj["frames"] if f.get("phase_tif_idx") is not None]
    if not cand: return None
    f = min(cand, key=lambda z: abs(z["t_sec"] - t)); idx = int(f["phase_tif_idx"])
    import tifffile
    with tifffile.TiffFile(p) as tf:
        idx = min(idx, len(tf.pages) - 1); a = tf.pages[idx].asarray().astype(np.float32)
    lo, hi = np.percentile(a, 1), np.percentile(a, 99.5)
    if hi - lo < 4: return None
    g8 = np.clip((a - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    return cv2.cvtColor(g8, cv2.COLOR_GRAY2BGR)

def get_abl_frame(b, ch, cap, ts, t):
    fr = grab(cap, ts, t) if cap is not None else None
    if ch == "Phase" and (fr is None or _is_dark(fr)):
        alt = phase_tif_frame(b, "ablation", t)
        if alt is not None: fr = alt
    return fr

def crop_box(b):
    abl = sorted(abl_outlines.get(b, []), key=lambda p: abs(p[0]))
    if abl:
        pts = abl[0][1]; x0, y0 = pts.min(0); x1, y1 = pts.max(0); m = 40
    else:
        outs = mon_outlines.get(b, [])
        if not outs: return None
        allp = np.vstack([p for _, p in outs]); x0, y0 = allp.min(0); x1, y1 = allp.max(0); m = 24
    cap = movie(b, "Phase", "Monitoring") or movie(b, "Phase", "Ablation") or movie(b, "Fluor", "Monitoring")
    if not cap: return None
    W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
    return (max(0, int(x0 - m)), max(0, int(y0 - m)), min(W, int(x1 + m)), min(H, int(y1 + m)))

def std_crop(b):
    abl = sorted(abl_outlines.get(b, []), key=lambda p: abs(p[0])); mon = sorted(mon_outlines.get(b, []), key=lambda p: p[0])
    ref = (abl[0][1] if abl else (mon[0][1] if mon else None))
    if ref is None: return None
    cap = movie(b, "Phase", "Monitoring") or movie(b, "Phase", "Ablation") or movie(b, "Fluor", "Monitoring")
    if not cap: return None
    W = int(cap.get(3)); H = int(cap.get(4)); cap.release()
    return ts_render.tight_square(np.asarray(ref, float), W, H, batch=b)

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

def ablation_portion(b, crop, aligned=False, sq=None):
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b)
    t_first = float(tsa.min()); t_last = float(tsa.max())
    tm = nonflash_t(b, "ablation", t_first)
    i = int(np.argmin(np.abs(tsa - tm))); tb = float(tsa[max(0, i - 1)]); ta = float(tsa[min(len(tsa) - 1, i + 1)])
    if ta <= tm: ta = t_last
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
    mcrop = sq if aligned else crop
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    R = None
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        if cap is None and ch == "Fluor": continue
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            fr = get_abl_frame(b, ch, cap, tsa, t)
            if fr is None: continue
            fr = fr.copy()
            if mk:
                r = R or max(9, int(0.011 * fr.shape[1]))
                for (x, y) in evs: cv2.circle(fr, (int(round(x)), int(round(y))), r, (255, 0, 255), 2, cv2.LINE_AA)
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            wide[ci][key] = fr
        if cap is not None: cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 10.0, fluor_only=True)
    if res: portions.append(("ablation", res[0], res[1]))
    HALF = ts_render.zoom_half_px(ps(b)) if aligned else 60; ZOOM = 3
    zoom_portions = []
    for ei, (ex, ey) in enumerate(evs[:3]):
        cu = [{"t": t, "phase": None, "fluor": None} for (_, t, _) in times]
        for ch in ("Phase", "Fluor"):
            cap = movie(b, ch, "Ablation")
            if cap is None and ch == "Fluor": continue
            key = "phase" if ch == "Phase" else "fluor"
            for ci, (tag, t, mk) in enumerate(times):
                fr = get_abl_frame(b, ch, cap, tsa, t)
                if fr is None: continue
                if aligned:
                    z = ts_render.zoom_to_square(fr, ex, ey, HALF, mk)
                    if z is not None: cu[ci][key] = z
                else:
                    xi, yi = int(round(ex)), int(round(ey)); h, wd = fr.shape[:2]
                    x0, y0 = max(0, xi - HALF), max(0, yi - HALF); x1, y1 = min(wd, xi + HALF), min(h, yi + HALF)
                    sub = fr[y0:y1, x0:x1].copy()
                    if sub.size == 0: continue
                    if mk: cv2.circle(sub, (xi - x0, yi - y0), 9, (255, 0, 255), 2, cv2.LINE_AA)
                    cu[ci][key] = cv2.resize(sub, (sub.shape[1] * ZOOM, sub.shape[0] * ZOOM), interpolation=cv2.INTER_NEAREST)
            if cap is not None: cap.release()
        zeff = ps(b) * (2 * HALF) / ts_render.ALIGN_N if aligned else ps(b) / ZOOM
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None], zeff, 2.0, fluor_only=True, show_fmt=False)
        if res: zoom_portions.append((f"ablation close-up {ei + 1}", res[0], res[1]))
    return portions + zoom_portions

def monitoring_portion(b, crop, aligned=False, sq=None):
    outs = sorted(mon_outlines.get(b, []), key=lambda x: x[0])
    tsm = role_ts(b, "monitoring")
    if not outs or tsm is None: return None
    mcrop = sq if aligned else crop
    idxs = np.linspace(0, len(outs) - 1, min(6, len(outs))).astype(int)
    sel = [outs[i][0] for i in idxs]
    mt = lib.parse_time(mr.get(b, {}).get("Metaphase Start (s)", "")); at = lib.parse_time(mr.get(b, {}).get("Anaphase Onset (s)", ""))
    def plab(t):
        if mt is not None and abs(t - mt) <= 20: return "metaphase"
        if at is not None and abs(t - at) <= 20: return "anaphase"
        return None
    panels = [{"t": t, "phase": None, "fluor": None, "phase_label": plab(t)} for t in sel]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Monitoring")
        if not cap: continue
        key = "phase" if ch == "Phase" else "fluor"
        for ci, t in enumerate(sel):
            fr = grab(cap, tsm, t)
            if fr is None: continue
            fr = fr.copy()
            if mcrop: fr = ts_render.crop_pad(fr, mcrop).copy()
            panels[ci][key] = fr
        cap.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if aligned and mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N if sq else ps(b)
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, fluor_only=False)

# ================= build ONLY this figure =================
assert render_dir(BATCH), f"no render dir for {BATCH}"
crop = std_crop(BATCH) or crop_box(BATCH)
if ALIGNED:
    sq = std_crop(BATCH)
    assert sq is not None, f"{ID}: no outline -> cannot build aligned variant"
    portions = ablation_portion(BATCH, crop, aligned=True, sq=sq)
    mon = monitoring_portion(BATCH, crop, aligned=True, sq=sq)
else:
    portions = ablation_portion(BATCH, crop)
    mon = monitoring_portion(BATCH, crop)
if mon: portions.append(("monitoring", mon[0], mon[1]))
assert portions, f"{ID}: no portions"
title = (f"Polar timestrip (aligned square crop) — {KIND} — {BATCH}" if ALIGNED
         else f"Polar timestrip — {KIND} — {BATCH}")
ok = ts_render.emit(portions, f"{OUT}/{ID}", title=title)
print(f"{ID}: {len(portions)} portions {'ok' if ok else 'FAIL'} -> {OUT}/{ID}.png")
