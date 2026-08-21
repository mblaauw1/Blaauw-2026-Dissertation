"""custom_vet_feature_blocks_20260722.py — sort the 226 UNVETTED warehouse blocks (user 2026-07-22).

WHY
  The structured model admits only 69 of 432 blocks. Only 111 of the 363 exclusions are real leakage; the
  other 226 were dropped because their source figure has no PLOT_SETTINGS entry, so there was nothing to
  vet them against. "Unverifiable" is not the same as "bad", and that gap is currently the single biggest
  restriction on the model.

WHAT THIS DOES
  Classifies every unvetted block BY DEFINITION — from what the column demonstrably is — and writes an
  AUDITABLE table she can override. It does NOT guess: a block whose meaning cannot be established from its
  column name is written as `unknown` and stays EXCLUDED. Filling that gap with an inference is exactly the
  failure that retired four figures.

DECISIONS AND THEIR GROUNDS
  acquisition   roi_x/roi_y/roi_w/roi_h/scalebar_um/pixel_um/render_*  -> how the CROP was drawn and how the
                movie was rendered. Properties of the figure, not of the cell. EXCLUDE.
  clock         frame_idx / t_sec / time / x / y                       -> index or axis, not a measurement.
  raw_pixel     abl_x_px / abl_y_px and other *_px coordinates         -> a position in IMAGE space. Where the
                cell happened to sit in the field of view is not biology; the same ablation at a different
                stage position gives a different number. The BIOLOGICAL version of this (distance to the
                plate, position along the plate normal, distance to pole) is rebuilt properly from the
                primary annotation stores instead. EXCLUDE here, recovered there.
  outcome       congression / behaviour / reached / polar / lagging / duration / score  -> the target.
  predictor     intensity, fluorescence, area, roundness, length, distance, angle, count of sisterless etc.
                -> measurable without knowing how the cell turned out. ADMIT.
  unknown       anything else -> EXCLUDED, flagged for her.

OUTPUT
  /Volumes/4 MB/ablation_plots/MODEL_FEATURE_VETTING_20260722.csv
  Columns: source, block, column, n_batches, decision, ground, admit
  Edit `admit` (yes/no) to override; the model reads this file, so her edit wins over my classification.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import json, re, csv, os
from collections import defaultdict

FEATJSON = "/Volumes/4 MB/_scratch/batch_features.json"
OUT = "/Volumes/4 MB/ablation_plots/MODEL_FEATURE_VETTING_20260722.csv"
PS = "/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"

LEAK = re.compile(r"metaphase|meta.?dur|meta.?start|duration|anaphase|\bana\b|ana_|_ana|mitotic|cytokin|"
                  r"neb.?to.?meta|abl.?to.?meta|meta.?min|dur_min", re.I)
OUTCOME = re.compile(r"congress|reach|frac_|fraction|\bscore\b|_score|exhaust|behaviou?r|outcome|"
                     r"\bpolar\b|lagging|noncong|at_plate|plate_join|rejoin|minutes|\bmins?\b|elapsed|"
                     r"time_to|to_ana|to_meta|survival|censored", re.I)

ACQUISITION = re.compile(r"^(roi_[xywh]|scalebar_um|pixel_um|pixel_size_um|render_|dpi|fig_|panel_|"
                         r"crop_[xywh]|w|h|width|height|[xy]_(min|max|lim|lo|hi))$", re.I)
CLOCK = re.compile(r"^(t_sec|t|time|frame_idx|frame|timepoint|x|y|index|idx)$", re.I)
RAW_PIXEL = re.compile(r"_px$|^(abl_[xy])$", re.I)
PREDICTOR = re.compile(r"intens|fluor|bgsub|au$|_au|area|round|circular|solid|aspect|perimeter|"
                       r"length|len_um|dist|distance|kk|angle|speed|velocit|n_sisterless|n_pairs|"
                       r"n_kt|n_chrom|edge|_um$|count|brightness|signal|ratio|norm|sum$|mean$|value$", re.I)

# A `*_zoom` figure is the SAME figure with tighter axes — its recorded column carries the parent's meaning.
# `zoom_outlier_removed` is that figure's plotted value with outliers dropped, so it inherits whatever the
# parent plots. Resolving it by inheritance is definitional, not a guess: if the parent plots the target,
# so does the zoom.
ZOOM_SUFFIX = re.compile(r"(_journal)?_zoom$", re.I)
_PS_CACHE = None


def parent_source(src):
    """'G1_violin2_no_dc_offtarget_journal_zoom' -> 'G1_violin2_no_dc_offtarget'"""
    p = ZOOM_SUFFIX.sub("", src)
    return p if p != src else None


# ---------------------------------------------------------------- RESOLVED BY INSPECTION (2026-07-22)
# The first pass left 105 blocks as `unknown` on column name alone. Each was then resolved by reading the
# SOURCE CSV's other columns and its value distribution — evidence, not inference. Recorded here so the
# decision is auditable and so nothing has to be re-guessed.
RESOLVED = {
    # 0/1 mask flagging which rows the ZOOMED variant of a figure dropped from its axis. A rendering
    # decision about the plot, not a measured quantity. (Sits beside the real value column; values only 0/1.)
    # This corrects the first pass, which tried to inherit the parent figure's meaning — wrong: the column
    # is a mask, not the plotted value.
    "zoom_outlier_removed": ("acquisition", "0/1 mask of rows dropped from the zoomed axis — a render flag", "no"),
    # index of WHICH ablation / FRAP event within the batch (0,1,2,5...) — an ordinal index, not a measurement
    "abl_seq":   ("clock", "ordinal index of the ablation event within the batch", "no"),
    "frap_seq":  ("clock", "ordinal index of the FRAP event within the batch", "no"),
    "seq":       ("clock", "ordinal event index within the batch", "no"),
    # plane / file position inside the source TIFF
    "flash_tif_pos": ("acquisition", "plane index inside the source TIFF", "no"),
    "tif_pos":       ("acquisition", "plane index inside the source TIFF", "no"),
    "abl_pre_frame": ("acquisition", "frame index of the pre-ablation reference", "no"),
    # descriptors of the ROW, not of the cell
    "is_pre_ablation": ("clock", "row descriptor: is this row before the ablation", "no"),
    "is_hole_marker":  ("acquisition", "plotting marker flag", "no"),
    "v2note":          ("acquisition", "annotation note flag on the figure", "no"),
    "channel_labels":  ("acquisition", "channel name text", "no"),
    "off_scale":       ("acquisition", "saturation QC flag on the trace, not a measurement", "no"),
    "rel_time_s":      ("clock", "time relative to the ablation — a clock", "no"),
    # REAL MEASUREMENTS — intensities, ratios, displacements, counts, angles
    "pre_over_cytosol":  ("predictor", "kinetochore intensity normalised to cytosol, before ablation", "yes"),
    "post_over_cytosol": ("predictor", "kinetochore intensity normalised to cytosol, after ablation", "yes"),
    "targeted_over_sister_start1": ("predictor", "targeted/sister intensity ratio, start-normalised", "yes"),
    "plate_I": ("predictor", "eYFP-Cdc20 intensity on the plate-control kinetochore", "yes"),
    "polar_I": ("predictor", "eYFP-Cdc20 intensity on the polar kinetochore", "yes"),
    "disp_um_per_20s": ("predictor", "kinetochore displacement per 20 s — oscillation magnitude", "yes"),
    "degrees_turned_net": ("predictor", "net metaphase-plate rotation in degrees", "yes"),
    "n_plate_spots": ("predictor", "number of TrackMate plate kinetochore spots", "yes"),
    "kt_n_tracks":   ("predictor", "number of tracked kinetochores in the cell", "yes"),
    # group descriptors: real initial conditions, but duplicates of n_sis already in the model
    "group":      ("predictor", "sisterless-KT count (duplicate of n_sis)", "yes"),
    "sisterless": ("predictor", "sisterless-KT count (duplicate of n_sis)", "yes"),
    # RESOLVED 2026-07-22 (second pass). These were held back because the rebuild of
    # G4_sisterless_cdc20_vs_bleaching "failed verification" against the RETIRED original. That verdict was
    # wrong, and the retired original is the broken artefact:
    #   * the retired y-values run to -3157 %/min, with 25 of 34 beyond +/-100 %/min and 8 beyond +/-1000.
    #     A kinetochore cannot lose >100% of its intensity per minute — that is a slope divided by a
    #     near-zero background-subtracted baseline, not a rate.
    #   * the rebuild's y-values are all within +/-20.3 %/min. Physically possible.
    #   * the x-axis reproduces the original EXACTLY (max difference 0.0046 across all 34 batches).
    #   * the failing rho (-0.010 / -0.022) was computed over 35 rows against the original's 34. On the
    #     matched 34 the rebuild gives rho -0.135 vs the recorded -0.143. It reproduces the statistic.
    #     One extra batch (20260420 ptk2 eyfp cdc20 1 ablation_13, kt_cdc20 +22.3) moves rho -0.135 -> -0.022.
    # Both columns are real measurements. ADMITTED. (The FIGURE still needs rebuilding to her 2026-07-22
    # spec — paired in-outline background, TrackMate for the plate-KT LOCATION only, z-defocus screen — but
    # that is a spec upgrade, not a correctness problem with these two quantities.)
    "cell_bleach_pct_per_min": ("predictor", "whole-cell fluorescence bleaching rate, %/min", "yes"),
    "kt_cdc20_pct_per_min":    ("predictor", "kinetochore eYFP-Cdc20 loss rate, %/min", "yes"),
}

# master columns judged by what they are. Acquisition/admin bookkeeping vs real initial conditions.
# `*_ids` are COMMA-SEPARATED ID LISTS. Harvested numerically they become "the first id" or "how many ids",
# i.e. annotation order and annotation effort — which track acquisition date, not biology. The structured
# model was selecting `master:preabl_chromosome_ids` in 195 of 200 folds on exactly that artefact.
MASTER_ACQ = re.compile(r"^(#\s*(Files|Marker Frames|Cropped Frames)|Crop |Dropped|Date|Processing Time|"
                        r"%\s*Post-Ablation|Time Jitter|Total Frames|Pixel Size|Time Interval|"
                        r"Log Ablation Events|$)|_ids$", re.I)
# Intervals that END at metaphase onset are bounded by the event that starts the target interval, and NEB
# is the event the whole clock is built from. Both are event times, not measurements of the cell.
MASTER_LEAK = re.compile(r"->\s*Meta|NEB Time", re.I)
MASTER_PRED = re.compile(r"^(#\s*Sisterless KTs|#\s*Unique Targets|Ablation Span|First Ablation|"
                         r"Last Ablation|1st Event Delta)", re.I)


def classify(block, ps=frozenset()):
    src, col = (block.split(":", 1) + [""])[:2]
    if LEAK.search(block) or OUTCOME.search(block):
        return "outcome", "names the target or an outcome of the experiment", "no"
    if col in RESOLVED:
        return RESOLVED[col]
    if src == "master":
        if MASTER_LEAK.search(col):
            return "outcome", "event time / interval ending at metaphase onset", "no"
        if col.strip() == "" or col.strip().endswith("_ids"):
            return "acquisition", "comma-separated ID list — encodes annotation order, not biology", "no"
        if MASTER_PRED.search(col):
            return "predictor", "initial condition, knowable at ablation time", "yes"
        if MASTER_ACQ.search(col):
            return "acquisition", "acquisition/admin bookkeeping, not a property of the cell", "no"
    # inherit from the un-zoomed parent figure before anything else
    par = parent_source(src)
    if par:
        txt = ""
        if par in ps:
            v = ps[par] if isinstance(ps, dict) else {}
            s = (v.get("settings") or {}) if isinstance(v, dict) else {}
            txt = " ".join(str(t) for t in (v.get("caption", ""), s.get("metric", ""))) if isinstance(v, dict) else ""
        if txt and (LEAK.search(txt) or OUTCOME.search(txt)):
            return "outcome", f"zoom variant of '{par}', which plots the target", "no"
        if re.search(r"zoom_outlier_removed|value", col, re.I) and txt:
            return "predictor", f"zoom variant of '{par}' ({txt.strip()[:60]})", "yes"
    if ACQUISITION.search(col):
        return "acquisition", "crop/render metadata — a property of the figure, not the cell", "no"
    if CLOCK.search(col):
        return "clock", "index or plot axis, not a measurement", "no"
    if RAW_PIXEL.search(col):
        return "raw_pixel", "position in image space; biological version rebuilt from primary stores", "no"
    if PREDICTOR.search(col):
        return "predictor", "measurable without knowing the cell's outcome", "yes"
    return "unknown", "meaning not establishable from the column name — needs a human", "no"


def main():
    raw = json.load(open(FEATJSON))
    psd = json.load(open(PS))
    ps = set(psd)
    blocks = defaultdict(set)
    for b, d in raw.items():
        for f in d:
            blk = f.rsplit("|", 1)[0] if "|" in f else f
            blocks[blk].add(b)

    rows = []
    for blk, bs in sorted(blocks.items()):
        src = blk.split(":", 1)[0]
        col = blk.split(":", 1)[1] if ":" in blk else ""
        vetted = (src in ps) or (src == "master")
        dec, ground, admit = classify(blk, psd)
        rows.append({"source": src, "block": blk, "column": col, "n_batches": len(bs),
                     "had_plot_settings": "yes" if vetted else "no",
                     "decision": dec, "ground": ground, "admit": admit})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source", "block", "column", "n_batches", "had_plot_settings",
                                           "decision", "ground", "admit"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    tot = defaultdict(int); newly = defaultdict(int)
    for r in rows:
        tot[r["decision"]] += 1
        if r["had_plot_settings"] == "no":
            newly[r["decision"]] += 1
    print(f"{len(rows)} blocks vetted -> {OUT}\n")
    print(f"  {'decision':14s} {'all blocks':>11s} {'of which previously UNVETTED':>30s}")
    for k in sorted(tot, key=lambda k: -tot[k]):
        print(f"  {k:14s} {tot[k]:11d} {newly.get(k,0):30d}")
    gained = sum(1 for r in rows if r["admit"] == "yes" and r["had_plot_settings"] == "no")
    print(f"\n  blocks RECOVERED for the model (were unvetted, now admitted on grounds): {gained}")
    print(f"  blocks still excluded as 'unknown' (need her eyes): "
          f"{sum(1 for r in rows if r['decision']=='unknown')}")
    ex = [r["block"] for r in rows if r["decision"] == "unknown"][:15]
    for b in ex:
        print(f"      {b}")


if __name__ == "__main__":
    main()
