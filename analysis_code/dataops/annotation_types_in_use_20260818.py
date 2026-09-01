#!/usr/bin/env python3
# ⚠ SUPERSEDED 2026-08-18 by dataops/annotation_types_table_20260818.py, which applies her filters
#   (no legacy/untagged rows, no IF or MUGs cells), adds the "how it was made" and "how it is used in
#   the analysis" columns, and writes the paste-ready HTML. Kept only because it is the version that
#   produced the first pass; do not run it expecting the current table.
"""WHICH ANNOTATION TYPES FEED THE ACTIVE DECKS — and, for each, on what and where it was gathered.

HER ASK (2026-08-18): "a table of all the different types of annotations gathered from the data that is
currently being used in the active ai files, for what cell types it was gathered on, if it was most often
gathered from ablation or monitoring movies (or frequently on both), the channel it was most frequently
annotated and then gathered on (may be different channels)."

Two different questions per row, and they are kept apart deliberately:
  * ANNOTATED ON  — the clip and channel of the frame she was looking at when she made the mark.
    Measured from the store's own `phase` (abl/mon) and `channel` / `video_file` columns.
  * GATHERED ON   — the pixels the MEASUREMENT is finally read from.  For a geometry mark (a line, an
    outline, a point position) there is no channel at all: the number is a distance or an area, so the
    answer is "geometry — channel-independent".  For an intensity measurement the answer is the raw
    16-bit stack of that batch's fluorescence channel, which is NOT always the channel she marked on.

"In use on the active decks" is resolved through PLOT_SETTINGS `source`, including one hop through the
DERIVED stores (KT_OUTLINE_TRACKS, KT_LANDMARK_ANALYSIS, KT_SISTER_KK, ... all trace back to her marks).
"""
import csv, io, json, os, re, subprocess, collections, sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"; A = ROOT + "/annotations/"
OUTDIR = ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818"
DECKS = ["META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
         "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"]

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}
ctype = lambda b: ((MB.get(b) or {}).get("Cell Type") or "unknown").strip() or "unknown"

# ---------------------------------------------------------------- what is placed, and what it derives from
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))
placed = set()
for d in DECKS:
    t = subprocess.run(["strings", f"{ROOT}/1_DECKS/{d}"], capture_output=True, text=True).stdout
    placed |= set(re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", t))

# every DERIVED store, and the marks it is computed from (read out of the builders, not assumed)
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
    "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv":["CHROMO_LENGTH_BEHAVIOR_PAIRING.csv"],
    "KT_TRACKS_DRIFTCORR_20260808.csv": ["kt_outlines.csv"],
}
PRIMARY = ["kt_points.csv", "kt_outlines.csv", "cell_outlines.csv", "meta_plates.csv", "chromo_lines.csv",
           "lagging_lengths.csv", "poles.csv", "CHROMOSOME_MASTER.csv", "SISTERLESS_PLATE_JOIN_TIMES.csv",
           "PREABL_CHROMOSOME_ASSIGNMENT.csv", "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv",
           "KT_TRACKING_MASTER.csv", "ABLATION_MASTER.csv"]

uses = collections.defaultdict(set)          # primary store -> {placed figure}

# The recorded `source` is sometimes just the master even when the builder reads annotation stores
# (timestrips cite the master but crop from `cell_outlines`), so the BUILDER SOURCE is scanned too and
# the two are unioned. Without this the table under-counts the stores that feed image panels.
CODE_DIRS = [ROOT + "/ablation_figures_20260625", ROOT + "/ablation_figures_20260625/figures",
             ROOT + "/ablation_plots/code", ROOT + "/dataops"]
_code_cache = {}
def stores_in_builder(code_name):
    if not code_name: return set()
    if code_name in _code_cache: return _code_cache[code_name]
    text = ""
    cands = [os.path.join(d, code_name) for d in CODE_DIRS]
    base = code_name.split("__", 1)[-1]
    cands += [os.path.join(d, base) for d in CODE_DIRS]
    for c in cands:
        if os.path.exists(c):
            try:
                text = open(c, errors="replace").read(); break
            except OSError:
                pass
    found = set()
    for m in re.findall(r"annotations/([A-Za-z0-9_]+\.csv)", text):
        for prim in (DERIVED.get(m) or ([m] if m in PRIMARY else [])):
            found.add(prim)
    _code_cache[code_name] = found
    return found

for pid in placed:
    e = ps.get(pid)
    if not e: continue
    src = e.get("source") or {}
    files = src.get("files") if isinstance(src, dict) else (src if isinstance(src, list) else [src])
    for f in files or []:
        b = os.path.basename(str(f))
        for prim in (DERIVED.get(b) or ([b] if b in PRIMARY else [])):
            uses[prim].add(pid)
    for prim in stores_in_builder(e.get("code") or ""):
        uses[prim].add(pid)

# ---------------------------------------------------------------- how each mark type was made
def chan_of(r):
    c = (r.get("channel") or "").strip()
    if c: return c
    vf = (r.get("video_file") or "")
    if "Fluor" in vf: return "fluor"
    if "Phase" in vf: return "phase"
    return ""

def norm_chan(c):
    c = c.lower()
    if not c: return "untagged"
    if "phase" in c or "bright" in c: return "phase"
    if c.startswith("640"): return "640 (Cy5)"
    if c.startswith("561"): return "561 (mCherry)"
    if c.startswith("405"): return "405 (DAPI)"
    if "fluor" in c or c.startswith("488"): return "fluorescence (488)"
    return c

# what the MEASUREMENT is read from, per mark type (from the builders, see module docstring)
GATHERED = {
 "cell_outlines.csv":  "geometry only — area/roundness/centroid from the traced polygon; also defines every timestrip crop, which is applied to BOTH channels",
 "kt_points.csv":      "BOTH: geometry (k-k, positions) is channel-independent; intensity is read from the raw 16-bit fluorescence stack of that batch (488 for the cdc20/mad1 lines, 561+640 for the IF/Hec1 sets) — never from the mp4",
 "kt_outlines.csv":    "geometry only — shape metrics from the raster mask of the traced polygon; the same outlines are re-used to read 16-bit fluorescence in the intensity figures",
 "meta_plates.csv":    "geometry only — plate axis and normal from the drawn line",
 "chromo_lines.csv":   "geometry only — length from the drawn line",
 "lagging_lengths.csv":"geometry only — length/width from the drawn line",
 "poles.csv":          "geometry only — pole positions and the pole–pole axis",
 "CHROMOSOME_MASTER.csv": "typed values (congression time, behaviour) — no pixels are measured",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "typed values (plate-join time per chromosome) — no pixels are measured",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "typed values + the pre-ablation KT positions — no pixels are measured",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "typed values (length + movement per chromosome) from the pairing tool",
 "KT_TRACKING_MASTER.csv": "TrackMate detection on the fluorescence channel (automated; used only where no manual mark exists)",
 "ABLATION_MASTER.csv": "event times scored by eye on the movie — the clip carries phase and fluorescence together, so no single channel",
}
LABEL = {
 "cell_outlines.csv": "cell outline (traced polygon, per frame)",
 "kt_points.csv": "kinetochore point marks (click) — incl. pre/post-ablation pairs, polar, lagging, sisterless, paired, cytosol background",
 "kt_outlines.csv": "kinetochore outline (traced polygon, per frame)",
 "meta_plates.csv": "metaphase plate (two-point line)",
 "chromo_lines.csv": "chromosome length (two-point line)",
 "lagging_lengths.csv": "lagging chromosome length / width (two-point line)",
 "poles.csv": "spindle pole (click)",
 "CHROMOSOME_MASTER.csv": "per-chromosome congression time + behaviour (typed)",
 "SISTERLESS_PLATE_JOIN_TIMES.csv": "per-chromosome plate-join time (typed)",
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": "pre-ablation chromosome assignment (typed + positions)",
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": "chromosome length ↔ behaviour pairing (typed)",
 "KT_TRACKING_MASTER.csv": "automated kinetochore tracks (TrackMate)",
 "ABLATION_MASTER.csv": "mitotic event times: NEB, metaphase start, anaphase onset, cytokinesis (scored)",
}

rows_out = []
for store in PRIMARY:
    figs = uses.get(store, set())
    if not figs: continue
    rows = rd(A + store) if store != "ABLATION_MASTER.csv" else []
    if store == "ABLATION_MASTER.csv":
        # the "annotation" here is the scored event times in the master itself
        cells = [b for b, r in MB.items()
                 if any((r.get(c) or "").strip() for c in
                        ("NEB Time (s)", "Metaphase Start (s)", "Anaphase Onset (s)", "Cytokinesis Onset (s)"))]
        rows = [{"batch": b, "phase": "", "channel": "", "video_file": ""} for b in cells]
    batches = collections.Counter((r.get("batch") or "").strip() for r in rows)
    batches.pop("", None)
    ct = collections.Counter()
    for b, n in batches.items(): ct[ctype(b)] += 1
    clip = collections.Counter((r.get("phase") or "").strip() or "untagged" for r in rows)
    ch = collections.Counter(norm_chan(chan_of(r)) for r in rows)

    def top(counter, drop_untagged=True):
        c = {k: v for k, v in counter.items() if not (drop_untagged and k == "untagged")}
        if not c: return "untagged", 0, 0
        tot = sum(c.values())
        k, v = max(c.items(), key=lambda kv: kv[1])
        return k, v, tot
    ck, cv, ctot = top(clip)
    clip_word = ("both, roughly evenly" if ctot and cv / ctot < 0.65 else
                 {"mon": "monitoring", "abl": "ablation"}.get(ck, ck))
    if ctot: clip_word += f" ({cv}/{ctot} tagged rows)"
    hk, hv, htot = top(ch)
    chan_word = ("both, roughly evenly" if htot and hv / htot < 0.65 else hk)
    if htot: chan_word += f" ({hv}/{htot} tagged rows)"
    TYPED = store in ("CHROMOSOME_MASTER.csv", "SISTERLESS_PLATE_JOIN_TIMES.csv",
                      "PREABL_CHROMOSOME_ASSIGNMENT.csv", "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv")
    if TYPED:
        clip_word = "n/a — typed into a table while watching the movie, not marked on a frame"
        chan_word = "n/a — typed value"
    elif store == "ABLATION_MASTER.csv":
        clip_word = "monitoring (the clip that spans NEB to cytokinesis)"
        chan_word = "the review clip shows phase and fluorescence together; the channel is not recorded per event"
    rows_out.append(dict(
        annotation_type=LABEL.get(store, store), store=store,
        live_deck_figures=len(figs), rows=len(rows), cells=len(batches),
        cell_types="; ".join(f"{k} {v}" for k, v in ct.most_common()),
        clip_annotated_on=clip_word,
        clip_breakdown="; ".join(f"{k} {v}" for k, v in clip.most_common()),
        channel_annotated_on=chan_word,
        channel_breakdown="; ".join(f"{k} {v}" for k, v in ch.most_common()),
        gathered_measured_from=GATHERED.get(store, ""),
        example_live_figures="; ".join(sorted(figs)[:4]))) 

rows_out.sort(key=lambda r: -r["live_deck_figures"])
with open(OUTDIR + "/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)

print(f"{'annotation type':52s} {'figs':>4} {'cells':>5}  clip / channel annotated on")
for r in rows_out:
    print(f"{r['annotation_type'][:51]:52s} {r['live_deck_figures']:4d} {r['cells']:5d}  "
          f"{r['clip_annotated_on'][:34]:36s} {r['channel_annotated_on'][:34]}")
    print(f"{'':52s}      cell types: {r['cell_types']}")
unused = []
for store in PRIMARY:
    if uses.get(store): continue
    rows = rd(A + store)
    if not rows: continue
    b = {(r.get("batch") or "").strip() for r in rows}; b.discard("")
    unused.append((LABEL.get(store, store), store, len(rows), len(b)))
if unused:
    print("\nANNOTATED BUT NOT FEEDING ANY FIGURE ON A LIVE DECK:")
    for lab, st, n, c in unused:
        print(f"   {lab[:60]:62s} {n:6d} rows over {c:4d} cells   ({st})")
print(f"\n[done] -> {OUTDIR}/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv")
