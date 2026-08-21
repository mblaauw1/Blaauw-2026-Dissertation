#!/usr/bin/env python3
"""Re-measure TrackMate spots with the MANUAL fluorescence method, so both are directly comparable.

USER 2026-07-22: "trackmate measures the flourescence of the kinetochores it marks differently than my
manual method. is there a way to make trackmate use my method ... for consistency?"

The two methods really are different:
  MANUAL      `lib.disk_sum(gray, x, y, r=9)` -- the SUM inside a radius-9 px circle (the annotation
              circle) on the 16-bit `<batch>_Fluor_Cropped.tif`, minus the SAME-size circle placed on
              that cell's `cytosol_bg` mark. Absolute, background-subtracted, one fixed aperture.
  TRACKMATE   MEAN_INTENSITY / TOTAL_INTENSITY inside the spot's OWN fitted radius (0.25 um ~ 4 px
              here), on the trimmed KTmon stack, with no background subtraction at all.
So TrackMate's numbers differ in aperture, in normalisation and in baseline -- three ways at once.

Rather than change TrackMate's detector (its intensity features are baked into its own model, and
editing them would make its detection incomparable to every earlier run), this keeps TrackMate for
WHAT IT IS GOOD AT -- finding and linking the kinetochore -- and re-measures the intensity at its
coordinates with the manual function. That is the same separation the cdc20-vs-bleaching rebuild used:
"a plate KT located by TrackMate but measured here with the same method and the same background".

Output: `<results_dir>/<batch>.spots_manual.csv` -- every TrackMate spot plus
  manual_disk_sum        SUM in the r=9 circle at the spot, on the 16-bit stack
  manual_bg_disk_sum     SUM in an r=9 circle at that cell's cytosol_bg mark on the same frame
  manual_bgsub           manual_disk_sum - manual_bg_disk_sum   <-- the number to compare/plot
  saturated              1 if the disk touches the 60000-count clip level (unquantifiable)

Usage:  python3 remeasure_trackmate_manual_method.py <results_dir> [batch ...]
        KT_STACKS=/Volumes/4 MB/kt_tracking/stacks_long
"""
import csv, glob, json, os, sys
import numpy as np

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

ROOT = "/Volumes/4 MB"
STACKS = os.environ.get("KT_STACKS", f"{ROOT}/kt_tracking/stacks")
PX = 0.062                      # the stacks are written ImageJ-calibrated at 0.062 um/px
csv.field_size_limit(10 ** 9)

RES = sys.argv[1]
ONLY = [a for a in sys.argv[2:] if not a.startswith("--")]

master = {r["Batch Name"]: r for r in lib.load_master()[0]}

# cytosol_bg marks: batch -> {frame: (x, y)}
BG = {}
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv")):
    if r.get("label") != "cytosol_bg":
        continue
    try:
        BG.setdefault(r["batch"], {})[int(float(r["frame"]))] = (float(r["x"]), float(r["y"]))
    except Exception:
        pass


def timing(batch):
    p = os.path.join(STACKS, batch.replace(" ", "_") + "_timing.csv")
    if not os.path.isfile(p):
        return None
    out = {}
    for r in csv.DictReader(open(p)):
        try:
            out[int(float(r.get("stitched_frame", r.get("frame", ""))))] = (
                float(r["t_sec"]), int(float(r.get("orig_idx", -1))))
        except Exception:
            pass
    return out or None


done, skipped = 0, []
for f in sorted(glob.glob(os.path.join(RES, "*.spots.csv"))):
    key = os.path.basename(f)[:-len(".spots.csv")]
    batch = next((b for b in master if b.replace(" ", "_") == key), None)
    if batch is None or (ONLY and batch not in ONLY):
        continue
    tif = lib.FluorTif(batch) if hasattr(lib, "FluorTif") else None
    tm = timing(batch)
    if tif is None or tm is None:
        skipped.append((batch, "no fluor stack" if tif is None else "no timing sidecar")); continue
    bg = BG.get(batch, {})
    rows_out, n_bg = [], 0
    for s in csv.DictReader(open(f)):
        try:
            sf = int(float(s["frame"]))
            x, y = float(s["x_um"]) / PX, float(s["y_um"]) / PX
        except Exception:
            continue
        t_sec, orig = tm.get(sf, (None, None))
        gray = None
        try:
            gray = tif.plane_by_frame(orig) if orig is not None and orig >= 0 else None
        except Exception:
            gray = None
        if gray is None:
            continue
        val = lib.disk_sum(gray, x, y, r=9)
        sat = 1 if (lib.disk_max(gray, x, y, r=9) or 0) >= lib.SAT else 0
        bgv = None
        if bg:
            bf = min(bg, key=lambda k: abs(k - (orig if orig is not None else sf)))
            bx, by = bg[bf]
            bgv = lib.disk_sum(gray, bx, by, r=9)
            if bgv is not None:
                n_bg += 1
        row = dict(s)
        row["t_sec_real"] = "" if t_sec is None else round(t_sec, 2)
        row["manual_disk_sum"] = "" if val is None else round(val, 1)
        row["manual_bg_disk_sum"] = "" if bgv is None else round(bgv, 1)
        row["manual_bgsub"] = "" if (val is None or bgv is None) else round(val - bgv, 1)
        row["saturated"] = sat
        rows_out.append(row)
    if not rows_out:
        skipped.append((batch, "no spot mapped to a fluor plane")); continue
    out = os.path.join(RES, key + ".spots_manual.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)
    done += 1
    print(f"  {batch}: {len(rows_out)} spots re-measured, {n_bg} with a cytosol background", flush=True)

print(f"\n{done} batches written to {RES}/*.spots_manual.csv")
for b, why in skipped[:10]:
    print(f"  skipped {b}: {why}")
if skipped:
    print(f"  ({len(skipped)} skipped in total)")
