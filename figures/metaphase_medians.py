#!/usr/bin/env python3
"""ONE canonical source for each group's MEDIAN METAPHASE DURATION.

USER 2026-08-19 (to-do list 0819 1pm, figure item 5):
    "lines dont mark horizontal median lines for groups at correct time (it seems it marks the median
     time for the samples used to build the actual line, and thats not what i want. I want the median
     from the main violin plot on the second art board.)"

THE MAIN VIOLIN PLOT ON ARTBOARD 2 of META_FIGURES_20260814.ai is `G1_violin2_no_dc_offtarget_journal`
(confirmed against the deck's own placed-figure index). Its recorded data CSV -- one row per CELL,
`batch, cohort, metaphase_duration_min` -- is therefore the authority for every group median line drawn
on any other figure.

WHY THIS FILE EXISTS RATHER THAN A LITERAL IN EACH BUILDER
    `group1_roundness.combined()` used `np.median(anaxs)` -- the median anaphase time of exactly those
    cells that happened to have a cell-outline / plate / centroid trace inside that one plot's window.
    That is a DIFFERENT and smaller set of cells than the violin plot's, so the same group's dashed line
    sat at a different time on every figure. Recomputing it per figure is the bug; importing it is the fix.

GROUPING matches `group1_roundness.FAM` exactly, so the marker lines up with the trend line it belongs to:
    * collagen cells are split out FIRST, by batch name (`"collagen" in batch.lower()`) -- same test as
      group1_roundness.py line 42 -- because a collagen cell is also a 2-/3-sisterless cell and would
      otherwise be counted twice.
    * the three off-target control cohorts are POOLED into one group (user 2026-08-19 figure item 6:
      "1,2,and 3 off-target groups arent plotted as a single group in the plots above as they should be").
    * 2-Sisterless is absent by design (removed from this plot family 2026-08-16).
"""
import collections
import csv
import os
import statistics

VIOLIN = "/Volumes/4 MB/ablation_plots/data/G1_violin2_no_dc_offtarget_journal.csv"
COLLAGEN_KEY = "Collagen (2/3-sis on-target)"
CTRL = {"1-Sister Controls", "2-Sister Controls", "3-Sister Controls"}

# cohort in the violin CSV -> FAM title used by the line plots
_FAM_OF = {
    "1-Sister": "1-Sisterless",
    "3-Sister": "3-Sisterless",
    "unModified": "unmodified",
}
OFFTARGET_KEY = "off-target (1/3)"


def _load(path=VIOLIN):
    if not os.path.exists(path):
        return {}
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(path, newline="", encoding="utf-8", errors="replace")):
        b = (r.get("batch") or "").strip()
        c = (r.get("cohort") or "").strip()
        try:
            v = float(r["metaphase_duration_min"])
        except Exception:
            continue
        if "collagen" in b.lower():          # collagen split FIRST -- it overlaps the sisterless cohorts
            per[COLLAGEN_KEY].append(v)
        elif c in CTRL:                      # 1 + 2 + 3 off-target pooled into ONE group
            per[OFFTARGET_KEY].append(v)
        elif c in _FAM_OF:
            per[_FAM_OF[c]].append(v)
    return per


def medians(path=VIOLIN):
    """{FAM title -> median metaphase duration in MINUTES}. Empty dict if the violin CSV is missing."""
    return {k: float(statistics.median(v)) for k, v in _load(path).items() if v}


def counts(path=VIOLIN):
    """{FAM title -> number of CELLS behind that median} -- for captions and for the slope table."""
    return {k: len(v) for k, v in _load(path).items() if v}


def medians_pooled_collagen_vs_rest(path=VIOLIN):
    """The same violin data pooled the TWO ways `group1_roundness.collagen_vs_pooled` draws it.
    Keys are that figure's own series labels so the caller can look them up directly."""
    per = _load(path)
    coll = list(per.get(COLLAGEN_KEY, []))
    rest = [v for k, vs in per.items() if k != COLLAGEN_KEY for v in vs]
    out = {}
    if coll: out["collagen"] = float(statistics.median(coll))
    if rest: out["all other groups pooled"] = float(statistics.median(rest))
    return out


def median_for(fam_title, path=VIOLIN):
    return medians(path).get(fam_title)


if __name__ == "__main__":
    m, n = medians(), counts()
    print(f"group medians from {os.path.basename(VIOLIN)} (metaphase duration, min):")
    for k in sorted(m):
        print(f"  {k:32s} n={n[k]:4d}  median={m[k]:6.2f}")
