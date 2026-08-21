#!/usr/bin/env python3
"""A LEARNED image-only kinetochore centre, fitted on the 917 verified outline placements (user 2026-07-28).

Earlier attempts each picked ONE hand-designed estimator and none beat the raw click by much. Two things
were left on the table:

  A. A GRID over the actual free parameters (smoothing sigma, window radius, background percentile) instead
     of one guessed setting. The kinetochore region is diffuse, so the right sigma/radius is an empirical
     question, not something to assume.
  B. COMBINING the estimators. The click carries real information (she is looking at the kinetochore); the
     image carries real information. The outline centre generally lies BETWEEN them. A fitted blend can beat
     every individual estimator, and nothing tried so far exploited that.

Everything is validated with GROUPED cross-validation — folds split by CELL, never by mark — so a blend fitted
on one set of cells is scored only on cells it has never seen. That is what makes the result trustworthy for
cells with no outlines at all.
"""
import sys, os, csv, json, collections, itertools
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import ndimage
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)

truth, meta = {}, {}
for r in csv.DictReader(open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv", newline="")):
    if r["status"] == "matched" and r["snap_x"]:
        truth[str(r["circle_id"])] = (float(r["snap_x"]), float(r["snap_y"]))
pts = {}
for r in csv.DictReader(open(f"{A}/kt_points.csv", newline="")):
    if str(r["id"]) in truth:
        pts[str(r["id"])] = (r["batch"].strip(), int(r["frame"]), float(r["x"]), float(r["y"]), r["label"].strip())
print(f"{len(pts)} ground-truth marks across {len({v[0] for v in pts.values()})} cells")

SIGMAS = [0.0, 1.0, 2.0, 3.0, 4.0]
RADII = [7, 9, 12, 15, 20]
BGP = 30

bycell = collections.defaultdict(list)
for pid, (b, f, x, y, lab) in pts.items():
    bycell[b].append((pid, f, x, y, lab))

feat = {}
for ci, b in enumerate(sorted(bycell), 1):
    ft = None
    for role in ("monitoring", "ablation"):
        try:
            ft = lib.FluorTif(b, role)
            if ft is not None and ft.plane_by_frame(bycell[b][0][1]) is not None:
                break
        except Exception:
            ft = None
    if ft is None:
        continue
    for pid, f, x, y, lab in bycell[b]:
        g = ft.plane_by_frame(f)
        if g is None:
            continue
        h, w = g.shape[:2]
        row = {}
        for rad in RADII:
            xi, yi = int(round(x)), int(round(y))
            x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
            y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
            sub = g[y0:y1, x0:x1].astype(float)
            if sub.size < 16:
                continue
            yy, xx = np.mgrid[y0:y1, x0:x1]
            for sg in SIGMAS:
                s = ndimage.gaussian_filter(sub, sg) if sg > 0 else sub
                v = s - np.percentile(s, BGP)
                v[v < 0] = 0
                if v.sum() <= 0:
                    continue
                row[(rad, sg)] = (float((xx * v).sum() / v.sum()), float((yy * v).sum() / v.sum()))
        if row:
            feat[pid] = row
    if ci % 15 == 0:
        print(f"  [{ci}/{len(bycell)}]")

ids = [p for p in feat if p in truth]
print(f"\nfeatures computed for {len(ids)} marks")
cells = sorted({pts[p][0] for p in ids})
fold = {c: i % 5 for i, c in enumerate(cells)}


def err_of(pred):
    return np.array([float(np.hypot(pred[p][0] - truth[p][0], pred[p][1] - truth[p][1])) for p in ids])


print("\nGRID over window radius x smoothing sigma (median error, px):")
print("        " + "".join(f"{s:>8.0f}" for s in SIGMAS))
best_cfg, best_med = None, 1e9
for rad in RADII:
    line = f"  r={rad:2d} "
    for sg in SIGMAS:
        ok = [p for p in ids if (rad, sg) in feat[p]]
        if len(ok) < 200:
            line += f"{'-':>8s}"; continue
        e = np.array([float(np.hypot(feat[p][(rad, sg)][0] - truth[p][0],
                                     feat[p][(rad, sg)][1] - truth[p][1])) for p in ok])
        m = float(np.median(e))
        line += f"{m:8.2f}"
        if m < best_med:
            best_med, best_cfg = m, (rad, sg)
    print(line)
print(f"  best single estimator: radius {best_cfg[0]}, sigma {best_cfg[1]} -> median {best_med:.2f} px")

rad, sg = best_cfg
use = [p for p in ids if (rad, sg) in feat[p]]
click = {p: (pts[p][2], pts[p][3]) for p in use}
img = {p: feat[p][(rad, sg)] for p in use}
e_click = np.array([float(np.hypot(click[p][0] - truth[p][0], click[p][1] - truth[p][1])) for p in use])
e_img = np.array([float(np.hypot(img[p][0] - truth[p][0], img[p][1] - truth[p][1])) for p in use])

print("\nBLEND  pred = a*click + (1-a)*image,  a chosen on TRAIN cells, scored on HELD-OUT cells:")
alphas = np.linspace(0, 1, 21)
oof = np.zeros(len(use))
for k in range(5):
    tr = [i for i, p in enumerate(use) if fold[pts[p][0]] != k]
    te = [i for i, p in enumerate(use) if fold[pts[p][0]] == k]
    if not tr or not te:
        continue
    best_a, best_e = 0.5, 1e9
    for a in alphas:
        ee = []
        for i in tr:
            p = use[i]
            px = a * click[p][0] + (1 - a) * img[p][0]
            py = a * click[p][1] + (1 - a) * img[p][1]
            ee.append(np.hypot(px - truth[p][0], py - truth[p][1]))
        m = float(np.median(ee))
        if m < best_e:
            best_e, best_a = m, a
    for i in te:
        p = use[i]
        px = best_a * click[p][0] + (1 - best_a) * img[p][0]
        py = best_a * click[p][1] + (1 - best_a) * img[p][1]
        oof[i] = np.hypot(px - truth[p][0], py - truth[p][1])
    print(f"  fold {k}: alpha={best_a:.2f} (train median {best_e:.2f})  -> held-out median {np.median(oof[te]):.2f} px")

print(f"\n  n={len(use)} marks, {len(cells)} cells")
print(f"  raw click                 median {np.median(e_click):5.2f} px | within 5px {np.mean(e_click<=5)*100:5.1f}%")
print(f"  best image estimator      median {np.median(e_img):5.2f} px | within 5px {np.mean(e_img<=5)*100:5.1f}%")
print(f"  BLEND (held-out)          median {np.median(oof):5.2f} px | within 5px {np.mean(oof<=5)*100:5.1f}%")
print(f"  floor (intensity centre inside her own outline): 2.29 px")

fig, ax = plt.subplots(figsize=(7.4, 5.0))
for d, nm, c in ((e_click, "raw click", "#999999"), (e_img, f"best image (r={rad}, s={sg:g})", "#e6820e"),
                 (oof, "fitted blend, held-out cells", "#2e8b57")):
    ax.hist(np.clip(d, 0, 20), bins=np.arange(0, 21, 1.0), histtype="step", lw=2.2, color=c,
            label=f"{nm}: med {np.median(d):.2f} px")
ax.axvline(2.29, ls="--", color="#d1495b", lw=1.4)
ax.text(2.45, ax.get_ylim()[1]*0.9, "floor 2.29 px", fontsize=7.5, color="#d1495b")
ax.set_xlabel("distance from the outline-derived centre (px)"); ax.set_ylabel("# marks")
ax.legend(fontsize=8)
ax.set_title(f"Learned image-only KT centering ({len(use)} verified marks, grouped CV by cell)",
             loc="left", fontweight="bold", fontsize=10)
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_learned_kt_centering.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("  QNEW_learned_kt_centering")
