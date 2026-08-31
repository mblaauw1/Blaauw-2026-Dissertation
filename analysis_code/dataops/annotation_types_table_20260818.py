#!/usr/bin/env python3
"""THE ANNOTATION TABLE for the active decks — v2, 2026-08-18.

HER SPEC, in three messages:
  * "a table of all the different types of annotations gathered from the data that is currently being used
     in the active ai files, for what cell types it was gathered on, if it was most often gathered from
     ablation or monitoring movies (or frequently on both), the channel it was most frequently annotated
     and then gathered on (may be different channels)"
  * "legacy annotations do not need to be included ... annotations specific to IFs, MUGs cells do not need
     to be included at this time either"
  * "include on the table how the annotation or measurement was made (a line drawn to measure length? a
     point to mark the location or center? an outline for shape?)" and "how the measurement was used in
     analysis"

FILTERS (all three are hers, and each is counted so the exclusion is visible, not silent):
  LEGACY  rows with no clip tag — the pre-tagging rows whose clip cannot be recovered — are DROPPED.
  IF      any batch matching "IF stained" / "IF dish" is DROPPED.
  MUGs    any batch matching "MUG" is DROPPED.

Outputs, all three from one pass so they cannot disagree:
  ANNOTATION_TYPES_IN_ACTIVE_DECKS.html   <- open, select all, copy, paste into Google Docs (stays an
                                             editable Docs table; it is markup, not a picture)
  ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv    <- for Sheets
  ANNOTATION_TYPES_IN_ACTIVE_DECKS.md     <- for reading on the drive
"""
import csv, io, json, os, re, subprocess, collections, sys, html
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"; A = ROOT + "/annotations/"
OUTDIR = ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818"
DECKS = ["META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
         "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"]
EXCLUDE_BATCH = re.compile(r"IF stained|IF dish|\bIF\b|mug", re.I)

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}
ctype = lambda b: ((MB.get(b) or {}).get("Cell Type") or "unknown").strip() or "unknown"

# ---------------------------------------------------------------- in use on a live deck
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))
placed = set()
for d in DECKS:
    t = subprocess.run(["strings", f"{ROOT}/1_DECKS/{d}"], capture_output=True, text=True).stdout
    placed |= set(re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", t))
# 2026-08-18: `strings` on a compressed .ai does NOT list every linked file — two AB5 excerpts placed on
# META_FIGURES_20260814 were invisible to it, so they were treated as unplaced and got no legend. The
# read-only geometry dumps (_claude_tmp/geom9_*.tsv) list the REAL placedItems, so union them in.
import csv as _csv, glob as _glob, os as _os
for _g in _glob.glob("/Volumes/4 MB/_claude_tmp/geom9_*.tsv"):
    try:
        with open(_g, encoding="utf-8", errors="replace") as _fh:
            for _r in _csv.DictReader(_fh, delimiter="\t"):
                if _r.get("kind") != "PlacedItem":
                    continue
                _lk = (_r.get("linked") or "").strip()
                if _lk:
                    placed.add(_os.path.basename(_lk).rsplit(".", 1)[0])
    except Exception:
        pass

DERIVED = {
    "KT_OUTLINE_TRACKS_20260723.csv":   ["kt_outlines.csv"],
    "KT_LANDMARK_ANALYSIS_20260723.csv":["kt_outlines.csv", "chromo_lines.csv", "meta_plates.csv"],
    "KT_CHROMO_ANALYSIS_20260723.csv":  ["chromo_lines.csv", "kt_outlines.csv", "meta_plates.csv"],
    "KT_SISTER_KK_20260723.csv":        ["kt_outlines.csv"],
    "KT_SISTER_KK_MERGED_20260809.csv": ["kt_outlines.csv", "kt_points.csv"],
    "KT_SISTERS_20260723.csv":          ["kt_outlines.csv"],
    "KT_TENSION_20260723.csv":          ["kt_outlines.csv", "meta_plates.csv"],
    "KT_TENSION_LOADAXIS_20260805.csv": ["kt_outlines.csv", "meta_plates.csv"],
    "KT_LOADING_AXIS_20260805.csv":     ["kt_outlines.csv", "meta_plates.csv"],
    "META_PLATE_NORMALIZED_20260728.csv":["meta_plates.csv"],
    "KT_FLUOR_CYTOSOLNORM_20260728.csv":["kt_outlines.csv", "kt_points.csv"],
    "MAD1_KT_OUTLINE_TRACKS_20260727.csv":["kt_outlines.csv"],
    "G5_hec1_mad1_TRUE_quant.csv":      ["kt_points.csv"],
    "G5_mad1_kt_fluor_measurements.csv":["kt_points.csv"],
    "KT_TRACKS_DRIFTCORR_20260808.csv": ["kt_outlines.csv"],
}
ORDER = ["ABLATION_MASTER.csv", "kt_outlines.csv", "meta_plates.csv", "cell_outlines.csv",
         "chromo_lines.csv", "kt_points.csv", "poles.csv", "CHROMOSOME_MASTER.csv",
         "SISTERLESS_PLATE_JOIN_TIMES.csv", "PREABL_CHROMOSOME_ASSIGNMENT.csv",
         "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv", "lagging_lengths.csv", "KT_TRACKING_MASTER.csv"]

CODE_DIRS = [ROOT + "/ablation_figures_20260625", ROOT + "/ablation_figures_20260625/figures",
             ROOT + "/ablation_plots/code", ROOT + "/dataops"]
_cache = {}
def stores_in_builder(code_name):
    if not code_name: return set()
    if code_name in _cache: return _cache[code_name]
    text = ""
    base = code_name.split("__", 1)[-1]
    for c in [os.path.join(d, n) for d in CODE_DIRS for n in (code_name, base)]:
        if os.path.exists(c):
            try: text = open(c, errors="replace").read(); break
            except OSError: pass
    found = set()
    for m in re.findall(r"annotations/([A-Za-z0-9_]+\.csv)", text):
        for prim in (DERIVED.get(m) or ([m] if m in ORDER else [])):
            found.add(prim)
    _cache[code_name] = found
    return found

uses = collections.defaultdict(set)
for pid in placed:
    e = ps.get(pid)
    if not e: continue
    src = e.get("source") or {}
    files = src.get("files") if isinstance(src, dict) else (src if isinstance(src, list) else [src])
    for f in files or []:
        b = os.path.basename(str(f))
        for prim in (DERIVED.get(b) or ([b] if b in ORDER else [])):
            uses[prim].add(pid)
    for prim in stores_in_builder(e.get("code") or ""):
        uses[prim].add(pid)

# ---------------------------------------------------------------- descriptions (hand-written, verified)
HOW_MADE = {
 "ABLATION_MASTER.csv": "Watched the movie and typed the timestamp of each event into the spreadsheet — no mark is drawn on the image.",
 "kt_outlines.csv": "TRACED OUTLINE — the kinetochore's edge drawn freehand, one closed shape per kinetochore per frame (several shapes when it is fractured; they belong to one kinetochore through her `grp` tag).",
 "meta_plates.csv": "LINE — two clicks across the metaphase plate, marking the plate's long axis on that frame.",
 "cell_outlines.csv": "TRACED OUTLINE — the cell's boundary drawn freehand, one closed shape per frame.",
 "chromo_lines.csv": "LINE — two clicks end-to-end along the chromosome, to measure its length.",
 "kt_points.csv": "POINT — a single click on the centre of the kinetochore (or, for `cytosol_bg`, on empty cytoplasm). The click is refined to the local intensity peak at measurement time; the stored click is never moved.",
 "poles.csv": "POINT — a single click on each spindle pole.",
 "CHROMOSOME_MASTER.csv": "TYPED — congression time and behaviour entered per chromosome in a table while watching the movie.",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "TYPED — the time each sisterless chromosome reaches the plate, entered per chromosome.",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "TYPED + POINTS — which chromosome each ablation attempt targeted, with the pre-ablation kinetochore positions.",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "TYPED — chromosome length paired with what that chromosome did, entered in the pairing tool.",
 "lagging_lengths.csv": "TWO CROSSED LINES — per kinetochore a long axis and a short axis, drawn as a cross; the length is the longer of the two (max caliper extent). 1 cross on a frame = the lagging kinetochore; 2 = longest is lagging, other is the control; 3 = two longest are lagging.",
 "KT_TRACKING_MASTER.csv": "NOT HAND-MADE — automated spot detection and linking (TrackMate in Fiji); listed for completeness.",
}
USED_FOR = {
 "ABLATION_MASTER.csv": "Every duration and every time axis in the paper: metaphase duration, NEB→metaphase, ablation→metaphase, and the alignment point for all trend plots. Also defines the cohorts (on/off target, sisterless number) and is the model's target variable.",
 "kt_outlines.csv": "Per-frame kinetochore shape from the traced polygon — area, perimeter, circularity, solidity, convexity, max/min caliper (Feret) — then tracked over time into: distortion along the spindle axis, fracture (a kinetochore in more than one piece), kinetochore speed and oscillation, and sister k-k distance for untargeted pairs.",
 "meta_plates.csv": "The plate axis and its perpendicular (the plate normal). Everything positional is measured against it: distance of each kinetochore to the plate, congression, plate rotation over time, plate width, and the axis along which kinetochore distortion is measured.",
 "cell_outlines.csv": "Cell area, roundness and centroid displacement across mitosis (the G1 trend family), and — separately — the crop window for every timestrip panel, applied identically to both channels.",
 "chromo_lines.csv": "Chromosome length, used on its own and paired against behaviour: whether length predicts congression, lagging, or how long metaphase lasts.",
 "kt_points.csv": "Two different things. GEOMETRY: k-k distance between the ablation target and its sister before and after ablation, and the positions of polar / lagging / sisterless kinetochores relative to the plate. INTENSITY: eYFP-Cdc20 (or Mad1 / Hec1) signal in a disk at the mark, minus the same-frame `cytosol_bg` mark, reported as fold over background.",
 "poles.csv": "The pole–pole axis and kinetochore-to-pole distance — the spindle's own coordinate frame, used where the plate normal is not the right reference.",
 "CHROMOSOME_MASTER.csv": "Whether and when each chromosome congressed — the outcome variable behind the congression figures, and a feature (held out of the onset model as an outcome) in the metaphase-duration model.",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "Time from ablation to plate arrival per sisterless chromosome; the timing half of the congression analysis.",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "Ties each ablation attempt to a specific chromosome, so a cell's fate can be attributed to the chromosome that was hit; also fixes the per-cell polar count.",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "Length ↔ behaviour pairing per chromosome, as a cross-check on the chromosome-length figures.",
 "lagging_lengths.csv": "Lagging vs control kinetochore LENGTH over time — the only figure that compares the stretched lagging kinetochore against a normal one in the same frame (G4_lagging_vs_control_length_over_time), plus the seeded auto-shape version (G4_lagging_auto_shape_v2), which uses each cross only as a SEED and then measures the real object in the 16-bit stack.",
 "KT_TRACKING_MASTER.csv": "Automated tracks, used only where no manual mark exists; manual always overrides. No live-deck figure is built from them.",
}
# HER INSTRUCTION 2026-08-18: the two explanations that used to sit in a note below the table belong IN
# the table. So (a) every geometry row states in its own cell WHY it has no channel, and (b) the kt_points
# row carries the Hec1 640 -> 488 case where the channel marked on and the channel measured differ.
GATHERED = {
 "ABLATION_MASTER.csv": "typed times — no pixels measured",
 "kt_outlines.csv": "THE SHAPE SHE DREW — no channel applies: an area, perimeter, angle or caliper length is read out of the polygon, not out of pixel values, so it does not depend on which channel was on screen. The same outlines are re-used as regions to read the RAW 16-BIT fluorescence in the intensity figures.",
 "meta_plates.csv": "THE LINE SHE DREW — no channel applies: the plate axis and its normal are geometry, independent of the channel displayed while marking.",
 "cell_outlines.csv": "THE SHAPE SHE DREW — no channel applies: area, roundness and centroid come from the polygon, not from pixel values.",
 "chromo_lines.csv": "THE LINE SHE DREW — no channel applies: length is the distance between her two clicks x the pixel size.",
 "kt_points.csv": "TWO KINDS. Geometry (k-k, positions) comes from the point coordinates and has no channel. Intensity comes from the RAW 16-BIT stack — never the 8-bit movie — of that batch's fluorescence channel. THIS IS THE ONE PLACE THE CHANNEL MARKED ON AND THE CHANNEL MEASURED DIFFER: in the Hec1-Halo + eYFP-Mad1 cells she placed `paired_kt` on the 640 (Cy5) Hec1 frames; each mark is then refined +/-2 px onto the Hec1 peak in that kinetochore's own z-slice and the refined position is used for BOTH channels — Mad1 read from 488, Hec1 from 640, background from her `cytosol_bg` marks in the same slice and same channel, reported as fold over background. Everywhere else the two agree.",
 "poles.csv": "THE POINTS SHE CLICKED — no channel applies: the pole-pole axis and distances are geometry.",
 "CHROMOSOME_MASTER.csv": "typed values", "SISTERLESS_PLATE_JOIN_TIMES.csv": "typed values",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "typed values + point positions",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "typed values",
 "lagging_lengths.csv": "THE LINES SHE DREW — no channel applies for the manual length (longer of the two cross axes); the seeded auto-shape version instead measures the object in the RAW 16-BIT fluorescence stack at her cross.",
 "KT_TRACKING_MASTER.csv": "automated detection on the fluorescence channel",
}
LABEL = {
 "ABLATION_MASTER.csv": "Mitotic event times (NEB, metaphase start, anaphase onset, cytokinesis)",
 "kt_outlines.csv": "Kinetochore outline",
 "meta_plates.csv": "Metaphase plate",
 "cell_outlines.csv": "Cell outline",
 "chromo_lines.csv": "Chromosome length",
 "kt_points.csv": "Kinetochore point marks (target pair before/after ablation, polar, lagging, sisterless, paired, cytosol background)",
 "poles.csv": "Spindle poles",
 "CHROMOSOME_MASTER.csv": "Per-chromosome congression time + behaviour",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "Per-chromosome plate-join time",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "Pre-ablation chromosome assignment",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "Chromosome length ↔ behaviour pairing",
 "lagging_lengths.csv": "Lagging kinetochore length (cross marks: long + short axis)",
 "KT_TRACKING_MASTER.csv": "Automated kinetochore tracks (TrackMate)",
}
TYPED = {"CHROMOSOME_MASTER.csv", "SISTERLESS_PLATE_JOIN_TIMES.csv", "PREABL_CHROMOSOME_ASSIGNMENT.csv",
         "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv", "ABLATION_MASTER.csv"}

def norm_chan(r):
    c = (r.get("channel") or "").strip()
    if not c:
        vf = r.get("video_file") or ""
        c = "fluor" if "Fluor" in vf else ("phase" if "Phase" in vf else "")
    c = c.lower()
    if not c: return ""
    if "phase" in c or "bright" in c: return "phase"
    if c.startswith("640"): return "640 (Cy5)"
    if c.startswith("561"): return "561 (mCherry)"
    if c.startswith("405"): return "405 (DAPI)"
    if "fluor" in c or c.startswith("488"): return "488 (fluorescence)"
    return c

def phrase(counter, kind):
    tot = sum(counter.values())
    if not tot: return "—"
    k, v = max(counter.items(), key=lambda kv: kv[1])
    parts = ", ".join(f"{a} {b}" for a, b in counter.most_common(3))
    if v / tot < 0.65:
        return f"both — {parts}"
    word = {"mon": "monitoring", "abl": "ablation"}.get(k, k)
    return f"{word} ({v} of {tot})" if len(counter) == 1 else f"mostly {word} — {parts}"

# The file a reader should open to see how each annotation was captured and how it becomes a number.
# Capture is the same browser tool for every hand mark; the measurement differs per type.
CODEFILE = {
 "ABLATION_MASTER.csv": "scored in the review deck (range_server.py); durations recomputed by ablation_figures_20260625/lib.py",
 "kt_outlines.csv": "captured: make_outline_html.py + serve_annotation.py · measured: kt_shape_metrics.py (shape), kt_tracks.py (tracking), kt_sisters.py (sister k-k)",
 "meta_plates.csv": "captured: make_annotation_html.py + serve_annotation.py · measured: normalize_meta_plates.py, kt_landmark_analysis.py (plate axis and normal)",
 "cell_outlines.csv": "captured: make_outline_html.py + serve_annotation.py · measured: group1_roundness.py (area/roundness/centroid), group_timestrips.py (crops)",
 "chromo_lines.csv": "captured: make_annotation_html.py + serve_annotation.py · measured: kt_chromo_analysis.py, group3_* builders",
 "kt_points.csv": "captured: make_annotation_html.py + serve_annotation.py · measured: group2_kk.py (k-k), lib.py disk_sum/disk_local_bg + FluorTif (intensity), group4_lagging_shape.py (lagging shape)",
 "poles.csv": "captured: make_annotation_html.py + serve_annotation.py · measured: kt_loading_axis.py, group4_cdc20_poles.py",
 "CHROMOSOME_MASTER.csv": "entered in the pairing tool (pairing_server.py) · read by sisterless_behavior_vs_duration.py, custom_todo0818_model.py",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "entered in the slide panel (serve_annotation.py) · read by sisterless_behavior_vs_duration.py, group3_* congression builders",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "built by dataops/preabl_chromosome_assignment.py from her ablation marks · read by sisterless_behavior_vs_duration.py",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "entered in the pairing tool (pairing_server.py) · read by the chromosome-length builders",
 "lagging_lengths.csv": "captured: make_annotation_html.py + serve_annotation.py · measured: lagging_length_over_time.py (manual crosses), lagging_auto_shape_v2.py (seeded auto shape)",
 "KT_TRACKING_MASTER.csv": "TrackMate (Fiji) via kt_tracking/code/kt_record.py · read by group4_tracking_dist.py",
}

rows_out, dropped, untagged = [], collections.Counter(), collections.Counter()
for store in ORDER:
    figs = uses.get(store, set())
    if store == "ABLATION_MASTER.csv":
        rows = [{"batch": b, "phase": "", "channel": "", "video_file": ""} for b, r in MB.items()
                if any((r.get(c) or "").strip() for c in
                       ("NEB Time (s)", "Metaphase Start (s)", "Anaphase Onset (s)", "Cytokinesis Onset (s)"))]
    else:
        rows = rd(A + store)
    keep = []
    for r in rows:
        b = (r.get("batch") or "").strip()
        if not b: continue
        if EXCLUDE_BATCH.search(b): dropped[store + " :: IF/MUGs cell"] += 1; continue
        # 2026-08-18, HER CORRECTION: dropping the untagged rows made the counts "much too small" —
        # it removed 2,554 of the 2,658 `sisterless` marks and 3,856 of the 4,490 plate lines, which are
        # real annotations that still feed figures. They are COUNTED here; what they cannot supply is the
        # clip, so the clip/channel columns are computed over the rows that carry a tag and say how many
        # did not. Only the IF and MUGs cells she asked to leave out are actually dropped.
        if store not in TYPED and store != "KT_TRACKING_MASTER.csv" and not (r.get("phase") or "").strip():
            untagged[store] += 1
        keep.append(r)
    if not keep: continue
    batches = collections.Counter((r.get("batch") or "").strip() for r in keep)
    ct = collections.Counter()
    for b in batches: ct[ctype(b)] += 1
    clip = collections.Counter((r.get("phase") or "").strip() for r in keep if (r.get("phase") or "").strip())
    ch = collections.Counter(c for c in (norm_chan(r) for r in keep) if c)
    if store in TYPED:
        clip_word = ("typed while watching the monitoring clip" if store != "ABLATION_MASTER.csv"
                     else "monitoring clip (NEB → cytokinesis)")
        chan_word = "n/a — typed, not marked on a frame"
    else:
        clip_word = phrase(clip, "clip")
        chan_word = phrase(ch, "channel")
        _ut = untagged.get(store, 0)
        if _ut:
            clip_word += f"; {_ut} older marks carry no clip tag"
    rows_out.append(dict(
        annotation=LABEL.get(store, store),
        how_made=HOW_MADE.get(store, ""),
        cell_types="; ".join(f"{k} ({v})" for k, v in ct.most_common()),
        clip=clip_word, channel_annotated=chan_word,
        channel_gathered=GATHERED.get(store, ""),
        code_file=CODEFILE.get(store, ""),
        used_for=USED_FOR.get(store, ""),
        live_deck_figures=len(figs), cells=len(batches), marks=len(keep), store=store))

# Types with no live-deck figure are NOT part of the table she asked for ("types ... currently being used
# in the active ai files"), but dropping them silently would hide that they exist -- they go in a note.
not_in_use = [r for r in rows_out if r["live_deck_figures"] == 0]
rows_out = [r for r in rows_out if r["live_deck_figures"] > 0]
rows_out.sort(key=lambda r: (-r["live_deck_figures"], -r["marks"]))

# ---------------------------------------------------------------- kt_points, broken out by label
LABEL_USE = {
 "pre_abl": "one half of the ablation target pair, marked before the shot",
 "pre_abl_pair": "the other half of the target pair before the shot — the two give k-k distance pre-ablation",
 "post_abl": "the ablated kinetochore's position after the shot",
 "post_abl_pair": "its sister after the shot — the two give k-k distance post-ablation",
 "polar": "a kinetochore held near the pole; position vs the plate, and its eYFP-Cdc20 intensity",
 "lagging": "a kinetochore lagging in anaphase; position and intensity",
 "sisterless": "the kinetochore left without a sister; position and intensity over time",
 "paired_kt": "an untargeted, normally-attached pair — the internal control for k-k and intensity",
 "cytosol_bg": "empty cytoplasm on the same frame; the background subtracted from every intensity",
}
kp = []
for r in rd(A + "kt_points.csv"):
    b = (r.get("batch") or "").strip()
    if not b or EXCLUDE_BATCH.search(b): continue
    kp.append(r)          # untagged rows are COUNTED (her correction); they just cannot report a clip
by = collections.defaultdict(lambda: {"clip": collections.Counter(), "ch": collections.Counter(),
                                      "cells": set(), "untagged": 0})
for r in kp:
    lab = (r.get("label") or "").strip() or "(unlabelled)"
    d = by[lab]
    _ph = (r.get("phase") or "").strip()
    if _ph: d["clip"][_ph] += 1
    else:   d["untagged"] = d.get("untagged", 0) + 1
    c = norm_chan(r)
    if c: d["ch"][c] += 1
    d["cells"].add((r.get("batch") or "").strip())
label_rows = []
for lab, d in sorted(by.items(), key=lambda kv: -sum(kv[1]["clip"].values())):
    n = sum(d["clip"].values()) + d.get("untagged", 0)
    if n < 10: continue
    ct = collections.Counter(ctype(b) for b in d["cells"])
    label_rows.append(dict(label=lab, marks=n, cells=len(d["cells"]),
                           cell_types="; ".join(f"{k} ({v})" for k, v in ct.most_common()),
                           clip=(phrase(d["clip"], "clip") +
                                 (f"; {d['untagged']} older marks carry no clip tag" if d.get("untagged") else "")),
                           channel=phrase(d["ch"], "channel"),
                           used_for=LABEL_USE.get(lab, "")))

COLS = [("annotation", "Annotation"), ("how_made", "How it was made"),
        ("cell_types", "Cell types (cells)"), ("clip", "Ablation or monitoring movie"),
        ("channel_annotated", "Channel it was annotated on"),
        ("channel_gathered", "What the measurement is gathered from"),
        ("code_file", "Code that captures it / turns it into a number"),
        ("used_for", "How it is used in the analysis"),
        ("live_deck_figures", "Figures on live decks"), ("cells", "Cells"), ("marks", "Marks")]

with open(OUTDIR + "/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow([c[1] for c in COLS])
    for r in rows_out: w.writerow([r[c[0]] for c in COLS])

def td(x): return html.escape(str(x)).replace("→", "&rarr;")
H = ["<!doctype html><html><head><meta charset='utf-8'><title>Annotation types in the active decks</title>",
     "<style>body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;margin:24px}",
     "table{border-collapse:collapse;width:100%}",
     "th,td{border:1px solid #999;padding:6px 8px;vertical-align:top;text-align:left}",
     "th{background:#eee;font-weight:bold}", "td.num{text-align:right}", "caption{text-align:left;padding-bottom:8px}",
     "</style></head><body>",
     "<h2>Annotations feeding the active Illustrator files</h2>",
     "<p>Built 2026-08-18 from the annotation stores. Legacy (untagged) rows, IF slides and MUGs cells are excluded. "
     "&ldquo;Annotated on&rdquo; is the frame she was looking at; &ldquo;gathered from&rdquo; is what the number is "
     "read out of &mdash; for a geometry mark that is the shape itself, which has no channel.</p>",
     "<table><thead><tr>" + "".join(f"<th>{td(c[1])}</th>" for c in COLS) + "</tr></thead><tbody>"]
for r in rows_out:
    H.append("<tr>" + "".join(
        f"<td class='num'>{td(r[c[0]])}</td>" if c[0] in ("live_deck_figures", "cells", "marks")
        else f"<td>{td(r[c[0]])}</td>" for c in COLS) + "</tr>")
H.append("</tbody></table>")

LCOLS = [("label", "Point mark"), ("used_for", "What it marks / what it is for"),
         ("cell_types", "Cell types (cells)"), ("clip", "Ablation or monitoring movie"),
         ("channel", "Channel annotated on"), ("cells", "Cells"), ("marks", "Marks")]
H.append("<h3>The kinetochore point marks, by label</h3>")
H.append("<p>The clip depends on which mark it is, so the single row above would mislead on its own: the marks "
         "about the ablation itself are made on the ablation movie, and the marks about what happens afterwards "
         "on the monitoring movie.</p>")
H.append("<table><thead><tr>" + "".join(f"<th>{td(c[1])}</th>" for c in LCOLS) + "</tr></thead><tbody>")
for r in label_rows:
    H.append("<tr>" + "".join(
        f"<td class='num'>{td(r[c[0]])}</td>" if c[0] in ("cells", "marks") else f"<td>{td(r[c[0]])}</td>"
        for c in LCOLS) + "</tr>")
H.append("</tbody></table>")
H.append("<h3>One thing that needs a sentence of its own</h3>")
H.append("<!-- moved into the table cells on her instruction, 2026-08-18 -->\n" + "<p style='display:none'><b>Where the channel annotated on and the channel gathered from differ.</b> The "
         "<i>paired_kt</i> marks in the Hec1-Halo + eYFP-Mad1 cells were placed on the <b>640 (Cy5) Hec1</b> "
         "frames. The quantification then refines each mark by &plusmn;2&nbsp;px onto the Hec1 peak in that "
         "kinetochore&rsquo;s own z-slice and uses that refined position for <b>both</b> channels &mdash; Mad1 "
         "read from 488, Hec1 from 640, background from her <i>cytosol_bg</i> marks in the same slice and the "
         "same channel, reported as fold over background. Everywhere else in this table the channel she marked "
         "on and the channel the number comes from are the same.</p>")
H.append("<p><b>Lagging kinetochore length is measured three different ways, all from her marks.</b> "
         "(1) the <i>cross marks</i> in this table &mdash; a long and a short axis drawn per kinetochore, which "
         "give the lagging-vs-control comparison; (2) her <i>lagging</i> point marks, where the bright object at "
         "the mark is segmented at half-maximum in the 16-bit stack and its major axis reported "
         "(<i>G4_lagging_shape</i>, <i>G4_lagging_position</i>); and (3) her <i>traced kinetochore outlines</i>, "
         "whose maximum caliper (Feret) extent is the stretch measure behind the shape, strain and fracture "
         "figures. They answer slightly different questions and are deliberately not merged.</p>")
H.append("<p style='display:none'><b>Why a geometry mark has no &ldquo;gathered from&rdquo; channel.</b> A length, an area, an angle "
         "or a distance is read out of the shape she drew, not out of pixel values, so it does not depend on "
         "which channel was displayed when she drew it. Only intensity measurements have a channel, and those "
         "are always read from the raw 16-bit stack, never from the 8-bit movie.</p>")
if not_in_use:
    H.append("<p style='color:#555'><b>Annotated but not feeding any figure on a live deck, so not in the table:</b> " +
             "; ".join(f"{td(r['annotation'])} ({r['marks']} marks over {r['cells']} cells)" for r in not_in_use) +
             ".</p>")
# WHERE the dropped legacy rows sit, so the exclusion cannot quietly shrink a mark type without saying so
legacy_by_label = collections.Counter()
for r in rd(A + "kt_points.csv"):
    b = (r.get("batch") or "").strip()
    if b and not EXCLUDE_BATCH.search(b) and not (r.get("phase") or "").strip():
        legacy_by_label[(r.get("label") or "").strip() or "(unlabelled)"] += 1
legacy_cells_plate = len({(r.get("batch") or "").strip() for r in rd(A + "meta_plates.csv")
                          if not (r.get("phase") or "").strip()})
H.append("<p style='color:#555'>Excluded from the counts: " +
         "; ".join(f"{k} &mdash; {v} rows" for k, v in dropped.most_common()) + ". "
         "The dropped kinetochore points are mostly <i>" +
         ", ".join(f"{k} ({v})" for k, v in legacy_by_label.most_common(3)) +
         "</i>, and the dropped plate lines cover " + str(legacy_cells_plate) +
         " cells &mdash; so those two rows above count fewer cells than the stores actually hold. The marks "
         "themselves are real and still feed their figures; they simply predate the clip tag, so which movie "
         "they were drawn on can no longer be recovered.</p></body></html>")
open(OUTDIR + "/ANNOTATION_TYPES_IN_ACTIVE_DECKS.html", "w", encoding="utf-8").write("\n".join(H))

md = ["# Annotations feeding the active Illustrator files",
      "*Built 2026-08-18 by `dataops/annotation_types_table_20260818.py`. Legacy (untagged) rows, IF slides and",
      "MUGs cells excluded. Paste-ready copy: `ANNOTATION_TYPES_IN_ACTIVE_DECKS.html`.*", "",
      "| " + " | ".join(c[1] for c in COLS) + " |",
      "|" + "|".join("---" for _ in COLS) + "|"]
for r in rows_out:
    md.append("| " + " | ".join(str(r[c[0]]).replace("|", "/") for c in COLS) + " |")
md += ["", "## The kinetochore point marks, by label", "",
       "| " + " | ".join(c[1] for c in LCOLS) + " |", "|" + "|".join("---" for _ in LCOLS) + "|"]
for r in label_rows:
    md.append("| " + " | ".join(str(r[c[0]]).replace("|", "/") for c in LCOLS) + " |")
md += ["", "## One thing that needs a sentence of its own", "",
       "**Lagging kinetochore length is measured three different ways, all from her marks.** (1) the *cross "
       "marks* in this table — a long and a short axis per kinetochore — which give the lagging-vs-control "
       "comparison; (2) her `lagging` point marks, where the object at the mark is segmented at half-maximum in "
       "the 16-bit stack and its major axis reported (`G4_lagging_shape`, `G4_lagging_position`); and (3) her "
       "traced kinetochore outlines, whose maximum caliper (Feret) extent is the stretch measure behind the "
       "shape, strain and fracture figures. They answer slightly different questions and are not merged.", "",
       "**Where the channel annotated on and the channel gathered from differ.** The `paired_kt` marks in the "
       "Hec1-Halo + eYFP-Mad1 cells were placed on the **640 (Cy5) Hec1** frames. The quantification refines each "
       "mark by ±2 px onto the Hec1 peak in that kinetochore's own z-slice and uses that refined position for "
       "**both** channels — Mad1 from 488, Hec1 from 640, background from her `cytosol_bg` marks in the same slice "
       "and channel, as fold over background. Everywhere else the mark channel and the measurement channel agree.",
       "",
       "**Why a geometry mark has no gathered-from channel.** A length, area, angle or distance comes out of the "
       "shape she drew, not out of pixel values, so it does not depend on which channel was on screen. Only "
       "intensity measurements have a channel, and those always come from the raw 16-bit stack."]
if not_in_use:
    md += ["", "**Annotated but not feeding any figure on a live deck:** " +
           "; ".join(f"{r['annotation']} ({r['marks']} marks over {r['cells']} cells)" for r in not_in_use) + "."]
md += ["", "**Excluded from the counts:** " + "; ".join(f"{k} — {v} rows" for k, v in dropped.most_common()) + ". "
       "The dropped kinetochore points are mostly " +
       ", ".join(f"`{k}` ({v})" for k, v in legacy_by_label.most_common(3)) +
       f", and the dropped plate lines cover {legacy_cells_plate} cells — so those two rows count fewer cells "
       "than the stores actually hold. The marks are real and still feed their figures; they simply predate the "
       "clip tag, so which movie they were drawn on can no longer be recovered."]
open(OUTDIR + "/ANNOTATION_TYPES_IN_ACTIVE_DECKS.md", "w", encoding="utf-8").write("\n".join(md) + "\n")

print(f"{'annotation':46s} {'figs':>4} {'cells':>5} {'marks':>6}  clip / channel")
for r in rows_out:
    print(f"{r['annotation'][:45]:46s} {r['live_deck_figures']:4d} {r['cells']:5d} {r['marks']:6d}  "
          f"{r['clip'][:32]:34s} {r['channel_annotated'][:34]}")
print("\nkt_points by label:")
for r in label_rows:
    print(f"   {r['label']:14s} {r['marks']:5d} marks {r['cells']:4d} cells  {r['clip'][:30]:32s} {r['channel'][:30]}")
if not_in_use:
    print("\nnot feeding any live-deck figure (kept out of the table):")
    for r in not_in_use: print(f"   {r['annotation']}  ({r['marks']} marks, {r['cells']} cells)")
print("\nexcluded:")
for k, v in dropped.most_common(): print(f"   {k:52s} {v} rows")
print(f"\n[done] -> {OUTDIR}/ANNOTATION_TYPES_IN_ACTIVE_DECKS.{{html,csv,md}}")
