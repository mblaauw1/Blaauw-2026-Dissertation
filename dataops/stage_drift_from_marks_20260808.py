#!/usr/bin/env python3
"""Measure stage/common-mode motion per frame from HER OWN MARKS, and quantify how much it skews movement.

USER 2026-08-08: "sometimes the stage of the microscope where the cells are being imaged will move in x-y,
thus moving the cell in the ROI. this stage movement should definitely be present in the video metadata, so
use it to make sure that when stage emovement happens, its not affecting calculations for the movement
patterns of kinetochores, cells, etc" ... "troubleshoot this as its important to not skew values because of
scope movement"

WHY NOT THE METADATA (checked, not assumed):
  * `<batch>_frames.json` carries NO stage fields.
  * `*_frame_data.csv` HAS `stage_x_um`/`stage_y_um`/`crop_shift_dx_px` -- but only 73 exist on 4 MB and in
    ALL 73 the stage columns are BLANK and crop-shift is 0. Those files were written by the OLD
    `~/ablation-pipeline`, which defined the columns and never populated them.
  * The real pipeline `~/movie_processing/metadata.py:88-96` reads `XPositionUm`/`YPositionUm` from
    **page 0 only** -> one value per source FILE, not a per-frame trace. Re-running it would not produce
    drift even with the raws attached; it needs a code change too.
  * The rendered `_Cropped.tif`s are bare (Software: tifffile.py, only a shape tag) -- the pipeline strips
    metadata when it writes crops.
  * ZERO raw `*MMStack*.ome.tif` files and ZERO `*metadata.txt` sidecars exist on 4 MB; the raw acquisition
    folders are on unmounted drives.

WHAT THIS DOES INSTEAD -- and it is not a workaround, it is the more direct measurement:
A stage translation moves the ENTIRE field rigidly, so every marked object shifts by the SAME vector
between two frames. Biological motion does not. So for each frame transition, the MEDIAN displacement
vector across all simultaneously-tracked objects estimates the common-mode (stage + whole-cell) motion,
and the residual after subtracting it is true intra-cell movement. The median is used rather than the mean
so a couple of genuinely-moving kinetochores cannot drag the estimate.

Requires >=3 objects tracked across the same frame pair, otherwise the common mode is not identifiable and
the transition is left uncorrected and FLAGGED rather than guessed.

Writes `annotations/STAGE_COMMON_MODE_20260808.csv` and prints how much of the measured KT displacement is
common-mode -- i.e. exactly how much the movement numbers would be skewed if it were ignored.
"""
import csv, os, sys, collections
import numpy as np
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
OUT = A + "STAGE_COMMON_MODE_20260808.csv"
MIN_OBJ = 3          # below this the common mode is not identifiable

TR = list(csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                              errors="replace")))
print(f"track rows: {len(TR)}")

# batch -> frame -> {track_id: (x, y)}
per = collections.defaultdict(lambda: collections.defaultdict(dict))
for r in TR:
    try:
        per[r["batch"].strip()][int(r["frame"])][r["track_id"]] = (float(r["cx_px"]), float(r["cy_px"]))
    except Exception:
        pass

full, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in full}

rows = []
raw_mag, cm_mag, res_mag = [], [], []
per_batch = collections.defaultdict(lambda: [0, 0.0, 0.0])   # n, sum|cm|, max|cm|

for b, frames in per.items():
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    fs = sorted(frames)
    for f0, f1 in zip(fs, fs[1:]):
        a, c = frames[f0], frames[f1]
        common = sorted(set(a) & set(c))
        if len(common) < MIN_OBJ:
            rows.append([b, f0, f1, len(common), "", "", "", "not_identifiable"])
            continue
        d = np.array([[c[t][0] - a[t][0], c[t][1] - a[t][1]] for t in common], float)
        cm = np.median(d, axis=0)                       # common-mode vector, px
        res = d - cm                                    # residual = true intra-cell motion
        cm_px = float(np.hypot(*cm))
        rows.append([b, f0, f1, len(common), f"{cm[0]:.3f}", f"{cm[1]:.3f}",
                     f"{cm_px*ps:.4f}", ""])
        for k in range(len(common)):
            raw_mag.append(float(np.hypot(*d[k])) * ps)
            res_mag.append(float(np.hypot(*res[k])) * ps)
        cm_mag.append(cm_px * ps)
        pb = per_batch[b]
        pb[0] += 1; pb[1] += cm_px * ps; pb[2] = max(pb[2], cm_px * ps)

with open(OUT, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["batch", "frame_from", "frame_to", "n_objects",
                "common_dx_px", "common_dy_px", "common_mag_um", "flag"])
    w.writerows(rows)
print(f"wrote {OUT}  ({len(rows)} frame transitions)")

ident = [r for r in rows if not r[7]]
print(f"\nidentifiable transitions (>={MIN_OBJ} objects): {len(ident)}/{len(rows)}")
if cm_mag:
    cm_mag = np.array(cm_mag); raw = np.array(raw_mag); res = np.array(res_mag)
    print("\n=== HOW MUCH WOULD MOVEMENT BE SKEWED? ===")
    print(f"  per-object displacement, UNCORRECTED : median {np.median(raw):.4f} um   p90 {np.percentile(raw,90):.4f}")
    print(f"  per-object displacement, CORRECTED   : median {np.median(res):.4f} um   p90 {np.percentile(res,90):.4f}")
    frac = 100 * (1 - np.median(res) / np.median(raw)) if np.median(raw) > 0 else 0
    print(f"  -> common mode accounts for {frac:.1f}% of the median measured displacement")
    print(f"\n  common-mode magnitude: median {np.median(cm_mag):.4f} um   p90 {np.percentile(cm_mag,90):.4f}"
          f"   max {cm_mag.max():.4f} um")
    big = int((cm_mag > 0.5).sum())
    print(f"  transitions with common mode > 0.5 um (a real field shift): {big} ({100*big/len(cm_mag):.1f}%)")

    print("\n=== worst batches by max common-mode jump ===")
    for b, (n, s, mx) in sorted(per_batch.items(), key=lambda kv: -kv[1][2])[:12]:
        print(f"   {b[:50]:50s} n={n:4d}  mean {s/max(n,1):.3f} um  MAX {mx:.3f} um")
