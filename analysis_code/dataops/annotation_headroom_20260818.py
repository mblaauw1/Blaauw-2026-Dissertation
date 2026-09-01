#!/usr/bin/env python3
"""What is thin: per-store annotation coverage, and the placed figures built on the least data.

HER ASK (2026-08-18): "what other figures/etc are low on annotations/data".

PART A -- COVERAGE PER STORE over the cells that could have it (the on-target, non-drug, non-excluded
1/2/3-sisterless cdc20 cohort, plus their off-target and unmodified controls).  Missing coverage here is
annotation headroom: it is work she can do that directly grows a figure.
PART B -- the placed figures ranked by how few CELLS their recorded data contains, with the store each
figure draws on, so a thin figure can be traced to the annotation that would thicken it.
"""
import csv, io, os, re, sys, collections, subprocess, json
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"; A = ROOT + "/annotations/"; DATA = ROOT + "/ablation_plots/data"
OUT = ROOT + "/4_TABLES_AND_REPORTS/ANNOTATION_HEADROOM_20260818.csv"

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}

def klass(b):
    r = MB.get(b)
    if not r: return None
    if (r.get("Exclude") or "").strip().lower() in ("yes", "true", "1"): return None
    if lib.is_drug(b): return None
    n = (r.get("# Sisterless KTs") or "").strip()
    tgt = (r.get("On-Target / Off-Target") or "").strip().lower()
    if tgt.startswith("off"): return "off-target control"
    if n in ("1", "2", "3"): return f"{n}-sisterless on-target"
    if not tgt and n in ("", "0"): return "unmodified"
    return None

pool = collections.defaultdict(set)
for b in MB:
    k = klass(b)
    if k: pool[k].add(b)

STORES = {
    "cell_outlines": "cell_outlines.csv", "kt_points": "kt_points.csv",
    "kt_outlines": "kt_outlines.csv", "meta_plates": "meta_plates.csv",
    "chromo_lines": "chromo_lines.csv", "lagging_lengths": "lagging_lengths.csv",
    "poles": "poles.csv", "CHROMOSOME_MASTER": "CHROMOSOME_MASTER.csv",
    "SISTERLESS_PLATE_JOIN_TIMES": "SISTERLESS_PLATE_JOIN_TIMES.csv",
    "KT_TRACKING_MASTER": "KT_TRACKING_MASTER.csv",
    "PREABL_CHROMOSOME_ASSIGNMENT": "PREABL_CHROMOSOME_ASSIGNMENT.csv",
}
have = {}
for name, fn in STORES.items():
    have[name] = {(r.get("batch") or "").strip() for r in rd(A + fn) if (r.get("batch") or "").strip()}

order = ["1-sisterless on-target", "2-sisterless on-target", "3-sisterless on-target",
         "off-target control", "unmodified"]
print("PART A — annotation coverage, cells with ANY row in the store / cells in that class\n")
print(f"{'store':30s}" + "".join(f"{k[:18]:>20s}" for k in order))
rowsA = []
for name in STORES:
    line = f"{name:30s}"
    for k in order:
        n = len(pool[k] & have[name]); d = len(pool[k])
        line += f"{n:>8d}/{d:<4d}{100*n/max(d,1):>6.0f}%"
        rowsA.append(dict(kind="coverage", store=name, cohort=k, have=n, eligible=d,
                          pct=round(100*n/max(d,1), 1)))
    print(line)

DECKS = ["META_FIGURES_20260814.ai", "META_FIGURES_20260813_supplemental.ai",
         "NEW_FIGURES_20260804.ai", "supplemental.ai", "NEW_TIMESTRIPS_20260804.ai"]
placed = set()
for d in DECKS:
    txt = subprocess.run(["strings", f"{ROOT}/1_DECKS/{d}"], capture_output=True, text=True).stdout
    placed |= set(re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", txt))
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))

figs = []
for pid in sorted(placed):
    p = f"{DATA}/{pid}.csv"
    if not os.path.exists(p): continue
    rows = rd(p)
    if not rows: 
        figs.append(dict(plot=pid, n_rows=0, n_cells=0, sources="")); continue
    bcol = next((c for c in rows[0] if c and c.strip().lower() in ("batch", "batch_name", "cell")), None)
    if not bcol:
        # An AGGREGATE figure (one row per cohort / per comparison) has no cell column at all.  Counting
        # its cells as 0 and calling it "thin" was wrong -- it is a different KIND of figure, so say so.
        figs.append(dict(plot=pid, n_rows=len(rows), n_cells=None, sources=""))
        continue
    cells = len({(r.get(bcol) or "").strip() for r in rows if (r.get(bcol) or "").strip()})
    src = (ps.get(pid) or {}).get("source") or ""
    if isinstance(src, list): src = ";".join(os.path.basename(str(s)) for s in src[:3])
    figs.append(dict(plot=pid, n_rows=len(rows), n_cells=cells, sources=str(src)[:70]))
percell = [f for f in figs if f["n_cells"] is not None]
aggregate = [f for f in figs if f["n_cells"] is None]
percell.sort(key=lambda f: (f["n_cells"], f["n_rows"]))
figs = percell + aggregate
thin = [f for f in percell if f["n_cells"] <= 8]
print(f"\nPART B — of {len(percell)} placed per-cell figures, {len(thin)} rest on <= 8 cells "
      f"({len(aggregate)} more are aggregate figures with no cell column)\n")
print(f"{'figure':56s} cells rows  sources")
for f in thin[:40]:
    print(f"{f['plot'][:55]:56s} {f['n_cells']:5d} {f['n_rows']:5d}  {f['sources'][:52]}")
for f in figs:
    rowsA.append(dict(kind="figure", store=f["sources"], cohort=f["plot"],
                      have=("aggregate" if f["n_cells"] is None else f["n_cells"]),
                      eligible=f["n_rows"], pct=""))
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["kind", "store", "cohort", "have", "eligible", "pct"])
    w.writeheader(); w.writerows(rowsA)
print(f"\n[done] -> {OUT}")
