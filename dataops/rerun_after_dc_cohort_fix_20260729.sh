#!/bin/bash
# Re-run after lib.double_chromosome_batches() dropped its `same chromosome` false positive
# (2026-07-29). `20251029 triple_ablation_26` is no longer a double-chromosome cell, so it RETURNS to
# the 3-Sister cohort (N 30 -> 31) — and because DC cells are filtered out of every standard cohort
# violin, that cell had been silently missing from BOTH groups. Every builder that calls
# lib.assign_cohorts() or lib.double_chromosome_batches() therefore has to be rebuilt.
#
# NOT included, on purpose: group_timestrips.py and build_demo_timestrips.py (hours of rendering; their
# example picks are hand-curated, not cohort-N-driven) and verify_consistency.py (a checker — run it
# afterwards, not as part of the rebuild).
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_dc_cohort_20260729"; mkdir -p "$LOG"; : > "$LOG/_progress.txt"; : > "$LOG/_summary.tsv"
run(){ echo "=== START $1 $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"; t0=$(date +%s)
  python3 -u "$1.py" > "$LOG/$1.log" 2>&1; rc=$?; t1=$(date +%s)
  echo "=== END   $1 rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$1" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"; }
for s in \
  g1_violin2 group1_build group1_roundness ablation_count_by_cohort \
  group2_build group2_kk group2_metaphase_ablated group2_prophase_dynamics \
  g2_prometa_alt_quant g2_prometaphase_lastabl \
  group3_build group3_plate_timing group3_pole_time \
  group4_drug group4_exhaustion_violin group4_fluor group4_movement group4_polar_lagging \
  group4_tracking_dist \
  chromo_length_congression_single kk_distance_vs_time_to_meta lagging_vs_congression_timing \
  metaphase_duration_delta pole_to_plate_vs_duration sisterless_behavior_vs_duration \
  sisterless_congression_score triple_prometa_ablation_to_mitosis \
  custom_centroid_movement_meta_to_ana custom_collagen_variants custom_collagen_vs_triple_shape \
  custom_DEMO_shape_rate_composite custom_double_chromosome_violin_20260722 \
  custom_lineplot_shape_by_metaphase custom_noc_washout_v2_20260722 custom_plate_pole_model_v3 \
  custom_plots_to_make_20260722 custom_shape_rate_vs_metaphase \
  ; do run "$s"; done
echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
