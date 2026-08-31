#!/usr/bin/env python3
"""WITHIN-CELL polar-vs-paired tension over time (user 2026-07-23): for each cell that has BOTH a polar
(sisterless) KT and paired sisters, compare the polar KT's EQUIVALENT tension (from its spindle strain via
the metaphase-sister calibration) to that same cell's paired k-k, as a function of minutes from metaphase
onset. Each cell is its own control."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
# USER 2026-08-05: "ultimately i want all the same plots but just with the updated info, so just makring
# them as retured isnt really a solution". Same two figures, same names, new metric.
#
# The polar series used to be `a_fit + b_fit*spindle_strain` — a calibration fitted at R2=0.001, i.e. a
# constant — plotted in um against paired MEASURED k-k, also in um. Same unit, different quantities, one
# of them not a measurement. Both series are now the SAME measurement on the SAME axis: DISTORTION along
# the spindle axis (extent across the plate over extent along it), for polar and paired alike, so the
# ratio compares like with like. The calibration is not computed at all any more.
SRC = [f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"]

TEN = list(csv.DictReader(open(SRC[0])))
def num(r, k):
    try: return float(r[k])
    except Exception: return None

ph = phase_times(sorted({r["batch"] for r in TEN}))
def tmeta(b, t):
    mt = ph.get(b, (None, None))[0]
    return ((t - mt) / 60.0) if (mt is not None and t is not None) else None

def ana_min(b):
    """That cell's anaphase onset, in minutes from its own metaphase onset."""
    mt, at = ph.get(b, (None, None))
    return ((at - mt) / 60.0) if (mt is not None and at is not None) else None

# per cell: polar and paired loading-axis strain over time. Outlier rows are kept in the CSV, skipped here.
polar = collections.defaultdict(list)
paired = collections.defaultdict(list)
for r in TEN:
    if r.get("outlier") == "1": continue
    v = num(r, "spindle_strain"); x = tmeta(r["batch"], num(r, "t_sec"))
    if v is None or x is None: continue
    if r["label"] == "polar":  polar[r["batch"]].append((x, v))
    if r["label"] == "paired": paired[r["batch"]].append((x, v))
both = sorted(set(polar) & set(paired), key=lambda b: -len(paired[b]))

COLp, COLk = "#e6820e", "#3b6fb6"

# ── USER 2026-08-16, artboard-7 panels ───────────────────────────────────────────────────────────
# "change the axes over which these line plots are plotted such that they start at 0 (metaphase onset)
#  and end at anaphase onset. also label each of the plots with the fate of the sisterless kinetochore
#  plotted within (polar, congressed, etc; if it was from a 1/2/3 sisterless cell, and if there were
#  lagging after anaphase)."
# This SUPERSEDES her 2026-08-04 instruction that the polar line should continue past anaphase to show the
# post-onset spikes: the window is now 0 -> anaphase for BOTH series. The earlier behaviour is preserved in
# kt_tension_withincell.py.bak_pre_ab7_20260816 in case she wants it back.
# Fate comes from HER recorded master columns, not from a regex over prose (§14 2026-08-14: her structured
# records beat my inference). "polar" here is the BEHAVIOURAL flag, which is what "fate" means in her
# sentence — distinct from an outline LABEL, which is identity (§1 rule 27).
_MRW = {r["Batch Name"]: r for r in lib.load_master()[0]}
def _fate_label(b):
    r = _MRW.get(b, {}) or {}
    sis = (r.get("# Sisterless KTs", "") or "?").strip()
    pol = (r.get("Polar Chromosomes", "") or "").strip().lower()
    lag = (r.get("Lagging Chromosomes", "") or "").strip().lower()
    fate = "polar to anaphase" if pol.startswith("y") else ("congressed" if pol.startswith("n") else "fate n/r")
    lagtxt = "lagging after ana" if lag.startswith("y") else ("no lagging" if lag.startswith("n") else "lagging n/r")
    return f"{sis}-sisterless · {fate} · {lagtxt}"




def _save(fig, name, cap):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try: lib.record_plot(name, ["x"], [], {"family": "tension"}, script=__file__, caption=cap, source=SRC, key_column=None, fig=fig)
    except Exception: pass
    print("  " + name)


if __name__ == "__main__":
    # small multiples: one panel per cell, polar equiv-kk (orange) + paired actual kk (blue) over time
    n = len(both); cols = 3; rows = (n + cols - 1) // cols
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 4.3, rows * 3.4), squeeze=False)
    for ax, b in zip(axs.flat, both):
        # USER 2026-08-04: "on each individual plot mark metaphase onset (0s) and anaphase onset (and stop
        # plotting the line for paired after anaphase onset)".
        _am = ana_min(b)
        p = sorted(polar[b]); k = sorted(paired[b])
        # USER 2026-08-16: window is 0 (metaphase onset) -> anaphase onset, for BOTH series.
        p = [z for z in p if z[0] >= 0 and (_am is None or z[0] <= _am)]
        k = [z for z in k if z[0] >= 0 and (_am is None or z[0] <= _am)]
        # 🔴 HER 2026-08-20, board-7 item 3: *"Would it be helpful to viewers if i applied a simple, common
        # smoothing technique on the jagged lines in these plots, like Jon Kuhn's three-point smoothing ...
        # specifically to make a plot more viewable (unsmoothed data still used for analysis)"* — yes, and it
        # is her lab's own convention, so it is applied here. The RAW trace stays visible underneath as a
        # faint line, so nothing is hidden, and NOTHING downstream is smoothed: every statistic, the recorded
        # data CSV and every other figure still use the unsmoothed values. Presentation only.
        def _sm3(v):
            if len(v) < 3: return v
            return [v[0]] + [ (v[i-1] + v[i] + v[i+1]) / 3.0 for i in range(1, len(v)-1) ] + [v[-1]]
        _px, _py = [z[0] for z in p], [z[1] for z in p]
        _kx, _ky = [z[0] for z in k], [z[1] for z in k]
        ax.plot(_px, _py, "-", lw=0.7, color=COLp, alpha=0.30, zorder=1)
        ax.plot(_kx, _ky, "-", lw=0.7, color=COLk, alpha=0.30, zorder=1)
        ax.plot(_px, _sm3(_py), "-o", ms=2, color=COLp, label="polar", zorder=3)
        ax.plot(_kx, _sm3(_ky), "-s", ms=2, color=COLk, alpha=0.8, label="paired", zorder=3)
        ax.axvline(0, ls="--", color="#3b6fb6", lw=1)
        if _am is not None: ax.axvline(_am, ls="--", color="#d1495b", lw=1)
        ax.axhline(1.0, ls=":", color="#999", lw=0.8)
        if _am is not None: ax.set_xlim(0, _am)
        else: ax.set_xlim(left=0)
        ax.set_title(b.split(" ", 1)[-1][:24] + "\n" + _fate_label(b), fontsize=7.2)
        # 🔴 HER 2026-08-20, board-7 item 3: *"in adobe illustrator put some text above each of these 6 plots
        # that just says if its from a 3- or 1-sisterless cell."* The panel TITLE already said it — but the
        # publication render STRIPS titles, and these panels are placed from the publication library, so on
        # the deck the label was gone. An in-axes annotation survives that strip, so the cell type travels
        # with the panel wherever it is placed.
        _sis = (_MRW.get(b, {}) or {}).get("# Sisterless KTs", "").strip() or "?"
        ax.text(0.015, 0.97, f"{_sis}-sisterless cell", transform=ax.transAxes,
                fontsize=7.4, fontweight="bold", va="top", ha="left", color="#222",
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec="none", alpha=0.75), zorder=9)
        ax.set_xlabel("min from metaphase", fontsize=7)
        ax.set_ylabel("kinetochore distortion", fontsize=7)
    for ax in axs.flat[n:]:
        ax.axis("off")
    axs.flat[0].legend(fontsize=6.5)
    # suptitle sat on top of the first row's panel titles; reserve a strip for it instead
    # 2026-08-16: the suptitle has to clear the first row by a real margin, because dataops/
    # split_panels_20260809.py crops each panel to its own tight bbox and was catching the last suptitle
    # line inside the top-row panels — visible as stray text across the top of __p1.._p3.
    fig.suptitle(f"Within-cell polar vs paired kinetochore distortion ({n} cells)",
                 fontweight="bold", fontsize=10.5, y=0.999, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    _save(fig, "G6ten_withincell_over_time", "within-cell polar vs paired spindle-axis distortion over time; blue = metaphase onset, red = anaphase onset")

    # ratio polar/paired per cell over time (paired interpolated to polar timepoints)
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    allr = []
    for b in both:
        p = sorted(polar[b]); k = sorted(paired[b])
        if len(k) < 2: continue
        kx = np.array([z[0] for z in k]); ky = np.array([z[1] for z in k])
        xs, rs = [], []
        for x, pv in p:
            if kx.min() - 3 <= x <= kx.max() + 3:
                kv = np.interp(x, kx, ky)
                if kv > 0.05:
                    xs.append(x); rs.append(pv / kv); allr.append((x, pv / kv))
        if xs:
            ax.plot(xs, rs, "-o", ms=3, lw=1.2, alpha=0.8, label=b.split(" ", 1)[-1][:20])
    ax.axhline(1.0, ls="--", color="#333", lw=1.2)
    ax.axvline(0, ls=":", color="#888", lw=1)
    if allr:
        med = np.median([r for _, r in allr])
        ax.text(0.02, 0.98, f"median ratio = {med:.2f}× (polar/paired)\n>1 = polar under more tension\nN={len(both)} cells",
                transform=ax.transAxes, va="top", fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("minutes from metaphase onset"); ax.set_ylabel("polar / paired spindle-axis distortion ratio")
    ax.set_title("Within-cell polar-vs-paired kinetochore distortion ratio over time", loc="left", fontweight="bold", fontsize=11)
    ax.legend(fontsize=7, ncol=2)
    _save(fig, "G6ten_withincell_ratio_time", "within-cell polar/paired spindle-axis distortion ratio over time")
    print(f"{len(both)} cells with both a polar and a paired distortion series")
