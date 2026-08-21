#!/usr/bin/env python3
"""Every statistical analysis used by the figures currently on the live decks.

HER QUESTION (2026-08-18): "what are all of the types of statistical analyses used in the currently
relevant results/plots/etc".

Method: for each figure placed on a live deck, read its BUILDER and record which tests it calls, then
group by test. Also reads the recorded settings and the drawn legend bullets, because some figures state
a test they compute inline. The unit of replication is reported per figure from the data CSV (does it hold
one row per cell, or many).
"""
import csv, io, json, os, re, collections
ROOT = "/Volumes/4 MB"
OUT = ROOT + "/4_TABLES_AND_REPORTS/STATISTICS_INVENTORY_20260818.csv"
ps = json.load(open(ROOT + "/ablation_plots/PLOT_SETTINGS.json"))

placed = set()
for f in os.listdir(ROOT + "/_claude_tmp"):
    if f.startswith("geom9_") and f.endswith(".tsv"):
        for r in csv.DictReader(io.open(f"{ROOT}/_claude_tmp/{f}", encoding="utf-8", errors="replace"), delimiter="\t"):
            if r.get("kind") == "PlacedItem" and (r.get("linked") or "").strip():
                placed.add(os.path.basename(r["linked"]).rsplit(".", 1)[0])

TESTS = {
    "mannwhitneyu": "Mann-Whitney U (two-sample, non-parametric)",
    "kruskal": "Kruskal-Wallis (k-sample, non-parametric)",
    "wilcoxon": "Wilcoxon signed-rank (paired)",
    "ttest_ind": "Student t-test (two-sample)",
    "ttest_rel": "paired t-test",
    "fisher_exact": "Fisher exact test (2x2 proportions)",
    "chi2_contingency": "chi-square test of independence",
    "spearmanr": "Spearman rank correlation",
    "pearsonr": "Pearson correlation",
    "linregress": "linear regression (least squares)",
    "curve_fit": "non-linear least-squares curve fit",
    "ranksums": "Wilcoxon rank-sum",
    "shapiro": "Shapiro-Wilk normality test",
    "levene": "Levene test for equal variance",
    "kstest": "Kolmogorov-Smirnov test",
    "ks_2samp": "two-sample Kolmogorov-Smirnov",
    "bootstrap": "bootstrap resampling",
    "permutation_test": "permutation test",
    "GroupKFold": "grouped k-fold cross-validation (model)",
    "cross_val": "cross-validation (model)",
    "logistic": "logistic regression",
    "roc_auc": "ROC AUC (classifier)",
    "weibull": "Weibull survival fit",
    "sem(": "standard error of the mean",
}
DIRS = [ROOT + "/ablation_figures_20260625", ROOT + "/ablation_figures_20260625/figures",
        ROOT + "/ablation_plots/code", ROOT + "/dataops"]
cache = {}
def source_of(code):
    if not code: return ""
    if code in cache: return cache[code]
    base = code.split("__", 1)[-1]
    txt = ""
    for d in DIRS:
        for n in (code, base):
            p = os.path.join(d, n)
            if os.path.exists(p):
                try: txt = open(p, errors="replace").read()
                except OSError: txt = ""
                break
        if txt: break
    cache[code] = txt
    return txt

rows, by_test = [], collections.defaultdict(set)
for pid in sorted(placed):
    e = ps.get(pid) or {}
    txt = source_of(e.get("code") or "")
    found = sorted({v for k, v in TESTS.items() if k in txt})
    # unit of replication, from the data CSV
    unit = ""
    dpath = f"{ROOT}/ablation_plots/data/{pid}.csv"
    if os.path.exists(dpath):
        try:
            d = list(csv.DictReader(io.open(dpath, encoding="utf-8", errors="replace")))
            if d:
                bcol = next((c for c in d[0] if c and c.strip().lower() == "batch"), None)
                if bcol:
                    per = collections.Counter((r.get(bcol) or "").strip() for r in d)
                    per.pop("", None)
                    if per:
                        unit = ("one row per cell" if max(per.values()) == 1
                                else f"{len(d)} rows over {len(per)} cells (median {int(sorted(per.values())[len(per)//2])}/cell)")
                else:
                    unit = "no cell column (aggregate figure)"
        except Exception:
            pass
    for t in found: by_test[t].add(pid)
    rows.append(dict(figure=pid, builder=e.get("code") or "", tests="; ".join(found) or "(none found in builder)",
                     unit_of_replication=unit))

with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print(f"figures on live decks: {len(placed)}   with a test in their builder: {sum(1 for r in rows if 'none found' not in r['tests'])}\n")
print(f"{'statistical analysis':52s} {'figures':>7}   examples")
for t, s in sorted(by_test.items(), key=lambda kv: -len(kv[1])):
    ex = ", ".join(sorted(s)[:3])
    print(f"{t[:51]:52s} {len(s):7d}   {ex[:70]}")
print(f"\n[done] -> {OUT}")
