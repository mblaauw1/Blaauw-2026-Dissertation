# Deck figure -> builder map

Generated from the read-only Illustrator geometry dumps of 2026-08-21 and `ablation_plots/PLOT_SETTINGS.json`, which records the generating script for every registered figure.

The full per-figure table is **`DECK_FIGURE_BUILDER_MAP.csv`** (`deck_tag, deck_file, artboard, figure, builder_in_this_repo, caption`).

## The decks

| tag | role | file |
|---|---|---|
| `0814` | main working | `META_FIGURES_20260814.ai` |
| `0813supp` | supplemental working | `META_FIGURES_20260813_supplemental.ai` |
| `newfig` | new figures | `NEW_FIGURES_20260804.ai` |
| `supp` | other | `other_20260820.ai` |
| `newts` | timestrips | `NEW_TIMESTRIPS_20260804.ai` |
| `pub0814` | main PUBLICATION | `META_FIGURES_20260814_PUBLICATION_20260820.ai` |
| `pub0813` | supplemental PUBLICATION | `META_FIGURES_20260813_supplemental_PUBLICATION_20260820.ai` |

**790 distinct figures** are placed across the five live decks; 828 across those plus the two publication copies. 123 distinct builder scripts produce them.

## Builders, by number of placed figures

| figures | builder |
|---|---|
| 102 | `figures/group_timestrips.py` |
| 96 | `figures/group1_roundness.py` |
| 39 | `figures/group5_mad1_examples.py` |
| 34 | `figures/custom_lagging_examples_outlines_20260729.py` |
| 33 | `figures/group4_polar_timestrips.py` |
| 31 | `figures/group_drug_ablation_timestrips.py` |
| 19 | `figures/custom_new_figures_20260804.py` |
| 17 | `figures/custom_todo0819_measure_strips.py` |
| 17 | `figures/group2_build.py` |
| 16 | `figures/custom_delta_axis_variants_20260816.py` |
| 16 | `figures/group4_movement.py` |
| 16 | `figures/kt_track_plots.py` |
| 15 | `figures/kt_track_plots2.py` |
| 14 | `figures/custom_todo0818_analysis.py` |
| 14 | `figures/group3_build.py` |
| 11 | `figures/custom_lagging_dynamics_20260804.py` |
| 11 | `figures/custom_perkt_vs_percell_20260810.py` |
| 11 | `figures/group4_tracking_dist.py` |
| 11 | `figures/kt_tension_metaphase.py` |
| 10 | `figures/custom_kymographs_20260820.py` |
| 9 | `figures/kt_shape_plots.py` |
| 8 | `deck/archived_builders/G7_kt_movement_vs_context__20260808.py` |
| 8 | `figures/custom_metafig_subitems_20260729.py` |
| 8 | `figures/g1_violin2.py` |
| 8 | `figures/group4_fluor.py` |
| 8 | `figures/group4_polar_lagging.py` |
| 7 | `figures/build_demo_timestrips.py` |
| 7 | `figures/custom_todo0819b_oscillations.py` |
| 7 | `figures/group_slippage_timestrips.py` |
| 7 | `figures/kt_oscillation.py` |
| 6 | `figures/custom_ab7_peak_zooms_20260816.py` |
| 6 | `figures/custom_six_polar_paired_strips_20260810.py` |
| 6 | `figures/group5_hec1_timestrip.py` |
| 6 | `figures/kk_osc_refined.py` |
| 6 | `figures/kt_tension_withincell.py` |
| 5 | `figures/custom_ab5_excerpts_20260817.py` |
| 5 | `figures/custom_plots_to_make_part2_20260722.py` |
| 5 | `figures/custom_prometa_vs_meta_20260810.py` |
| 5 | `figures/group4_lagging_shape.py` |
| 4 | `dataops/register_unlegended_20260818.py` |
| 4 | `figures/G7_prometa_single_vs_meta_triple__20260808.py` |
| 4 | `figures/custom_ablation_location_vs_behavior.py` |
| 4 | `figures/custom_congression_dynamics_20260804.py` |
| 4 | `figures/custom_lagging_vs_congression.py` |
| 4 | `figures/custom_sisterless_movement.py` |
| 4 | `figures/custom_todo0818_model.py` |
| 4 | `figures/group1_build.py` |
| 4 | `figures/group2_prophase_dynamics.py` |
| 4 | `figures/group4_ablation_intensity.py` |
| 4 | `figures/group4_drug.py` |
| 3 | `deck/archived_builders/G7_prophase_vs_prometaphase_triple__20260808.py` |
| 3 | `deck/archived_builders/G7_track_to_chromosome_assignment__20260808.py` |
| 3 | `figures/custom_area_vs_distortion_20260805.py` |
| 3 | `figures/custom_lagging_congression_doubleablation_split_20260803.py` |
| 3 | `figures/custom_oscillation_1v3_20260805.py` |
| 3 | `figures/custom_rtf_questions_20260722.py` |
| 3 | `figures/custom_sisterless_fluor_20260722.py` |
| 3 | `figures/custom_sisterless_longaxis.py` |
| 3 | `figures/group2_metaphase_ablated.py` |
| 3 | `figures/group4_exhaustion_violin.py` |
| 3 | `figures/make_window_companions_20260729.py` |
| 2 | `deck/archived_builders/G1_imaging_rate_vs_metaphase_unmodified__QNEW_imaging_rate_vs_metaphase__unmodified_20260808.py` |
| 2 | `deck/archived_builders/G5_hec1_mad1_multibatch_quant__20260808.py` |
| 2 | `deck/archived_builders/G5_mad1_kt_fluor_over_time__mad1_20260808.py` |
| 2 | `deck/archived_builders/G5_sac_active_kt_over_time__20260808.py` |
| 2 | `deck/archived_builders/G6_polar_dist_to_plate_over_metaphase__20260808.py` |
| 2 | `figures/ablation_count_by_cohort.py` |
| 2 | `figures/custom_abl_to_meta_vs_duration_20260805.py` |
| 2 | `figures/custom_allgroup_violin_and_table_20260817.py` |
| 2 | `figures/custom_creation_time_vs_behavior.py` |
| 2 | `figures/custom_length_spread_20260722.py` |
| 2 | `figures/custom_lineplot_shape_by_metaphase.py` |
| 2 | `figures/custom_osc_definition_panels_20260810.py` |
| 2 | `figures/custom_polar_tension_vs_chromolen_20260805.py` |
| 2 | `figures/custom_shape_rate_vs_metaphase.py` |
| 2 | `figures/custom_todo0819_collagen_table_figs.py` |
| 2 | `figures/custom_todo0819b_kt_size_intensity.py` |
| 2 | `figures/group2_kk.py` |
| 2 | `figures/group3_plate_timing.py` |
| 2 | `figures/group4_cdc20_poles.py` |
| 2 | `figures/group4_prepost.py` |
| 2 | `figures/group5_if_timestrip.py` |
| 2 | `figures/kt_cell_outline.py` |
| 2 | `figures/kt_polar_phase_time.py` |
| 2 | `figures/kt_sisters.py` |
| 2 | `figures/kt_tension.py` |
| 2 | `figures/kt_time_meta2ana.py` |
| 2 | `figures/kt_time_trajectories.py` |
| 2 | `figures/metaphase_duration_delta.py` |
| 2 | `figures/sisterless_congression_score.py` |
| 1 | `deck/archived_builders/G7_triple_converges_on_single__20260808.py` |
| 1 | `deck/archived_builders/G8_pole_distance_over_time__20260809.py` |
| 1 | `deck/archived_builders/kk_vs_time.py` |
| 1 | `figures/chromo_length_congression_single.py` |
| 1 | `figures/custom_cdc20_vs_bleaching_spec_20260722.py` |
| 1 | `figures/custom_double_chromosome_violin_20260722.py` |
| 1 | `figures/custom_frap_bps_20260817.py` |
| 1 | `figures/custom_kk_zoom_candidates_20260816.py` |
| 1 | `figures/custom_lagging_fragment_strips_20260810.py` |
| 1 | `figures/custom_lagging_stretch_reference_20260821.py` |
| 1 | `figures/custom_length_congression_outcomes.py` |
| 1 | `figures/custom_mad1_kt_fluor_traces_20260803.py` |
| 1 | `figures/custom_max_congression_delay_20260722.py` |
| 1 | `figures/custom_meta_ana_pairs_20260816.py` |
| 1 | `figures/custom_metaphase_early_late_20260804.py` |
| 1 | `figures/custom_noc_washout_v2_20260722.py` |
| 1 | `figures/custom_osc_metric_sensitivity_20260810.py` |
| 1 | `figures/custom_plots_to_make_20260722.py` |
| 1 | `figures/custom_todo0819_rate_table.py` |
| 1 | `figures/custom_todo0819b_pooling_test.py` |
| 1 | `figures/figures/G1_violin2_sisterless_1234.py` |
| 1 | `figures/figures/G4_lagging_bar.py` |
| 1 | `figures/group3_pole_time.py` |
| 1 | `figures/group5_mad1_polar_plate.py` |
| 1 | `figures/group_frap_timestrips.py` |
| 1 | `figures/kt_polar_3d.py` |
| 1 | `figures/lagging_auto_shape_v2.py` |
| 1 | `figures/lagging_length_over_time.py` |
| 1 | `figures/lagging_vs_congression_timing.py` |
| 1 | `figures/pole_to_plate_vs_duration.py` |
| 1 | `figures/rebuild_182_187_outline_intensity.py` |
| 1 | `figures/rebuild_186_outline_intensity.py` |
| 1 | `figures/sisterless_behavior_vs_duration.py` |
