"""Her 2026-08-17 requests, two figures:

(1) ONE metaphase-duration violin carrying the groups that were sitting on their own plots — the FOUR-
    ablation group, the cells where TWO on-target ablations landed on ONE kinetochore, and the collagen-
    plated cells — alongside every normal cohort, so they can actually be compared:
      "make sure they're on the same violin plot, with all of the other normal violins for comparison"
    -> G1_violin2_all_cohorts  (goes to the main supplemental deck, artboard 2)

(2) A table: every collagen cell's metaphase duration, then the fastest and slowest QUARTILE of the
    triple-ablation cells on the same measurement.
      "Make Table with breakdown of collagen cell metaphase duration, then top 25% of triple ablation
       that did the measured thing the fastest/slowest."
    -> G1_collagen_duration_table

COHORT DEFINITIONS — from the master's own columns, never from file names (feedback_sisterless_kts_is_
ablation_number, feedback_filename_never_identifies_across_dates):
  * ablation number      = `# Sisterless KTs`
  * two hits on one KT   = On-target AND `# Sisterless KTs` == 1 AND `# Unique Targets` >= 2, i.e. one
                           kinetochore destroyed, more than one shot taken at it. `# Unique Targets` is
                           only ever used HERE, to count SHOTS; the cohort itself is still keyed off
                           `# Sisterless KTs` (feedback_single_ontarget_definition).
  * collagen             = plating substrate, NOT a drug (feedback_collagen_not_a_drug_exclusion), so it
                           is carved out of the on-target cells rather than excluded from them.
Metaphase-ablated and drug-treated cells stay excluded by default, as everywhere else.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as _st
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"
SCRIPT = __file__
rows, _ = lib.load_master()
dbl = set(lib.double_chromosome_batches())

COLLAGEN = "Collagen"
TWOHIT = "1-sis, 2 hits"
lib.PALETTE.setdefault(COLLAGEN, "#e69f00")     # amber; CB-safe against the greens/purples
lib.PALETTE.setdefault(TWOHIT, "#0072b2")       # blue


def _int(v):
    try: return int(float(str(v).strip()))
    except Exception: return None


def cohort_of(r):
    """Main-violin cohort for a master row, or None. Same gate as lib.assign_cohorts, plus the two groups
    she asked to bring in (collagen, two-hits-on-one-KT) which that helper deliberately does not emit."""
    b = r["Batch Name"]
    if lib.is_drug(b) or lib.is_mad1(b): return None
    if str(r.get("Exclude", "")).strip().lower() == "yes": return None
    # NOT lib.plot_excluded(): that helper also bundles the 4-SISTERLESS cohort out by default, and the
    # four-ablation group is one of the three she explicitly asked to see ON this plot. Metaphase- and
    # prophase-timed ablations and REVIEW_EXCLUDE outliers are still dropped, exactly as everywhere else.
    if lib.excluded(b) or lib.is_metaphase_ablation(b) or lib.is_prophase_ablation(b): return None
    tt = (r.get("On-Target / Off-Target", "") or "").strip()
    sis = _int(r.get("# Sisterless KTs", ""))
    tg = _int(r.get("# Unique Targets", ""))
    if "collagen" in b.lower(): return COLLAGEN   # plating substrate, so target type does not gate it
    if b in dbl: return "Double Chromosome"
    if tt == "Unmodified": return "unModified"
    if tt == "Off-target": return "Off-Target/Control"
    if tt == "On-target" and sis == 1 and (tg or 0) >= 2: return TWOHIT
    if tt == "On-target" and sis in (1, 2, 3, 4): return f"{sis}-Sister"
    return None


byc = {}
for r in rows:
    k = cohort_of(r)
    if k is None: continue
    v, ok = lib.mitotic_duration_min(r)
    if not ok or v is None: continue
    byc.setdefault(k, []).append((r["Batch Name"], float(v)))

ORDER = ["unModified", "Off-Target/Control", "1-Sister", TWOHIT, "2-Sister", "3-Sister", "4-Sister",
         "Double Chromosome", COLLAGEN]
ORDER = [k for k in ORDER if byc.get(k)]
print("cohort Ns:", {k: len(byc[k]) for k in ORDER})

# ───────────────────────────── (1) the combined violin ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13.0, 5.6))
for i, k in enumerate(ORDER):
    d = [v for _, v in byc[k]]
    col = lib.PALETTE.get(k, "#888888")
    # journal_violin enforces the shared conventions (scale='width', width 0.8, cut at the data, no body
    # under N=6) and now also draws the SD bar her 2026-08-17 rule requires.
    lib.journal_violin(ax, d, i, col, alpha=0.30, lw=1.0, min_n=5)
    jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), i) + jit, d, s=lib.VIOLIN_DOT_S, color=col, alpha=0.8,
               edgecolor="white", linewidth=0.3, zorder=3)
    lib.violin_stats(ax, d, i, col, half=0.34)
    ax.text(i, -0.045, f"N={len(d)}", transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8.5)

ax.set_xticks(range(len(ORDER)))
import canon_labels as CL
# short cohort names: the raw key for the double-chromosome cohort is a three-line sentence that collides
# with the N under it. One canonical short name per group (canon_labels.GROUP), defined once in the legend.
ax.set_xticklabels([CL.canon_group(lib.lbl(k)) for k in ORDER], fontsize=9.5)
ax.set_ylabel("Metaphase duration (min)")
ax.set_ylim(bottom=0)
ax.set_title("Metaphase duration — every cohort on one axis "
             "(bar = median, dashed/diamond = mean, whisker = SD)", loc="left", fontweight="bold",
             fontsize=10, pad=16)
_ytop = max(v for k in ORDER for _, v in byc[k])
ax.set_ylim(0, _ytop * 1.16)

# pairwise Mann-Whitney vs unmodified, printed under each violin -- the comparison she wants this figure for
base = [v for _, v in byc.get("unModified", [])]
prow = []
for i, k in enumerate(ORDER):
    if k == "unModified" or not base: continue
    d = [v for _, v in byc[k]]
    if len(d) < 3: continue
    p = float(_st.mannwhitneyu(base, d, alternative="two-sided").pvalue)
    prow.append([k, len(d), round(float(np.median(d)), 2), round(p, 6), lib.sig_stars(p)])
    # stars sit just above THIS violin's own data, not at the axis ceiling where they ran into the title
    ax.text(i, max(d) + _ytop * 0.035, lib.sig_stars(p), ha="center", va="bottom", fontsize=10, color="#333")
plt.tight_layout()
plt.savefig(f"{OUT}/G1_violin2_all_cohorts.png", bbox_inches="tight")
plt.close()
lib.record_plot("G1_violin2_all_cohorts", ["cohort", "batch", "metaphase_duration_min"],
                [[k, b, round(v, 3)] for k in ORDER for b, v in byc[k]],
                {"type": "violin, all cohorts on one axis",
                 "groups": ORDER,
                 "error_bars": "SD (mean +/- 1 SD), per her 2026-08-17 rule",
                 "two_hit_definition": "On-target, # Sisterless KTs == 1, # Unique Targets >= 2",
                 "collagen": "plating substrate, kept as its own cohort (not a drug exclusion)",
                 "between_group_test": "Mann-Whitney U vs unmodified",
                 "pairwise_vs_unmodified": prow},
                SCRIPT, "Metaphase duration by cohort — four-ablation, two-hits-on-one-kinetochore and "
                        "collagen shown alongside every normal cohort")

# ───────────────────────────── (2) the table ──────────────────────────────────────────────────────────
coll = sorted(byc.get(COLLAGEN, []), key=lambda x: x[1])
trip = sorted(byc.get("3-Sister", []), key=lambda x: x[1])


def _q(vals, lo, hi):
    n = len(vals)
    if n == 0: return []
    k = max(1, int(round(n * 0.25)))
    return vals[:k] if lo else vals[-k:]


fast = _q(trip, True, False)          # fastest quartile = shortest metaphase
slow = _q(trip, False, True)          # slowest quartile = longest metaphase


def _stats(v):
    a = np.array([x[1] for x in v], float)
    if a.size == 0: return ["-"] * 5
    return [f"{a.size}", f"{a.mean():.1f}", f"{np.median(a):.1f}",
            f"{a.std(ddof=1):.1f}" if a.size > 1 else "-", f"{a.min():.1f}–{a.max():.1f}"]


tbl = [["group", "N", "mean (min)", "median (min)", "SD (min)", "range (min)"],
       ["collagen (all)", *_stats(coll)],
       ["triple ablation (all)", *_stats(trip)],
       ["triple ablation — fastest 25%", *_stats(fast)],
       ["triple ablation — slowest 25%", *_stats(slow)]]

percell = [["collagen cell", "metaphase duration (min)"]] + [[b, f"{v:.1f}"] for b, v in coll]
fastrows = [["fastest-quartile triple-ablation cell", "min"]] + [[b, f"{v:.1f}"] for b, v in fast]
slowrows = [["slowest-quartile triple-ablation cell", "min"]] + [[b, f"{v:.1f}"] for b, v in slow]

nrow = max(len(percell), len(fastrows), len(slowrows))
figH = 1.6 + 0.30 * (len(tbl) + nrow)
figT, axes = plt.subplots(2, 1, figsize=(17.0, figH),
                          gridspec_kw={"height_ratios": [len(tbl) + 1, nrow + 1]})
for a in axes: a.axis("off")


def draw(a, rows, x0=0.0, w=1.0, title=None, colw=None):
    t = a.table(cellText=[[str(c) for c in r] for r in rows[1:]], colLabels=[str(c) for c in rows[0]],
                loc="upper left", cellLoc="left", bbox=[x0, 0.0, w, 1.0], colWidths=colw)
    t.auto_set_font_size(False); t.set_fontsize(7.6)
    for (rr, cc), cell in t.get_celld().items():
        cell.set_linewidth(0.4)
        if rr == 0: cell.set_text_props(fontweight="bold"); cell.set_facecolor("#eeeeee")
    return t


draw(axes[0], tbl)
axes[0].set_title("Metaphase duration — collagen cells, and the fastest / slowest quartile of "
                  "triple-ablation cells", loc="left", fontweight="bold", fontsize=10)
# the three per-cell listings side by side
# batch names carry their DATE (a filename alone does not identify a raw file across dates), so the name
# column needs ~3x the width of the number column or the identity is clipped off.
for j, rr in enumerate((percell, fastrows, slowrows)):
    pad = [["", ""]] * (nrow - len(rr))
    draw(axes[1], rr + pad, x0=j / 3.0 + 0.005, w=1 / 3.0 - 0.01, colw=[0.76, 0.24])
plt.tight_layout()
plt.savefig(f"{OUT}/G1_collagen_duration_table.png", bbox_inches="tight")
plt.close()

lib.record_plot("G1_collagen_duration_table",
                ["section", "batch", "metaphase_duration_min"],
                [["collagen", b, round(v, 3)] for b, v in coll]
                + [["triple_fastest_quartile", b, round(v, 3)] for b, v in fast]
                + [["triple_slowest_quartile", b, round(v, 3)] for b, v in slow],
                {"type": "table",
                 "measured_quantity": "metaphase duration (Anaphase Onset - Metaphase Start)",
                 "quartile_rule": "ceil-rounded 25% of the triple-ablation cells at each end, sorted by duration",
                 "collagen_n": len(coll), "triple_n": len(trip),
                 "summary_rows": tbl},
                SCRIPT, "Collagen metaphase durations, with the fastest and slowest quartile of "
                        "triple-ablation cells for comparison")
print(f"collagen N={len(coll)}  triple N={len(trip)}  fastest25={len(fast)}  slowest25={len(slow)}")
print("wrote G1_violin2_all_cohorts.png and G1_collagen_duration_table.png")
