"""Meta-figure SUB-ITEMS she asked for alongside the 8 topics (2026-07-29g).

M4a  DEMO_shape_rate_vs_metaphase_SINGLE_AND_TRIPLE
     "modify so that it includes not just the single sisterless group, but also the triple sisterless group
      (but dont combine into one giant group; so top two plots will have separate trendlines for each and
      there will be 4 box plots on each of the lower two plots"
     -> the existing composite, but 1-Sister and 3-Sister overlaid: one trendline EACH on the two scatters,
        and slow/fast x single/triple = 4 boxes on each lower panel. The separate _single and _triple
        figures are left exactly as they are.

M4b  G1_shape_rate_vs_polar_fraction  and  G1_shape_rate_vs_lagging_fraction
     "should have a different title, such as 'Do cells that change shape faster have different liklihoods
      for entering anaphase with polar or lagging kinetochores?' and should instead be plotted as y-axis as
      it is now, but instead of violin plots, make x-axis the ratio of kinetochores that stayed polar
      (perhaps use different color markers for the different groups of 1,2,3 sisterless); and then make a
      corresponding plot for percent that turn lagging"
     -> y stays the roundness-change rate. x becomes the FRACTION of that cell's scored chromosomes that
        stayed polar, marker colour by 1/2/3 sisterless. The old violin figure is not touched.
     ** THE LAGGING VERSION IS PARTLY BLOCKED AND SAYS SO ON THE FIGURE. ** CHROMOSOME_MASTER carries
        `behavior` (congressed / noncongression / at_plate) and `n_sisterless` but NO per-chromosome lagging
        column. For 1-sisterless cells the fraction is exact - the standing rule is master
        `Lagging Chromosomes` yes->1 / no->0 over that cell's single sisterless chromosome
        (memory/project_sisterless_plate_join). For 2-/3-sisterless cells only a CELL-LEVEL yes/no exists,
        so their fraction is unknown and they are drawn as open markers pinned at the cell-level value.
        This is exactly the gap she offered to fill - the 46 cells on port 8817. Once those are annotated
        this script produces the real fractions with no code change.

M4d  G4_plate_distance_time_roundness_1sis / _3sis
     "Remake 'KT-to-plate distance vs cell roundness plot' so that its actually two plots - one for
      sisterless kinetochores in the three sisterless kinetochore batches and one for sisterless
      kinetochores in the single ablation batches."
     -> rebuilt from the recorded data CSV of the existing figure, split on the master's # Sisterless KTs.

M5a  G4_oscillation_vs_time_to_event_traces
     "in addition to the trendlines, show the traces for individual kinetochore tracks. And, color code the
      points as dark blue, turqouise, or light blue depending on if the chromosome was large, medium, or
      small, respectively."
     -> per-track polylines behind the trendline; chromosome length from CHROMOSOME_MASTER binned into
        tertiles (large / medium / small) -> dark blue / turquoise / light blue.
"""
import sys
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv
import json
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

import lib
try:
    lib.apply_style()
except Exception:
    pass

OUT = "/Volumes/4 MB/ablation_figures_20260625/custom_collagen_vs_triple"
G4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
G1 = "/Volumes/4 MB/ablation_figures_20260625/group1"
DATA = "/Volumes/4 MB/ablation_plots/data"
SCRIPT = __file__
os.makedirs(os.path.join(OUT, "illustrator"), exist_ok=True)

master, _ = lib.load_master_plots()
MR = {r["Batch Name"]: r for r in master}
SIS_COL = {"1": "#e08214", "2": "#2166ac", "3": "#b2182b"}


def sis_of(b):
    return (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()


def read_plot(pid):
    p = os.path.join(DATA, pid + ".csv")
    return list(csv.DictReader(open(p))) if os.path.isfile(p) else []


# =====================================================================================  M4b
chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    chromo[r["batch"].strip()].append(r)


def shape_rate_by_batch():
    """Reuse the rate the ORIGINAL figure plotted, straight from its recorded data CSV, so the y-axis is
    provably the same quantity rather than a re-derivation that might drift."""
    out = {}
    for row in read_plot("G1_shape_rate_vs_congression"):
        try:
            out[row["batch"].strip()] = float(row["roundness_rate"])
        except (KeyError, ValueError):
            pass
    return out


def m4b():
    rate = shape_rate_by_batch()
    if not rate:
        print("M4b SKIPPED - G1_shape_rate_vs_congression has no recorded data")
        return
    # ---- polar fraction: exact, straight from the per-chromosome behaviour calls
    pol, lag, rows = [], [], []
    for b, y in rate.items():
        rs = [x for x in chromo.get(b, []) if (x.get("behavior") or "").strip()]
        s = sis_of(b)
        if rs:
            f = sum(1 for x in rs if x["behavior"].strip() == "noncongression") / len(rs)
            pol.append((f, y, s, b, len(rs)))
            rows.append([b, s, "polar", round(f, 4), round(y, 6), len(rs), "per-chromosome"])
        # ---- lagging fraction. UPDATED 2026-07-30: she scored the 46 multi-sisterless cells on port 8817
        # and the counts are now in the master column `# Lagging Chromosomes`, so this is a REAL fraction
        # for those cells - count / (# sisterless KTs in the cell), the population that was manipulated.
        # 1-sisterless cells without a count still fall back to the yes/no rule (yes->1, no->0 over a
        # single chromosome), which is exact for them. Anything else stays a cell-level fallback and is
        # drawn hollow.
        cnt = (MR.get(b, {}).get("# Lagging Chromosomes", "") or "").strip()
        lv = (MR.get(b, {}).get("Lagging Chromosomes", "") or "").strip().lower()
        den = 0
        try:
            den = int((MR.get(b, {}).get("# Sisterless KTs", "") or "0").strip())
        except ValueError:
            den = 0
        f2 = exact = None
        if cnt != "" and den > 0:
            f2 = min(1.0, int(cnt) / den); exact = True
            prov_l = f"counted {cnt} of {den} sisterless (8817 pass)"
        elif s == "1" and lv in ("yes", "no"):
            f2 = 1.0 if lv == "yes" else 0.0; exact = True
            prov_l = "1-sisterless: master yes/no over a single chromosome"
        elif lv in ("yes", "no"):
            f2 = 1.0 if lv == "yes" else 0.0; exact = False
            prov_l = "CELL-LEVEL yes/no - not counted on the 8817 pass"
        if f2 is not None:
            lag.append((f2, y, s, b, exact))
            rows.append([b, s, "lagging", round(f2, 4), round(y, 6), len(rs), prov_l])

    for kind, pts in (("polar", pol), ("lagging", lag)):
        if len(pts) < 3:
            print(f"M4b {kind}: too few cells ({len(pts)})")
            continue
        fig, ax = plt.subplots(figsize=(7.4, 5.4))
        for s in ("1", "2", "3"):
            sub = [p for p in pts if p[2] == s]
            if not sub:
                continue
            xs = [p[0] for p in sub]
            ys = [p[1] for p in sub]
            if kind == "lagging":
                solid = [(x, y) for x, y, _, _, e in sub if e]
                hollow = [(x, y) for x, y, _, _, e in sub if not e]
                if solid:
                    ax.scatter([q[0] for q in solid], [q[1] for q in solid], s=44, color=SIS_COL[s],
                               edgecolor="white", lw=.5, alpha=.9, zorder=3, label=f"{s}-sisterless")
                if hollow:
                    ax.scatter([q[0] for q in hollow], [q[1] for q in hollow], s=44, facecolor="none",
                               edgecolor=SIS_COL[s], lw=1.3, alpha=.9, zorder=3,
                               label=f"{s}-sisterless (cell-level only)")
            else:
                ax.scatter(xs, ys, s=44, color=SIS_COL[s], edgecolor="white", lw=.5, alpha=.9,
                           zorder=3, label=f"{s}-sisterless")
        X = np.array([p[0] for p in pts], float)
        Y = np.array([p[1] for p in pts], float)
        rho, pv = stats.spearmanr(X, Y)
        if len(X) >= 3 and X.max() - X.min() > 1e-9:
            m, c = np.polyfit(X, Y, 1)
            xx = np.linspace(X.min(), X.max(), 50)
            ax.plot(xx, m * xx + c, ls="--", lw=1.6, color="#111", zorder=4)
        ax.set_xlabel(f"Fraction of the cell's kinetochores that {'stayed polar' if kind=='polar' else 'became lagging'}")
        ax.set_ylabel("Cell roundness change per frame")
        ax.set_title("Do cells that change shape faster have different likelihoods for entering\n"
                     f"anaphase with polar or lagging kinetochores?   ({kind})   "
                     f"Spearman rho={rho:.2f}, p={pv:.2g}, N={len(X)}",
                     loc="left", fontweight="bold", fontsize=9.5)
        ax.legend(fontsize=8, loc="best")
        if kind == "lagging":
            nh = sum(1 for p in pts if not p[4])
            fig.text(0.005, 0.005,
                     f"OPEN MARKERS ({nh} cells): no counted lagging number - only the master's cell-level "
                     "'Lagging Chromosomes' yes/no, so their value is pinned at 0 or 1 and is NOT a real "
                     "fraction. Filled markers are real fractions: she counted the lagging chromosomes for "
                     "the 46 multi-sisterless cells on port 8817 (2026-07-30), and the fraction is that "
                     "count over the cell's number of sisterless kinetochores.",
                     fontsize=6.8, color="#8b0000", ha="left", va="bottom", wrap=True)
        fig.tight_layout(rect=[0, 0.06 if kind == "lagging" else 0, 1, 1])
        stem = f"G1_shape_rate_vs_{kind}_fraction"
        fig.savefig(os.path.join(G1, stem + ".png"), dpi=140, bbox_inches="tight")
        plt.close(fig)
        lib.record_plot(stem, ["batch", "sisterless", "kind", "fraction", "roundness_rate",
                               "n_chromosomes", "provenance"],
                        [r for r in rows if r[2] == kind],
                        {"type": "scatter, colour = # sisterless KTs", "y": "cell roundness change per frame",
                         "x": f"fraction of scored chromosomes {kind}",
                         "rho": round(float(rho), 3), "p": float(pv),
                         "caveat": ("2/3-sisterless lagging is cell-level yes/no, not a fraction"
                                    if kind == "lagging" else "")},
                        SCRIPT,
                        "Shape-change rate vs the fraction of kinetochores that "
                        f"{'stayed polar' if kind == 'polar' else 'became lagging'}",
                        source=["/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv",
                                "/Volumes/4 MB/ABLATION_MASTER.csv"])
        print(f"M4b {kind}: N={len(X)} rho={rho:.2f} p={pv:.2g} -> {stem}")


# =====================================================================================  M4d
def m4d():
    rows = read_plot("G4_plate_distance_time_roundness")
    if not rows:
        print("M4d SKIPPED - no recorded data for G4_plate_distance_time_roundness")
        return
    cols = rows[0].keys()
    bcol = "batch" if "batch" in cols else None
    xcol = next((c for c in cols if "round" in c.lower()), None)
    ycol = next((c for c in cols if "dist" in c.lower()), None)
    if not (bcol and xcol and ycol):
        print(f"M4d SKIPPED - columns not recognised: {list(cols)}")
        return
    groups = {"1sis": ("1", "single-ablation cells"), "3sis": ("3", "three-sisterless cells")}
    for slug, (want, human) in groups.items():
        pts = []
        for r in rows:
            if sis_of(r[bcol].strip()) != want:
                continue
            try:
                pts.append((float(r[xcol]), float(r[ycol]), r[bcol].strip()))
            except (TypeError, ValueError):
                continue
        if len(pts) < 3:
            print(f"M4d {slug}: too few points ({len(pts)})")
            continue
        X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
        rho, pv = stats.spearmanr(X, Y)
        fig, ax = plt.subplots(figsize=(6.6, 5.2))
        ax.scatter(X, Y, s=18, alpha=.6, color=SIS_COL[want], edgecolor="none")
        if X.max() - X.min() > 1e-9:
            m, c = np.polyfit(X, Y, 1)
            xx = np.linspace(X.min(), X.max(), 50)
            ax.plot(xx, m * xx + c, ls="--", lw=1.6, color="#111")
        # 2026-08-04: these were labelled with the raw CSV column names (`cell_roundness`, `plate_dist_um`),
        # which is fine for a data table and wrong on a figure. Map to readable labels with units, and fall
        # back to the column name only for a column this map does not know.
        _AXLAB = {"cell_roundness": "Cell roundness  (4πA / P²)",
                  "plate_dist_um": "Kinetochore distance to the metaphase plate (µm)"}
        ax.set_xlabel(_AXLAB.get(xcol, xcol)); ax.set_ylabel(_AXLAB.get(ycol, ycol))
        ax.set_title(f"KT-to-plate distance vs cell roundness - {human}\n"
                     f"Spearman rho={rho:.2f}, p={pv:.2g}, N={len(X)} points, "
                     f"{len(set(p[2] for p in pts))} cells",
                     loc="left", fontweight="bold", fontsize=10)
        fig.tight_layout()
        stem = f"G4_plate_distance_time_roundness_{slug}"
        fig.savefig(os.path.join(G4, stem + ".png"), dpi=140, bbox_inches="tight")
        plt.close(fig)
        lib.record_plot(stem, ["batch", "roundness", "distance"],
                        [[p[2], round(p[0], 5), round(p[1], 5)] for p in pts],
                        {"split": human, "rho": round(float(rho), 3), "p": float(pv),
                         "parent": "G4_plate_distance_time_roundness"},
                        SCRIPT, f"KT-to-plate distance vs cell roundness - {human}")
        print(f"M4d {slug}: N={len(X)} cells={len(set(p[2] for p in pts))} rho={rho:.2f} -> {stem}")


# =====================================================================================  M5a
def m5a():
    rows = read_plot("G4_oscillation_vs_time_to_event")
    if not rows:
        print("M5a SKIPPED - no recorded data for G4_oscillation_vs_time_to_event")
        return
    # The recorded columns are event / min_to_event / disp_um_per_20s / batch. There is no separate track
    # id and none is needed: the parent builder walks sister(b), which returns ONE tracked sisterless
    # kinetochore per cell, so (batch, event) IS the individual kinetochore track she asked to see.
    cols = list(rows[0].keys())
    bcol, tcol, vcol, ecol = "batch", "min_to_event", "disp_um_per_20s", "event"
    if not all(c in cols for c in (bcol, tcol, vcol, ecol)):
        print(f"M5a SKIPPED - columns not recognised: {cols}")
        return
    # chromosome length per cell -> tertiles
    length = {}
    for b, rs in chromo.items():
        vals = [float(x["length_um"]) for x in rs if (x.get("length_um") or "").strip()]
        if vals:
            length[b] = float(np.mean(vals))
    if len(length) < 3:
        print("M5a SKIPPED - too few chromosome lengths")
        return
    q1, q2 = np.quantile(list(length.values()), [1 / 3, 2 / 3])
    def cls(b):
        v = length.get(b)
        if v is None: return None
        return "small" if v <= q1 else ("medium" if v <= q2 else "large")
    CLSCOL = {"large": "#0b3d91", "medium": "#2ec4b6", "small": "#9ecae1"}

    # USER 2026-08-03: (a) omit every point above 2 um displacement, (b) drop the 'to congression' panel and
    # keep only 'to anaphase', (c) give each chromosome-size group its own trendline instead of one pooled fit.
    DISP_MAX = 2.0
    EVENT = "to anaphase"
    pts, tracks = [], defaultdict(list)
    n_over = 0
    for r in rows:
        b = r[bcol].strip(); ev = r[ecol].strip()
        if ev != EVENT:
            continue
        try:
            t = float(r[tcol]); v = float(r[vcol])
        except (TypeError, ValueError):
            continue
        if v > DISP_MAX:                                   # trimmed BEFORE the fits, so trends reflect the kept data
            n_over += 1
            lib.log_review("G4_oscillation_vs_time_to_event_traces", b, f"{v:.3f} um/20s",
                           f"displacement > {DISP_MAX:g} um/20s - omitted (user 2026-08-03)")
            continue
        c = cls(b)
        pts.append((t, v, c, b, ev))
        tracks[(b, ev)].append((t, v, c))

    fig, ax = plt.subplots(figsize=(7.6, 5.6))
    sub = pts
    for (b, e), seq in tracks.items():                     # one faint polyline per tracked kinetochore
        if len(seq) < 2:
            continue
        seq = sorted(seq)
        ax.plot([q[0] for q in seq], [q[1] for q in seq],
                color=CLSCOL.get(seq[0][2], "#cccccc"), lw=0.7, alpha=0.30, zorder=1)
    for c in ("large", "medium", "small"):
        g = [p for p in sub if p[2] == c]
        if not g:
            continue
        gx = np.array([p[0] for p in g]); gy = np.array([p[1] for p in g])
        ax.scatter(gx, gy, s=15, color=CLSCOL[c], alpha=.8, edgecolor="none", zorder=3,
                   label=f"{c} chromosome (n={len(g)})")
        if len(gx) >= 3 and gx.max() - gx.min() > 1e-9:    # per-group trendline, in that group's colour
            grho, gp = stats.spearmanr(gx, gy)
            m, c0 = np.polyfit(gx, gy, 1)
            xx = np.linspace(gx.min(), gx.max(), 60)
            ax.plot(xx, m * xx + c0, ls="--", lw=2.0, color=CLSCOL[c], zorder=5,
                    label=f"{c} trend (rho={grho:.2f}, p={gp:.2g})")
    unk = [p for p in sub if p[2] is None]
    if unk:
        ux = np.array([p[0] for p in unk]); uy = np.array([p[1] for p in unk])
        ax.scatter(ux, uy, s=13, color="#cccccc", alpha=.6, edgecolor="none", zorder=2,
                   label=f"no chromosome length (n={len(unk)})")
        if len(ux) >= 3 and ux.max() - ux.min() > 1e-9:
            urho, up = stats.spearmanr(ux, uy)
            m, c0 = np.polyfit(ux, uy, 1)
            xx = np.linspace(ux.min(), ux.max(), 60)
            ax.plot(xx, m * xx + c0, ls="--", lw=1.6, color="#999999", zorder=4,
                    label=f"no-length trend (rho={urho:.2f}, p={up:.2g})")
    X = np.array([p[0] for p in sub]); Y = np.array([p[1] for p in sub])
    rho = pv = float("nan")
    if len(X) >= 3 and X.max() - X.min() > 1e-9:
        rho, pv = stats.spearmanr(X, Y)
    ntr = sum(1 for s2 in tracks.values() if len(s2) > 1)
    ax.set_xlabel("minutes relative to anaphase")
    ax.set_ylim(0, DISP_MAX)
    ax.set_title(f"{EVENT}  -  pooled Spearman rho={rho:.2f}, p={pv:.2g}, N={len(X)} steps, {ntr} KT tracks",
                 loc="left", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="best")
    ax.set_ylabel("displacement per 20 s (um)")
    fig.suptitle("Does kinetochore oscillation intensify approaching anaphase?   "
                 "individual KT tracks as faint lines; colour = chromosome size tertile, one trend per group",
                 x=.01, ha="left", fontweight="bold", fontsize=11)
    fig.text(0.005, 0.005, f"size tertiles from CHROMOSOME_MASTER per-cell mean length: "
                           f"small <= {q1:.2f} um < medium <= {q2:.2f} um < large   |   one tracked "
                           f"sisterless kinetochore per cell, so a track = a cell   |   "
                           f"{n_over} step(s) above {DISP_MAX:g} um/20 s omitted",
             fontsize=7, color="#444", ha="left", va="bottom")
    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    stem = "G4_oscillation_vs_time_to_event_traces"
    fig.savefig(os.path.join(G4, stem + ".png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(stem, ["batch", "event", "min_to_event", "disp_um_per_20s", "size_class"],
                    [[p[3], p[4], round(p[0], 4), round(p[1], 5), p[2] or ""] for p in pts],
                    {"traces": "one faint polyline per KT track", "colour": "chromosome size tertile",
                     "tertiles_um": [round(float(q1), 3), round(float(q2), 3)],
                     "parent": "G4_oscillation_vs_time_to_event",
                     "event": EVENT, "disp_max_um_per_20s": DISP_MAX, "n_omitted_over_max": n_over,
                     "trendline": "one per chromosome-size group (user 2026-08-03)"},
                    SCRIPT, "KT oscillation vs time to anaphase, individual tracks, per-size-group trends")
    print(f"M5a: {len(pts)} steps kept, {n_over} omitted >{DISP_MAX:g}um, "
          f"{sum(1 for s2 in tracks.values() if len(s2)>1)} KT tracks -> {stem}")


# =====================================================================================  M4a
def m4a():
    """Single AND triple (AND unModified, added 2026-08-03 -- feedback M2-15 "should definitely be more
    samples (and resolve unmodified)") on ONE composite: separate trendline per scatter group, and one
    slow/fast box-pair per group on each lower panel. Built from the recorded data of the existing _single /
    _triple / _unmodified figures (data[slug] rows are filtered to that group's own `group` column value, so
    the unModified rows now also recorded inside the _single CSV -- it overlays unModified on that figure
    too -- can never leak into the "single" cohort's numbers here). The quantity plotted is provably
    identical to the parent figures - not a re-derivation. None of the three parent figures is modified by
    this function; this is an additional, combined view."""
    GRP = [("single", "1-ablation (single) on-target", lib.PALETTE.get("1-Sister", "#e08214")),
           ("triple", "3-ablation (triple) on-target", lib.PALETTE.get("3-Sister", "#b2182b")),
           ("unmodified", "Unmodified (no ablation)", "#4d4d4d")]
    data = {}
    for slug, human, col in GRP:
        rs = read_plot(f"DEMO_shape_rate_vs_metaphase_{slug}")
        if not rs:
            print(f"M4a SKIPPED - no recorded data for DEMO_shape_rate_vs_metaphase_{slug}")
            return
        data[slug] = rs
    panels = sorted({r["panel"] for rs in data.values() for r in rs})
    if len(panels) < 2:
        print(f"M4a SKIPPED - expected two panels, got {panels}")
        return
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.4))
    prov = []
    for ci, panel in enumerate(panels):
        ax = axes[0][ci]
        boxes, blabels, bcols = [], [], []
        for slug, human, col in GRP:
            pts = []
            for r in data[slug]:
                if r["panel"] != panel:
                    continue
                if r.get("group", human) != human:   # _single's CSV now ALSO carries unModified overlay rows -- keep them out of the "single" group here
                    continue
                try:
                    pts.append((float(r["rate"]), float(r["metaphase_duration_min"]), r["batch"]))
                except (TypeError, ValueError):
                    continue
            if not pts:
                continue
            X = np.array([q[0] for q in pts]); Y = np.array([q[1] for q in pts])
            ax.scatter(X, Y, s=34, color=col, edgecolor="white", lw=.4, alpha=.85, zorder=3,
                       label=None)
            rho = pv = float("nan")
            if len(X) >= 3 and X.max() - X.min() > 1e-9:
                rho, pv = stats.spearmanr(X, Y)
                m, c0 = np.polyfit(X, Y, 1)
                xx = np.linspace(X.min(), X.max(), 50)
                ax.plot(xx, m * xx + c0, ls="--", lw=1.8, color=col, zorder=4,
                        label=f"{human}: rho={rho:.2f}, p={pv:.2g}, N={len(X)}")
            med = float(np.median(X))            # each group split on its OWN median, as the parent did
            lo = [y for x, y in zip(X, Y) if x <= med]
            hi = [y for x, y in zip(X, Y) if x > med]
            boxes += [lo, hi]
            blabels += [f"{slug}\nslow\nN={len(lo)}", f"{slug}\nfast\nN={len(hi)}"]
            bcols += [col, col]
            prov += [[b, slug, panel, round(float(x), 6), round(float(y), 3),
                      "low" if x <= med else "high"] for x, y, b in pts]
        ax.set_xlabel(panel + "  (first half of mitosis)", fontsize=9)
        ax.set_ylabel("Metaphase duration (min)")
        ax.set_title(panel + " - separate trendline per group", loc="left", fontsize=10, fontweight="bold")
        ax.legend(fontsize=8, loc="best")

        axb = axes[1][ci]
        nbox = 2 * len(GRP)
        if len(boxes) == nbox and all(len(b) for b in boxes):
            bp = axb.boxplot(boxes, labels=blabels, widths=.55, patch_artist=True, showfliers=False)
            for patch, col in zip(bp["boxes"], bcols):
                patch.set_facecolor(col); patch.set_alpha(.40)
            for i, (g, col) in enumerate(zip(boxes, bcols)):
                axb.scatter(np.random.default_rng(ci * 11 + i).normal(i + 1, .05, len(g)), g,
                            c=col, s=18, alpha=.85, zorder=3, edgecolor="white", lw=.3)
            ps = []
            for j, (slug, human, col) in enumerate(GRP):
                lo, hi = boxes[2 * j], boxes[2 * j + 1]
                if len(lo) >= 1 and len(hi) >= 1 and len(lo) + len(hi) >= 5:
                    try:
                        ps.append(f"{slug} p={stats.mannwhitneyu(lo, hi)[1]:.2g}")
                    except Exception:
                        pass
            axb.set_title("Metaphase duration by within-group median split — MW " + "  |  ".join(ps),
                          fontsize=8.5)
            axb.set_ylabel("Metaphase duration (min)")
            axb.tick_params(axis="x", labelsize=7.5)
        else:
            axb.text(.5, .5, f"too few cells for a {nbox}-box split", ha="center", va="center",
                     transform=axb.transAxes); axb.axis("off")
    fig.suptitle("Early-mitosis shape-change rate vs metaphase duration - single, triple AND unModified, "
                 "kept as separate groups", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    stem = "DEMO_shape_rate_vs_metaphase_single_and_triple"
    fig.savefig(os.path.join(OUT, stem + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(OUT, "illustrator", stem + ".svg"))
    plt.close(fig)
    lib.record_plot(stem, ["batch", "group", "panel", "rate", "metaphase_duration_min", "median_split"],
                    prov,
                    {"type": f"composite: 3 scatters (each own trendline) + 2 {2*len(GRP)}-box median splits",
                     "groups": "1-Sister, 3-Sister and unModified kept SEPARATE, never pooled",
                     "window": "first-half (NEB..midpoint-to-anaphase)",
                     "note": "2026-08-03 (feedback M2-15): added unModified as a third group, and N widened "
                             "(parent slope_win() now accepts >=2 window points, the true minimum for a "
                             "linear slope, instead of >=3)",
                     "parents": ["DEMO_shape_rate_vs_metaphase_single",
                                 "DEMO_shape_rate_vs_metaphase_triple",
                                 "DEMO_shape_rate_vs_metaphase_unmodified"]},
                    SCRIPT,
                    "Shape-change rate vs metaphase duration - single, triple and unModified side by side")
    print(f"M4a: {len(prov)} rows -> {stem}")


# =====================================================================================  M6a
def m6a():
    """M6a "Randomness of chromosome length ablation plot": were the ablated chromosomes a RANDOM draw
    from the karyotype, or biased by size?

    The null is the PtK2 karyotype itself, from 4_TABLES_AND_REPORTS/PTK2_CHROMOSOME_LENGTHS_REFERENCE.md - 13 chromosomes
    (2n=13, male: 5 autosome pairs + X + Y1 + Y2) at 10.5, 10.5, 10.3, 10.3, 8.9, 8.5, 8.5, 4.2, 4.2,
    3.7, 2.0, 2.0, 0.8 um, each equally likely if the operator picked without regard to size.
    The scales are comparable - the measured ablated lengths run 0.97-12.40 um against a karyotype range
    of 0.8-10.5 um - so this is a like-for-like comparison, not a units mismatch.
    """
    rows = read_plot("G3_chromo_length")
    if not rows:
        print("M6a SKIPPED - no recorded data for G3_chromo_length")
        return
    obs, prov = [], []
    for r in rows:
        try:
            v = float(r["length_um"])
        except (TypeError, ValueError):
            continue
        obs.append(v)
        prov.append([r.get("batch", ""), round(v, 3)])
    if len(obs) < 10:
        print(f"M6a SKIPPED - only {len(obs)} lengths")
        return
    obs = np.array(obs, float)
    NULL = np.array([10.5, 10.5, 10.3, 10.3, 8.9, 8.5, 8.5, 4.2, 4.2, 3.7, 2.0, 2.0, 0.8])
    rng = np.random.default_rng(0)
    draw = rng.choice(NULL, size=200000, replace=True)      # uniform pick from the 13 chromosomes
    ks, kp = stats.ks_2samp(obs, draw)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.4, 5.2))
    bins = np.linspace(0, 13, 27)
    axL.hist(obs, bins=bins, density=True, color="#2166ac", alpha=.75, label=f"ablated chromosomes (n={len(obs)})")
    for v in NULL:
        axL.axvline(v, color="#b2182b", lw=1.1, alpha=.55)
    axL.axvline(NULL[0], color="#b2182b", lw=1.1, alpha=.55, label="the 13 PtK2 chromosomes")
    axL.set_xlabel("chromosome length (um)"); axL.set_ylabel("density")
    axL.set_title("Measured ablated-chromosome lengths vs the karyotype", loc="left",
                  fontweight="bold", fontsize=10)
    axL.legend(fontsize=8)

    xs = np.sort(obs)
    axR.step(xs, np.arange(1, len(xs) + 1) / len(xs), where="post", color="#2166ac", lw=2,
             label=f"ablated (n={len(obs)}), median {np.median(obs):.2f} um")
    nx = np.sort(draw)
    axR.step(nx, np.arange(1, len(nx) + 1) / len(nx), where="post", color="#b2182b", lw=2, ls="--",
             label=f"random pick from the karyotype, median {np.median(NULL):.2f} um")
    axR.set_xlabel("chromosome length (um)"); axR.set_ylabel("cumulative fraction")
    axR.set_title(f"Random targeting would follow the dashed curve\n"
                  f"Kolmogorov-Smirnov D={ks:.3f}, p={kp:.2g}", loc="left", fontweight="bold", fontsize=10)
    axR.legend(fontsize=8, loc="lower right")

    # Deliberately an OBSERVATION, not a causal verdict. A KS test against 13 discrete karyotype values
    # will reject easily: the observed values are continuous and carry tracing spread, so "significant"
    # here does not by itself prove size-biased TARGETING. The median shift is the substantive part -
    # spread alone does not move a median - but traced mitotic length could also systematically
    # under-measure long chromosomes (foreshortening, partial traces). Both readings are stated.
    verdict = (f"ablated median {np.median(obs):.2f} um vs {np.median(NULL):.2f} um expected - "
               "shifted SHORT" if np.median(obs) < np.median(NULL) - 0.5 else
               "no clear shift from the karyotype expectation")
    fig.suptitle(f"Were the ablated chromosomes chosen at random with respect to SIZE?   -   {verdict}",
                 x=.01, ha="left", fontweight="bold", fontsize=12)
    fig.text(0.005, 0.055,
             "READ WITH CARE: a KS test against 13 discrete karyotype values rejects easily, because the "
             "observed lengths are continuous and carry tracing spread - significance alone does not prove "
             "size-biased targeting. The MEDIAN shift is the substantive part (spread does not move a "
             "median), but traced mitotic length could also under-measure the longest chromosomes.",
             fontsize=7, color="#8b0000", ha="left", va="bottom", wrap=True)
    fig.text(0.005, 0.005,
             "Null = the 13 chromosomes of a male PtK2 cell (2n=13) from "
             "4_TABLES_AND_REPORTS/PTK2_CHROMOSOME_LENGTHS_REFERENCE.md, each equally likely. Caveat: the observed values are "
             "TRACED mitotic lengths from chromo_lines, the null is published karyotype lengths; the two "
             "ranges overlap closely (0.97-12.40 vs 0.8-10.5 um) but they are not the same measurement.",
             fontsize=7, color="#444", ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])
    stem = "G3_ablated_length_randomness"
    fig.savefig(os.path.join(G4, stem + ".png"), dpi=140, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(stem, ["batch", "length_um"], prov,
                    {"null": "uniform pick from the 13 PtK2 chromosomes",
                     "ks_D": round(float(ks), 4), "p": float(kp),
                     "median_observed_um": round(float(np.median(obs)), 3),
                     "median_null_um": float(np.median(NULL)),
                     "verdict": verdict}, SCRIPT,
                    "Were ablated chromosomes chosen at random with respect to size?",
                    source=["/Volumes/4 MB/annotations/chromo_lines.csv",
                            "/Volumes/4 MB/4_TABLES_AND_REPORTS/PTK2_CHROMOSOME_LENGTHS_REFERENCE.md"])
    print(f"M6a: n={len(obs)} median {np.median(obs):.2f} vs null {np.median(NULL):.2f}  "
          f"KS D={ks:.3f} p={kp:.2g}  -> {stem}")


if __name__ == "__main__":
    m4a()
    m4b()
    m4d()
    m5a()
    m6a()
    print("done")
