#!/usr/bin/env python3
"""Per-frame stage offset for every batch, from the REAL MicroManager metadata. Supersedes the inference.

WHY THIS REPLACES THE MARKS-BASED ESTIMATE. On 2026-08-08, with no stage metadata anywhere on 4 MB, drift
was inferred as the MEDIAN displacement across all objects tracked between two frames ("common mode"), and
that estimate was baked into `kt_tracks.py`, removing ~38% of measured kinetochore displacement everywhere.
The 2026-08-09 harvest gives 1,518,809 planes with real `XPositionUm`/`YPositionUm` (99.9% coverage), and
checking the inference against it FAILED: for `20250826 test_ablation_8` -- the batch cited as proof, with a
"29.2 um jump a kinetochore cannot make" -- the real stage makes ONE 2627 um move at the start (travelling
to the position) and then just 1 step >0.5 um in 44 frames. The 29.2 um transition shows no stage motion at
all and is not a source-file boundary. So the common mode there was NOT the stage, and the correction was
removing something real.

THIS SCRIPT USES THE MEASUREMENT INSTEAD OF THE INFERENCE.
  sidecar filename  ->  source tif        : strip `_metadata.txt`, append `.ome.tif`
  source tif        ->  batch            : master `Source Files` column
  FrameKey-f-c-s    ->  frame_in_file    : f
  (source, frame_in_file) -> global frame: frames.json
Then per batch: stage XY per global frame, converted to PIXELS via that batch's pixel size, expressed
relative to the batch's first frame. A downstream consumer subtracts it exactly like the old common mode.

Writes `annotations/STAGE_XY_BY_FRAME_20260809.csv`.
"""
import csv, gzip, json, os, sys, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

csv.field_size_limit(10 ** 9)
HARV = "/Volumes/4 MB/_working/_reviews_and_reference/raw_metadata_harvest/STAGE_XY_BY_PLANE.csv.gz"
OUT = "/Volumes/4 MB/annotations/STAGE_XY_BY_FRAME_20260809.csv"

rows, _ = lib.load_master()
MR = {r["Batch Name"]: r for r in rows}

# ---- source tif -> batches that use it ----------------------------------------------------------
tif2batch = collections.defaultdict(list)
for b, r in MR.items():
    for s in (r.get("Source Files", "") or "").split(";"):
        s = s.strip()
        if s:
            tif2batch[s].append(b)
print(f"source tifs referenced by the master: {len(tif2batch)}")

# ---- stage XY per (source tif, frame_in_file) ----------------------------------------------------
stage = collections.defaultdict(dict)          # tif -> frame_in_file -> (x_um, y_um)
seen_side = set()
with gzip.open(HARV, "rt", newline="") as f:
    for r in csv.DictReader(f):
        sc = r["sidecar"]
        if not sc.endswith("_metadata.txt"):
            continue
        tif = sc[:-len("_metadata.txt")] + ".ome.tif"
        if tif not in tif2batch:
            continue
        seen_side.add(sc)
        x, y = (r.get("x_um") or "").strip(), (r.get("y_um") or "").strip()
        if not x or not y:
            continue
        try:
            fr = int(r["framekey"].split("-")[1])
        except Exception:
            continue
        d = stage[tif]
        if fr not in d:                       # one value per frame; channels/slices share a position
            d[fr] = (float(x), float(y))
print(f"source tifs matched in the harvest  : {len(stage)}   sidecars used: {len(seen_side)}")

# ---- map to each batch's global frames via frames.json --------------------------------------------
out, no_json, no_stage = [], 0, 0
batches = sorted({b for t in stage for b in tif2batch[t]})
print(f"batches touched: {len(batches)}")
for b in batches:
    d = (MR.get(b, {}).get("Drive Path", "") or "").strip()
    if not (d and os.path.isdir(d)):
        d = os.path.join("/Volumes/4 MB/pipeline_session_output", b.split()[0], b)
    fj = os.path.join(d, f"{b}_frames.json")
    if not os.path.isfile(fj):
        no_json += 1
        continue
    try:
        j = json.load(open(fj))
    except Exception:
        no_json += 1
        continue
    try:
        px = float(j.get("pixel_size_um") or MR[b].get("Pixel Size (um)") or 0.062)
    except Exception:
        px = 0.062
    per = []
    for fr in j.get("frames", []):
        src = fr.get("source")
        fif = fr.get("frame_in_file")
        if src is None or fif is None:
            continue
        xy = stage.get(src, {}).get(int(fif))
        if xy is None:
            continue
        per.append((int(fr["idx"]), fr.get("role"), xy[0], xy[1]))
    if not per:
        no_stage += 1
        continue
    per.sort()
    x0, y0 = per[0][2], per[0][3]
    for idx, role, x, y in per:
        dx_um, dy_um = x - x0, y - y0
        out.append([b, idx, role, f"{x:.3f}", f"{y:.3f}",
                    f"{dx_um:.4f}", f"{dy_um:.4f}",
                    f"{dx_um/px:.3f}", f"{dy_um/px:.3f}", f"{px:.4f}"])

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["batch", "frame_idx", "role", "stage_x_um", "stage_y_um",
                "dx_um_from_first", "dy_um_from_first",
                "dx_px_from_first", "dy_px_from_first", "pixel_size_um"])
    w.writerows(out)
print(f"\nwrote {OUT}")
print(f"  rows: {len(out)}   batches with a stage trace: {len({r[0] for r in out})}")
print(f"  batches skipped: no frames.json {no_json}, no stage match {no_stage}")

# ---- how much does the stage ACTUALLY move within a batch? ----------------------------------------
import math
per_b = collections.defaultdict(list)
for r in out:
    per_b[r[0]].append((int(r[1]), float(r[7]), float(r[8])))
mags = []
for b, v in per_b.items():
    v.sort()
    steps = [math.hypot(v[i+1][1]-v[i][1], v[i+1][2]-v[i][2]) for i in range(len(v)-1)]
    if steps:
        mags.append((b, max(steps), sum(steps), len(steps)))
mags.sort(key=lambda t: -t[1])
print("\n=== real stage movement per batch (in PIXELS of that batch) ===")
print(f"  batches with a trace: {len(mags)}")
big = [m for m in mags if m[1] > 5]
print(f"  batches with any single step > 5 px: {len(big)}")
for b, mx, tot, n in mags[:10]:
    print(f"     {b[:46]:46s} max step {mx:9.1f} px   total {tot:10.1f} px   over {n} steps")
