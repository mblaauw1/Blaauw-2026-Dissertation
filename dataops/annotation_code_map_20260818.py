#!/usr/bin/env python3
"""WHICH PYTHON FILE DOES WHAT, PER ANNOTATION TYPE — a standalone table.

HER ASK (2026-08-19): "make a new table that has the python files for each annotation type specified"
(so a reader can find the code on GitHub).

Three columns of code per annotation type, and only the first is hand-written:
  CAPTURED BY   the browser tool + server that record the mark (one pair for every hand annotation)
  COMPUTED BY   every live script that READS that store - found by scanning the code, not listed by hand
  FEEDS         the builders of figures actually placed on the five live decks that depend on it

Outputs HTML (paste into Google Docs), CSV and Markdown from one pass.
"""
import csv, io, json, os, re, subprocess, collections, html

ROOT = "/Volumes/4 MB"
OUTDIR = ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818"
SCAN_DIRS = [ROOT + "/ablation_figures_20260625", ROOT + "/ablation_figures_20260625/figures",
             ROOT + "/dataops", ROOT + "/kt_outline", os.path.expanduser("~/ablation-pipeline"),
             os.path.expanduser("~/ablation-pipeline/analysis_slides_package")]
SKIP = (".bak", "_builder_backup", "_retired", "/code/", "__pycache__", "_ARCHIVE", ".bak_violin")

STORES = {
 "kt_points.csv": ("Kinetochore point marks (target pair before/after ablation, polar, lagging, sisterless, paired, cytosol background)",
                   "make_annotation_html.py + serve_annotation.py"),
 "kt_outlines.csv": ("Kinetochore outlines (traced)", "make_outline_html.py + serve_annotation.py"),
 "cell_outlines.csv": ("Cell outlines (traced)", "make_outline_html.py + serve_annotation.py"),
 "meta_plates.csv": ("Metaphase plate line", "make_annotation_html.py + serve_annotation.py"),
 "chromo_lines.csv": ("Chromosome length line", "make_annotation_html.py + serve_annotation.py"),
 "lagging_lengths.csv": ("Lagging kinetochore length/width cross marks", "make_annotation_html.py + serve_annotation.py"),
 "poles.csv": ("Spindle pole points", "make_annotation_html.py + serve_annotation.py"),
 "CHROMOSOME_MASTER.csv": ("Per-chromosome congression time + behaviour (typed)", "pairing_server.py (port 8781)"),
 "SISTERLESS_PLATE_JOIN_TIMES.csv": ("Per-chromosome plate-join time (typed)", "serve_annotation.py slide panel"),
 "PREABL_CHROMOSOME_ASSIGNMENT.csv": ("Pre-ablation chromosome assignment", "derived from her ablation marks"),
 "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv": ("Chromosome length <-> behaviour pairing (typed)", "pairing_server.py (port 8781)"),
 "KT_TRACKING_MASTER.csv": ("Automated kinetochore tracks (TrackMate)", "kt_tracking/code/kt_record.py (Fiji/TrackMate)"),
 "ABLATION_MASTER.csv": ("Mitotic event times (NEB, metaphase, anaphase, cytokinesis)", "range_server.py review deck (port 8781)"),
}
# derived stores that stand between a mark and a figure
DERIVED_OF = {
 "kt_outlines.csv": ["KT_OUTLINE_TRACKS_20260723", "KT_LANDMARK_ANALYSIS_20260723", "KT_SISTER_KK_20260723",
                     "KT_SISTERS_20260723", "KT_TENSION_20260723", "KT_TENSION_LOADAXIS_20260805",
                     "KT_LOADING_AXIS_20260805", "MAD1_KT_OUTLINE_TRACKS_20260727", "KT_TRACKS_DRIFTCORR_20260808"],
 "meta_plates.csv": ["META_PLATE_NORMALIZED_20260728", "KT_LANDMARK_ANALYSIS_20260723"],
 "chromo_lines.csv": ["KT_CHROMO_ANALYSIS_20260723"],
 "kt_points.csv": ["KT_FLUOR_CYTOSOLNORM_20260728", "G5_hec1_mad1_TRUE_quant", "CYTOSOL_BACKGROUND_MASTER"],
}

def py_files():
    out = []
    for d in SCAN_DIRS:
        if not os.path.isdir(d): continue
        for fn in os.listdir(d):
            p = os.path.join(d, fn)
            if not fn.endswith(".py") or not os.path.isfile(p): continue
            if any(s in p for s in SKIP): continue
            out.append(p)
    return sorted(set(out))

FILES = py_files()
TEXT = {}
for p in FILES:
    try: TEXT[p] = open(p, errors="replace").read()
    except OSError: pass

# A reader is only interesting to a READER OF THE PAPER if it MEASURES something. checks.py, the
# archive tools and my own 2026-08-18 audit scripts read every store and would bury the real answer.
AUDIT_HINTS = ("checks.py", "audit", "archive_cold", "complete_work_index", "annotation_headroom",
               "annotation_types_", "annotation_code_map", "congression_coverage", "congression_store",
               "build_plot_provenance", "moved_index", "verify_", "diff_coverage", "snapshot",
               "feedback_log", "stats_inventory", "exclusion_consistency", "pseudoreplication",
               "kt_count_per_cell", "collagen_grouping", "marker_control", "exposure_table",
               "register_unlegended", "sig_scan", "apply_edits", "repair", "fix_")

def classify(basename, text):
    if any(h in basename for h in AUDIT_HINTS):
        return "audit"
    if "record_plot(" in text or "register_panel(" in text:
        return "measurement"
    if "csv.writer" in text or "DictWriter" in text or "to_csv" in text:
        return "measurement"
    return "other"

def readers(store):
    stem = store.replace(".csv", "")
    meas, audit, other = [], [], []
    for p, t in TEXT.items():
        if not (store in t or (stem in t and len(stem) > 8)):
            continue
        b = os.path.basename(p)
        k = classify(b, t)
        (meas if k == "measurement" else audit if k == "audit" else other).append(b)
    return sorted(set(meas)), sorted(set(audit)), sorted(set(other))

# figures placed on live decks, and their builders
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))
placed = set()
for f in os.listdir(ROOT + "/_claude_tmp"):
    if f.startswith("geom9_") and f.endswith(".tsv"):
        for r in csv.DictReader(io.open(f"{ROOT}/_claude_tmp/{f}", encoding="utf-8", errors="replace"), delimiter="\t"):
            if r.get("kind") == "PlacedItem" and (r.get("linked") or "").strip():
                placed.add(os.path.basename(r["linked"]).rsplit(".", 1)[0])

builder_src = {}
for pid in placed:
    code = (ps.get(pid) or {}).get("code") or ""
    if not code: continue
    base = code.split("__", 1)[-1]
    for p in FILES:
        if os.path.basename(p) == base:
            builder_src.setdefault(base, set()).add(pid)
            break

def feeds(store):
    stem = store.replace(".csv", "")
    keys = [store, stem] + DERIVED_OF.get(store, [])
    out = collections.Counter()
    for base, pids in builder_src.items():
        p = next((x for x in FILES if os.path.basename(x) == base), None)
        if not p: continue
        t = TEXT.get(p, "")
        if any(k in t for k in keys):
            out[base] = len(pids)
    return out

rows = []
for store, (label, capture) in STORES.items():
    meas, audit, other = readers(store)
    fd = feeds(store)
    rows.append(dict(annotation=label, store=store, captured_by=capture,
                     computed_by="; ".join(meas[:10]) + (" ..." if len(meas) > 10 else ""),
                     n_readers=len(meas),
                     qa_tools=f"{len(audit)} QA/audit scripts also read it (checks.py, the 2026-08-18 audits)",
                     feeds_builders="; ".join(f"{b} ({n} figs)" for b, n in fd.most_common(6)),
                     n_live_figures=sum(fd.values()),
                     derived_stores="; ".join(DERIVED_OF.get(store, [])) or "—"))

rows.sort(key=lambda r: -r["n_live_figures"])
# An empty cell in a table she will paste into Google Docs reads as "not checked"; it actually means
# "nothing" (TrackMate tracks feed no live figure -- manual marks override them). Say so with an em dash.
for _r in rows:
    for _k, _v in list(_r.items()):
        if isinstance(_v, str) and not _v.strip(): _r[_k] = "\u2014"
COLS = [("annotation", "Annotation type"), ("store", "Stored in"),
        ("captured_by", "Captured by (the tool that records the mark)"),
        ("derived_stores", "Intermediate derived tables"),
        ("computed_by", "Python files that MEASURE from it"),
        ("feeds_builders", "Figure builders it feeds (live decks)"),
        ("qa_tools", "Also read by"), ("n_readers", "# measuring scripts"),
        ("n_live_figures", "# live figures")]

with open(OUTDIR + "/ANNOTATION_CODE_MAP.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow([c[1] for c in COLS])
    for r in rows: w.writerow([r[c[0]] for c in COLS])

def td(x): return html.escape(str(x))
H = ["<!doctype html><html><head><meta charset='utf-8'><title>Annotation types and their code</title>",
     "<style>body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;margin:24px}",
     "table{border-collapse:collapse;width:100%}th,td{border:1px solid #999;padding:6px 8px;vertical-align:top;text-align:left}",
     "th{background:#eee}td.num{text-align:right}code{font-size:10pt}</style></head><body>",
     "<h2>Annotation types and the python files behind them</h2>",
     "<p>Built 2026-08-18 by <code>dataops/annotation_code_map_20260818.py</code>. The capture column is the "
     "browser tool and server that record the mark; the other code columns are found by scanning the code "
     "itself, so they cannot go stale by hand. &quot;Live figures&quot; counts figures placed on the five "
     "live Illustrator decks whose builder reads that annotation (directly or through a derived table).</p>",
     "<table><thead><tr>" + "".join(f"<th>{td(c[1])}</th>" for c in COLS) + "</tr></thead><tbody>"]
for r in rows:
    H.append("<tr>" + "".join(
        f"<td class='num'>{td(r[c[0]])}</td>" if c[0].startswith("n_") else f"<td>{td(r[c[0]])}</td>"
        for c in COLS) + "</tr>")
H.append("</tbody></table></body></html>")
open(OUTDIR + "/ANNOTATION_CODE_MAP.html", "w", encoding="utf-8").write("\n".join(H))

md = ["# Annotation types and the python files behind them", "",
      "*Built 2026-08-18 by `dataops/annotation_code_map_20260818.py`; the code columns are scanned from the",
      "code itself. Paste-ready copy: `ANNOTATION_CODE_MAP.html`.*", "",
      "| " + " | ".join(c[1] for c in COLS) + " |", "|" + "|".join("---" for _ in COLS) + "|"]
for r in rows:
    md.append("| " + " | ".join(str(r[c[0]]).replace("|", "/") for c in COLS) + " |")
open(OUTDIR + "/ANNOTATION_CODE_MAP.md", "w", encoding="utf-8").write("\n".join(md) + "\n")

print(f"{'annotation':52s} {'scripts':>7} {'live figs':>9}")
for r in rows:
    print(f"{r['annotation'][:51]:52s} {r['n_readers']:7d} {r['n_live_figures']:9d}")
    print(f"      captured by : {r['captured_by']}")
    print(f"      computed by : {r['computed_by'][:150]}")
print(f"\n[done] -> {OUTDIR}/ANNOTATION_CODE_MAP.{{html,csv,md}}")
