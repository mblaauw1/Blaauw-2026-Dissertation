"""custom_plots_to_make_20260722.py — figures for `~/Documents/plots to make.rtf`.

Covers the items that are answerable from the MANUAL annotations alone (no TrackMate dependency), so they
are not blocked on the TrackMate work. Every metric is either copied from an existing builder or derived
from the user's own marks; nothing here invents a definition.

  #10  G3_length_by_behavior_group          polar vs at-plate vs congressing chromosome length
  #13  G3_lagging_vs_congression_balance    lagging likelihood vs how many chromosomes congressed
  #6   G4_polar_angle_to_plate              inside/outside polar placement as an ANGLE at the plate centre
  #14  G1_cell_centroid_movement_by_group   cell movement in the imaging plane, by cohort
  #16  G3_cell_movement_vs_polar_length_sum cell movement vs the SUM of polar chromosome length
  #15  G3_plate_rotation_vs_polar_length    plate pivot/rotation vs polar chromosome length

SOURCES: CHROMOSOME_MASTER (length, behavior), cell_outlines (centroid, cell frame),
meta_plates (plate line + its angle over time), kt_points polar/sisterless, ABLATION_MASTER (events, cohort).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT1 = "/Volumes/4 MB/ablation_figures_20260625/group1"
OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"
OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
lib.apply_style()

data, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in data}
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
outl_tsec = defaultdict(dict)      # ITEM M2-11 windowing: frame -> t_sec, same source rows as `outl`
_co = list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv")))
cx = {c: i for i, c in enumerate(_co[0])}
for r in _co[1:]:
    try:
        b = r[cx['batch']].strip(); p = np.array(json.loads(r[cx['points']]), float)
        fr = int(float(r[cx['frame']]))
        if len(p) >= 6: outl[b][fr] = p
        try: outl_tsec[b][fr] = float(r[cx['t_sec']])
        except Exception: pass
    except Exception: pass

plates = defaultdict(dict)
plates_tsec = defaultdict(dict)    # ITEM M2-11 windowing: frame -> t_sec, same source rows as `plates`
_mp = list(csv.reader(open("/Volumes/4 MB/annotations/meta_plates.csv")))
jx = {c: i for i, c in enumerate(_mp[0])}
for r in _mp[1:]:
    try:
        b = r[jx['batch']].strip(); p = np.array(json.loads(r[jx['points']]), float)
        fr = int(float(r[jx['frame']]))
        if len(p) >= 2: plates[b][fr] = p
        try: plates_tsec[b][fr] = float(r[jx['t_sec']])
        except Exception: pass
    except Exception: pass


# ITEM M2-11 (2026-08-03): "make sure plots of centroid movement, plate rotation etc are just of the
# metaphase to anaphase time region." HOUSE RULE: measure by FRAME, never by comparing raw t_sec (t_sec has
# two documented look-alike bugs on some rows -- see /Volumes/4 MB/_READ_FIRST_DATA_MAP.md §2b). So instead
# of filtering rows by "is t_sec between these two floats", we find the ANNOTATED FRAME nearest each event
# time (same nearest-frame pattern already used elsewhere in this file, e.g. p6's `pl[min(pl,key=...)]`),
# then filter every downstream computation by frame number. A batch missing either event, or whose window
# collapses (anaphase frame <= metaphase frame), is dropped and logged -- never given an assumed window.
def _nearest_frame(tsec_map, target_sec):
    if target_sec is None or not tsec_map: return None
    return min(tsec_map, key=lambda f: abs(tsec_map[f] - target_sec))


def meta_ana_frame_window(b, tsec_map, plot_id):
    m = lib.parse_time(gv(b, "Metaphase Start (s)")) or lib.parse_time(gv(b, "Metaphase Onset (s)"))
    a = lib.parse_time(gv(b, "Anaphase Onset (s)"))
    if m is None or a is None:
        lib.log_review(f"{plot_id}_window", b, "missing Metaphase Start / Anaphase Onset",
                        "cannot determine a metaphase->anaphase FRAME window for this batch -- excluded from "
                        "the windowed metric instead of using its full un-windowed track")
        return None, None
    mf = _nearest_frame(tsec_map, m); af = _nearest_frame(tsec_map, a)
    if mf is None or af is None or af <= mf:
        lib.log_review(f"{plot_id}_window", b, f"mf={mf} af={af}",
                        "no annotated frame falls in a valid metaphase->anaphase span for this batch -- "
                        "excluded from the windowed metric")
        return None, None
    return mf, af

kt = defaultdict(list)
_kp = list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
kx = {c: i for i, c in enumerate(_kp[0])}
for r in _kp[1:]:
    if r[kx['label']].strip() not in ("polar", "sisterless"): continue
    b = r[kx['batch']].strip()
    if lib.plot_excluded(b) or lib.is_mad1(b): continue
    try: kt[b].append((int(float(r[kx['frame']])), float(r[kx['x']]), float(r[kx['y']])))
    except Exception: pass


def keep(b):
    return not lib.plot_excluded(b) and not lib.is_mad1(b)


def violin(ax, groups, order, cols, ylab, title):
    for i, g in enumerate(order):
        v = np.array(groups[g], float)
        if len(v) == 0: continue
        if len(v) > 1:
            for bd in ax.violinplot([v], positions=[i], widths=.7, showextrema=False)['bodies']:
                bd.set_facecolor(cols[g]); bd.set_alpha(.25); bd.set_edgecolor(cols[g])
        ax.scatter(np.zeros(len(v)) + i + (np.random.RandomState(0).rand(len(v)) - .5) * .18, v,
                   s=26, color=cols[g], alpha=.8, edgecolor="none")
        ax.hlines(np.median(v), i - .3, i + .3, color=cols[g], lw=2.2)
    # N goes in the tick label, not floating at the top where it collided with the title
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{o.replace('_',' ')}\nN={len(groups[o])}" for o in order])
    ax.set_ylabel(ylab); ax.set_title(title, loc="left", fontweight="bold", fontsize=9.5)


# ============================================================ #10
def p10():
    g = defaultdict(list)
    for b, rs in chromo.items():
        if not keep(b): continue
        for r in rs:
            try: L = float(r.get("length_um") or "")
            except Exception: continue
            beh = (r.get("behavior") or "").strip()
            if beh in ("noncongression", "at_plate", "congressed"): g[beh].append(L)
    order = [o for o in ("at_plate", "congressed", "noncongression") if len(g[o]) >= 2]
    if len(order) < 2: print("#10 too few"); return
    cols = {"at_plate": "#1b7837", "congressed": "#2166ac", "noncongression": "#b2182b"}
    fig, ax = plt.subplots(figsize=(6.6, 5))
    ttl = ""
    if len(order) >= 2:
        u, p = stats.mannwhitneyu(g[order[0]], g[order[-1]])
        ttl = f"   {order[0]} vs {order[-1]}: MW p={p:.3g}"
    violin(ax, g, order, cols, "Chromosome length (µm)",
           "Chromosome length by outcome — immediate-plate vs congressing vs polar" + ttl)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_length_by_behavior_group.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G3_length_by_behavior_group", ["behavior", "length_um"],
                    [[k, round(v, 3)] for k in g for v in g[k]],
                    {k: len(v) for k, v in g.items()}, SCRIPT,
                    "Chromosome length by behaviour group (plots-to-make #10)")
    print(f"#10 {[(k, len(v)) for k, v in g.items()]}")


# ============================================================ #13  -- RETIRED 2026-08-08
# SUPERSEDED. `custom_lagging_congression_doubleablation_split_20260803.py` is the rebuild of
# `G3_lagging_vs_congression_balance` she asked for in feedback M2-02 (individual cells as jittered dots
# per bin, double-ablation cells drawn as a separate labelled series). BOTH scripts were writing that same
# plot_id, so whichever ran last silently won -- exactly the failure NOTES section 8 records ("TWO SCRIPTS
# CAN WRITE THE SAME plot_id AND THE LAST ONE SILENTLY WINS ... Fix by removing the superseded WRITE, never
# by ordering"). This older version is disabled rather than deleted so the earlier analysis stays readable.
def p13_RETIRED_20260808():
    xs, ys, cells = [], [], []
    for b, rs in chromo.items():
        if not keep(b): continue
        behs = [(r.get("behavior") or "").strip() for r in rs]
        if not behs or any(x == "" for x in behs): continue
        n = len(behs)
        if n < 2: continue
        ncong = sum(1 for x in behs if x in ("congressed", "at_plate"))
        lag = gv(b, "Lagging Chromosomes").strip().lower()
        if lag not in ("yes", "no"): continue
        xs.append(ncong / n); ys.append(1 if lag == "yes" else 0); cells.append(b)
    if len(xs) < 8: print(f"#13 only {len(xs)} cells"); return
    xs = np.array(xs); ys = np.array(ys)
    bins = [(-.01, .34), (.34, .67), (.67, 1.01)]
    lab = ["≤1/3 congressed", "1/3–2/3", ">2/3 congressed"]
    frac, ns = [], []
    for lo, hi in bins:
        m = (xs > lo) & (xs <= hi)
        frac.append(100 * ys[m].mean() if m.sum() else 0); ns.append(int(m.sum()))
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    ax.bar(range(3), frac, color="#e08214", alpha=.85)
    for i, (f, n) in enumerate(zip(frac, ns)):
        ax.text(i, f + 1.5, f"{f:.0f}%\nN={n}", ha="center", fontsize=9)
    rho, pv = stats.spearmanr(xs, ys)
    ax.set_xticks(range(3)); ax.set_xticklabels(lab)
    ax.set_ylabel("Cells with lagging chromosomes (%)")
    # 2026-08-04: the second title line ran the full width of the axes and collided with the "% / N=" label
    # over the right-hand bar. Keep the question in the title; move the method + statistics under the axes,
    # and give the bar labels headroom so nothing sits on top of them.
    ax.set_title("Is lagging more likely when MORE chromosomes congress?",
                 loc="left", fontweight="bold", fontsize=10.5)
    ax.set_ylim(top=max(frac) * 1.18 if frac else 1)
    ax.text(0.0, -0.13,
            f"x = fraction of the cell's sisterless chromosomes that reached the plate.  "
            f"N={len(xs)} cells; Spearman ρ={rho:.2f}, p={pv:.3g}",
            transform=ax.transAxes, ha="left", va="top", fontsize=7.6, color="#555")
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_lagging_vs_congression_balance.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G3_lagging_vs_congression_balance", ["frac_congressed", "lagging", "batch"],
                    [[round(a, 3), int(c), d] for a, c, d in zip(xs, ys, cells)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(xs)}, SCRIPT,
                    "Lagging likelihood vs fraction congressed (plots-to-make #13)")
    print(f"#13 N={len(xs)} rho={rho:.3f} p={pv:.3g}")


# ============================================================ #6
def p6():
    """Inside/outside polar placement as the ANGLE the KT makes at the plate CENTRE, measured from the
    plate line. 0 deg = along the plate (lateral/'outside'), 90 deg = straight off the plate face
    (toward the pole, 'inside' the spindle). Cell outline supplies the centre the RTF asks for."""
    rows = []
    for b, marks in kt.items():
        if not keep(b): continue
        beh = chromo.get(b, [{}])[0].get("behavior", "").strip() if len(chromo.get(b, [])) == 1 else ""
        for (f, x, y) in marks:
            pl = plates.get(b, {})
            if not pl: continue
            pf = pl[f] if f in pl else pl[min(pl, key=lambda k: abs(k - f))]
            o = outl.get(b, {})
            if not o: continue
            of = o[f] if f in o else o[min(o, key=lambda k: abs(k - f))]
            c = of.mean(0)                                   # cell centre from the outline
            d1 = pf[-1] - pf[0]; n = np.hypot(*d1)
            if n < 1e-6: continue
            d1 = d1 / n
            v = np.array([x, y]) - c
            nv = np.hypot(*v)
            if nv < 1e-6: continue
            cosang = abs(float(np.dot(v / nv, d1)))
            ang = np.degrees(np.arccos(np.clip(cosang, 0, 1)))   # 0 = along plate, 90 = off its face
            rows.append((ang, beh, b))
    if len(rows) < 20: print(f"#6 only {len(rows)}"); return
    g = defaultdict(list)
    for ang, beh, b in rows:
        if beh in ("noncongression", "congressed", "at_plate"): g[beh].append(ang)
    order = [o for o in ("at_plate", "congressed", "noncongression") if len(g[o]) >= 3]
    cols = {"at_plate": "#1b7837", "congressed": "#2166ac", "noncongression": "#b2182b"}
    fig, ax = plt.subplots(figsize=(6.8, 5))
    if order:
        violin(ax, g, order, cols, "Angle at the cell centre (deg)\n0 = along the plate, 90 = off its face",
               "Polar-KT placement as an ANGLE to the metaphase plate")
    else:
        ax.hist([r[0] for r in rows], bins=18, color="#762a83", alpha=.8)
        ax.set_xlabel("Angle at the cell centre (deg)"); ax.set_ylabel("marks")
        ax.set_title("Polar-KT placement angle to the plate", loc="left", fontweight="bold", fontsize=10)
    plt.tight_layout(); fig.savefig(f"{OUT4}/G4_polar_angle_to_plate.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G4_polar_angle_to_plate", ["angle_deg", "behavior", "batch"],
                    [[round(a, 2), c, d] for a, c, d in rows], {k: len(v) for k, v in g.items()},
                    SCRIPT, "Polar KT angle to the metaphase plate (plots-to-make #6)")
    print(f"#6 N={len(rows)} groups={[(k, len(v)) for k, v in g.items()]}")


# ============================================================ #14 / #16
def centroid_series(b):
    o = outl.get(b, {})
    if len(o) < 3: return None
    fr = sorted(o)
    return [(f, o[f].mean(0)) for f in fr]


def p14_16():
    coh = {}
    try:
        cohorts = lib.assign_cohorts()
        if isinstance(cohorts, dict):
            for k, v in cohorts.items():
                for item in v:
                    bb = item[0] if isinstance(item, (list, tuple)) else item
                    coh[bb] = k
    except Exception as e:
        print("cohort lookup failed:", e)
    g = defaultdict(list); rows = []
    for b in outl:
        if not keep(b): continue
        cs = centroid_series(b)
        if not cs: continue
        p = ps(b)
        tot = sum(float(np.hypot(*(cs[i + 1][1] - cs[i][1]))) * p for i in range(len(cs) - 1))
        span = cs[-1][0] - cs[0][0]
        if span <= 0: continue
        rate = tot / span                      # µm per frame of outline coverage
        # ITEM M2-12 (2026-08-03): a batch with no cohort in assign_cohorts() used to fall into a literal
        # "unassigned" bucket and get PLOTTED as if it were a real group. assign_cohorts() now logs a
        # specific reason for every such batch (see lib.assign_cohorts "cohort_assign_gap"); here we just
        # drop it from the plot instead of inventing a fake group, and log which cells were dropped from
        # THIS plot specifically so the drop is auditable per-figure too.
        c = coh.get(b)
        if c is None:
            lib.log_review("G1_centroid_movement_unassigned", b, "no cohort",
                            "no cohort from assign_cohorts() -- dropped from G1_cell_centroid_movement_by_group "
                            "instead of being plotted as a literal 'unassigned' group (see lib.assign_cohorts "
                            "cohort_assign_gap log for why)")
            continue
        g[c].append(rate); rows.append([c, round(rate, 4), b])
    order = [k for k in g if len(g[k]) >= 3]
    if not order: print("#14 no cohorts"); return
    order = sorted(order, key=lambda k: -len(g[k]))[:5]
    cols = {k: c for k, c in zip(order, ["#1b7837", "#2166ac", "#b2182b", "#e08214", "#762a83"])}
    fig, ax = plt.subplots(figsize=(7.2, 5))
    violin(ax, g, order, cols, "Cell-centroid movement (µm per outline frame)",
           "Cell movement in the imaging plane, by group (manual cell outlines)")
    plt.tight_layout(); fig.savefig(f"{OUT1}/G1_cell_centroid_movement_by_group.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G1_cell_centroid_movement_by_group", ["cohort", "um_per_frame", "batch"], rows,
                    {k: len(v) for k, v in g.items()}, SCRIPT,
                    "Cell centroid movement by cohort (plots-to-make #14)")
    print(f"#14 {[(k, len(v)) for k, v in g.items()]}")

    # ---- #16: same movement vs the SUM of polar chromosome length ----
    # ITEM M2-11: span used to be first-to-last OUTLINE frame (whole traced range). Restricted here to the
    # Metaphase Start -> Anaphase Onset FRAME window (meta_ana_frame_window), matching her "just the
    # metaphase to anaphase time region" instruction.
    X, Y, C = [], [], []
    for b in outl:
        if not keep(b): continue
        rs = chromo.get(b, [])
        pol = [r for r in rs if (r.get("behavior") or "").strip() == "noncongression"
               and (r.get("length_um") or "").strip()]
        if not pol: continue
        try: s = sum(float(r["length_um"]) for r in pol)
        except Exception: continue
        cs_full = centroid_series(b)
        if not cs_full: continue
        mf, af = meta_ana_frame_window(b, outl_tsec.get(b, {}), "G3_cell_movement_vs_polar_length_sum")
        if mf is None: continue
        cs = [(f, c) for (f, c) in cs_full if mf <= f <= af]
        if len(cs) < 3: continue
        p = ps(b)
        tot = sum(float(np.hypot(*(cs[i + 1][1] - cs[i][1]))) * p for i in range(len(cs) - 1))
        span = cs[-1][0] - cs[0][0]
        if span <= 0: continue
        X.append(s); Y.append(tot / span); C.append(b)
    if len(X) >= 5:
        X = np.array(X); Y = np.array(Y)
        rho, pv = stats.spearmanr(X, Y)
        fig, ax = plt.subplots(figsize=(6.4, 5))
        ax.scatter(X, Y, s=42, color="#762a83", alpha=.85, edgecolor="#3b1250")
        if len(X) >= 4:
            m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
            ax.plot(xr, m * xr + c0, "--", color="#b30000", lw=1.6)
        ax.set_xlabel("Sum of polar chromosome length in the cell (µm)")
        ax.set_ylabel("Cell-centroid movement (µm/frame)")
        ax.set_title(f"Does a bigger polar chromosome load move the cell more?\n"
                     f"metaphase onset -> anaphase onset only — N={len(X)} cells; Spearman ρ={rho:.2f}, p={pv:.3g}",
                     loc="left", fontweight="bold", fontsize=10)
        plt.tight_layout(); fig.savefig(f"{OUT3}/G3_cell_movement_vs_polar_length_sum.png",
                                        bbox_inches="tight", dpi=130); plt.close(fig)
        lib.record_plot("G3_cell_movement_vs_polar_length_sum",
                        ["polar_length_sum_um", "um_per_frame", "batch"],
                        [[round(a, 3), round(c, 4), d] for a, c, d in zip(X, Y, C)],
                        {"rho": round(float(rho), 3), "p": float(pv), "N": len(X),
                         "window": "meta_to_ana (frame-based, item M2-11)"}, SCRIPT,
                        "Cell movement vs summed polar chromosome length, metaphase-anaphase only (plots-to-make #16)")
        print(f"#16 N={len(X)} rho={rho:.3f} p={pv:.3g}")
    else:
        print(f"#16 only {len(X)} cells")


# ============================================================ #15
def p15():
    # ITEM M2-11: this used to compute rotation over the WHOLE plates track (no window, no companion).
    # Restricted here to the Metaphase Start -> Anaphase Onset FRAME window (meta_ana_frame_window), matching
    # her "just the metaphase to anaphase time region" instruction, and matching #16's fix above and
    # item M2-13's request that this be the plate-rotation analogue of G3_cell_movement_vs_polar_length_sum.
    X, Y, C = [], [], []
    for b, pl_full in plates.items():
        if not keep(b) or len(pl_full) < 3: continue
        rs = chromo.get(b, [])
        pol = [r for r in rs if (r.get("behavior") or "").strip() == "noncongression"
               and (r.get("length_um") or "").strip()]
        if not pol: continue
        try: s = sum(float(r["length_um"]) for r in pol)
        except Exception: continue
        mf, af = meta_ana_frame_window(b, plates_tsec.get(b, {}), "G3_plate_rotation_vs_polar_length")
        if mf is None: continue
        pl = {f: v for f, v in pl_full.items() if mf <= f <= af}
        if len(pl) < 3: continue
        fr = sorted(pl)
        angs = []
        for f in fr:
            v = pl[f][-1] - pl[f][0]
            if np.hypot(*v) < 1e-6: continue
            angs.append((f, np.degrees(np.arctan2(v[1], v[0])) % 180.0))
        if len(angs) < 3: continue
        tot = 0.0
        for i in range(len(angs) - 1):
            d = abs(angs[i + 1][1] - angs[i][1]) % 180.0
            tot += min(d, 180.0 - d)                 # undirected rotation, ±90 unwrapped
        span = angs[-1][0] - angs[0][0]
        if span <= 0: continue
        X.append(s); Y.append(tot / span); C.append(b)
    if len(X) < 5:
        print(f"#15 only {len(X)} cells"); return
    X = np.array(X); Y = np.array(Y)
    rho, pv = stats.spearmanr(X, Y)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.scatter(X, Y, s=42, color="#e08214", alpha=.85, edgecolor="#7a4300")
    if len(X) >= 4:
        m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
        ax.plot(xr, m * xr + c0, "--", color="#b30000", lw=1.6)
    ax.set_xlabel("Sum of polar chromosome length in the cell (µm)")
    ax.set_ylabel("Metaphase-plate rotation (deg/frame)")
    ax.set_title(f"Does the plate pivot more when the polar chromosomes are larger?\n"
                 f"undirected rotation of the drawn plate line, metaphase onset -> anaphase onset only — "
                 f"N={len(X)} cells; Spearman ρ={rho:.2f}, p={pv:.3g}", loc="left", fontweight="bold", fontsize=10)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_plate_rotation_vs_polar_length.png",
                                    bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G3_plate_rotation_vs_polar_length", ["polar_length_sum_um", "deg_per_frame", "batch"],
                    [[round(a, 3), round(c, 4), d] for a, c, d in zip(X, Y, C)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X),
                     "window": "meta_to_ana (frame-based, item M2-11)"}, SCRIPT,
                    "Plate rotation vs summed polar chromosome length, metaphase-anaphase only (plots-to-make #15)")
    print(f"#15 N={len(X)} rho={rho:.3f} p={pv:.3g}")




# ============================================================ #9  spindle spin by cohort
def p9():
    """Plate rotation (a proxy for spindle spin) between metaphase and anaphase, per cohort.
    Same undirected ±90-unwrapped rotation used by metaplate_rotation_by_sisterless."""
    coh = {}
    try:
        c = lib.assign_cohorts()
        if isinstance(c, dict):
            for k, v in c.items():
                for it in v:
                    coh[it[0] if isinstance(it, (list, tuple)) else it] = k
    except Exception: pass
    g = defaultdict(list); rows = []
    for b, pl in plates.items():
        if not keep(b) or len(pl) < 3: continue
        meta = lib.parse_time(gv(b, "Metaphase Start (s)")); ana = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        fr = sorted(pl)
        angs = []
        for f in fr:
            v = pl[f][-1] - pl[f][0]
            if np.hypot(*v) < 1e-6: continue
            angs.append((f, np.degrees(np.arctan2(v[1], v[0])) % 180.0))
        if len(angs) < 3: continue
        tot = 0.0
        for i in range(len(angs) - 1):
            dd = abs(angs[i + 1][1] - angs[i][1]) % 180.0
            tot += min(dd, 180.0 - dd)
        span = angs[-1][0] - angs[0][0]
        if span <= 0: continue
        # ITEM M2-12 (2026-08-03): same fix as G1_cell_centroid_movement_by_group above -- don't invent a
        # literal "unassigned" plotted group; drop + log instead. See lib.assign_cohorts cohort_assign_gap
        # for the per-batch reason.
        k = coh.get(b)
        if k is None:
            lib.log_review("G3_plate_rotation_by_group_unassigned", b, "no cohort",
                            "no cohort from assign_cohorts() -- dropped from G3_plate_rotation_by_group instead "
                            "of being plotted as a literal 'unassigned' group (see lib.assign_cohorts "
                            "cohort_assign_gap log for why)")
            continue
        g[k].append(tot / span); rows.append([k, round(tot / span, 4), b])
    order = sorted([k for k in g if len(g[k]) >= 3], key=lambda k: -len(g[k]))[:5]
    if not order: print("#9 no cohorts"); return
    cols = {k: c for k, c in zip(order, ["#1b7837", "#2166ac", "#b2182b", "#e08214", "#762a83"])}
    fig, ax = plt.subplots(figsize=(7.2, 5))
    ttl = ""
    if len(order) >= 2:
        u, pv = stats.mannwhitneyu(g[order[0]], g[order[1]])
        ttl = f"   {order[0]} vs {order[1]}: MW p={pv:.3g}"
    violin(ax, g, order, cols, "Plate rotation (deg per outline frame)",
           "Spindle spin (metaphase-plate rotation) by group" + ttl)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_plate_rotation_by_group.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G3_plate_rotation_by_group", ["cohort", "deg_per_frame", "batch"], rows,
                    {k: len(v) for k, v in g.items()}, SCRIPT,
                    "Spindle spin by cohort (plots-to-make #9)")
    print(f"#9 {[(k, len(v)) for k, v in g.items()]}")


# ============================================================ #2  chromosome flux to/from the plate
def p2():
    """How much a sisterless chromosome shuttles toward/away from the plate, vs metaphase duration.
    flux = mean |change in plate distance| per 20 s over the KT's track (manual marks only)."""
    X, Y, C = [], [], []
    for b, marks in kt.items():
        if not keep(b): continue
        pl = plates.get(b)
        if not pl or len(marks) < 6: continue
        p = ps(b)
        seq = sorted(marks)
        ds = []
        for (f, x, y) in seq:
            pf = pl[f] if f in pl else pl[min(pl, key=lambda k: abs(k - f))]
            if len(pf) < 2: continue
            d = 1e18
            for i in range(len(pf) - 1):
                a, bb = pf[i], pf[i + 1]; ab = bb - a; L = float(np.dot(ab, ab))
                tt = 0 if L < 1e-9 else float(np.clip(np.dot(np.array([x, y]) - a, ab) / L, 0, 1))
                d = min(d, float(np.hypot(*(a + tt * ab - np.array([x, y])))))
            ds.append(d * p)
        if len(ds) < 5: continue
        flux = float(np.mean(np.abs(np.diff(ds))))
        dur = lib.parse_time(gv(b, "Meta Duration (s)"))
        if dur is None:
            m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
            dur = (a0 - m0) if (m0 is not None and a0 is not None) else None
        if dur is None or dur <= 0: continue
        X.append(flux); Y.append(dur / 60.0); C.append(b)
    if len(X) < 6: print(f"#2 only {len(X)}"); return
    X = np.array(X); Y = np.array(Y)
    rho, pv = stats.spearmanr(X, Y)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.scatter(X, Y, s=42, color="#2166ac", alpha=.85, edgecolor="#10345c")
    if len(X) >= 4:
        m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
        ax.plot(xr, m * xr + c0, "--", color="#b30000", lw=1.6)
    ax.set_xlabel("Chromosome flux toward/away from the plate (µm per step)")
    ax.set_ylabel("Metaphase duration (min)")
    ax.set_title(f"Does a chromosome that shuttles more take longer in metaphase?\n"
                 f"manual sisterless/polar tracks — N={len(X)} cells; Spearman ρ={rho:.2f}, p={pv:.3g}",
                 loc="left", fontweight="bold", fontsize=10)
    plt.tight_layout(); fig.savefig(f"{OUT4}/G4_chromosome_flux_vs_metaphase.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G4_chromosome_flux_vs_metaphase", ["flux_um_per_step", "meta_min", "batch"],
                    [[round(a, 4), round(c, 2), d] for a, c, d in zip(X, Y, C)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X)}, SCRIPT,
                    "Chromosome flux vs metaphase duration (plots-to-make #2)")
    print(f"#2 N={len(X)} rho={rho:.3f} p={pv:.3g}")


if __name__ == "__main__":
    p10(); p6(); p14_16(); p15(); p9(); p2()   # p13 retired 2026-08-08 (plot_id collision, see above)
    lib.flush_review("/Volumes/4 MB/ablation_figures_20260625/_review/outlier_review_custom20260722.csv")
