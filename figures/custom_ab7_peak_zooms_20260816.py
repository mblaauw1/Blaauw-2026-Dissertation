#!/usr/bin/env python3
"""Artboard-7 peak zoom frames — 8 per trace panel, 48 in all.

USER 2026-08-16: "pick out 4 timepoints in each of those plots - two corresponding to peaks of the polar kt
plot and 2 corresponding to peaks of the plate kt plot that fall within the metaphase-to-anaphase range -
and go to those frames on those movies. the polar and plate kts that the plot uses for measurements will be
marked - so make zoom frames of each and place them with that individual plot on artboard 7. so there
should be 8 zoom frames for each of the 6 plots then (4 each of polar and plate chosen as directed)."

HOW THE CHOICES ARE MADE, so they can be argued with
  * PANEL -> BATCH comes from `kt_tension_withincell.both` (the builder's own ordered list). The recorded
    CSV's `panel` column truncates at 24 characters and several real batches collapse onto one key, so it
    must NOT be used for this — going to a frame in the wrong cell's movie is the failure mode here.
  * "PEAK" is defined, not eyeballed: scipy `find_peaks` with a prominence floor of 25% of that series'
    range, restricted to the metaphase->anaphase window, then the two highest-PROMINENCE maxima. Every
    chosen timepoint is printed so she can overrule any of them.
  * Both kinetochores are zoomed at each of the 4 timepoints -> 4 polar + 4 plate = 8 per panel.
  * Centred on HER marked kinetochores — the tracks the trace measures — never auto-detected
    (feedback_measure_at_her_marks_not_autodetect); nothing snapped or recentred (§1 rule 22).
  * Frames via the annotation `frame` through FluorTif.plane_by_frame, never t_sec
    (project_fluor_frame_mapping_bug).
  * Identical crop, scale and contrast across all 8 panels of a sheet; window clamped inside the frame,
    never padded (§1 rule 29); marks MAGENTA/CYAN, never red on green (§1 rule 30).
"""
import os, sys, csv, collections
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import kt_tension_withincell as W          # reuse its `both`, phase times and series construction

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
TRK  = f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv"
LOAD = f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"
OUT  = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

PANELS = [2, 3, 5, 9, 12, 15]          # the six __pN placed on artboard 7
# USER 2026-08-17: "its not zoomed in enough". A kinetochore is well under 1 um across, so a 5 um window
# rendered it as a speck in a field of background. 1.5 um half-width (3 um window) fills the tile with the
# kinetochore and its immediate surround, which is what a deformation panel has to show.

# ── USER 2026-08-18, item 19 ────────────────────────────────────────────────────────────────────
# "Crops can be tighter on kinetochore frames for kinetochore deformation. And to that point, for each
#  set of kinetochore frames showing kinetochore distortion, and frames showing k-k distances across
#  different samples, keep the scale constant so its easy to look from one to the next and compare."
# ONE constant is now shared by BOTH families (this file and the other one named below), so a panel from
# either can be compared directly against a panel from the other. The value is set by the widest sister
# pair that has to stay inside the frame: max k-k among the candidates is 2.41 um, so a 1.5 um half-width
# (3.0 um window) contains it with ~25% margin. That is also TIGHTER than the 1.6 um the k-k sheets used.
# Shared by: custom_ab7_peak_zooms_20260816.py and custom_kk_zoom_candidates_20260816.py.
SHARED_KT_HALF_UM = 1.5

HALF_UM = SHARED_KT_HALF_UM   # item 19: one scale for BOTH zoom families
BG_SIGMA = 0.8                         # px; keeps shot noise from swamping a faint punctum

# ---- series with FRAME kept, so a peak maps straight to an image -------------------------------
ser = collections.defaultdict(lambda: collections.defaultdict(list))   # batch -> label -> [(x_min, v, frame, track)]
for r in csv.DictReader(open(LOAD)):
    if r.get("in_window") != "1" or r.get("outlier") == "1": continue
    if r["label"] not in ("polar", "paired"): continue
    try:
        v = float(r["spindle_strain"]); fr = int(float(r["frame"]))
        x = W.tmeta(r["batch"], float(r["t_sec"]))
    except Exception:
        continue
    if x is None: continue
    ser[r["batch"]][r["label"]].append((x, v, fr, r["track_id"]))

pos = {}
for r in csv.DictReader(open(TRK)):
    try: pos[(r["batch"], r["track_id"], int(float(r["frame"])))] = (float(r["cx_px"]), float(r["cy_px"]))
    except Exception: continue

def peaks_two(pts, am):
    """Two highest-prominence maxima inside [0, anaphase]."""
    pts = sorted(p for p in pts if p[0] >= 0 and (am is None or p[0] <= am))
    if len(pts) < 3: return pts[:2]
    y = np.array([p[1] for p in pts], float)
    rng = float(y.max() - y.min())
    idx, props = find_peaks(y, prominence=max(rng * 0.25, 1e-9))
    if len(idx) == 0:
        return [pts[int(np.argmax(y))]]
    order = np.argsort(-props["prominences"])
    return [pts[idx[i]] for i in order[:2]]

def _stretch(pl, lo_hi=None):
    v = pl.astype(np.float32)
    lo, hi = (np.percentile(v, 20), np.percentile(v, 99.6)) if lo_hi is None else lo_hi
    return np.clip((v - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8), (lo, hi)

recs = []
for pn in PANELS:
    if pn - 1 >= len(W.both): continue
    b = W.both[pn - 1]
    am = W.ana_min(b)
    chosen = []
    for lab in ("polar", "paired"):
        for (x, v, fr, tid) in peaks_two(ser[b][lab], am):
            chosen.append((lab, x, v, fr, tid))
    if not chosen:
        print(f"  __p{pn} {b}: no peaks in window"); continue

    # 🔴 2026-08-17 — THE REASON THE PANELS SHOWED BACKGROUND INSTEAD OF KINETOCHORES: role="monitoring".
    # FRAME_CALIBRATION.csv stores the annotation-frame -> TIF-POSITION correspondence PER ROLE, and every
    # kinetochore annotation here is a monitoring-phase mark. Built with role=None the stack indexes across
    # ALL roles, so calibrated position 69 landed 26 pages away from the monitoring frame it names.
    # MEASURED on 20250417 ptk_yfpcdc20_3 frame 70: role=None -> page 60, signal at her marks 22 counts over
    # background; role="monitoring" -> page 86, 99 counts over background, and page 86 is the BEST page in
    # the whole 145-page stack. The plane is chosen by the calibration, not by which one looks best.
    ft = lib.FluorTif(b, role="monitoring")
    if not ft.ok():
        print(f"  __p{pn} {b}: no fluor stack"); continue
    px = 0.062
    half = int(round(HALF_UM / px)); box = 2 * half

    # ONE contrast stretch for the whole sheet (her rule 5: identical contrast, or a difference between
    # panels is just rendering) — but pooled over the actual CROP WINDOWS, not taken from a single
    # reference plane. Fluor intensity varies a lot frame to frame, and a stretch fitted to one plane blew
    # the brighter frames out to flat green on the first render.
    # 2026-08-17: pooling over whole PLANES spends the whole display range on background -- the punctum is
    # only ~10% above it -- which is the green static she saw. Pool over the CROPS instead, after removing
    # each crop's own camera offset (its median). Still ONE mapping for the whole sheet, so rule 5 holds.
    import scipy.ndimage as _nd
    def _crop_raw(pl, p):
        H_, W_ = pl.shape[:2]
        x0 = int(min(max(0, round(p[0] - half)), W_ - box)); y0 = int(min(max(0, round(p[1] - half)), H - box)) if False else int(min(max(0, round(p[1] - half)), H_ - box))
        c = _nd.gaussian_filter(pl[y0:y0 + box, x0:x0 + box].astype(np.float32), BG_SIGMA)
        return c - float(np.median(c)), x0, y0
    _pool = []
    for _l, _x, _v, fr, _t in chosen:
        pl = ft.plane_by_frame(fr)
        if pl is None: continue
        for _w in ("polar", "paired"):
            _cand = [t for (xx, vv, ff, t) in ser[b][_w] if ff == fr]
            _tr = _t if _w == _l else (_cand[0] if _cand else None)
            _p = pos.get((b, _tr, fr)) if _tr else None
            if _p is None: continue
            if pl.shape[1] < box or pl.shape[0] < box: continue
            _pool.append(_crop_raw(pl, _p)[0].ravel())
    if not _pool:
        print(f"  __p{pn} {b}: no planes"); continue
    _allpx = np.concatenate(_pool)
    lohi = (float(np.percentile(_allpx, 55)), float(np.percentile(_allpx, 99.5)))

    tiles = []
    for (lab, x, v, fr, tid) in chosen:
        pl = ft.plane_by_frame(fr)
        if pl is None: continue
        H, W_ = pl.shape[:2]
        if W_ < box or H < box: continue
        # at THIS timepoint show BOTH kinetochores: the peak's own track and the other label's track
        for want in ("polar", "paired"):
            tr = tid if want == lab else None
            if tr is None:
                cand = [t for (xx, vv, ff, t) in ser[b][want] if ff == fr]
                tr = cand[0] if cand else None
            p = pos.get((b, tr, fr)) if tr else None
            if p is None: continue
            _raw, x0, y0 = _crop_raw(pl, p)                        # clamp, never pad
            sub = np.clip((_raw - lohi[0]) / max(lohi[1] - lohi[0], 1e-6) * 255, 0, 255).astype(np.uint8)
            img = np.zeros((box, box, 3), np.uint8); img[..., 1] = sub
            # USER 2026-08-17: "right now you have circle markers around the kinetochores on the single
            # frames showing deformations in the kinetochores. dont add the circles. it blocks features of
            # the kinetochores, plus its zoomed on one kinetochore already."
            # NO MARKER AT ALL on these panels: the crop is centred on the kinetochore by construction and
            # the panel title already says which one it is (polar vs paired), so the ring only ever covered
            # the shape the panel exists to show. The polar/plate distinction stays in the TITLE.
            tiles.append((img, f"{want} @ {lab} peak\n{x:.1f} min · frame {fr}\ndistortion {v:.2f}"))
            recs.append([b, pn, lab, want, round(x, 3), fr, round(v, 4)])

    if not tiles: print(f"  __p{pn} {b}: no tiles"); continue
    ncol = 4; nrow = int(np.ceil(len(tiles) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.3 * ncol, 2.85 * nrow), squeeze=False)
    for i, ax in enumerate(axes.flat):
        ax.axis("off")
        if i >= len(tiles): continue
        ax.imshow(tiles[i][0][..., ::-1], interpolation="nearest")
        ax.set_title(tiles[i][1], fontsize=6.0)
    fig.suptitle(f"{b} — peak zooms (panel __p{pn})\neach panel is centred on the kinetochore named above it; "
                 f"{2*HALF_UM:.1f} µm window, identical scale and contrast", fontsize=8, y=0.998)
    fig.tight_layout(rect=[0, 0, 1, 0.90]); fig.subplots_adjust(hspace=0.5)
    name = f"G6ten_peakzoom__p{pn}"
    fig.savefig(f"{OUT}/{name}.png", dpi=190, bbox_inches="tight"); plt.close(fig)
    lib.record_plot(name, ["batch", "panel", "peak_series", "kt_shown", "t_min", "frame", "distortion"],
                    [r for r in recs if r[1] == pn],
                    {"type": "peak zoom sheet", "half_um": HALF_UM,
                     "peak_rule": "find_peaks, prominence >= 25% of series range, top 2 by prominence"},
                    SCRIPT, f"Artboard-7 peak zooms for {b} (panel __p{pn})",
                    source=[LOAD, TRK], key_column="batch")
    print(f"  __p{pn} {b}: {len(tiles)} tiles -> {name}.png")
    for (lab, x, v, fr, tid) in chosen:
        print(f"        chosen: {lab} peak at {x:.1f} min (frame {fr}, distortion {v:.2f})")

print(f"TOTAL zoom tiles: {len(recs)}")
