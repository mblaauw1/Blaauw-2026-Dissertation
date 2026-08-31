#!/usr/bin/env python3
"""Kinetochore-SHAPE figure family (NEW, 2026-07-23).

Source: annotations/kt_outlines.csv (freehand KT outline traces) -> shape metrics COMPUTED per trace by
kt_shape_metrics.py (rule: geometry computed from the point files, never the sparse columns).

Question set (from her notes): kinetochores of lagging chromosomes look STRETCHED; polar chromosomes sit
at the pole; paired = normal bi-oriented; plate = metaphase plate. Do the shape metrics separate these
states, and can we quantify "stretch"? Median table already shows lagging = most elongated
(aspect 2.3, elong 0.57, lowest circularity/solidity), polar = largest.

Mirrors the deck's existing plot vocabulary: journal violins (points + median/mean + N + stat), ECDFs,
2-D shape-space scatters, temporal trajectories, per-cell aggregates by her stretch-class.

Every figure saved as PNG under group5_shape/ -> lib's savefig monkeypatch also emits an editable PDF into
_ai_relink/pdf/<name>.pdf (the deck link) + an SVG. Each is registered via lib.record_plot.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as st
import lib
import kt_stats
from kt_shape_metrics import load_shapes

lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group5_shape"
os.makedirs(OUT, exist_ok=True)
SRC = ["/Volumes/4 MB/annotations/kt_outlines.csv"]
SCRIPT = __file__

ROWS = load_shapes()
# category order + colours (plate=teal, paired=blue, polar=orange, lagging=crimson)
# plate merged into paired 2026-07-23 (user: plate & paired are the same group)
LAB_ORDER = ["paired", "polar", "lagging"]
LAB_COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
LAB_DISP = {"paired": "paired\n(plate/bi-oriented)", "polar": "polar", "lagging": "lagging"}
CLASS_ORDER = ["no lagging", "lagging, no stretch", "stretch visible"]
CLASS_COL = {"no lagging": "#7a7a7a", "lagging, no stretch": "#e6820e", "stretch visible": "#d1495b"}


# ITEM 11 (user 2026-08-04): per-state phase matching — paired/polar measured during METAPHASE, lagging
# during ANAPHASE. The shape table has no `phase` column, so the phase is derived from each cell's own
# metaphase-start / anaphase-onset times (the same source kt_time_trajectories uses to anchor t=0).
PHASE_BY_LABEL = {"paired": "metaphase", "polar": "metaphase", "lagging": "anaphase"}
PHASE_MATCH_NOTE = ("phase-matched: paired & polar measured during METAPHASE, lagging during ANAPHASE — "
                    "each state scored in the window where that label describes the kinetochore")
_PH = None
def _row_phase(r):
    """'metaphase' / 'anaphase' / None for a shape row, from its batch's event times and its own t_sec."""
    global _PH
    if _PH is None:
        from kt_landmark_analysis import phase_times
        _PH = phase_times(sorted({x.get("batch") for x in ROWS if x.get("batch")}))
    mt, at = _PH.get(r.get("batch"), (None, None))
    try: t = float(r.get("t_sec"))
    except Exception: return None
    if mt is None: return None
    if at is not None and t >= at: return "anaphase"
    if t >= mt: return "metaphase"
    return "prometaphase"


def vals_by_label(metric, phase_match=False):
    d = collections.defaultdict(list)
    for r in ROWS:
        v = r.get(metric)
        if v == "" or v is None:
            continue
        if phase_match:
            want = PHASE_BY_LABEL.get(r["label"])
            if want is not None and _row_phase(r) != want:
                continue
        d[r["label"]].append(float(v))
    return d


def _p_annot(groups):
    """Kruskal-Wallis across all groups (>=3), else Mann-Whitney; return short text."""
    gs = [np.asarray(g, float) for g in groups if len(g) >= 3]
    if len(gs) < 2:
        return ""
    try:
        if len(gs) >= 3:
            H, p = st.kruskal(*gs)
            return f"Kruskal–Wallis p = {p:.2g}"
        U, p = st.mannwhitneyu(gs[0], gs[1], alternative="two-sided")
        return f"Mann–Whitney p = {p:.2g}"
    except Exception:
        return ""


def violin(metric, ylabel, title, outname, order=LAB_ORDER, cols=LAB_COL, disp=LAB_DISP,
           logy=False, fmt="{:.2f}", phase_match=False):
    D = vals_by_label(metric, phase_match=phase_match)
    if phase_match:
        print(f"  {outname} phase-matched N: " + ", ".join(f"{k}={len(D.get(k,[]))}" for k in order))
    data_v = [D.get(k, []) for k in order]
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    dmax = max((max(d) for d in data_v if d), default=1.0)
    rows_csv = []
    for i, (k, d) in enumerate(zip(order, data_v)):
        if not d:
            continue
        col = cols[k]
        lib.journal_violin(ax, d, i, col, alpha=0.28, lw=1.0)
        jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.20
        ax.scatter(np.full(len(d), i) + jit, d, s=9, color=col, alpha=0.45,
                   edgecolor="white", linewidth=0.2, zorder=3)
        mean, med = float(np.mean(d)), float(np.median(d))
        ax.hlines(med, i - 0.34, i + 0.34, color=col, lw=2.4, zorder=4)
        ax.hlines(mean, i - 0.28, i + 0.28, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=4)
        ax.scatter([i], [mean], marker="D", s=30, facecolor="white", edgecolor=col, lw=1.3, zorder=5)
        ax.text(i, dmax * 1.02, f"med {fmt.format(med)}\nx̄ {fmt.format(mean)}\nN={len(d)}",
                ha="center", va="bottom", fontsize=7.5, color="#222")
        for v in d:
            rows_csv.append([k, v])
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([disp.get(k, k) for k in order], fontsize=9)
    ax.set_ylabel(ylabel)
    if logy:
        ax.set_yscale("log")
    # 2026-08-04: same collision as kt_track_plots - at 1.28 the upper-right statistics box overlapped the
    # "med / x̄ / N" label above the right-hand violin (clearest on G5shape_elongation). More headroom.
    ax.set_ylim(top=dmax * 1.45)
    p = _p_annot([d for d in data_v if d])
    kt_stats.add_group_stats(ax, {k: D.get(k, []) for k in order}, order, loc="upper right")
    ax.set_title(title + (f"    ({p})" if p else ""), loc="left", fontweight="bold", fontsize=11)
    if phase_match:
        ax.text(0.0, -0.135, PHASE_MATCH_NOTE, transform=ax.transAxes, fontsize=7, color="#555", va="top")
    leg = [Line2D([0], [0], color="#444", lw=2.4, label="median"),
           Line2D([0], [0], marker="D", color="#444", lw=1.3, ls=(0, (2, 1.5)),
                  markerfacecolor="white", markeredgecolor="#444", label="mean")]
    ax.legend(handles=leg, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["label", metric], rows_csv,
                    {"kind": "journal_violin", "metric": metric, "n": len(rows_csv)},
                    script=SCRIPT, caption=title, source=SRC, key_column="label")
    print(f"  {outname}: {sum(len(d) for d in data_v)} traces")


def ecdf(metric, xlabel, title, outname, order=LAB_ORDER, cols=LAB_COL):
    D = vals_by_label(metric)
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    for k in order:
        d = np.sort(np.asarray(D.get(k, []), float))
        if len(d) < 3:
            continue
        y = np.arange(1, len(d) + 1) / len(d)
        ax.step(d, y, where="post", color=cols[k], lw=2.0, label=f"{k} (N={len(d)})")
    ax.set_xlabel(xlabel); ax.set_ylabel("cumulative fraction")
    ax.set_title(title, loc="left", fontweight="bold", fontsize=11)
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["label", metric], [[r["label"], r[metric]] for r in ROWS if r.get(metric) != ""],
                    {"kind": "ecdf", "metric": metric}, script=SCRIPT, caption=title, source=SRC, key_column="label")
    print(f"  {outname}")


def scatter2d(mx, my, xlabel, ylabel, title, outname, order=LAB_ORDER, cols=LAB_COL, diag=False,
              trim_nonlagging_um=None):
    """trim_nonlagging_um: USER 2026-08-03 - for any label that is NOT lagging (i.e. polar or paired), drop the
    point if EITHER axis length exceeds this many um. A paired or polar kinetochore that measures >2 um on an
    axis is a tracing artefact, not a real shape; lagging KTs are genuinely stretched so they are never trimmed."""
    fig, ax = plt.subplots(figsize=(6.6, 6.0))
    rows_csv = []
    n_trimmed_total = 0
    for k in order:
        sel = [r for r in ROWS if r["label"] == k and r.get(mx) != "" and r.get(my) != ""]
        pairs = [(float(r[mx]), float(r[my]), r.get("batch", "")) for r in sel]
        if trim_nonlagging_um is not None and k != "lagging":
            kept = []
            for a, b, bt in pairs:
                if a > trim_nonlagging_um or b > trim_nonlagging_um:
                    n_trimmed_total += 1
                    lib.log_review(outname, bt, f"{mx}={a:.3f} {my}={b:.3f}",
                                   f"non-lagging ({k}) point with an axis > {trim_nonlagging_um:g} um - "
                                   f"trimmed (user 2026-08-03)")
                else:
                    kept.append((a, b, bt))
            pairs = kept
        xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
        if not xs:
            continue
        ax.scatter(xs, ys, s=12, color=cols[k], alpha=0.45, edgecolor="white", linewidth=0.2,
                   label=f"{k} (N={len(xs)})")
        for a, b, _bt in pairs:
            rows_csv.append([k, a, b])
    if trim_nonlagging_um is not None:
        ax.text(0.99, 0.01,
                f"non-lagging points with either axis > {trim_nonlagging_um:g} um trimmed "
                f"({n_trimmed_total} removed); lagging never trimmed",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#555")
    if diag:
        lo = min(ax.get_xlim()[0], ax.get_ylim()[0]); hi = max(ax.get_xlim()[1], ax.get_ylim()[1])
        ax.plot([lo, hi], [lo, hi], ls=":", color="#999", lw=1.0)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=11)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["label", mx, my], rows_csv,
                    {"kind": "scatter", "x": mx, "y": my}, script=SCRIPT, caption=title, source=SRC, key_column="label")
    print(f"  {outname}")


def per_cell_class_violin(metric, agg, ylabel, title, outname, fmt="{:.2f}"):
    """One point per CELL (batch): agg of `metric` over that cell's traces, grouped by her stretch-class."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))  # class -> batch -> vals
    for r in ROWS:
        v = r.get(metric)
        if v != "" and v is not None:
            by[r["stretch_class"]][r["batch"]].append(float(v))
    fig, ax = plt.subplots(figsize=(7.0, 5.2))
    rows_csv = []
    allvals = []
    for i, cl in enumerate(CLASS_ORDER):
        cells = by.get(cl, {})
        pts = [agg(vs) for vs in cells.values() if vs]
        allvals.append(pts)
        if not pts:
            continue
        col = CLASS_COL[cl]
        lib.journal_violin(ax, pts, i, col, alpha=0.28, lw=1.0, min_n=4)
        jit = (np.random.RandomState(i).rand(len(pts)) - 0.5) * 0.16
        ax.scatter(np.full(len(pts), i) + jit, pts, s=26, color=col, alpha=0.85,
                   edgecolor="white", linewidth=0.4, zorder=3)
        med = float(np.median(pts))
        ax.hlines(med, i - 0.3, i + 0.3, color=col, lw=2.4, zorder=4)
        ax.text(i, max(pts) * 1.02 if max(pts) > 0 else 0.02,
                f"med {fmt.format(med)}\nN={len(pts)} cells", ha="center", va="bottom", fontsize=8, color="#222")
        for b, vs in cells.items():
            rows_csv.append([cl, b, agg(vs)])
    ax.set_xticks(range(len(CLASS_ORDER)))
    ax.set_xticklabels(CLASS_ORDER, fontsize=9)
    ax.set_ylabel(ylabel)
    p = _p_annot([v for v in allvals if len(v) >= 3])
    ax.set_title(title + (f"    ({p})" if p else ""), loc="left", fontweight="bold", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["stretch_class", "batch", metric + "_agg"], rows_csv,
                    {"kind": "per_cell_class_violin", "metric": metric}, script=SCRIPT,
                    caption=title, source=SRC, key_column="batch")
    print(f"  {outname}")


def lagging_over_time(outname):
    """Aspect ratio vs time for lagging traces, ONE LINE PER LAGGING KINETOCHORE, aligned so t=0 is that
    kinetochore's LAST traced frame (proxy for anaphase/segregation end). Shows whether lagging KTs stretch
    as they resolve."""
    # ONE LINE PER KINETOCHORE, not per cell (user 2026-08-03). A double/triple-ablation cell can carry
    # several lagging kinetochores at once, and she separates them with "+ New KT" -> distinct `grp`.
    # Averaging them into one per-cell line would put two different kinetochores on one trace, which is
    # exactly the merge the grp-aware keying in kt_shape_metrics was added to undo. Rows with no grp tag
    # are single-ablation cells with one lagging KT, so they stay one line per cell.
    # Within one kinetochore, several traces on ONE frame are PIECES of it and are already combined into a
    # single record upstream; the median here only guards against a residual duplicate.
    perf = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in ROWS:
        if r["label"] == "lagging" and r.get("aspect_ratio") != "" and np.isfinite(r["t_sec"]):
            perf[(r["batch"], r.get("grp") or "")][round(r["t_sec"], 1)].append(float(r["aspect_ratio"]))
    by = {k: [(t, float(np.median(v))) for t, v in d.items()] for k, d in perf.items()}
    ncell = len({b for b, _ in by})
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    rows_csv = []
    for (b, g), pts in by.items():
        if len(pts) < 3:
            continue
        pts.sort()
        t = np.array([p[0] for p in pts]); a = np.array([p[1] for p in pts])
        trel = (t - t.max()) / 60.0  # minutes relative to this kinetochore's last traced frame
        lab = b.split(" ", 1)[-1][:22] + (f" KT{g}" if g else "")
        ax.plot(trel, a, "-o", ms=3, lw=1.2, alpha=0.8, label=lab)
        for tt, aa in zip(trel, a):
            rows_csv.append([b, g, tt, aa])
    # 2026-08-03 (her: "I don't think this is right, shows lagging getting shorter as time goes on").
    # The figure was 30 unlabelled trajectories with NO trend and no stated direction, so the eye lands on
    # the declining minority and the two dramatic spikes. Measured, the data says the OPPOSITE of shorter:
    # 18 of 30 kinetochores rise toward their last lagging frame vs 12 that fall, median per-track slope
    # +0.021 aspect/min, and the pooled slope is +0.021 (+0.017 with the single largest track removed, so
    # it is NOT one-track-driven). State that on the figure instead of leaving it to be read off by eye.
    _sl = []
    for (_b, _g), _p in by.items():
        if len(_p) < 3: continue
        _p = sorted(_p)
        _x = np.array([q[0] for q in _p]); _y = np.array([q[1] for q in _p])
        if _x.max() - _x.min() < 1e-9: continue
        _sl.append(float(np.polyfit((_x - _x.max()) / 60.0, _y, 1)[0]))
    if rows_csv:
        _ax = np.array([r[2] for r in rows_csv], float); _ay = np.array([r[3] for r in rows_csv], float)
        _m, _c = np.polyfit(_ax, _ay, 1)
        _xx = np.linspace(_ax.min(), 0, 60)
        ax.plot(_xx, _m * _xx + _c, ls="--", lw=2.6, color="#111", zorder=6,
                label=f"pooled trend ({_m:+.3f} aspect/min)")
    ax.axhline(1.0, ls=":", color="#999", lw=1.0)
    ax.set_xlabel("time relative to last lagging frame (min; 0 = last frame this KT was lagging)")
    ax.set_ylabel("kinetochore aspect ratio (stretch; higher = more elongated)")
    ax.set_title("Lagging-kinetochore stretch over time (one line per kinetochore)",
                 loc="left", fontweight="bold", fontsize=11)
    if _sl:
        _up = sum(1 for s in _sl if s >= 0)
        _med = float(np.median(_sl))
        ax.text(0.01, -0.155,
                f"Direction, measured: the POOLED trend rises ({_m:+.3f} aspect/min), but per kinetochore it is "
                f"near-even — {_up} of {len(_sl)} get more stretched toward their last lagging frame and "
                f"{len(_sl)-_up} get less, median per-KT slope {_med:+.3f} aspect/min. So the figure does NOT "
                f"show lagging shortening over time; it shows no consistent per-KT direction, with the pooled "
                f"rise driven by the late high-stretch excursions near t=0.",
                transform=ax.transAxes, fontsize=7.0, color="#8b3a00", va="top", wrap=True)
    ax.legend(fontsize=6.5, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["batch", "grp", "t_rel_min", "aspect_ratio"], rows_csv,
                    {"kind": "trajectory", "metric": "aspect_ratio"}, script=SCRIPT,
                    caption="Lagging KT stretch over time", source=SRC, key_column="batch")
    print(f"  {outname}: {len(by)} lagging kinetochores in {ncell} cells")


def polar_vs_paired_paired(metric, ylabel, title, outname, fmt="{:.2f}"):
    """Within cells that traced BOTH polar and paired KTs: cell-median metric, polar vs paired, connected."""
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in ROWS:
        if r["label"] in ("polar", "paired") and r.get(metric) != "":
            by[r["batch"]][r["label"]].append(float(r[metric]))
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    rows_csv = []
    n = 0
    for b, d in by.items():
        if "polar" not in d or "paired" not in d:
            continue
        yp, ya = float(np.median(d["polar"])), float(np.median(d["paired"]))
        ax.plot([0, 1], [ya, yp], "-", color="#bbb", lw=1.0, zorder=1)
        ax.scatter([0], [ya], color=LAB_COL["paired"], s=34, zorder=3, edgecolor="white", lw=0.4)
        ax.scatter([1], [yp], color=LAB_COL["polar"], s=34, zorder=3, edgecolor="white", lw=0.4)
        rows_csv.append([b, ya, yp]); n += 1
    ax.set_xticks([0, 1]); ax.set_xticklabels(["paired", "polar"], fontsize=10)
    ax.set_ylabel(ylabel)
    if n >= 3:
        pa = [row[1] for row in rows_csv]; po = [row[2] for row in rows_csv]
        try:
            W, p = st.wilcoxon(pa, po)
            title += f"    (Wilcoxon p = {p:.2g}, N={n} cells)"
        except Exception:
            title += f"    (N={n} cells)"
    ax.set_title(title, loc="left", fontweight="bold", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(outname, ["batch", "paired_median", "polar_median"], rows_csv,
                    {"kind": "paired_within_cell", "metric": metric}, script=SCRIPT,
                    caption=title, source=SRC, key_column="batch")
    print(f"  {outname}: {n} cells with both")


# ── hue families for the lagging traces (user 2026-08-04) ─────────────────────────────────────────
# "Can the traces be hue-coded by if they came from 1 or 2/3 batches? Not exactly the same color but, for
# example, all blues and all reds/oranges." One family per ablation number, several shades inside each so
# individual tracks remain separable without losing the at-a-glance 1 vs 2/3 split.
_LAG_SHADES = {
    "1":   ["#08306b", "#08519c", "#2171b5", "#4292c6", "#6baed6", "#9ecae1", "#c6dbef"],
    "23":  ["#7f2704", "#a63603", "#d94801", "#f16913", "#fd8d3c", "#fdae6b", "#fdd0a2"],
    "other": ["#737373", "#969696", "#bdbdbd"],
}
_LAG_MR = None
def _lag_family(b):
    """'1' for 1-sisterless, '23' for 2- or 3-sisterless, 'other' when the master does not say."""
    global _LAG_MR
    if _LAG_MR is None:
        _m, _ = lib.load_master_plots()
        _LAG_MR = {r["Batch Name"]: r for r in _m}
    v = str((_LAG_MR.get(b, {}) or {}).get("# Sisterless KTs", "") or "").strip()
    if v == "1": return "1"
    if v in ("2", "3"): return "23"
    return "other"


def lagging_peak_aligned(peaks, outname):
    """FB11a (user 2026-08-04): "Is there a way to make a plot of these traces such that the peaks are
    aligned in some way?" Same envelopes, but x is re-zeroed on each track's own peak, so the rise and the
    recovery can be compared across tracks whose peaks occur at different times after anaphase."""
    if not peaks: return
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    seen = collections.Counter(); rows = []
    for b, g, fam, tpk, ypk, xs, ys in peaks:
        shade = _LAG_SHADES[fam][seen[fam] % len(_LAG_SHADES[fam])]; seen[fam] += 1
        xr = xs - tpk
        ax.plot(xr, ys, "-o", ms=3, lw=1.2, alpha=0.85, color=shade)
        rows += [[b, g, fam, round(float(a), 3), round(float(c), 4)] for a, c in zip(xr, ys)]
    ax.axvline(0, color="#333", lw=1.2, ls="--", zorder=1)
    ax.set_xlabel("Time relative to that track's own peak length (min)")
    ax.set_ylabel("Kinetochore length, major axis (µm)")
    ax.set_title(f"Lagging-kinetochore length, PEAK-ALIGNED — {len(peaks)} kinetochores",
                 loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(handles=[Line2D([0], [0], color=_LAG_SHADES["1"][2], lw=2.4, label="1-sisterless (blues)"),
                       Line2D([0], [0], color=_LAG_SHADES["23"][2], lw=2.4, label="2/3-sisterless (oranges)")],
              fontsize=8)
    ax.text(0.0, -0.145,
            "Same monotone envelopes as the since-anaphase figure, with each track's x re-zeroed on its own "
            "peak (dashed line).\nThis makes the rise and the recovery comparable across tracks whose peaks "
            "fall at different times after anaphase onset.",
            transform=ax.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    lib.record_plot(outname, ["batch", "grp", "family", "t_rel_peak_min", "major_um"], rows,
                    {"fb11a": "peak-aligned lagging length traces", "hue": "1-sis blues, 2/3-sis oranges"},
                    script=__file__, caption="Lagging-kinetochore length, peak-aligned", key_column="batch")
    print(f"FB11a peak-aligned: {len(peaks)} tracks, {len(rows)} points")


def lagging_since_anaphase(outname):
    """ITEM 23 (user 2026-08-04). Her four changes to G5shape_lagging_stretch_time:
      (a) plot only points SINCE ANAPHASE ONSET
      (b) x starts at 0 and is labelled "time since anaphase onset"
      (c) use LENGTH (major axis, um) instead of aspect ratio
      (d) monotone envelope — before each track's max plot only increasing points, after the max only
          decreasing ones. Her words: "significantly simplify how the plot looks without losing any of the
          info". This keeps the rise, the peak and the fall and drops only the jitter between them.
    One line per lagging KINETOCHORE (batch, grp), as before: a double/triple cell carries several."""
    global _PH
    if _PH is None:            # anaphase onset per batch (same source the trajectory family uses)
        from kt_landmark_analysis import phase_times
        _PH = phase_times(sorted({x.get("batch") for x in ROWS if x.get("batch")}))
    per = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in ROWS:
        if r["label"] != "lagging": continue
        if r.get("major_um") in ("", None): continue
        try:
            _t = float(r["t_sec"])
        except Exception:
            continue
        per[(r["batch"], r.get("grp") or "")][round(_t, 1)].append(float(r["major_um"]))
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    rows_csv = []; n_tracks = 0; n_drop_pts = 0
    _lag_seen = collections.Counter(); _peaks = []
    for (b, g), d in per.items():
        mt, at = _PH.get(b, (None, None))
        if at is None: continue
        pts = sorted((t, float(np.median(v))) for t, v in d.items())
        rel = [((t - at) / 60.0, y) for t, y in pts]
        keep = [(x, y) for x, y in rel if x >= 0]          # (a) since anaphase onset only
        n_drop_pts += len(rel) - len(keep)
        if len(keep) < 3: continue
        x = np.array([p[0] for p in keep]); y = np.array([p[1] for p in keep])
        # (d) monotone envelope around the track max
        # USER 2026-08-04: "there's one batch, plotted in bright green, that's not smoothed correctly.
        # Remove the spike of points at the end (should end on lowest point)." Cause: when a track's global
        # maximum lands on one of its LAST frames, that late spike becomes the peak, the whole trace is
        # treated as the rising limb and it ends on its highest point. A peak must have somewhere to fall
        # to, so only points with at least two frames after them can be the peak.
        _cand_end = len(y) - 2
        imax = int(np.argmax(y[:_cand_end])) if _cand_end >= 1 else int(np.argmax(y))
        sel = [imax]
        run = y[imax]
        for i in range(imax - 1, -1, -1):                  # before the max: keep only rising points
            if y[i] <= run: sel.append(i); run = y[i]
        run = y[imax]
        for i in range(imax + 1, len(y)):                  # after the max: keep only falling points
            if y[i] <= run: sel.append(i); run = y[i]
        sel = sorted(set(sel))
        xs, ys = x[sel], y[sel]
        # end the trace on its LOWEST post-peak point: anything after that minimum is a rebound, not part of
        # the shortening she wants to read off this figure (user 2026-08-04)
        _ip = int(np.argmax(ys))
        if _ip < len(ys) - 1:
            _imin = _ip + 1 + int(np.argmin(ys[_ip + 1:]))
            xs, ys = xs[:_imin + 1], ys[:_imin + 1]
        # hue-code by ablation number: 1-sisterless in BLUES, 2/3-sisterless in REDS/ORANGES, each track a
        # different shade within its family so individual tracks stay distinguishable (user 2026-08-04)
        _fam = _lag_family(b)
        _shade = _LAG_SHADES[_fam][_lag_seen[_fam] % len(_LAG_SHADES[_fam])]; _lag_seen[_fam] += 1
        lab = b.split(" ", 1)[-1][:22] + (f" KT{g}" if g else "")
        ax.plot(xs, ys, "-o", ms=3, lw=1.2, alpha=0.85, label=lab, color=_shade)
        _peaks.append((b, g, _fam, float(xs[int(np.argmax(ys))]), float(np.max(ys)), xs.copy(), ys.copy()))
        n_tracks += 1
        for xx, yy in zip(xs, ys): rows_csv.append([b, g, round(float(xx), 3), round(float(yy), 4)])
    ax.set_xlim(left=0)                                    # (b)
    ax.set_xlabel("Time since anaphase onset (min)")
    ax.set_ylabel("Kinetochore length, major axis (µm)")   # (c)
    ax.set_title(f"Lagging-kinetochore LENGTH after anaphase onset — {n_tracks} kinetochores",
                 loc="left", fontweight="bold", fontsize=10.5)
    ax.text(0.0, -0.145,
            "ITEM 23: points before anaphase onset removed; length replaces aspect ratio; each track is "
            "reduced to its monotone envelope\n(only rising points before its maximum, only falling points "
            f"after) — {n_drop_pts} pre-anaphase points dropped, jitter between rise and fall suppressed.\n"
            "2026-08-04: a track's peak must have at least two frames after it (so a spike on the last frame "
            "can no longer be read as the peak),\nand each trace is cut at its lowest post-peak point. "
            "Hue = ablation number: BLUES are 1-sisterless, ORANGES are 2/3-sisterless.",
            transform=ax.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.5)
    if n_tracks <= 14: ax.legend(fontsize=6.2, ncol=2)
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    lib.record_plot(outname, ["batch", "grp", "t_since_anaphase_min", "major_um"], rows_csv,
                    {"item23": "since anaphase onset; LENGTH not aspect; monotone envelope per track",
                     "x_label": "Time since anaphase onset (min)",
                     "y_label": "Kinetochore length, major axis (um)", "n_tracks": n_tracks},
                    script=__file__, caption="Lagging-kinetochore length after anaphase onset", key_column="batch")
    print(f"ITEM 23: {n_tracks} lagging kinetochores, {len(rows_csv)} envelope points, "
          f"{n_drop_pts} pre-anaphase points dropped")
    lagging_peak_aligned(_peaks, outname + "_peak_aligned")     # FB11a companion (user 2026-08-04)
    return _peaks


if __name__ == "__main__":
    print("=== kinetochore shape violins (by KT state) ===")
    violin("area_um2", "kinetochore area (µm²)", "Kinetochore area by state", "G5shape_area")
    violin("perimeter_um", "outline perimeter (µm)", "Kinetochore perimeter by state", "G5shape_perimeter")
    violin("aspect_ratio", "aspect ratio (major/minor)", "Kinetochore stretch (aspect ratio) by state", "G5shape_aspect")
    violin("elongation", "elongation (1 − minor/major)", "Kinetochore elongation by state", "G5shape_elongation")
    violin("major_um", "major-axis length (µm)", "Kinetochore stretch length by state", "G5shape_major")
    # ITEM 11 (user 2026-08-04): circularity by state must be phase-matched — paired/polar from metaphase,
    # lagging from anaphase.
    violin("circularity", "circularity (4π·A/P²)", "Kinetochore circularity by state (phase-matched)",
           "G5shape_circularity", phase_match=True)
    violin("solidity", "solidity (A / convex-hull A)", "Kinetochore solidity by state", "G5shape_solidity")

    print("=== ECDFs ===")
    ecdf("aspect_ratio", "aspect ratio (major/minor)", "Aspect-ratio distribution by KT state (ECDF)", "G5shape_aspect_ecdf")
    ecdf("area_um2", "kinetochore area (µm²)", "Area distribution by KT state (ECDF)", "G5shape_area_ecdf")

    print("=== 2-D shape space ===")
    scatter2d("minor_um", "major_um", "minor-axis length (µm)", "major-axis length (µm)",
              "Kinetochore shape space: major vs minor axis", "G5shape_major_vs_minor", diag=True,
              trim_nonlagging_um=2.0)
    scatter2d("area_um2", "circularity", "kinetochore area (µm²)", "circularity",
              "Kinetochore shape space: area vs circularity", "G5shape_area_vs_circularity")
    scatter2d("aspect_ratio", "solidity", "aspect ratio", "solidity",
              "Kinetochore shape space: aspect ratio vs solidity", "G5shape_aspect_vs_solidity")

    print("=== per-cell by her stretch class ===")
    per_cell_class_violin("aspect_ratio", lambda v: float(np.max(v)),
                          "per-cell MAX aspect ratio", "Peak kinetochore stretch per cell, by stretch class",
                          "G5shape_maxaspect_by_class")
    per_cell_class_violin("aspect_ratio", lambda v: float(np.mean([x > 2.0 for x in v])),
                          "fraction of traces with aspect ratio > 2",
                          "Fraction of stretched kinetochores per cell, by stretch class",
                          "G5shape_fracstretched_by_class")

    print("=== temporal + within-cell ===")
    lagging_since_anaphase("G5shape_lagging_stretch_time")   # ITEM 23 (user 2026-08-04)
    polar_vs_paired_paired("area_um2", "cell-median kinetochore area (µm²)",
                           "Polar vs paired kinetochore area (within cell)", "G5shape_polar_vs_paired_area")
    polar_vs_paired_paired("aspect_ratio", "cell-median aspect ratio",
                           "Polar vs paired kinetochore stretch (within cell)", "G5shape_polar_vs_paired_aspect")

    print(f"\nAll kinetochore-shape figures -> {OUT}")
