#!/usr/bin/env python3
"""k-k illustration frames, 1- vs 3-sisterless, for artboard 8.

USER 2026-08-16: "the figures on artboard 8 talk a lot about k-k distance differences between 1 and 3
sisterless kinetochore cells so find some representative zoom frames that show k-k distance between paired
kinetochores in these two cell types so i can pick some to use for illustration on artboard 8."

RULES HONOURED
  * The source is `KT_SISTER_KK` — UNTARGETED paired sister k-k. It must never be mixed with, or replaced
    by, the ablation-TARGET pair (`pre_abl`/`pre_abl_pair`); merging those two once faked a -0.44 um shift
    at p=1.5e-4 (feedback_kk_target_vs_untargeted_never_mix). No fallback to the target pair, ever.
  * "Representative" is DEFINED, not eyeballed: metaphase rows only, split by the cell's master
    "# Sisterless KTs", and the pairs whose k-k sits nearest that group's MEDIAN. An illustration chosen
    for looking dramatic would misrepresent the distribution the artboard-8 plots report.
  * Frames come from the annotation `frame` via FluorTif.plane_by_frame — never t_sec
    (project_fluor_frame_mapping_bug).
  * Centred on HER marked kinetochores (the two tracks the row names), never auto-detected
    (feedback_measure_at_her_marks_not_autodetect); nothing is snapped or recentred (NOTES §1 rule 22).
  * Identical crop size, scale and contrast across every candidate in BOTH groups, so a k-k difference can
    never be an artefact of rendering (§1 rule 5).
  * NOTES §1 rule 29 (no black bars — the window is clamped inside the frame) and rule 30 (no red on green:
    the marks and the connecting line are MAGENTA/CYAN, never red).
"""
import os, sys, csv, collections
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import ts_render   # scale-aware overlay stroke (user 2026-08-20, board 8 item 4)

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
KK   = f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv"
TRK  = f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv"
OUT  = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

N_PER_GROUP = 5          # candidates offered per group; she picks
# USER 2026-08-17: "most of the frames dont actually show a kinetochore at all but just zooms of
# background ... and even the frames that do [show one], its not zoomed in enough."
# BOTH halves were measured before changing anything (2026-08-17):
#   * ZOOM — a sister pair is ~1.6-2.4 um apart, so a 6 um window (HALF_UM 3.0) left the pair occupying
#     about a third of the panel. 1.6 um half-width puts the pair across most of the tile.
#   * "NO KINETOCHORE" — the kinetochores ARE at her marks, but only just: on 20250417 ptk_yfpcdc20_3
#     frame 70 the whole 16-bit plane spans 812-1183 counts on a median of 818, and the signal at her
#     marks is ~917, i.e. a 12% bump over background. The old stretch took percentiles of the WHOLE
#     PLANE (20th to 99.6th), which maps that entire 12% into a few grey levels and fills the tile with
#     amplified shot noise -- the green static she is describing. It is a rendering fault, not missing
#     data, and no re-picking of frames would have fixed it.

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

HALF_UM     = SHARED_KT_HALF_UM   # item 19: one scale for BOTH zoom families
BG_SIGMA    = 0.8        # px of gaussian smoothing, to keep shot noise from swamping a 12% signal


MR  = {r["Batch Name"]: r for r in lib.load_master()[0]}
DBL = lib.double_chromosome_batches()
def sis(b): return ((MR.get(b, {}) or {}).get("# Sisterless KTs", "") or "").strip()
def ok(b):  return (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in DBL and not lib.is_drug(b)

# ---- 1. metaphase sister-k-k rows, split by cohort ----------------------------------------------
rows = [r for r in csv.DictReader(open(KK)) if (r.get("phase") or "").strip() == "metaphase"]
by = collections.defaultdict(list)
for r in rows:
    b = r["batch"]
    g = sis(b)
    if g not in ("1", "3") or not ok(b): continue
    try: by[g].append((float(r["kk_dist_um"]), b, r["track_a"], r["track_c"], int(float(r["frame"]))))
    except Exception: continue

# ---- 2. per-cell median, then the cells nearest the GROUP median ---------------------------------
picks = {}
for g, v in by.items():
    med_g = float(np.median([q[0] for q in v]))
    percell = collections.defaultdict(list)
    for kk, b, ta, tc, fr in v: percell[b].append((kk, ta, tc, fr))
    cand = []
    for b, lst in percell.items():
        cm = float(np.median([q[0] for q in lst]))
        # the frame in this cell whose k-k is closest to the CELL median -> a typical frame, not an extreme
        kk, ta, tc, fr = min(lst, key=lambda q: abs(q[0] - cm))
        cand.append((abs(cm - med_g), cm, kk, b, ta, tc, fr))
    cand.sort()
    picks[g] = (med_g, cand[:N_PER_GROUP])
    print(f"  {g}-sisterless: {len(v)} metaphase pairs / {len(percell)} cells, group median k-k = {med_g:.3f} um")

# ---- 3. kinetochore positions for the chosen frames ----------------------------------------------
pos = {}
for r in csv.DictReader(open(TRK)):
    try: pos[(r["batch"], r["track_id"], int(float(r["frame"])))] = (float(r["cx_px"]), float(r["cy_px"]))
    except Exception: continue

def zoom(b, ta, tc, fr, half_px):
    """Crop centred on the MIDPOINT of her two marked kinetochores, clamped inside the frame."""
    pa = pos.get((b, ta, fr)); pc = pos.get((b, tc, fr))
    if pa is None or pc is None: return None, None, None
    # 🔴 2026-08-17 — THE REASON THE PANELS SHOWED BACKGROUND INSTEAD OF KINETOCHORES: role="monitoring".
    # FRAME_CALIBRATION.csv stores the annotation-frame -> TIF-POSITION correspondence PER ROLE, and every
    # kinetochore annotation here is a monitoring-phase mark. Built with role=None the stack indexes across
    # ALL roles, so calibrated position 69 landed 26 pages away from the monitoring frame it names.
    # MEASURED on 20250417 ptk_yfpcdc20_3 frame 70: role=None -> page 60, signal at her marks 22 counts over
    # background; role="monitoring" -> page 86, 99 counts over background, and page 86 is the BEST page in
    # the whole 145-page stack. The plane is chosen by the calibration, not by which one looks best.
    ft = lib.FluorTif(b, role="monitoring")
    if not ft.ok(): return None, None, None
    pl = ft.plane_by_frame(fr)
    if pl is None: return None, None, None
    H, W = pl.shape[:2]
    cx, cy = (pa[0] + pc[0]) / 2.0, (pa[1] + pc[1]) / 2.0
    box = int(round(2 * half_px))
    if W < box or H < box: return None, None, None
    x0 = int(min(max(0, round(cx - half_px)), W - box))      # rule 29: clamp, never pad
    y0 = int(min(max(0, round(cy - half_px)), H - box))
    A = (int(round(pa[0] - x0)), int(round(pa[1] - y0)))
    C = (int(round(pc[0] - x0)), int(round(pc[1] - y0)))
    # LOCAL BACKGROUND SUBTRACTION, not a per-panel contrast change: each crop has its own camera offset
    # (medians differ by ~13 counts between cells while the kinetochore signal is ~100), so subtracting the
    # crop's own median puts every panel on the SAME zero. One shared stretch is then applied to all of
    # them in the render loop below, so §1 rule 5 still holds -- identical contrast across panels.
    import scipy.ndimage as _nd
    raw = pl[y0:y0 + box, x0:x0 + box].astype(np.float32)
    raw = _nd.gaussian_filter(raw, BG_SIGMA)
    raw = raw - float(np.median(raw))
    return raw, A, C

def _stretch(pl):
    v = pl.astype(np.float32)
    lo, hi = np.percentile(v, 20), np.percentile(v, 99.6)
    return np.clip((v - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)

# ---- 4. one contact sheet, both groups, identical scale ------------------------------------------
recs = []
made = collections.defaultdict(list)
for g, (med_g, cand) in sorted(picks.items()):
    for _d, cm, kk, b, ta, tc, fr in cand:
        px = lib.pixel_size(b) if hasattr(lib, "pixel_size") else 0.062
        img, A, C = zoom(b, ta, tc, fr, HALF_UM / (px or 0.062))
        if img is None:
            print(f"    skip (no frame/position): {b} f{fr}"); continue
        made[g].append((img, A, C, b, fr, kk, cm))
        recs.append([b, g, ta, tc, fr, round(kk, 4), round(cm, 4), round(med_g, 4)])

# ONE contrast mapping for the whole sheet, pooled over the ACTUAL crop windows (§1 rule 5: identical
# contrast, or a difference between panels is just rendering). Pooling over the crops rather than over the
# whole planes is the point: the kinetochore signal is ~12% of the plane's background, so a plane-wide
# stretch spends its whole range on background noise.
_allpix = np.concatenate([im.ravel() for v in made.values() for im, *_ in v]) if made else np.array([0.0])
LO, HI = float(np.percentile(_allpix, 55)), float(np.percentile(_allpix, 99.5))
print(f"  shared stretch over pooled crops: {LO:.1f} .. {HI:.1f} counts above local background")

def _to_rgb(raw, A, C):
    g = np.clip((raw - LO) / max(HI - LO, 1e-6) * 255, 0, 255).astype(np.uint8)
    img = np.zeros(g.shape + (3,), np.uint8); img[..., 1] = g            # green fluorescence
    r = max(3, g.shape[0] // 14)
    # THE CONNECTOR STOPS SHORT OF BOTH KINETOCHORES. Drawn end to end it lands exactly ON the two puncta
    # and hides the thing the panel exists to show -- which is why the marked spots read as dark while
    # unmarked blobs elsewhere looked brighter. Same principle as the open-centre ablation marker.
    _a = np.array(A, float); _c = np.array(C, float)
    _v = _c - _a; _L = float(np.hypot(*_v)) or 1.0; _u = _v / _L
    _gap = r + 2
    if _L > 2 * _gap + 2:
        _p = tuple(np.round(_a + _u * _gap).astype(int)); _q = tuple(np.round(_c - _u * _gap).astype(int))
        cv2.line(img, _p, _q, (255, 255, 0), ts_render.stroke_px(img), cv2.LINE_AA)             # CYAN connector (rule 30)
    for P in (A, C):
        cv2.circle(img, P, r, (255, 0, 255), ts_render.stroke_px(img), cv2.LINE_AA)             # MAGENTA marks
    return img

made = {g: [(_to_rgb(im, A, C), b, fr, kk, cm) for im, A, C, b, fr, kk, cm in v] for g, v in made.items()}

ncol = max(len(v) for v in made.values()) if made else 0
if ncol:
    nrow = len(made)
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.5 * ncol, 3.5 * nrow), squeeze=False)
    for ri, g in enumerate(sorted(made)):
        for ci in range(ncol):
            ax = axes[ri][ci]; ax.axis("off")
            if ci >= len(made[g]): continue
            img, b, fr, kk, cm = made[g][ci]
            ax.imshow(img[..., ::-1], interpolation="nearest")           # BGR -> RGB
            ax.set_title(f"{b[:26]}\nframe {fr} · k-k {kk:.2f} µm\n(cell median {cm:.2f})", fontsize=6.2)
        axes[ri][0].text(-0.08, 0.5, f"{g}-sisterless\ngroup median {picks[g][0]:.2f} µm",
                         transform=axes[ri][0].transAxes, rotation=90, va="center", ha="right",
                         fontsize=8, fontweight="bold")
    fig.suptitle("Sister k–k illustration candidates — untargeted PAIRED kinetochores, metaphase\n"
                 "identical crop, scale and contrast across every panel; magenta = her marked kinetochores, "
                 "cyan = the measured k–k", fontsize=8.5, y=0.995)
    fig.tight_layout(rect=[0.02, 0, 1, 0.94])
    fig.subplots_adjust(hspace=0.55)   # room for the per-panel captions; they were landing on the row above
    fig.savefig(f"{OUT}/G6kk_zoom_candidates.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G6kk_zoom_candidates",
                    ["batch", "n_sisterless", "track_a", "track_c", "frame", "kk_um",
                     "cell_median_kk_um", "group_median_kk_um"],
                    recs, {"type": "candidate contact sheet", "half_um": HALF_UM,
                           "selection": "cells nearest the group median; frame nearest the cell median"},
                    SCRIPT, "k-k illustration candidates, 1 vs 3 sisterless (untargeted paired sisters)",
                    source=[KK, TRK], key_column="batch")
    print(f"  wrote G6kk_zoom_candidates.png with {len(recs)} panels")
else:
    print("  no panels produced")
