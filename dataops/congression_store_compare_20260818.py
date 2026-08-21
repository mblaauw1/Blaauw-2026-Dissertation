#!/usr/bin/env python3
"""Are `CHROMOSOME_MASTER` congression times and `SISTERLESS_PLATE_JOIN_TIMES` the same measurement?

HER QUESTION (2026-08-18): "the annotations table lists separately 'Per-chromosome congression time +
behaviour' and 'Per-chromosome plate-join time'. Assess if these annotation types are truly different, and
do they cover different batches, which would ultimately cause incomplete data on plots of chromosome
localization?"

Compares them cell by cell and chromosome by chromosome: coverage, overlap, and — where both hold a time
for the same chromosome — whether the two times agree.
"""
import csv, io, os, sys, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/4_TABLES_AND_REPORTS/CONGRESSION_STORE_COMPARE_20260818.csv"

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))
def fl(x, d=None):
    try:
        s = str(x).strip(); return float(s) if s not in ("", "None", "nan", "n/a") else d
    except Exception: return d
def hms(v):
    s = str(v or "").strip()
    if not s or s.lower() in ("n/a", "na", "-", "0"): return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try:
        if ":" in s:
            p = [float(x or 0) for x in s.split(":")]
            while len(p) < 3: p.insert(0, 0)
            sec = p[0]*3600 + p[1]*60 + p[2]
        else: sec = float(s)
    except ValueError: return None
    return -sec if neg else sec

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}

cm = collections.defaultdict(dict)     # batch -> chr_num -> time_s
cmb = collections.defaultdict(dict)    # batch -> chr_num -> behaviour
for r in rd(A + "CHROMOSOME_MASTER.csv"):
    b = (r.get("batch") or "").strip(); c = (r.get("chr_num") or "").strip()
    if not b or not c: continue
    t = fl(r.get("congression_time_s"))
    if t is None: t = hms(r.get("congression_hms"))
    if t is not None: cm[b][c] = t
    if (r.get("behavior") or "").strip(): cmb[b][c] = (r.get("behavior") or "").strip()

sp = collections.defaultdict(dict)
for r in rd(A + "SISTERLESS_PLATE_JOIN_TIMES.csv"):
    b = (r.get("batch") or "").strip()
    if not b: continue
    for i in (1, 2, 3):
        t = fl(r.get(f"chromosome_{i}_plate_join_s"))
        if t is None: t = hms(r.get(f"chromosome_{i}_plate_join"))
        if t is not None: sp[b][str(i)] = t

bc, bs = set(cm), set(sp)
both = bc & bs
print(f"cells with a congression TIME in CHROMOSOME_MASTER : {len(bc)}")
print(f"cells with a plate-join TIME in SISTERLESS_PLATE_JOIN: {len(bs)}")
print(f"   in BOTH: {len(both)}   only CHROMOSOME_MASTER: {len(bc-bs)}   only PLATE_JOIN: {len(bs-bc)}")
print(f"   UNION (cells with a time from either): {len(bc | bs)}")

agree = dis = 0; deltas = []
rows = []
for b in sorted(bc | bs):
    for c in sorted(set(cm.get(b, {})) | set(sp.get(b, {}))):
        t1, t2 = cm.get(b, {}).get(c), sp.get(b, {}).get(c)
        d = (t2 - t1) if (t1 is not None and t2 is not None) else None
        if d is not None:
            deltas.append(d)
            if abs(d) <= 60: agree += 1
            else: dis += 1
        rows.append(dict(batch=b, chr_num=c, chromosome_master_s=t1, plate_join_s=t2,
                         delta_s=(round(d, 1) if d is not None else ""),
                         behaviour=cmb.get(b, {}).get(c, ""),
                         only_in=("both" if (t1 is not None and t2 is not None) else
                                  "CHROMOSOME_MASTER" if t1 is not None else "SISTERLESS_PLATE_JOIN")))
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

import statistics
if deltas:
    print(f"\nchromosomes with a time in BOTH stores: {len(deltas)}")
    print(f"   agree within 60 s: {agree}   differ by more: {dis}")
    print(f"   median |difference|: {statistics.median(abs(x) for x in deltas):.0f} s")
print(f"\nrows written: {len(rows)}  ->  {OUT}")

# who reads which store?
import subprocess
for store in ("CHROMOSOME_MASTER", "SISTERLESS_PLATE_JOIN_TIMES"):
    out = subprocess.run(["grep", "-rl", store, "--include=*.py",
                          "/Volumes/4 MB/ablation_figures_20260625", "/Volumes/4 MB/dataops"],
                         capture_output=True, text=True).stdout.split()
    live = [os.path.basename(x) for x in out if ".bak" not in x and "/code/" not in x and "backup" not in x]
    print(f"\nbuilders reading {store}: {len(live)}")
    for x in sorted(set(live))[:10]: print("   ", x)
