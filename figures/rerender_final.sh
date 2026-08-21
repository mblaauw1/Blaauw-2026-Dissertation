#!/bin/zsh
# Final re-render: calibrated frame mapping (FRAME_CALIBRATION.csv) + saturation guard + r=8.
cd "/Volumes/4 MB/ablation_figures_20260625"
export KT_R=9
LOG=/Volumes/4\ MB/ablation_plots/rerender_final.log
: > "$LOG"
echo "===== screen_kt_placement.py =====" >> "$LOG"
python3 screen_kt_placement.py >> "$LOG" 2>&1
echo "----- exit $? -----" >> "$LOG"
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
