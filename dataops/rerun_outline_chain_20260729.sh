#!/bin/bash
# Re-run EVERY measurement and plot derived from the manual kinetochore outlines, after the
# 2026-07-29 correction that a manual outline's measurement covers the enclosed area PLUS the pixels
# the traced line covers - which required area, perimeter, hull, circularity and solidity all to come
# from ONE raster of the traced polygon(s).
# Order: derived tables first, then every consumer.
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_outline_chain_20260729"; mkdir -p "$LOG"; : > "$LOG/_progress.txt"; : > "$LOG/_summary.tsv"
run(){ echo "=== START $1 $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"; t0=$(date +%s)
  python3 -u "$1.py" > "$LOG/$1.log" 2>&1; rc=$?; t1=$(date +%s)
  echo "=== END   $1 rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$1" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"; }
# derived tables from the outlines
for s in kt_shape_metrics kt_tracks kt_landmark_analysis kt_sisters kt_tension \
         kt_tension_withincell kt_tension_metaphase kt_chromo_analysis polar_fluor_matched; do run "$s"; done
# every plot builder that reads them
for s in kt_shape_plots kt_mad1_plots kt_track_plots kt_track_plots2 kt_oscillation kt_phase_split \
         kt_polar_3d kt_polar_phase_time kt_polar_tension_timelines kt_time_meta2ana \
         kt_time_trajectories kt_cell_outline kt_stats cytosol_relax_accuracy \
         custom_lagging_examples_outlines_20260729 lagging_auto_shape_v2 \
         group4_lagging_shape group5_mad1_polar_plate custom_questions_20260727 \
         custom_questions2_20260727 custom_questions3_20260727; do run "$s"; done
# outline-derived intensity figures LAST (they own plot 186/187)
for s in rebuild_186_outline_intensity rebuild_182_187_outline_intensity; do run "$s"; done
run make_zoom_companions
echo "ALL DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
