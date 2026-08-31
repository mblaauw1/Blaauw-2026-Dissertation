#!/usr/bin/env python3
"""Reproduce the OUTLINE-derived kinetochore centre from the image alone, by segmenting the kinetochore
REGION rather than hunting its brightest pixel (user 2026-07-28).

WHY the earlier attempt failed, measured: with her outline handed to the algorithm, the brightest pixel
inside it still sits a median 5.09 px from the outline's area centroid, while the intensity centroid of the
enclosed region sits only 2.29 px away. Peak-finders were chasing the wrong target. Median outline area is
196 px (equivalent radius 7.9 px), so a +/-9 px window with a 2.5-sigma cut can only ever capture the bright
core, not the region.

THIS method:
  1. window +/-RAD (15 px, so a ~196 px region fits with margin)
  2. background = 25th pct, noise = IQR/1.349, mask = pixels above bg + K*noise
  3. find local maxima in the window -> one seed per kinetochore
  4. WATERSHED the mask from those seeds, so touching kinetochores are SPLIT into separate basins
  5. keep the basin whose seed is nearest the click AND is not claimed by another circle annotation on the
     same frame (we know where the other kinetochores were marked, so we can actively repel from them)
  6. return the AREA CENTROID of that basin

CONTAMINATION CONTROL — the specific thing a 15 px radius risks:
  * watershed splitting means a neighbouring kinetochore forms its own basin and cannot bleed into ours;
  * any seed closer to a DIFFERENT circle annotation than to ours is excluded outright;
  * `sep_px` (distance to the nearest competing seed) and `n_seeds` are recorded, so a crowded window is
    visible in the output instead of silently biasing the centroid;
  * a basin touching the window edge is flagged (it is truncated, so its centroid is biased inward);
  * `area_px` far from the expected kinetochore area flags an under- or over-grown region.
All of these feed the confidence score, which is validated against the 917 known-correct placements.

Outputs annotations/KT_REGION_CENTER_20260728.csv + a figure.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import ndimage
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
RAD = 15
K_NOISE = 1.2          # low, so the REGION grows rather than just the core
AREA_LO, AREA_HI = 40, 700

truth = {}
for r in csv.DictReader(open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv", newline="")):
    if r["status"] == "matched" and r["snap_x"]:
        truth[str(r["circle_id"])] = (float(r["snap_x"]), float(r["snap_y"]))

circles = collections.defaultdict(list)          # (batch, frame) -> [(x,y,label,id)]
for r in csv.DictReader(open(f"{A}/kt_points.csv", newline="")):
    if r["label"].strip() not in ("polar", "sisterless", "paired_kt", "lagging"):
        continue
    if not r["frame"].strip().isdigit():
        continue
    try: circles[(r["batch"].strip(), int(r["frame"]))].append(
        (float(r["x"]), float(r["y"]), r["label"].strip(), r["id"]))
    except Exception: pass
print(f"{sum(len(v) for v in circles.values())} circles; {len(truth)} with outline ground truth")


def region_center(g, x, y, others=(), rad=RAD, k=K_NOISE):
    """others = [(x,y), ...] the OTHER circle annotations on this frame, used to repel."""
    h, w = g.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
    y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
    sub = g[y0:y1, x0:x1].astype(float)
    if sub.size < 25:
        return None
    bg = float(np.percentile(sub, 25))
    noise = (float(np.percentile(sub, 75) - np.percentile(sub, 25)) / 1.349) or 1.0
    mask = sub >= bg + k * noise
    if mask.sum() < 6:
        return None
    sm = ndimage.gaussian_filter(sub, 1.0)
    seeds = peak_local_max(sm, min_distance=3, labels=mask, exclude_border=False)
    if len(seeds) == 0:
        seeds = np.array([[int(round(y - y0)), int(round(x - x0))]])
    mk = np.zeros(sub.shape, int)
    for i, (sy, sx) in enumerate(seeds, 1):
        mk[sy, sx] = i
    lab = watershed(-sm, mk, mask=mask)
    cy, cx = y - y0, x - x0
    # a seed that is closer to ANOTHER circle annotation than to ours belongs to that kinetochore
    oth = [(oy - y0, ox - x0) for ox, oy in others]
    cand = []
    for i, (sy, sx) in enumerate(seeds, 1):
        dmine = float(np.hypot(sx - cx, sy - cy))
        if oth and min(float(np.hypot(sx - ox, sy - oy)) for oy, ox in oth) < dmine:
            continue                                   # claimed by a neighbour's annotation
        cand.append((dmine, i, sy, sx))
    if not cand:
        return None
    cand.sort()
    dmine, best, sy, sx = cand[0]
    sep = cand[1][0] if len(cand) > 1 else float(np.hypot(rad, rad)) * 2
    ys, xs = np.where(lab == best)
    if len(ys) < 6:
        return None
    v = sub[ys, xs] - bg
    v[v < 0] = 0
    if v.sum() <= 0:
        gx, gy = xs.mean(), ys.mean()
    else:
        gx, gy = (xs * v).sum() / v.sum(), (ys * v).sum() / v.sum()
    touches = bool(xs.min() == 0 or ys.min() == 0 or xs.max() == sub.shape[1] - 1 or ys.max() == sub.shape[0] - 1)
    return dict(x=float(x0 + gx), y=float(y0 + gy), area=int(len(xs)), n_seeds=int(len(seeds)),
                sep_px=float(sep), snr=float((sub[ys, xs].max() - bg) / noise),
                touches_edge=touches, moved=float(np.hypot(x0 + gx - x, y0 + gy - y)))


rows = []
bycell = collections.defaultdict(list)
for (b, f), v in circles.items():
    bycell[b].append((f, v))
for ci, b in enumerate(sorted(bycell), 1):
    ft = None
    for role in ("monitoring", "ablation"):
        try:
            ft = lib.FluorTif(b, role)
            if ft is not None and ft.plane_by_frame(bycell[b][0][0]) is not None:
                break
        except Exception:
            ft = None
    if ft is None:
        continue
    for f, v in bycell[b]:
        g = ft.plane_by_frame(f)
        if g is None:
            continue
        for x, y, lab, pid in v:
            others = [(ox, oy) for ox, oy, _l, oid in v if oid != pid]
            res = region_center(g, x, y, others)
            row = dict(batch=b, frame=f, circle_id=pid, circle_label=lab,
                       click_x=round(x, 2), click_y=round(y, 2))
            if res:
                row.update(region_x=round(res["x"], 2), region_y=round(res["y"], 2),
                           area_px=res["area"], n_seeds=res["n_seeds"],
                           sep_px=round(res["sep_px"], 1), snr=round(res["snr"], 2),
                           touches_edge=int(res["touches_edge"]), moved_px=round(res["moved"], 2))
            t = truth.get(str(pid))
            row["truth_x"] = round(t[0], 2) if t else ""
            row["truth_y"] = round(t[1], 2) if t else ""
            rows.append(row)
    if ci % 20 == 0:
        print(f"  [{ci}/{len(bycell)}]")

for r in rows:
    if "region_x" not in r:
        r["confidence"] = 0.0; continue
    c = 1.0
    c *= 1.0 if AREA_LO <= r["area_px"] <= AREA_HI else 0.35     # region grew to a plausible KT size
    c *= min(1.0, r["sep_px"] / 10.0)                            # nearest competing kinetochore
    c *= 0.45 if r["touches_edge"] else 1.0                      # truncated region -> biased centroid
    c *= min(1.0, r["snr"] / 6.0)
    c *= 1.0 if r["moved_px"] <= 8 else 0.5
    r["confidence"] = round(float(min(1.0, max(0.0, c))), 3)

cols = ["batch", "frame", "circle_id", "circle_label", "click_x", "click_y", "region_x", "region_y",
        "area_px", "n_seeds", "sep_px", "snr", "touches_edge", "moved_px", "confidence", "truth_x", "truth_y"]
with open(f"{A}/KT_REGION_CENTER_20260728.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

ev = [r for r in rows if r["truth_x"] != "" and "region_x" in r]
e = np.array([float(np.hypot(r["region_x"] - r["truth_x"], r["region_y"] - r["truth_y"])) for r in ev])
ec = np.array([float(np.hypot(r["click_x"] - r["truth_x"], r["click_y"] - r["truth_y"])) for r in ev])
print(f"\n{len(rows)} circles; {len(ev)} evaluable against the outline placement")
print(f"  raw click             median {np.median(ec):5.2f} px | within 3px {np.mean(ec<=3)*100:5.1f}% | within 5px {np.mean(ec<=5)*100:5.1f}%")
print(f"  REGION centroid       median {np.median(e):5.2f} px | within 3px {np.mean(e<=3)*100:5.1f}% | within 5px {np.mean(e<=5)*100:5.1f}%")
ar = np.array([r["area_px"] for r in ev])
print(f"  segmented area: median {np.median(ar):.0f} px (her outlines: 196 px)")
conf = np.array([r["confidence"] for r in ev])
print("\nconfidence vs error:")
for lo, hi in [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]:
    m = (conf >= lo) & (conf < hi)
    if m.sum() >= 10:
        print(f"  {lo:.1f}-{hi:.1f}: n={m.sum():4d}  median {np.median(e[m]):5.2f} px  within 5px {np.mean(e[m]<=5)*100:5.1f}%")
crowd = np.array([r["sep_px"] for r in ev])
print("\ncrowding (distance to the nearest competing kinetochore seed):")
for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 1e9)]:
    m = (crowd >= lo) & (crowd < hi)
    if m.sum() >= 10:
        print(f"  sep {lo:>2}-{hi if hi<1e9 else 'inf':>3}px: n={m.sum():4d}  median error {np.median(e[m]):5.2f} px")

fig, axs = plt.subplots(1, 2, figsize=(12.6, 4.8))
ax = axs[0]
ax.hist(np.clip(ec, 0, 20), bins=np.arange(0, 21, 1.0), histtype="step", lw=2.0, color="#999",
        label=f"raw click: med {np.median(ec):.2f} px")
ax.hist(np.clip(e, 0, 20), bins=np.arange(0, 21, 1.0), histtype="step", lw=2.4, color="#2e8b57",
        label=f"region centroid: med {np.median(e):.2f} px")
ax.axvline(2.29, ls="--", color="#d1495b", lw=1.4)
ax.text(2.4, ax.get_ylim()[1]*0.92, "floor: 2.29 px\n(intensity centre inside\nher own outline)",
        fontsize=7.5, color="#d1495b", va="top")
ax.set_xlabel("distance from the outline-derived placement (px)"); ax.set_ylabel("# marks")
ax.legend(fontsize=8); ax.set_title("Region segmentation vs the known-correct centre", loc="left", fontweight="bold", fontsize=10)
ax = axs[1]
xs, ys, ns = [], [], []
for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 1e9)]:
    m = (crowd >= lo) & (crowd < hi)
    if m.sum() >= 10:
        xs.append(min(hi, 25)); ys.append(float(np.median(e[m]))); ns.append(int(m.sum()))
ax.plot(xs, ys, "-o", color="#3b6fb6", lw=2.4)
for x_, y_, n_ in zip(xs, ys, ns):
    ax.annotate(f"n={n_}", (x_, y_), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=7.5)
ax.set_xlabel("distance to the nearest competing kinetochore (px)")
ax.set_ylabel("median error (px)")
ax.set_title("crowding is detected and recorded, not silently absorbed", loc="left", fontweight="bold", fontsize=10)
fig.suptitle(f"Image-only kinetochore REGION centering, validated on {len(ev)} verified marks",
             fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_region_centering.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("  QNEW_region_centering")
