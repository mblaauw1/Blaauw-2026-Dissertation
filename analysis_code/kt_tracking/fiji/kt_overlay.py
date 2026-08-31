#!/usr/bin/env python3
"""
kt_overlay.py — QC overlay movie for one batch's kinetochore tracking.

Renders the stitched monitoring stack (contrast-stretched GFP) with each
tracked kinetochore drawn as a circle colored by track id, plus a short motion
trail, the real elapsed time, and a seam flag. Lets you verify tracking
visually across all batches without opening the Fiji GUI.

Usage: kt_overlay.py <batch_base>
  where <batch_base> matches stacks/<base>_KTmon.tif and results/<base>.spots_timed.csv
"""
import os, sys, csv, glob
import numpy as np
import tifffile
import cv2

OUT_BASE = "/Volumes/5 MB/kt_tracking"
STK = os.path.join(OUT_BASE, "stacks")
RES = os.path.join(OUT_BASE, "results")
OVL = os.path.join(OUT_BASE, "overlays")
FPS = 7
TRAIL = 5  # frames of trailing history to draw

# distinct BGR colors cycled per track
PALETTE = [(66, 135, 245), (66, 245, 132), (245, 66, 66), (245, 209, 66),
           (245, 66, 224), (66, 245, 245), (245, 138, 66), (138, 66, 245),
           (66, 245, 191), (191, 245, 66), (245, 66, 138), (120, 200, 255)]


def stretch8(img, lo_pct=50, hi_pct=99.9):
    lo, hi = np.percentile(img, lo_pct), np.percentile(img, hi_pct)
    if hi <= lo:
        hi = lo + 1
    out = np.clip((img.astype(np.float32) - lo) / (hi - lo), 0, 1)
    return (out * 255).astype(np.uint8)


def build(base):
    tif = glob.glob(os.path.join(STK, base + "_KTmon.tif"))
    spc = os.path.join(RES, base + ".spots_timed.csv")
    if not tif or not os.path.isfile(spc):
        return None, "missing stack or spots_timed.csv"
    stack = tifffile.imread(tif[0])
    if stack.ndim == 4:               # TZYX -> TYX
        stack = stack[:, 0]
    T, H, W = stack.shape
    px = 0.062

    # spots grouped by frame, with track id; positions in um -> px
    spots = list(csv.DictReader(open(spc)))
    by_frame = {}
    track_color = {}
    ci = 0
    for s in spots:
        f = int(s["frame"])
        tid = s["track_id"]
        if tid not in track_color:
            track_color[tid] = PALETTE[ci % len(PALETTE)]
            ci += 1
        by_frame.setdefault(f, []).append({
            "tid": tid,
            "x": float(s["x_um"]) / px,
            "y": float(s["y_um"]) / px,
            "t": s.get("t_sec", ""),
            "seam": s.get("seam", "0"),
        })
    # per-track point history for trails
    hist = {}

    os.makedirs(OVL, exist_ok=True)
    out_path = os.path.join(OVL, base + "_KToverlay.mp4")
    # H.264 / yuv420p via imageio+ffmpeg so the MP4 plays in browsers
    # (cv2's mp4v writes MPEG-4 part 2, which HTML5 <video> can't decode).
    import imageio
    vw = imageio.get_writer(out_path, fps=FPS, codec="libx264",
                            pixelformat="yuv420p", macro_block_size=1,
                            output_params=["-movflags", "+faststart"])
    rad = max(6, int(round(0.5 / px / 2)) + 4)  # ~KT radius + halo
    for f in range(T):
        frame = cv2.cvtColor(stretch8(stack[f]), cv2.COLOR_GRAY2BGR)
        fs = by_frame.get(f, [])
        seam = any(s["seam"] == "1" for s in fs)
        tnow = next((s["t"] for s in fs if s["t"] != ""), "")
        for s in fs:
            c = track_color[s["tid"]]
            p = (int(round(s["x"])), int(round(s["y"])))
            hist.setdefault(s["tid"], []).append(p)
            cv2.circle(frame, p, rad, c, 1, cv2.LINE_AA)
            trail = hist[s["tid"]][-TRAIL:]
            for i in range(1, len(trail)):
                cv2.line(frame, trail[i - 1], trail[i], c, 1, cv2.LINE_AA)
        # HUD
        hud = f"frame {f}/{T-1}"
        if tnow != "":
            hud += f"   t={float(tnow)/60:.1f} min"
        hud += f"   KTs={len(fs)}"
        cv2.putText(frame, hud, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        if seam:
            cv2.putText(frame, "SEAM (acquisition gap)", (8, H - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 215, 255), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (1, 1), (W - 2, H - 2), (0, 215, 255), 2)
        vw.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))  # imageio expects RGB
    vw.close()
    return out_path, f"{T} frames, {len(track_color)} tracks"


def main():
    base = sys.argv[1]
    path, msg = build(base)
    print(f"  overlay: {path}  ({msg})" if path else f"  overlay FAILED: {msg}")


if __name__ == "__main__":
    main()
