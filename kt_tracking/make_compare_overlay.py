"""make_compare_overlay.py — QC movie showing TrackMate detections AND the manual KT marks together,
so the tracking can be judged directly against ground truth rather than in isolation.

  yellow circle + id : a TrackMate spot (colour keyed to its track)
  magenta cross      : a MANUAL kinetochore mark
  green ring         : a manual mark that TrackMate FOUND (a spot within TOL um)
  red ring           : a manual mark TrackMate MISSED

Per-frame counters are burned into the corner, plus a running recall for the movie.
Join is by TIME (frames.json / timing sidecar), never by frame index — see score_vs_manual.py.

Usage: python3 make_compare_overlay.py <batch> <results_dir> [out.mp4]
"""
import csv, os, sys, json
from collections import defaultdict
import numpy as np, tifffile, cv2

ROOT = "/Volumes/4 MB"
STACKS = f"{ROOT}/kt_tracking/stacks"
TOL = 1.5

batch = sys.argv[1]
resdir = sys.argv[2] if len(sys.argv) > 2 else f"{ROOT}/kt_tracking/results"
safe = batch.replace(" ", "_")
out = sys.argv[3] if len(sys.argv) > 3 else f"{ROOT}/kt_tracking/overlays/{safe}_compare.mp4"
os.makedirs(os.path.dirname(out), exist_ok=True)


def pixel_size():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv")))
    hdr = [c.strip() for c in rows[1]]; pi = hdr.index("Pixel Size (um)")
    for r in rows[2:]:
        if r and r[0].strip() == batch and len(r) > pi:
            try:
                v = float(r[pi]); return v if v > 0 else 0.062
            except Exception: return 0.062
    return 0.062


PS = pixel_size()

# timing: stitched frame -> t_sec
tim = {}
tp = os.path.join(STACKS, safe + "_timing.csv")
for r in csv.DictReader(open(tp)):
    tim[int(r["stitched_frame"])] = float(r["t_sec"])

# TrackMate spots by stitched frame
spots = defaultdict(list)
timed = os.path.join(resdir, safe + ".spots_timed.csv")
raw = os.path.join(resdir, safe + ".spots.csv")
src = timed if os.path.isfile(timed) else raw
for s in csv.DictReader(open(src)):
    try:
        f = int(float(s["frame"]))
        spots[f].append((float(s["x_um"]) / PS, float(s["y_um"]) / PS, str(s.get("track_id", ""))))
    except Exception: pass

# manual marks by t_sec
man = []
rows = list(csv.reader(open(f"{ROOT}/annotations/kt_points.csv")))
ix = {c: i for i, c in enumerate(rows[0])}
for r in rows[1:]:
    if r[ix['batch']].strip() != batch: continue
    if r[ix['label']].strip() not in ("polar", "sisterless"): continue
    if not r[ix['t_hms']].strip(): continue
    try: man.append((float(r[ix['t_sec']]), float(r[ix['x']]), float(r[ix['y']])))
    except Exception: pass

stack = tifffile.imread(os.path.join(STACKS, safe + "_KTmon.tif"))
T = stack.shape[0]
lo, hi = np.percentile(stack, [1, 99.7])
COLORS = [(0, 255, 255), (0, 200, 255), (80, 255, 120), (255, 200, 0), (255, 120, 255), (120, 200, 255)]

H, W = stack.shape[1], stack.shape[2]
vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), 6, (W, H))
hit = tot = 0
for f in range(T):
    im = np.clip((stack[f].astype(float) - lo) / max(1e-6, hi - lo), 0, 1)
    bgr = cv2.cvtColor((im * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    t = tim.get(f)
    for (x, y, tid) in spots.get(f, []):
        c = COLORS[(hash(tid) % len(COLORS))]
        cv2.circle(bgr, (int(round(x)), int(round(y))), 9, c, 1, cv2.LINE_AA)
    fh = ft = 0
    if t is not None:
        for (mt, mx, my) in man:
            if abs(mt - t) > 10: continue
            ft += 1; tot += 1
            found = any(np.hypot((sx - mx) * PS, (sy - my) * PS) <= TOL for (sx, sy, _) in spots.get(f, []))
            fh += found; hit += found
            col = (80, 255, 80) if found else (60, 60, 255)
            cv2.drawMarker(bgr, (int(round(mx)), int(round(my))), (255, 0, 255),
                           cv2.MARKER_CROSS, 16, 2, cv2.LINE_AA)
            cv2.circle(bgr, (int(round(mx)), int(round(my))), 14, col, 2, cv2.LINE_AA)
    cv2.putText(bgr, f"f{f}  t={0 if t is None else int(t)}s   spots={len(spots.get(f,[]))}"
                     f"   manual {fh}/{ft}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    vw.write(bgr)
vw.release()
print(f"{batch}: {out}  recall {hit}/{tot} = {100*hit/max(1,tot):.1f}%")
