#!/usr/bin/env python3
"""COMPLETE WORK INDEX — one row per imaged cell, what was done to it, and where it appears.

WHY (Sophie Dumont, 2026-07-07, thesis-committee thread): "the lab notebook and list of movies,
experiments, analyses, etc. should not just be for the thesis but for the totality of work you have
done ... since 2023. Most work people do does not end up in the thesis but must still be accessible to
others so others can build on it or learn from it."

The panel-centric map (PANEL_SOURCE_DATA_MAP.csv) answers "what went into Figure 2A".  This answers the
other direction: for EVERY cell ever imaged and recorded in the master, what exists for it — which
annotation stores hold marks, whether it was ablated, whether it is excluded and why, which figures use
it, and which processed movies exist.  Cells that never reached a figure are listed too; that is the
point.
"""
import csv, io, os, re, sys, collections, subprocess
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"; A = ROOT + "/annotations/"; DATA = ROOT + "/ablation_plots/data"
OUT = ROOT + "/4_TABLES_AND_REPORTS/THESIS_SOURCE_DATA_20260818/COMPLETE_WORK_INDEX_20260818.csv"

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
STORES = ["cell_outlines.csv", "kt_points.csv", "kt_outlines.csv", "meta_plates.csv",
          "chromo_lines.csv", "lagging_lengths.csv", "poles.csv", "CHROMOSOME_MASTER.csv",
          "SISTERLESS_PLATE_JOIN_TIMES.csv", "PREABL_CHROMOSOME_ASSIGNMENT.csv",
          "KT_TRACKING_MASTER.csv", "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv"]
marks = {}
for s in STORES:
    c = collections.Counter((r.get("batch") or "").strip() for r in rd(A + s))
    c.pop("", None)
    marks[s[:-4]] = c

figs = collections.defaultdict(set)
for fn in os.listdir(DATA):
    if not fn.endswith(".csv"): continue
    rows = rd(os.path.join(DATA, fn))
    if not rows: continue
    bcol = next((c for c in rows[0] if c and c.strip().lower() in ("batch", "batch_name", "cell")), None)
    if not bcol: continue
    for r in rows:
        b = (r.get(bcol) or "").strip()
        if b: figs[b].add(fn[:-4])

DECKS = ["META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
         "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"]
placed = set()
for d in DECKS:
    txt = subprocess.run(["strings", f"{ROOT}/1_DECKS/{d}"], capture_output=True, text=True).stdout
    placed |= set(re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", txt))

PIPE = ROOT + "/pipeline_session_output"
have_dir = {}
for date in os.listdir(PIPE) if os.path.isdir(PIPE) else []:
    dp = os.path.join(PIPE, date)
    if not os.path.isdir(dp): continue
    for b in os.listdir(dp):
        have_dir[b] = os.path.join(date, b)

rows_out = []
for r in M:
    b = (r.get("Batch Name") or "").strip()
    if not b: continue
    f = sorted(figs.get(b, ()))
    fp = [x for x in f if x in placed]
    d = have_dir.get(b, "")
    n_mp4 = 0
    if d:
        try: n_mp4 = sum(1 for x in os.listdir(os.path.join(PIPE, d)) if x.endswith(".mp4"))
        except OSError: pass
    row = dict(batch=b, date=b.split()[0], cell_type=(r.get("Cell Type") or "").strip(),
               phase_of_ablation=(r.get("Phase of Ablations") or "").strip(),
               on_off_target=(r.get("On-Target / Off-Target") or "").strip(),
               n_sisterless=(r.get("# Sisterless KTs") or "").strip(),
               excluded=(r.get("Exclude") or "").strip(),
               exclude_reason=(r.get("Exclude Reason") or "").strip()[:120],
               processed_movie_dir=d, n_mp4=n_mp4,
               n_figures_any=len(f), n_figures_on_a_live_deck=len(fp),
               figures_on_a_live_deck=";".join(fp[:8]),
               notes=(r.get("Notes") or "").strip()[:200])
    for s, c in marks.items():
        row["marks_" + s] = c.get(b, 0)
    rows_out.append(row)

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)

n = len(rows_out)
anno = sum(1 for r in rows_out if any(r[k] for k in r if k.startswith("marks_")))
inplace = sum(1 for r in rows_out if r["n_figures_on_a_live_deck"])
anyfig = sum(1 for r in rows_out if r["n_figures_any"])
mov = sum(1 for r in rows_out if r["processed_movie_dir"])
print(f"cells recorded in the master      : {n}")
print(f"  with a processed movie folder   : {mov}")
print(f"  with at least one annotation    : {anno}")
print(f"  used in at least one figure     : {anyfig}")
print(f"  used in a figure on a live deck : {inplace}")
print(f"  imaged but never used in a figure: {n - anyfig}")
by = collections.Counter(r["date"][:4] for r in rows_out)
print("  by year:", dict(sorted(by.items())))
print(f"\n[done] -> {OUT}")
