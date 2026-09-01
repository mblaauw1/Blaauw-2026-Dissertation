#!/usr/bin/env python3
"""
kt_finalize.py — merge REAL acquisition timing into TrackMate spot output and
recompute velocities against real elapsed time (not the nominal 20 s/frame,
which is wrong across acquisition seams).

For each <batch>.spots.csv in results/, joins the matching <batch>_timing.csv
from stacks/ on stitched frame, then writes <batch>.spots_timed.csv with:
  + t_sec        real elapsed-from-ablation seconds
  + source_acquisition, seam (1 if frame crosses an acquisition gap)
  + step_um, dt_s, speed_um_per_min   (per-step, using real dt; blanked at seams)
and rewrites <batch>.tracks_timed.csv with real-time per-track speed
(excluding seam-crossing steps so multi-minute gaps don't inflate velocity).

Also emits results/KT_tracking_summary.csv: one row per batch with track counts
and median KT speed, for quick QC across the night's run.
"""
import os, glob, csv, math
from collections import defaultdict

OUT_BASE = "/Volumes/5 MB/kt_tracking"
RES = os.path.join(OUT_BASE, "results")
STK = os.path.join(OUT_BASE, "stacks")


def load_timing(batch_base):
    p = os.path.join(STK, batch_base + "_timing.csv")
    if not os.path.isfile(p):
        return None
    out = {}
    for r in csv.DictReader(open(p)):
        out[int(r["stitched_frame"])] = {
            "t_sec": float(r["t_sec"]),
            "source": r["source_acquisition"],
            "seam": r["seam"] == "1",
        }
    return out


def finalize(spots_csv):
    base = os.path.basename(spots_csv).replace(".spots.csv", "")
    timing = load_timing(base)
    if timing is None:
        return None
    rows = list(csv.DictReader(open(spots_csv)))
    # attach real time
    for r in rows:
        f = int(r["frame"])
        t = timing.get(f, {})
        r["t_sec"] = t.get("t_sec", "")
        r["source_acquisition"] = t.get("source", "")
        r["seam"] = 1 if t.get("seam") else 0

    # per-step kinematics per track, in real time, skipping seam-crossing steps
    by_track = defaultdict(list)
    for r in rows:
        by_track[r["track_id"]].append(r)
    track_speeds = {}
    for tid, sp in by_track.items():
        sp.sort(key=lambda r: int(r["frame"]))
        speeds = []
        for i, r in enumerate(sp):
            if i == 0:
                r["step_um"] = r["dt_s"] = r["speed_um_per_min"] = ""
                continue
            p = sp[i - 1]
            try:
                dx = float(r["x_um"]) - float(p["x_um"])
                dy = float(r["y_um"]) - float(p["y_um"])
                dt = float(r["t_sec"]) - float(p["t_sec"])
            except (ValueError, TypeError):
                r["step_um"] = r["dt_s"] = r["speed_um_per_min"] = ""
                continue
            step = math.hypot(dx, dy)
            r["step_um"] = round(step, 4)
            r["dt_s"] = round(dt, 1)
            # seam step or non-positive dt -> distance is real but velocity meaningless
            if r["seam"] or dt <= 0:
                r["speed_um_per_min"] = ""
            else:
                v = step / dt * 60.0
                r["speed_um_per_min"] = round(v, 3)
                speeds.append(v)
        track_speeds[tid] = speeds

    # write timed spots
    out_cols = ["track_id", "frame", "t_sec", "source_acquisition", "seam",
                "x_um", "y_um", "radius_um", "quality", "mean_intensity",
                "total_intensity", "snr", "contrast",
                "step_um", "dt_s", "speed_um_per_min"]
    op = os.path.join(RES, base + ".spots_timed.csv")
    with open(op, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # timed track summary
    tp = os.path.join(RES, base + ".tracks_timed.csv")
    all_speeds = []
    with open(tp, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["track_id", "n_spots", "median_speed_um_per_min",
                    "mean_speed_um_per_min", "n_real_steps"])
        for tid, sp in by_track.items():
            sv = sorted(track_speeds[tid])
            med = sv[len(sv) // 2] if sv else ""
            mean = sum(sv) / len(sv) if sv else ""
            w.writerow([tid, len(sp),
                        round(med, 3) if med != "" else "",
                        round(mean, 3) if mean != "" else "", len(sv)])
            all_speeds.extend(sv)
    med_all = sorted(all_speeds)[len(all_speeds) // 2] if all_speeds else None
    return {"batch": base, "n_tracks": len(by_track), "n_spots": len(rows),
            "median_kt_speed_um_per_min": round(med_all, 3) if med_all else ""}


def main():
    summ = []
    for sc in sorted(glob.glob(os.path.join(RES, "*.spots.csv"))):
        r = finalize(sc)
        if r:
            summ.append(r)
            print(f"  {r['batch'].split('cdc20_1_')[-1]:16} tracks={r['n_tracks']:3} "
                  f"spots={r['n_spots']:4} medianKTspeed={r['median_kt_speed_um_per_min']} um/min")
    sp = os.path.join(RES, "KT_tracking_summary.csv")
    if summ:
        with open(sp, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(summ[0].keys()))
            w.writeheader()
            w.writerows(summ)
    print(f"\n{len(summ)} batches finalized -> {sp}")


if __name__ == "__main__":
    main()
