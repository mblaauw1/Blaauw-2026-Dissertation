"""custom_plots_to_make_part2_20260722.py — the remaining `plots to make.rtf` items.

Part 1 (`custom_plots_to_make_20260722.py`) covered #2 #6 #9 #10 #13 #14 #15 #16.
This covers:
  #1   G1_shape_rate_vs_congression        rapid cell shape change vs whether chromosomes congress
  #3   G2_trend_single_vs_triple           does the length->outcome trend hold in 1- vs 2/3-sisterless
  #7   G2_noc_washout_vs_prophase          noc washout behaving like a prophase ablation ("memory")
  #8   G4_sisterless_vs_paired_plate_dist  sisterless distance to plate vs the PAIRED/plate KTs' distance
  #11  G4_drug_vs_control_behaviour        do drug treatments change KT behaviour / oscillation
  #12  G2_combined_23_sisterless           2- and 3-sisterless pooled where it is defensible
  #17  G3_outcome_probability_by_length    P(state | chromosome length), split 1 vs 2/3 sisterless

Each function guards on data availability and says WHY it skipped rather than inventing a metric.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT1 = "/Volumes/4 MB/ablation_figures_20260625/group1"
OUT2 = "/Volumes/4 MB/ablation_figures_20260625/group2"
OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"
OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
lib.apply_style()

data, HDR = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in data}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()
def ps(b):
    try:
        v = float(gv(b, "Pixel Size (um)")); return v if v > 0 else 0.062
    except Exception: return 0.062

chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    chromo[r["batch"].strip()].append(r)

outl = defaultdict(dict)
_co = list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv")))
cx = {c: i for i, c in enumerate(_co[0])}
for r in _co[1:]:
    try:
        b = r[cx['batch']].strip(); p = np.array(json.loads(r[cx['points']]), float)
        if len(p) >= 6: outl[b][int(float(r[cx['frame']]))] = p
    except Exception: pass

plates = defaultdict(dict)
_mp = list(csv.reader(open("/Volumes/4 MB/annotations/meta_plates.csv")))
jx = {c: i for i, c in enumerate(_mp[0])}
for r in _mp[1:]:
    try:
        b = r[jx['batch']].strip(); p = np.array(json.loads(r[jx['points']]), float)
        if len(p) >= 2: plates[b][int(float(r[jx['frame']]))] = p
    except Exception: pass

ktp = defaultdict(lambda: defaultdict(list))
_kp = list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
kx = {c: i for i, c in enumerate(_kp[0])}
for r in _kp[1:]:
    lab = r[kx['label']].strip()
    if lab not in ("polar", "sisterless", "paired_kt", "pre_abl", "pre_abl_pair"): continue
    b = r[kx['batch']].strip()
    try: ktp[b][lab].append((int(float(r[kx['frame']])), float(r[kx['x']]), float(r[kx['y']])))
    except Exception: pass


def keep(b): return not lib.plot_excluded(b) and not lib.is_mad1(b)
def nsis(b):
    v = gv(b, "# Sisterless KTs")
    return v if v in ("1", "2", "3") else ""


def dist_to_plate(b, f, x, y):
    pl = plates.get(b)
    if not pl: return None
    pf = pl[f] if f in pl else pl[min(pl, key=lambda k: abs(k - f))]
    if len(pf) < 2: return None
    p = np.array([x, y], float); d = 1e18
    for i in range(len(pf) - 1):
        a, bb = pf[i], pf[i + 1]; ab = bb - a; L = float(np.dot(ab, ab))
        t = 0 if L < 1e-9 else float(np.clip(np.dot(p - a, ab) / L, 0, 1))
        d = min(d, float(np.hypot(*(a + t * ab - p))))
    return d * ps(b)


def violin(ax, groups, order, cols, ylab, title):
    """USER 2026-08-05: "make sure to include lines for mean and median, and also to include the median
    value for each group". Same convention the rest of the deck uses (ablation_count_by_cohort,
    Violin 2 - metaphase duration): SOLID line = median, DASHED line + open diamond = mean."""
    for i, g in enumerate(order):
        v = np.array(groups[g], float)
        if len(v) == 0: continue
        if len(v) > 1:
            for bd in ax.violinplot([v], positions=[i], widths=.7, showextrema=False)['bodies']:
                bd.set_facecolor(cols[g]); bd.set_alpha(.25); bd.set_edgecolor(cols[g])
        ax.scatter(np.zeros(len(v)) + i + (np.random.RandomState(0).rand(len(v)) - .5) * .18, v,
                   s=26, color=cols[g], alpha=.8, edgecolor="none")
        med = float(np.median(v)); mean = float(np.mean(v))
        ax.hlines(med, i - .3, i + .3, color=cols[g], lw=2.2, zorder=4)                       # median
        ax.hlines(mean, i - .24, i + .24, color=cols[g], lw=1.4, ls=(0, (2, 1.5)), zorder=4)  # mean
        ax.scatter([i], [mean], marker="D", s=30, facecolor="white", edgecolor=cols[g], lw=1.3, zorder=5)
        ax.text(i, float(v.max()), f"med {med:.2f}\nx\u0304 {mean:.2f}", ha="center", va="bottom",
                fontsize=7.5, color="#222")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{o}\nN={len(groups[o])}" for o in order])
    ax.set_ylabel(ylab); ax.set_title(title, loc="left", fontweight="bold", fontsize=9.5)


def shape_rate(b):
    """roundness change per frame from the manual outlines (4piA/P^2, shoelace area)."""
    o = outl.get(b, {})
    if len(o) < 3: return None
    fr = sorted(o); vals = []
    for f in fr:
        p = o[f]
        A = abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                    for i in range(len(p)))) / 2
        P = sum(float(np.hypot(*(p[(i + 1) % len(p)] - p[i]))) for i in range(len(p)))
        if P <= 0: continue
        vals.append((f, 4 * np.pi * A / (P * P)))
    if len(vals) < 3: return None
    span = vals[-1][0] - vals[0][0]
    if span <= 0: return None
    return float(np.mean(np.abs(np.diff([v for _, v in vals])))), span


# ================================================== #1
def p1():
    g = defaultdict(list); rows = []
    for b in outl:
        if not keep(b): continue
        rs = chromo.get(b, [])
        behs = [(r.get("behavior") or "").strip() for r in rs if (r.get("behavior") or "").strip()]
        if not behs: continue
        sr = shape_rate(b)
        if sr is None: continue
        allcong = all(x in ("congressed", "at_plate") for x in behs)
        anypolar = any(x == "noncongression" for x in behs)
        k = "all reached plate" if allcong else ("some stayed polar" if anypolar else "mixed")
        g[k].append(sr[0]); rows.append([k, round(sr[0], 6), b])
    order = [o for o in ("all reached plate", "some stayed polar") if len(g[o]) >= 3]
    if len(order) < 2: print(f"#1 skipped — groups {[(k,len(v)) for k,v in g.items()]}"); return
    # 2026-08-16 (NOTES §1 rule 30): "#1b7837" is GREEN and "#b2182b" is RED — the two categories a reader
    # most needs to separate were exactly the pair ~8% of men cannot. Vermillion (Okabe-Ito) keeps the warm
    # "stayed polar" reading while staying distinguishable from the green under deuteranopia.
    cols = {"all reached plate": "#1b7837", "some stayed polar": "#d55e00"}
    u, pv = stats.mannwhitneyu(g[order[0]], g[order[1]])
    fig, ax = plt.subplots(figsize=(6.4, 5))
    violin(ax, g, order, cols, "Cell roundness change per frame",
           f"Do cells that change shape faster lose grip on the plate?   MW p={pv:.3g}")
    plt.tight_layout(); fig.savefig(f"{OUT1}/G1_shape_rate_vs_congression.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G1_shape_rate_vs_congression", ["group", "roundness_rate", "batch"], rows,
                    {"p": float(pv), **{k: len(v) for k, v in g.items()}}, SCRIPT,
                    "Cell shape-change rate vs congression outcome (plots-to-make #1)")
    print(f"#1 p={pv:.3g} {[(k,len(v)) for k,v in g.items()]}")


# ================================================== #3 / #17
def _length_outcome_rows():
    out = []
    for b, rs in chromo.items():
        if not keep(b): continue
        n = nsis(b)
        if not n: continue
        for r in rs:
            try: L = float(r.get("length_um") or "")
            except Exception: continue
            beh = (r.get("behavior") or "").strip()
            if beh not in ("congressed", "at_plate", "noncongression"): continue
            # USER 2026-08-05: "leave double sisterless data out of it" — 2-sisterless is no longer
            # folded in with 3; only the 1- and 3-sisterless cohorts are carried.
            if n not in ("1", "3"): continue
            out.append((L, beh, f"{n}-sisterless", b))
    return out


def p3():
    """USER 2026-08-05: "i think right now you're including kinetochores that were already at the plate at
    metaphase onset in the 'reached plate' group. i want you to alter this plot so that theres actually a
    violin for at the plate before metaphase, congressed, and stayed polar - for each of the 1 and 3
    sisterless groups. moreover, put them on the same plot, not two separate plots, so i can easily compare"

    She is right: the old version pooled `at_plate` with `congressed` into one "reached plate" violin, which
    merges a kinetochore that never had to travel with one that did — the exact distinction the figure is
    about. Now three separate outcomes per cohort, six violins on ONE axis.
    """
    rows = _length_outcome_rows()
    if len(rows) < 20: print(f"#3 skipped — {len(rows)} rows"); return
    STATES = [("at_plate", "at plate\nbefore metaphase", "#2166ac"),
              ("congressed", "congressed", "#4daf4a"),
              ("noncongression", "stayed polar", "#d55e00")]   # rule 30: was red beside the green "congressed"
    GROUPS = ["1-sisterless", "3-sisterless"]
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    order, groups, cols, xticks = [], {}, {}, []
    pos = 0; stats_out = {}
    for gi, grp in enumerate(GROUPS):
        sub = [r for r in rows if r[2] == grp]
        vals = {}
        for beh, lab, c in STATES:
            v = [r[0] for r in sub if r[1] == beh]
            key = f"{grp}|{beh}"
            groups[key] = v; cols[key] = c; order.append(key)
            xticks.append(f"{lab}\nN={len(v)}")
            vals[beh] = v
        # within-cohort test across the three outcomes (only the states that actually have data)
        present = [v for v in (vals[b] for b, _, _ in STATES) if len(v) >= 3]
        if len(present) >= 2:
            try:
                h, pv = stats.kruskal(*present)
                stats_out[grp] = {"kruskal_p": float(pv), "n": {b: len(vals[b]) for b, _, _ in STATES},
                                  "median": {b: (round(float(np.median(vals[b])), 2) if vals[b] else None)
                                             for b, _, _ in STATES}}
            except Exception:
                pass
        if gi == 0: pos = len(order)
    violin(ax, groups, order, cols, "Chromosome length (µm)", "")
    ax.set_xticklabels(xticks, fontsize=8)
    ax.axvline(pos - 0.5, color="#888", ls=":", lw=1.2)      # divider between the two cohorts
    for gi, grp in enumerate(GROUPS):
        c = (gi * 3) + 1
        note = ""
        if grp in stats_out: note = f"\nKruskal p={stats_out[grp]['kruskal_p']:.3g}"
        ax.text(c, ax.get_ylim()[1], f"{grp}{note}", ha="center", va="bottom", fontweight="bold", fontsize=9)
    ax.set_title("Does the length-to-outcome trend hold in 3-sisterless cells as in 1-sisterless?\n"
                 "outcome split three ways — already at the plate, congressed, stayed polar "
                 "(double-sisterless excluded)",
                 loc="left", fontweight="bold", fontsize=10)
    ax.set_ylim(top=ax.get_ylim()[1] * 1.12)
    plt.tight_layout(rect=[0, 0, 1, .92])
    fig.savefig(f"{OUT2}/G2_trend_single_vs_triple.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G2_trend_single_vs_triple", ["length_um", "behavior", "group", "batch"],
                    [[round(a, 3), b2, c, d] for a, b2, c, d in rows], stats_out, SCRIPT,
                    "Chromosome length by outcome (at plate / congressed / stayed polar), 1 vs 3 sisterless")
    print(f"#3 {stats_out}")


def p17():
    rows = _length_outcome_rows()
    if len(rows) < 20: print(f"#17 skipped — {len(rows)} rows"); return
    fig, ax = plt.subplots(figsize=(7, 5))
    edges = np.percentile([r[0] for r in rows], [0, 25, 50, 75, 100])
    out = {}
    # USER 2026-08-03: "since essentially binned, would make more sense not as line plot". It was a
    # 4-point line per group, which reads as a continuous relationship when the underlying quantity is a
    # PROPORTION measured in four length quartiles. Drawn as grouped bars per quartile instead, with the
    # bin RANGE on the x tick (not a midpoint, which implied interpolation) and a Wilson 95% interval so
    # the small per-bin n is visible rather than implied by an annotation.
    GRPS = (("1-sisterless", "#2166ac"), ("2/3-sisterless", "#b2182b"))
    nb = len(edges) - 1
    W = 0.38
    def wilson(k, n, z=1.96):
        if n == 0: return 0.0, 0.0
        p = k / n; d = 1 + z*z/n
        c = (p + z*z/(2*n)) / d
        h = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
        return max(0.0, c-h), min(1.0, c+h)
    for gi, (grp, col) in enumerate(GRPS):
        xs, ys, ns, los, his = [], [], [], [], []
        for i in range(nb):
            sub = [r for r in rows if r[2] == grp and edges[i] <= r[0] <= edges[i + 1]]
            if len(sub) < 4: continue
            k = sum(1 for r in sub if r[1] == "noncongression")
            lo, hi = wilson(k, len(sub))
            xs.append(i); ys.append(100 * k / len(sub)); ns.append(len(sub))
            los.append(100 * k / len(sub) - 100 * lo); his.append(100 * hi - 100 * k / len(sub))
        if xs:
            pos = [x + (gi - 0.5) * W for x in xs]
            ax.bar(pos, ys, width=W, color=col, alpha=.85, edgecolor="white", label=f"{grp}")
            ax.errorbar(pos, ys, yerr=[los, his], fmt="none", ecolor="#333", elinewidth=1.0, capsize=3)
            for x, y, n in zip(pos, ys, ns):
                ax.annotate(f"n={n}", (x, y), fontsize=7, color="#333", xytext=(0, 3),
                            textcoords="offset points", ha="center")
            out[grp] = {"bin": [int(v) for v in xs], "p_polar": [round(v, 1) for v in ys], "n": ns}
    ax.set_xticks(range(nb))
    ax.set_xticklabels([f"{edges[i]:.1f}–{edges[i+1]:.1f}" for i in range(nb)])
    ax.set_ylim(0, 105)
    ax.set_xlabel("Chromosome length quartile (µm)"); ax.set_ylabel("P(stays polar)  %")
    ax.set_title("Probability a sisterless chromosome stays polar, by its length\n"
                 "length quartiles; 1-sisterless vs 2/3-sisterless cells",
                 loc="left", fontweight="bold", fontsize=10)
    ax.legend(fontsize=9)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_outcome_probability_by_length.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G3_outcome_probability_by_length", ["length_um", "behavior", "group", "batch"],
                    [[round(a, 3), b2, c, d] for a, b2, c, d in rows], out, SCRIPT,
                    "P(polar | length), 1 vs 2/3 sisterless (plots-to-make #17)")
    print(f"#17 {out}")


# ================================================== #12
def p12():
    """Pool 2- and 3-sisterless where the RTF says it is defensible (their metaphase durations do not
    differ). The pooling is only reported alongside the test that justifies it."""
    g = defaultdict(list)
    for r in data:
        b = r["Batch Name"]
        if not keep(b): continue
        n = nsis(b)
        if not n: continue
        d = lib.parse_time(r.get("Meta Duration (s)", ""))
        if d is None:
            m0 = lib.parse_time(r.get("Metaphase Start (s)", "")); a0 = lib.parse_time(r.get("Anaphase Onset (s)", ""))
            d = (a0 - m0) if (m0 is not None and a0 is not None) else None
        if d is None or d <= 0: continue
        g[n].append(d / 60.0)
    if len(g.get("2", [])) < 3 or len(g.get("3", [])) < 3:
        print(f"#12 skipped — 2sis={len(g.get('2',[]))} 3sis={len(g.get('3',[]))}"); return
    u, p23 = stats.mannwhitneyu(g["2"], g["3"])
    pooled = g["2"] + g["3"]
    p1v23 = stats.mannwhitneyu(g["1"], pooled)[1] if len(g.get("1", [])) >= 3 else float("nan")
    p1v3 = stats.mannwhitneyu(g["1"], g["3"])[1] if len(g.get("1", [])) >= 3 else float("nan")
    gg = {"1-sis": g.get("1", []), "2-sis": g["2"], "3-sis": g["3"], "2+3 pooled": pooled}
    order = [o for o in ("1-sis", "2-sis", "3-sis", "2+3 pooled") if len(gg[o]) >= 3]
    cols = {"1-sis": "#2166ac", "2-sis": "#e08214", "3-sis": "#b2182b", "2+3 pooled": "#762a83"}
    fig, ax = plt.subplots(figsize=(7.6, 5))
    violin(ax, gg, order, cols, "Metaphase duration (min)",
           f"Pooling 2- and 3-sisterless: 2 vs 3 p={p23:.3g} (n.s. justifies pooling)\n"
           f"1 vs 3 p={p1v3:.3g}   ->  1 vs pooled p={p1v23:.3g}")
    plt.tight_layout(); fig.savefig(f"{OUT2}/G2_combined_23_sisterless.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G2_combined_23_sisterless", ["group", "meta_min"],
                    [[k, round(v, 2)] for k in gg for v in gg[k]],
                    {"p_2v3": float(p23), "p_1v3": float(p1v3), "p_1v23pooled": float(p1v23),
                     **{k: len(v) for k, v in gg.items()}}, SCRIPT,
                    "2+3 sisterless pooled, with the test that justifies it (plots-to-make #12)")
    print(f"#12 p(2v3)={p23:.3g} p(1v3)={p1v3:.3g} p(1v2+3)={p1v23:.3g}")


# ================================================== #8
def p8():
    """Sisterless distance to the plate vs the PAIRED (plate-resident) kinetochores' distance in the
    same cell — manual paired_kt marks only, per the manual-over-TrackMate rule."""
    X, Y, C = [], [], []
    for b, labs in ktp.items():
        if not keep(b): continue
        sis = labs.get("sisterless") or labs.get("polar") or []
        pair = labs.get("paired_kt") or []
        if len(sis) < 3 or len(pair) < 2: continue
        ds = [d for d in (dist_to_plate(b, f, x, y) for f, x, y in sis) if d is not None]
        dp = [d for d in (dist_to_plate(b, f, x, y) for f, x, y in pair) if d is not None]
        if len(ds) < 3 or len(dp) < 2: continue
        X.append(float(np.median(dp))); Y.append(float(np.median(ds))); C.append(b)
    if len(X) < 4:
        print(f"#8 skipped — only {len(X)} cells have BOTH sisterless and manual paired_kt marks "
              f"(the known paired_kt annotation gap)"); return
    X = np.array(X); Y = np.array(Y)
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    ax.scatter(X, Y, s=46, color="#762a83", alpha=.85, edgecolor="#3b1250")
    m = max(X.max(), Y.max()) * 1.05
    ax.plot([0, m], [0, m], "--", color="#888", lw=1.2, label="equal distance")
    for x, y, b in zip(X, Y, C):
        ax.annotate(b.split()[-1], (x, y), fontsize=6, color="#555", xytext=(3, 3), textcoords="offset points")
    rho, pv = stats.spearmanr(X, Y)
    ax.set_xlabel("Median distance to plate — PAIRED (plate) kinetochores (µm)")
    ax.set_ylabel("Median distance to plate — SISTERLESS kinetochore (µm)")
    ax.set_title(f"Sisterless vs paired kinetochore distance from the plate\n"
                 f"same cell, manual marks — N={len(X)}; Spearman ρ={rho:.2f}, p={pv:.3g}",
                 loc="left", fontweight="bold", fontsize=10)
    ax.legend(fontsize=8)
    plt.tight_layout(); fig.savefig(f"{OUT4}/G4_sisterless_vs_paired_plate_dist.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G4_sisterless_vs_paired_plate_dist", ["paired_um", "sisterless_um", "batch"],
                    [[round(a, 3), round(c, 3), d] for a, c, d in zip(X, Y, C)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X)}, SCRIPT,
                    "Sisterless vs paired KT plate distance (plots-to-make #8)")
    print(f"#8 N={len(X)} rho={rho:.3f} p={pv:.3g}")


# ================================================== #11
def p11():
    """Do drug-treated cells show different KT behaviour? Uses lib.is_drug (the established tag) and the
    per-chromosome behaviour vocabulary; drug cells are normally excluded from every plot, so this is the
    dedicated comparison."""
    g = defaultdict(lambda: defaultdict(int)); durs = defaultdict(list)
    for b, rs in chromo.items():
        if lib.is_mad1(b): continue
        k = "drug-treated" if lib.is_drug(b) else "untreated"
        for r in rs:
            beh = (r.get("behavior") or "").strip()
            if beh in ("congressed", "at_plate", "noncongression"): g[k][beh] += 1
        d = lib.parse_time(gv(b, "Meta Duration (s)"))
        if d and d > 0: durs[k].append(d / 60.0)
    if sum(g["drug-treated"].values()) < 5:
        # 2026-07-22 (user): drug batches were never scored per-chromosome, but COLLAGEN batches were —
        # collagen is the treatment that actually has behaviour data, so compare that instead of skipping.
        # ── ITEM 33 (user 2026-08-04): "the right plot of metaphase duration is wrong as the metaphase
        # duration of collagen is marked as higher than no collagen when it should be lower."
        # She is right, and there were TWO faults:
        #  (1) COHORT CONFOUND. Collagen experiments are almost entirely 3-sisterless TRIPLE ablations, so
        #      pooling "all collagen" against "all no collagen" compared collagen-triples against a
        #      mostly-single-ablation rest. Pooled: no-collagen 10.99 vs collagen 13.24 min (collagen HIGHER).
        #      Matched on on-target 3-sisterless: no-collagen 22.67 vs collagen 13.33 min (collagen LOWER).
        #      Same failure mode as item 26 — a between-group offset masquerading as a treatment effect.
        #  (2) WRONG DENOMINATOR for the duration panel. `durs` was filled while looping CHROMOSOME_MASTER,
        #      so the duration comparison silently used only the handful of cells that happen to carry
        #      per-chromosome BEHAVIOUR rows (collagen n=4). Metaphase duration needs no behaviour data —
        #      every cell with a Meta Start/Anaphase Onset qualifies (collagen n=7 in the matched cohort).
        # NOTE: the master has NO substrate/collagen column, so the batch NAME is the only available signal
        # for collagen. That is a known gap (project_collagen_unnamed_confound) — flagged on the figure.
        COLL_COHORT = ("on-target", "3")     # the cohort the collagen experiments belong to
        def _is_coll(b): return "collagen" in b.lower()
        def _in_cohort(b):
            r = mr.get(b, {})
            return ("on-target" in (r.get("On-Target / Off-Target", "") or "").lower()
                    and (r.get("# Sisterless KTs", "") or "").strip() == COLL_COHORT[1])
        def _meta_min(b):
            d = lib.parse_time(gv(b, "Meta Duration (s)"))
            if d is None or d <= 0:
                m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
                d = (a0 - m0) if (m0 is not None and a0 is not None) else None
            return d / 60.0 if d and d > 0 else None
        g.clear(); durs.clear()
        # LEFT panel (behaviour): per-chromosome rows, same matched cohort
        for b, rs in chromo.items():
            if lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b): continue
            if not _in_cohort(b): continue
            k = "collagen" if _is_coll(b) else "no collagen"
            for r in rs:
                beh = (r.get("behavior") or "").strip()
                if beh in ("congressed", "at_plate", "noncongression"): g[k][beh] += 1
        # RIGHT panel (duration): EVERY cell in the matched cohort with a duration — behaviour not required
        for _r in data:
            b = _r["Batch Name"]
            if (_r.get("Exclude", "") or "").strip() in ("Yes", "yes"): continue
            if lib.is_mad1(b) or lib.is_drug(b) or lib.excluded(b): continue
            if not _in_cohort(b): continue
            d = _meta_min(b)
            if d is not None: durs["collagen" if _is_coll(b) else "no collagen"].append(d)
        keys = ["no collagen", "collagen"]
        title = ("Does collagen change kinetochore behaviour?   "
                 "(matched cohort: ON-TARGET 3-SISTERLESS only — collagen experiments are triples, so the "
                 "pooled comparison reversed the duration difference)")
        print(f"#11 collagen matched-cohort N: behaviour "
              f"{ {k: sum(v.values()) for k, v in g.items()} }  duration { {k: len(v) for k, v in durs.items()} }")
        if sum(g["collagen"].values()) < 5:
            print("#11 skipped — no treated group with behaviour rows"); return
    else:
        keys = ["untreated", "drug-treated"]
        title = "Do drug treatments change kinetochore behaviour?"
    behs = ["at_plate", "congressed", "noncongression"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    w = .35
    for i, k in enumerate(keys):
        tot = max(1, sum(g[k].values()))
        axes[0].bar(np.arange(len(behs)) + i * w, [100 * g[k][x] / tot for x in behs], w,
                    label=f"{k} (n={tot})", color=["#2166ac", "#b2182b"][i], alpha=.85)
    axes[0].set_xticks(np.arange(len(behs)) + w / 2); axes[0].set_xticklabels([b.replace("_", " ") for b in behs])
    axes[0].set_ylabel("% of sisterless chromosomes"); axes[0].legend(fontsize=8)
    axes[0].set_title("Chromosome outcome", loc="left", fontweight="bold", fontsize=9.5)
    if len(durs[keys[1]]) >= 3 and len(durs[keys[0]]) >= 3:
        pv = stats.mannwhitneyu(durs[keys[0]], durs[keys[1]])[1]
        violin(axes[1], durs, keys,
               {keys[0]: "#2166ac", keys[1]: "#b2182b"},
               "Metaphase duration (min)", f"Metaphase duration   MW p={pv:.3g}")
    fig.suptitle(title, fontweight="bold",
                 fontsize=11, x=.01, ha="left")
    plt.tight_layout(rect=[0, 0, 1, .93])
    fig.savefig(f"{OUT4}/G4_drug_vs_control_behaviour.png", bbox_inches="tight", dpi=130); plt.close(fig)
    try:
        tbl = np.array([[g[k][x] for x in behs] for k in keys])
        chi2, pchi = stats.chi2_contingency(tbl)[:2]
        axes[0].set_title(f"Chromosome outcome   chi2 p={pchi:.3g}", loc="left", fontweight="bold", fontsize=9.5)
    except Exception: pchi = float("nan")
    lib.record_plot("G4_drug_vs_control_behaviour", ["group", "behavior", "count"],
                    [[k, x, g[k][x]] for k in g for x in behs],
                    {k: dict(v) for k, v in g.items()}, SCRIPT,
                    "Drug vs untreated KT behaviour (plots-to-make #11)")
    print(f"#11 {dict((k, dict(v)) for k, v in g.items())}")


# ================================================== #7
def p7():
    """Noc washout vs prophase/prometaphase ablation — the 'memory' question. Groups by batch name
    (noc washout batches are named …noc…) and compares metaphase duration against the phase-of-ablation
    groups, which is the comparison the RTF asks for."""
    g = defaultdict(list)
    for r in data:
        b = r["Batch Name"]
        if lib.is_mad1(b): continue
        d = lib.parse_time(r.get("Meta Duration (s)", ""))
        if d is None or d <= 0: continue
        low = b.lower()
        # 2026-08-03 (her standing rule, restated: "Make sure everything uses the v2 designation of
        # prophase now (all plots everywhere)"). This read the raw column, so every batch whose Notes carry
        # the "v2=prometaphase" marker was still being counted as PROPHASE here while every other
        # phase-split plot had already rebinned it to prometaphase. Same rebin as group2_build.phase_of.
        ph = (r.get("Phase of Ablations", "") or "").strip().lower()
        if ph == "prophase" and lib.is_v2_prometaphase(b):
            ph = "prometaphase"
        if "noc" in low and ("washout" in low or "wash" in low):
            g["noc washout"].append(d / 60.0)
        elif lib.is_drug(b):
            continue
        elif ph == "prophase":
            g["prophase ablation"].append(d / 60.0)
        elif ph == "prometaphase":
            g["prometaphase ablation"].append(d / 60.0)
    order = [o for o in ("noc washout", "prophase ablation", "prometaphase ablation") if len(g[o]) >= 3]
    if "noc washout" not in order:
        print(f"#7 skipped — noc-washout batches with a metaphase duration: {len(g['noc washout'])}"); return
    cols = {"noc washout": "#762a83", "prophase ablation": "#1b7837", "prometaphase ablation": "#b2182b"}
    ttl = ""
    if "prophase ablation" in order and "prometaphase ablation" in order:
        p_a = stats.mannwhitneyu(g["noc washout"], g["prophase ablation"])[1]
        p_b = stats.mannwhitneyu(g["noc washout"], g["prometaphase ablation"])[1]
        ttl = f"   vs prophase p={p_a:.3g}   vs prometaphase p={p_b:.3g}"
    fig, ax = plt.subplots(figsize=(7.4, 5))
    violin(ax, g, order, cols, "Metaphase duration (min)",
           "Does a noc washout behave like a PROPHASE ablation? ('memory')" + ttl)
    # SUPERSEDED 2026-07-29 - do NOT write this figure here.
    # custom_noc_washout_v2_20260722.py owns the plot_id G2_noc_washout_vs_prophase. User 2026-07-22:
    # "this plots all noc washout batches as one group, all prophase batches as one group ... This should
    # instead be displayed like the G2_phase_split_violin_v2_tripledouble violin plot." The v2 script is
    # that rebuild and also applies the v2 prometaphase binning this version lacks.
    # Both scripts used to savefig + record_plot the same id, so whichever ran last silently won - the same
    # collision found on plot 186 the same day. The computation is left intact; only the write is removed.
    plt.tight_layout()
    plt.close(fig)
    print(f"#7 {[(k, len(v)) for k, v in g.items()]}  "
          f"(figure + registration NOT written — owned by custom_noc_washout_v2_20260722.py)")


if __name__ == "__main__":
    for fn in (p1, p3, p17, p12, p8, p11, p7):
        try: fn()
        except Exception as e:
            print(f"{fn.__name__} FAILED: {type(e).__name__}: {e}")
