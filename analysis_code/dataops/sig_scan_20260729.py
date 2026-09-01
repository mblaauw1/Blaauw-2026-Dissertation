#!/usr/bin/env python3
"""Rebuild the significance list that drives the yellow SIG_HIGHLIGHT rects on copy.ai.

WHY: the curated list (_sig_highlight_list_v2.json) is gone from 4 MB, and 162 placed figures from
families added after the 2026-07-20 scan (G5shape_*, G6*, QNEW/RNEW, MAD1kt_*) were never tested - so
the yellow highlights only reflect the pre-07-20 deck.

METHOD (from memory/feedback_copyai_significance_highlights, user 2026-07-20 "there should be more
than 29"): for EVERY placed live figure's recorded data CSV, test
    * Mann-Whitney / Kruskal on EVERY grouping column x EVERY numeric metric
    * Spearman on EVERY numeric column pair
and flag p<0.05. Then strip non-findings:
    * statgrid / sanitycheck figures (they are diagnostics, not results)
    * |rho| >= 0.95, and known MECHANICAL pairs (mean~sum, n_x~n_y, duration~abl_to_ana,
      major~area, length~aspect) - a correlation that is true by construction is not a finding
    * retired figures are never highlighted
Records WHICH test fired, so a highlight can be justified rather than trusted.

  python3 sig_scan_20260729.py            # scan + write the list
"""
import csv, json, os, re, subprocess, itertools, collections
import numpy as np
from scipy import stats

ROOT = "/Volumes/4 MB"
DATA = os.path.join(ROOT, "ablation_plots/data")
OUT = os.path.join(ROOT, "_sig_highlight_list_20260729.json")
csv.field_size_limit(10 ** 9)

ps = json.load(open(os.path.join(ROOT, "ablation_plots/PLOT_SETTINGS.json")))
placed = set()
for d in ["ablation_plots/_superseded_decks/ablation_figures_grouped copy.ai",
          "ablation_plots/_superseded_decks/ablation_figures_kinetochore_overflow.ai"]:
    out = subprocess.run(["strings", os.path.join(ROOT, d)], capture_output=True, text=True).stdout
    for m in re.findall(r"([A-Za-z0-9_.\-]+)\.(?:pdf|png)", out):
        placed.add(m)

SKIP_NAME = ("statgrid", "sanitycheck", "contactsheet", "candidates", "timestrip", "filmstrip")
GROUPY = {"cohort", "group", "phase", "series", "location", "marker", "kt_type", "label",
          "sisterless_group", "panel", "fate", "role", "state", "behavior", "behaviour", "class"}
IDISH = re.compile(r"^(batch|track|id|ann_id|kt|chromosome|seq|frap_seq|abl_seq|n$|n_|frame|tif_pos)")
# pairs whose correlation is true by construction, not a finding
MECH = [("mean", "sum"), ("major", "area"), ("length", "aspect"), ("duration", "abl_to_ana"),
        ("area", "perimeter"), ("major", "minor"), ("n_", "n_"), ("area", "eq_diam"),
        ("aspect", "elong"), ("major", "eq_diam"), ("circular", "solid")]


def mechanical(a, b):
    a, b = a.lower(), b.lower()
    for u, v in MECH:
        if (u in a and v in b) or (u in b and v in a):
            return True
    return False


def numeric(vals):
    out = []
    for v in vals:
        try:
            f = float(v)
        except (TypeError, ValueError):
            out.append(np.nan); continue
        out.append(f)
    return np.array(out, float)


hits = {}
scanned = skipped = 0
for pid in sorted(placed):
    e = ps.get(pid) or {}
    if str(e.get("retired")) == "True":
        continue
    if any(s in pid.lower() for s in SKIP_NAME):
        continue
    p = os.path.join(DATA, pid + ".csv")
    if not os.path.isfile(p):
        skipped += 1; continue
    try:
        rows = list(csv.reader(open(p)))
    except Exception:
        skipped += 1; continue
    if len(rows) < 8:
        continue
    hdr, body = rows[0], rows[1:]
    scanned += 1
    cols = {c: [r[i] if i < len(r) else "" for r in body] for i, c in enumerate(hdr)}
    nums = {}
    for c, v in cols.items():
        if IDISH.match(c.lower()):
            continue
        a = numeric(v)
        if np.isfinite(a).sum() >= max(6, 0.5 * len(a)) and len(set(a[np.isfinite(a)])) > 2:
            nums[c] = a
    found = []
    # grouping x metric
    for gc in [c for c in cols if c.lower() in GROUPY]:
        labs = np.array(cols[gc])
        for mc, a in nums.items():
            if mc == gc:
                continue
            groups = [a[(labs == u) & np.isfinite(a)] for u in sorted(set(labs)) if u != ""]
            groups = [g for g in groups if len(g) >= 4]
            if len(groups) < 2:
                continue
            try:
                if len(groups) == 2:
                    st, pv = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
                    kind = "Mann-Whitney"
                else:
                    st, pv = stats.kruskal(*groups)
                    kind = "Kruskal"
            except Exception:
                continue
            if pv < 0.05:
                found.append({"test": kind, "by": gc, "metric": mc, "p": float(pv),
                              "n_groups": len(groups)})
    # numeric pairs
    keys = sorted(nums)
    for c1, c2 in itertools.combinations(keys, 2):
        if mechanical(c1, c2):
            continue
        a, b = nums[c1], nums[c2]
        m = np.isfinite(a) & np.isfinite(b)
        if m.sum() < 8:
            continue
        try:
            rho, pv = stats.spearmanr(a[m], b[m])
        except Exception:
            continue
        if not np.isfinite(rho) or abs(rho) >= 0.95:
            continue
        if pv < 0.05:
            found.append({"test": "Spearman", "x": c1, "y": c2, "rho": round(float(rho), 3),
                          "p": float(pv), "n": int(m.sum())})
    if found:
        found.sort(key=lambda f: f["p"])
        hits[pid] = found[:6]

json.dump(hits, open(OUT, "w"), indent=1)
print("figures scanned: %d   (no data CSV: %d)" % (scanned, skipped))
print("figures with at least one significant test: %d" % len(hits))
def _fam(k):
    m = re.match(r"([A-Za-z]+[0-9]*)", k)
    return m.group(1) if m else "other"
fam = collections.Counter(_fam(k) for k in hits)
print("by family:", dict(fam.most_common(12)))
print("wrote %s" % OUT)
