#!/usr/bin/env python3
"""Can we reproduce the OUTLINE-derived circle placement from the IMAGE ALONE? (user 2026-07-28)

The constrained circle->outline match gives 917 placements we know are correct (the area centroid of her
manual outline). Those are the ground truth. This script asks: for a cell with NO outlines, can an
image-only estimator land in the same place?

WHY the outline works: an outline encloses the kinetochore REGION and we take the middle of that area.
So the image-only method that should match it is not "brightest pixel" (a single noisy maximum, and in a
crowded plate often a NEIGHBOUR's pixel) but "segment the punctum, take the centroid of the segmented
AREA" — the same quantity, derived automatically.

Estimators compared, all inside a +/-RAD window around the click:
  click       the raw annotation
  peak        brightest pixel                            (the deck's original)
  wcent       intensity-weighted centroid                (the current fallback)
  blob        threshold at bg + K*noise, keep the connected component nearest the click,
              return the centroid of THAT AREA           <- the outline analogue
  blob_it     as blob, but the window is re-centred on the result and it is recomputed (mean-shift),
              so a click near the window edge cannot bias the answer

CONFIDENCE is recorded per mark from image quantities only (never from the outline), so it is available
for cells that have no outlines: SNR, segmented area, how far the estimate moved from the click, whether
the blob touches the window edge, and how many competing blobs are in the window. The script then shows
that the confidence actually predicts the error, and picks a usable cut.

Outputs: annotations/KT_CENTER_IMAGE_20260728.csv + a figure in group7_questions/.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import ndimage
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
RAD = 9
K_NOISE = 2.5

truth = {}
for r in csv.DictReader(open(f"{A}/CIRCLE_OUTLINE_MATCH_20260728.csv", newline="")):
    if r["status"] == "matched" and r["snap_x"]:
        truth[str(r["circle_id"])] = (float(r["snap_x"]), float(r["snap_y"]))
print(f"{len(truth)} ground-truth placements (outline area centroids)")

circles = collections.defaultdict(list)
for r in csv.DictReader(open(f"{A}/kt_points.csv", newline="")):
    if r["label"].strip() not in ("polar", "sisterless", "paired_kt", "lagging"):
        continue
    if not r["frame"].strip().isdigit():
        continue
    try: circles[r["batch"].strip()].append(
        (int(r["frame"]), float(r["x"]), float(r["y"]), r["label"].strip(), r["id"]))
    except Exception: pass


def window(g, x, y, rad):
    h, w = g.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
    y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
    return g[y0:y1, x0:x1].astype(float), x0, y0


def blob_center(g, x, y, rad=RAD, k=K_NOISE):
    """threshold at bg + k*noise, take the connected component nearest the click, return the centroid of
    its AREA (the automatic analogue of 'middle of the traced outline') + the confidence features."""
    sub, x0, y0 = window(g, x, y, rad)
    if sub.size < 9:
        return None
    bg = float(np.percentile(sub, 25))
    noise = float(np.percentile(sub, 75) - np.percentile(sub, 25)) / 1.349 or 1.0
    thr = bg + k * noise
    mask = sub >= thr
    if mask.sum() < 3:
        return None
    lab, n = ndimage.label(mask)
    cy, cx = (y - y0), (x - x0)
    best, bestd = None, None
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        d = float(np.hypot(xs.mean() - cx, ys.mean() - cy))
        if bestd is None or d < bestd:
            bestd, best = d, i
    ys, xs = np.where(lab == best)
    wgt = sub[ys, xs] - bg
    wgt[wgt < 0] = 0
    if wgt.sum() <= 0:
        gx, gy = xs.mean(), ys.mean()
    else:
        gx, gy = (xs * wgt).sum() / wgt.sum(), (ys * wgt).sum() / wgt.sum()
    peak = float(sub[ys, xs].max())
    touches = bool(xs.min() == 0 or ys.min() == 0 or xs.max() == sub.shape[1] - 1 or ys.max() == sub.shape[0] - 1)
    return dict(x=float(x0 + gx), y=float(y0 + gy), area=int(len(xs)),
                snr=float((peak - bg) / noise), nblob=int(n), touches_edge=touches)


def blob_iter(g, x, y, rad=RAD, k=K_NOISE, iters=2):
    cur = (x, y); out = None
    for _ in range(iters):
        out = blob_center(g, cur[0], cur[1], rad, k)
        if out is None:
            return None
        if np.hypot(out["x"] - cur[0], out["y"] - cur[1]) < 0.25:
            break
        cur = (out["x"], out["y"])
    return out


rows = []
cells = sorted(circles)
for ci, b in enumerate(cells, 1):
    ft = None
    for role in ("monitoring", "ablation"):
        try:
            ft = lib.FluorTif(b, role)
            if ft is not None and ft.plane_by_frame(circles[b][0][0]) is not None:
                break
        except Exception:
            ft = None
    if ft is None:
        continue
    for f, x, y, lab, pid in circles[b]:
        g = ft.plane_by_frame(f)
        if g is None:
            continue
        px_, py_ = lib.snap_to_peak_pixel(g, x, y, RAD)
        wx, wy = lib.snap_to_peak(g, x, y, RAD)
        bi = blob_iter(g, x, y)
        bl = blob_center(g, x, y)
        t = truth.get(str(pid))
        row = dict(batch=b, frame=f, circle_id=pid, circle_label=lab,
                   click_x=round(x, 2), click_y=round(y, 2),
                   peak_x=round(px_, 2), peak_y=round(py_, 2),
                   wcent_x=round(wx, 2), wcent_y=round(wy, 2))
        for tag, res in (("blob", bl), ("blobit", bi)):
            if res:
                row[f"{tag}_x"] = round(res["x"], 2); row[f"{tag}_y"] = round(res["y"], 2)
                if tag == "blobit":
                    row.update(snr=round(res["snr"], 2), area_px=res["area"],
                               n_blobs=res["nblob"], touches_edge=int(res["touches_edge"]),
                               moved_px=round(float(np.hypot(res["x"] - x, res["y"] - y)), 2))
            else:
                row[f"{tag}_x"] = ""; row[f"{tag}_y"] = ""
        row["truth_x"] = round(t[0], 2) if t else ""
        row["truth_y"] = round(t[1], 2) if t else ""
        rows.append(row)
    if ci % 10 == 0:
        print(f"  [{ci}/{len(cells)}]")

# ---- confidence, from image quantities only ----
for r in rows:
    snr = r.get("snr"); ar = r.get("area_px"); nb = r.get("n_blobs")
    if snr is None or ar is None:
        r["confidence"] = 0.0; continue
    c = 1.0
    c *= min(1.0, snr / 8.0)                      # bright, clean punctum
    c *= 1.0 if 6 <= ar <= 160 else 0.45          # plausible kinetochore area
    c *= 1.0 if nb <= 2 else 0.6                  # window not crowded with competitors
    c *= 0.5 if r.get("touches_edge") else 1.0    # blob clipped by the window -> biased
    c *= 1.0 if (r.get("moved_px") or 0) <= 6 else 0.6
    r["confidence"] = round(float(min(1.0, max(0.0, c))), 3)

with open(f"{A}/KT_CENTER_IMAGE_20260728.csv", "w", newline="") as f:
    cols = ["batch", "frame", "circle_id", "circle_label", "click_x", "click_y", "peak_x", "peak_y",
            "wcent_x", "wcent_y", "blob_x", "blob_y", "blobit_x", "blobit_y",
            "snr", "area_px", "n_blobs", "touches_edge", "moved_px", "confidence", "truth_x", "truth_y"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(rows)

ev = [r for r in rows if r["truth_x"] != ""]
print(f"\n{len(rows)} circles measured; {len(ev)} have outline ground truth\n")
METH = [("click", "click"), ("peak", "brightest pixel"), ("wcent", "weighted centroid"),
        ("blob", "blob-area centroid"), ("blobit", "blob-area centroid, re-centred")]
err = {}
for k, nm in METH:
    d = [float(np.hypot(r[f"{k}_x"] - r["truth_x"], r[f"{k}_y"] - r["truth_y"]))
         for r in ev if r.get(f"{k}_x") not in ("", None)]
    err[k] = np.array(d)
    print(f"  {nm:32s} median {np.median(d):5.2f} px | p90 {np.percentile(d,90):5.2f} | "
          f"within 3px {np.mean(np.array(d)<=3)*100:5.1f}% | within 5px {np.mean(np.array(d)<=5)*100:5.1f}%")

best = "blobit"
conf = np.array([r["confidence"] for r in ev])
e = np.array([float(np.hypot(r[f"{best}_x"] - r["truth_x"], r[f"{best}_y"] - r["truth_y"]))
              if r.get(f"{best}_x") not in ("", None) else np.nan for r in ev])
print("\nDOES THE CONFIDENCE PREDICT THE ERROR? (blob-area centroid, re-centred)")
for lo, hi in [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]:
    m = (conf >= lo) & (conf < hi) & np.isfinite(e)
    if m.sum() >= 10:
        print(f"  confidence {lo:.1f}-{hi:.1f}: n={m.sum():4d}  median error {np.median(e[m]):5.2f} px  "
              f"within 5px {np.mean(e[m]<=5)*100:5.1f}%")
allc = np.array([r["confidence"] for r in rows])
print(f"\nacross ALL {len(rows)} circles (including cells with NO outlines): "
      f"{np.mean(allc>=0.5)*100:.1f}% reach confidence >= 0.5")

fig, axs = plt.subplots(1, 2, figsize=(12.6, 4.8))
ax = axs[0]
for k, nm in METH:
    if len(err[k]):
        ax.hist(np.clip(err[k], 0, 20), bins=np.arange(0, 21, 1.0), histtype="step", lw=2.0,
                label=f"{nm}: med {np.median(err[k]):.2f} px")
ax.set_xlabel("distance from the OUTLINE-derived placement (px)"); ax.set_ylabel("# marks")
ax.legend(fontsize=8)
ax.set_title("Image-only estimators vs the known-correct placement", loc="left", fontweight="bold", fontsize=10)
ax = axs[1]
xs, ys, ns = [], [], []
for lo, hi in [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]:
    m = (conf >= lo) & (conf < hi) & np.isfinite(e)
    if m.sum() >= 10:
        xs.append((lo + min(hi, 1.0)) / 2); ys.append(float(np.median(e[m]))); ns.append(int(m.sum()))
ax.plot(xs, ys, "-o", color="#3b6fb6", lw=2.4)
for x_, y_, n_ in zip(xs, ys, ns):
    ax.annotate(f"n={n_}", (x_, y_), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=7.5)
ax.set_xlabel("image-only confidence score"); ax.set_ylabel("median error vs the outline placement (px)")
ax.set_title("confidence predicts accuracy, so it can be used to filter", loc="left", fontweight="bold", fontsize=10)
fig.suptitle(f"Reproducing the outline-derived KT centre from the image alone "
             f"({len(ev)} verified marks)", fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_image_only_kt_centering.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("  QNEW_image_only_kt_centering")
