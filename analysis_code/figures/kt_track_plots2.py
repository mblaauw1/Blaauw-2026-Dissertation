#!/usr/bin/env python3
"""Addendum plots (2026-07-23): metric-vs-mitotic-time relationships + chromosome-line geometry.
Reads KT_LANDMARK_ANALYSIS + KT_CHROMO_ANALYSIS. Saves to group6_tracks/, registers via record_plot."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
import kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv", f"{ROOT}/annotations/KT_CHROMO_ANALYSIS_20260723.csv"]
SCRIPT = __file__
R = list(csv.DictReader(open(SRC[0])))
CH = list(csv.DictReader(open(SRC[1])))
# USER 2026-08-06: prophase ablations are excluded from every plot that has no prophase group.
# This file reads annotation CSVs directly, so the shared gates do not reach it.
R = [r for r in R if not lib.is_prophase_ablation(r.get("batch",""))]
CH = [r for r in CH if not lib.is_prophase_ablation(r.get("batch",""))]

def num(r, k):
    try: return float(r.get(k, ""))
    except Exception: return None
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}

# per-batch mitotic anchors from the (properly clocked) phase column
meta_on = {}; ana_on = {}
for r in R:
    t = num(r, "t_sec")
    if t is None: continue
    if r["phase"] == "metaphase": meta_on[r["batch"]] = min(meta_on.get(r["batch"], 1e18), t)
    if r["phase"] == "anaphase": ana_on[r["batch"]] = min(ana_on.get(r["batch"], 1e18), t)


def _save(fig, name, header, rows, cap, key="batch"):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try: lib.record_plot(name, header, rows, {"family": "tracks"}, script=SCRIPT, caption=cap, source=SRC, key_column=key)
    except Exception as e: print("  warn", name, e)
    print("  " + name)


def time_refs(metric, ylabel, title, outname, label="polar", ref_label=None, trim_outliers=False):
    """3 panels: metric vs (time from metaphase onset) | (time UNTIL anaphase, pre) | (time SINCE anaphase, post).

    ref_label: USER 2026-08-03 - draw a second KT state alongside the primary one as a reference series
    (e.g. paired/plate kinetochores under the polar ones), so the primary trend can be read against a
    baseline instead of in isolation. The reference is drawn fainter with a dashed median trend."""
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    defs = [
        ("from metaphase onset (min)", lambda r, t: (t - meta_on[r["batch"]]) / 60 if r["batch"] in meta_on and t >= meta_on[r["batch"]] else None, (0, None)),
        ("until anaphase (min, pre)", lambda r, t: (ana_on[r["batch"]] - t) / 60 if r["batch"] in ana_on and t < ana_on[r["batch"]] else None, (0, None)),
        ("since anaphase onset (min, post)", lambda r, t: (t - ana_on[r["batch"]]) / 60 if r["batch"] in ana_on and t >= ana_on[r["batch"]] else None, (0, None)),
    ]
    series = [(label, False)] + ([(ref_label, True)] if ref_label else [])
    # USER 2026-08-03: "remove the outliers" - a handful of extreme values were stretching the y-axis so the
    # bulk of the data sat flat against the bottom. Fence is computed ONCE over every series and every time
    # reference (so all three panels share one y-scale and stay comparable), using the same robust IQR rule the
    # zoom companions use. Dropped points are logged and counted on the figure - never silently removed.
    fence_hi = None; n_trimmed = 0
    if trim_outliers:
        pool = [num(r, metric) for r in R
                if r["label"] in {lab for lab, _ in series} and num(r, metric) is not None]
        if len(pool) >= 8:
            fence_hi = lib.zoom_trim(np.array(pool, float))["fence_hi"]
    allrows = []
    for ax, (xl, fx, _) in zip(axs, defs):
        for lab, is_ref in series:
            xs, ys = [], []
            for r in R:
                if r["label"] != lab: continue
                t = num(r, "t_sec"); v = num(r, metric)
                if t is None or v is None: continue
                x = fx(r, t)
                if x is None: continue
                if fence_hi is not None and v > fence_hi:
                    n_trimmed += 1
                    lib.log_review(outname, r["batch"], f"{metric}={v:.4g}",
                                   f"{lab} point above the IQR fence ({fence_hi:.3g}) - removed (user 2026-08-03)")
                    continue
                xs.append(x); ys.append(v); allrows.append([r["batch"], lab, xl, x, v])
            ax.scatter(xs, ys, s=6 if is_ref else 8, color=COL[lab],
                       alpha=0.14 if is_ref else 0.3, edgecolor="white", lw=0.15,
                       zorder=1 if is_ref else 2)
            xs = np.array(xs); ys = np.array(ys)
            if len(xs) > 10:
                lo, hi = np.percentile(xs, [1, 99]); bins = np.linspace(lo, hi, 10)
                idx = np.digitize(xs, bins); bx, bm = [], []
                for bi in range(1, len(bins)):
                    sel = ys[idx == bi]
                    if len(sel) >= 3: bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
                ax.plot(bx, bm, "--o" if is_ref else "-o", color=COL[lab] if is_ref else "#222",
                        lw=1.6 if is_ref else 2, ms=3, zorder=3 if is_ref else 4,
                        label=(f"{lab} (reference), binned median" if is_ref else f"{lab}, binned median"))
                if not is_ref:
                    try:
                        kt_stats.add_corr_stats(ax, xs, ys, loc="upper right", fontsize=6.4)
                    except Exception:
                        pass
        ax.set_title(xl, fontsize=8.5)
        ax.set_xlabel(xl, fontsize=8); ax.set_ylabel(ylabel, fontsize=8)
    if ref_label:
        axs[0].legend(fontsize=6.6, loc="upper left")
    _sub = f" ({label} KTs, {ref_label} KTs shown as reference)" if ref_label else f" ({label} KTs)"
    fig.suptitle(f"{title}{_sub}", fontweight="bold", fontsize=11)
    _foot = []
    if ref_label:
        _foot.append(f"Correlation statistics are computed on the {label} points only; the {ref_label} series "
                     f"is a visual baseline, drawn fainter with a dashed binned-median trend.")
    if fence_hi is not None:
        _foot.append(f"{n_trimmed} outlier point(s) above {fence_hi:.3g} removed (robust IQR fence over all "
                     f"series and all three time references, so the panels share one y-scale).")
    if _foot:
        fig.text(0.005, -0.04, "  ".join(_foot), fontsize=6.8, color="#444", ha="left", va="top")
    _save(fig, outname, ["batch", "kt_state", "time_ref", "x", metric], allrows, title)


def chromo_violin(metric, ylabel, title, outname, labels=("polar", "paired", "lagging"), fmt="{:.1f}"):
    g = {k: [num(r, metric) for r in CH if r["paired_label"] == k and num(r, metric) is not None] for k in labels}
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    dmax = max((max(v) for v in g.values() if v), default=1)
    for i, k in enumerate(labels):
        d = g[k]
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, COL[k], alpha=0.28, lw=1.0, min_n=6)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[k], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
        ax.hlines(np.median(d), i-0.34, i+0.34, color=COL[k], lw=2.4)
        ax.text(i, dmax*1.02, f"med {fmt.format(np.median(d))}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=9); ax.set_ylabel(ylabel); ax.set_ylim(top=dmax*1.25)
    kt_stats.add_group_stats(ax, g, labels, loc="upper right")
    gs = [g[k] for k in labels if len(g[k]) >= 3]
    p = ""
    if len(gs) >= 2:
        try: p = f"   (Kruskal p={st.kruskal(*gs)[1]:.2g})" if len(gs) >= 3 else f"   (MW p={st.mannwhitneyu(*gs)[1]:.2g})"
        except Exception: pass
    ax.set_title(title + p, loc="left", fontweight="bold", fontsize=10.5)
    _save(fig, outname, ["paired_label", metric], [[r["paired_label"], num(r, metric)] for r in CH if num(r, metric) is not None], title, key="paired_label")


if __name__ == "__main__":
    print("=== metric vs mitotic time (polar) ===")
    time_refs("circularity", "circularity", "Polar-KT circularity vs mitotic time", "G6trk_circ_vs_time")
    time_refs("aspect_ratio", "aspect ratio", "Polar-KT stretch vs mitotic time", "G6trk_aspect_vs_time")
    time_refs("area_um2", "area (µm²)", "Polar-KT area vs mitotic time", "G6trk_area_vs_time")
    time_refs("dist_to_plate_um", "distance to plate (µm)", "Polar-KT distance-to-plate vs mitotic time", "G6trk_dist_vs_time")
    # USER 2026-08-03: "add the speed for a paired/plate kinetochore for reference/comparison"
    time_refs("speed_um_s", "speed (µm/s)", "Polar-KT speed vs mitotic time", "G6trk_speed_vs_time",
              ref_label="paired", trim_outliers=True)
    # USER 2026-08-03: "Why are plots for time until anaphase and time since metaphase onset that different?
    # Or make plot that's time until anaphase + time since metaphase (still just for polar or for polar plus
    # plate aligned). Use % stretch".
    # They looked different because the deck never showed the SAME metric on both time bases - it placed
    # aspect-vs-metaphase-onset next to area/circularity-vs-time-to-anaphase, so the axes were not comparable.
    # time_refs() already draws both bases (and post-anaphase) in one figure, so building % stretch here puts
    # the two side by side for one metric, with plate-aligned (paired) KTs as the reference series she asked for.
    # % stretch = elongation x 100 = (1 - minor/major) x 100: 0% is a round kinetochore, higher is more stretched.
    for _r in R:
        try:
            _e = float(_r.get("elongation", ""))
            _r["pct_stretch"] = str(round(_e * 100.0, 4))
        except (TypeError, ValueError):
            _r["pct_stretch"] = ""
    time_refs("pct_stretch", "% stretch  (1 - minor/major, x100)",
              "Polar-KT % stretch vs mitotic time - both time bases, plate-aligned reference",
              "G6trk_pct_stretch_vs_time", ref_label="paired", trim_outliers=True)
    print("=== chromosome-line geometry ===")
    chromo_violin("orient_vs_plate_deg", "chromosome angle vs plate (°: 0=parallel, 90=perpendicular)", "Chromosome orientation relative to the plate", "G6trk_chromo_orient", fmt="{:.0f}")
    chromo_violin("far_end_dist_um", "furthest chromosome end to plate (µm)", "Chromosome far-end distance from plate", "G6trk_chromo_farend")
    chromo_violin("near_end_dist_um", "closest chromosome end to plate (µm)", "Chromosome near-end distance from plate", "G6trk_chromo_nearend")
    chromo_violin("length_um", "chromosome length (µm)", "Chromosome length by paired kinetochore state", "G6trk_chromo_length")
    print("done")
