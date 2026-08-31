"""Does the "lagging is the most stretched" result depend on the ELLIPSE FIT?

`kt_shape_metrics._combined_metrics` reports stretch as `aspect_ratio` = major/minor of a `cv2.fitEllipse`
fitted to the traced boundary points. A lagging kinetochore is irregular and often fractured, so an ellipse
is a strong assumption. This re-measures the SAME objects with two FIT-FREE elongations and compares:

  feret_aspect = max caliper diameter / min caliper width  (rotating calipers on the convex hull)
  rect_aspect  = long side / short side of the minimum-area rotated bounding box

and, because an ellipse's major axis is a CHORD, a bendiness check:
  bend = (max caliper diameter) / (length of the object's own boundary between the two caliper endpoints,
         taken the short way round)   -- 1.0 = straight, <1 = the object is curved/banana-shaped, where an
         ellipse necessarily UNDER-states the true extent.
"""
import sys, csv, json, collections
import numpy as np, cv2
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import kt_shape_metrics as K
import lib as _lib
csv.field_size_limit(10 ** 9)


def calipers(pts):
    """max caliper diameter and min caliper width, from the convex hull — no model fitted."""
    h = cv2.convexHull(pts.astype(np.float32)).reshape(-1, 2)
    if len(h) < 3:
        return np.nan, np.nan
    d = np.linalg.norm(h[:, None, :] - h[None, :, :], axis=-1)
    dmax = float(d.max())
    best = np.inf
    for i in range(len(h)):
        e = h[(i + 1) % len(h)] - h[i]
        n = np.linalg.norm(e)
        if n < 1e-9:
            continue
        nrm = np.array([-e[1], e[0]]) / n
        proj = (h - h[i]) @ nrm
        best = min(best, float(proj.max() - proj.min()))
    return dmax, (best if np.isfinite(best) else np.nan)


recs = []
for r in csv.DictReader(open(K.SRC)):
    if r.get("channel") != "fluor":
        continue
    if _lib.kt_outline_excluded(r.get("batch")) or _lib.focus_excluded(r.get("id")):
        continue
    try:
        pts = json.loads(r["points"])
    except Exception:
        continue
    recs.append((r, pts))

groups = collections.OrderedDict()
for r, pts in recs:
    key = ("trace", r.get("id")) if r["label"] in K.SEPARATE_LABELS else \
          (r["batch"], r["label"], r.get("frame"), K.grp_of(r))
    groups.setdefault(key, []).append((r, pts))

out = collections.defaultdict(list)
for key, members in groups.items():
    r0 = members[0][0]
    px = float(r0.get("pixel_size_um") or 0.062)
    pieces = [np.asarray(p, float) for (_, p) in members if np.asarray(p, float).ndim == 2 and len(p) >= 5]
    if not pieces:
        continue
    m = K._combined_metrics([p.tolist() for p in pieces], px)
    if m is None:
        continue
    cap = K.MAX_MAJOR_UM if m["n_pieces"] == 1 else K.MAX_MAJOR_MULTI_UM
    if m["major_um"] > cap:
        continue
    allp = np.vstack(pieces)
    dmax, wmin = calipers(allp)
    if not (np.isfinite(dmax) and np.isfinite(wmin) and wmin > 0):
        continue
    (_c, _s, _a) = cv2.minAreaRect(allp.astype(np.float32))
    rect = max(_s) / min(_s) if min(_s) > 0 else np.nan
    # bendiness: only meaningful for a SINGLE closed piece
    bend = np.nan
    if len(pieces) == 1:
        p = pieces[0]
        d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
        i, j = np.unravel_index(np.argmax(d), d.shape)
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        cum = np.concatenate([[0], np.cumsum(seg)])
        lo, hi = (i, j) if i < j else (j, i)
        a_len = cum[hi] - cum[lo]
        b_len = cum[-1] - a_len
        short = min(a_len, b_len)
        if short > 0:
            bend = float(d[i, j] / short)
    out[r0["label"]].append((m["aspect_ratio"], dmax / wmin, rect, bend))

print(f"{'label':9s} {'n':>5s} {'ELLIPSE aspect':>15s} {'feret aspect':>14s} {'minrect aspect':>15s} {'bend (1=straight)':>19s}")
for lab in ("paired", "polar", "lagging"):
    v = out.get(lab, [])
    if not v:
        continue
    a = np.array([x[0] for x in v]); f = np.array([x[1] for x in v])
    rc = np.array([x[2] for x in v]); b = np.array([x[3] for x in v], float)
    print(f"{lab:9s} {len(v):5d} {np.median(a):15.2f} {np.median(f):14.2f} {np.median(rc):15.2f} {np.nanmedian(b):19.3f}")

from scipy.stats import mannwhitneyu
print()
for metric, idx in (("ELLIPSE aspect", 0), ("feret aspect (fit-free)", 1), ("minrect aspect (fit-free)", 2)):
    L = [x[idx] for x in out["lagging"]]; P = [x[idx] for x in out["paired"]]; O = [x[idx] for x in out["polar"]]
    print(f"{metric:28s} lagging vs paired p={mannwhitneyu(L,P).pvalue:.2e}   "
          f"lagging vs polar p={mannwhitneyu(L,O).pvalue:.2e}   "
          f"medians {np.median(L):.2f} / {np.median(P):.2f} / {np.median(O):.2f}")
