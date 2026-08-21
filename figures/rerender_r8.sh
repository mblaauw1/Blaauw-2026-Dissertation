#!/bin/zsh
# Full r=8 re-render with the misplaced-annotation exclusion active (MISPLACED_KT_IDS.txt = 44 ids).
cd "/Volumes/4 MB/ablation_figures_20260625"
export KT_R=8
LOG=/Volumes/4\ MB/ablation_plots/rerender_r8.log
: > "$LOG"
for s in \
  group4_ablation_intensity.py \
  group4_cdc20_poles.py \
  group4_fluor.py \
  group4_frap.py \
  group4_prepost.py \
  group4_movement.py \
  group4_tracking_dist.py \
  group4_lagging_shape.py \
  group4_lagging_examples.py \
  group4_polar_lagging.py \
  negatives_by_radius.py ; do
  echo "===== $s =====" >> "$LOG"
  python3 "$s" >> "$LOG" 2>&1
  echo "----- exit $? -----" >> "$LOG"
done
echo "RERENDER_DONE" >> "$LOG"
