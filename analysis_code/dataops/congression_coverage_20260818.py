#!/usr/bin/env python3
"""CELL-BY-CELL congression coverage for the base cohort.

HER QUESTION (2026-08-18): "circle back to how claude said only 31% of cells had annotation for time of
chromosome congression to plate ... I'm still confident that all cells in the base sets of cdc20
nondrugged 1 and 3 on-target ablations have this info."

The 31% was one store read alone; the 84% figure counted structured stores.  This lists EVERY cell in the
cohort and EVERY store that holds congression information for it, so a gap is a named cell, not a percent.

Stores checked, in order of authority (structured table beats prose -- NOTES 2026-08-14):
  1 CHROMOSOME_MASTER.csv            congression_time_s (a TIME) / behavior (an OUTCOME)
  2 SISTERLESS_PLATE_JOIN_TIMES.csv  chromosome_N_plate_join(_s)
  3 PREABL_CHROMOSOME_ASSIGNMENT.csv behavior per ablation attempt
  4 CHROMO_LENGTH_BEHAVIOR_PAIRING   chrN_movement (free text from the 8781 pairing tool)
  5 master Notes / batch_meta notes  her prose (weakest; parsed, never authoritative)

  python3 dataops/congression_coverage_20260818.py
"""
import csv, io, os, re, sys, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/4_TABLES_AND_REPORTS/CONGRESSION_COVERAGE_20260818.csv"

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))

def fl(x, d=None):
    try:
        s = str(x).strip()
        return float(s) if s not in ("", "None", "nan") else d
    except Exception: return d

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}

# ---------------------------------------------------------------- cohort (same test as the model)
cohort = []
for b, r in MB.items():
    if lib.plot_excluded(b): continue                                   # excludes drugs + metaphase + 4-sis
    if (r.get("On-Target / Off-Target", "") or "").strip().lower().startswith("off"): continue
    n = fl(r.get("# Sisterless KTs"))
    if n is None or int(n) not in (1, 3): continue
    ct = (r.get("Cell Type") or "").strip().lower()
    if "cdc20" not in ct: continue                                       # her wording: cdc20 cells
    cohort.append((b, int(n), r))
cohort.sort()

CM  = collections.defaultdict(list)
for r in rd(A + "CHROMOSOME_MASTER.csv"): CM[(r.get("batch") or "").strip()].append(r)
SPJ = {(r.get("batch") or "").strip(): r for r in rd(A + "SISTERLESS_PLATE_JOIN_TIMES.csv")}
PRE = collections.defaultdict(list)
for r in rd(A + "PREABL_CHROMOSOME_ASSIGNMENT.csv"): PRE[(r.get("batch") or "").strip()].append(r)
PAIR = {(r.get("batch") or "").strip(): r for r in rd(A + "CHROMO_LENGTH_BEHAVIOR_PAIRING.csv")}
BMETA = collections.defaultdict(list)
for r in rd(A + "batch_meta.csv"): BMETA[(r.get("batch") or "").strip()].append(r)

BEH = re.compile(r"congress|plate|polar|at pole|never|align|join", re.I)

rows, gaps = [], []
for b, n, r in cohort:
    cm = CM.get(b, [])
    cm_time = sum(1 for x in cm if fl(x.get("congression_time_s")) is not None)
    cm_beh  = sum(1 for x in cm if (x.get("behavior") or "").strip())
    spj = SPJ.get(b)
    spj_n = 0
    if spj:
        for i in (1, 2, 3):
            v = (spj.get(f"chromosome_{i}_plate_join") or "").strip()
            s = fl(spj.get(f"chromosome_{i}_plate_join_s"))
            if (v and v.lower() not in ("n/a", "na", "-")) or s is not None: spj_n += 1
    pre_beh = sum(1 for x in PRE.get(b, []) if (x.get("behavior") or "").strip())
    pr = PAIR.get(b)
    pair_mv = sum(1 for i in (1, 2, 3) if pr and (pr.get(f"chr{i}_movement") or "").strip()) if pr else 0
    notes = " ".join([(r.get("Notes") or "")] + [(x.get("notes") or "") + (x.get("label") or "")
                                                 for x in BMETA.get(b, [])])
    prose = bool(BEH.search(notes))

    any_time = (cm_time > 0) or (spj_n > 0)
    any_info = any_time or cm_beh > 0 or pre_beh > 0 or pair_mv > 0 or prose
    best = ("CHROMOSOME_MASTER time" if cm_time else
            "SISTERLESS_PLATE_JOIN time" if spj_n else
            "CHROMOSOME_MASTER behavior" if cm_beh else
            "PREABL behavior" if pre_beh else
            "pairing chrN_movement" if pair_mv else
            "prose only" if prose else "NONE")
    rows.append(dict(batch=b, n_sisterless=n, cell_type=(r.get("Cell Type") or "").strip(),
                     chromosome_master_rows=len(cm), cm_congression_times=cm_time, cm_behaviors=cm_beh,
                     plate_join_entries=spj_n, preabl_behaviors=pre_beh, pairing_movements=pair_mv,
                     prose_mentions=int(prose), has_any_congression_info=int(any_info),
                     has_a_congression_TIME=int(any_time), best_source=best))
    if not any_info: gaps.append((b, n))

tot = len(rows)
anyi = sum(r["has_any_congression_info"] for r in rows)
anyt = sum(r["has_a_congression_TIME"] for r in rows)
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print(f"cohort: cdc20, non-drug, on-target, 1- or 3-sisterless, not excluded  ->  {tot} cells "
      f"(1-sis {sum(1 for r in rows if r['n_sisterless']==1)}, 3-sis {sum(1 for r in rows if r['n_sisterless']==3)})")
print(f"  ANY congression information : {anyi}/{tot} = {100*anyi/tot:.1f}%")
print(f"  a congression TIME          : {anyt}/{tot} = {100*anyt/tot:.1f}%")
src = collections.Counter(r["best_source"] for r in rows)
print("\n  best source per cell:")
for k, v in src.most_common(): print(f"    {k:32s} {v}")
if gaps:
    print(f"\n  CELLS WITH NO CONGRESSION INFORMATION IN ANY STORE ({len(gaps)}):")
    for b, n in gaps: print(f"    [{n}-sis] {b}")
notime = [r for r in rows if r["has_any_congression_info"] and not r["has_a_congression_TIME"]]
if notime:
    print(f"\n  HAVE AN OUTCOME BUT NO TIME ({len(notime)}) -- these are the ones to annotate for timing:")
    for r in notime: print(f"    [{r['n_sisterless']}-sis] {r['batch']}   ({r['best_source']})")
print(f"\n[done] -> {OUT}")
