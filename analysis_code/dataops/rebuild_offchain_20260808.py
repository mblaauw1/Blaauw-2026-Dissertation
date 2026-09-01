#!/usr/bin/env python3
"""Rebuild every figure builder that reads the new annotation data but is NOT in rerun_kt_chain.

USER 2026-08-08: "make sure that all the plots that used the data are updated so it includes the new
annotation data".

The chain covers 24 stages. An audit found 42 further builders in ablation_figures_20260625 that read
kt_outlines / KT_OUTLINE_TRACKS / KT_SISTERS / KT_TENSION / KT_LOADING_AXIS / cell_outlines / meta_plates
AND call record_plot -- i.e. they render figures off data that changed today (new annotations, plus the
common-mode drift correction now applied inside kt_tracks.py). NOTES §8 records a previous pass where three
such scripts were missed and left 19 figures rendered off retired geometry; this is that same failure mode.

PLOT NUMBERS: lib.record_plot rewrites PLOT_SETTINGS entries without `plot_number`, so deck numbers are
snapshotted before and restored after, exactly as the chain does.
"""
import json, os, subprocess, sys, time

FIG = "/Volumes/4 MB/ablation_figures_20260625"
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"
SNAP = "/Volumes/4 MB/_scratch/plot_numbers_pre_offchain_20260808.json"
SKIP = {"lib.py", "register_derived_plots.py"}   # library / registrar, not figure builders

names = [n for n in open("/tmp/rebuild_list.txt").read().split() if n and n not in SKIP]
print(f"{len(names)} builders to run\n", flush=True)

os.makedirs(os.path.dirname(SNAP), exist_ok=True)
S = json.load(open(PS))
snap = {k: v.get("plot_number") for k, v in S.items()
        if isinstance(v, dict) and isinstance(v.get("plot_number"), int)}
json.dump(snap, open(SNAP, "w"))
print(f"plot_number snapshot: {len(snap)} figures\n", flush=True)

ok, bad = [], []
for i, n in enumerate(names, 1):
    p = os.path.join(FIG, n)
    t0 = time.time()
    r = subprocess.run([sys.executable, "-u", p], cwd=FIG, capture_output=True, text=True, timeout=1800)
    dt = time.time() - t0
    if r.returncode == 0:
        ok.append(n); print(f"[ OK ] {i:3d}/{len(names)} {n:52s} {dt:6.1f}s", flush=True)
    else:
        bad.append((n, (r.stderr or r.stdout)[-500:]))
        print(f"[FAIL] {i:3d}/{len(names)} {n:52s} {dt:6.1f}s", flush=True)

S = json.load(open(PS))
lost = [k for k, v in snap.items() if not isinstance(S.get(k, {}).get("plot_number"), int)]
for k in lost:
    S.setdefault(k, {})["plot_number"] = snap[k]
if lost:
    tmp = PS + ".tmp"; json.dump(S, open(tmp, "w"), indent=1); os.replace(tmp, PS)
print(f"\nplot_number restored for {len(lost)} figures", flush=True)
print(f"=== {len(ok)} OK, {len(bad)} FAILED ===", flush=True)
for n, e in bad:
    print(f"\n--- {n} ---\n{e}", flush=True)
