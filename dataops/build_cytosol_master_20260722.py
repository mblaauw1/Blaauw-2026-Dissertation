#!/usr/bin/env python3
"""ONE master table of every cytosol-background measurement: hers and the automatic ones together.

USER 2026-07-22: "log the values you measure for the cytosol very logically and organized with my
custom measurements so all cytosol measurements are in one master annotation csv file".

OUTPUT: `annotations/CYTOSOL_BACKGROUND_MASTER.csv`, one row per measurement, sorted by
batch -> clip -> frame, with a `source` column that is either:
    manual   -- one of her own `cytosol_bg` marks in kt_points.csv (the id is carried across)
    auto     -- placed by dataops/auto_cytosol_bg_20260722.py
Both are measured the SAME way, `lib.disk_sum(r=9)` on the 16-bit fluor stack, so the column
`disk_sum_r9` is directly comparable and directly subtractable from an on-target reading.

HER MARKS ARE NOT MOVED OR CHANGED.  They stay in kt_points.csv exactly as they are; this table
mirrors them so everything is readable in one place, and `kt_point_id` points back at the original.

KNOWN, DELIBERATE OFFSET: an auto point lands on cytoplasm a median 3.4% dimmer than a hand-placed
one (IQR -3.7% to -3.1%, measured on 68 frames where both exist). She chose to leave it uncorrected,
so `auto` rows carry that convention consistently. The `source` column is what tells them apart, and
`rel_to_manual_pct` records the measured offset on rows where both exist.
"""
import csv, os, sys, datetime, shutil

ROOT = "/Volumes/4 MB"
PROPOSALS = f"{ROOT}/_scratch/auto_cytosol_bg_proposals.csv"
OUT = f"{ROOT}/annotations/CYTOSOL_BACKGROUND_MASTER.csv"
APPLY = "--apply" in sys.argv
csv.field_size_limit(10 ** 9)

COLS = ["id", "batch", "clip", "frame", "t_sec", "t_hms", "x", "y", "disk_sum_r9", "radius_px",
        "source", "kt_point_id", "outline_from_clip", "outline_gap_frames", "relax_level", "n_candidates",
        "local_mean", "local_sd", "rel_to_manual_pct", "method", "recorded_on"]

# NOTE ON NAMING (user 2026-07-22): the word "phase" is avoided in this table entirely. Everything here
# is a FLUORESCENCE measurement -- the brightfield/phase channel is never measured, and lib.FluorTif
# refuses a batch whose fluor channel is named brightfield/phase/DIC. The column that says WHICH CLIP a
# frame came from is called `clip`, with values `monitoring` / `ablation`, so it can never be read as a
# channel.
CLIP = {"mon": "monitoring", "abl": "ablation", "pre": "pre", "monitoring": "monitoring",
        "ablation": "ablation", "": "monitoring"}

TODAY = datetime.date.today().isoformat()
METHOD_M = "manual mark; lib.disk_sum(r=9) on the 16-bit <batch>_Fluor_Cropped.tif"
METHOD_A = ("auto (dataops/auto_cytosol_bg_20260722.py): inside the traced cell outline eroded 12px, "
            "bright objects + 9px halo removed, 22px cleared around every manual mark, disk chosen at "
            "the 59th percentile of in-cell intensity near 0.40 of the cell radius; "
            "lib.disk_sum(r=9) on the same stack")

rows = []

# ---- her marks, mirrored from kt_points (never modified there) ----
n_manual = 0
for r in csv.DictReader(open(f"{ROOT}/annotations/kt_points.csv")):
    if r.get("label") != "cytosol_bg":
        continue
    rows.append({"batch": r.get("batch", ""), "clip": CLIP.get(r.get("phase", ""), "monitoring"),
                 "frame": r.get("frame", ""), "t_sec": r.get("t_sec", ""), "t_hms": r.get("t_hms", ""),
                 "x": r.get("x", ""), "y": r.get("y", ""), "disk_sum_r9": "", "radius_px": 9,
                 "source": "manual", "kt_point_id": r.get("id", ""), "outline_from_clip": "",
                 "outline_gap_frames": "", "relax_level": "", "n_candidates": "", "local_mean": "", "local_sd": "",
                 "rel_to_manual_pct": "", "method": METHOD_M, "recorded_on": TODAY})
    n_manual += 1

# ---- the automatic proposals ----
n_auto = 0
if os.path.exists(PROPOSALS):
    for r in csv.DictReader(open(PROPOSALS)):
        rel = ""
        try:
            if r.get("her_disk_sum"):
                rel = round(100 * (float(r["disk_sum"]) - float(r["her_disk_sum"])) / float(r["her_disk_sum"]), 2)
        except Exception:
            rel = ""
        rows.append({"batch": r["batch"], "clip": CLIP.get(r.get("phase", "mon"), "monitoring"),
                     "frame": r["frame"],
                     "t_sec": r.get("t_sec", ""), "t_hms": r.get("t_hms", ""),
                     "x": r["x"], "y": r["y"], "disk_sum_r9": r.get("disk_sum", ""), "radius_px": 9,
                     "source": "auto", "kt_point_id": "",
                     "outline_from_clip": CLIP.get(r.get("outline_from_phase", ""), r.get("outline_from_phase", "")),
                     "outline_gap_frames": r.get("outline_gap_frames", ""),
                     "relax_level": r.get("relax_level", ""),
                     "n_candidates": r.get("n_candidates", ""), "local_mean": r.get("local_mean", ""),
                     "local_sd": r.get("local_sd", ""), "rel_to_manual_pct": rel,
                     "method": METHOD_A, "recorded_on": TODAY})
        n_auto += 1


def key(r):
    try:
        fr = int(float(r["frame"]))
    except Exception:
        fr = 0
    return (r["batch"], r["clip"], fr, 0 if r["source"] == "manual" else 1)


rows.sort(key=key)
for i, r in enumerate(rows, 1):
    r["id"] = i

print(f"manual rows mirrored: {n_manual}   auto rows: {n_auto}   total: {len(rows)}")
by_batch = len({r["batch"] for r in rows})
print(f"batches covered: {by_batch}")
have_both = [r for r in rows if r["rel_to_manual_pct"] not in ("", None)]
if have_both:
    import statistics
    v = [float(r["rel_to_manual_pct"]) for r in have_both]
    print(f"frames where both exist: {len(v)}   median auto-vs-manual {statistics.median(v):+.2f}%")

if APPLY:
    if os.path.exists(OUT):
        shutil.copy(OUT, f"{ROOT}/_master_backups/CYTOSOL_BACKGROUND_MASTER_pre_"
                         f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    tmp = OUT + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    os.replace(tmp, OUT)
    chk = list(csv.DictReader(open(OUT)))
    print(f"WROTE {OUT} -- verified {len(chk)} rows on re-read")
else:
    print("(dry run -- pass --apply to write the master table)")
