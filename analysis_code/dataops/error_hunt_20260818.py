#!/usr/bin/env python3
"""ERROR HUNT — look for mistakes of the same CLASS as the ones she has already caught.

HER WORDS (2026-08-19): "the filters were just one example of an error youve made and didnt catch so im
sure there are many, many others."

So this does not re-check the things I already know about. It looks for the SHAPES of error that have
actually occurred on this project:
  1  SILENT DROPS      a script that filters rows without saying how many it dropped
  2  STALE OUTPUTS     a deliverable older than the data it is built from
  3  UNBACKED CLAIMS   a number in a report that no artefact can reproduce
  4  DUPLICATE TOOLS   two scripts that answer the same question and can disagree
  5  ORPHAN OUTPUTS    a figure/table on a deck whose builder no longer exists
  6  EMPTY DATA        a recorded plot CSV with zero rows behind a placed figure
"""
import csv, io, json, os, re, subprocess, collections, datetime

ROOT = "/Volumes/4 MB"
OUT = ROOT + "/4_TABLES_AND_REPORTS/ERROR_HUNT_20260818.md"
findings = collections.defaultdict(list)

# ---------------------------------------------------------------- 2 STALE OUTPUTS
DELIVERABLES = {
 "4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.html":
     ["annotations/kt_points.csv", "annotations/kt_outlines.csv", "annotations/meta_plates.csv",
      "ablation_plots/PLOT_SETTINGS.json"],
 "4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_CODE_MAP.html": ["ablation_plots/PLOT_SETTINGS.json"],
 "4_TABLES_AND_REPORTS/CONGRESSION_COVERAGE_20260818.csv":
     ["annotations/CHROMOSOME_MASTER.csv", "annotations/SISTERLESS_PLATE_JOIN_TIMES.csv", "ABLATION_MASTER.csv"],
 "4_TABLES_AND_REPORTS/COLLAGEN_GROUPING_20260818.csv": ["ABLATION_MASTER.csv"],
 "4_TABLES_AND_REPORTS/KT_COUNT_PER_CELL_20260818.csv": ["annotations/KT_TRACKING_MASTER.csv", "annotations/kt_outlines.csv"],
 "4_TABLES_AND_REPORTS/ANNOTATION_HEADROOM_20260818.csv": ["annotations/kt_points.csv", "ABLATION_MASTER.csv"],
 "4_TABLES_AND_REPORTS/STATISTICS_INVENTORY_20260818.csv": ["ablation_plots/PLOT_SETTINGS.json"],
 "4_TABLES_AND_REPORTS/PSEUDOREPLICATION_SCAN_20260818.csv": ["ablation_plots/PLOT_SETTINGS.json"],
 "4_TABLES_AND_REPORTS/EXCLUSION_CONSISTENCY_20260818.csv": ["annotations/MANUAL_PLOT_EXCLUSIONS.csv"],
 "4_TABLES_AND_REPORTS/THESIS_SOURCE_DATA_20260818/COMPLETE_WORK_INDEX_20260818.csv": ["ABLATION_MASTER.csv"],
}
for out, srcs in DELIVERABLES.items():
    p = os.path.join(ROOT, out)
    if not os.path.exists(p):
        findings["MISSING DELIVERABLE"].append(f"{out} does not exist"); continue
    om = os.path.getmtime(p)
    for s in srcs:
        sp = os.path.join(ROOT, s)
        if os.path.exists(sp) and os.path.getmtime(sp) > om + 60:
            findings["STALE OUTPUT"].append(
                f"{out} (built {datetime.datetime.fromtimestamp(om):%H:%M}) is older than {s} "
                f"({datetime.datetime.fromtimestamp(os.path.getmtime(sp)):%H:%M})")

# ---------------------------------------------------------------- 6 EMPTY DATA behind placed figures
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))
placed = set()
for f in os.listdir(ROOT + "/_claude_tmp"):
    if f.startswith("geom9_") and f.endswith(".tsv"):
        for r in csv.DictReader(io.open(f"{ROOT}/_claude_tmp/{f}", encoding="utf-8", errors="replace"), delimiter="\t"):
            if r.get("kind") == "PlacedItem" and (r.get("linked") or "").strip():
                placed.add(os.path.basename(r["linked"]).rsplit(".", 1)[0])
for pid in sorted(placed):
    d = os.path.join(ROOT, "ablation_plots/data", pid + ".csv")
    if os.path.exists(d):
        try:
            n = sum(1 for _ in io.open(d, encoding="utf-8", errors="replace")) - 1
        except OSError:
            continue
        if n <= 0:
            findings["EMPTY DATA BEHIND A PLACED FIGURE"].append(f"{pid}: data CSV has 0 rows")

# ---------------------------------------------------------------- 5 ORPHAN builders
for pid in sorted(placed):
    e = ps.get(pid)
    if not e:
        findings["PLACED FIGURE WITH NO PROVENANCE"].append(pid); continue
    raw = (e.get("code") or "")
    if not raw: continue
    # a recorded code name can carry the plot id AND a panel prefix ("G6ten_peakzoom__p12__custom_x.py",
    # "code/G4_x__builder.py"), so try every suffix, not just the last one, before calling it an orphan
    cands = {raw, os.path.basename(raw)}
    parts = os.path.basename(raw).split("__")
    for i in range(len(parts)):
        cands.add("__".join(parts[i:]))
    cands = {c for c in cands if c.endswith(".py")}
    found = any(os.path.exists(os.path.join(d, c))
                for d in (ROOT + "/ablation_figures_20260625", ROOT + "/ablation_figures_20260625/figures",
                          ROOT + "/dataops", ROOT + "/ablation_plots/code", ROOT)
                for c in cands)
    code = os.path.basename(raw)
    if not found:
        findings["BUILDER NOT ON DISK"].append(f"{pid} -> {code}")

# ---------------------------------------------------------------- 1 SILENT DROPS in my own new tools
MINE = [f for f in os.listdir(ROOT + "/dataops") if f.endswith("_20260818.py")]
for f in MINE:
    t = open(os.path.join(ROOT, "dataops", f), errors="replace").read()
    conts = len(re.findall(r"\n\s+continue\b", t))
    reports = len(re.findall(r"drop|skip|exclud|untagged", t, re.I))
    if conts >= 3 and reports == 0:
        findings["FILTER WITH NO REPORTING"].append(f"dataops/{f}: {conts} filter branches, no drop counter")

# ---------------------------------------------------------------- 4 DUPLICATE TOOLS
# congression_coverage (per-cell coverage) and congression_store_compare (do the two stores agree) answer
# DIFFERENT questions, so they are not a duplicate pair.
pairs = [("annotation_types_in_use_20260818.py", "annotation_types_table_20260818.py")]
for a, b in pairs:
    pa, pb = os.path.join(ROOT, "dataops", a), os.path.join(ROOT, "dataops", b)
    if os.path.exists(pa) and os.path.exists(pb):
        ta = open(pa, errors="replace").read()
        if "SUPERSEDED" not in ta.split("\n", 6)[0] + ta[:400]:
            findings["TWO TOOLS, SAME QUESTION"].append(f"dataops/{a} vs dataops/{b} — is {a} marked superseded?")

# ---------------------------------------------------------------- 3 UNBACKED CLAIMS (spot list)
def rows(p):
    with io.open(os.path.join(ROOT, p), encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))
claims = []
try:
    t = open(ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.md",
             encoding="utf-8", errors="replace").read()
    kt = len([r for r in rows("annotations/kt_points.csv")
              if not re.search(r"IF stained|IF dish|\bIF\b|mug", (r.get("batch") or ""), re.I)])
    claims.append(("kt_points marks in the table", str(kt) in t, kt))
    mp = len(rows("annotations/meta_plates.csv"))
    claims.append(("meta_plates marks in the table", str(mp) in t, mp))
except Exception as e:
    findings["CLAIM CHECK FAILED"].append(str(e))
for name, ok, val in claims:
    if not ok:
        findings["NUMBER IN A DOC NOT REPRODUCIBLE"].append(f"{name}: recomputed {val}, not found in the doc")


# ---------------------------------------------------------------- 7 CROSS-TOOL DISAGREEMENT
# Two of my own tools reporting different numbers for the same quantity is how a silent error shows itself.
def _count_cells(store, exclude_ifmug=True):
    rs = rows("annotations/" + store)
    b = set()
    for r in rs:
        x = (r.get("batch") or "").strip()
        if not x: continue
        if exclude_ifmug and re.search(r"IF stained|IF dish|\bIF\b|mug", x, re.I): continue
        b.add(x)
    return len(b), len(rs)

try:
    tbl = list(csv.DictReader(io.open(ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818/ANNOTATION_TYPES_IN_ACTIVE_DECKS.csv",
                                      encoding="utf-8", errors="replace")))
    STORE_OF = {"Kinetochore outline": "kt_outlines.csv", "Metaphase plate": "meta_plates.csv",
                "Cell outline": "cell_outlines.csv", "Chromosome length": "chromo_lines.csv",
                "Spindle poles": "poles.csv"}
    for r in tbl:
        for label, store in STORE_OF.items():
            # EXACT label, not startswith: "Chromosome length" also prefixes "Chromosome length <-> behaviour
            # pairing", and the loose match produced a false disagreement on the first run of this check.
            if r["Annotation"].strip() == label:
                cells, marks = _count_cells(store)
                if int(r["Cells"]) != cells or int(r["Marks"]) != marks:
                    findings["CROSS-TOOL DISAGREEMENT"].append(
                        f"{label}: table says {r['Cells']} cells / {r['Marks']} marks; the store has {cells} / {marks}")
except Exception as e:
    findings["CLAIM CHECK FAILED"].append("annotation table cross-check: " + str(e))

# work index vs master
try:
    wi = rows("4_TABLES_AND_REPORTS/THESIS_SOURCE_DATA_20260818/COMPLETE_WORK_INDEX_20260818.csv")
    master = rows("ABLATION_MASTER.csv")
    n_master = sum(1 for r in master if (r.get("Batch Name") or r.get("") or "").strip()) 
    if abs(len(wi) - 1612) > 5:
        findings["CROSS-TOOL DISAGREEMENT"].append(f"work index has {len(wi)} rows; the report says 1,612")
except Exception as e:
    findings["CLAIM CHECK FAILED"].append("work index: " + str(e))

# ---------------------------------------------------------------- 8 TRIPLET AGREEMENT (html/csv/md)
for stem in ("ANNOTATION_TYPES_IN_ACTIVE_DECKS", "ANNOTATION_CODE_MAP"):
    d = ROOT + "/4_TABLES_AND_REPORTS/METHODS_20260818/"
    try:
        c = list(csv.reader(io.open(d + stem + ".csv", encoding="utf-8", errors="replace")))
        h = io.open(d + stem + ".html", encoding="utf-8", errors="replace").read()
        m = io.open(d + stem + ".md", encoding="utf-8", errors="replace").read()
        n_csv = len(c) - 1
        n_html = h.count("<tr>") - h.count("<th>") // max(1, len(c[0]))
        n_md = sum(1 for line in m.splitlines() if line.startswith("| ") and not set(line) <= set("| -"))
        if n_csv < 1:
            findings["EMPTY DELIVERABLE"].append(stem + ".csv has no rows")
        for col in c[0]:
            if col and col not in h:
                findings["TRIPLET MISMATCH"].append(f"{stem}: column '{col}' is in the CSV but not the HTML")
    except Exception as e:
        findings["CLAIM CHECK FAILED"].append(f"{stem} triplet: {e}")

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("# Error hunt — 2026-08-18\n\n*Looking for the SHAPES of mistake that have actually happened on\n"
            "this project, not re-checking what is already known.*\n\n")
    total = sum(len(v) for v in findings.values())
    f.write(f"**{total} finding(s).**\n\n")
    for k, v in sorted(findings.items(), key=lambda kv: -len(kv[1])):
        f.write(f"## {k} — {len(v)}\n")
        for x in v[:40]:
            f.write(f"* {x}\n")
        f.write("\n")
    if not findings:
        f.write("No findings in any category.\n")
print(f"findings: {sum(len(v) for v in findings.values())}")
for k, v in findings.items():
    print(f"  {k}: {len(v)}")
    for x in v[:6]: print("      ", x)
print("->", OUT)
