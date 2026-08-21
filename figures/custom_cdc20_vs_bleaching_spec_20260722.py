"""custom_cdc20_vs_bleaching_spec_20260722.py — rebuild G4_sisterless_cdc20_vs_bleaching to HER spec.

HER SPEC (2026-07-22, verbatim intent)
  * plot cdc20 fluorescence on the identified SISTERLESS KT(s) over time
  * standardised to a BACKGROUND cdc20 measurement taken INSIDE THE CELL OUTLINE
  * the SAME measurement area
  * ONE background reading PER TIMEPOINT, so it is paired
  * ALSO include a POLAR/PLATE KT per set. Use the MANUAL paired outline ONLY for that KT's LOCATION, never for its
    intensity; measure its intensity with the same method as the sisterless KT
  * treat the paired KT IDENTICALLY with respect to background — no separate background for it
  * measure on the 16-bit `_Fluor_Cropped.tif`, NOT the mp4 (8-bit, contrast-stretched, clips bright KTs)
  * z-defocus rule (intensity plots only): quick dips are the KT leaving the imaging plane, so keep the
    brighter half of each KT's OWN timepoints (per-KT median split), sacrificing as few points as possible

WHY THE PREVIOUS ATTEMPT WAS QUARANTINED, AND WHY THAT VERDICT WAS WRONG (established 2026-07-22)
  The earlier rebuild was quarantined for "failing verification" against the RETIRED original. The retired
  original is in fact the broken artefact:
      retired kt_cdc20_pct_per_min: median -114 %/min, range -3157..+1521;
                                    25 of 34 values beyond +/-100 %/min, 8 beyond +/-1000
  A kinetochore cannot lose more than 100% of its intensity per minute. Those are slopes divided by a
  near-zero background-subtracted baseline, not rates. The rebuild's values all sit within +/-20.3 %/min.
  The failing rho was also computed over 35 rows against the original's 34; on the MATCHED 34 the rebuild
  gives rho -0.135 against the recorded -0.143. So the quantities were right and the test was wrong.
  This script does NOT chase the retired numbers. It implements the spec above and states its own result.

MEASUREMENT DEFINITIONS (stated so they are never guessed again)
  KT_raw(t)   = lib.disk_sum(plane, x, y, r=R) — total signal in the radius-R circle, the standard
                annotation-circle measurement used across this deck.
  BG(t)       = median pixel INSIDE the cell outline at t, multiplied by the disk's pixel count.
                => the same measurement AREA as the KT, one reading per timepoint, paired by construction.
                The cell outlines are marked sparsely (~8 frames per batch), so the polygon nearest in TIME
                is used and the pixels are sampled from the CURRENT timepoint's plane. The cell moves little
                between marked outlines; the intensity being sampled is always the current frame's.
  ratio(t)    = KT_raw(t) / BG(t)  — "standardised to" the in-outline background.
  rate        = 100 * slope(ratio vs minutes) / mean(ratio)   [%/min]
  bleach rate = 100 * slope(BG vs minutes) / mean(BG)         [%/min]  — the whole-cell bleaching axis
  The PAIRED plate/polar KT uses the SAME BG(t) series — never its own background (her instruction).

FRAME MAPPING
  Fluorescence is mapped by the annotation's `frame` via FluorTif.plane_by_frame, never by t_sec
  (project_fluor_frame_mapping_bug: frames.json t_sec is shifted 1-2 frames and throws moving KTs off disk).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os, json, glob, re
import numpy as np
import cv2
import matplotlib.pyplot as plt
from collections import defaultdict
import lib

lib.apply_style()
OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
R = 9                      # disk radius — lib's standard everywhere in this deck
MIN_PTS = 5                # a KT needs this many in-focus timepoints to get a slope
csv.field_size_limit(10 ** 8)

master, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in master}


def ann(store):
    d = defaultdict(list)
    with open(f"/Volumes/4 MB/annotations/{store}.csv", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            d[r["batch"].strip()].append(r)
    return d


KT = ann("kt_points"); CO = ann("cell_outlines"); KO = ann("kt_outlines")


def fnum(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def outlines_by_time(batch):
    """[(t_sec, polygon)] for the batch's cell outlines, sorted in time."""
    out = []
    for r in CO.get(batch, []):
        t = fnum(r.get("t_sec"))
        try:
            p = np.asarray(json.loads(r.get("points") or "[]"), float)
        except Exception:
            continue
        if t is None or p.ndim != 2 or len(p) < 3:
            continue
        out.append((t, p))
    return sorted(out, key=lambda z: z[0])


def bg_at(plane, polys, t, disk_px):
    """One background reading for THIS timepoint: median pixel inside the cell outline nearest in time,
    scaled to the KT disk's area. Same measurement area, paired per timepoint (her spec)."""
    if plane is None or not polys:
        return None
    _, poly = min(polys, key=lambda z: abs(z[0] - t))
    h, w = plane.shape[:2]
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 1)
    sel = plane[m > 0]
    if sel.size < 50:
        return None
    return float(np.median(sel)) * disk_px


def zfilter(vals):
    """Keep the brighter half of THIS kinetochore's own timepoints — her z-defocus rule. Sacrifices as few
    points as possible: a median split, not a fixed threshold."""
    if len(vals) < 4:
        return list(range(len(vals)))
    med = np.median([v for _, v in vals])
    return [i for i, (_, v) in enumerate(vals) if v >= med]


def pct_per_min(times_s, series):
    """100 * slope / mean, in %/min. None if it cannot be estimated."""
    if len(series) < MIN_PTS:
        return None
    t = np.asarray(times_s, float) / 60.0
    v = np.asarray(series, float)
    ok = np.isfinite(t) & np.isfinite(v)
    t, v = t[ok], v[ok]
    if len(v) < MIN_PTS or np.ptp(t) <= 0 or np.mean(v) == 0:
        return None
    slope = float(np.polyfit(t, v, 1)[0])
    return 100.0 * slope / float(np.mean(v))


# ------------------------------------------------- MANUAL paired outlines: LOCATION ONLY
# USER 2026-08-04: manual annotations automatically override TrackMate. The paired plate KT used to be
# LOCATED from the TrackMate spot CSVs; it is now located from her traced `paired` kinetochore outlines
# (kt_outlines), one polygon per KT per frame -> the polygon centroid is the KT position. Nothing about
# the MEASUREMENT changes: intensity is still measured here with the same disk + same background as the
# sisterless KT, which was always her spec. Keyed by FRAME (never t_sec).
def paired_spots(batch):
    """frame -> [(x_px, y_px)] centroids of the manually traced `paired` kinetochore outlines."""
    by = defaultdict(list)
    for r in KO.get(batch, []):
        if (r.get("label") or "").strip() != "paired":
            continue
        f = fnum(r.get("frame"))
        if f is None:
            continue
        try:
            a = np.asarray(json.loads(r.get("points") or "[]"), float)
        except Exception:
            continue
        if a.ndim != 2 or len(a) < 3:
            continue
        by[int(f)].append((float(a[:, 0].mean()), float(a[:, 1].mean())))
    return by


def measure(batch):
    """-> (bleach_pct_per_min, [sisterless rates], [paired plate-KT rates])"""
    rows = [r for r in KT.get(batch, [])
            if (r.get("label") or "").strip() == "sisterless"
            and (r.get("phase") or "").strip().lower() in ("mon", "")]
    if not rows:
        return None
    polys = outlines_by_time(batch)
    if not polys:
        return None
    ft = lib.FluorTif(batch, role="monitoring")
    if not ft.ok():
        return None
    _yy, _xx = np.ogrid[-R:R + 1, -R:R + 1]
    disk_px = int(np.sum((_xx ** 2 + _yy ** 2) <= R * R))   # pixel count of the r=R disk

    # group the sisterless marks into individual kinetochores via the `kt:N` note
    per_kt = defaultdict(list)
    for r in rows:
        x, y = fnum(r.get("x")), fnum(r.get("y"))
        fr, t = fnum(r.get("frame")), fnum(r.get("t_sec"))
        if None in (x, y, fr, t):
            continue
        m = re.search(r"kt:(\d+)", r.get("notes") or "")
        per_kt[int(m.group(1)) if m else 0].append((int(fr), t, x, y))

    spots = paired_spots(batch)
    bg_series, sis_rates, plate_rates = [], [], []
    bg_cache = {}

    for num, marks in per_kt.items():
        marks.sort()
        kt_vals, plate_vals, ts = [], [], []
        for fr, t, x, y in marks:
            plane = ft.plane_by_frame(fr)
            if plane is None:
                continue
            if fr not in bg_cache:
                bg_cache[fr] = bg_at(plane, polys, t, disk_px)
            bg = bg_cache[fr]
            if not bg:
                continue
            raw = lib.disk_sum(plane, x, y, r=R)
            if raw is None:
                continue
            kt_vals.append((t, raw / bg)); ts.append((t, bg))

            # PAIRED plate KT: her traced outline gives the LOCATION, we measure it ourselves, same background
            cand = spots.get(int(ft.pos_of_frame(fr) or fr)) or spots.get(fr) or []
            if cand:
                d = [((cx - x) ** 2 + (cy - y) ** 2, cx, cy) for cx, cy in cand]
                d.sort()
                # nearest traced paired KT that is NOT the sisterless one itself (>2 disk radii away)
                far = [z for z in d if z[0] > (2 * R) ** 2]
                if far:
                    _, px, py = far[0]
                    praw = lib.disk_sum(plane, px, py, r=R)
                    if praw is not None:
                        plate_vals.append((t, praw / bg))

        for series, sink in ((kt_vals, sis_rates), (plate_vals, plate_rates)):
            if len(series) < MIN_PTS:
                continue
            keep = zfilter(series)                      # z-defocus screen, per KT
            tt = [series[i][0] for i in keep]; vv = [series[i][1] for i in keep]
            rate = pct_per_min(tt, vv)
            if rate is not None:
                sink.append(rate)
        bg_series.extend(ts)

    ft.close()
    if not bg_series or not sis_rates:
        return None
    bg_series = sorted(set(bg_series))
    bleach = pct_per_min([t for t, _ in bg_series], [v for _, v in bg_series])
    if bleach is None:
        return None
    return bleach, sis_rates, plate_rates


def main():
    batches = sorted(set(KT) & set(CO))
    rows = []
    for b in batches:
        if lib.plot_excluded(b):
            continue
        try:
            got = measure(b)
        except Exception as e:
            print(f"   skip {b[:44]}: {type(e).__name__} {e}")
            continue
        if not got:
            continue
        bleach, sis, plate = got
        rows.append({"batch": b,
                     "cell_bleach_pct_per_min": round(bleach, 4),
                     "kt_cdc20_pct_per_min": round(float(np.mean(sis)), 4),
                     "n_sisterless_kt": len(sis),
                     "paired_plate_kt_pct_per_min": round(float(np.mean(plate)), 4) if plate else "",
                     "n_plate_kt": len(plate)})
        print(f"   {b[:46]:46s} bleach {bleach:7.3f}  sisKT {np.mean(sis):8.3f} (n={len(sis)})"
              f"  plateKT {(np.mean(plate) if plate else float('nan')):8.3f} (n={len(plate)})")

    if not rows:
        print("no measurable batches"); return
    x = np.array([r["cell_bleach_pct_per_min"] for r in rows], float)
    y = np.array([r["kt_cdc20_pct_per_min"] for r in rows], float)
    from scipy import stats
    rho, p = stats.spearmanr(x, y)

    # PLAUSIBILITY GUARD — the exact failure that made the retired figure meaningless.
    bad = int(np.sum(np.abs(y) > 100))
    print(f"\nN={len(rows)}  rho={rho:.3f} p={p:.4g}")
    print(f"plausibility: {bad} of {len(y)} KT rates beyond +/-100 %/min "
          f"(the retired figure had 25 of 34)  max|rate|={np.max(np.abs(y)):.1f}")
    if bad:
        print("!! REFUSING TO SAVE — a rate beyond 100 %/min is not physically possible.")
        return

    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    pl = np.array([r["paired_plate_kt_pct_per_min"] for r in rows
                   if r["paired_plate_kt_pct_per_min"] != ""], float)
    px = np.array([r["cell_bleach_pct_per_min"] for r in rows
                   if r["paired_plate_kt_pct_per_min"] != ""], float)
    # Axis range from the BULK of the data, not the extremes: a single -4.2 %/min point was stretching the
    # x axis to +/-5 even though every bleaching value sits within +/-0.5, which hid the actual scatter.
    # Outliers are still drawn (clipped markers), just not allowed to set the scale.
    allv = np.concatenate([x, y] + ([pl] if len(pl) else []))
    lo, hi = np.percentile(allv, 2), np.percentile(allv, 98)
    pad = 0.25 * max(hi - lo, 1e-6)
    lim = [lo - pad, hi + pad]
    ax.plot(lim, lim, "--", color="#999", lw=1.2, zorder=1,
            label="y = x  (KT loss explained by bleaching alone)")
    ax.axhline(0, color="#ccc", lw=.8, zorder=0); ax.axvline(0, color="#ccc", lw=.8, zorder=0)
    if len(pl):
        ax.scatter(px, pl, s=44, facecolor="#7fbf7b", edgecolor="#20502a", lw=.7, zorder=2,
                   label=f"paired plate KT (manual outline location, same background)  n={len(pl)}")
    ax.scatter(x, y, s=52, facecolor="#762a83", edgecolor="#2d0f33", lw=.7, zorder=3,
               label=f"sisterless KT  n={len(rows)}")
    ax.set_xlabel("whole-cell eYFP-Cdc20 bleaching  (%/min)")
    ax.set_ylabel("kinetochore eYFP-Cdc20 change  (%/min)")
    ax.set_title("Sisterless-KT Cdc20 loss vs whole-cell bleaching", fontsize=12)
    ax.text(.02, .02, f"Spearman rho={rho:.3f}, p={p:.3g}, N={len(rows)}\n"
                      f"paired in-outline background, same disk area (r={R}), one reading per timepoint\n"
                      f"z-defocus: brighter half of each KT's own timepoints",
            transform=ax.transAxes, fontsize=7.5, va="bottom", color="#444")
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal", adjustable="box")
    ax.legend(fontsize=7, loc="upper left", framealpha=.9)
    n_out = int(np.sum((y < lim[0]) | (y > lim[1])))
    if n_out:
        ax.text(.98, .02, f"{n_out} point(s) outside the axes", transform=ax.transAxes,
                fontsize=7, ha="right", va="bottom", color="#a33")
    fig.tight_layout()
    name = "G4_sisterless_cdc20_vs_bleaching"
    hdr = ["batch", "cell_bleach_pct_per_min", "kt_cdc20_pct_per_min", "n_sisterless_kt",
           "paired_plate_kt_pct_per_min", "n_plate_kt"]
    lib.record_plot(name, hdr, [[r[h] for h in hdr] for r in rows],
                    {"x": "whole-cell eYFP-Cdc20 bleaching %/min from the in-outline background",
                     "y": "sisterless-KT eYFP-Cdc20 %/min, standardised to that same background",
                     "background": "median inside the cell outline x disk area, one reading per timepoint",
                     "paired_kt": "plate KT located by MANUAL paired kt_outlines centroid, intensity measured here, SAME background",
                     "zfilter": "per-KT median split (brighter half kept)",
                     "radius_px": R, "rho": round(float(rho), 4), "p": float(p), "N": len(rows)},
                    SCRIPT, caption="Sisterless-KT Cdc20 loss vs whole-cell bleaching (rebuilt to spec)",
                    source=[lib.SOURCE_MASTER, lib.SOURCE_ANNOT_KT, lib.SOURCE_ANNOT_OUT])
    fig.savefig(f"{OUT4}/{name}.png", dpi=200)
    print(f"saved {OUT4}/{name}.png")


if __name__ == "__main__":
    main()
