#!/bin/bash
# FULL rebuild after (a) lib.snap_to_peak gained Gaussian pre-smoothing (rad 10, sigma 1.5:
# centering 3.00 -> 2.21 px, within-3px 49.9% -> 66.8%) and (b) six kinetochore label/track edits
# in kt_outlines.csv + kt_points.csv on 2026-07-29.
#
# ORDER IS LOAD-BEARING. Each stage writes a table the next stage reads:
#   1 screen_kt_placement    -> MISPLACED_KT_IDS      (lib.is_misplaced_id gate)
#   2 polar_focus_check      -> POLAR_FOCUS_CHECK     (lib.focus_excluded gate)
#   3 circle_outline_matching-> CIRCLE_OUTLINE_MATCH  (lib.kt_center resolves through this)
#   4 kt_shape_metrics       -> data/kt_shape_metrics.csv
#   5 kt_tracks -> kt_landmark_analysis -> kt_sisters -> kt_tension -> _withincell -> _metaphase
#   6 circle/intensity derived tables
#   7 every figure builder that depends on circle or outline data
# Running a figure builder before its gate table is rebuilt reproduces the mixed state this run exists
# to clear, so do not reorder.
#
# NOT RUN, deliberately:
#   kt_center_from_image / kt_center_learned / kt_region_center / kt_mser_center / kt_dp_tracker /
#   kt_center_search  - dead estimators, handoff-7 section 10 says they need not run again
#   group4_lagging_examples - superseded by custom_lagging_examples_outlines_20260729 (circle-derived
#                             anaphase lagging shape is not a supported measurement)
#   diag_filmstrip          - pre-existing crash on empty input (nrows=0)
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rebuild_all_20260729"; mkdir -p "$LOG"
: > "$LOG/_progress.txt"; : > "$LOG/_summary.tsv"

run(){ echo "=== START $1 $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"; t0=$(date +%s)
  python3 -u "$1.py" > "$LOG/$1.log" 2>&1; rc=$?; t1=$(date +%s)
  echo "=== END   $1 rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$1" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"; }

echo "STAGE 1-3 gate tables" >> "$LOG/_progress.txt"
for s in screen_kt_placement polar_focus_check circle_outline_matching; do run "$s"; done

echo "STAGE 4-5 derived tables" >> "$LOG/_progress.txt"
for s in kt_shape_metrics kt_tracks kt_landmark_analysis kt_sisters kt_tension \
         kt_tension_withincell kt_tension_metaphase kt_chromo_analysis; do run "$s"; done

echo "STAGE 6 circle/intensity derived" >> "$LOG/_progress.txt"
for s in polar_fluor_matched validate_circle_centering; do run "$s"; done

echo "STAGE 7 figure builders" >> "$LOG/_progress.txt"
for s in group2_kk group3_build group4_movement group4_frap group4_ablation_intensity \
         group4_cdc20_poles group4_prepost group4_fluor group4_tracking_dist group4_lagging_shape \
         group5_if_kt_quant group5_mad1_polar_plate \
         analysis_manual_polar_vs_paired custom_cdc20_vs_bleaching_spec_20260722 \
         custom_ablation_location_vs_behavior custom_kk_before_ablation_vs_behavior \
         custom_plots_to_make_20260722 custom_plots_to_make_part2_20260722 \
         custom_questions_20260727 custom_questions2_20260727 custom_questions3_20260727 \
         custom_rtf_questions_20260722 custom_sisterless_longaxis custom_sisterless_movement \
         custom_sisterless_vs_trackmate_plate_20260722 custom_lagging_examples_outlines_20260729 \
         cytosol_relax_accuracy kk_distance_vs_time_to_meta \
         kt_cell_outline kt_mad1_plots kt_oscillation kt_phase_split kt_polar_3d \
         kt_polar_phase_time kt_polar_tension_timelines kt_shape_plots kt_stats \
         kt_time_meta2ana kt_time_trajectories kt_track_plots kt_track_plots2 \
         gt_cdc20 negatives_by_radius; do run "$s"; done

# rebuild_186 / rebuild_182_187 MUST run AFTER group4_movement. Both write the plot_id
# G4_kt_intensity_polar_vs_plate: group4_movement from CIRCLE marks + TrackMate, rebuild_186 from her
# TRACED OUTLINES. User 2026-07-28: "update it so it's all manual data from kinetochore outlines
# instead of the current circle regions and trackmate data" - so the OUTLINE version is the live one
# and must be written last, or group4_movement silently clobbers it (observed 2026-07-29).
echo "STAGE 7b outline-derived plot 186/182-187 (must follow group4_movement)" >> "$LOG/_progress.txt"
for s in rebuild_186_outline_intensity rebuild_182_187_outline_intensity; do run "$s"; done

echo "STAGE 8 diagnostics" >> "$LOG/_progress.txt"
for s in diag_placement diag_temporal snap_proof verify_annotation_placement verify_kt_size verify_snap_demo; do run "$s"; done

echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
