#!/usr/bin/env python3
"""Assign all 549 live figures in copy.ai + the overflow board to her 8 META-FIGURES (2026-07-29f).

Her 8 topics, verbatim in short form:
  M1  Ablations can destroy one or multiple kinetochores in a cell in early phases of mitosis
  M2  One sisterless KT in early mitosis does NOT lengthen metaphase vs control; multiple do
  M3  Mad1 at sisterless kinetochores is consistent with an unsatisfied SAC if localised to poles
  M4  As metaphase duration increases, cells display more exaggerated physical phenotypes
  M5  Persistent polar chromosomes with sisterless KTs experience MORE force than paired bioriented
      KTs; smaller chromosomes reach end-on attachment and move plate-ward (merotelic risk)
  M6  Where a targeted chromosome ends up at anaphase depends on chromosome SIZE and on the NUMBER
      of sisterless kinetochores in the cell
  M7  Permanently disrupting three chromosomes inhibits maturation of paired KT oscillation, reduces
      force on persistent polar chromosomes, and destabilises the spindle
  M8  WHEN in mitosis the ablation happens drives the delay seen in the 2- and 3-sisterless groups

METHOD. Assignment is driven by the SOURCE ARTBOARD first - those boards are already thematic and were
grouped by her - and then corrected figure-by-figure with the OVERRIDES table below, which is where every
judgement call lives so it can be audited and changed in one place. Nothing is assigned by guessing from a
filename prefix alone.

CONFIDENCE. A figure placed by its board default AND not contradicted by an override is "sure". A figure
whose home is genuinely arguable is marked "unsure" and gets a RED OUTLINE on the meta-figure, per her
instruction ("if you're really having a hard time placing a figure ... make your best shot at where it
should go and then outline it in red").

  python3 build_meta_assignment_20260729.py          # write meta_assignment.json + print the audit
"""
import collections
import json
import os

ROOT = "/Volumes/4 MB"
INV = os.path.join(ROOT, "_deck_jsx_inputs/meta_inventory.json")
OUT = os.path.join(ROOT, "_deck_jsx_inputs/meta_assignment.json")

TITLES = {
    "M1": "Ablation destroys one or several kinetochores in early mitosis",
    "M2": "One sisterless kinetochore does not delay metaphase; several do",
    "M3": "Mad1 at sisterless kinetochores: an unsatisfied checkpoint at the poles",
    "M4": "Longer metaphase, more exaggerated cell-shape phenotypes",
    "M5": "Force on persistent polar kinetochores, and how small chromosomes escape",
    "M6": "Chromosome size and sisterless number set the anaphase fate",
    "M7": "Three disrupted chromosomes: oscillation, force and spindle stability",
    "M8": "When the ablation happens sets the delay",
    # ---- ONE split, using the first of the 1-3 she allowed --------------------------------------
    # M5 came out at 183 figures, more than twice any other board, and it was carrying two different
    # arguments. 67 of those are the SYSTEMATIC SWEEP families - G6time_* (aligned to metaphase onset),
    # G6timeMA_* (metaphase->anaphase refit), G6ph_* (split by mitotic phase), G6ppt_* (polar KT coloured
    # by phase) and G6poly_* - which are the same handful of shape/motion measures re-plotted over every
    # time base. They are a reference panel, not part of the force argument, and interleaving them buries
    # the tension and oscillation figures that ARE the argument. Split off; M5 drops to 116.
    "M5b": "Kinetochore shape and motion across mitotic time: the systematic sweep",
}

# ---- source artboard -> default meta-figure ------------------------------------------------------
BOARD_DEFAULT = {
    "AB1": "M2",    # metaphase-duration violins
    "AB2": "M2",    # time-to-anaphase survival
    "AB3": "M4",    # cell shape (roundness / area)
    "AB4": "M4",    # shape at onset vs duration
    "AB5": "M1",    # example timestrips of the ablations themselves
    "AB6": "M2",    # mitotic-phase durations  (the phase-SPLIT ones move to M8 below)
    "AB7": "M5",    # k-k distance = the tension readout
    "AB8": "M6",    # chromosome length
    "AB9": "M6",    # KT fate / position / congression
    "AB10": "M1",   # FRAP recovery - evidence the KT was actually destroyed
    "AB11": "M1",   # ablation intensity
    "AB12": "M1",   # pre/post-ablation intensity
    "AB13": "M6",   # polar & lagging chromosomes
    "AB14": "M5",   # kinetochore oscillation
    "AB15": "M5",   # KT velocity & plate distance
    "AB16": "M2",   # eYFP-Cdc20 intensity over time - the checkpoint/degradation readout
    "AB17": "M4",   # cell fluorescence, mostly vs duration
    "AB18": "M8",   # drug controls (Noc / ZM) - she asked for the washouts here
    "AB19": "M1",   # FRAP timestrips
    "AB20": "M3",   # IF quantification (Mad1 / Hec1)
    "AB21": "M3",   # Mad1 / Hec1 IF imaging
    "AB22": "M4",   # "custom analyses" - mostly shape-rate vs metaphase duration
    "AB24": "M4",   # collagen variants: shape over metaphase
    "AB25": "M6",   # lagging KT length over time
    "AB26": "M6",   # lagging KT auto shape
    "AB27": "M6",   # sisterless-KT behaviour vs metaphase duration
    "AB28": "M6",   # length -> position -> congression -> fate
    "AB29": "M5",   # sisterless-KT movement / oscillation
    "AB30": "M5",   # KT outline morphometrics = the stretch/force readout
    "AB31": "M6",   # per-track chromosome measurements
    "AB32": "M5",   # cell-outline / sisters / oscillation / predictive
    "OV-AB1": "M5", # force / tension on the polar kinetochore
    "OV-AB2": "M5", # over time, aligned to metaphase onset
    "OV-AB3": "M5", # distributions split by mitotic phase
    "OV-AB4": "M5", # polar KT over time, coloured by phase
    "OV-AB5": "M5", # polar KT: time x distance-to-plate x area
    "OV-AB6": "M5", # sister k-k oscillation: single vs 2/3 ablation
    "OV-AB7": "M5", # over time: metaphase onset to anaphase
}

# ---- per-figure corrections. (meta, sure?) --------------------------------------------------------
# Each entry is a place where the board default is wrong for THIS figure, with the reason.
OVERRIDES = {}


def put(meta, figs, sure=True, why=""):
    for f in figs:
        OVERRIDES[f] = (meta, sure, why)


# --- M8: the phase-of-ablation story is scattered across AB6 and AB28 -------------------------------
put("M8", [
    "G2_phase_split_violin_v2_journal", "G2_phase_split_violin_v2_tripledouble_journal",
    "G2_phase_split_statgrid", "G2_abl_to_meta_1sis_prophase", "G2_abl_to_meta_1sis_prophase_zoom",
    "G2_abl_to_meta_1sis_prometaphase", "G2_prophase_dynamics", "G2_prometaphase_dynamics",
    "G2_metaphase_dynamics_prometa",
], why="ablation PHASE vs delay - M8's core claim, not a plain duration comparison")
put("M8", [
    "G2_prophase_dynamics_zoom", "G2_prometaphase_dynamics_lastablation", "G2_prometa_combined_123",
    "G2_prometa_combined_13", "G2_prometa_ratio", "G2_prometa_zscore",
    "triple_prometa_ablation_to_mitosis", "G2_noc_washout_metaphase_by_sisterless",
    "G3_creation_time_vs_behavior",
], why="prometaphase-vs-prophase timing and the noc washout, from AB28")

# --- M7: the 3-sisterless / spindle-instability set -------------------------------------------------
put("M7", [
    "G3_plate_rotation_by_group", "G3_plate_rotation_by_group_zoom", "G3_plate_rotation_vs_polar_length",
    "metaplate_rotation_by_sisterless", "metaplate_rotation_by_sisterless_win_meta_to_ana",
    "G1_cell_centroid_movement_by_group", "G1_cell_centroid_movement_by_group_zoom",
    "centroid_movement_metaphase_to_anaphase_vs_sisterless",
    "centroid_movement_metaphase_to_anaphase_vs_sisterless_zoom",
    "G3_cell_movement_vs_polar_length_sum", "G3_cell_movement_vs_polar_length_sum_zoom",
], why="plate rotation and whole-cell movement = spindle instability, M7")
put("M7", ["G6trk_postanaphase_speed"],
    why="she asked for the anaphase chromatid-speed comparison (1 vs 3 sisterless) on M7")
put("M7", ["G2_combined_23_sisterless", "G2_trend_single_vs_triple"], sure=False,
    why="1-vs-3 contrast: could equally sit on M2 as a duration comparison")

# --- M4: the shape-rate story, plus the two she named explicitly ------------------------------------
put("M4", ["G3_slippage_timestrip_colcemid", "G3_slippage_timestrip_colcemid_aligned",
           "G3_slippage_timestrip_nocodazole", "G3_slippage_timestrip_nocodazole_aligned"],
    why="she asked for the colcemid plots on M4")
put("M4", ["G4_distance_vs_roundness", "G4_distance_vs_roundness_win_meta_to_ana",
           "G4_plate_distance_time_roundness", "G4_plate_distance_time_roundness_win_meta_to_ana"],
    why="KT-to-plate distance vs cell roundness - the plot she asked to split in two on M4")
put("M4", ["G6cell_area_vs_progress", "G6cell_circularity_vs_progress", "G6cell_symmetry_vs_progress",
           "G6cell_ktdist_vs_cellarea", "G6cell_ktstretch_vs_cellcirc"],
    why="whole-CELL shape against mitotic progress belongs with the cell-phenotype figure")

# --- M2: exhaustion controls set the ceiling on how long metaphase can last -------------------------
put("M2", ["G4_exhaustion_violin_journal", "G4_exhaustion_statgrid",
           "G4_exhaustion_violin_journal_win_measured_exit",
           "G4_exhaustion_violin_journal_win_measured_exit_zoom",
           "G4_exhaustion_violin_journal_win_nebd_captured",
           "G4_exhaustion_violin_journal_win_nebd_captured_zoom",
           "metaphase_duration_delta_from_unmodified", "metaphase_duration_delta_from_unmodified_zoom"],
    why="metaphase-duration comparisons and their arrest ceiling")

# --- M1: the ablation itself ------------------------------------------------------------------------
put("M1", ["ablation_count_by_cohort", "ablation_count_by_cohort_zoom", "ablation_count_on_vs_offpooled",
           "ablation_count_on_vs_offpooled_zoom", "G4_ablation_individual_contactsheet"],
    why="how many ablations were delivered, and to what")
put("M1", ["G3_ablation_location_vs_behavior"], sure=False,
    why="ablation geometry, but its payload is behaviour - could be M6")

# --- M5 vs M6 boundary cases ------------------------------------------------------------------------
put("M5", ["G5shape_polar_vs_paired_area", "G5shape_polar_vs_paired_aspect",
           "G5shape_fracstretched_by_class", "G5shape_maxaspect_by_class"],
    why="polar vs paired KT stretch IS the force readout M5 is about")
put("M6", ["G5shape_lagging_stretch_time", "G5shape_lagging_stretch_time_zoom"],
    why="lagging-specific: an anaphase fate, M6")
put("M6", ["G6trk_chromo_length", "G6trk_chromo_farend", "G6trk_chromo_farend_zoom",
           "G6trk_chromo_nearend", "G6trk_chromo_nearend_zoom", "G6trk_chromo_orient",
           "G6trk_chromolen_vs_aspect", "G6trk_chromolen_vs_circ", "G6trk_chromolen_vs_speed"],
    why="chromosome SIZE vs outcome - M6's core variable")
put("M5", ["G6trk_speed_by_phase", "G6trk_speed_by_phase_zoom", "G6trk_speed_vs_time",
           "G6trk_speed_vs_time_zoom", "G6trk_dist_to_plate", "G6trk_dist_vs_time",
           "G6trk_distance_per20s", "G6trk_distance_total", "G6trk_distance_total_zoom",
           "G6trk_toward_vs_away", "G6trk_toward_vs_away_zoom", "G6trk_stretch_radial",
           "G6trk_fractures", "G6trk_reflection_asym", "G6trk_anisotropy", "G6trk_anisotropy_zoom"],
    why="motion and stretch of the tracked KT - M5")
put("M5", ["pole_to_plate_jointime_vs_duration"],
    why="pole-to-plate travel time: a movement measure")
put("M6", ["pole_to_plate_behavior_vs_duration"], sure=False,
    why="pole-to-plate BEHAVIOUR classes read as fate (M6) but the axis is duration (M4)")
put("M4", ["G1_shape_rate_vs_congression"], sure=False,
    why="shape rate (M4) against congression (M6) - genuinely spans two figures")
put("M2", ["G4_fluor_vs_duration", "G4_fluor_vs_duration_scaled01", "G4_fluor_vs_duration_unmodified",
           "G4_fluor_vs_duration_zoom"], sure=False,
    why="Cdc20 level vs metaphase duration: checkpoint story (M2) or cell phenotype (M4)")


SWEEP_PREFIXES = ("G6time_", "G6timeMA_", "G6ph_", "G6ppt_", "G6poly_")


def main():
    rows = json.load(open(INV))
    out, unknown = {}, []
    for r in rows:
        f, ab = r["fig"], r["ab"]
        if f in OVERRIDES:
            meta, sure, why = OVERRIDES[f]
        elif ab in BOARD_DEFAULT:
            meta, sure, why = BOARD_DEFAULT[ab], True, "source board " + ab
        else:
            meta, sure, why = "M6", False, "no rule - parked on M6, RED"
            unknown.append(f)
        if meta == "M5" and f.startswith(SWEEP_PREFIXES):
            meta, why = "M5b", "systematic time/phase sweep - split off M5 (see M5b note)"
        out[f] = {"meta": meta, "sure": bool(sure), "why": why, "src": ab, "title": r["title"]}

    json.dump(out, open(OUT, "w"), indent=1)
    n = collections.Counter(v["meta"] for v in out.values())
    unsure = [k for k, v in out.items() if not v["sure"]]
    print(f"assigned {len(out)} figures  (inventory {len(rows)})")
    for m in sorted(TITLES):
        print(f"   {m}  {n[m]:4d}   {TITLES[m]}")
    print(f"\nRED-OUTLINED (uncertain placement): {len(unsure)}")
    for u in sorted(unsure):
        print(f"   {u:56s} -> {out[u]['meta']}   {out[u]['why']}")
    if unknown:
        print(f"\nNO RULE AT ALL ({len(unknown)}): {unknown}")
    assert len(out) == len(rows), "every inventory figure must get exactly one meta-figure"


if __name__ == "__main__":
    main()
