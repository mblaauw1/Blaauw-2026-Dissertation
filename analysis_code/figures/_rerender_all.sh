cd "/Volumes/4 MB/ablation_figures_20260625"
BUILDERS="group1_build.py g1_violin2.py group1_roundness.py group2_build.py group2_kk.py group2_prophase_dynamics.py group2_metaphase_ablated.py group3_build.py group3_plate_timing.py group3_pole_time.py group4_polar_lagging.py plot_1sis_polar_lagging.py group4_exhaustion_violin.py group4_lagging_shape.py group4_movement.py group4_drug.py metaphase_duration_delta.py chromo_length_congression_single.py group4_tracking_dist.py group4_fluor.py group4_ablation_intensity.py group4_frap.py group4_cdc20_poles.py custom_shape_rate_vs_metaphase.py"
for b in $BUILDERS; do
  out=$(python3 "$b" 2>&1); rc=$?
  echo "$([ $rc -eq 0 ] && echo OK || echo FAIL) $b"
  [ $rc -ne 0 ] && echo "$out" | grep -iv "zshenv\|cargo\|Decompress\|warnings.warn\|extra bytes\|created. timestamp" | tail -3
done
echo "ALL BUILDERS DONE"
