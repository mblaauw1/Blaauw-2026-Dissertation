#!/usr/bin/env python3
"""EQUAL-LENGTH, CENTRED metaphase-plate markers (user 2026-07-28, her algorithm).

Why: the plate line defines the spindle axis and the plate position, but the hand-drawn markers vary in
length and are not consistently centred on the plate, so "movement relative to the spindle axis" and
"distance to plate" inherit that jitter. Her recipe, implemented exactly:

  1. STRAIGHTEN — any marker that is not already a 2-point line is reduced to one, by total-least-squares
     (the principal axis of its points) and taking the extreme projections as the two endpoints.
  2. EQUALISE — within a cell, find the SHORTEST marker and trim every other one to that length, removing
     the same amount from each end (i.e. keeping the midpoint fixed).
  3. CENTRE — slide the trimmed line ALONG ITS OWN DIRECTION so its two ends sit the same distance from the
     cell outline (equally inside, equally outside, or equally overlapping). Distance is signed: positive
     outside the outline, negative inside. Solved by scanning the shift that minimises |d_end1 - d_end2|.
     A frame with no usable cell outline is left un-slid and marked centering=no-outline.

NON-DESTRUCTIVE. annotations/meta_plates.csv is NOT modified. The ORIGINAL endpoints are copied verbatim
into the output and also archived to _retired/ so the normalisation can always be reverted.
Output: annotations/META_PLATE_NORMALIZED_20260728.csv
"""
import sys, os, csv, json, shutil, time, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
SRC = f"{A}/meta_plates.csv"
OUT = f"{A}/META_PLATE_NORMALIZED_20260728.csv"
ARCHIVE = f"{ROOT}/_retired/meta_plates_ORIGINAL_pre_normalize_20260728.csv"


def pts_of(r):
    try:
        p = np.array(json.loads(r["points"]), float)
    except Exception:
        return None
    return p if p.ndim == 2 and len(p) >= 2 else None


def straighten(P):
    """total-least-squares straight line through P -> (endpoint_a, endpoint_b) at the extreme projections."""
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    d = vt[0] / np.linalg.norm(vt[0])
    t = (P - c) @ d
    return c + d * t.min(), c + d * t.max()


def poly_signed_dist_many(P, poly):
    """Vectorised: signed distance for an (N,2) array of points against one polygon.
    + outside, - inside. Replaces the per-point python loop, which made this run for >10 min."""
    A0 = poly; B0 = np.roll(poly, -1, axis=0)
    AB = B0 - A0                                     # (E,2)
    L2 = np.einsum("ij,ij->i", AB, AB)               # (E,)
    L2 = np.where(L2 == 0, 1e-12, L2)
    d = P[:, None, :] - A0[None, :, :]               # (N,E,2)
    t = np.clip(np.einsum("nej,ej->ne", d, AB) / L2[None, :], 0, 1)
    proj = A0[None, :, :] + t[:, :, None] * AB[None, :, :]
    dist = np.min(np.hypot(*(P[:, None, :] - proj).transpose(2, 0, 1)), axis=1)
    # even-odd inside test, vectorised over points
    x = P[:, 0][:, None]; y = P[:, 1][:, None]
    x1 = A0[:, 0][None, :]; y1 = A0[:, 1][None, :]
    x2 = B0[:, 0][None, :]; y2 = B0[:, 1][None, :]
    cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1)
    inside = (cond.sum(axis=1) % 2) == 1
    return np.where(inside, -dist, dist)


def poly_signed_dist(pt, poly):
    """+distance to the outline boundary when OUTSIDE it, -distance when INSIDE."""
    n = len(poly)
    best = np.inf
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        ab = b - a; L2 = float(ab @ ab)
        t = 0.0 if L2 == 0 else float(np.clip((pt - a) @ ab / L2, 0, 1))
        best = min(best, float(np.hypot(*(pt - (a + t * ab)))))
    # even-odd point-in-polygon
    inside = False
    x, y = pt
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            inside = not inside
    return -best if inside else best


plates = [r for r in csv.DictReader(open(SRC, newline="")) if pts_of(r) is not None]
print(f"{len(plates)} plate markers in {len({r['batch'] for r in plates})} cells")

# archive the originals (revertability, her request)
os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
shutil.copy2(SRC, ARCHIVE)
print(f"originals archived -> {ARCHIVE}")

# cell outlines, per (batch, frame)
outlines = collections.defaultdict(list)
try:
    for r in csv.DictReader(open(f"{A}/cell_outlines.csv", newline="")):
        try: P = np.array(json.loads(r["points"]), float)
        except Exception: continue
        if len(P) >= 8 and r["frame"].strip().isdigit():
            outlines[r["batch"]].append((int(r["frame"]), P))
except FileNotFoundError:
    pass
for b in outlines:
    outlines[b].sort(key=lambda z: z[0])   # sort on frame only; arrays are not comparable


def outline_for(batch, frame, max_gap=12):
    v = outlines.get(batch)
    if not v: return None
    f, P = min(v, key=lambda z: abs(z[0] - frame))
    return P if abs(f - frame) <= max_gap else None


# 1) straighten, and collect lengths per cell
straight = {}
for r in plates:
    a, b = straighten(pts_of(r))
    straight[r["id"]] = (a, b, float(np.hypot(*(b - a))))
by_batch = collections.defaultdict(list)
for r in plates:
    by_batch[r["batch"]].append(r)

rows = []
stats = collections.Counter()
for batch, rs in sorted(by_batch.items()):
    Ls = [straight[r["id"]][2] for r in rs]
    target = float(min(Ls))
    for r in rs:
        a, b, L = straight[r["id"]]
        mid = (a + b) / 2.0
        d = (b - a) / (L if L > 0 else 1.0)
        # 2) trim symmetrically to the cell's shortest marker
        a2 = mid - d * target / 2.0
        b2 = mid + d * target / 2.0
        # 3) slide along the line so both ends sit the same signed distance from the cell outline
        mode = "no-outline"
        shift = 0.0
        frame = int(r["frame"]) if r["frame"].strip().isdigit() else None
        poly = outline_for(batch, frame) if frame is not None else None
        if poly is not None:
            span = target * 0.5
            S = np.linspace(-span, span, 121)
            P1 = a2[None, :] + d[None, :] * S[:, None]
            P2 = b2[None, :] + d[None, :] * S[:, None]
            err = np.abs(poly_signed_dist_many(P1, poly) - poly_signed_dist_many(P2, poly))
            shift = float(S[int(np.argmin(err))])
            a2 = a2 + d * shift; b2 = b2 + d * shift
            mode = "centred-on-outline"
        stats[mode] += 1
        rows.append(dict(
            id=r["id"], batch=batch, frame=r["frame"], t_sec=r.get("t_sec", ""),
            orig_points=r["points"],
            orig_x1=round(float(a[0]), 2), orig_y1=round(float(a[1]), 2),
            orig_x2=round(float(b[0]), 2), orig_y2=round(float(b[1]), 2),
            orig_len_px=round(L, 2),
            norm_x1=round(float(a2[0]), 2), norm_y1=round(float(a2[1]), 2),
            norm_x2=round(float(b2[0]), 2), norm_y2=round(float(b2[1]), 2),
            norm_len_px=round(target, 2),
            trimmed_px=round(L - target, 2), slid_px=round(shift, 2),
            n_orig_points=len(pts_of(r)), centering=mode))

cols = ["id", "batch", "frame", "t_sec", "orig_x1", "orig_y1", "orig_x2", "orig_y2", "orig_len_px",
        "norm_x1", "norm_y1", "norm_x2", "norm_y2", "norm_len_px", "trimmed_px", "slid_px",
        "n_orig_points", "centering", "orig_points"]
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
tr = [r["trimmed_px"] for r in rows]; sl = [abs(r["slid_px"]) for r in rows]
multi = sum(1 for r in rows if r["n_orig_points"] > 2)
print(f"wrote {len(rows)} normalised markers -> {OUT}")
print(f"  {multi} were multi-point and were straightened to 2 points")
print(f"  trimmed: median {np.median(tr):.1f} px, max {max(tr):.1f} px")
print(f"  slid:    median {np.median(sl):.1f} px, max {max(sl):.1f} px")
print(f"  centering: {dict(stats)}")
