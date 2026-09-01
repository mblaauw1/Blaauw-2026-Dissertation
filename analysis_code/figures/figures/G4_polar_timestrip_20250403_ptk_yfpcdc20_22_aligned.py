# 2026-08-16 (NOTES §1 rule 30): red marker on a GREEN fluorescence panel is the forbidden pair.
# Ablation-site circles are MAGENTA (255,0,255) BGR. Found by a pixel audit of the RENDERED figures
# after a first sweep missed these files.
#!/usr/bin/env python3
"""Standalone 1:1:1 rebuild of ONE figure: G4_polar_timestrip_20250403_ptk_yfpcdc20_22_aligned.

The ALIGNED-CROP variant of the polar-chromosome timestrip for batch "20250403 ptk_yfpcdc20_22"
(single sisterless-KT; polar KT persists until anaphase). Aligned = ablation strip + ablation zoom
close-up(s) + monitoring strip all share ONE fixed square footprint (ts_render.ALIGN_N) cropped from
the cell's TIGHT square window (ts_render.tight_square on the MANUAL ablation outline) so every tile
renders at the same magnification and stacks in aligned columns.

Ported from group4_polar_timestrips.py (the `_aligned` block only), pinned to this one batch. Imports
ONLY ts_render primitives + lib styling — never another figure's builder. Ablation markers come from
frames.json ablation_events_local (render_xy = x_px - roi.x). Ablation strips are FLUOR-ONLY (no phase,
per 07-09 feedback); monitoring is phase + fluor. Honors $KTFIG_OUT for the output dir.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, glob, json, csv, numpy as np, cv2, tifffile
from collections import defaultdict
import lib, ts_render

BATCH = "20250403 ptk_yfpcdc20_22"
KIND  = "persists"
ID    = f"G4_polar_timestrip_{BATCH.replace(' ','_')}_aligned"
OUT   = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group4"
os.makedirs(OUT, exist_ok=True)

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def ps(b):
    try: return float(mr.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    except Exception: return 0.062

# ---- render dir (this batch's *_frames.json), skipping archives/backups ----
def _find_render_dir(b):
    for fj in glob.glob("/Volumes/4 MB/**/%s_frames.json" % b, recursive=True):
        if "_ARCHIVED" in fj or "backup" in fj.lower(): continue
        return os.path.dirname(fj)
    return None
RDIR = _find_render_dir(BATCH)

def fjson(b):
    if RDIR and os.path.isfile(f"{RDIR}/{b}_frames.json"): return json.load(open(f"{RDIR}/{b}_frames.json"))
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
        except Exception: pass
    return out
def movie(b, ch, role):
    if not RDIR: return None
    mp4 = f"{RDIR}/{b}_{ch}_{role}.mp4"
    if not os.path.isfile(mp4): return None
    cap = cv2.VideoCapture(mp4)
    if int(cap.get(7)) < 1: cap.release(); return None
    return cap
def grab(cap, ts, t):
    fi = int(np.argmin(np.abs(ts - t))); cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, fr = cap.read()
    return fr if ok else None
def _is_dark(fr):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if fr.ndim == 3 else fr
    return float(np.percentile(g, 99.5)) < 12

# ---- manual outlines for THIS batch ----
oc = list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv"))); ox = {c: i for i, c in enumerate(oc[0])}
mon_outlines = defaultdict(list); abl_outlines = defaultdict(list)
for r in oc[1:]:
    if r[ox['batch']].strip() != BATCH: continue
    ph = r[ox['phase']]
    if ph not in ('mon', 'abl'): continue
    try:
        _p = (float(r[ox['t_sec']]), np.array(json.loads(r[ox['points']]), np.int32))
        (abl_outlines if ph == 'abl' else mon_outlines)[BATCH].append(_p)
    except Exception: pass

def phase_tif_frame(b, role, t):
    if not RDIR: return None
    p = f"{RDIR}/{b}_Phase_Cropped.tif"
    if not os.path.isfile(p): return None
    fj = fjson(b)
    if not fj: return None
    cand = [f for f in fj["frames"] if f["role"] == role and f.get("phase_tif_idx") is not None] \
           or [f for f in fj["frames"] if f.get("phase_tif_idx") is not None]
    if not cand: return None
    f = min(cand, key=lambda z: abs(z["t_sec"] - t)); idx = int(f["phase_tif_idx"])
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

def std_crop(b):
    """TIGHT exactly-square crop (ts_render.tight_square) from THIS cell's first ablation outline (fallback
    first monitoring outline) so the cell fills ~89% of the frame; forced square -> uniform resize."""
    abl = sorted(abl_outlines.get(b, []), key=lambda p: abs(p[0]))
    mon = sorted(mon_outlines.get(b, []), key=lambda p: p[0])
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

def ablation_portion(b, sq):
    """Aligned ablation strip (fluor-only) + one zoom close-up per event (cap 3). Main tiles cropped to the
    fixed square `sq` window + resampled to ts_render.ALIGN_N; zoom uses a fixed-µm half window."""
    tsa = role_ts(b, "ablation")
    if tsa is None or len(tsa) == 0: return []
    evs = abl_events(b)
    t_first = float(tsa.min()); t_last = float(tsa.max())
    tm = nonflash_t(b, "ablation", t_first)
    i = int(np.argmin(np.abs(tsa - tm))); tb = float(tsa[max(0, i - 1)]); ta = float(tsa[min(len(tsa) - 1, i + 1)])
    if ta <= tm: ta = t_last
    times = [("before", tb, False), ("ablation", tm, True), ("after", ta, False)]
    wide = [{"t": t, "phase": None, "fluor": None, "phase_label": None} for (_, t, _) in times]
    for ch in ("Phase", "Fluor"):
        cap = movie(b, ch, "Ablation")
        if cap is None and ch == "Fluor": continue
        key = "phase" if ch == "Phase" else "fluor"
        for ci, (tag, t, mk) in enumerate(times):
            fr = get_abl_frame(b, ch, cap, tsa, t)
            if fr is None: continue
            fr = fr.copy()
            if mk:
                r = max(9, int(0.011 * fr.shape[1]))
                for (x, y) in evs: cv2.circle(fr, (int(round(x)), int(round(y))), r, (255, 0, 255), 2, cv2.LINE_AA)
            fr = ts_render.crop_pad(fr, sq).copy()
            wide[ci][key] = fr
        if cap is not None: cap.release()
    portions = []
    mpan = [p for p in wide if p["phase"] is not None or p["fluor"] is not None]
    if mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N
    else:
        eff = ps(b)
    res = ts_render.assemble(mpan, eff, 10.0, fluor_only=True)
    if res: portions.append(("ablation", res[0], res[1]))
    HALF = ts_render.zoom_half_px(ps(b))
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
                z = ts_render.zoom_to_square(fr, ex, ey, HALF, mk)
                if z is not None: cu[ci][key] = z
            if cap is not None: cap.release()
        zeff = ps(b) * (2 * HALF) / ts_render.ALIGN_N
        res = ts_render.assemble([p for p in cu if p["phase"] is not None or p["fluor"] is not None],
                                 zeff, 2.0, fluor_only=True, show_fmt=False)
        if res: zoom_portions.append((f"ablation close-up {ei + 1}", res[0], res[1]))
    return portions + zoom_portions

def monitoring_portion(b, sq):
    """Aligned monitoring strip (phase + fluor): up to 6 evenly-spaced monitoring frames cropped to `sq`."""
    outs = sorted(mon_outlines.get(b, []), key=lambda x: x[0])
    tsm = role_ts(b, "monitoring")
    if not outs or tsm is None: return None
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
            fr = ts_render.crop_pad(fr.copy(), sq).copy()
            panels[ci][key] = fr
        cap.release()
    mpan = [p for p in panels if p["phase"] is not None or p["fluor"] is not None]
    if mpan:
        mpan = ts_render.resize_panels(mpan, ts_render.ALIGN_N)
        eff = ps(b) * (sq[2] - sq[0]) / ts_render.ALIGN_N
    else:
        eff = ps(b)
    return ts_render.assemble(mpan, eff, 10.0, fluor_only=False)

def main():
    if not RDIR:
        print(f"FAIL {ID}: no render dir for {BATCH}"); return
    sq = std_crop(BATCH)
    if sq is None:
        print(f"FAIL {ID}: no manual outline -> no aligned square crop"); return
    pA = ablation_portion(BATCH, sq)
    mA = monitoring_portion(BATCH, sq)
    if mA: pA.append(("monitoring", mA[0], mA[1]))
    if not pA:
        print(f"FAIL {ID}: no portions"); return
    ok = ts_render.emit(pA, f"{OUT}/{ID}", title=f"Polar timestrip (aligned square crop) — {KIND} — {BATCH}")
    print(f"{ID}: {len(pA)} portions -> {OUT}/{ID}.png {'ok' if ok else 'FAIL'}")

if __name__ == "__main__":
    main()
