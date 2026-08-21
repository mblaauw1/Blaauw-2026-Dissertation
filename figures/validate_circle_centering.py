#!/usr/bin/env python3
"""Is the circle-marker centering actually landing on the kinetochore? (user 2026-07-28)

For every cell that has BOTH a circle kt_point AND a traced kt_outline on the SAME frame, compare three
candidate centres against the OUTLINE as ground truth:

  raw       the clicked (x,y), used as-is
  peak      lib.snap_to_peak — the brightest pixel within +/-9 px (what the deck currently does)
  centroid  intensity-weighted centre of mass within +/-9 px (the alternative she asked me to try)

Reported per method: distance to the outline centroid, and whether the point falls INSIDE the outline
polygon. A method that is "accidentally moving somewhere random" shows up as a LOWER inside-fraction and a
LONGER tail than raw. Measured on the 16-bit fluor TIF (lib.FluorTif), not on the preview movie.

Writes annotations/CIRCLE_CENTERING_CHECK_20260728.csv + a figure in group7_questions/.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
RAD = 10   # match the deployed lib.snap_to_peak default (2026-07-29); was 9

KT_LABELS = {"polar", "sisterless", "paired_kt", "lagging"}
pts = collections.defaultdict(list)
for r in csv.DictReader(open(f"{A}/kt_points.csv", newline="")):
    if r["label"].strip() not in KT_LABELS:
        continue
    try: pts[r["batch"].strip()].append((int(r["frame"]), float(r["x"]), float(r["y"]), r["label"].strip(), r["id"]))
    except Exception: pass

outl = collections.defaultdict(list)
for r in csv.DictReader(open(f"{A}/kt_outlines.csv", newline="")):
    try: P = np.array(json.loads(r["points"]), float)
    except Exception: continue
    if len(P) < 4 or not r["frame"].strip().isdigit():
        continue
    outl[r["batch"].strip()].append((int(r["frame"]), P, r["label"], float(r.get("pixel_size_um") or 0.062)))

cells = sorted(set(pts) & set(outl))
print(f"{len(cells)} cells have both circle markers and outlines")


def inside(pt, poly):
    x, y = pt; ins = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            ins = not ins
    return ins


def centroid_snap(g, x, y, rad=RAD):
    """intensity-weighted centre of mass in the +/-rad window, after subtracting the window's floor."""
    h, w = g.shape[:2]
    xi, yi = int(round(x)), int(round(y))
    x0, x1 = max(0, xi - rad), min(w, xi + rad + 1)
    y0, y1 = max(0, yi - rad), min(h, yi + rad + 1)
    sub = g[y0:y1, x0:x1].astype(float)
    if sub.size == 0:
        return x, y
    sub = sub - np.percentile(sub, 20)
    sub[sub < 0] = 0
    if sub.sum() <= 0:
        return x, y
    yy, xx = np.mgrid[y0:y1, x0:x1]
    return float((xx * sub).sum() / sub.sum()), float((yy * sub).sum() / sub.sum())


rows = []
for ci, b in enumerate(cells, 1):
    byf = collections.defaultdict(list)
    for f, P, lab, px in outl[b]:
        byf[f].append((P, lab, px))
    ft = None
    for role in ("monitoring", "ablation"):
        try:
            ft = lib.FluorTif(b, role)
            if ft is not None and ft.plane_by_frame(min(byf)) is not None:
                break
        except Exception:
            ft = None
    if ft is None:
        print(f"  [{ci}/{len(cells)}] {b}: no fluor TIF, skipped"); continue
    n = 0
    for f, x, y, lab, pid in pts[b]:
        if f not in byf:
            continue
        g = ft.plane_by_frame(f)
        if g is None:
            continue
        # the outline on this frame whose centroid is nearest the click
        best = None
        for P, olab, px in byf[f]:
            c = lib.polygon_centroid(P)   # AREA centroid, not the biased vertex mean (2026-07-29)
            d = float(np.hypot(c[0] - x, c[1] - y))
            if best is None or d < best[0]:
                best = (d, P, c, olab, px)
        if best is None or best[0] > 40:      # not the same object
            continue
        d0, P, cen, olab, px = best
        sx, sy = lib.snap_to_peak_pixel(g, x, y, RAD)   # legacy, for comparison
        gx, gy = lib.snap_to_peak(g, x, y, RAD)          # the DEPLOYED centering (now centroid)
        rows.append(dict(batch=b, frame=f, point_id=pid, point_label=lab, outline_label=olab,
                         px_um=px,
                         raw_d=round(d0, 2), peak_d=round(float(np.hypot(sx - cen[0], sy - cen[1])), 2),
                         cent_d=round(float(np.hypot(gx - cen[0], gy - cen[1])), 2),
                         raw_in=int(inside((x, y), P)), peak_in=int(inside((sx, sy), P)),
                         cent_in=int(inside((gx, gy), P)),
                         peak_moved=round(float(np.hypot(sx - x, sy - y)), 2),
                         cent_moved=round(float(np.hypot(gx - x, gy - y)), 2)))
        n += 1
    print(f"  [{ci}/{len(cells)}] {b}: {n} matched marks")

if not rows:
    raise SystemExit("no matched marks")
with open(f"{A}/CIRCLE_CENTERING_CHECK_20260728.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

px_um = float(np.median([r["px_um"] for r in rows]))
M = {k: np.array([r[f"{k}_d"] for r in rows]) for k in ("raw", "peak", "cent")}
I = {k: np.array([r[f"{k}_in"] for r in rows]) for k in ("raw", "peak", "cent")}
print(f"\n{len(rows)} matched marks across {len({r['batch'] for r in rows})} cells  (px = {px_um} um)")
for k, name in (("raw", "raw click"), ("peak", "peak-snap (legacy)"), ("cent", "centroid-snap (DEPLOYED)")):
    d = M[k]
    print(f"  {name:22s} median {np.median(d):5.2f} px ({np.median(d)*px_um:.3f} um) | "
          f"p90 {np.percentile(d,90):5.2f} | worst {d.max():6.2f} | inside outline {I[k].mean()*100:5.1f}%")
for k, nm in (("peak", "legacy peak-snap"), ("cent", "DEPLOYED centroid-snap")):
    worse = int((M[k] > M['raw'] + 2).sum()); better = int((M[k] < M['raw'] - 2).sum())
    print(f"  {nm:24s} moved the point >2px AWAY from the KT in {worse:4d} marks "
          f"({worse/len(rows)*100:4.1f}%), >2px CLOSER in {better:4d} ({better/len(rows)*100:4.1f}%)")

fig, axs = plt.subplots(1, 2, figsize=(12.4, 4.8))
C = {"raw": "#999999", "peak": "#d1495b", "cent": "#3b6fb6"}
L = {"raw": "raw click", "peak": "peak-snap (legacy)", "cent": "centroid-snap (DEPLOYED)"}
ax = axs[0]
bins = np.arange(0, 22, 1.0)
for k in ("raw", "peak", "cent"):
    ax.hist(np.clip(M[k], 0, 21), bins=bins, histtype="step", lw=2.0, color=C[k],
            label=f"{L[k]}: med {np.median(M[k]):.2f} px, {I[k].mean()*100:.0f}% inside")
ax.set_xlabel("distance from the OUTLINE centroid (px)"); ax.set_ylabel("# marks")
ax.legend(fontsize=8)
ax.set_title("Is the circle centred on the kinetochore?", loc="left", fontweight="bold", fontsize=10)
ax = axs[1]
ax.scatter(M["raw"], M["peak"], s=8, alpha=0.3, color=C["peak"], lw=0, label="peak-snap")
ax.scatter(M["raw"], M["cent"], s=8, alpha=0.3, color=C["cent"], lw=0, label="centroid-snap")
lim = [0, float(np.percentile(M["raw"], 99)) + 4]
ax.plot(lim, lim, "--", color="#666", lw=1.2)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("raw click -> outline centroid (px)"); ax.set_ylabel("after snapping -> outline centroid (px)")
ax.legend(fontsize=8)
ax.set_title("below the line = snapping improved it", loc="left", fontweight="bold", fontsize=10)
fig.suptitle(f"Circle-marker centering validated against the traced outlines "
             f"({len(rows)} marks, {len({r['batch'] for r in rows})} cells)", fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_circle_centering_validation.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("  QNEW_circle_centering_validation")
