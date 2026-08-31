#!/usr/bin/env python3
"""Task-by-task audit: is each completed item ACTUALLY in the current files, and did it rebuild?

USER 2026-08-05: "go back through the entire task list and check to make sure you completed every task
completely and correctly".

The failure mode this is built to catch is the one that already bit twice today: an edit that looked
applied but was not. Once because a helper script asserted before it wrote the file (the fb9 re-source was
silently lost), and once because a replace pattern did not match the real line (NF8 kept writing under its
old filename). Both passed a syntax check and neither raised. So this does not re-read my own notes — it
greps the CURRENT source and stats the CURRENT output, and reports what it actually finds.

Each check is (task, description, kind, target, test). Kinds:
  src   — a string that MUST appear in a source file
  nosrc — a string that must NOT appear (the old behaviour is gone)
  fig   — a figure file that must exist, and be newer than the cutoff (i.e. rebuilt today)
  data  — a recorded data CSV that must exist and be non-trivial
"""
import os, sys, csv, datetime

ROOT = "/Volumes/4 MB"
B = f"{ROOT}/ablation_figures_20260625"
D = f"{ROOT}/ablation_plots/data"
CUTOFF = datetime.datetime(2026, 8, 5, 0, 0).timestamp()   # "rebuilt today"

CHECKS = [
    # (task, what it is, kind, target, needle)
    (16, "F1 Mad1 outliers removed by robust z", "src", "group5_hec1_timestrip.py", "MAD1_F1_DROPPED"),
    (16, "Hec1/Mad1 figure rebuilt", "fig", "group4/G5_hec1_mad1_dot_quant.png", None),
    (17, "mad1 coverage audit exists", "src", "audit_mad1_snapshot_coverage_20260805.py", "MIN_TRACE"),
    (17, "ablation_17 timestrip present", "fig", "group4/G5_mad1_timestrip_20260304_Mad1_ablation_17_aligned.png", None),
    (18, "ablation_8 #0 time shift", "src", "group4_ablation_intensity.py", "ABL_SEL_TSHIFT"),
    (18, "clamp recorded for the legend notes", "src", "group4_ablation_intensity.py", "negative_clamped_to_zero"),
    (18, "selected-traces figure rebuilt", "fig", "group4/G4_ablation_intensity_selected_combined.png", None),
    (19, "4-group distance builder", "src", "kt_track_plots.py", "def distance_4group"),
    (19, "survivorship guard on the cumulative plot", "src", "kt_track_plots.py", "MIN_FRAC"),
    (19, "distance per-minute figure", "fig", "group6_tracks/G6trk_distance_per_min_4group.png", None),
    (19, "cumulative distance figure", "fig", "group6_tracks/G6trk_distance_cumulative_4group.png", None),
    (20, "4-group time-to-anaphase builder", "src", "kt_track_plots.py", "def _vs_time_to_anaphase_4"),
    (20, "window widened to -40", "src", "kt_track_plots.py", "lo=-40"),
    (20, "circularity 4-group figure", "fig", "group6_tracks/G6trk_circ_vs_ttana_4group.png", None),
    (20, "speed 4-group figure", "fig", "group6_tracks/G6trk_speed_vs_ttana_4group.png", None),
    (22, "ROI follows by fluor detection, not template matching", "src", "group_slippage_timestrips.py", "connectedComponentsWithStats"),
    (22, "contrast gate for degraded Cdc20", "src", "group_slippage_timestrips.py", "CONTRAST GATE"),
    (22, "nocodazole timestrip rebuilt", "fig", "group4/G3_slippage_timestrip_nocodazole_aligned.png", None),
    (40, "noc washout on ONE axes", "src", "custom_noc_washout_v2_20260722.py", "fig, ax = plt.subplots(figsize=(13.0, 5.6))"),
    (40, "pooled washout violin dropped", "src", "custom_noc_washout_v2_20260722.py", "G[1:]"),
    (40, "noc washout figure rebuilt", "fig", "group2/G2_noc_washout_vs_prophase.png", None),
    (42, "NF8 on distortion", "src", "custom_new_figures_20260804.py", "def _nf8_polar_distortion"),
    (42, "NF8 also writes the legacy filename", "src", "custom_new_figures_20260804.py", "G6_polar_equivalent_kk_single_vs_triple.png"),
    (42, "NF8 figure (new name)", "fig", "new_figures_20260804/G6_polar_distortion_single_vs_triple.png", None),
    (42, "NF8 figure (legacy name the deck links)", "fig", "new_figures_20260804/G6_polar_equivalent_kk_single_vs_triple.png", None),
    (43, "G6tenM equivalency series removed", "nosrc", "kt_tension_metaphase.py", '"   |   ".join(_it6)'),
    (43, "G6tenM figure rebuilt", "fig", "group6_tracks/G6tenM_equivalent_kk_over_time.png", None),
    (44, "chromosome-length figure keyed per chromosome", "src", "custom_polar_tension_vs_chromolen_20260805.py", "paired_track"),
    (44, "leave-one-out robustness reported", "src", "custom_polar_tension_vs_chromolen_20260805.py", "loo_max_p"),
    (44, "chromolen figure", "fig", "new_figures_20260804/G6_polar_distortion_vs_chromolen_single.png", None),
    (45, "FRAP anchors on the first post-ablation point", "src", "group4_frap.py", "def first_post_zero"),
    (45, "FRAP no longer anchors on the global minimum", "nosrc", "group4_frap.py", "sz=second_zero(Tk,Q)"),
    (45, "FRAP figure rebuilt", "fig", "group4/G4_frap_combined.png", None),
    (46, "one violin dot constant", "src", "lib.py", "VIOLIN_DOT_S = 26"),
    (46, "shared mean/median helper", "src", "lib.py", "def violin_stats"),
    (46, "reference violin uses it", "src", "custom_double_chromosome_violin_20260722.py", "lib.violin_stats"),
    (47, "lagging included in the loading axis", "src", "kt_loading_axis.py", '"polar", "paired", "lagging"'),
    (47, "joined distortion table exists", "data", "../annotations/KT_TENSION_LOADAXIS_20260805.csv", None),
    (49, "one axis for every kinetochore", "src", "kt_tension_metaphase.py", 'def tension(r): return num(r, "spindle_strain")'),
    (49, "retirement stamp emptied", "src", "kt_tension_metaphase.py", "_RETIRED_METRIC = set()"),
    (49, "per-cell headline figure", "fig", "group6_tracks/G6tenM_polar_vs_paired_percell.png", None),
    (49, "kt_tension on distortion", "nosrc", "kt_tension.py", 'col(polar, "spindle_strain")'),
    (49, "fb9 re-sourced (was silently empty)", "src", "custom_new_figures_20260804.py", "G6tenM_strain_over_time.csv"),
    (49, "fb9 figure has data again", "data", "G6_polar_equivalent_kk_over_metaphase.csv", None),
]

FAIL = []; PASS = 0
for task, what, kind, target, needle in CHECKS:
    ok = False; why = ""
    if kind in ("src", "nosrc"):
        p = os.path.join(B, target)
        if not os.path.exists(p):
            why = "source file missing"
        else:
            txt = open(p, encoding="utf-8", errors="replace").read()
            present = needle in txt
            ok = present if kind == "src" else (not present)
            why = ("needle absent" if kind == "src" else "old behaviour still present") if not ok else ""
    elif kind == "fig":
        p = os.path.join(B, target)
        if not os.path.exists(p):
            why = "figure missing"
        elif os.path.getmtime(p) < CUTOFF:
            why = "figure NOT rebuilt today (" + datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M") + ")"
        elif os.path.getsize(p) < 5000:
            why = f"figure suspiciously small ({os.path.getsize(p)} bytes)"
        else:
            ok = True
    elif kind == "data":
        p = target if target.startswith("..") is False else os.path.abspath(os.path.join(B, target))
        if not os.path.isabs(p): p = os.path.join(D, target)
        if not os.path.exists(p):
            why = "data csv missing"
        else:
            n = sum(1 for _ in open(p, encoding="utf-8", errors="replace")) - 1
            if n < 5: why = f"only {n} data rows"
            else: ok = True
    if ok: PASS += 1
    else: FAIL.append((task, what, kind, target, why))

print(f"AUDIT: {PASS}/{len(CHECKS)} checks pass\n")
if FAIL:
    print("FAILURES:")
    for task, what, kind, target, why in FAIL:
        print(f"  task #{task:<3} [{kind:5}] {what}")
        print(f"           target: {target}")
        print(f"           reason: {why}")
else:
    print("Every completed task verified against the CURRENT source and the CURRENT output.")
sys.exit(1 if FAIL else 0)
