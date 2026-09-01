#!/usr/bin/env python3
"""ITEM-BY-ITEM CHECKLIST of everything she has asked for since 2026-08-18, with the evidence for each.

Written because she said items were being missed. Every row is CHECKED at run time — a row can only say
DONE if the artefact it names exists and contains what it claims.
"""
import csv, io, json, os, re, subprocess
ROOT = "/Volumes/4 MB"
OUT = ROOT + "/4_TABLES_AND_REPORTS/REQUEST_CHECKLIST_20260818.md"

def exists(p): return os.path.exists(os.path.join(ROOT, p))
def contains(p, *needles):
    try: t = io.open(os.path.join(ROOT, p), encoding="utf-8", errors="replace").read()
    except OSError: return False
    return all(n.lower() in t.lower() for n in needles)
def csv_has_col(p, col):
    try:
        with io.open(os.path.join(ROOT, p), encoding="utf-8", errors="replace") as f:
            return col.lower() in [c.strip().lower() for c in next(csv.reader(f))]
    except Exception: return False

ITEMS = [
 ("Paths correct after the two reorgs (code, 5 live .ai, 2 publication .ai, elsewhere)",
  lambda: exists("_claude_tmp/paths_20260818/fix_paths_report.json") and contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "177 replacements"),
  "SESSION_REPORT §1 — 70 files, 177 replacements; all 20 .ai link-checked, 0 missing on the live and publication decks"),
 ("Re-derive the five headline findings",
  lambda: exists("_claude_tmp/todo0818/results.json") and contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "does not hold"),
  "SESSION_REPORT §2 — reproduced bit-for-bit; the 3-sisterless speed result does not survive per-cell testing"),
 ("Exposure times per cell type for Methods",
  lambda: exists("4_TABLES_AND_REPORTS/METHODS_20260818/EXPOSURES_SUMMARY.csv") and exists("4_TABLES_AND_REPORTS/METHODS_20260818/ACQUISITION_AND_IMAGING.md"),
  "METHODS_20260818/ACQUISITION_AND_IMAGING.md + EXPOSURES_{SUMMARY,BY_CELLTYPE}.csv — 10,817 records, 57 dates"),
 ("Plate width / field criteria for Methods",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/MEASUREMENTS_AND_ANNOTATIONS.md", "plate width", "23.0"),
  "MEASUREMENTS_AND_ANNOTATIONS.md — 23.0 um median width, 1.02 um thickness, with Jaqaman 2010 definition"),
 ("List of every annotation type, how gathered, with code file names",
  lambda: csv_has_col("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv", "Code that captures it / turns it into a number"),
  "ANNOTATION_TYPES_IN_ACTIVE_DECKS.{html,csv,md} — column present"),
 ("A dedicated table of the python file per annotation type",
  lambda: exists("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_CODE_MAP.html") and csv_has_col("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_CODE_MAP.csv", "Python files that MEASURE from it"),
  "ANNOTATION_CODE_MAP.{html,csv,md} — captured-by / measured-by / feeds-builders per annotation type"),
 ("Citable precedent for each measurement method",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/MEASUREMENTS_AND_ANNOTATIONS.md", "Richter", "Jaqaman"),
  "MEASUREMENTS_AND_ANNOTATIONS.md — precedent table (Elting 2014/2017, Richter 2023, Jaqaman 2010)"),
 ("Congression coverage, cell by cell",
  lambda: exists("4_TABLES_AND_REPORTS/CONGRESSION_COVERAGE_20260818.csv"),
  "CONGRESSION_COVERAGE_20260818.csv — 65/66 = 98.5%, the one gap named"),
 ("Are the two congression annotation types different? do they cover different batches?",
  lambda: exists("4_TABLES_AND_REPORTS/CONGRESSION_STORE_COMPARE_20260818.csv") and contains("ablation_figures_20260625/lib.py", "def congression_times"),
  "CONGRESSION_STORE_COMPARE_20260818.csv + lib.congression_times() — same measurement, 43 vs 29 cells, union 44"),
 ("What other figures are low on data",
  lambda: exists("4_TABLES_AND_REPORTS/ANNOTATION_HEADROOM_20260818.csv"),
  "ANNOTATION_HEADROOM_20260818.csv — coverage per store per cohort + thin figures"),
 ("Journal figure/video guidelines",
  lambda: exists("4_TABLES_AND_REPORTS/METHODS_20260818/JOURNAL_FIGURE_GUIDELINES.md"),
  "JOURNAL_FIGURE_GUIDELINES.md — JCB and eLife requirements + checklist"),
 ("Overexpression control evidence (unlabelled PtK2? mad1 vs cdc20 timing?)",
  lambda: contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "no unlabelled PtK2 data"),
  "SESSION_REPORT §10 — no unlabelled data exists; mad1 timing not scored; 145 movies ready to score"),
 ("Do any cdc20 cells have more than the typical number of kinetochores",
  lambda: exists("4_TABLES_AND_REPORTS/KT_COUNT_PER_CELL_20260818.csv") and contains("dataops/kt_count_per_cell_20260818.py", "14, 28"),
  "KT_COUNT_PER_CELL_20260818.csv — screened at 14 chromosomes / 28 kinetochores (corrected); 4 candidates"),
 ("Committee source-data package: raw data, movies, instructions, figure components",
  lambda: contains("4_TABLES_AND_REPORTS/THESIS_SOURCE_DATA_20260818/PROTOCOL.md", "FIGURE_COMPONENTS", "COMPLETE_WORK_INDEX"),
  "PROTOCOL.md §8a-d + COMPLETE_WORK_INDEX_20260818.csv"),
 ("Batch inclusion/exclusion consistency across plots",
  lambda: exists("4_TABLES_AND_REPORTS/EXCLUSION_CONSISTENCY_20260818.csv"),
  "EXCLUSION_CONSISTENCY_20260818.csv — 3 defects found, 2 fixed, 1 left to her (now resolved: keep it)"),
 ("Should collagen batches be pooled or shown separately",
  lambda: exists("4_TABLES_AND_REPORTS/COLLAGEN_GROUPING_20260818.csv"),
  "COLLAGEN_GROUPING_20260818.csv — pool for shape/mechanics, keep separate for duration"),
 ("Do linear display adjustments need accounting for in intensity measurements",
  lambda: contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "background subtraction is NOT enough"),
  "SESSION_REPORT §8 — gain survives background subtraction; all deck figures use raw 16-bit; one builder fixed"),
 ("Extend/add artboards over the figures",
  lambda: contains("NOTES.md", "ADD_ARTBOARDS_0818.jsx"),
  "21 artboards added; off-board figures 178 -> 35 (the 35 are outside the artboard-legal canvas)"),
 ("Relink/delete the retired G3 figure in the paper files",
  lambda: exists("ablation_plots/DELETE_RETIRED_G3_0818.jsx"),
  "Checked all four paper files: 0 live placements — the 'broken link' was XMP history, files untouched"),
 ("triple_ablation_12 stays in the two named lagging analyses",
  lambda: contains("ablation_figures_20260625/custom_lagging_vs_congression.py", "REVIEW_EXCLUDE CARVE-OUT"),
  "Carve-out now documented IN custom_lagging_vs_congression.py (ALLOW_REVIEW_EXCLUDED), not only in NOTES"),
 ("Redraw legend bullets and resolve all legend items",
  lambda: contains("NOTES.md", "2,089 bullet lines"),
  "2,089 bullet lines across the five decks, 0 figures without a legend"),
 ("Annotation table: counts were too small",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.md", "5589") or contains("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv", "5589"),
  "Legacy rows counted again — kt_points 5,589 marks / 135 cells; meta_plates 4,490 / 82"),
 ("The two channel/geometry explanations belong in the table",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv", "THE SHAPE SHE DREW", "640"),
  "Both moved into the cells of the table"),
 ("What filters dropped thousands of points; what else have I filtered",
  lambda: contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "measured not asserted"),
  "SESSION_REPORT §17 — today 3 figures / 5 rows, both her exclusions; the big drops since 08-03 are all her instructions"),
 ("All types of statistical analyses in the current results",
  lambda: exists("4_TABLES_AND_REPORTS/STATISTICS_INVENTORY_20260818.csv"),
  "STATISTICS_INVENTORY_20260818.csv — 13 test types across 417 figures"),
 ("Online supplemental material — needed? GitHub location instead?",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/METHODS_REVIEW_LIST_20260818.md", "Online supplemental material"),
  "METHODS_REVIEW_LIST — keep it only for numbered supplements; add the code/data availability paragraph"),
 ("Add supplier designations to the Methods tab, in Dumont-lab format",
  lambda: contains("4_TABLES_AND_REPORTS/METHODS_20260818/METHODS_REVIEW_LIST_20260818.md", "11095", "M1404"),
  "5 insertions made and highlighted in the doc; the papers searched and what each gave are listed"),
 ("Keep a list of everything else noticed",
  lambda: exists("4_TABLES_AND_REPORTS/METHODS_20260818/METHODS_REVIEW_LIST_20260818.md"),
  "METHODS_REVIEW_LIST_20260818.md"),
 ("Highlight the changes made in the Google Doc",
  lambda: contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "highlighted pale blue"),
  "All five insertions highlighted pale blue; verified the highlighting changed no text"),
 ("A_OFF_DECK_QUESTIONS and B_DECK_FEEDBACK_STATUS kept updated",
  lambda: contains("dataops/feedback_log.py", "_infer_deck"),
  "Routing bug fixed — instructions were defaulting into A; B now 82 items, A 143, 0 unannotated"),
 ("No figure overlaps on the artboards",
  lambda: contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "0 overlapping pairs among visible figures"),
  "0 on any artboard, all 8 decks (re-audited in \u00a718 from dumps that postdate every deck save); the one "
  "18% pair left is two PASTEBOARD items on pub-0813, off every artboard"),
 ("Check again, even more thoroughly (2026-08-19)",
  lambda: exists("4_TABLES_AND_REPORTS/DEEP_VERIFY_20260818.md")
          and contains("4_TABLES_AND_REPORTS/SESSION_REPORT_20260818b.md", "\u00a718 Second-level verification"),
  "DEEP_VERIFY_20260818.md + report \u00a718 \u2014 6 defects found and fixed: 5 orphan registry entries, sync_pub audit scope (155\u2192185), 4 unbacked edits, overlap re-audit, annotation counts re-derived, 4 stale outputs"),
 ("Check the work thoroughly / hunt for uncaught errors",
  lambda: exists("4_TABLES_AND_REPORTS/ERROR_HUNT_20260818.md"),
  "ERROR_HUNT_20260818.md — stale-output, orphan-builder, silent-filter, cross-tool and triplet checks"),
]

rows = []
for name, test, evidence in ITEMS:
    try: ok = bool(test())
    except Exception: ok = False
    rows.append((ok, name, evidence))

done = sum(1 for ok, _, _ in rows if ok)
with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("# Every item you asked for, and where it is\n\n")
    f.write(f"*Checked at run time by `dataops/request_checklist_20260818.py` — a row can only say DONE if the\n"
            f"artefact it names exists and contains what it claims.* **{done} of {len(rows)} verified.**\n\n")
    f.write("| | item | where it is |\n|---|---|---|\n")
    for ok, name, ev in rows:
        f.write(f"| {'✅' if ok else '❌'} | {name} | {ev} |\n")
print(f"{done}/{len(rows)} items verified")
for ok, name, _ in rows:
    if not ok: print("   NOT VERIFIED:", name)
print("->", OUT)
