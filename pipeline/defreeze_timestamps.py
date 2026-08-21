#!/usr/bin/env python3
"""
defreeze_timestamps.py — repair frozen per-frame timestamps in a batch's
frames.json, then (optionally) re-render its MP4s from the cached cropped TIFs
so the burned-in clock is correct.

A frozen run = >=N consecutive frames sharing one t_sec inside a single-plane
(z-projected) MONITORING timelapse — a MicroManager ElapsedTime metadata stall,
NOT a z-volume (those share a timestamp legitimately; gated out by the caller).

Repair = replace each frozen run's t_sec with a strictly-monotonic ramp between
the surrounding real timestamps (linear interpolation; median-interval
extrapolation for a leading/trailing run). Non-cascading and fully reversible:
the original frames.json is archived first, and the MP4s are deterministic from
frames.json + the cropped TIF.

Usage: defreeze_timestamps.py <frames_json> <archive_dir> [--no-render]
"""
import json, os, sys, shutil, statistics, subprocess


def frozen_runs(ts):
    out = []; i = 0
    while i < len(ts):
        j = i
        while j + 1 < len(ts) and ts[j + 1] == ts[i]:
            j += 1
        if j > i:
            out.append((i, j))
        i = j + 1
    return out


def median_interval(ts):
    diffs = [b - a for a, b in zip(ts, ts[1:]) if b > a]
    return statistics.median(diffs) if diffs else 20.0


def defreeze(ts, min_run):
    """Return (new_ts, changes) where changes = [(idx, old, new), ...]."""
    ts = list(ts)
    med = median_interval(ts)
    changes = []
    for i, j in frozen_runs(ts):
        n = j - i + 1
        if n < min_run:
            continue  # short run (e.g. ablation burst) — leave alone
        prev_t = ts[i - 1] if i > 0 else None
        next_t = ts[j + 1] if j + 1 < len(ts) else None
        if prev_t is not None and next_t is not None and next_t > prev_t:
            span = next_t - prev_t
            for k in range(i, j + 1):
                nt = round(prev_t + span * (k - i + 1) / (n + 1), 3)
                changes.append((k, ts[k], nt)); ts[k] = nt
        elif prev_t is not None:                      # trailing run
            for k in range(i, j + 1):
                nt = round(prev_t + med * (k - i + 1), 3)
                changes.append((k, ts[k], nt)); ts[k] = nt
        elif next_t is not None:                      # leading run
            for k in range(i, j + 1):
                nt = round(next_t - med * (j + 1 - k), 3)
                changes.append((k, ts[k], nt)); ts[k] = nt
    return ts, changes


def main():
    fj = sys.argv[1]
    arch_root = sys.argv[2]
    render = "--no-render" not in sys.argv
    min_run = 12

    batch = os.path.basename(os.path.dirname(fj))
    J = json.load(open(fj))
    fr = J["frames"]
    ts = [f.get("t_sec") for f in fr]
    new_ts, changes = defreeze(ts, min_run)
    if not changes:
        print(f"  {batch}: no frozen runs >= {min_run}; skipped")
        return

    # monotonicity check
    nonmono = sum(1 for a, b in zip(new_ts, new_ts[1:]) if b < a)

    # archive original frames.json
    ad = os.path.join(arch_root, batch)
    os.makedirs(ad, exist_ok=True)
    shutil.copy2(fj, os.path.join(ad, os.path.basename(fj) + ".orig"))
    with open(os.path.join(ad, "changes.json"), "w") as f:
        json.dump({"batch": batch, "frames_json": fj, "n_changed": len(changes),
                   "nonmono_after": nonmono,
                   "sample": changes[:5] + changes[-5:]}, f, indent=1)

    # write repaired frames.json
    for f_, nt in zip(fr, new_ts):
        f_["t_sec"] = nt
    tmp = fj + ".tmp"
    with open(tmp, "w") as f:
        json.dump(J, f)
    os.replace(tmp, fj)
    print(f"  {batch}: de-froze {len(changes)} frames, nonmono_after={nonmono}")

    if render:
        bdir = os.path.dirname(fj)
        r = subprocess.run([sys.executable,
                            os.path.join(os.path.dirname(__file__), "rerender_from_cropped.py"),
                            bdir], capture_output=True, text=True)
        print("   rerender:", (r.stdout or r.stderr).strip().split("\n")[-1][:120])


if __name__ == "__main__":
    main()
