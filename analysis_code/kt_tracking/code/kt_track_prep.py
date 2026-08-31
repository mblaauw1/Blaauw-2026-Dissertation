#!/usr/bin/env python3
"""
kt_track_prep.py — Build per-batch kinetochore-tracking input stacks.

For each qualifying batch (Metaphase + Anaphase defined, not Excluded) it:
  1. Reads the batch frames.json to get the MONITORING-role frames in time order.
  2. Keeps frames from the START of monitoring up to ANAPHASE ONSET + 3 min.
  3. Pulls those frames (full 16-bit, max-Z projected, GFP/fluor channel only,
     cell-cropped) directly from the pipeline's <batch>_Fluor_Cropped.tif,
     indexed by each frame's fluor_tif_idx.
  4. Writes a single ImageJ-calibrated multi-frame TIF per batch (pixel size
     0.062 um) into stacks/, ready for TrackMate.
  5. Writes a timing sidecar CSV (stitched_frame, source_acquisition, orig_idx,
     t_sec [real elapsed-from-ablation], dt_prev_s, seam) so velocities use REAL
     time and acquisition seams (multi-minute gaps) are flagged.

The monitoring "movie" of a batch is several raw acquisitions stitched in time
order; this script reproduces that stitch at full bit depth for tracking.
"""
import os, sys, glob, json, csv
import numpy as np
import tifffile

MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
# Render search path: prefer pipeline_correct (has today's reprocessing fixes),
# then fall back to older output roots on other drives. First hit wins.
RENDER_ROOTS = [
    "/Volumes/4 MB/pipeline_session_output",   # 4 MB first: works with ONLY 4 MB plugged in
    "/Volumes/5 MB/pipeline_correct",          # optional, used only if 5 MB is also mounted
    "/Volumes/5 MB/pipeline_output",
]
OUT_BASE = "/Volumes/4 MB/kt_tracking"          # all output lives on the 5 MB drive
STACKS = os.path.join(OUT_BASE, "stacks")
PIXEL_UM = 0.062
POST_ANAPHASE_S = 180.0   # 3 minutes after anaphase onset


_DRIVE_PATHS = None
def _drive_paths():
    rows = list(csv.reader(open(MASTER, newline="")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    hdr = rows[hi]; bi = hdr.index("Batch Name"); pi = hdr.index("Drive Path")
    return {r[bi].strip(): r[pi].strip() for r in rows[hi + 1:] if len(r) > pi and r[bi].strip()}

def _has_render_dir(bd):
    return bool(bd and glob.glob(os.path.join(bd, "*_frames.json"))
               and glob.glob(os.path.join(bd, "*_Fluor_Cropped.tif")))

def resolve_batch_dir(name):
    """Return the render dir for a batch (with both frames.json and Fluor_Cropped.tif).
    Uses the FULL date-folder token (handles '20260303_extra2' etc.), then falls back to
    the master Drive Path so non-standard names aren't silently dropped."""
    global _DRIVE_PATHS
    datefolder = name.split(" ", 1)[0]
    for root in RENDER_ROOTS:
        bd = os.path.join(root, datefolder, name)
        if _has_render_dir(bd):
            return bd
    if _DRIVE_PATHS is None:
        _DRIVE_PATHS = _drive_paths()
    dp = _DRIVE_PATHS.get(name, "")
    if _has_render_dir(dp):
        return dp
    return None


def hms_to_sec(s):
    """'0:30:23' / '-0:02:55' / '00:28:21' (H:MM:SS) OR raw seconds '6207.0'
    -> seconds (signed). The master mixes both formats across dates."""
    s = s.strip()
    if not s:
        return None
    neg = s.startswith("-")
    s = s.lstrip("-")
    try:
        if ":" in s:
            parts = [float(p) for p in s.split(":")]
            while len(parts) < 3:
                parts.insert(0, 0)
            h, m, sec = parts
            val = h * 3600 + m * 60 + sec
        else:
            val = float(s)
    except ValueError:
        return None
    return -val if neg else val


def _has_render(name):
    return resolve_batch_dir(name) is not None


def qualifying_batches(date_filter=None, bottom_up=False, trackable_only=True):
    """Batches with Metaphase + Anaphase defined and not Excluded.
    bottom_up=True returns them in reverse master order (newest cells first).
    trackable_only=True keeps only those with a rendered Fluor_Cropped.tif."""
    rows = list(csv.reader(open(MASTER, newline="")))
    hdr = [h.strip() for h in rows[1]]
    ci = {h: i for i, h in enumerate(hdr)}
    ms, ao, ex = ci["Metaphase Start (s)"], ci["Anaphase Onset (s)"], ci["Exclude"]
    out = []
    for r in rows[2:]:
        if not r or not r[0].strip():
            continue
        name = r[0].strip()
        if date_filter and not name.startswith(date_filter):
            continue
        g = lambda i: r[i].strip() if i < len(r) else ""
        if g(ms) and g(ao) and g(ex).lower() != "yes":
            ana = hms_to_sec(g(ao))
            if ana is None:
                continue
            if trackable_only and not _has_render(name):
                continue
            out.append((name, ana))
    if bottom_up:
        out.reverse()
    return out


def build_stack(name, anaphase_s):
    bdir = resolve_batch_dir(name)
    if bdir is None:
        return None, "no render (frames.json + Fluor_Cropped.tif) on any drive"
    fjs = glob.glob(os.path.join(bdir, "*_frames.json"))
    flc = glob.glob(os.path.join(bdir, "*_Fluor_Cropped.tif"))
    d = json.load(open(fjs[0]))
    cutoff = anaphase_s + POST_ANAPHASE_S
    mon = [f for f in d["frames"]
           if f.get("role") == "monitoring"
           and f.get("fluor_tif_idx") is not None
           and f["t_sec"] <= cutoff]
    mon.sort(key=lambda f: f["idx"])
    if len(mon) < 3:
        return None, f"only {len(mon)} monitoring frames in window"

    # Guard: must be a real motion timelapse, not a z-stack (all frames share a
    # timestamp) — tracking across z-slices is not kinetochore motion.
    ts = sorted(set(round(f["t_sec"], 1) for f in mon))
    if (ts[-1] - ts[0]) <= 60 or len(ts) < max(3, len(mon) // 2):
        return None, f"z-stack/flat (t spans {ts[-1]-ts[0]:.0f}s, {len(ts)} distinct) — not a motion timelapse"

    sidecar = []
    frames = []
    with tifffile.TiffFile(flc[0]) as tf:
        npg = len(tf.pages)
        prev_t = None
        prev_src = None
        for sf, f in enumerate(mon):
            fi = f["fluor_tif_idx"]
            if fi >= npg:
                continue
            frames.append(tf.pages[fi].asarray())
            src = f["source"].split("cdc20 1 ")[-1].split("_MMStack")[0]
            dt = "" if prev_t is None else round(f["t_sec"] - prev_t, 1)
            seam = 1 if (prev_src is not None and src != prev_src) else 0
            sidecar.append({
                "stitched_frame": sf,
                "source_acquisition": src,
                "orig_idx": f["idx"],
                "t_sec": round(f["t_sec"], 2),
                "dt_prev_s": dt,
                "seam": seam,
            })
            prev_t = f["t_sec"]
            prev_src = src

    if len(frames) < 3:
        return None, "too few frames after page check"
    stack = np.stack(frames).astype(np.uint16)  # (T, Y, X)

    safe = name.replace(" ", "_")
    tif_path = os.path.join(STACKS, safe + "_KTmon.tif")
    # ImageJ-calibrated hyperstack: single channel, T frames. Real (non-uniform)
    # timing is in the sidecar; we record nominal 20 s only for display.
    tifffile.imwrite(
        tif_path, stack[:, np.newaxis, :, :],  # TZYX with Z=1
        imagej=True,
        resolution=(1.0 / PIXEL_UM, 1.0 / PIXEL_UM),
        metadata={"unit": "um", "axes": "TZYX", "finterval": 20.0,
                  "spacing": 1.0, "tunit": "sec"},
    )
    csv_path = os.path.join(STACKS, safe + "_timing.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sidecar[0].keys()))
        w.writeheader()
        w.writerows(sidecar)
    nseam = sum(s["seam"] for s in sidecar)
    return tif_path, f"{len(frames)} frames, {nseam} acquisition seams, t=[{sidecar[0]['t_sec']:.0f},{sidecar[-1]['t_sec']:.0f}]s"


def main():
    os.makedirs(STACKS, exist_ok=True)
    arg = sys.argv[1] if len(sys.argv) > 1 else "20260420"
    if arg.lower() == "all":
        batches = qualifying_batches(bottom_up=True)   # all trackable, newest cells first
        label = "all_bottomup"
        print(f"{len(batches)} trackable qualifying batches (bottom-up / newest first)\n")
    else:
        batches = qualifying_batches(date_filter=arg)
        label = arg
        print(f"{len(batches)} trackable qualifying batches for {arg}\n")
    ok = 0
    manifest = []
    for name, ana in batches:
        path, msg = build_stack(name, ana)
        tag = "OK " if path else "SKIP"
        short = name.split("cdc20 1 ")[-1] if "cdc20 1 " in name else name
        print(f"  [{tag}] {short[:30]:30} ana={ana:5}s  {msg}")
        if path:
            ok += 1
            manifest.append({"batch": name, "tif": path, "anaphase_s": ana})
    mpath = os.path.join(STACKS, f"manifest_{label}.json")
    json.dump(manifest, open(mpath, "w"), indent=2)
    print(f"\n{ok}/{len(batches)} stacks built -> {STACKS}")
    print(f"manifest -> {mpath}")


if __name__ == "__main__":
    main()
