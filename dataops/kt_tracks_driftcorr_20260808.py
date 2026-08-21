#!/usr/bin/env python3
"""Drift-corrected kinetochore track coordinates.

Reads `KT_OUTLINE_TRACKS_20260723.csv`, removes the per-frame common-mode (stage + whole-cell) translation
measured in `stage_drift_from_marks_20260808.py`, and writes `KT_TRACKS_DRIFTCORR_20260808.csv` with the
corrected coordinates ALONGSIDE the originals so nothing is lost and any change is auditable.

WHY: common-mode motion accounts for 38% of the median measured kinetochore displacement (0.481 -> 0.298 um),
with a 29.2 um single-frame jump in `20250826 test_ablation_8` -- a kinetochore cannot move 29 um between
frames, so that is the stage. Every plot deriving speed / displacement / oscillation from absolute
`cx_px`/`cy_px` is inflated until this is removed.

METHOD. For each frame transition, the median displacement vector across all objects tracked on BOTH frames
is the common mode (median, not mean, so genuinely-moving kinetochores cannot drag it). Integrating those
per-transition vectors along the frame sequence gives a cumulative offset per frame; subtracting it from the
raw position yields coordinates in a drift-free frame.

WHAT IS DELIBERATELY *NOT* DONE:
* A transition with fewer than 3 simultaneously tracked objects cannot identify a common mode. Its
  increment is set to ZERO (offset carried forward unchanged) and the frame is flagged
  `corr_identifiable=0`. Guessing there would invent movement.
* The correction is per BATCH -- offsets are never shared across batches.
* Absolute position within the ROI is not meaningful after correction (it is drift-free, not
  stage-registered); only DISPLACEMENTS between frames are. That is exactly what the movement plots use.

CAVEAT WORTH KNOWING: the common mode contains stage motion AND any true rigid translation of the whole
cell. For intra-cell kinetochore dynamics -- which is what every affected plot measures -- removing both is
correct. It would NOT be correct for a plot about how the cell itself migrates.
"""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
SRC = A + "KT_OUTLINE_TRACKS_20260723.csv"
OUT = A + "KT_TRACKS_DRIFTCORR_20260808.csv"
MIN_OBJ = 3

rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8", errors="replace")))
hdr = list(rows[0].keys())
print(f"track rows: {len(rows)}")

full, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in full}

# batch -> frame -> {track_id: (x,y)}
per = collections.defaultdict(lambda: collections.defaultdict(dict))
for r in rows:
    try:
        per[r["batch"].strip()][int(r["frame"])][r["track_id"]] = (float(r["cx_px"]), float(r["cy_px"]))
    except Exception:
        pass

# cumulative offset per (batch, frame)
OFF, IDENT = {}, {}
for b, frames in per.items():
    fs = sorted(frames)
    cum = np.zeros(2)
    OFF[(b, fs[0])] = cum.copy(); IDENT[(b, fs[0])] = 1
    for f0, f1 in zip(fs, fs[1:]):
        a, c = frames[f0], frames[f1]
        common = sorted(set(a) & set(c))
        if len(common) >= MIN_OBJ:
            d = np.array([[c[t][0] - a[t][0], c[t][1] - a[t][1]] for t in common], float)
            cum = cum + np.median(d, axis=0)
            IDENT[(b, f1)] = 1
        else:
            IDENT[(b, f1)] = 0          # not identifiable -> carry the offset forward unchanged
        OFF[(b, f1)] = cum.copy()

out_rows, nident = [], 0
for r in rows:
    b = r["batch"].strip()
    try:
        fr = int(r["frame"]); x = float(r["cx_px"]); y = float(r["cy_px"])
    except Exception:
        continue
    off = OFF.get((b, fr), np.zeros(2))
    ident = IDENT.get((b, fr), 0)
    nident += ident
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    out_rows.append([r["track_id"], b, r["label"], fr, r["t_sec"],
                     f"{x:.4f}", f"{y:.4f}",
                     f"{x-off[0]:.4f}", f"{y-off[1]:.4f}",
                     f"{off[0]:.4f}", f"{off[1]:.4f}", ident, f"{ps:.4f}"])

with open(OUT, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["track_id", "batch", "label", "frame", "t_sec",
                "cx_px_raw", "cy_px_raw", "cx_px_corr", "cy_px_corr",
                "cum_off_x_px", "cum_off_y_px", "corr_identifiable", "pixel_size_um"])
    w.writerows(out_rows)
print(f"wrote {OUT}  ({len(out_rows)} rows)")
print(f"  frames with an identifiable common mode: {nident}/{len(out_rows)} "
      f"({100*nident/max(len(out_rows),1):.1f}%)")

# ---- what changed, per track: total path length raw vs corrected ---------------------------------
byt = collections.defaultdict(list)
for r in out_rows:
    # t_sec is blank on a few track rows -> order by FRAME, which is always present. Sorting by a
    # float() of an empty t_sec is what crashed the first run.
    try:
        t = float(r[4]) if str(r[4]).strip() else float(r[3])
    except Exception:
        t = float(r[3])
    byt[(r[1], r[0])].append((t, float(r[5]), float(r[6]), float(r[7]), float(r[8]), float(r[12])))
raw_tot, cor_tot = [], []
for k, v in byt.items():
    v.sort()
    if len(v) < 2:
        continue
    ps = v[0][5]
    rt = sum(np.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(v, v[1:])) * ps
    ct = sum(np.hypot(b[3] - a[3], b[4] - a[4]) for a, b in zip(v, v[1:])) * ps
    raw_tot.append(rt); cor_tot.append(ct)
raw_tot = np.array(raw_tot); cor_tot = np.array(cor_tot)
print(f"\n=== total path length per track ({len(raw_tot)} tracks) ===")
print(f"  raw       median {np.median(raw_tot):7.3f} um   mean {raw_tot.mean():7.3f}")
print(f"  corrected median {np.median(cor_tot):7.3f} um   mean {cor_tot.mean():7.3f}")
if np.median(raw_tot) > 0:
    print(f"  -> median path length falls {100*(1-np.median(cor_tot)/np.median(raw_tot)):.1f}% once "
          f"common-mode motion is removed")
infl = np.argsort(-(raw_tot - cor_tot))[:8]
ks = [k for k, v in byt.items() if len(v) >= 2]
print("\n=== tracks most inflated by drift ===")
for i in infl:
    b, t = ks[i]
    print(f"   {b[:46]:46s} track {t:>6s}  raw {raw_tot[i]:7.2f} -> corr {cor_tot[i]:7.2f} um")
