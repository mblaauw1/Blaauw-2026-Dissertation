"""How faithfully do the stored outlines represent her curved traces?
Two independent sensitivity tests, no assumptions:
 (1) DECIMATION — drop every 2nd/4th/8th vertex and re-measure. If the stored sampling already resolves the
     curve, throwing vertices away changes nothing; if it changes a lot, the sampling was marginal.
 (2) RASTER vs TRACED PERIMETER — the measurement rasterises the polygon (her rule: the line counts as part
     of the object). A rasterised boundary is a staircase, so compare it against the true traced path length.
"""
import sys, csv, json, numpy as np
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import kt_shape_metrics as K
csv.field_size_limit(10**9)
rng = np.random.default_rng(0)

def traced_perim(p):
    q = p if np.allclose(p[0], p[-1]) else np.vstack([p, p[0]])
    return float(np.sum(np.hypot(*np.diff(q, axis=0).T)))

for name, path in (("kt_outlines", "/Volumes/4 MB/annotations/kt_outlines.csv"),
                   ("cell_outlines", "/Volumes/4 MB/annotations/cell_outlines.csv")):
    rows = [r for r in csv.DictReader(open(path))]
    polys = []
    for r in rows:
        try: p = np.asarray(json.loads(r["points"]), float)
        except Exception: continue
        if p.ndim == 2 and len(p) >= 40:
            polys.append((p, float(r.get("pixel_size_um") or 0.062)))
    idx = rng.choice(len(polys), size=min(300, len(polys)), replace=False)
    sample = [polys[i] for i in idx]
    print(f"\n=== {name}: {len(sample)} random traces (>=40 vertices), median {int(np.median([len(p) for p,_ in sample]))} vertices ===")

    print("  (1) DECIMATION sensitivity — median |change| vs the full-resolution measurement")
    print(f"      {'keep':>10} {'area':>10} {'perimeter':>12} {'circularity':>12}")
    base = []
    for p, px in sample:
        m = K._combined_metrics([p], px)
        base.append(m)
    for step in (2, 4, 8):
        da, dp, dc = [], [], []
        for (p, px), b in zip(sample, base):
            if b is None or len(p) // step < 12: continue
            m = K._combined_metrics([p[::step]], px)
            if m is None: continue
            da.append(abs(m["area_um2"] - b["area_um2"]) / b["area_um2"] * 100)
            dp.append(abs(m["perimeter_um"] - b["perimeter_um"]) / b["perimeter_um"] * 100)
            dc.append(abs(m["circularity"] - b["circularity"]) / b["circularity"] * 100)
        print(f"      every {step}nd/th {np.median(da):8.2f}% {np.median(dp):11.2f}% {np.median(dc):11.2f}%")

    print("  (2) RASTER staircase — measured perimeter vs the length of her traced path")
    rat = []
    for (p, px), b in zip(sample, base):
        if b is None: continue
        t = traced_perim(p) * px
        if t > 0: rat.append(b["perimeter_um"] / t)
    rat = np.array(rat)
    print(f"      raster/traced ratio: median {np.median(rat):.3f}  IQR {np.percentile(rat,25):.3f}-{np.percentile(rat,75):.3f}")
