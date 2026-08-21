#!/usr/bin/env python3
"""Metaphase-entry / anaphase-entry frame PAIRS, 1- and 3-sisterless, for artboard 4.

USER 2026-08-16: "the line plots on artboard 4 ... discuss cells changing shape, etc through metaphase, and
i want visuals for this. so for each of 1 and 3 sisterless kinetochores, find some cells and take the frame
where they enter metaphase, and the frame where they enter anaphase, PAIRED, and give them to me (on the
file) so i can choose some pairs to use as examples."

DESIGN DECISIONS, and why
  * Cells are restricted to those that HAVE `cell_outlines` — the artboard-4 line plots are built from those
    outlines, so an example cell must be one the plots actually contain, otherwise the visual illustrates a
    cell the data never saw.
  * Event times come from `lib.load_master()` — never `load_master_plots()`, which returns nothing for a
    dropped batch so event times read as EMPTY rather than missing (§14 2026-08-08/09 trap (a)).
  * The frame is chosen as the OUTLINE frame nearest each event time, and the image is fetched by that
    annotation `frame` through FluorTif.plane_by_frame — never by t_sec (project_fluor_frame_mapping_bug).
  * WITHIN a pair the crop box, scale and contrast are IDENTICAL (one box sized to the union of the two
    outlines, one stretch computed across both frames), so an apparent shape change can never be a
    rendering artefact (§1 rule 5). The box is clamped inside the frame, never padded (§1 rule 29).
  * Her traced outline is drawn in CYAN, never red on green (§1 rule 30). Nothing is snapped or re-centred
    (§1 rule 22) — the polygon is drawn exactly as she traced it.
"""
import os, sys, csv, collections, json
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import ts_render   # scale-aware overlay stroke (user 2026-08-20, board 8 item 4)

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
CO   = f"{ROOT}/annotations/cell_outlines.csv"
OUT  = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
N_PER_GROUP = 6

MR  = {r["Batch Name"]: r for r in lib.load_master()[0]}
DBL = lib.double_chromosome_batches()
def sis(b): return ((MR.get(b, {}) or {}).get("# Sisterless KTs", "") or "").strip()
def ok(b):  return (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in DBL and not lib.is_drug(b)
def ev(b, col):
    return lib.parse_time((MR.get(b, {}) or {}).get(col, "") or "")

# ---- outlines by batch -> {frame: polygon, t_sec} ------------------------------------------------
outl = collections.defaultdict(dict)
for r in csv.DictReader(open(CO)):
    b = r.get("batch", "")
    if not b: continue
    p = (r.get("points") or "").strip()
    if not p: continue
    try:
        pts = np.array(json.loads(p), float)
        fr  = int(round(float(r["frame"]))); ts = float(r.get("t_sec") or "nan")
    except Exception:
        continue
    if pts.ndim != 2 or len(pts) < 3: continue
    outl[b][fr] = (pts, ts)

def frame_near(b, t):
    """Outline frame whose own t_sec is nearest the event time."""
    cand = [(abs(ts - t), fr) for fr, (_p, ts) in outl[b].items() if ts == ts]
    return min(cand)[1] if cand else None

# ---- pick cells --------------------------------------------------------------------------------
picked = collections.defaultdict(list)
for b in sorted(outl):
    g = sis(b)
    if g not in ("1", "3") or not ok(b): continue
    mt, at = ev(b, "Metaphase Start (s)"), ev(b, "Anaphase Onset (s)")
    if mt is None or at is None or at <= mt: continue
    fm, fa = frame_near(b, mt), frame_near(b, at)
    if fm is None or fa is None or fm == fa: continue
    picked[g].append((b, fm, fa, (at - mt) / 60.0))

for g in picked:
    picked[g].sort(key=lambda q: q[3])          # ordered by metaphase duration, short -> long
    step = max(1, len(picked[g]) // N_PER_GROUP)
    picked[g] = picked[g][::step][:N_PER_GROUP] # spread across the duration range, not the extremes
    print(f"  {g}-sisterless: {len(picked[g])} pairs offered")

def _stretch2(a, bimg):
    v = np.concatenate([a.ravel(), bimg.ravel()]).astype(np.float32)   # ONE stretch across the pair
    lo, hi = np.percentile(v, 20), np.percentile(v, 99.6)
    f = lambda x: np.clip((x.astype(np.float32) - lo) / max(hi - lo, 1e-6) * 255, 0, 255).astype(np.uint8)
    return f(a), f(bimg)

def pair_images(b, fm, fa):
    ft = lib.FluorTif(b)
    if not ft.ok(): return None
    pm, pa = ft.plane_by_frame(fm), ft.plane_by_frame(fa)
    if pm is None or pa is None: return None
    gm, ga = _stretch2(pm, pa)
    P1, P2 = outl[b][fm][0], outl[b][fa][0]
    allp = np.vstack([P1, P2])
    cx, cy = allp[:, 0].mean(), allp[:, 1].mean()
    half = int(round(max(np.ptp(allp[:, 0]), np.ptp(allp[:, 1])) * 0.75)) + 10   # numpy 2: ndarray.ptp removed
    H, W = gm.shape[:2]; box = 2 * half
    if W < box or H < box: half = min(W, H) // 2; box = 2 * half
    x0 = int(min(max(0, round(cx - half)), W - box))       # clamp, never pad (rule 29)
    y0 = int(min(max(0, round(cy - half)), H - box))
    outs = []
    for g8, P in ((gm, P1), (ga, P2)):
        sub = g8[y0:y0 + box, x0:x0 + box]
        img = np.zeros((box, box, 3), np.uint8); img[..., 1] = sub
        q = (P - np.array([x0, y0])).astype(np.int32)
        cv2.polylines(img, [q], True, (255, 255, 0), ts_render.stroke_px(img), cv2.LINE_AA)    # CYAN outline (rule 30)
        outs.append(img)
    return outs

recs, made = [], collections.defaultdict(list)
for g in sorted(picked):
    for b, fm, fa, dur in picked[g]:
        im = pair_images(b, fm, fa)
        if im is None: continue
        made[g].append((im, b, fm, fa, dur))
        recs.append([b, g, fm, fa, round(dur, 2)])

ncol = max((len(v) for v in made.values()), default=0)
if ncol:
    nrow = 2 * len(made)
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.4 * ncol, 2.7 * nrow), squeeze=False)
    ri = 0
    for g in sorted(made):
        for k, lab in ((0, "metaphase entry"), (1, "anaphase entry")):
            for ci in range(ncol):
                ax = axes[ri][ci]; ax.axis("off")
                if ci >= len(made[g]): continue
                im, b, fm, fa, dur = made[g][ci]
                ax.imshow(im[k][..., ::-1], interpolation="nearest")
                if k == 0: ax.set_title(f"{b[:24]}\nmetaphase {dur:.0f} min", fontsize=6.0)
            axes[ri][0].text(-0.10, 0.5, f"{g}-sis\n{lab}", transform=axes[ri][0].transAxes,
                             rotation=90, va="center", ha="right", fontsize=7.5, fontweight="bold")
            ri += 1
    fig.suptitle("Metaphase-entry / anaphase-entry PAIRS — candidates for artboard 4\n"
                 "each column is ONE cell; identical crop, scale and contrast within a pair; "
                 "cyan = her traced outline", fontsize=8.5, y=0.997)
    fig.tight_layout(rect=[0.03, 0, 1, 0.95]); fig.subplots_adjust(hspace=0.45)
    fig.savefig(f"{OUT}/G1_meta_ana_pair_candidates.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G1_meta_ana_pair_candidates",
                    ["batch", "n_sisterless", "frame_metaphase", "frame_anaphase", "metaphase_min"],
                    recs, {"type": "candidate pair sheet",
                           "selection": "cells WITH cell_outlines, spread across metaphase duration"},
                    SCRIPT, "Metaphase/anaphase frame pairs, 1 vs 3 sisterless (choosing sheet)",
                    source=[CO], key_column="batch")
    print(f"  wrote G1_meta_ana_pair_candidates.png with {len(recs)} pairs")
else:
    print("  no pairs produced")
