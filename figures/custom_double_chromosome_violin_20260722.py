"""custom_double_chromosome_violin_20260722.py — the DOUBLE-KINETOCHORE-ON-ONE-CHROMOSOME violins.

WHY THESE STOPPED APPEARING: double-chromosome cells (both kinetochores of ONE chromosome ablated) are
filtered OUT of every cohort violin by design — `g1_violin2._cohort_of` returns None for
`b in lib.double_chromosome_batches()`, and `lib.assign_cohorts` drops them too. They are a distinct
condition, not a 1/2/3-sisterless cell, so they were excluded to keep the cohorts clean — and with that
they simply vanished from the deck. The surviving trace of the pair is `G1_violin2_no_dc_offtarget`
("no double-chromosome"), which implies a with-DC companion once existed.

This rebuilds them as their OWN cohort, shown ALONGSIDE the standard groups rather than mixed into them:
  G1_violin_double_chromosome        mitotic duration, double-chromosome vs the standard cohorts
  G2_violin_double_chromosome_meta   metaphase duration, same comparison

Cohort membership comes from `lib.double_chromosome_batches()` (the kinetochoreless tag + the
comment patterns for "two KTs on one chromosome"), so it stays in sync with the rest of the codebase.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT1 = "/Volumes/4 MB/ablation_figures_20260625/group1"
OUT2 = "/Volumes/4 MB/ablation_figures_20260625/group2"
SCRIPT = __file__
lib.apply_style()

data, _ = lib.load_master()
dbl = lib.double_chromosome_batches()
# USER 2026-08-11: this figure must report the SAME numbers as "Violin 2 — metaphase duration by cohort
# (with matched controls)". include_double=True makes assign_cohorts hand back the double-chromosome
# cohort instead of emptying it, so BOTH figures now read the identical cohort from the identical call.
coh = lib.assign_cohorts(include_four=True, include_double=True)

COLS = {"unModified": "#7f7f7f", "Off-Target/Control": "#1b7837", "1-Sister": "#2166ac",
        "2-Sister": "#e08214", "3-Sister": "#b2182b", "double-chromosome": "#762a83",
        # user 2026-07-22: split the double-chromosome cells out by their sisterless-KT count too
        "DC · kinetochoreless": "#4a148c", "DC · 2-sis": "#8e24aa", "DC · 3-sis": "#c158dc"}

# WHAT THE THREE DC SUB-GROUPS ACTUALLY ARE (user asked, 2026-07-29 — answered here so the figure can say it).
# EVERY cell in all of them is the same experiment: BOTH kinetochores of ONE chromosome were ablated. The
# sub-groups are NOT three biological conditions — they are three different ways the master's
# `# Sisterless KTs` column happens to be filled in for that experiment:
#   DC · kinetochoreless  the column literally reads "kinetochoreless chromosome".
#   DC · 2-sis            the column records the ABLATION COUNT (2) instead of the tag. All three members are
#                         `20251021 double_ablation_single_chromosome_{1,4,9}`, whose own Notes read
#                         "destruction of both kinetochores on one chromosome" — i.e. identical to the group
#                         above, just labelled differently. Merging the two is a master-column decision, hers.
#   DC · 3-sis            the ONLY remaining member is `20250923 triple_ablation_collagen_2`, and even that is
#                         her own uncertain note ("i think theres at lease two on the same chromosome. exclude
#                         but could be neat anecdotal"). Its companion `20251029 triple_ablation_26` was a
#                         regex false positive and was removed from the cohort at source on 2026-07-29
#                         (lib.double_chromosome_batches) — its note is about cut chromosome ARMS.
#
# SHOULD THE THREE BE COMBINED? (user asked 2026-08-03) — tested, not guessed. With the outlier
# `20251029 single_ablation_8` dropped (per MANUAL_PLOT_EXCLUSIONS, unchanged here), mitotic-duration N is
# kinetochoreless=5, 2-sis=3, 3-sis=1 (total DC N=9). Kruskal-Wallis across all three:
# H=2.56, p=0.278 (scipy.stats.kruskal on [16.02,8.85,10.63,12.65,22.47] vs [12.67,11.68,10.0] vs [23.0]);
# pairwise kinetochoreless-vs-2-sis alone (the only pair both with N>=3): Mann-Whitney U=9, p=0.786.
# Indistinguishable AND every sub-group is tiny (N<=5) -> COMBINED into one pooled "double-chromosome"
# cohort below; the sub-group split is kept as backing detail in this comment/DC_GROUP_DEFS and in
# `dc_label`/the recorded plot-data CSV, but is no longer drawn as separate violins (was redundant with the
# pooled bar anyway — every point appeared twice). Re-split if DC·3-sis ever grows past N=1.
DC_GROUP_DEFS = ("all DC groups = BOTH kinetochores of ONE chromosome ablated; the split is only how the "
                 "master's '# Sisterless KTs' column was filled — 'kinetochoreless chromosome' vs the "
                 "ablation count. DC·2-sis notes read 'destruction of both kinetochores on one chromosome', "
                 "i.e. the same condition as DC·kinetochoreless. Combined into ONE pooled DC cohort here "
                 "(Kruskal-Wallis across the 3 sub-groups: H=2.56, p=0.278, ns; N=5/3/1) rather than shown "
                 "split — see builder comment for the numbers.")

def dc_label(r):
    v = (r.get("# Sisterless KTs", "") or "").strip().lower()
    if v.startswith("kinetochoreless"): return "DC · kinetochoreless"
    if v in ("2",): return "DC · 2-sis"
    if v in ("3",): return "DC · 3-sis"
    if v in ("1",): return "DC · 1-sis"
    return "DC · unspecified"


def cohort_lists(metric, plot_id=None):
    """metric: 'mitotic' or 'meta'. Returns ({cohort: [minutes]}, [dropped batches]) with double-chromosome
    added. plot_id, when given, honours the per-plot manual removals in
    annotations/MANUAL_PLOT_EXCLUSIONS.csv (lib.manual_plot_exclusions) — currently
    `20251029 single_ablation_8`, the 39.85 min outlier she asked to remove on 2026-07-29. The drop is
    reported back so the figure can SAY it was made rather than quietly showing a smaller N."""
    drop = lib.manual_plot_exclusions(plot_id) if plot_id else set()
    dropped = []
    g = defaultdict(list)
    byname = {r["Batch Name"]: r for r in data}
    for k, lst in coh.items():
        for item in lst:
            b = item[0] if isinstance(item, (list, tuple)) else item
            r = byname.get(b)
            if not r or b in dbl or b in drop:
                continue
            v = value(r, metric)
            if v is not None:
                g[k].append(v)
    # DC MEMBERSHIP COMES FROM assign_cohorts (2026-08-11), not from a second hand-rolled filter over `dbl`.
    # The old loop applied only is_mad1/is_drug/Exclude, so it kept cells that assign_cohorts drops for
    # OTHER reasons — the metaphase/prophase phase rule and REVIEW_EXCLUDE — and reported N=9 where Violin 2
    # reported N=6 for the same cohort in the same deck. One source, one number.
    for b, _dur in coh.get("Double Chromosome", []):
        r = byname.get(b)
        if not r:
            continue
        v = value(r, metric)
        if v is None:
            continue
        if b in drop:
            dropped.append((b, round(v, 1)))
            continue
        g["double-chromosome"].append(v)          # pooled
        g[dc_label(r)].append(v)                  # and split by how '# Sisterless KTs' was filled in
    return g, dropped


def value(r, metric):
    if metric == "meta":
        d = lib.parse_time(r.get("Meta Duration (s)", ""))
        if d is None:
            m0 = lib.parse_time(r.get("Metaphase Start (s)", ""))
            a0 = lib.parse_time(r.get("Anaphase Onset (s)", ""))
            d = (a0 - m0) if (m0 is not None and a0 is not None) else None
        return d / 60.0 if d and d > 0 else None
    d, ok = lib.mitotic_duration_min(r)
    return d if (ok and d and d > 0) else None


def draw(g, metric, fname, ylab, title, dropped=()):
    # DC sub-groups (kinetochoreless / 2-sis / 3-sis) are NOT drawn separately: Kruskal-Wallis across them
    # is ns (H=2.56, p=0.278, N=5/3/1 — see comment above) and every sub-group is tiny, so they are pooled
    # into the single "double-chromosome" bar to avoid both double-plotting each point and reading spurious
    # differences into noise. Sub-group membership is still recorded in the plot-data CSV via dc_label().
    order = [k for k in ("unModified", "Off-Target/Control", "1-Sister", "2-Sister", "3-Sister",
                         "double-chromosome") if len(g.get(k, [])) >= 2]
    if "double-chromosome" not in order:
        print(f"  {fname}: double-chromosome group has {len(g.get('double-chromosome', []))} cells — not drawn")
        return None
    fig, ax = plt.subplots(figsize=(11.2, 5.4))
    for i, k in enumerate(order):
        v = np.array(g[k], float)
        if len(v) > 1:
            for bd in ax.violinplot([v], positions=[i], widths=.72, showextrema=False)['bodies']:
                bd.set_facecolor(COLS.get(k, "#762a83")); bd.set_alpha(.25); bd.set_edgecolor(COLS.get(k, "#762a83"))
        ax.scatter(np.zeros(len(v)) + i + (np.random.RandomState(0).rand(len(v)) - .5) * .18, v,
                   s=26, color=COLS.get(k, "#762a83"), alpha=.85, edgecolor="none")
        # USER 2026-08-05: "the above mentioned violin plot is missing mean lines ... so add this".
        # Solid = median, dashed + hollow diamond = mean; same helper every other violin now uses.
        lib.violin_stats(ax, v, i, COLS.get(k, "#762a83"), half=0.3)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{k}\nN={len(g[k])}" for k in order], fontsize=7.6)
    ax.set_ylabel(ylab)
    # test the double-chromosome group against each standard cohort
    dc = g["double-chromosome"]; ps = []
    for k in order:
        if k.startswith("DC") or k == "double-chromosome" or len(g[k]) < 3 or len(dc) < 3:
            continue
        ps.append(f"vs {k}: p={stats.mannwhitneyu(dc, g[k])[1]:.3g}")
    # DC sub-groups combined into one bar above — say the test that justified it, ON the figure (not just in
    # a code comment), per her "should the three DC groups be combined" question (2026-08-03).
    sub = [g[k] for k in ("DC · kinetochoreless", "DC · 2-sis", "DC · 3-sis") if g.get(k)]
    kw_line = ""
    if len(sub) >= 2:
        try:
            H, p = stats.kruskal(*sub)
            ns = [len(s) for s in sub]
            kw_line = f"\nDC sub-groups (kinetochoreless/2-sis/3-sis, N={ns}) combined: Kruskal-Wallis H={H:.2f}, p={p:.3g} (ns) — pooled as one bar"
        except ValueError:
            pass
    ax.set_title(title + kw_line + ("\ndouble-chromosome " + " | ".join(ps) if ps else ""),
                 loc="left", fontweight="bold", fontsize=9.5)
    # Say on the FIGURE what the DC sub-groups are — she asked what they were, so the answer travels with
    # the PNG into the deck instead of living only in a builder comment.
    fig.text(0.008, -0.045, "DC = " + DC_GROUP_DEFS, fontsize=6.6, color="#444", ha="left", va="top", wrap=True)
    if dropped:
        fig.text(0.008, -0.105,
                 "removed on request (2026-07-29): " + "; ".join(f"{b} ({v} min)" for b, v in dropped)
                 + " — still in the master and in every other plot",
                 fontsize=6.6, color="#8b0000", ha="left", va="top")
    plt.tight_layout()
    fig.savefig(f"{fname}.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    return {k: len(g[k]) for k in order}


gm, dm = cohort_lists("mitotic", "G1_violin_double_chromosome")
n1 = draw(gm, "mitotic", f"{OUT1}/G1_violin_double_chromosome",
          # NOT "mitotic duration": lib.mitotic_duration_min is Metaphase Start -> Anaphase Onset, i.e. the
          # metaphase duration, and it never reads NEB. Verified 2026-07-29 — this figure's 305 recorded
          # values are byte-identical to G2_violin_double_chromosome_meta's. Labelled honestly; whether the
          # deck still wants two copies of the same measurement is hers to decide.
          "Metaphase duration (min)",
          "Double-kinetochore ablation on ONE chromosome — metaphase-to-anaphase duration vs the standard cohorts", dm)
if n1:
    lib.record_plot("G1_violin_double_chromosome", ["cohort", "mitotic_min"],
                    [[k, round(v, 2)] for k in gm for v in gm[k]], n1, SCRIPT,
                    "Double-chromosome cohort, metaphase duration (restored 2026-07-22; "
                    "relabelled from 'mitotic' 2026-07-29 — identical values to G2_..._meta)")
    print(f"G1_violin_double_chromosome {n1}")

gd, dd = cohort_lists("meta", "G2_violin_double_chromosome_meta")
n2 = draw(gd, "meta", f"{OUT2}/G2_violin_double_chromosome_meta",
          "Metaphase duration (min)",
          "Double-kinetochore ablation on ONE chromosome — metaphase duration vs the standard cohorts", dd)
if n2:
    lib.record_plot("G2_violin_double_chromosome_meta", ["cohort", "meta_min"],
                    [[k, round(v, 2)] for k in gd for v in gd[k]], n2, SCRIPT,
                    "Double-chromosome cohort, metaphase duration (restored 2026-07-22)")
    print(f"G2_violin_double_chromosome_meta {n2}")
