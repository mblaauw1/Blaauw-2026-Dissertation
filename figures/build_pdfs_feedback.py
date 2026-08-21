"""Build BOTH updated PDFs after the 2026-07-06 feedback pass:
  ablation_figures.pdf           — same group order as before, with add/remove/swap changes
  ablation_figures_REORDERED.pdf — group-label separators removed, companions kept adjacent,
                                    RETIRED-plots section at the end.
Reads the GROUPS manifest from deck.py, mutates it, renders via reportlab (no captions beyond
the short bottom label, matching the current no-long-caption PDF the user likes)."""
import os, copy
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT="/Volumes/4 MB/ablation_figures_20260625"
IMGCACHE=os.path.join(ROOT,"_compact_img"); os.makedirs(IMGCACHE,exist_ok=True)
MAXW=2200; JPEGQ=82

ns={}
top=open(os.path.join(ROOT,"deck.py")).read().split("# ---------------- PPTX")[0]
exec(top,ns)
GROUPS=copy.deepcopy(ns["GROUPS"])

def compact(img):
    src=os.path.join(ROOT,img)
    if not os.path.isfile(src): return None
    out=os.path.join(IMGCACHE,img.replace("/","__").rsplit(".",1)[0]+".jpg")
    if os.path.isfile(out) and os.path.getmtime(out)>=os.path.getmtime(src): return out
    im=Image.open(src)
    if im.mode in ("RGBA","P","LA"):
        bg=Image.new("RGB",im.size,(255,255,255)); bg.paste(im.convert("RGBA"),mask=im.convert("RGBA").split()[-1]); im=bg
    else: im=im.convert("RGB")
    if im.width>MAXW: im=im.resize((MAXW,max(1,round(im.height*MAXW/im.width))),Image.LANCZOS)
    im.save(out,"JPEG",quality=JPEGQ,optimize=True); return out

# ---------- companion pairing (same-slide 2-up: an original + its outlier _zoom / _journal sibling) ----------
# Reusable: given a BASE figure path, return the companion PNGs that exist on disk so the deck can place the
# original and its companion on ONE slide (side-by-side) instead of two separate slides.
def companion_pngs(img):
    """On-disk companions of a BASE figure, ordered: <stem>_zoom.png, <stem>_journal.png,
    <stem>_journal_zoom.png. Returns [] when `img` is itself a companion (avoids double-pairing)."""
    b=os.path.basename(img)
    if b.endswith("_zoom.png") or b.endswith("_journal.png"): return []
    stem=img[:-4]; out=[]
    for cand in (stem+"_zoom.png", stem+"_journal.png", stem+"_journal_zoom.png"):
        if os.path.isfile(os.path.join(ROOT,cand)): out.append(cand)
    return out
def companion_label(img):
    b=os.path.basename(img)
    if b.endswith("_journal_zoom.png"): return "journal-style, outlier-trimmed companion"
    if b.endswith("_journal.png"):      return "journal-style companion"
    if b.endswith("_zoom.png"):         return "outlier-trimmed companion"
    return "original"

# ---------- helpers to mutate the manifest by matching the image path ----------
def find(group_n, contains):
    g=next(g for g in GROUPS if g["n"]==group_n)
    for i,s in enumerate(g["slides"]):
        if "img" in s and contains in s["img"]: return g,i
    return next(g for g in GROUPS if g["n"]==group_n), None
def insert_after(group_n, after_contains, img, cap):
    g,i=find(group_n, after_contains)
    if i is None: g["slides"].append({"img":img,"cap":cap})
    else: g["slides"].insert(i+1,{"img":img,"cap":cap})
def remove(group_n, contains):
    g=next(g for g in GROUPS if g["n"]==group_n)
    g["slides"]=[s for s in g["slides"] if not ("img" in s and contains in s["img"])]
def swap_img(group_n, old_contains, new_img):
    g,i=find(group_n, old_contains)
    if i is not None: g["slides"][i]["img"]=new_img

# ===== APPLY FEEDBACK MANIFEST CHANGES =====
# G3: chromo-length by-sister companions
insert_after(5,"G3_chromo_length.png","group3/G3_chromo_length_bysister.png",
             "Chromosome length vs metaphase duration — trendlines per 1/2/3-sisterless group (points colored by phase)")
insert_after(5,"G3_chromo_length_percell.png","group3/G3_chromo_length_percell_bysister.png",
             "Chromosome length (per-cell avg) vs metaphase duration — trendlines per sisterless group")
# G6: swap polar-timestrip cell (old movie corrupt) -> new cell
swap_img(6,"G4_polar_timestrip_20250401_ptk_yfpcdc20_28.png","group4/G4_polar_timestrip_20250410_ptk_yfpcdc20_11.png")
# G6: T16 — add two NEW timestrips to the polar trio (full format: marked ablation + zoom + monitoring).
insert_after(6,"G4_polar_timestrip_20250403_ptk_yfpcdc20_22.png",
             "group4/G4_polar_timestrip_20260416_single_ablation_10.png",
             "Timestrip — single ablation; sisterless KT at the metaphase plate the whole rest of mitosis (ablation + zoom + monitoring, phase+fluor)")
insert_after(6,"G4_polar_timestrip_20260416_single_ablation_10.png",
             "group4/G4_polar_timestrip_20260416_single_ablation_15.png",
             "Timestrip — single ablation; good/stretched LAGGING kinetochore example (ablation + zoom + monitoring, phase+fluor)")
# G6: ALIGNED-CROP variant of each polar timestrip (immediately after its status-quo version) — main ablation +
# zoom + monitoring tiles share one fixed-physical (78µm) square footprint so every batch renders at the SAME
# magnification with column-aligned stacking.
for _base,_kind in [("20250410_ptk_yfpcdc20_11","polar KT joins the plate"),
                    ("20250403_ptk_yfpcdc20_22","polar KT persists to anaphase"),
                    ("20260416_single_ablation_10","sisterless KT at the plate whole mitosis"),
                    ("20260416_single_ablation_15","lagging/stretched KT")]:
    insert_after(6, f"G4_polar_timestrip_{_base}.png",
                 f"group4/G4_polar_timestrip_{_base}_aligned.png",
                 f"Polar timestrip — {_kind}, ALIGNED-CROP variant: main ablation + zoom + monitoring tiles share one fixed-physical 78µm square footprint (consistent magnification across batches; zoom column-aligned under the main row)")
# G1: FRAP timestrip = a sample that ALSO appears in the FRAP selected-combined recovery-traces plot
# (user request) — 20250411 ptk_yfpcdc20_13 (#0), a clean single-cell FRAP with a clear ablation site + recovery.
swap_img(1,"frap_timestrips/20250501_ptk_yfpcdc20_12_frap0.png","group1/frap_timestrips/20250411_ptk_yfpcdc20_13_frap0.png")
# G3(sec4 duration): add the new 4-panel duration stat grid right after the duration figure
insert_after(3,"G2_duration_combined.png","group2/G2_duration_statgrid.png",
             "Duration comparisons — four Mann–Whitney-U stat grids (Meta→Ana, First-Align→Meta, NEBD→Meta, Ana→Cyto)")
# G3: point shape-at-metaphase-onset stat grid at the new correct grid (was mis-wired to violin2 grid)
insert_after(3,"G1_start_rounded_metaphase.png","group1/G1_start_rounded_metaphase_statgrid.png",
             "Shape at metaphase onset vs metaphase duration — stat grid (per-group Spearman ρ, p)")
# G7: distance-to-plate roundness iteration
insert_after(7,"G4_plate_distance_time.png","group4/G4_plate_distance_time_roundness.png",
             "Polar/sisterless-KT distance to plate over time — points colored by cell roundness")
# G2 (validation): prepost second version (no connector lines)
insert_after(2,"G4_prepost_intensity.png","group4/G4_prepost_intensity_nolines.png",
             "Pre- vs post-ablation KT intensity — connectors removed (scatter + median/mean + Wilcoxon)")
# G2 (validation): FRAP both-normalized combined + successful-ablation selected combined (new selected-trace plots)
insert_after(2,"G4_frap_combined.png","group4/G4_frap_both_combined.png",
             "FRAP — selected COMBINED recovery traces, both-normalized (targeted+sister each start=1; y-floor 0)")
insert_after(2,"G4_ablation_intensity_combined.png","group4/G4_ablation_intensity_selected_combined.png",
             "Successful-ablation — selected COMBINED traces (targeted+sister start=1; y-floor 0; open circle = missing point)")
# G10: fluor metaphase-onset companions + paired cdc20 plot (Agent G new plots)
insert_after(10,"G4_fluor_over_time.png","group4/G4_fluor_over_time_metaphase.png",
             "Cell fluorescence over time — starting at METAPHASE ONSET (trends capped at each group's mean metaphase duration)")
insert_after(10,"G4_fluor_over_time_scaled01.png","group4/G4_fluor_over_time_scaled01_metaphase.png",
             "Cell fluorescence SCALED 0–1 — starting at metaphase onset (each group re-normalized to 1 at metaphase onset)")
insert_after(10,"G4_cdc20_intensity_sanitycheck.png","group4/G4_distance_vs_fluor_paired.png",
             "eYFP-Cdc20 polar vs plate KT — PAIRED same-cell same-method (Wilcoxon polar>plate; stats on plot)")
# G10: retire redundant/incorrect cdc20_vs_distance (user 2026-07-09) — now handled via RETIRE list below
# so it is recorded as retired (appears in retired section + retired_figs.json, excluded from .ai manifest).
# remove(10,"G4_cdc20_vs_distance.png")
# G9: remove the ZM-3-groups-only plot
remove(9,"G4_zm_by_target.png")
# G9: TWO NEW drug-ablation TIMESTRIPS (full ablation format: marked ablation + zoom + monitoring, phase+fluor)
# placed with the drug controls; each followed by its fixed-physical-78µm ALIGNED-CROP variant.
insert_after(9,"G4_nocodazole.png","group4/G9_drug_timestrip_noc.png",
             "Timestrip — low-dose nocodazole + 1 ablation (20260416 …noc_15): ablation (red-circle marker) + zoom + monitoring; eYFP-Cdc20 stays bright and cell has NOT reached anaphase by 1:18:00 (mitotic arrest); phase+fluor, 10µm bar")
insert_after(9,"G9_drug_timestrip_noc.png","group4/G9_drug_timestrip_noc_aligned.png",
             "Low-dose nocodazole ablation timestrip — ALIGNED-CROP variant (main ablation + zoom + monitoring tiles share one fixed-physical 78µm square footprint; consistent magnification, zoom column-aligned under the main row)")
insert_after(9,"G4_zm.png","group4/G9_drug_timestrip_zm.png",
             "Timestrip — ZM (Aurora-B inhibitor) + 3-sisterless ablation (20260422 Zm_ablation_2um_31): ablation (red-circle markers) + zoom close-ups + monitoring; two chromosomes polar until anaphase (~32:26), cell proceeds to cytokinesis (~41:06); phase+fluor, 10µm bar")
insert_after(9,"G9_drug_timestrip_zm.png","group4/G9_drug_timestrip_zm_aligned.png",
             "ZM ablation timestrip — ALIGNED-CROP variant (main ablation + zoom + monitoring tiles share one fixed-physical 78µm square footprint; consistent magnification, zoom column-aligned under the main row)")
# ZM cell with 3 CLEAR ablations (kept the 2-visible-site _31 too) + aligned variant
insert_after(9,"G9_drug_timestrip_zm_aligned.png","group4/G9_drug_timestrip_zm3.png",
             "Timestrip — ZM + 3-sisterless ablation (20260422 Zm_ablation_2um_25): 3 spatially-distinct ablated KTs (3 red-circle markers + 3 zoom close-ups) + monitoring; cell stays a rounded mitotic mass in prolonged arrest (no anaphase); phase+fluor, 10µm bar")
insert_after(9,"G9_drug_timestrip_zm3.png","group4/G9_drug_timestrip_zm3_aligned.png",
             "ZM 3-ablation timestrip — ALIGNED-CROP variant")
# new FRAP recovery vs complete-ablation comparison plot (targeted only) — near the other FRAP combined plots
insert_after(2,"G4_frap_both_combined.png","group4/G4_frap_vs_complete_targeted.png",
             "FRAP recovery vs complete ablation — TARGETED kinetochore only (no sisters); each start-normalized to 1; faint individual traces + bold binned-median trend per group (FRAP=blue, complete ablation=red)")
# candidate-picker slides (≥4 cells each) so the user can choose the best
insert_after(1,"unmanipulated-control.png","group1/timestrips2/unmanipulated_candidates.png",
             "Unmanipulated-control CANDIDATES — several good unmodified cells (start→meta→ana→cyto), tight square crop, each labeled; pick the best")
insert_after(1,"20250411_ptk_yfpcdc20_13_frap0.png","group1/frap_timestrips/frap_candidates.png",
             "FRAP timestrip CANDIDATES — several FRAP cells, tight square crop, each labeled; pick the best")
# G11 (IF/Mad1): add the new IF/Mad1/hec1 quantification + timestrip plots
for img,cap in [
    ("group4/G5_item2_IF_KT_561.png","IF KT quantification — sisterless vs paired KT, 561 channel (per-cell normalized to mean paired-KT)"),
    ("group4/G5_item2_IF_KT_640.png","IF KT quantification — sisterless vs paired KT, 640 channel"),
    ("group4/G5_item3_mad1_polar_vs_plate.png","Mad1 IF — polar vs plate KT (488/Mad1, background-normalized; 20260304 Mad1 batches)"),
    ("group4/G5_item4_hec1_timestrip_xy5.png","Hec1 timestrip — 20260313 …Hec1halo_640_4_xy5 (unaligned / biorientation / anaphase onset)"),
    ("group4/G5_item4_hec1_timestrip_xy2.png","Hec1 timestrip — 20260313 …Hec1halo_640_4_xy2 (comment-flagged good timelapse; Hec1 marks all KTs)"),
    ("group4/G5_item4_hec1_timestrip_xy4.png","Hec1 timestrip — 20260313 …Hec1halo_640_4_xy4 (comment-flagged good timelapse)"),
    ("group4/G5_item4_hec1_timestrip_xy6.png","Hec1 timestrip — 20260313 …Hec1halo_640_4_xy6 (comment-flagged good timelapse)"),
    ("group4/G5_IF_mad1hec1_pos9_tubsub.png","IF (Mad1/Hec1) — TUBULIN-SUBTRACTED variant: CREST' = CREST − 0.75·tubulin, Mad1' = Mad1 − 0.75·tubulin (clip 0) to strip spindle background; + KT zoom close-ups")]:
    next(g for g in GROUPS if g["n"]==11)["slides"].append({"img":img,"cap":cap})

# ===== NEW SLIDES (2026-07-14): new analysis plots (each into its topical group) =====
for _n,_img,_cap in [
    (2,"group1/ablation_count_by_cohort.png","Ablation dose control — laser ablation events per cell, on- vs off-target split by count (1/2/3); tests matched dose (off-1/off-3 tiny n)"),
    (2,"group1/ablation_count_on_vs_offpooled.png","Ablation dose control — on-target (1/2/3) vs POOLED off-target; on-target 10.5 vs off-target 11.6 events, no significant difference (matched dose)"),
    (3,"group1/metaphase_duration_delta_from_unmodified.png","Metaphase duration as DIFFERENCE from the unmodified-cohort mean (unmodified = 0); dose-dependent delay (2-sis +8.5, 3-sis +15.3 min)"),
    (4,"group1/triple_prometa_ablation_to_mitosis.png","Triple ablation, PROMETAPHASE group (incl. v2=prometaphase notes): time from mitosis start (NEB) to first ablation vs metaphase duration — NEB-limited (n=4; 37 need NEB)"),
    (5,"group1/single_sisterless_length_congression.png","Single sisterless kinetochore: metaphase duration vs sisterless-chromosome congression time (colour = chromosome length; incl. stayed-polar & at-plate-from-onset)"),
    (6,"group1/pole_to_plate_behavior_vs_duration.png","Sisterless chromosome pole-to-plate behaviour (stayed-at-plate / rejoined / stayed-polar to anaphase) vs metaphase duration, by ablation group"),
    (6,"group1/pole_to_plate_jointime_vs_duration.png","Pole-to-plate rejoin time vs metaphase duration (cells whose sisterless KT rejoined the plate; Spearman)")]:
    next(g for g in GROUPS if g["n"]==_n)["slides"].append({"img":_img,"cap":_cap})

# ===== NEW SLIDES (2026-07-07 feedback pass) =====
# G3 (deck n=3): roundness/area metaphase-onset companions (base + trend-scaled); by-group placed after combined
insert_after(3,"G1_roundness_combined.png","group1/G1_roundness_combined_meta.png",
             "Cell roundness — all groups combined, metaphase onset → anaphase (light=cells, bold=group trend)")
insert_after(3,"G1_roundness_combined_meta.png","group1/G1_roundness_combined_meta_trendscaled.png",
             "Cell roundness — combined, metaphase onset → anaphase; TREND-SCALED companion (axes fit trends; cells may run off-plot)")
insert_after(3,"G1_area_combined.png","group1/G1_area_combined_meta.png",
             "Cell cross-sectional area — all groups combined, metaphase onset → anaphase")
insert_after(3,"G1_area_combined_meta.png","group1/G1_area_combined_meta_trendscaled.png",
             "Cell cross-sectional area — combined, metaphase onset → anaphase; TREND-SCALED companion (axes fit trends; cells may run off-plot)")
insert_after(3,"G1_roundness_split.png","group1/G1_roundness_split_meta.png",
             "Cell roundness by group, metaphase onset → anaphase — trend ends at each group's mean metaphase duration")
insert_after(3,"G1_roundness_split_meta.png","group1/G1_roundness_split_meta_trendscaled.png",
             "Cell roundness by group, metaphase onset → anaphase; TREND-SCALED (each panel fits its own trend; cells may run off-plot)")
insert_after(3,"G1_area_split.png","group1/G1_area_split_meta.png",
             "Cell cross-sectional area by group, metaphase onset → anaphase — trend ends at mean metaphase duration")
insert_after(3,"G1_area_split_meta.png","group1/G1_area_split_meta_trendscaled.png",
             "Cell cross-sectional area by group, metaphase onset → anaphase; TREND-SCALED (each panel fits its own trend; cells may run off-plot)")
# G3: start-rounded-vs-duration stat grid (twin of the metaphase-onset grid)
insert_after(3,"G1_start_rounded_vs_duration.png","group1/G1_start_rounded_vs_duration_statgrid.png",
             "Start-rounded (first outline) vs metaphase duration — stat grid (per-group Spearman ρ, p)")
# G4 (deck n=4): prometaphase companion to the 1-sisterless prophase abl->meta plot
insert_after(4,"G2_abl_to_meta_1sis_prophase.png","group2/G2_abl_to_meta_1sis_prometaphase.png",
             "Ablation→Metaphase vs metaphase duration — single (1-)sisterless on-target PROMETAPHASE cells only (Spearman; stats on plot)")
# G5 (deck n=5): 1-sisterless-only per-cell chromosome-length companions
insert_after(5,"G3_chromo_length_percell.png","group3/G3_chromo_length_percell_1sis.png",
             "Chromosome length (per-cell avg) vs metaphase duration — 1-sisterless group only, per-phase trend lines")
insert_after(5,"G3_chromo_length_percell_bysister.png","group3/G3_chromo_length_percell_bysister_1sis.png",
             "Chromosome length (per-cell avg) vs metaphase duration — 1-sisterless only, trendline per sisterless group")
# G7 (deck n=7): oscillation effective-displacement + intensity-diff + distance companions
insert_after(7,"G4_oscillation.png","group4/G4_oscillation_effective.png",
             "Kinetochore oscillation — EFFECTIVE displacement per 20s interval (net start→end; polar-marked KTs; companion to the per-frame/total version)")
insert_after(7,"G4_oscillation_tracking.png","group4/G4_oscillation_tracking_effective.png",
             "Kinetochore oscillation (TrackMate) — EFFECTIVE displacement per 20s interval, polar vs plate-control (companion to the total-displacement version)")
insert_after(7,"G4_kt_intensity_time_scaled01.png","group4/G4_kt_intensity_diff.png",
             "KT eYFP intensity over time — DIFFERENCE between sisterless-KT and paired plate-KT intensity (per cell, background-subtracted)")
insert_after(7,"G4_plate_distance_time.png","group4/G4_plate_distance_time_metaphase.png",
             "Polar/sisterless-KT distance to metaphase plate over time — x = time from METAPHASE ONSET (companion to the from-ablation version)")
insert_after(7,"G4_plate_distance_time_roundness.png","group4/G4_distance_vs_roundness.png",
             "Polar/sisterless-KT distance to plate vs cell roundness — per KT per frame (alternative view of the roundness-colored distance plot)")
# G10 (deck n=10): scaled-0-1 companion to fluor-vs-duration
insert_after(10,"G4_fluor_vs_duration.png","group4/G4_fluor_vs_duration_scaled01.png",
             "Cell fluorescence (area-normalized) vs metaphase duration — SCALED 0–1 companion; overall trend (stats on plot)")
# G11 (IF/Mad1): Hec1/Mad1 dot-quant, z-stack MIP grid, and 6 Mad1 timelapse/ablation timestrips (end / IF section)
for img,cap in [
    ("group4/G5_hec1_mad1_dot_quant.png","Hec1 / Mad1 IF — per-frame intensity at sisterless vs paired KTs (violin + points)"),
    ("group4/G5_mad1_zstack_mips.png","Mad1 IF — z-stack MIP grid (20260302 FullVolume_17 + 20260313 Hec1halo_640_1); per-channel MIP + fluor overlay"),
    ("group4/G5_mad1_timestrip_20260304_Mad1_timelapse_2_xy1.png","Mad1 timelapse timestrip — 20260304 Mad1_timelapse_2_xy1 (phase+fluor; comment-specified frames)"),
    ("group4/G5_mad1_timestrip_20260304_Mad1_timelapse_2_xy10.png","Mad1 timelapse timestrip — 20260304 Mad1_timelapse_2_xy10 (phase+fluor; comment-specified frames)"),
    ("group4/G5_mad1_timestrip_20260304_Mad1_timelapse_1_xy6.png","Mad1 timelapse timestrip — 20260304 Mad1_timelapse_1_xy6 (phase+fluor; comment-specified frames)"),
    ("group4/G5_mad1_timestrip_20260310_ptk2_eyfp_mad1_14.png","Mad1 timelapse timestrip — 20260310 ptk2_eyfp_mad1_14 (phase+fluor; comment-specified frames)"),
    ("group4/G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52.png","Mad1 ablation timestrip — 20260303 Mad1_Ptk_Eyfpcdc20_ablation_1metaphase_52 (phase+fluor; comment-specified frames)"),
    ("group4/G5_mad1_timestrip_20260303_Mad1_Ptk_Eyfpmad1_ablation_10.png","Mad1 ablation timestrip — 20260303 Mad1_Ptk_Eyfpmad1_ablation_10 (phase+fluor; comment-specified frames)")]:
    next(g for g in GROUPS if g["n"]==11)["slides"].append({"img":img,"cap":cap})
# G11: ALIGNED-CROP variant of each Mad1 ABLATION timestrip (immediately after its status-quo version). Same
# fixed-physical 78µm square footprint (centroid from the fluor-estimated crop, no manual outline) so these
# render at the SAME magnification as every other aligned ablation timestrip.
for _base in ["20260310_ptk2_eyfp_mad1_14",
              "20260303_Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52",
              "20260303_Mad1_Ptk_Eyfpmad1_ablation_10"]:
    insert_after(11, f"G5_mad1_timestrip_{_base}.png",
                 f"group4/G5_mad1_timestrip_{_base}_aligned.png",
                 f"Mad1 ablation timestrip — {_base}, ALIGNED-CROP variant: main ablation + zoom + monitoring tiles share one fixed-physical 78µm square footprint (consistent magnification; zoom column-aligned under the main row)")

# ===== RETIRED plots =====
# user's "no longer needed" list: all trend-scaled companions, the metaphase-onset a.u. fluor plot (CF5),
# and the violin2 Mann-Whitney stat grid (D3, 4-sisterless=2-batch problem).
# 2026-07-09 retirements: G1_statgrid (MWU stat grid no longer needed; NOT the start_rounded_*_statgrid twins,
# which are kept) and G4_cdc20_vs_distance (redundant/incorrect).
RETIRE=["_trendscaled","G4_fluor_over_time_metaphase","G1_violin2_statgrid","G1_statgrid","G4_cdc20_vs_distance"]
retired=[]
for g in GROUPS:
    keep=[]
    for s in g["slides"]:
        if "img" in s and any(r in s["img"] for r in RETIRE): retired.append(s)
        else: keep.append(s)
    g["slides"]=keep

# ---------- PDF renderer ----------
PW,PH=13.333*72,7.5*72
# ---------- data-source footnote (bottom of each figure page; from the plot's source lineage) ----------
# Brief + specific: manual annotations vs automated (TrackMate). Derived from PLOT_SETTINGS source.files so it's
# comprehensive (every page). NOT drawn into the illustrator SVGs — only here at PDF assembly (per user).
import json as _json
_SETTINGS={}
try: _SETTINGS=_json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
except Exception: pass
_SRCLBL={"ABLATION_MASTER.csv":"manual review-slide annotations (event times/cohorts)",
         "kt_points.csv":"manual kinetochore annotations","cell_outlines.csv":"manual cell outlines",
         "SISTERLESS_PLATE_JOIN_TIMES.csv":"manual plate-join annotations"}
_TRACKMATE=("oscillation_tracking","plate_distance_tracking","kt_intensity_diff","kt_intensity_polar_vs_plate",
            "distance_vs_fluor","plate_distance_time","plate_distance_chronological","_tracking")
# TIMESTRIP detection must be PATH/name-specific — NOT broad cohort words like "sisterless"/"off-target"
# (those also match violin/cohort plot filenames, e.g. G1_violin2_sisterless_1234, and would mislabel them).
_TSPATHS=("timestrips2/","frap_timestrips/","_timestrip","G5_IF_mad1hec1")
def data_source(img):
    base=os.path.basename(img)[:-4]
    if any(k in img for k in _TSPATHS):
        return "Data source: microscopy time-lapse — ablation events (frames.json) + manual cell/KT annotations"
    if "zstack_mips" in base or "z_stack" in base:
        return "Data source: microscopy z-stack — max-intensity projections"
    labels=[]
    for f in _SETTINGS.get(base,{}).get("source",{}).get("files",[]):
        lbl=_SRCLBL.get(os.path.basename(f))
        if lbl and lbl not in labels: labels.append(lbl)
    if any(k in base for k in _TRACKMATE) and "automated TrackMate tracking" not in labels:
        labels.append("automated TrackMate tracking")
    # outline-derived plots (roundness/area/cell-fluorescence) are measured inside the MANUAL cell outlines
    if any(k in base for k in ("roundness","area_combined","area_split","G1_area","fluor_over_time","fluor_vs_duration","fluor_")) \
       and "manual cell outlines" not in labels:
        labels.insert(0,"manual cell outlines")
    if not labels: labels=["manual annotations"]
    return "Data source: "+" + ".join(labels)

def render(path, groups, separators=True, retired_section=None):
    c=canvas.Canvas(path,pagesize=(PW,PH))
    def sep(title,color):
        r,gr,b=int(color[0:2],16)/255,int(color[2:4],16)/255,int(color[4:6],16)/255
        c.setFillColorRGB(r,gr,b); c.rect(0,0,PW,PH,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1); c.setFont("Helvetica-Bold",26)
        c.drawCentredString(PW/2,PH/2, title); c.showPage()
    def img_slide(img,cap):
        cp=compact(img)
        if not cp: return
        c.setFillColorRGB(1,1,1); c.rect(0,0,PW,PH,fill=1,stroke=0)
        iw,ih=Image.open(cp).size; ar=iw/ih; maxw,maxh=PW-72,PH-90; dw=maxw; dh=dw/ar
        if dh>maxh: dh=maxh; dw=dh*ar
        c.drawImage(ImageReader(cp),(PW-dw)/2,PH-46-dh,dw,dh,preserveAspectRatio=True,mask='auto')
        c.setFillColorRGB(0,0,0); c.setFont("Helvetica",10); c.drawCentredString(PW/2,22,cap[:180])
        # data-source footnote — very bottom, small grey, clear of the caption + figure (no overlap)
        c.setFillColorRGB(0.45,0.45,0.45); c.setFont("Helvetica",7); c.drawCentredString(PW/2,8,data_source(img)[:150])
        c.showPage()
    def img_slide_paired(base_img,cap,comps):
        """One slide holding the ORIGINAL + its outlier/journal companion(s), so they can be compared
        side-by-side. Falls back to a normal single-figure slide if the companions won't compact."""
        tiles=[]
        for im in [base_img]+list(comps):
            cp=compact(im)
            if cp: tiles.append((im,cp))
        if len(tiles)<=1:
            img_slide(base_img,cap); return
        c.setFillColorRGB(1,1,1); c.rect(0,0,PW,PH,fill=1,stroke=0)
        n=len(tiles); cols=2; rows=(n+cols-1)//cols
        top=PH-30; bot=34; cellw=(PW-72)/cols; cellh=(top-bot)/rows
        for i,(im,cp) in enumerate(tiles):
            rr=i//cols; cc=i%cols
            cell_bottom=top-(rr+1)*cellh; cell_left=36+cc*cellw
            iw,ih=Image.open(cp).size; ar=iw/ih
            maxw=cellw-14; maxh=cellh-20; dw=maxw; dh=dw/ar
            if dh>maxh: dh=maxh; dw=dh*ar
            x=cell_left+(cellw-dw)/2; y=cell_bottom+16+(maxh-dh)/2
            c.drawImage(ImageReader(cp),x,y,dw,dh,preserveAspectRatio=True,mask='auto')
            c.setFillColorRGB(0.30,0.30,0.30); c.setFont("Helvetica-Oblique",8)
            c.drawCentredString(cell_left+cellw/2, cell_bottom+4, companion_label(im))
        c.setFillColorRGB(0,0,0); c.setFont("Helvetica",10); c.drawCentredString(PW/2,20,cap[:180])
        c.setFillColorRGB(0.45,0.45,0.45); c.setFont("Helvetica",7); c.drawCentredString(PW/2,7,data_source(base_img)[:150])
        c.showPage()
    paired_skip=set()  # companion imgs already shown alongside their base (skip their standalone slide, if any)
    for g in groups:
        if separators: sep(f"GROUP {g['n']} · {g['title'].split('·',1)[-1].strip()}", g["color"])
        else:
            # light topical divider title (no "GROUP N")
            sep(g["title"].split("·",1)[-1].strip(), g["color"])
        for s in g["slides"]:
            if "img" not in s: continue
            img=s["img"]
            if img in paired_skip: continue  # already rendered on its base's slide
            comps=companion_pngs(img)
            if comps:
                img_slide_paired(img,s["cap"],comps); paired_skip.update(comps)
            else:
                img_slide(img,s["cap"])
    if retired_section:
        sep("Retired plots","888888")
        for s in retired_section:
            if "img" in s: img_slide(s["img"],s.get("cap",""))
    c.save()
    return path

# ---------- topical reordering (REORDERED pdf ONLY; the as-is pdf stays as-is) ----------
def _find(groups, contains):
    for g in groups:
        for i,s in enumerate(g["slides"]):
            if "img" in s and contains in s["img"]: return g,i
    return None,None
def move_after(groups, move_contains, after_contains):
    """Relocate the slide matching move_contains to immediately follow after_contains (cross-group ok)."""
    gm,im=_find(groups,move_contains)
    if gm is None: return
    s=gm["slides"].pop(im)
    ga,ia=_find(groups,after_contains)
    if ga is None: gm["slides"].append(s)
    else: ga["slides"].insert(ia+1,s)

REORDERED=copy.deepcopy(GROUPS)
# G3: by-group roundness/area immediately follow the combined ones
move_after(REORDERED,"G1_roundness_split.png","G1_area_combined_meta.png")
move_after(REORDERED,"G1_roundness_split_meta.png","G1_roundness_split.png")
move_after(REORDERED,"G1_area_split.png","G1_roundness_split_meta.png")
move_after(REORDERED,"G1_area_split_meta.png","G1_area_split.png")
# G5: KK average-per-cell right after KK-by-phase
move_after(REORDERED,"G2_kk_distance_percell.png","G2_kk_distance_by_phase.png")
# G6: ablation->cell-edge distance right after time-at-pole
move_after(REORDERED,"G3_edge_distance.png","G3_pole_time_vs_duration.png")
# G7: TrackMate oscillation right after the per-frame oscillation slide
move_after(REORDERED,"G4_oscillation_tracking.png","G4_oscillation_effective.png")
move_after(REORDERED,"G4_oscillation_tracking_effective.png","G4_oscillation_tracking.png")
# near-poles + cdc20-over-time grouped with the other polar-KT fluorescence (kt-intensity) plots
move_after(REORDERED,"G4_cdc20_intensity_near_poles.png","G4_kt_intensity_diff.png")
move_after(REORDERED,"G4_cdc20_intensity_chronological.png","G4_cdc20_intensity_near_poles.png")

# 1) AS-IS order (group separators kept), retired plots appended at the very end
render(os.path.join(ROOT,"ablation_figures.pdf"), GROUPS, separators=True, retired_section=retired)
# 2) REORDERED: topical flow, group-number separators replaced by light topical divider titles,
#    same-topic plots made adjacent, retired section at the end.
render(os.path.join(ROOT,"ablation_figures_REORDERED.pdf"), REORDERED, separators=False, retired_section=retired)

# Dump the EXACT reordered figure list (in reordered-PDF order, retired appended) so the .ai LIBRARY builder
# places every figure that's in the reordered PDF, in that order — comprehensive + reordered, always in sync.
import json as _json_m
# EXCLUDE the retired figures from the .ai manifest (user: don't make .ai versions of retired figures). The
# retired plots still appear in the reordered PDF's retired section, just not in the .ai library.
_reordered_figs=[s["img"] for g in REORDERED for s in g["slides"] if "img" in s]
os.makedirs(os.path.join(ROOT,"_ai_relink"),exist_ok=True)
_json_m.dump(_reordered_figs,open(os.path.join(ROOT,"_ai_relink","reordered_manifest.json"),"w"),indent=0)
_json_m.dump([s["img"] for s in retired if "img" in s],open(os.path.join(ROOT,"_ai_relink","retired_figs.json"),"w"),indent=0)
print(f"reordered_manifest.json: {len(_reordered_figs)} figures (retired excluded -> not in .ai)")

import glob
for p in ["ablation_figures.pdf","ablation_figures_REORDERED.pdf"]:
    fp=os.path.join(ROOT,p); print(f"{p}: {os.path.getsize(fp)/1e6:.1f} MB")
print(f"retired plots moved to end: {[s['img'].split('/')[-1] for s in retired]}")

# REDUNDANCY: self-check that every placed plot's chain (script->PNG->cache->PDF->Adobe) is fresh, so a
# code change can never silently fail to reach the end products. Prints STALE links if any remain.
print("\n--- self-checks (freshness + effects + SVG content/overlap) ---")
import subprocess as _sp
for _v in ("verify_freshness.py","verify_effects.py","verify_svg.py","verify_source_lineage.py","verify_consistency.py"):
    try: _sp.run(["python3", os.path.join(ROOT,_v)])
    except Exception as _e: print(f"{_v} skipped:", _e)
