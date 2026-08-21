#!/usr/bin/env python3
"""Metaphase duration vs the FRACTION of a cell's sisterless chromosomes with each fate.

Her R7 pointer was right: the chromosome-length/behaviour pass DOES carry a per-chromosome fate, in
annotations/CHROMOSOME_MASTER.csv `behavior` = congressed / noncongression / at_plate. So the
"joined the plate" and "remained polar until anaphase" fractions can both be computed now.
LAGGING is the one fate that pass never recorded — it is not in CHROMOSOME_MASTER, CHROMO_LENGTH_BEHAVIOR_PAIRING
or PREABL_CHROMOSOME_ASSIGNMENT (every "lag" hit in those files is the word colLAGen), and the master's
Lagging Chromosomes column is a cell-level YES/NO with no per-chromosome breakdown. That plot needs her to
annotate it."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)

def hms(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try: q = [float(x) for x in s.split(":")]
    except ValueError: return None
    v = q[0]*3600 + q[1]*60 + q[2] if len(q) == 3 else (q[0]*60 + q[1] if len(q) == 2 else q[0])
    return -v if neg else v

master, _ = lib.load_master(); M = {r["Batch Name"]: r for r in master}
CM = list(csv.DictReader(open(f"{ROOT}/annotations/CHROMOSOME_MASTER.csv", newline="")))
per = collections.defaultdict(list)
for r in CM:
    b = r["batch"].strip()
    if r["behavior"].strip(): per[b].append(r["behavior"].strip())

FATES = [("congressed", "joined the plate", "#2e8b57"),
         ("noncongression", "remained polar until anaphase", "#e6820e"),
         ("at_plate", "at the plate from the start", "#3b6fb6")]
fig, axs = plt.subplots(1, 3, figsize=(15.2, 4.8))
rep = []
for ax, (key, lab, colr) in zip(axs, FATES):
    X, Y, CO = [], [], []
    for b, v in per.items():
        if b not in M: continue
        mt, at = hms(M[b].get("Metaphase Start (s)")), hms(M[b].get("Anaphase Onset (s)"))
        if mt is None or at is None or at <= mt: continue
        X.append(sum(1 for z in v if z == key) / len(v))
        Y.append((at - mt) / 60.0)
        CO.append((M[b].get("# Sisterless KTs") or "").strip())
    if len(X) < 8:
        ax.axis("off"); ax.text(.5, .5, f"n={len(X)}", ha="center"); continue
    X = np.array(X); Y = np.array(Y)
    for co, mk in (("1", "o"), ("3", "^")):
        m = np.array([c == co for c in CO])
        if m.any(): ax.scatter(X[m], Y[m], s=40, marker=mk, color=colr, alpha=0.75,
                               edgecolor="white", lw=0.4, label=f"{co}-sisterless (n={int(m.sum())})")
    other = np.array([c not in ("1", "3") for c in CO])
    if other.any(): ax.scatter(X[other], Y[other], s=30, color="#999", alpha=0.6, lw=0, label="other/unscored")
    rho, pv = st.spearmanr(X, Y)
    if pv < 0.05:
        b_, a_ = np.polyfit(X, Y, 1); xf = np.linspace(0, 1, 20); ax.plot(xf, a_ + b_*xf, "-", color=colr, lw=2.0)
    ax.text(0.98, 0.02, f"Spearman rho={rho:.2f}, p={pv:.2g}\nN={len(X)} cells", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel(f"fraction of sisterless chromosomes that {lab}")
    ax.set_ylabel("metaphase duration (min)"); ax.legend(fontsize=7.5, loc="upper right")
    ax.set_title(lab, loc="left", fontweight="bold", fontsize=9.5)
    rep.append(f"{lab}: N={len(X)}, rho={rho:.2f}, p={pv:.2g}")
fig.suptitle("Metaphase duration vs the fate of a cell's sisterless chromosomes", fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/QNEW_metaphase_vs_fate_fraction.png", dpi=200, bbox_inches="tight")
plt.close(fig)
try: lib.record_plot("QNEW_metaphase_vs_fate_fraction", ["x"], [], {"family": "questions_20260727"},
                     script=__file__, caption="metaphase duration vs sisterless-chromosome fate fractions",
                     source=[f"{ROOT}/annotations/CHROMOSOME_MASTER.csv"], key_column=None, fig=fig)
except Exception: pass
print("  QNEW_metaphase_vs_fate_fraction")
for r in rep: print("   ", r)
print("   LAGGING fraction: NOT ANNOTATED anywhere per-chromosome - needs her pass")
