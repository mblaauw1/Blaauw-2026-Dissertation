#!/bin/bash
# FULL clean re-run after lib.snap_to_peak gained Gaussian pre-smoothing (rad 10, sigma 1.5),
# which took centering from 3.00 px / 49.9% within-3px to 2.21 px / 66.8% on the 917 ground-truth
# pairs and reproduces handoff-7 section 2's 2.24 / 65.8%. Every fluorescence measurement that snaps
# is affected, so this re-runs the whole set rather than a subset.
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_snapfix_20260729"; mkdir -p "$LOG"; : > "$LOG/_progress.txt"; : > "$LOG/_summary.tsv"
run(){ echo "=== START $1 $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"; t0=$(date +%s)
  python3 -u "$1.py" > "$LOG/$1.log" 2>&1; rc=$?; t1=$(date +%s)
  echo "=== END   $1 rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$1" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"; }
# 1. the placement screen first - everything downstream consumes its exclusion list
run screen_kt_placement
# 2. measurement + figure scripts that snap
for s in group4_movement analysis_manual_polar_vs_paired group4_frap group4_ablation_intensity \
         group4_cdc20_poles group4_prepost group4_fluor group4_tracking_dist group4_lagging_shape \
         group4_lagging_examples custom_cdc20_vs_bleaching_spec_20260722 gt_cdc20 negatives_by_radius \
         group5_if_kt_quant custom_rtf_questions_20260722; do run "$s"; done
# 3. centering/intensity derived data, in handoff-7 section 7 step 2 order
for s in circle_outline_matching validate_circle_centering polar_focus_check polar_fluor_matched \
         rebuild_186_outline_intensity rebuild_182_187_outline_intensity; do run "$s"; done
# 4. diagnostics
for s in diag_placement diag_temporal snap_proof verify_annotation_placement verify_kt_size verify_snap_demo; do run "$s"; done
echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
