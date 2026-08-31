"""custom_primary_geometry_20260722.py — build REAL geometry from the primary annotation stores.

WHY (user 2026-07-22)
  The model had never seen a single hand-marked coordinate. Its features came from `ablation_plots/data/*.csv`
  — figure OUTPUTS, already aggregated and filtered for plotting. The primary stores are the richer source
  (`_READ_FIRST_DATA_MAP.md` §0: measured geometry is COMPUTED from `annotations/*.csv`, never read from the
  master's sparse columns):
      kt_points     5307 marks / 139 batches   labels: sisterless, polar, lagging, paired_kt, pre_abl, post_abl
      meta_plates   4183 polylines / 77 batches
      cell_outlines 1420 polygons / 184 batches
      chromo_lines   174 polylines / 98 batches
  76 batches have BOTH kinetochore marks and a metaphase plate; 61 have all three.

  Where the old warehouse offered `mean_x`/`sd_x` in pixels — which encodes where the cell sat in the field
  of view, not biology — this builds the quantities that actually mean something:
      distance from the kinetochore to the metaphase plate           (µm)
      signed position along the plate NORMAL                          (µm; which side, how far)
      lateral position along the plate AXIS                           (fraction of plate half-length)
      distance from the cell centroid                                 (fraction of the cell's own radius)
      how all of those move, expressed in MITOTIC PROGRESS

WHAT IT EMITS
  1. `_scratch/primary_geometry_cell.json`  — batch -> {feature: value}, cell level (metaphase-duration task)
  2. `_scratch/primary_geometry_chrom.csv`  — one row per kinetochore/chromosome (plate-vs-polar task),
     INCLUDING WITHIN-CELL RELATIVE FEATURES, which is the point:

     Her established result is that chromosome length predicts staying polar in 2/3-sisterless (p=0.019) but
     NOT in 1-sisterless (p=0.79) — length matters only under COMPETITION. Competition is a statement about
     RANK INSIDE THE CELL, not about micrometres. A model given only absolute length cannot express "the
     longest chromosome in this cell", so it cannot represent the very effect she found. Hence, per cell:
        length_rank, length_rank_frac, length_z_in_cell, length_over_cell_max, length_over_cell_mean,
        is_longest, is_shortest, n_chromo_in_cell        (and the same ranking for the geometry above)

FUNCTIONAL TRAJECTORIES
  Each per-kinetochore series is resampled onto a COMMON MITOTIC-PROGRESS GRID (0 = metaphase onset,
  1 = anaphase onset) at 0, .25, .5, .75, 1. A curve summarised only by `slope` has lost its shape; sampling
  it on a shared grid keeps the shape while staying comparable between a 6-minute and a 50-minute metaphase.

NOT DONE ON PURPOSE
  Cells that never reach anaphase are dropped, per her instruction 2026-07-22 — they have no mitotic-progress
  clock and are excluded from her other analyses too. No survival model.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, re
import numpy as np
from collections import defaultdict
import lib

ANN = "/Volumes/4 MB/annotations"
OUT = "/Volumes/4 MB/_scratch"
GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
PLATE_T_TOL = 40.0         # seconds: how far a KT mark may sit from the nearest marked plate/outline
                           # (acquisition interval is 20 s, so this is +/- 2 timepoints)
csv.field_size_limit(10 ** 8)


# ---------------------------------------------------------------- polygon / axis maths
def parse_pts(s):
    try:
        p = json.loads(s)
    except Exception:
        return None
    a = np.asarray(p, float)
    return a if a.ndim == 2 and a.shape[0] >= 2 and a.shape[1] == 2 else None


def poly_metrics(P, um):
    """area (µm²), perimeter (µm), roundness, centroid (px), equivalent radius (µm).

    The stored area_um2 / roundness columns are EMPTY for these rows, so they are computed here from the
    polygon itself — which is what `_READ_FIRST_DATA_MAP.md` says to do anyway."""
    x, y = P[:, 0], P[:, 1]
    a = 0.5 * float(np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))   # shoelace, px²
    d = np.diff(np.vstack([P, P[:1]]), axis=0)
    per = float(np.sum(np.hypot(d[:, 0], d[:, 1])))                                  # px
    A = a * um * um; Pm = per * um
    rnd = (4.0 * np.pi * A / (Pm * Pm)) if Pm > 0 else np.nan
    return A, Pm, rnd, P.mean(0), (np.sqrt(A / np.pi) if A > 0 else np.nan)


def plate_axis(P):
    """principal axis of the plate polyline: unit direction u, centroid c, half-length (px).

    PCA/SVD, matching how the existing consumers read these marks (group4_tracking_dist.plate_axis) — the
    freehand lines are POLYLINES and must not be flattened to their chord (NOTES: median 0.65 µm curvature)."""
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c, full_matrices=False)
    d = vt[0] / (np.linalg.norm(vt[0]) or 1.0)
    proj = (P - c) @ d
    return d, c, float(max(proj.max(), -proj.min()))


def fnum(s):
    try:
        v = float(s)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- load
def load(store):
    rows = defaultdict(list)
    with open(f"{ANN}/{store}.csv", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            rows[r["batch"].strip()].append(r)
    return rows


KT = load("kt_points"); PL = load("meta_plates"); CO = load("cell_outlines")
master, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in master}


def clock(b):
    """(metaphase_start_s, anaphase_onset_s) or None — the mitotic-progress reference."""
    r = mr.get(b) or {}
    m = lib.parse_time((r.get("Metaphase Start (s)") or "").strip())
    a = lib.parse_time((r.get("Anaphase Onset (s)") or "").strip())
    return (m, a) if (m is not None and a is not None and a > m) else None


def progress(b, t, ck):
    return None if (t is None or ck is None) else (t - ck[0]) / (ck[1] - ck[0])


# ---------------------------------------------------------------- trajectory summarisation
def traj_features(prog, val, tag):
    """One series -> functional features on the shared progress grid + shape descriptors."""
    o = np.argsort(prog); p = np.asarray(prog, float)[o]; v = np.asarray(val, float)[o]
    ok = np.isfinite(p) & np.isfinite(v); p, v = p[ok], v[ok]
    out = {}
    if len(v) == 0:
        return out
    out[f"{tag}|mean"] = float(np.mean(v)); out[f"{tag}|med"] = float(np.median(v))
    out[f"{tag}|min"] = float(np.min(v));   out[f"{tag}|max"] = float(np.max(v))
    out[f"{tag}|range"] = float(np.max(v) - np.min(v))
    out[f"{tag}|sd"] = float(np.std(v))
    if len(v) >= 3:
        out[f"{tag}|volatility"] = float(np.mean(np.abs(np.diff(v))))
    if len(v) >= 2 and np.ptp(p) > 1e-9:
        out[f"{tag}|slope_per_progress"] = float(np.polyfit(p, v, 1)[0])
        # FUNCTIONAL: the curve itself on a common grid, so shape survives
        lo, hi = p.min(), p.max()
        for g in GRID:
            if lo - 0.15 <= g <= hi + 0.15:
                out[f"{tag}|at{g:g}"] = float(np.interp(g, p, v))
        out[f"{tag}|progress_at_max"] = float(p[int(np.argmax(v))])
        out[f"{tag}|progress_at_min"] = float(p[int(np.argmin(v))])
    for nm, lo, hi in (("premeta", -9e9, 0.0), ("meta1", 0.0, 0.5), ("meta2", 0.5, 1.0)):
        m = (p >= lo) & (p < hi)
        if m.sum():
            out[f"{tag}|{nm}_mean"] = float(np.mean(v[m]))
    if f"{tag}|meta1_mean" in out and f"{tag}|meta2_mean" in out:
        out[f"{tag}|meta_half_delta"] = out[f"{tag}|meta2_mean"] - out[f"{tag}|meta1_mean"]
    return out


def rank_features(vals, tag):
    """WITHIN-CELL relative position — the competition representation."""
    v = np.asarray(vals, float); n = len(v)
    out = []
    mu, sd, mx, mn = np.mean(v), np.std(v), np.max(v), np.min(v)
    order = np.argsort(np.argsort(-v))          # 0 = largest
    for i in range(n):
        out.append({
            f"{tag}_rank": float(order[i]),
            f"{tag}_rank_frac": float(order[i] / (n - 1)) if n > 1 else 0.0,
            f"{tag}_z_in_cell": float((v[i] - mu) / sd) if sd > 0 else 0.0,
            f"{tag}_over_cell_max": float(v[i] / mx) if mx else np.nan,
            f"{tag}_over_cell_mean": float(v[i] / mu) if mu else np.nan,
            f"{tag}_minus_cell_mean": float(v[i] - mu),
            f"is_largest_{tag}": 1.0 if v[i] == mx else 0.0,
            f"is_smallest_{tag}": 1.0 if v[i] == mn else 0.0,
            f"n_in_cell_{tag}": float(n),
            f"cell_spread_{tag}": float(mx - mn),
        })
    return out


# ---------------------------------------------------------------- main build
def build():
    cell_feats = {}
    chrom_rows = []
    stats = defaultdict(int)

    for b in sorted(set(KT) | set(CO)):
        ck = clock(b)
        if ck is None:
            stats["no mitotic clock (dropped, per her rule)"] += 1
            continue

        # ---- cell outline trajectory (area / roundness / radius), computed from the polygons
        cser = defaultdict(list)
        centro, radius = {}, {}
        for r in CO.get(b, []):
            P = parse_pts(r.get("points") or ""); um = fnum(r.get("pixel_size_um")); t = fnum(r.get("t_sec"))
            if P is None or not um or t is None:
                continue
            A, Pm, rnd, cen, rad = poly_metrics(P, um)
            g = progress(b, t, ck)
            if g is None:
                continue
            cser["cell_area_um2"].append((g, A)); cser["cell_perimeter_um"].append((g, Pm))
            cser["cell_roundness"].append((g, rnd))
            centro[float(t)] = cen; radius[float(t)] = rad

        feats = {}
        for k, sers in cser.items():
            feats.update(traj_features([p for p, _ in sers], [v for _, v in sers], k))

        # ---- plate geometry per frame
        plate = {}
        for r in PL.get(b, []):
            P = parse_pts(r.get("points") or ""); um = fnum(r.get("pixel_size_um")); ts = fnum(r.get("t_sec"))
            if P is None or not um or ts is None:
                continue
            d, c, half = plate_axis(P)
            plate[float(ts)] = (d, c, half, um)
            g = progress(b, ts, ck)
            if g is not None:
                cser.setdefault("_plate_len", []).append((g, 2 * half * um))
        if "_plate_len" in cser:
            feats.update(traj_features([p for p, _ in cser["_plate_len"]],
                                       [v for _, v in cser["_plate_len"]], "plate_length_um"))

        # PLATE AS A CONTINUOUS FUNCTION OF TIME — **t_sec, NOT frame**.
        # `frame` is numbered PER PHASE / per video file: a mark at abl-frame 23 and a mark at mon-frame 23
        # are different instants, and kt_points spans {abl, mon, ''} while meta_plates is mostly {'', mon}.
        # Matching them by frame silently compared different movies — the same class of error as the
        # TrackMate rule in NOTES ("JOIN BY TIME, NEVER BY FRAME"). t_sec is the one global clock, and it is
        # the field that was repaired on 2026-07-22, so it is now trustworthy.
        # Nearest-plate-within-2-frames threw away 711 of 828 kinetochore marks, because the plate and the
        # kinetochores were not always marked on the same frames. The plate translates and rotates smoothly,
        # so interpolating its centroid, its angle and its half-length between marked frames uses the marks
        # she actually made instead of discarding them. Interpolation only — never extrapolated beyond the
        # first and last marked plate frame.
        pframes = np.array(sorted(plate), float) if plate else np.array([])
        if len(pframes) >= 2:
            _cx = np.array([plate[f][1][0] for f in pframes])
            _cy = np.array([plate[f][1][1] for f in pframes])
            _ang = np.unwrap([np.arctan2(plate[f][0][1], plate[f][0][0]) * 2 for f in pframes]) / 2
            _half = np.array([plate[f][2] for f in pframes])
            _um = np.array([plate[f][3] for f in pframes])

            def plate_at(fr):
                if fr < pframes[0] or fr > pframes[-1]:
                    return None
                a = float(np.interp(fr, pframes, _ang))
                return (np.array([np.cos(a), np.sin(a)]),
                        np.array([float(np.interp(fr, pframes, _cx)), float(np.interp(fr, pframes, _cy))]),
                        float(np.interp(fr, pframes, _half)), float(np.interp(fr, pframes, _um)))
        elif len(pframes) == 1:
            def plate_at(fr):
                return plate[float(pframes[0])] if abs(fr - pframes[0]) <= PLATE_T_TOL else None
        else:
            def plate_at(fr):
                return None

        # ---- kinetochore marks -> geometry relative to plate and cell
        per_kt = defaultdict(lambda: defaultdict(list))     # (label, kt_num) -> series
        for r in KT.get(b, []):
            lab = (r.get("label") or "").strip()
            if lab in ("cytosol_bg",):
                continue
            x, y = fnum(r.get("x")), fnum(r.get("y")); fr = fnum(r.get("frame")); t = fnum(r.get("t_sec"))
            um = fnum(r.get("pixel_size_um"))
            if x is None or y is None or fr is None or not um:
                continue
            g = progress(b, t, ck)
            if g is None:
                continue
            m = re.search(r"kt:(\d+)", r.get("notes") or "")
            key = (lab, int(m.group(1)) if m else 0)
            p = np.array([x, y])

            if len(pframes):
                _pa = plate_at(t)
                if _pa is not None:
                    d, c, half, pum = _pa
                    rel = p - c
                    nrm = np.array([-d[1], d[0]])
                    signed = float(rel @ nrm) * pum
                    per_kt[key]["dist_to_plate_um"].append((g, abs(signed)))
                    per_kt[key]["signed_normal_um"].append((g, signed))
                    per_kt[key]["dist_to_plate_centroid_um"].append((g, float(np.hypot(*rel)) * pum))
                    if half > 0:
                        per_kt[key]["lateral_frac"].append((g, float(rel @ d) / half))
                else:
                    stats["KT mark outside the marked plate frame range"] += 1

            if centro:
                _ct = np.array(sorted(centro), float)
                _j = float(_ct[np.argmin(np.abs(_ct - t))])
                if abs(_j - t) <= PLATE_T_TOL and np.isfinite(radius.get(_j, np.nan)) and radius[_j] > 0:
                    per_kt[key]["dist_from_cell_centre_frac"].append(
                        (g, float(np.hypot(*(p - centro[_j]))) * um / radius[_j]))

        # ---- per-kinetochore trajectory features, then cell-level aggregation
        kt_summ = {}
        for (lab, num), sers in per_kt.items():
            f = {}
            for metric, s in sers.items():
                f.update(traj_features([p for p, _ in s], [v for _, v in s], metric))
            # speed along the plate normal, in mitotic-progress units
            s = sers.get("signed_normal_um") or []
            if len(s) >= 3:
                o = sorted(s)
                dv = np.diff([v for _, v in o]); dp = np.diff([p for p, _ in o])
                ok = dp > 1e-9
                if ok.sum():
                    f["normal_speed_um_per_progress|mean"] = float(np.mean(np.abs(dv[ok] / dp[ok])))
                    f["normal_direction_switches|n"] = float(np.sum(np.diff(np.sign(dv[ok])) != 0))
            if f:
                kt_summ[(lab, num)] = f

        for lab in {l for l, _ in kt_summ}:
            group = [f for (l, _), f in kt_summ.items() if l == lab]
            keys = {k for f in group for k in f}
            for k in keys:
                vals = [f[k] for f in group if k in f]
                if not vals:
                    continue
                feats[f"kt.{lab}.{k}|cellmean"] = float(np.mean(vals))
                feats[f"kt.{lab}.{k}|cellmax"] = float(np.max(vals))
                feats[f"kt.{lab}.{k}|cellmin"] = float(np.min(vals))
                if len(vals) > 1:
                    feats[f"kt.{lab}.{k}|cellspread"] = float(np.max(vals) - np.min(vals))
            feats[f"kt.{lab}|n_marked"] = float(len(group))

        if feats:
            cell_feats[b] = feats
            stats["cells with geometry"] += 1

        # ---- per-kinetochore rows with WITHIN-CELL RANK (plate-vs-polar task)
        marks = [(lab, num, f) for (lab, num), f in kt_summ.items()
                 if lab in ("sisterless", "polar", "lagging", "paired_kt")]
        if marks:
            base = "dist_to_plate_um|mean"
            have = [m for m in marks if base in m[2]]
            ranks = rank_features([m[2][base] for m in have], "dist_to_plate") if have else []
            rk = {(m[0], m[1]): r for m, r in zip(have, ranks)}
            for lab, num, f in marks:
                row = {"batch": b, "label": lab, "kt_num": num}
                row.update(f)
                row.update(rk.get((lab, num), {}))
                chrom_rows.append(row)

    return cell_feats, chrom_rows, stats


# ---------------------------------------------------------------- chromosome lengths, ranked in-cell
def chromosome_rank_table():
    """CHROMOSOME_MASTER lengths turned into WITHIN-CELL relative features (the competition fix)."""
    by = defaultdict(list)
    for r in csv.DictReader(open(f"{ANN}/CHROMOSOME_MASTER.csv", encoding="utf-8", errors="replace")):
        L = fnum(r.get("length_um"))
        if L is None:
            continue
        by[r["batch"].strip()].append((r, L))
    out = []
    for b, rs in by.items():
        rk = rank_features([L for _, L in rs], "length")
        for (r, L), k in zip(rs, rk):
            row = {"batch": b, "chr_num": r.get("chr_num", ""), "length_um": L,
                   "behavior": (r.get("behavior") or "").strip(),
                   "n_sisterless": (r.get("n_sisterless") or "").strip()}
            row.update(k)
            out.append(row)
    return out


if __name__ == "__main__":
    cf, cr, st = build()
    ct = chromosome_rank_table()
    os.makedirs(OUT, exist_ok=True)
    json.dump(cf, open(f"{OUT}/primary_geometry_cell.json", "w"))

    def dump(rows, path):
        keys = sorted({k for r in rows for k in r})
        keys = [k for k in ("batch", "label", "kt_num", "chr_num") if k in keys] + \
               [k for k in keys if k not in ("batch", "label", "kt_num", "chr_num")]
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys); w.writeheader()
            for r in rows:
                w.writerow(r)
        return keys

    k1 = dump(cr, f"{OUT}/primary_geometry_chrom.csv")
    k2 = dump(ct, f"{OUT}/primary_chromosome_ranks.csv")

    nfeat = len({k for f in cf.values() for k in f})
    print(f"CELL-LEVEL   {len(cf)} batches, {nfeat} geometry features -> primary_geometry_cell.json")
    print(f"KT-LEVEL     {len(cr)} kinetochore rows, {len(k1)} columns -> primary_geometry_chrom.csv")
    print(f"CHROMOSOMES  {len(ct)} rows from CHROMOSOME_MASTER with within-cell ranks "
          f"-> primary_chromosome_ranks.csv")
    print("\nbuild notes:")
    for k, v in sorted(st.items(), key=lambda kv: -kv[1]):
        print(f"   {v:6d}  {k}")
    ex = sorted({k for f in cf.values() for k in f})
    print(f"\nexample geometry features ({len(ex)}):")
    for e in ex[:14]:
        print("   ", e)
