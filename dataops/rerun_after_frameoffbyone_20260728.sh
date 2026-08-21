#!/bin/bash
# Downstream re-run after the frame off-by-one fix (handoff-7 §7).
# Baseline to diff against: snapshot 20260728_222440_v7_full_output_coverage
# All 19 scripts take NO flags; every env var (KT_R, ABL_NFRAMES, FRAP_NREC,
# ABL_NORM_CAP, ABL_NEG_FLOOR, KT_SWEEP_OUT) defaults to its standard value,
# so a bare invocation IS the original invocation. Verified 2026-07-28.
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_frameoffbyone_20260728"
mkdir -p "$LOG"

STEP1="group4_movement analysis_manual_polar_vs_paired group4_frap group4_ablation_intensity \
group4_cdc20_poles group4_prepost group4_fluor group4_tracking_dist group4_lagging_shape \
custom_cdc20_vs_bleaching_spec_20260722 gt_cdc20 negatives_by_radius screen_kt_placement"

# order is prescribed by handoff-7 §7 step 2 - do not reorder
STEP2="circle_outline_matching validate_circle_centering polar_focus_check \
polar_fluor_matched rebuild_186_outline_intensity rebuild_182_187_outline_intensity"

run_one() {
  s="$1"
  echo "=== START $s $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"
  t0=$(date +%s)
  python3 -u "$s.py" > "$LOG/$s.log" 2>&1
  rc=$?
  t1=$(date +%s)
  echo "=== END   $s rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$s" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"
}

: > "$LOG/_progress.txt"
: > "$LOG/_summary.tsv"
echo "STEP 1" >> "$LOG/_progress.txt"
for s in $STEP1; do run_one "$s"; done
echo "STEP 2" >> "$LOG/_progress.txt"
for s in $STEP2; do run_one "$s"; done
echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
