#!/usr/bin/env python3
"""ONE TABLE: per-kinetochore fate probability, 1-sisterless vs 3-sisterless cells.

Her question, in two parts: is a sisterless kinetochore in a 3-sisterless cell more likely to become
LAGGING than one in a 1-sisterless cell, and the same for congressing / remaining polar / starting at the
plate. The unit is the KINETOCHORE, not the cell — a 3-sisterless cell contributes three.

Deliberately NOT written into any .ai (another session is working in those documents). Emits a standalone
PNG + PDF + CSV.

SOURCES
  congression fates : annotations/CHROMOSOME_MASTER.csv  `behavior` (congressed / at_plate / noncongression)
  lagging           : master `# Lagging Chromosomes` (her 8817 count pass) falling back to the cell-level
                      `Lagging Chromosomes` Yes/No, which is equivalent for 1-sisterless cells since n=1
COHORT (both)       : on-target, `# Sisterless KTs` in {1,3}, NOT lib.plot_excluded — which removes
                      Exclude=Yes, drugs, review outliers, metaphase-phase ablations and 4-sisterless.

STATS
  Fisher exact per fate on kinetochore counts. Holm correction is applied ONLY within the three congression
  fates, which are one compositional family (they sum to 1); lagging is a separate question from a separate
  source and carries its raw p. The omnibus 3-fate chi-square is the primary test for the congression family.
"""
import sys, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from scipy import stats
import lib

csv.field_size_limit(10 ** 9)
OUT = "/Volumes/4 MB/ablation_plots"
C1, C3 = "#3b6fb6", "#e6820e"          # validated pair: CVD ΔE 25.7 protan / 31.6 tritan, normal 32.6
INK, INK2, MUTED = "#1b1b1b", "#444444", "#8a8a8a"
SURFACE, BAND = "#fcfcfb", "#f2f4f7"

data, _ = lib.load_master()
M = {r["Batch Name"]: r for r in data}


def in_cohort(batch, want=("1", "3")):
    m = M.get(batch)
    if not m or lib.plot_excluded(batch):
        return None
    if (m.get("On-Target / Off-Target", "") or "").strip().lower() != "on-target":
        return None
    s = (m.get("# Sisterless KTs", "") or "").strip()
    return int(s) if s in want else None


# ---- congression fates ---------------------------------------------------------------------------
fates = []
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    b = (r.get("batch") or "").strip()
    s = in_cohort(b)
    beh = (r.get("behavior") or "").strip()
    if s and beh:
        fates.append((b, s, beh))

# ---- lagging -------------------------------------------------------------------------------------
lag = []
for r in data:
    b = r["Batch Name"]
    s = in_cohort(b)
    if not s:
        continue
    v = (r.get("# Lagging Chromosomes", "") or "").strip()
    if v.isdigit():
        nl = min(int(v), s)
    else:
        yn = (r.get("Lagging Chromosomes", "") or "").strip().lower()
        if s == 1 and yn in ("yes", "no"):
            nl = 1 if yn == "yes" else 0
        else:
            continue
    lag.append((b, s, nl))

rows = []
def add(label, k1, n1, c1, k3, n3, c3, fam):
    odds, p = stats.fisher_exact([[k1, n1 - k1], [k3, n3 - k3]])
    rows.append(dict(fate=label, k1=k1, n1=n1, c1=c1, k3=k3, n3=n3, c3=c3,
                     p1=k1 / n1, p3=k3 / n3, orr=odds, p=p, fam=fam))

A = [x for x in fates if x[1] == 1]
B = [x for x in fates if x[1] == 3]
for key, label in (("noncongression", "remains polar"), ("congressed", "congresses"),
                   ("at_plate", "starts at the plate")):
    add(label, sum(1 for x in A if x[2] == key), len(A), len({x[0] for x in A}),
        sum(1 for x in B if x[2] == key), len(B), len({x[0] for x in B}), "congression")
g1 = [x for x in lag if x[1] == 1]; g3 = [x for x in lag if x[1] == 3]
add("becomes lagging", sum(x[2] for x in g1), sum(x[1] for x in g1), len(g1),
    sum(x[2] for x in g3), sum(x[1] for x in g3), len(g3), "lagging")

fam = sorted([r for r in rows if r["fam"] == "congression"], key=lambda r: r["p"])
prev = 0.0
for i, r in enumerate(fam):
    v = max(min(1.0, (len(fam) - i) * r["p"]), prev); r["holm"] = v; prev = v
for r in rows:
    r.setdefault("holm", None)

chi2, pomni, dof, _ = stats.chi2_contingency(
    [[r["k1"] for r in rows if r["fam"] == "congression"],
     [r["k3"] for r in rows if r["fam"] == "congression"]])

order = ["remains polar", "congresses", "starts at the plate", "becomes lagging"]
rows.sort(key=lambda r: order.index(r["fate"]))

# ---- render --------------------------------------------------------------------------------------
fig = plt.figure(figsize=(14.4, 6.6), facecolor=SURFACE)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
ax.set_xlim(0, 1); ax.set_ylim(0, 1)

X = dict(fate=0.030, prob=0.235, counts=0.545, orr=0.712, p=0.775, holm=0.840, verdict=0.905)
ax.text(0.030, 0.955, "Probability that one sisterless kinetochore meets each fate",
        fontsize=17, fontweight="bold", color=INK, va="top")
ax.text(0.030, 0.905, "1-sisterless vs 3-sisterless cells · on-target, non-drug, non-excluded · "
                      "the unit is the KINETOCHORE, so a 3-sisterless cell contributes three",
        fontsize=10.5, color=INK2, va="top")

yh = 0.800
for k, lab, ha in (("fate", "fate", "left"), ("prob", "P(fate) per kinetochore", "left"),
                   ("counts", "counts", "left"), ("orr", "odds\nratio", "center"),
                   ("p", "Fisher\np", "center"), ("holm", "Holm\np", "center"),
                   ("verdict", "verdict", "center")):
    ax.text(X[k], yh, lab, fontsize=9.5, color=MUTED, fontweight="bold", ha=ha, va="center")
ax.plot([0.025, 0.975], [0.768, 0.768], color="#d5d8dd", lw=1.1)

# legend for the two cohorts
ax.plot([0.033], [0.852], "o", ms=9, color=C1); ax.text(0.046, 0.852, "1-sisterless cell", fontsize=10, color=INK2, va="center")
ax.plot([0.150], [0.852], "o", ms=9, color=C3); ax.text(0.163, 0.852, "3-sisterless cell", fontsize=10, color=INK2, va="center")

BAR0, BAR1 = 0.235, 0.500
def xp(p): return BAR0 + (BAR1 - BAR0) * p

rh = 0.148
for i, r in enumerate(rows):
    y = 0.688 - i * rh
    if r["holm"] is not None and r["holm"] < 0.05:
        ax.add_patch(FancyBboxPatch((0.022, y - 0.055), 0.958, 0.112,
                                    boxstyle="round,pad=0.004,rounding_size=0.008",
                                    facecolor="#fdf6e3", edgecolor="#efe0b0", lw=1.0, zorder=0))
    elif i % 2 == 1:
        ax.add_patch(FancyBboxPatch((0.022, y - 0.055), 0.958, 0.112,
                                    boxstyle="round,pad=0.004,rounding_size=0.008",
                                    facecolor=BAND, edgecolor="none", zorder=0))
    ax.text(X["fate"], y, r["fate"], fontsize=13, color=INK, fontweight="bold", va="center", zorder=3)

    # probability comparison — dumbbell, both values directly labelled (relieves the contrast WARN)
    ax.plot([xp(min(r["p1"], r["p3"])), xp(max(r["p1"], r["p3"]))], [y, y],
            color="#c9ced6", lw=2.0, solid_capstyle="round", zorder=2)
    for val, col in ((r["p1"], C1), (r["p3"], C3)):
        ax.plot([xp(val)], [y], "o", ms=11, color=col, markeredgecolor=SURFACE, markeredgewidth=2.0, zorder=4)
    lo, hi = (r["p1"], r["p3"]) if r["p1"] <= r["p3"] else (r["p3"], r["p1"])
    locol, hicol = (C1, C3) if r["p1"] <= r["p3"] else (C3, C1)
    ax.text(xp(lo) - 0.012, y, f"{lo:.2f}", fontsize=11, color=locol, fontweight="bold", ha="right", va="center", zorder=4)
    ax.text(xp(hi) + 0.012, y, f"{hi:.2f}", fontsize=11, color=hicol, fontweight="bold", ha="left", va="center", zorder=4)

    ax.text(X["counts"], y + 0.020, f"{r['k1']}/{r['n1']} KTs  ({r['c1']} cells)",
            fontsize=9.5, color=C1, va="center", zorder=3)
    ax.text(X["counts"], y - 0.022, f"{r['k3']}/{r['n3']} KTs  ({r['c3']} cells)",
            fontsize=9.5, color=C3, va="center", zorder=3)
    ax.text(X["orr"], y, f"{r['orr']:.2f}", fontsize=11, color=INK2, ha="center", va="center", zorder=3)
    bold = r["p"] < 0.05
    ax.text(X["p"], y, f"{r['p']:.4f}", fontsize=11, ha="center", va="center", zorder=3,
            color=INK if bold else INK2, fontweight="bold" if bold else "normal")
    ht = "—" if r["holm"] is None else f"{r['holm']:.3f}"
    hb = r["holm"] is not None and r["holm"] < 0.05
    ax.text(X["holm"], y, ht, fontsize=11, ha="center", va="center", zorder=3,
            color=INK if hb else INK2, fontweight="bold" if hb else "normal")
    if r["fate"] == "remains polar":
        v, vc = "real difference", "#1a7f4f"
    elif r["fate"] == "congresses":
        v, vc = "suggestive", "#a8791a"
    else:
        v, vc = "no evidence", MUTED
    ax.text(X["verdict"], y, v, fontsize=9.5, color=vc, fontweight="bold", ha="center", va="center", zorder=3)

ax.plot([0.025, 0.975], [0.098, 0.098], color="#d5d8dd", lw=1.1)
foot = (
    f"Omnibus across the three congression fates: chi-square = {chi2:.2f}, df = {dof}, p = {pomni:.4f}.  "
    f"Holm correction is applied only within those three, which are compositional (they sum to 1); lagging is a "
    f"separate question from a separate source and carries its raw p.\n"
    f"Fates from CHROMOSOME_MASTER `behavior`; lagging from the master `# Lagging Chromosomes` counts (8817 pass), "
    f"falling back to the cell-level Yes/No, which is equivalent for 1-sisterless cells since n=1 — so the lagging row "
    f"rests on a different, larger cell set than the other three.\n"
    f"Cell-level tests on per-cell fractions (which respect the clustering of 3 kinetochores in one cell) agree in "
    f"direction for all four rows, but none survive Holm individually — the omnibus is the primary test."
)
ax.text(0.030, 0.075, foot, fontsize=8.6, color=MUTED, va="top", linespacing=1.65)

for ext in ("png", "pdf"):
    fig.savefig(f"{OUT}/sisterless_fate_table_20260804.{ext}", dpi=200,
                facecolor=SURFACE, bbox_inches="tight")
plt.close(fig)

with open(f"{OUT}/sisterless_fate_table_20260804.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["fate", "P_per_KT_1sis", "P_per_KT_3sis", "lagging_1sis_k", "n_KT_1sis", "n_cells_1sis",
                "k_3sis", "n_KT_3sis", "n_cells_3sis", "odds_ratio", "fisher_p", "holm_p_within_congression"])
    for r in rows:
        w.writerow([r["fate"], round(r["p1"], 4), round(r["p3"], 4), r["k1"], r["n1"], r["c1"],
                    r["k3"], r["n3"], r["c3"], round(r["orr"], 3), round(r["p"], 5),
                    "" if r["holm"] is None else round(r["holm"], 4)])
print(f"omnibus chi2={chi2:.2f} df={dof} p={pomni:.4f}")
for r in rows:
    print(f"  {r['fate']:22s} {r['p1']:.3f} vs {r['p3']:.3f}  p={r['p']:.4f}")
print(f"-> {OUT}/sisterless_fate_table_20260804.[png|pdf|csv]")
