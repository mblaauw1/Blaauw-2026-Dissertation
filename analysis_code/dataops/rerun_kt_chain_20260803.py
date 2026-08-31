#!/usr/bin/env python3
"""Re-run the ENTIRE kinetochore chain after retiring the ellipse fit (2026-08-03).

Every module below reads geometry that was, until today, produced by `cv2.fitEllipse` — a model fitted to
hand-traced outlines that are irregular and frequently fractured. `kt_shape_metrics` now measures extent
with calipers instead, so every derived store and every figure downstream of it is stale and must be
rebuilt before any of its numbers can be quoted again.

Order matters: each stage writes a CSV the next one reads.
`lib.record_plot` rewrites PLOT_SETTINGS entries WITHOUT `plot_number`, so the deck numbers are snapshotted
before the run and restored after (NOTES §14 2026-07-23, the collision that assigned 406-418 twice).
"""
import json, os, subprocess, sys, time

FIG = "/Volumes/4 MB/ablation_figures_20260625"
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
SNAP = "/Volumes/4 MB/_scratch/plot_numbers_pre_kt_chain_20260803.json"

STAGES = [
    # derived geometry stores, in dependency order
    "kt_shape_metrics.py",
    "kt_tracks.py",
    "kt_landmark_analysis.py",
    "kt_chromo_analysis.py",
    "kt_sisters.py",
    "kt_tension.py",
    "kt_tension_withincell.py",
    "kt_tension_metaphase.py",
    # figure builders
    "kt_shape_plots.py",
    "kt_track_plots.py",
    "kt_track_plots2.py",
    "kt_cell_outline.py",
    "kt_oscillation.py",
    "kt_phase_split.py",
    "kt_polar_phase_time.py",
    "kt_polar_3d.py",
    "kt_time_trajectories.py",
    "kt_time_meta2ana.py",
    "kt_polar_tension_timelines.py",
    "kt_mad1_plots.py",
    "custom_lagging_examples_outlines_20260729.py",
    # 2026-08-03: these three were missed on the first pass and left 19 figures rendered off the retired
    # ellipse geometry. They read KT_LANDMARK_ANALYSIS / kt_shape_metrics like the rest — any script that
    # reads that geometry belongs in this list.
    "custom_questions_20260727.py",
    "custom_questions2_20260727.py",
    "custom_questions3_20260727.py",
]


def snapshot():
    S = json.load(open(PS))
    n = {k: v.get("plot_number") for k, v in S.items()
         if isinstance(v, dict) and isinstance(v.get("plot_number"), int)}
    json.dump(n, open(SNAP, "w"))
    return n


def restore():
    S = json.load(open(PS))
    snap = json.load(open(SNAP))
    lost = [k for k, v in snap.items() if not isinstance(S.get(k, {}).get("plot_number"), int)]
    for k in lost:
        S.setdefault(k, {})["plot_number"] = snap[k]
    if lost:
        tmp = PS + ".tmp"
        json.dump(S, open(tmp, "w"), indent=1)
        os.replace(tmp, PS)
    return len(lost)


def main():
    n = snapshot()
    print(f"plot_number snapshot: {len(n)} figures -> {SNAP}", flush=True)
    ok, bad = [], []
    for s in STAGES:
        p = os.path.join(FIG, s)
        if not os.path.isfile(p):
            print(f"[SKIP] {s} — not on disk", flush=True)
            continue
        t0 = time.time()
        r = subprocess.run([sys.executable, "-u", p], cwd=FIG, capture_output=True, text=True)
        dt = time.time() - t0
        if r.returncode == 0:
            ok.append(s)
            print(f"[ OK ] {s:52s} {dt:6.1f}s", flush=True)
        else:
            bad.append((s, (r.stderr or r.stdout)[-700:]))
            print(f"[FAIL] {s:52s} {dt:6.1f}s", flush=True)
    lost = restore()
    print(f"\nplot_number restored for {lost} figures", flush=True)
    print(f"=== {len(ok)} OK, {len(bad)} FAILED ===", flush=True)
    for s, err in bad:
        print(f"\n--- {s} ---\n{err}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
