"""build_kt_outline_pkgs.py — build the media packages for the KT-OUTLINE slides.

SET: single-ablation (# Sisterless KTs == 1), ON-TARGET, non-drug, not-excluded, non-metaphase
     (lib.plot_excluded enforces drug/Exclude/REVIEW/metaphase/4-sis), MONITORING movie only.

WHY RE-ENCODE: the pipeline's monitoring mp4s carry exactly ONE keyframe, so browser seeking is not
frame-accurate — the root cause of a whole class of "annotation landed on the wrong frame" bugs in this
project. Each monitoring mp4 is re-encoded with `-g 1` (every frame a keyframe) so `currentTime` -> frame
is exact. Frame i of the monitoring mp4 == monitoring frame i of frames.json (verified 1:1 by count).

Also writes, per batch, a meta.json holding the ONLY frame source of truth: the frames.json monitoring
frames (idx + t_sec), the roi, the pixel size, the master event times, and the compiled comments.

Usage: python3 build_kt_outline_pkgs.py [--limit N] [--force]
"""
import sys, os, json, csv, subprocess, shutil

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

OUT = "/Volumes/4 MB/kt_outline_pkgs_20260722"
MASTER = "/Volumes/4 MB/ABLATION_MASTER.csv"
FORCE = "--force" in sys.argv
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

# NB `First/Last Ablation (s)` are UNIX ABSOLUTE timestamps (NOTES §8) — never show them raw next to the
# elapsed H:MM:SS event times. Everything else is elapsed from the first ablation, so first ablation IS 0.
EVENT_COLS = [("NEB", "NEB Time (s)"), ("Metaphase", "Metaphase Start (s)"),
              ("Anaphase", "Anaphase Onset (s)"), ("Cytokinesis", "Cytokinesis Onset (s)"),
              ("Ablation span", "Ablation Span (s)")]
COMMENT_COLS = ["Notes", "annotation_notes", "Polar Comments", "Lagging Comments", "Exclude Reason",
                "Sisterless KT Brightness", "Sisterless Dist from Pole", "Ablation Success",
                "Healthy Anaphase", "Phase of Ablations", "Cell Type", "# Unique Targets"]


def batch_set():
    data, _ = lib.load_master()
    return [r for r in data
            if r.get("# Sisterless KTs") == "1"
            and r.get("On-Target / Off-Target", "").lower() == "on-target"
            and not lib.plot_excluded(r["Batch Name"])]


def frames_json(dp):
    for f in sorted(os.listdir(dp)):
        if f.endswith("_frames.json"):
            return json.loads(open(os.path.join(dp, f), encoding="utf-8", errors="replace").read())
    return None


def nb_frames(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    try: return int(r.stdout.strip().split(",")[0])
    except Exception: return -1


def reencode(src, dst, crf="22"):
    tmp = dst + ".tmp.mp4"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                        "-c:v", "libx264", "-g", "1", "-crf", crf, "-pix_fmt", "yuv420p",
                        "-fps_mode", "passthrough", "-movflags", "+faststart", tmp],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(tmp):
        if os.path.isfile(tmp): os.remove(tmp)
        return False, r.stderr[-300:]
    if nb_frames(tmp) != nb_frames(src):          # never ship a clip that lost/gained a frame
        os.remove(tmp); return False, "frame count changed during re-encode"
    os.replace(tmp, dst)
    return True, ""


def zmark(mon):
    """Tag each monitoring frame with its position inside a run of identical t_sec.
    z=0 -> a genuine timepoint; z>=1 -> the 2nd, 3rd ... slice of a z-stack sitting in the monitoring role."""
    out = []
    run_start, run_len = 0, 1
    for i, f in enumerate(mon):
        if i and abs(f["t_sec"] - mon[i - 1]["t_sec"]) < 1e-6:
            run_len += 1
        else:
            run_start, run_len = i, 1
        out.append({"i": i, "idx": f.get("idx"), "t_sec": f["t_sec"], "z": i - run_start})
    # second pass: record the total run length on every member so the UI can say "slice 2/6"
    for i, f in enumerate(out):
        j = i
        while j + 1 < len(out) and out[j + 1]["z"] > 0:
            j += 1
        if f["z"] == 0:
            n = j - i + 1
        f["zrun"] = n if f["z"] == 0 else out[i - f["z"]]["zrun"]
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    sel = batch_set()
    if LIMIT: sel = sel[:LIMIT]
    print(f"{len(sel)} batches in the set", flush=True)
    index = []
    for n, r in enumerate(sel, 1):
        b, dp = r["Batch Name"], r["Drive Path"]
        pkg = os.path.join(OUT, b)
        if not os.path.isdir(dp):
            print(f"[{n}/{len(sel)}] SKIP {b} — no output dir", flush=True); continue
        fj = frames_json(dp)
        if not fj:
            print(f"[{n}/{len(sel)}] SKIP {b} — no frames.json", flush=True); continue
        mon = [f for f in fj["frames"] if f.get("role") == "monitoring"]
        if not mon:
            print(f"[{n}/{len(sel)}] SKIP {b} — no monitoring frames", flush=True); continue
        os.makedirs(pkg, exist_ok=True)
        chans, bad = {}, None
        for ch in ("Phase", "Fluor"):
            src = os.path.join(dp, f"{b}_{ch}_Monitoring.mp4")
            if not os.path.isfile(src) or os.path.getsize(src) < 2000: continue
            dst = os.path.join(pkg, f"{ch.lower()}.mp4")
            if os.path.isfile(dst) and not FORCE and nb_frames(dst) == len(mon):
                chans[ch.lower()] = f"{ch.lower()}.mp4"; continue
            nsrc = nb_frames(src)
            if nsrc != len(mon):
                bad = f"{ch}: mp4 has {nsrc} frames, frames.json monitoring has {len(mon)}"
                continue
            # fluor carries the kinetochores -> keep it sharp; phase is context only -> cheaper.
            # (the 4 MB drive is 98% full, so package size is a real constraint)
            ok, err = reencode(src, dst, crf="20" if ch == "Fluor" else "30")
            if ok: chans[ch.lower()] = f"{ch.lower()}.mp4"
            else:  bad = f"{ch}: {err}"
        if not chans:
            print(f"[{n}/{len(sel)}] FAIL {b} — {bad or 'no monitoring mp4'}", flush=True); continue
        ps = r.get("Pixel Size (um)", "").strip() or fj.get("pixel_size_um") or 0.062
        meta = {
            "batch": b, "drive_path": dp, "channels": chans,
            "pixel_size_um": float(ps), "roi": fj.get("roi") or {"x": 0, "y": 0},
            "fps_display": fj.get("fps") or 10,
            # THE frame source of truth. index i here == frame i of the packaged mp4s.
            # `z` > 0 marks a frame that shares its t_sec with the previous one — a Z-SLICE that the pipeline
            # routed into the monitoring role (known bug, memory: project_zstack_as_monitoring_bug). Those are
            # NOT timepoints; the UI flags them so an outline is never dated to a slice.
            "frames": zmark(mon),
            "events": ([{"name": "First ablation", "value": "00:00:00 (t=0 reference)"}] +
                       [{"name": nm, "value": r.get(col, "").strip()} for nm, col in EVENT_COLS
                        if r.get(col, "").strip()]),
            "n_zslice": sum(1 for f in zmark(mon) if f["z"]),
            "comments": [{"col": c, "text": r.get(c, "").strip()} for c in COMMENT_COLS if r.get(c, "").strip()],
            "warn": bad or "",
        }
        json.dump(meta, open(os.path.join(pkg, "meta.json"), "w"), indent=1)
        index.append({"batch": b, "n_frames": len(mon), "channels": sorted(chans),
                      "t_start": mon[0]["t_sec"], "t_end": mon[-1]["t_sec"]})
        print(f"[{n}/{len(sel)}] OK   {b}  {len(mon)} frames  {sorted(chans)}" + (f"  WARN {bad}" if bad else ""), flush=True)
    json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=1)
    print(f"\nDONE — {len(index)} packages in {OUT}", flush=True)


if __name__ == "__main__":
    main()
