#!/usr/bin/env python3
"""For a figure, say EXACTLY which cells reached it and which did not, and why — one line per cell.

WHY THIS EXISTS. Her single most repeated complaint is that a figure's n is smaller than the data she
annotated: *"the n for triple ablation for most of the plots is 18. It should be far more and i know i
thoroughly annotated all batches that are relevant"*, *"n for 1-sisterless is 21, but there are 30-something
1-sisterless batches"*, *"there is more than 11kts to include here"*, *"i am certain you are not plotting the
full set of appropriate data"*. Every time, I have answered by guessing at one filter. This answers it by
walking the actual funnel and naming the cells that fall out at each stage, so the reply is a list she can
check rather than a claim she has to trust.

It has already found one real bug this way (a needless metaphase-plate requirement on figures that never
used the plate, which had cut the lagging group from 7 kinetochores to 3).

    python3 dataops/why_is_n_20260820.py <figure-id> [--group 3-Sisterless]
    python3 dataops/why_is_n_20260820.py --cohort 3          # every cell of that sisterless count
"""
import collections
import csv
import glob
import os
import sys

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import osclib

ANN = "/Volumes/4 MB/annotations"
DATA = "/Volumes/4 MB/ablation_plots/data"


def master():
    d, _ = lib.load_master()
    return {r["Batch Name"]: r for r in d}


def store_counts(store, label=None):
    c = collections.Counter()
    p = f"{ANN}/{store}"
    if not os.path.exists(p):
        return c
    for r in csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")):
        if label and (r.get("label") or "").strip() != label:
            continue
        c[r.get("batch")] += 1
    return c


def in_metaphase(store, label=None):
    """batch -> how many rows of that store fall inside the cell's metaphase window."""
    c = collections.Counter()
    p = f"{ANN}/{store}"
    if not os.path.exists(p):
        return c
    win = {}
    for r in csv.DictReader(open(p, newline="", encoding="utf-8", errors="replace")):
        if label and (r.get("label") or "").strip() != label:
            continue
        b = r.get("batch")
        if b not in win:
            win[b] = osclib.metaphase_window(b)
        w = win[b]
        if not w:
            continue
        try:
            t = float(r["t_sec"])
        except Exception:
            continue
        if w[0] <= t <= w[1]:
            c[b] += 1
    return c


def why_out(b, MR):
    """The FIRST standing reason this cell is not plotted, in the order the rules are applied."""
    r = MR.get(b, {})
    if (r.get("Exclude", "") or "").strip().lower() in ("yes", "true", "1"):
        return f"master Exclude=Yes ({(r.get('Exclude Reason','') or '').strip()[:40]})"
    for name, fn in (("drug-treated", lib.is_drug), ("review-excluded", lib.excluded),
                     ("metaphase ablation", lib.is_metaphase_ablation),
                     ("prophase ablation", lib.is_prophase_ablation),
                     ("4-sisterless", lib.is_four_sisterless)):
        try:
            if fn(b):
                return name
        except Exception:
            pass
    if not osclib.metaphase_window(b):
        return "no metaphase window in the master (Metaphase Start / Anaphase Onset missing)"
    return None


def report(cohort, store, label, min_rows):
    MR = master()
    cells = [b for b in MR if (MR[b].get("# Sisterless KTs", "") or "").strip() == str(cohort)]
    have = store_counts(store, label)
    meta = in_metaphase(store, label)
    print(f"\n{len(cells)} cells with '# Sisterless KTs' = {cohort} in the master")
    print(f"source store: {store}" + (f" (label={label})" if label else ""))
    print(f"{'cell':50s} {'rows':>5s} {'in meta':>7s}  status")
    IN = OUT = 0
    reasons = collections.Counter()
    for b in sorted(cells):
        n, m = have.get(b, 0), meta.get(b, 0)
        why = why_out(b, MR)
        # EXCLUSION IS CHECKED FIRST. A drug-treated or metaphase-ablation cell is not expected to carry
        # annotations at all, so reporting it as "not annotated" made the annotation gap look far larger
        # than it is -- ten ZM cells were listed as missing marks when they are simply out of cohort.
        if why:
            st = f"excluded: {why}"
        elif not n:
            st = "NOT ANNOTATED in this store"
        elif m < min_rows:
            st = f"only {m} row(s) inside metaphase (needs {min_rows})"
        else:
            st = "IN"
        if st == "IN":
            IN += 1
        else:
            OUT += 1
            reasons["excluded (standing rule)" if st.startswith("excluded")
                    else ("not annotated" if st.startswith("NOT") else "too few metaphase rows")] += 1
        print(f"{b[:50]:50s} {n:5d} {m:7d}  {st}")
    print(f"\nIN {IN}   OUT {OUT}")
    print("   " + "   ".join(f"{k}={v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    print("A cell marked NOT ANNOTATED needs the mark drawn; one marked 'excluded' is a standing rule she set;")
    print("one with too few metaphase rows needs more timepoints annotated inside metaphase, not a code change.")


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    if a[0] == "--cohort":
        cohort = a[1] if len(a) > 1 else "3"
        store = "cell_outlines.csv"
        label = None
        for i, x in enumerate(a):
            if x == "--store":
                store = a[i + 1]
            if x == "--label":
                label = a[i + 1]
        mr = 2
        for i, x in enumerate(a):
            if x == "--min":
                mr = int(a[i + 1])
        report(cohort, store, label, mr)
        return
    print("use --cohort N [--store kt_outlines.csv] [--label polar] [--min 2]")


if __name__ == "__main__":
    main()
