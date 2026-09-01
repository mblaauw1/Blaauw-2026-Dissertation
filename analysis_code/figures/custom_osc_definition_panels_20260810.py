#!/usr/bin/env python3
"""The three groups plotted under EVERY definition of period and amplitude, not just summarised.

USER 2026-08-10: "also, i want to see the plots under these different definitions".

The sensitivity figure (G6_osc_metric_sensitivity_threegroup) reduces each definition to one effect size,
which answers "does the contrast survive?" but hides what the distributions actually look like -- whether a
definition changes the answer by shifting one group, by compressing everyone, or by moving a couple of
points. These panels show the data itself: one panel per definition, the same three groups, same unit
(per KINETOCHORE, paired only), with n, Kruskal-Wallis and the three pairwise Mann-Whitney p-values on
every panel so no panel has to be read against another figure.

The manually-excluded outlier is honoured here too, through lib.manual_point_exclusions on the same
plot ids, so these panels agree with G6_three_group_period rather than quietly disagreeing with it.

Definitions and cohorts are imported from the existing builders so nothing is re-derived.
"""
import sys, os, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, kruskal

import lib
import custom_prometa_vs_meta_20260810 as SRC
import custom_osc_metric_sensitivity_20260810 as SENS

OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group6"
os.makedirs(OUT, exist_ok=True)

# The exclusion is recorded against the PERIOD plots only, and that is deliberate: the point is bad because
# the zero-crossing period estimator returned twice the window length for a drifting kinetochore, which says
# nothing about how far it swung. Its AMPLITUDE is a normal value and is kept, exactly as the production
# G6_three_group_amplitude keeps it (n=33). So the two grids ask the exclusions file separately rather than
# sharing one list -- applying a period-specific decision to amplitude would be silent over-removal.
def keep(K, plot_id):
    ex = lib.manual_point_exclusions(plot_id)
    return [k for k in K if (k["cell"], str(k["kt"])) not in ex] if ex else K


def groups(plot_id):
    g = [("single\nPROMETAPHASE", keep(SRC.kt_single_prometa, plot_id), "#2a7fff"),
         ("single\nMETAPHASE",    keep(SRC.kt_single_meta, plot_id),    "#7fb2ff"),
         ("3-sisterless\nMETAPHASE", keep(SRC.kt_triple_meta, plot_id), "#ff5a3c")]
    ex = lib.manual_point_exclusions(plot_id)
    print(f"{plot_id}: excluded {sorted(ex) if ex else 'none'};  n = {[len(k) for _l, k, _c in g]}")
    return g


G3 = groups("G6_three_group_period")


def mw(a, b):
    return mannwhitneyu(a, b, alternative="two-sided").pvalue if len(a) >= 3 and len(b) >= 3 else float("nan")


def grid(defs, is_amp, ylab, supt, name, ncols=3, G3=None):
    nrow = int(np.ceil(len(defs) / ncols))
    fig, axs = plt.subplots(nrow, ncols, figsize=(4.9 * ncols, 4.5 * nrow), squeeze=False)
    rows_rec = []
    for di, (dname, fn) in enumerate(defs.items()):
        ax = axs[di // ncols][di % ncols]
        vals = []
        for lab, K, col in G3:
            v = []
            for k in K:
                try:
                    r = fn(k["pos"], k["t"]) if is_amp else fn(k["t"], k["pos"])
                except Exception:
                    r = None
                if r is not None and np.isfinite(r): v.append(float(r))
            vals.append(v)
        for i, ((lab, _K, col), v) in enumerate(zip(G3, vals)):
            if not v: continue
            x = np.random.default_rng(i).normal(i, 0.075, len(v))
            ax.scatter(x, v, c=col, s=30, alpha=.72, edgecolor="k", lw=.3, zorder=3)
            ax.boxplot(v, positions=[i], widths=.55, showfliers=False)
        ok = [v for v in vals if len(v) >= 3]
        kw = kruskal(*ok).pvalue if len(ok) == 3 else float("nan")
        pAB, pAC, pBC = mw(vals[0], vals[1]), mw(vals[0], vals[2]), mw(vals[1], vals[2])
        ax.set_xticks(range(3))
        ax.set_xticklabels([f"{lab}\n(n={len(v)})" for (lab, _, _), v in zip(G3, vals)], fontsize=7.5)
        ax.set_ylabel(ylab, fontsize=9)
        ax.set_title(f"{dname}\nKruskal-Wallis p={kw:.3g}", fontsize=10, fontweight="bold")
        ax.text(0.0, -0.20, f"P:M1 p={pAB:.3g}   P:M3 p={pAC:.3g}   M1:M3 p={pBC:.3g}",
                transform=ax.transAxes, fontsize=7, color="#555", va="top")
        ax.grid(alpha=.3, axis="y")
        for i, v in enumerate(vals):
            for x in v:
                rows_rec.append([dname, G3[i][0].replace("\n", " "), round(float(x), 5)])
    for k in range(len(defs), nrow * ncols):
        axs[k // ncols][k % ncols].axis("off")
    fig.suptitle(supt, fontweight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0.01, 1, 0.955])
    p = os.path.join(OUT, name + ".png")
    fig.savefig(p, dpi=200)
    print(f"wrote {p}")
    lib.record_plot(name, ["definition", "group", "value"], rows_rec,
                    {"kind": "three-group distributions under each definition",
                     "unit": "one point per KINETOCHORE, paired KTs only",
                     "excluded_points": sorted(f"{b} kt{k}" for b, k in lib.manual_point_exclusions(name)) or "none",
                     "groups": "P single prometaphase, M1 single metaphase, M3 triple metaphase"},
                    __file__, supt, key_column=None)
    return p


grid(SENS.PERIODS, False, "period (min)",
     "Oscillation period per kinetochore, under six definitions\n"
     "paired KTs only; the 30.3-min prometaphase outlier is excluded throughout",
     "G6_period_by_definition_panels", G3=G3)

grid(SRC.STATS, True, "amplitude (um)",
     "Oscillation amplitude per kinetochore, under seven definitions\npaired KTs only",
     "G6_amplitude_by_definition_panels", ncols=4,
     G3=groups("G6_three_group_amplitude"))
