#!/bin/bash
# Re-run everything consuming lib.is_misplaced_id after screen_kt_placement was repointed to
# snap_to_peak_pixel (2026-07-29). The previous run excluded 2277 ids (48.5% of KT annotations)
# because the z-score was computed at the CENTROID instead of the brightest pixel; it is now 20.
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_misplacedfix_20260729"; mkdir -p "$LOG"; : > "$LOG/_progress.txt"; : > "$LOG/_summary.tsv"
for s in group4_movement group4_frap group4_ablation_intensity group4_cdc20_poles group4_prepost \
         group4_tracking_dist gt_cdc20 negatives_by_radius custom_rtf_questions_20260722 diag_placement; do
  echo "=== START $s $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"
  t0=$(date +%s); python3 -u "$s.py" > "$LOG/$s.log" 2>&1; rc=$?; t1=$(date +%s)
  echo "=== END   $s rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$s" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"
done
echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
