#!/usr/bin/env python3
"""PSEUDOREPLICATION SCAN -- does each figure's significance survive testing PER CELL?

HER RULE (NOTES 2026-08-18, item 20): "Any test over these stores must aggregate to the cell first."
A cell contributes many kinetochores, tracks and frames; a test run over rows counts one cell many
times, which manufactures significance.  This scan repeats every group x metric comparison on the
recorded data of every figure placed on a LIVE deck, first per ROW (as the builder does) and then
per CELL (one median per batch per group), and reports the ones that disagree.

  python3 dataops/pseudoreplication_scan_20260818.py            # scan, write CSV + JSON
"""
import csv, json, os, re, subprocess, itertools, collections
import numpy as np
from scipy import stats

ROOT = "/Volumes/4 MB"
DATA = os.path.join(ROOT, "ablation_plots/data")
DECKS = [  # the five LIVE decks (NOTES 2026-08-18 / handoff-13)
    "1_DECKS/META_FIGURES_20260814.ai", "1_DECKS/META_FIGURES_20260813_supplemental.ai",
    "1_DECKS/NEW_FIGURES_20260804.ai", "1_DECKS/other_20260820.ai",
    "1_DECKS/NEW_TIMESTRIPS_20260804.ai",
]
OUT_CSV = os.path.join(ROOT, "4_TABLES_AND_REPORTS", "PSEUDOREPLICATION_SCAN_20260818.csv")
OUT_JSON = os.path.join(ROOT, "_claude_tmp", "rederive_20260818", "pseudo_scan.json")
csv.field_size_limit(10 ** 9)

ps = json.load(open(os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json")))
placed = set()
for d in DECKS:
    out = subprocess.run(["strings", os.path.join(ROOT, d)], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", out):
        placed.add(m)

SKIP_NAME = ("statgrid", "sanitycheck", "contactsheet", "candidates", "timestrip", "filmstrip")
GROUPY = {"cohort", "group", "phase", "series", "location", "marker", "kt_type", "label",
          "sisterless_group", "panel", "fate", "role", "state", "behavior", "behaviour", "class",
          "n_sisterless", "arm", "condition"}
IDISH = re.compile(r"^(batch|track|id|ann_id|kt|chromosome|seq|frap_seq|abl_seq|n$|n_|frame|tif_pos)")
BATCHY = ("batch", "batch_name", "cell", "batch name")

def numeric(vals):
    out = []
    for v in vals:
        try: out.append(float(v))
        except (TypeError, ValueError): out.append(np.nan)
    return np.array(out, float)

def test(groups):
    groups = [g for g in groups if len(g) >= 4]
    if len(groups) < 2: return None, None, None
    try:
        if len(groups) == 2:
            _, pv = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
            return "Mann-Whitney", float(pv), [len(g) for g in groups]
        _, pv = stats.kruskal(*groups)
        return "Kruskal", float(pv), [len(g) for g in groups]
    except Exception:
        return None, None, None

rows_out = []
scanned = noBatch = 0
for pid in sorted(placed):
    e = ps.get(pid) or {}
    if str(e.get("retired")) == "True": continue
    if any(s in pid.lower() for s in SKIP_NAME): continue
    p = os.path.join(DATA, pid + ".csv")
    if not os.path.isfile(p): continue
    try:
        rows = list(csv.reader(open(p, encoding="utf-8", errors="replace")))
    except Exception:
        continue
    if len(rows) < 8: continue
    hdr, body = rows[0], rows[1:]
    cols = {c: [r[i] if i < len(r) else "" for r in body] for i, c in enumerate(hdr) if c}
    bcol = next((c for c in cols if c.strip().lower() in BATCHY), None)
    if not bcol:
        noBatch += 1; continue
    batches = np.array(cols[bcol])
    if len(set(batches)) < 4:      # too few cells to test per cell at all
        continue
    scanned += 1
    nums = {}
    for c, v in cols.items():
        if IDISH.match(c.lower()): continue
        a = numeric(v)
        if np.isfinite(a).sum() >= max(6, .5 * len(a)) and len(set(a[np.isfinite(a)])) > 2:
            nums[c] = a
    for gc in [c for c in cols if c.lower() in GROUPY]:
        labs = np.array(cols[gc])
        levels = [u for u in sorted(set(labs)) if u != ""]
        if not (2 <= len(levels) <= 6): continue
        for mc, a in nums.items():
            if mc == gc: continue
            grp_row, grp_cell = [], []
            for u in levels:
                m = (labs == u) & np.isfinite(a)
                grp_row.append(a[m])
                per = collections.defaultdict(list)
                for b, v in zip(batches[m], a[m]): per[b].append(v)
                grp_cell.append(np.array([np.median(v) for v in per.values()], float))
            k1, p1, n1 = test(grp_row)
            k2, p2, n2 = test(grp_cell)
            if p1 is None or p2 is None: continue
            verdict = ("LOSES per cell" if (p1 < .05 <= p2) else
                       "gains per cell" if (p2 < .05 <= p1) else
                       "survives" if p1 < .05 else "ns both")
            if verdict == "ns both": continue
            rows_out.append(dict(plot=pid, group_col=gc, metric=mc, test=k1,
                                 n_rows=sum(n1), n_cells=sum(n2), groups_rows=";".join(map(str, n1)),
                                 groups_cells=";".join(map(str, n2)),
                                 p_per_row=round(p1, 8), p_per_cell=round(p2, 8), verdict=verdict,
                                 builder=(e.get("code") or "")))

order = {"LOSES per cell": 0, "gains per cell": 1, "survives": 2}
rows_out.sort(key=lambda r: (order[r["verdict"]], r["p_per_row"]))
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)
json.dump(rows_out, open(OUT_JSON, "w"), indent=1)
n_lose = sum(1 for r in rows_out if r["verdict"] == "LOSES per cell")
n_surv = sum(1 for r in rows_out if r["verdict"] == "survives")
n_gain = sum(1 for r in rows_out if r["verdict"] == "gains per cell")
print(f"placed figures with data: {scanned}  (no batch column: {noBatch})")
print(f"comparisons: LOSES per cell={n_lose}  survives={n_surv}  gains per cell={n_gain}")
print(f"\n--- LOSES SIGNIFICANCE WHEN TESTED PER CELL (top 40) ---")
for r in rows_out[:40]:
    if r["verdict"] != "LOSES per cell": break
    print(f"  {r['plot'][:46]:48s} {r['group_col'][:12]:13s} x {r['metric'][:26]:27s} "
          f"row p={r['p_per_row']:.4g} ({r['n_rows']:5d}) -> cell p={r['p_per_cell']:.3g} ({r['n_cells']})")
print(f"\n[done] -> {OUT_CSV}")
