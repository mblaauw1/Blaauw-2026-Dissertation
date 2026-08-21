#!/usr/bin/env python3
"""Is lagging more likely when MORE chromosomes congress — split by ablation number (USER 2026-08-05).

  "because this makes bars based on a situation of three sisterless kinetochores, it would be more accurate
   to break it up into a plot for triple that has four bars (0,1,2,3); and a plot for single that has two
   bars (0,1). leave double sisterless data out of it."

The parent figure (G3_lagging_vs_congression_balance) binned every cell by the FRACTION congressed, which
puts a 1-sisterless cell with its one chromosome congressed in the same bin as a 3-sisterless cell with all
three congressed — different situations. Here the bin is the COUNT of congressed chromosomes and the two
ablation numbers get their own figure, so each bar is one well-defined situation.

Double-chromosome cells are excluded (lib.double_chromosome_batches), as are drugs, Mad1 and the standing
review exclusions. Congression count comes from CHROMOSOME_MASTER behaviour, lagging from the master's
"Lagging Chromosomes" Yes/No.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib

lib.apply_style()
ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/group3"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

rows, _ = lib.load_master()
dbl = lib.double_chromosome_batches()
act = [r for r in rows if r.get("Exclude") not in ("Yes", "yes") and not lib.is_drug(r["Batch Name"])
       and not lib.is_mad1(r["Batch Name"]) and not lib.excluded(r["Batch Name"])
       and r["Batch Name"] not in dbl]

beh = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/annotations/CHROMOSOME_MASTER.csv", encoding="utf-8", errors="replace")):
    v = (r.get("behavior") or "").strip().lower()
    if v: beh[r["batch"].strip()].append(v)

def yn(v):
    v = (v or "").strip().lower()
    return "Yes" if v == "yes" else ("No" if v == "no" else None)

cells = collections.defaultdict(lambda: [0, 0])   # (nsis, ncong) -> [lag_yes, lag_no]
for r in act:
    ns = (r.get("# Sisterless KTs") or "").strip()
    if ns not in ("1", "3"): continue
    b = r["Batch Name"]
    if b not in beh: continue
    lag = yn(r.get("Lagging Chromosomes"))
    if lag is None: continue
    nc = sum(1 for v in beh[b] if v == "congressed")
    cells[(ns, nc)][0 if lag == "Yes" else 1] += 1

SPEC = [("3", 3, "3-sisterless (triple)", "#762a83", "G3_lagging_by_ncongressed_triple"),
        ("1", 1, "1-sisterless (single)", "#1b7837", "G3_lagging_by_ncongressed_single")]
for ns, mx, title, col, pid in SPEC:
    bins = list(range(0, mx + 1))
    ys = [cells[(ns, n)][0] for n in bins]; ns_ = [cells[(ns, n)][1] for n in bins]
    N = [a + b for a, b in zip(ys, ns_)]
    frac = [(a / t if t else 0.0) for a, t in zip(ys, N)]
    fig, ax = plt.subplots(figsize=(6.4 if mx == 3 else 4.6, 4.8))
    ax.bar(bins, frac, color=col, alpha=0.85, width=0.62)
    for i, n in enumerate(bins):
        ax.text(n, frac[i] + 0.02, f"{frac[i]*100:.0f}%\nN={N[i]}", ha="center", va="bottom", fontsize=8.5)
    # between-bin test on the Yes/No table (bins with no cells dropped)
    tab = np.array([[ys[i], ns_[i]] for i in range(len(bins)) if N[i] > 0], float)
    txt = ""
    if tab.shape[0] >= 2 and tab.sum() > 0:
        try:
            if tab.shape[0] == 2:
                _, p = st.fisher_exact(tab); txt = f"Fisher exact p={p:.3g}"
            else:
                chi2, p, dof, exp = st.chi2_contingency(tab)
                txt = f"χ²={chi2:.2f}, df={dof}, p={p:.3g}" + ("  (some expected<5)" if (exp < 5).any() else "")
        except Exception:
            pass
    if txt: ax.text(0.01, 0.985, txt, transform=ax.transAxes, ha="left", va="top", fontsize=8, color="#222")
    ax.set_xticks(bins); ax.set_xticklabels([str(b) for b in bins])
    ax.set_xlabel("number of sisterless chromosomes that congressed")
    ax.set_ylabel("fraction of cells with a lagging chromosome")
    ax.set_ylim(0, 1.22)
    ax.set_title(f"Is lagging more likely when more chromosomes congress?\n{title} — "
                 f"{sum(N)} cells (double-chromosome cells excluded)", loc="left", fontweight="bold", fontsize=9.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/{pid}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    lib.record_plot(pid, ["n_congressed", "fraction_lagging", "N", "n_lagging_yes", "n_lagging_no"],
                    [[bins[i], round(frac[i], 4), N[i], ys[i], ns_[i]] for i in range(len(bins))],
                    {"split": f"{ns}-sisterless only", "bins": "COUNT of congressed chromosomes (not fraction)",
                     "excluded": "double-chromosome, drug, Mad1, review exclusions", "between_bin_test": txt},
                    SCRIPT, f"Lagging vs number of chromosomes congressed — {title}")
    print(f"{pid}: bins={bins} N={N} lagging%={[round(f*100) for f in frac]}  {txt}")
