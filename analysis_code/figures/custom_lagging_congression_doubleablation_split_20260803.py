"""custom_lagging_congression_doubleablation_split_20260803.py — rebuild of `G3_lagging_vs_congression_balance`
("Is lagging more likely when MORE chromosomes congress?").

FEEDBACK (2026-08, message-2 item M2-02): "double could 1/3 congressed population". The original figure
(custom_plots_to_make_20260722.py, function p13 — DO NOT EDIT, so this is a standalone rebuild that
overwrites the same plot_id/output path per the established convention, e.g.
custom_max_congression_delay_20260722.py) bins cells by the fraction of their sisterless chromosomes that
congressed and bars the %-lagging per bin. `frac_congressed` contains exactly 0.333 for ONE row, and that
row IS a literal double-ablation cell: `20250711 double ablation_21`. She is asking for double-ablation
cells to be shown as their OWN identifiable population, not silently folded into an aggregate bar where a
single double-ablation cell can be mistaken for (or hidden inside) a broader "1/3 congressed" trend.

Checked how many double-ablation cells exist in this cohort at all: exactly ONE
(`20250711 double ablation_21`, batch-name pattern `double[ _]ablation`) out of N=42 -- the other
"double ablation"-named batches from 20250711/20250723 are either excluded (plot_excluded) or have no
usable Lagging-Chromosomes/behavior annotation, so they never entered this cohort to begin with. With N=1
there is nothing to bar-chart as a separate cohort (a %-lagging bar from 1 cell is not informative), so the
fix is to make that single point EXPLICIT on the same plot: every individual cell is now shown as a
jittered dot within its bin (so the reader can see the bars are built from a handful of points, not a
smooth distribution), and the one double-ablation cell is drawn as a distinct marker + directly labelled,
so it can never again be misread as representative of its whole bin.

SOURCE: identical to p13 (CHROMOSOME_MASTER behavior + ABLATION_MASTER "Lagging Chromosomes"); double-ablation
identity from the batch name itself (`double ablation` / `double_ablation`, as used consistently elsewhere
in this codebase, e.g. group4_ablation_intensity.py ABL_COMBINED_PICKS, group4_frap.py FRAP_DROP_REQUESTS).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, re, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT = __file__
lib.apply_style()
data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    chromo[r["batch"].strip()].append(r)

def keep(b):
    return not lib.plot_excluded(b) and not lib.is_mad1(b)

DBL_RE = re.compile(r"double[ _]ablation", re.I)

# ── ITEM 18 (user 2026-08-04, REPEAT — she says the earlier concern was not addressed) ────────────
# (1) "there should not be a double-ablation batch included". The 2026-08-03 rebuild KEPT the single
#     double-ablation cell and merely drew it as a distinct marker. She asked for it OUT. Dropped here,
#     and reported so the removal is visible rather than silent.
# (2) "the points in bar 1 are included in duplicate in bar 2". The bins are arithmetically disjoint
#     ((lo, hi] with lo=-0.01/0.34/0.67), so no cell is counted twice — but the LABELS both name 1/3
#     ("<=1/3 congressed" and "1/3-2/3"), so the one cell sitting at exactly 0.333 reads as if it belongs
#     to both bars. That is a labelling fault, not a counting fault. Labels are now explicit about which
#     side each boundary falls on, and each bar prints its own membership.
xs, ys, cells = [], [], []
n_dbl_dropped = []
for b, rs in chromo.items():
    if not keep(b): continue
    if DBL_RE.search(b):                      # ITEM 18(1): double-ablation cells excluded outright
        n_dbl_dropped.append(b); continue
    behs = [(r.get("behavior") or "").strip() for r in rs]
    if not behs or any(x == "" for x in behs): continue
    n = len(behs)
    if n < 2: continue
    ncong = sum(1 for x in behs if x in ("congressed", "at_plate"))
    lag = gv(b, "Lagging Chromosomes").strip().lower()
    if lag not in ("yes", "no"): continue
    xs.append(ncong / n); ys.append(1 if lag == "yes" else 0); cells.append(b)

assert len(xs) >= 8, f"only {len(xs)} cells -- refusing to build"
xs = np.array(xs); ys = np.array(ys)
is_dbl = np.zeros(len(xs), bool)              # none remain, kept so downstream references stay valid
print(f"N={len(xs)} cells; ITEM 18 dropped {len(n_dbl_dropped)} double-ablation cell(s): {n_dbl_dropped}")

bins = [(-.01, .34), (.34, .67), (.67, 1.01)]
lab = ["≤ 1/3 congressed\n(incl. exactly 1/3)", "> 1/3 to 2/3", "> 2/3 congressed"]
frac, ns, ns_dbl = [], [], []
for lo, hi in bins:
    m = (xs > lo) & (xs <= hi)
    frac.append(100 * ys[m].mean() if m.sum() else 0); ns.append(int(m.sum())); ns_dbl.append(int((m & is_dbl).sum()))

fig, ax = plt.subplots(figsize=(7.4, 5.4))
ax.bar(range(3), frac, color="#e08214", alpha=.55, zorder=1, width=.62)
for i, (f, n, nd) in enumerate(zip(frac, ns, ns_dbl)):
    tag = f" ({nd} double-abl.)" if nd else ""
    ax.text(i, f + 3, f"{f:.0f}%\nN={n}{tag}", ha="center", fontsize=8.5)

# --- individual cells as a RUG, not as points on the percentage axis ---------------------------------
# USER 2026-08-03: the y-axis was carrying two different quantities at once - the bars are "% of cells with
# lagging in this bin" while the dots were individual cells pinned at 0 or 100. Same axis, two meanings, and
# a reviewer would ask. Each cell's lagging status is BINARY, so it does not belong on a percentage scale at
# all. The cells now sit in two thin rug lanes drawn OUTSIDE the plotting range - "lagging" above the bars,
# "no lagging" below the zero line - so the reader can still count the cells each bar is built from without
# the axis pretending they are percentages.
rng = np.random.RandomState(3)
bin_of = np.digitize(xs, [b[1] for b in bins[:-1]])   # 0,1,2
LANE_YES, LANE_NO = -9.0, -21.0           # BOTH lanes below the axes: a lane above 100 collided
                                          # with the 4-line title, which sits in that same space
for i in range(3):
    for lagging_state, lane in ((1, LANE_YES), (0, LANE_NO)):
        m = (bin_of == i) & ~is_dbl & (ys == lagging_state)
        if not m.sum():
            continue
        jit = i + (rng.rand(m.sum()) - .5) * .42
        ax.scatter(jit, np.full(m.sum(), lane) + (rng.rand(m.sum()) - .5) * 3.0,
                   s=22, color="#555", alpha=.55, edgecolor="white", lw=.3, zorder=2, clip_on=False)
# the double-ablation cell(s): own marker + direct label, drawn LAST so it is never hidden
for i in range(3):
    m = (bin_of == i) & is_dbl
    if m.sum():
        jit = i + (rng.rand(m.sum()) - .5) * .12
        yv = np.where(ys[m] == 1, LANE_YES, LANE_NO)
        ax.scatter(jit, yv, s=140, color="#b2182b", marker="*", edgecolor="white", lw=.6, zorder=5,
                   clip_on=False, label=f"double-ablation cell (N={int(is_dbl.sum())})")
        for xj, yj, c in zip(jit, yv, [c for c, mm in zip(cells, m) if mm]):
            ax.annotate(c, (xj, yj), textcoords="offset points", xytext=(12, 0),
                        fontsize=7.5, color="#b2182b", fontweight="bold", ha="left",
                        va="center", annotation_clip=False)
ax.axhline(0, color="#999", lw=.8, zorder=1)
for lane, txt in ((LANE_YES, "each cell: lagging"), (LANE_NO, "each cell: no lagging")):
    ax.annotate(txt, (2.62, lane), fontsize=7, color="#555", va="center", annotation_clip=False)

rho, pv = stats.spearmanr(xs, ys)
ax.set_xticks(range(3)); ax.set_xticklabels(lab)
ax.set_ylim(0, 100)
ax.set_xlim(-0.55, 2.55)
ax.set_ylabel("Cells with lagging chromosomes (%)")
ax.legend(loc="upper left", fontsize=8, frameon=False)
ax.set_title(f"Is lagging more likely when MORE chromosomes congress?\n"
             f"fraction of the cell's sisterless chromosomes reaching the plate — "
             f"N={len(xs)} cells ({int(is_dbl.sum())} double-ablation); Spearman ρ={rho:.2f}, p={pv:.3g}\n"
             f"bars = %lagging per bin (built from as few as N={min(ns)} cells). Every cell appears once in the two\n"
             f"rug lanes beneath the axis - lagging in the upper lane, no lagging in the lower - so the bars\n"
             f"never hide how few cells they rest on. Her double-ablation cell is the red star.",
             loc="left", fontweight="bold", fontsize=9.2)
plt.tight_layout(); fig.savefig(f"{OUT3}/G3_lagging_vs_congression_balance.png", bbox_inches="tight", dpi=130)
plt.close(fig)
lib.record_plot("G3_lagging_vs_congression_balance", ["frac_congressed", "lagging", "batch", "is_double_ablation"],
                [[round(a, 3), int(c), d, int(dd)] for a, c, d, dd in zip(xs, ys, cells, is_dbl)],
                {"rho": round(float(rho), 3), "p": float(pv), "N": len(xs),
                 "n_double_ablation": int(is_dbl.sum()),
                 "double_ablation_cells": [c for c, d in zip(cells, is_dbl) if d],
                 "note": "rebuilt 2026-08-03 (feedback M2-02): individual cells now shown as jittered dots "
                         "per bin, double-ablation cell(s) drawn as a separate labelled series so a "
                         "single double-ablation cell can no longer be mistaken for a representative "
                         "'1/3 congressed' population. Only 1 double-ablation cell exists in this cohort "
                         "(N=42) -- too few to bar-chart as its own bin, so it is called out on the "
                         "existing bars instead."},
                SCRIPT, "Lagging likelihood vs fraction congressed, with double-ablation cell(s) split out "
                        "(plots-to-make #13, rebuilt 2026-08-03 for feedback M2-02)")
print(f"#13 (rebuilt) N={len(xs)} rho={rho:.3f} p={pv:.3g}  double-ablation cells: {int(is_dbl.sum())}")


# ── ITEM 18 (user 2026-08-04), SIMPLIFIED VERSION ─────────────────────────────────────────────────
# Her words: "make a version of it that's simplified in that it plots congressed yes/no against lagging
# for single, already at plate vs lagging for single, and then separate bars for 1 congressed, 2
# congressed, or three congressed, and 1 at plate, 2 at plate, and 3 at plate for triple".
# So: SINGLE (1-sisterless) has one chromosome, so its outcome is binary -> two paired comparisons
# (congressed y/n, at-plate y/n) against %-lagging. TRIPLE (3-sisterless) gets a bar per COUNT (1/2/3).
# Counts come from the per-chromosome behaviour rows; group from the master "# Sisterless KTs" column.
def _simplified():
    single = {"congressed": {"yes": [], "no": []}, "at_plate": {"yes": [], "no": []}}
    triple = {"congressed": {1: [], 2: [], 3: []}, "at_plate": {1: [], 2: [], 3: []}}
    for b, rs in chromo.items():
        if not keep(b) or DBL_RE.search(b): continue
        lag = gv(b, "Lagging Chromosomes").strip().lower()
        if lag not in ("yes", "no"): continue
        behs = [(r.get("behavior") or "").strip() for r in rs]
        if not behs or any(x == "" for x in behs): continue
        grp = gv(b, "# Sisterless KTs")
        lagv = 1 if lag == "yes" else 0
        n_cong = sum(1 for x in behs if x == "congressed")
        n_plate = sum(1 for x in behs if x == "at_plate")
        if grp == "1" and len(behs) == 1:
            single["congressed"]["yes" if n_cong else "no"].append(lagv)
            single["at_plate"]["yes" if n_plate else "no"].append(lagv)
        elif grp == "3":
            if 1 <= n_cong <= 3: triple["congressed"][n_cong].append(lagv)
            if 1 <= n_plate <= 3: triple["at_plate"][n_plate].append(lagv)

    def pct(v): return 100.0 * float(np.mean(v)) if v else np.nan
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8))
    COL = {"congressed": "#2166ac", "at_plate": "#1b7837"}
    # LEFT: single
    labs, vals, ns, cols = [], [], [], []
    for kind in ("congressed", "at_plate"):
        for yn in ("yes", "no"):
            labs.append(f"{kind.replace('_',' ')}\n{yn}"); vals.append(pct(single[kind][yn]))
            ns.append(len(single[kind][yn])); cols.append(COL[kind])
    axes[0].bar(range(len(vals)), vals, .62, color=cols, alpha=.85)
    axes[0].set_xticks(range(len(labs))); axes[0].set_xticklabels(labs, fontsize=8.5)
    for i, (v, n) in enumerate(zip(vals, ns)):
        if np.isfinite(v): axes[0].text(i, v + 1.5, f"{v:.0f}%\nn={n}", ha="center", fontsize=7.5)
    axes[0].set_ylabel("% of cells with a lagging chromosome")
    axes[0].set_title("SINGLE (1-sisterless) — one chromosome, so outcome is yes/no",
                      loc="left", fontweight="bold", fontsize=9.5)
    # NF4, her question: "why do values for yes and no (ex. congressed yes + congressed no) not equal 100?"
    # Because each bar is the %-LAGGING *within that subset of cells*, not that subset's share of one whole.
    # 'congressed yes' = of the cells whose chromosome congressed, what fraction lagged. The two bars describe
    # two different groups of cells, so there is no reason for them to sum to 100.
    axes[0].text(0.0, -0.26,
                 "Each bar = % of the cells IN THAT SUBSET with a lagging chromosome — not a share of one whole.\n"
                 "'congressed yes' and 'congressed no' are two different groups of cells, so they do not sum to 100.",
                 transform=axes[0].transAxes, fontsize=7.2, color="#a33", va="top", linespacing=1.5)
    # RIGHT: triple, bar per count
    labs, vals, ns, cols = [], [], [], []
    # NF4 (user 2026-08-04): "remove 2 congressed and 2 at plate samples from triple plot" — those bars rest
    # on a single cell and read as if they were rates. Drop any level with fewer than MIN_BAR cells, and say
    # on the figure which were dropped rather than letting them vanish.
    MIN_BAR = 2
    dropped_bars = []
    for kind in ("congressed", "at_plate"):
        for k in (1, 2, 3):
            if len(triple[kind][k]) < MIN_BAR:
                dropped_bars.append(f"{k} {kind.replace('_',' ')} (n={len(triple[kind][k])})"); continue
            labs.append(f"{k} {kind.replace('_',' ')}"); vals.append(pct(triple[kind][k]))
            ns.append(len(triple[kind][k])); cols.append(COL[kind])
    axes[1].bar(range(len(vals)), vals, .62, color=cols, alpha=.85)
    axes[1].set_xticks(range(len(labs))); axes[1].set_xticklabels(labs, fontsize=8.5, rotation=12, ha="right")
    for i, (v, n) in enumerate(zip(vals, ns)):
        if np.isfinite(v): axes[1].text(i, v + 1.5, f"{v:.0f}%\nn={n}", ha="center", fontsize=7.5)
    axes[1].set_title("TRIPLE (3-sisterless) — one bar per number of chromosomes",
                      loc="left", fontweight="bold", fontsize=9.5)
    for a in axes: a.set_ylim(0, 108)
    fig.suptitle("Is lagging more likely when more chromosomes congress / reach the plate?  "
                 "ITEM 18 simplified — double-ablation cells excluded"
                 + (f"\nNF4: dropped bars with n<2: {', '.join(dropped_bars)}" if dropped_bars else ""),
                 x=.01, ha="left", fontweight="bold", fontsize=10)
    plt.tight_layout()
    fig.savefig(f"{OUT3}/G3_lagging_vs_congression_simple.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    rows = ([["single", k, yn, len(single[k][yn]), round(pct(single[k][yn]), 2)]
             for k in single for yn in single[k]]
            + [["triple", k, str(n), len(triple[k][n]), round(pct(triple[k][n]), 2)]
               for k in triple for n in triple[k]])
    lib.record_plot("G3_lagging_vs_congression_simple",
                    ["group", "outcome", "level", "n_cells", "pct_lagging"], rows,
                    {"item18": "simplified split she specified; double-ablation cells excluded",
                     "y_label": "% of cells with a lagging chromosome"},
                    SCRIPT, "Lagging vs congression / at-plate, split single vs triple (simplified)")
    print("ITEM 18 simplified — single:",
          {k: {yn: len(v) for yn, v in d.items()} for k, d in single.items()},
          " triple:", {k: {n: len(v) for n, v in d.items()} for k, d in triple.items()})

_simplified()
