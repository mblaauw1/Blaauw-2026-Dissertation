#!/usr/bin/env python3
"""Re-derive the 640 (Cy5 / Hec1-Halo) background-subtracted monitoring movies from the raw 16-bit stack.

USER 2026-07-22 on `20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy8`: the bg-subtracted 640 display "looks better
than the version to the left, however there seems to be this weird burn-in mark that is constant on every
frame - like a dark splotch ... and then frames in that movie channel version are completely black after
frame 5."

CAUSE (measured, not guessed).  The existing BgSub movie subtracts the LAST FRAME of the stack from every
frame (the Cy5 last-frame-subtraction trick used to kill the vertical banding):
  * the last frame contains its own kinetochore cluster, so subtracting it punches a permanent DARK HOLE at
    that position in every frame -- the "burn-in splotch";
  * the last frame minus itself is zero, so the final frame renders completely black. The 640 channel here
    only has 6 timepoints, so that is 1 of 6 frames lost.

FIX.  Subtract the per-pixel TEMPORAL MEDIAN of the stack instead.  The median is robust to a bright object
sitting in any single frame, so no dark hole appears and no frame is consumed.  Measured on xy8 frame 0:
last-frame-sub leaves a visible dark splotch; median-sub does not, and the kinetochore signal is unchanged
(p99.7 = 189 vs 163 counts over a background of ~1290, punctate signal preserved in both).
A large-kernel median-BLUR background was also tested and rejected -- it leaves residual vertical banding.

Writes `<batch>_640_Cy5_BgSub_Monitoring.mp4` next to the raw stack, keeping the old file as
`.bak_lastframesub_<stamp>` first. Run with --apply.
"""
import os, sys, glob, csv, json, shutil, datetime
import numpy as np, tifffile, cv2

ROOT = "/Volumes/4 MB"
APPLY = "--apply" in sys.argv
ONLY = [a for a in sys.argv[1:] if not a.startswith("--")]


def batches():
    rows = list(csv.reader(open(f"{ROOT}/ABLATION_MASTER.csv", encoding="utf-8", errors="replace")))
    hi = next(i for i, r in enumerate(rows) if r and r[0].strip() == "Batch Name")
    hdr = [c.strip() for c in rows[hi]]
    bi, pi = hdr.index("Batch Name"), hdr.index("Drive Path")
    return [(r[bi].strip(), r[pi].strip()) for r in rows[hi + 1:] if r and len(r) > pi and r[bi].strip()]


def norm8(x, lo_pct=1.0, hi_pct=99.7):
    lo, hi = np.percentile(x, lo_pct), np.percentile(x, hi_pct)
    return (np.clip((x - lo) / max(hi - lo, 1e-6), 0, 1) * 255).astype(np.uint8)


def resolve_640(batch, d):
    """Return (stack_path, page_indices_for_monitoring).

    Most batches store the 640 as `<batch>_640_Cy5_Cropped.tif`.  Some do NOT: on
    `20260331 ptk eyfp mad 1 640 halotag hec1_3` the 640 IS the "Fluor" channel
    (frames.json ch_names = ['640 (Cy5)', 'Brightfield'], fluor_ch = 0), and its stack holds the
    ablation AND monitoring pages together.  Reading the role -> page mapping out of frames.json is the
    only way to pick the right pages, so that is what this does instead of trusting the file name.
    """
    named = os.path.join(d, f"{batch}_640_Cy5_Cropped.tif")
    fj = glob.glob(os.path.join(d, "*_frames.json"))
    idx = None
    if fj:
        try:
            j = json.loads(open(fj[0], encoding="utf-8", errors="replace").read())
            names = [str(x).lower() for x in (j.get("ch_names") or [])]
            fch = j.get("fluor_ch")
            fluor_is_640 = fch is not None and fch < len(names) and "640" in names[fch]
            if not os.path.isfile(named) and fluor_is_640:
                alt = os.path.join(d, f"{batch}_Fluor_Cropped.tif")
                if os.path.isfile(alt):
                    idx = [f["fluor_tif_idx"] for f in j.get("frames", [])
                           if f.get("role") == "monitoring" and f.get("fluor_tif_idx") is not None]
                    return alt, idx
        except Exception:
            pass
    return (named if os.path.isfile(named) else None), None


def rederive(batch, d):
    tif, pages = resolve_640(batch, d)
    out = os.path.join(d, f"{batch}_640_Cy5_BgSub_Monitoring.mp4")
    ref = os.path.join(d, f"{batch}_640_Cy5_Monitoring.mp4")
    if not tif or not os.path.isfile(out):
        return None
    tf = tifffile.TiffFile(tif)
    sel = pages if pages else range(len(tf.pages))
    a = np.stack([tf.pages[i].asarray() for i in sel]).astype(np.float32)
    if len(a) < 3:
        # Too few planes for a temporal median. Falling back to a per-frame large-kernel median-BLUR
        # background: it removes the illumination gradient and the fixed splotch without consuming a
        # frame. It leaves some residual vertical banding (measured on xy8), but that beats the old
        # behaviour here, which turned 1 of only 2 frames completely black.
        from scipy.ndimage import median_filter
        sub = []
        for f in a:
            small = cv2.resize(f, None, fx=.25, fy=.25, interpolation=cv2.INTER_AREA)
            bg = cv2.resize(median_filter(small, size=31), (f.shape[1], f.shape[0]),
                            interpolation=cv2.INTER_LINEAR)
            sub.append(np.clip(f - bg, 0, None))
        sub = np.stack(sub)
    else:
        med = np.median(a, axis=0)
        sub = np.clip(a - med, 0, None)
    # one contrast range for the whole clip, so brightness does not jump between frames
    lo, hi = float(np.percentile(sub, 1)), float(np.percentile(sub, 99.7))
    frames = [(np.clip((f - lo) / max(hi - lo, 1e-6), 0, 1) * 255).astype(np.uint8) for f in sub]
    fps = 5
    if os.path.isfile(ref):
        c = cv2.VideoCapture(ref)
        f2 = c.get(cv2.CAP_PROP_FPS)
        if f2 and f2 > 0:
            fps = f2
    h, w = frames[0].shape
    if not APPLY:
        blank = sum(1 for f in frames if f.mean() < 1)
        return f"WOULD FIX {batch}: {len(frames)} planes, blank-after={blank} (median-sub)"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(out, out + f".bak_lastframesub_{stamp}")
    vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in frames:
        vw.write(cv2.cvtColor(f, cv2.COLOR_GRAY2BGR))
    vw.release()
    cap = cv2.VideoCapture(out)
    n, blank = 0, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        n += 1
        if fr.mean() < 1:
            blank += 1
    return f"FIXED {batch}: {n} frames written, {blank} blank"


hits = []
for b, d in batches():
    if ONLY and b not in ONLY:
        continue
    if not d or not os.path.isdir(d):
        continue
    if not os.path.isfile(os.path.join(d, f"{b}_640_Cy5_BgSub_Monitoring.mp4")):
        continue
    r = rederive(b, d)
    if r:
        hits.append(r)
        print(" ", r, flush=True)

print(f"\n{len(hits)} batches with a 640 BgSub movie" + ("" if APPLY else "  (dry run -- pass --apply)"))
