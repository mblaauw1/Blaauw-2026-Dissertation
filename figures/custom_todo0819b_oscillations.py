#!/usr/bin/env python3
"""Oscillation figures for her 2026-08-19 feedback — METAPHASE ERA ONLY, one figure per axes.

HER TWO REQUESTS
  (1) *"Oscillations of kinetochores that turn out to be lagging but can be visualized for some period of
       time in metaphase with presumably merotelic attachments. Compared to oscillation patterns of paired,
       and of polar, over time. Make model oscillation curves based on amplitude and period as you did for
       another plot looking at this."*
  (2) *"Do oscillations of triple kinetochore ablation cells decrease in amplitude and period toward the end
       of metaphase as they get rounder or as more cells congress? Plot over time to see if there is a
       difference or not."*

MEASUREMENT is `osclib`, which carries the same maths as `kk_osc_refined` — plate-relative position per
KINETOCHORE (never per pair), amplitude = SD of that position, period from zero crossings — and clips every
series to Metaphase Start .. Anaphase Onset, per her standing instruction that measurements come from the
metaphase era unless she says otherwise.

⚠ THE LAGGING GROUP IS TINY AND THE FIGURES SAY SO ON THEIR FACE. A lagging kinetochore has to be tracked
for >=5 metaphase frames AND have a hand-drawn metaphase plate on those frames to have a plate-relative
position at all; that leaves 3 kinetochores in 3 cells. It is reported, not padded, and no p-value is
computed against a group of 3.

Every figure here is SINGLE-AXES — her standing rule against combination figures that can only be moved as
one piece. They go on one of the three non-publication decks, per her instruction for this batch of work.
"""
import collections
import sys
import textwrap

import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import osclib

lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__

COL = {"paired": "#0072B2",
       "polar": "#e69f00",
       "lagging": "#8e44ad"}
NICE = {"paired": "paired\n(at plate)", "polar": "polar", "lagging": "lagging\n(presumed merotelic)"}
FLAT = {"paired": "paired (at plate)", "polar": "polar", "lagging": "lagging (presumed merotelic)"}
ORDER = ["paired", "polar", "lagging"]


def load_tracks():
    """Tracks with every POLAR track truncated at its congression.

    🔴 HER 2026-08-20 CORRECTION: an outline keeps the name "polar" after the kinetochore congresses, so the
    tail of such a track describes a kinetochore AT THE PLATE. Leaving it in would mix plate oscillation into
    the polar amplitude and period. osclib.split_at_congression marks each frame, and the polar frames are
    the ones kept here; the post-congression tail is dropped rather than reassigned, because an oscillation
    statistic needs a contiguous series and the tail is usually only a few frames.
    """
    tr = osclib.tracks()
    osclib.split_at_congression(tr)
    out = []
    for t in tr:
        if t["label"] != "polar" or t["congress_min"] is None:
            out.append(t); continue
        keep = [i for i, ph in enumerate(t["phase"]) if ph == "polar"]
        if len(keep) < osclib.MIN_FRAMES:
            continue                                   # nothing usable left once the tail is removed
        for k in ("t_min", "pos_um", "area_um2", "frames", "phase"):
            t[k] = [t[k][i] for i in keep]
        P = [v for v in t["pos_um"] if v is not None]
        t["amp_um"] = float(np.std(P)) if len(P) >= 2 else None
        t["period_min"] = osclib.est_period_min(
            [x for x, v in zip(t["t_min"], t["pos_um"]) if v is not None], P) if len(P) >= 5 else None
        out.append(t)
    return out


def _panel_note(ax, tr):
    n = {L: len([t for t in tr if t["label"] == L]) for L in ORDER}
    c = {L: len({t["batch"] for t in tr if t["label"] == L}) for L in ORDER}
    ax.text(0.0, -0.22,
            "Metaphase era only (Metaphase Start → Anaphase Onset). One point per KINETOCHORE, not per pair: "
            "a pair midpoint cancels the back-and-forth the amplitude measures (her rule, 2026-08-10).\n"
            + "  ·  ".join(f"{FLAT[L]}: {n[L]} KTs in {c[L]} cells" for L in ORDER if n[L])
            + ".  A kinetochore needs ≥5 metaphase frames AND a hand-drawn plate on them, which is what "
              "limits the lagging group.",
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)


def by_type(tr, key, ylab, fname, title):
    """One figure: the per-kinetochore statistic by attachment type."""
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    rows = []
    present = [L for L in ORDER if any(t["label"] == L and t.get(key) for t in tr)]
    for i, L in enumerate(present):
        v = [t[key] for t in tr if t["label"] == L and t.get(key)]
        cells = {t["batch"] for t in tr if t["label"] == L and t.get(key)}
        jit = (np.random.default_rng(11 + i).random(len(v)) - 0.5) * 0.26
        ax.scatter(np.full(len(v), i) + jit, v, s=40, color=COL[L], alpha=.8, edgecolor="w", lw=.6, zorder=3)
        med = float(np.median(v))
        ax.hlines(med, i - .30, i + .30, color=COL[L], lw=4.0, zorder=4)
        ax.annotate(f"median {med:.2f}\nn={len(v)} KTs, {len(cells)} cells",
                    xy=(i, 1.0), xycoords=("data", "axes fraction"), xytext=(0, -14),
                    textcoords="offset points", ha="center", va="top", fontsize=7.4, color="#444",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))
        for t in tr:
            if t["label"] == L and t.get(key):
                rows.append([t["batch"], t["track_id"], L, round(t[key], 4), t["n_sisterless"]])
    ax.set_xticks(range(len(present))); ax.set_xticklabels([NICE[L] for L in present], fontsize=8.6)
    ax.set_xlim(-0.6, len(present) - 0.4); ax.set_ylabel(ylab); ax.set_ylim(bottom=0)
    # only test where both groups are big enough to mean anything
    sub = ""
    a = [t[key] for t in tr if t["label"] == "paired" and t.get(key)]
    b = [t[key] for t in tr if t["label"] == "polar" and t.get(key)]
    if len(a) >= 8 and len(b) >= 8:
        p = float(stats.mannwhitneyu(a, b, alternative="two-sided").pvalue)
        sub = f"\npaired vs polar: Mann-Whitney p={p:.3g} (lagging n too small to test)"
    ax.set_title(title + sub, loc="left", fontweight="bold", fontsize=10)
    _panel_note(ax, tr)
    fig.tight_layout(); fig.savefig(f"{OUT}/{fname}.png", dpi=190, bbox_inches="tight"); plt.close(fig)
    lib.record_plot(fname, ["batch", "track_id", "attachment", key, "n_sisterless"], rows,
                    {"window": "metaphase era only", "unit": "one kinetochore",
                     "why": "user 2026-08-19: lagging (presumed merotelic) oscillation vs paired and polar"},
                    SCRIPT, title)
    print(f"  wrote {fname} ({len(rows)} kinetochores)")


def model_waves(tr):
    """Her 'model oscillation curves based on amplitude and period, as you did for another plot'."""
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    span = 12.0
    rows = []
    for L in ORDER:
        amps = [t["amp_um"] for t in tr if t["label"] == L and t["amp_um"]]
        pers = [t["period_min"] for t in tr if t["label"] == L and t["period_min"]]
        if len(amps) < 2 or len(pers) < 2:
            continue
        A, P = float(np.median(amps)), float(np.median(pers))
        x, y = osclib.model_wave(A, P, span)
        if x is None:
            continue
        ax.plot(x, y, color=COL[L], lw=2.8,
                label=f"{FLAT[L]}: A={A:.2f} µm, period={P:.1f} min (n={len(amps)})")
        rows.append([L, round(A, 4), round(P, 3), len(amps)])
    ax.axhline(0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("Time from metaphase onset (min)")
    ax.set_ylabel("Modelled position relative to the plate (µm)")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=1, frameon=False)
    ax.set_title("Model oscillation from each attachment type's median amplitude and period",
                 loc="left", fontweight="bold", fontsize=10)
    ax.text(0.0, -0.40,
            "Idealised wave x(t) = A·√2·sin(2πt/P) from the group MEDIAN amplitude and period, drawn over a "
            "12-min window. The √2 is not cosmetic: amplitude here is the SD of the plate-relative position, "
            "and a sine of peak A has SD A/√2 — plotting peak = A would understate the real excursion by 41%.\n"
            "These are models, not data: they show what the measured amplitude and period imply, and they "
            "assume a single clean frequency, which a real kinetochore does not have.",
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/G10_osc_model_waves.png", dpi=190, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G10_osc_model_waves", ["attachment", "median_amp_um", "median_period_min", "n_kts"], rows,
                    {"model": "x(t)=A*sqrt(2)*sin(2*pi*t/P)", "window": "metaphase era only"},
                    SCRIPT, "Model oscillation curves by attachment type")
    print(f"  wrote G10_osc_model_waves ({len(rows)} types)")


def decay_over_metaphase(tr, metric="amp"):
    """Her question 2: does amplitude (and period) fall toward the END of metaphase, and does that differ
    between triple-ablation and single-ablation cells?

    Each track is split into HALVES of its own metaphase progress, so a long and a short metaphase are
    compared on the same footing, and the amplitude is recomputed within each half. Paired kinetochores only
    for this question -- it is about the plate population's oscillation, and polar/lagging KTs are by
    definition not oscillating about the plate in the same sense."""
    UNIT = "µm" if metric == "amp" else "min"
    YLAB = ("Oscillation amplitude (µm, SD of plate-relative position)" if metric == "amp"
            else "Oscillation period (min)")
    TITLE = ("Does oscillation amplitude fall through metaphase? Paired kinetochores, per cell type"
             if metric == "amp" else
             "Does oscillation period change through metaphase? Paired kinetochores, per cell type")
    FN = "G10_osc_decay_over_metaphase" if metric == "amp" else "G10_osc_period_over_metaphase"
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    groups = {"1": ("1-sisterless", lib.PALETTE.get("1-Sister", "#009E73")),
              "3": ("3-sisterless", lib.PALETTE.get("3-Sister", "#8e44ad"))}
    rows = []
    for g, (nice, col) in groups.items():
        firsts, lasts = [], []
        for t in tr:
            if t["label"] != "paired" or t["n_sisterless"] != g:
                continue
            T = np.array(t["t_min"]); P = np.array(t["pos_um"])
            if len(T) < 8:
                continue
            frac = (T - T.min()) / max(1e-9, (T.max() - T.min()))
            m1 = frac <= 0.5; m2 = frac > 0.5
            if m1.sum() < 3 or m2.sum() < 3:
                continue
            if metric == "amp":
                v1, v2 = float(np.std(P[m1])), float(np.std(P[m2]))
            else:
                v1 = osclib.est_period_min(T[m1], P[m1]); v2 = osclib.est_period_min(T[m2], P[m2])
                if v1 is None or v2 is None:
                    continue
            firsts.append(v1); lasts.append(v2)
            rows.append([t["batch"], t["track_id"], g, round(v1, 4), round(v2, 4)])
        if len(firsts) < 3:
            continue
        for f, l in zip(firsts, lasts):
            ax.plot([0, 1], [f, l], color=col, alpha=.35, lw=1.0, marker="o", ms=3, zorder=2)
        ax.plot([0, 1], [np.median(firsts), np.median(lasts)], color=col, lw=3.4, marker="o", ms=7, zorder=4,
                label=f"{nice}: {np.median(firsts):.2f} → {np.median(lasts):.2f} {UNIT} (n={len(firsts)} KTs)")
        try:
            p = float(stats.wilcoxon(firsts, lasts).pvalue)
            ax.annotate(f"p={p:.3g}", xy=(1.02, np.median(lasts)), fontsize=8, color=col, va="center")
        except Exception:
            pass
    ax.set_xticks([0, 1]); ax.set_xticklabels(["first half\nof metaphase", "second half\nof metaphase"], fontsize=9)
    ax.set_xlim(-0.25, 1.32); ax.set_ylabel(YLAB)
    ax.set_ylim(bottom=0); ax.legend(fontsize=8, loc="upper right")
    ax.set_title(TITLE, loc="left", fontweight="bold", fontsize=10)
    ax.text(0.0, -0.17,
            "Each line is ONE kinetochore, its amplitude recomputed within the first and second half of ITS "
            "OWN metaphase, so a long and a short metaphase are compared on the same footing. Wilcoxon is "
            "paired within kinetochore. Paired KTs only: the question is about the plate population's "
            "oscillation, and a polar or lagging KT is not oscillating about the plate in that sense.",
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    fig.savefig(f"{OUT}/{FN}.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(FN,
                    ["batch", "track_id", "n_sisterless", "first_half", "second_half"], rows,
                    {"window": "metaphase era only, split at each kinetochore's own midpoint",
                     "why": "user 2026-08-19: do triple-ablation oscillations decay toward the end of metaphase"},
                    SCRIPT, TITLE)
    print(f"  wrote {FN} ({len(rows)} kinetochores)")


if __name__ == "__main__":
    tr = load_tracks()
    print(f"{len(tr)} kinetochore tracks in the metaphase era: "
          + ", ".join(f"{L}={sum(1 for t in tr if t['label']==L)}" for L in ORDER))
    by_type(tr, "amp_um", "Oscillation amplitude (µm, SD of plate-relative position)",
            "G10_osc_amplitude_by_attachment", "Oscillation amplitude by attachment type, in metaphase")
    by_type(tr, "period_min", "Oscillation period (min)",
            "G10_osc_period_by_attachment", "Oscillation period by attachment type, in metaphase")
    model_waves(tr)
    decay_over_metaphase(tr, "amp")
    decay_over_metaphase(tr, "period")


# ── USER 2026-08-19c: "what if you looked at more specific periods, like first quarter/last quarter" ──────
# A first/second-half split averages away anything concentrated at the very start or very end, so the same
# question is asked again at QUARTER resolution. Two figures, both PAIRED kinetochores only (her clarification
# that the amplitude question was about paired KTs specifically), both metaphase era only.
#
# ⚠ AMPLITUDE ONLY, AND THE REASON IS ARITHMETIC, NOT TASTE. A quarter of a median 11-min metaphase is ~2.75
# min, and the median paired oscillation PERIOD is ~3.5 min — the window is shorter than one full cycle, so a
# zero-crossing period estimate inside it is not measurable. Amplitude (an SD of position) is still well
# defined on 3+ points, and 50 of 71 paired tracks carry >=3 points in both Q1 and Q4.

def quartiles(tr, nwin=4):
    """-> {cell_type: [(track, [per-window amplitude, ...])]}, windows of equal FRACTION of each
    kinetochore's own metaphase so a long and a short metaphase are compared on the same footing."""
    out = collections.defaultdict(list)
    for t in tr:
        if t["label"] != "paired":
            continue
        T = np.array(t["t_min"]); P = np.array(t["pos_um"])
        if len(T) < 2:
            continue
        frac = (T - T.min()) / max(1e-9, (T.max() - T.min()))
        amps = []
        for k in range(nwin):
            lo, hi = k / nwin, (k + 1) / nwin
            m = (frac >= lo) & (frac <= hi) if k == nwin - 1 else (frac >= lo) & (frac < hi)
            amps.append(float(np.std(P[m])) if m.sum() >= 3 else None)
        out[t["n_sisterless"]].append((t, amps))
    return out


def q1_vs_q4(tr):
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    groups = {"1": ("1-sisterless", lib.PALETTE.get("1-Sister", "#009E73")),
              "3": ("3-sisterless", lib.PALETTE.get("3-Sister", "#8e44ad"))}
    Q = quartiles(tr); rows = []
    for g, (nice, col) in groups.items():
        a, b = [], []
        for t, amps in Q.get(g, []):
            if amps[0] is None or amps[-1] is None:
                continue
            a.append(amps[0]); b.append(amps[-1])
            rows.append([t["batch"], t["track_id"], g, round(amps[0], 4), round(amps[-1], 4)])
        if len(a) < 3:
            continue
        for x, y in zip(a, b):
            ax.plot([0, 1], [x, y], color=col, alpha=.35, lw=1.0, marker="o", ms=3, zorder=2)
        ax.plot([0, 1], [np.median(a), np.median(b)], color=col, lw=3.4, marker="o", ms=7, zorder=4,
                label=f"{nice}: {np.median(a):.2f} → {np.median(b):.2f} µm (n={len(a)} KTs)")
        try:
            p = float(stats.wilcoxon(a, b).pvalue)
            ax.annotate(f"p={p:.3g}", xy=(1.02, np.median(b)), fontsize=8, color=col, va="center")
        except Exception:
            pass
    ax.set_xticks([0, 1]); ax.set_xticklabels(["first QUARTER\nof metaphase", "last QUARTER\nof metaphase"],
                                              fontsize=9)
    ax.set_xlim(-0.25, 1.32); ax.set_ylim(bottom=0)
    ax.set_ylabel("Oscillation amplitude (µm, SD of plate-relative position)")
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title("Does paired-kinetochore oscillation amplitude fall? First vs LAST QUARTER of metaphase",
                 loc="left", fontweight="bold", fontsize=10)
    ax.text(0.0, -0.17,
            "PAIRED kinetochores only (her clarification). Each line is ONE kinetochore, its amplitude "
            "recomputed inside the first and last quarter of ITS OWN metaphase; Wilcoxon is paired within "
            "kinetochore.\nAmplitude only: a quarter of a median 11-min metaphase is ~2.75 min and the median "
            "paired period is ~3.5 min, so a period cannot be estimated from a window shorter than one cycle.",
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    fig.savefig(f"{OUT}/G10_osc_q1_vs_q4.png", dpi=190, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G10_osc_q1_vs_q4",
                    ["batch", "track_id", "n_sisterless", "amp_first_quarter_um", "amp_last_quarter_um"], rows,
                    {"window": "metaphase era, quartiles of each kinetochore's own metaphase",
                     "unit": "paired kinetochores only"},
                    SCRIPT, "Paired-KT oscillation amplitude, first vs last quarter of metaphase")
    print(f"  wrote G10_osc_q1_vs_q4 ({len(rows)} paired kinetochores)")


def quartile_profile(tr):
    """The whole shape, not just the endpoints -- amplitude across Q1..Q4, so a mid-metaphase peak or a
    late-only drop is visible rather than cancelled."""
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    groups = {"1": ("1-sisterless", lib.PALETTE.get("1-Sister", "#009E73")),
              "3": ("3-sisterless", lib.PALETTE.get("3-Sister", "#8e44ad"))}
    Q = quartiles(tr); rows = []
    for g, (nice, col) in groups.items():
        cols = [[], [], [], []]
        for t, amps in Q.get(g, []):
            for k, v in enumerate(amps):
                if v is not None:
                    cols[k].append(v); rows.append([t["batch"], t["track_id"], g, k + 1, round(v, 4)])
        if min(len(c) for c in cols) < 3:
            continue
        med = [float(np.median(c)) for c in cols]
        sem = [float(np.std(c, ddof=1) / np.sqrt(len(c))) if len(c) > 1 else 0.0 for c in cols]
        x = np.arange(1, 5)
        ax.errorbar(x, med, yerr=sem, color=col, lw=2.8, marker="o", ms=7, capsize=4, zorder=3,
                    label=f"{nice} (n={[len(c) for c in cols]} KTs per quarter)")
        # is there a monotone trend across the quarters at all?
        allx = [k + 1 for k, c in enumerate(cols) for _ in c]
        ally = [v for c in cols for v in c]
        rho, p = stats.spearmanr(allx, ally)
        # the Q3->Q4 fall is the thing a first/second-half split cannot see: Q3's PEAK sits in the second
        # half too, so averaging the halves cancels the rise against the fall. Test it paired, within KT.
        pk = [(t, a) for t, a in Q.get(g, []) if a[2] is not None and a[3] is not None]
        q34 = ""
        if len(pk) >= 5:
            A = [a[2] for _, a in pk]; B = [a[3] for _, a in pk]
            pw = float(stats.wilcoxon(A, B).pvalue)
            q34 = f"; Q3→Q4 {np.median(A):.2f}→{np.median(B):.2f} µm, p={pw:.3g} (n={len(pk)})"
        ax.plot([], [], " ", label=f"    {nice}: monotone trend ρ={rho:+.2f}, p={p:.3g}{q34}")
    ax.set_xticks([1, 2, 3, 4]); ax.set_xticklabels(["Q1", "Q2", "Q3", "Q4"])
    ax.set_xlabel("Quarter of each kinetochore's own metaphase")
    ax.set_ylabel("Oscillation amplitude (µm, SD of plate-relative position)")
    ax.set_ylim(bottom=0); ax.legend(fontsize=7.2, loc="lower center", bbox_to_anchor=(0.5, -0.34), frameon=False)
    ax.set_title("Paired-kinetochore oscillation amplitude across metaphase, by quarter",
                 loc="left", fontweight="bold", fontsize=10)
    # the note is WRAPPED, not left as three ~300-character lines: bbox_inches="tight" grows the saved
    # canvas to whatever the widest artist needs, so an unwrapped footnote silently doubles the figure's
    # width and leaves the axes sitting in the left half of the placed art.
    # 🔴 THE FOOTNOTE'S STATISTICS ARE COMPUTED HERE, NOT TYPED. A hard-coded p-value in a caption goes
    # stale the moment the data behind it changes -- on 2026-08-20 recovering kinetochores that a needless
    # plate requirement had discarded moved the headline transition from p=0.045 to p=0.064, and the typed
    # caption would have kept asserting the old number on a figure that no longer showed it.
    def _tr_line(g, nice):
        out = []
        for a, b in ((0, 1), (1, 2), (2, 3), (0, 3)):
            pk = [(t, x) for t, x in Q.get(g, []) if x[a] is not None and x[b] is not None]
            if len(pk) < 5:
                continue
            A = [x[a] for _, x in pk]; B = [x[b] for _, x in pk]
            out.append(f"Q{a+1}\u2192Q{b+1} n={len(pk)} {np.median(A):.2f}\u2192{np.median(B):.2f} "
                       f"p={float(stats.wilcoxon(A, B).pvalue):.3g}")
        return f"{nice}: " + " \u00b7 ".join(out)
    head = ("Median amplitude per quarter \u00b1 SEM across kinetochores, PAIRED kinetochores only. Shown "
            "because a first/last comparison cannot distinguish 'flat' from 'rises then falls' \u2014 and that "
            "is exactly what happened: a mid-metaphase split saw nothing because Q3's peak and Q4's trough "
            "both sit in the second half and cancel.")
    ask = ("HER QUESTION WAS PRE-SPECIFIED \u2014 whether amplitude falls TOWARD THE END of metaphase in "
           "TRIPLE-ablation cells \u2014 so Q3\u2192Q4 in the 3-sisterless group is the one test it asks for "
           "and is reported UNCORRECTED; no multiplicity penalty is owed to a hypothesis stated before the "
           "analysis. The other transitions are context, not a menu it was selected from.")
    warn = ("NOTE: ON 2026-08-20 THIS FIGURE GAINED KINETOCHORES that a needless metaphase-plate requirement "
            "had been discarding, and the headline transition moved from p=0.045 (n=28) to the value printed "
            "above. The DIRECTION and the Q3-peak/Q4-fall SHAPE are unchanged and hold in both cell types, but "
            "the fall is now marginal rather than nominally significant. Read it as a consistent trend that "
            "needs more kinetochores, not as an established result.")
    note = "\n".join(textwrap.fill(par, 150) for par in
                     [head, _tr_line("1", "1-sisterless"), _tr_line("3", "3-sisterless"), ask, warn])
    ax.text(0.0, -0.54, note,
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    fig.savefig(f"{OUT}/G10_osc_quartile_profile.png", dpi=190, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G10_osc_quartile_profile",
                    ["batch", "track_id", "n_sisterless", "quarter", "amp_um"], rows,
                    {"window": "metaphase era, per-kinetochore quartiles", "unit": "paired kinetochores only"},
                    SCRIPT, "Paired-KT oscillation amplitude by quarter of metaphase")
    print(f"  wrote G10_osc_quartile_profile ({len(rows)} kinetochore-quarters)")


if __name__ == "__main__":
    _tr = load_tracks()
    q1_vs_q4(_tr)
    quartile_profile(_tr)
