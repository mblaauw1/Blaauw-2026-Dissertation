#!/usr/bin/env python3
"""Re-derive the statistics quoted in a deliverable document from the figure's own data CSV.

WHY THIS EXISTS: on 2026-08-20 the quartile answer in `ANSWERS_20260819b.md` still read "p=0.045, n=28"
after the underlying data had improved TWICE -- first when a needless metaphase-plate requirement was
removed, then when a congression double-count was fixed and plates were reconstructed from her sister-pair
annotations. The figure was right and the prose was stale, which is the failure mode she has now caught
more than once: a number typed into text does not move when the data does.

It checks the CLAIM AGAINST THE DATA, not against another document -- NOTES 2026-08-19d records the
opposite mistake, a checker that agreed with a superseded claim because both halves were stale together.

    python3 dataops/verify_doc_numbers_20260820.py
"""
import collections
import csv
import io
import os
import re
import sys

import numpy as np
from scipy import stats

DATA = "/Volumes/4 MB/ablation_plots/data"
DOC = "/Volumes/4 MB/4_TABLES_AND_REPORTS/ANSWERS_20260819b.md"


def quartile_truth():
    """(cell type, from, to) -> (median_before, median_after, p, n) straight from the plot CSV."""
    p = f"{DATA}/G10_osc_quartile_profile.csv"
    if not os.path.exists(p):
        return {}
    d = collections.defaultdict(dict)
    for r in csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")):
        d[(r["batch"], r["track_id"], r["n_sisterless"])][int(r["quarter"])] = float(r["amp_um"])
    out = {}
    for g in ("1", "3"):
        v = [q for (_b, _t, n), q in d.items() if n == g]
        for a, b in ((1, 2), (2, 3), (3, 4), (1, 4)):
            pk = [(x[a], x[b]) for x in v if a in x and b in x]
            if len(pk) < 5:
                continue
            A = [x[0] for x in pk]; B = [x[1] for x in pk]
            out[(g, a, b)] = (float(np.median(A)), float(np.median(B)),
                              float(stats.wilcoxon(A, B).pvalue), len(pk))
    return out


def main():
    truth = quartile_truth()
    if not truth:
        print("no quartile data CSV -- cannot verify"); return 1
    txt = io.open(DOC, encoding="utf-8").read()
    bad = 0
    # every "p=<x>, n=<k>" pair quoted anywhere in the document must exist in the data
    quoted = re.findall(r"p=([0-9.]+(?:e-?\d+)?), n=(\d+)", txt)
    have = {(f"{p:.3g}", str(n)) for _a, _b, p, n in truth.values()}
    print(f"{len(quoted)} (p, n) pairs quoted in {os.path.basename(DOC)}; {len(truth)} available in the data")
    for p, n in quoted:
        if (p, n) not in have:
            bad += 1
            print(f"   STALE: the document quotes p={p}, n={n}, which the current data does not produce")
    for (g, a, b), (m1, m2, p, n) in sorted(truth.items()):
        print(f"   data: {g}-sis Q{a}->Q{b}  {m1:.2f} -> {m2:.2f}  p={p:.3g}  n={n}")
    print("\nOK -- every quoted statistic is reproduced by the data." if not bad
          else f"\n{bad} QUOTED STATISTIC(S) NO LONGER MATCH THE DATA -- regenerate that section.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
