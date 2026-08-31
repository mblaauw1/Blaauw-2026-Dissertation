"""Congression timing questions — user feedback 2026-08-04, her item 13.

FB13a — "in the 3-sisterless population, the congression of kinetochores to the plate appears even over
    time. Are the ones to congress later longer than the ones that congress quickly?"
    -> length vs congression time, WITHIN each ablation number (not pooled: pooling 1- and 3-sisterless
       mixes two different chromosome populations and can manufacture a trend that neither group has).

FB13b — her argument, in her words: triple-ablation cells shrink over metaphase and the kinetochores end up
    closer to the plate, so the RATE of congression should rise as metaphase progresses, yet the plot looks
    flat. And: "because there are less kinetochores to congress as metaphase progresses in triple ablation
    cells and yet the same number of congressions happen per period of time (roughly), that in itself is
    increasing the rate of congression."

    She is right, and it is worth being precise about why. A COUNT of congressions per time bin is not a
    rate — it has no denominator. The quantity that answers her question is the HAZARD: in each bin,

        congressions in the bin  /  kinetochores still un-congressed at the start of the bin

    If the count stays flat while the at-risk pool shrinks, the hazard rises by construction. That is the
    real per-kinetochore rate, and it is what this figure plots. Kinetochores that never congress stay in
    the at-risk pool for the whole of metaphase, so they correctly hold the denominator up.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import scipy.stats as st
import lib

SCRIPT = __file__
ROOT = "/Volumes/4 MB"
OUT = "/Volumes/4 MB/ablation_figures_20260625/new_figures_20260804"
os.makedirs(OUT, exist_ok=True)
lib.apply_style()

master, _ = lib.load_master_plots(); MR = {r["Batch Name"]: r for r in master}
def gv(b, c): return str((MR.get(b, {}) or {}).get(c, "") or "").strip()
def sis(b): return gv(b, "# Sisterless KTs")
def cohort_ok(b): return (not lib.plot_excluded(b)) and (not lib.is_mad1(b))

COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}

SRC = f"{ROOT}/ablation_plots/data/G3_length_vs_congression_time.csv"
if not os.path.exists(SRC):
    raise SystemExit(f"missing {SRC} — run the builder that produces G3_length_vs_congression_time first")

REC = []
for r in csv.DictReader(open(SRC)):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    b = (r.get("batch") or "").strip()
    if not b or not cohort_ok(b): continue
    g = (r.get("n_sisterless") or "").strip() or sis(b)
    if g not in ("1", "3"): continue
    try:
        REC.append({"batch": b, "g": g, "length": float(r["length_um"]),
                    "t": float(r["t_to_congress_min"]), "frac": float(r["frac_meta_to_ana"])})
    except Exception:
        continue
print(f"congression records: {len(REC)}  (1-sis {sum(1 for x in REC if x['g']=='1')}, "
      f"3-sis {sum(1 for x in REC if x['g']=='3')})")


# ── FB13a: are the late congressers longer? ───────────────────────────────────────────────────────
def fb13a_length_vs_timing():
    fig, axs = plt.subplots(1, 2, figsize=(11.6, 5.0), sharey=True)
    rows, notes = [], []
    for ax, xk, xlab in ((axs[0], "t", "Time to congression (min after metaphase onset)"),
                         (axs[1], "frac", "Congression time as metaphase progress (0-1)")):
        for g in ("1", "3"):
            sel = [x for x in REC if x["g"] == g]
            if not sel: continue
            X = np.array([x[xk] for x in sel]); Y = np.array([x["length"] for x in sel])
            ax.scatter(X, Y, s=34, color=COL[g], alpha=.85, edgecolor="white", lw=.4, zorder=3,
                       label=f"{lib.lbl(g+'-Sister')} (n={len(sel)})")
            if len(X) >= 5:
                rho, p = st.spearmanr(X, Y)
                if xk == "t":
                    notes.append(f"{g}-sisterless: length vs congression time rho={rho:+.2f}, p={p:.3g}, n={len(X)}")
                # per-group trend line, drawn only where that group has data
                m, c = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 40)
                ax.plot(xr, m * xr + c, "--", color=COL[g], lw=1.8, zorder=4)
            rows += [[x["batch"], g, round(x["length"], 4), round(x["t"], 4), round(x["frac"], 4)]
                     for x in sel]
        ax.set_xlabel(xlab)
    axs[0].set_ylabel("Chromosome length (µm)")
    axs[0].legend(fontsize=8)
    fig.suptitle("Are the kinetochores that congress LATER longer?  (user 2026-08-04)\n"
                 + "   |   ".join(notes),
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    axs[0].text(0.0, -0.155,
                "Tested WITHIN each ablation number rather than pooled: 1- and 3-sisterless cells contribute "
                "different chromosome populations, and a\npooled correlation can appear where neither group "
                "has one. Dashed lines are per-group linear fits, drawn only over that group's range.",
                transform=axs[0].transAxes, fontsize=6.7, color="#555", va="top", linespacing=1.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G3_length_vs_congression_timing_by_group.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G3_length_vs_congression_timing_by_group",
                    ["batch", "n_sisterless", "length_um", "t_to_congress_min", "frac_meta_to_ana"], rows,
                    {"fb13a": "length vs congression timing, within group",
                     "note": "per-group Spearman; pooled correlation deliberately not used"},
                    SCRIPT, "Chromosome length vs congression timing, by ablation number", key_column="batch")
    for n in notes: print("   FB13a " + n)


# ── FB13b: congression HAZARD across metaphase ────────────────────────────────────────────────────
NBINS = 5
MIN_EVENTS_FOR_TREND = 15   # below this a 5-bin hazard curve is monotone by construction, not by biology

def fb13b_hazard():
    """Count vs hazard, side by side, so the difference between them is visible rather than asserted."""
    bins = np.linspace(0, 1, NBINS + 1)
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 5.0))
    rows, msg = [], []
    for g in ("1", "3"):
        cells = sorted({x["batch"] for x in REC if x["g"] == g})
        if not cells: continue
        # at-risk pool: every sisterless KT in the cell, congressed or not
        n_total = 0; events = []
        for b in cells:
            try: n_kt = int(sis(b))
            except Exception: n_kt = len([x for x in REC if x["batch"] == b])
            n_kt = max(n_kt, len([x for x in REC if x["batch"] == b]))
            n_total += n_kt
            events += [x["frac"] for x in REC if x["batch"] == b]
        events = [e for e in events if 0.0 <= e <= 1.0]
        counts, _ = np.histogram(events, bins=bins)
        at_risk = []; remaining = n_total
        for c in counts:
            at_risk.append(remaining); remaining -= c
        haz = [c / a if a > 0 else np.nan for c, a in zip(counts, at_risk)]
        ctr = (bins[:-1] + bins[1:]) / 2
        axs[0].plot(ctr, counts, "-o", color=COL[g], lw=2.4, ms=6,
                    label=f"{lib.lbl(g+'-Sister')} ({n_total} KTs, {len(events)} congressions)")
        axs[1].plot(ctr, haz, "-o", color=COL[g], lw=2.4, ms=6, label=lib.lbl(g + "-Sister"))
        rows += [[g, round(float(a), 3), round(float(b2), 3), int(c), int(a_), (round(float(h), 5) if h == h else "")]
                 for a, b2, c, a_, h in zip(bins[:-1], bins[1:], counts, at_risk, haz)]
        ok = [(x, y) for x, y in zip(ctr, haz) if y == y]
        # A hazard curve built from a handful of events is not interpretable: with few congressions spread
        # over 5 bins the curve is near-monotone by construction and Spearman returns rho=1 with an absurd
        # p-value. Require enough events before quoting a trend at all (2026-08-04).
        if len(events) < MIN_EVENTS_FOR_TREND:
            msg.append(f"{g}-sis: only {len(events)} congressions across {n_total} KTs — too few to read a "
                       f"hazard trend from {NBINS} bins")
        elif len(ok) >= 4:
            rho, p = st.spearmanr([o[0] for o in ok], [o[1] for o in ok])
            msg.append(f"{g}-sis hazard across metaphase: rho={rho:+.2f}, p={p:.3g} "
                       f"({haz[0]:.2f} in the first bin -> {[h for h in haz if h==h][-1]:.2f} in the last)")
    axs[0].set_xlabel("Fraction of metaphase elapsed")
    axs[0].set_ylabel("Congressions per bin  (a COUNT — no denominator)")
    axs[0].set_title("What the original plot shows: a count", loc="left", fontweight="bold", fontsize=9.5)
    axs[0].legend(fontsize=8)
    axs[1].set_xlabel("Fraction of metaphase elapsed")
    axs[1].set_ylabel("Congression hazard  (congressions ÷ KTs still un-congressed)")
    axs[1].set_title("The actual per-kinetochore rate: a hazard", loc="left", fontweight="bold", fontsize=9.5)
    axs[1].legend(fontsize=8)
    fig.suptitle("Does the congression RATE rise as metaphase progresses?  (user 2026-08-04)\n"
                 + "   |   ".join(msg),
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    axs[0].text(0.0, -0.165,
                "Her reasoning, made explicit: a flat COUNT does not mean a flat rate. The pool of "
                "un-congressed kinetochores shrinks every time one\ncongresses, so holding the count steady "
                "while the denominator falls IS a rising per-kinetochore rate. The right panel divides by "
                "that\nshrinking pool. Kinetochores that never congress stay in the denominator for the whole "
                "of metaphase, so they are not silently dropped.",
                transform=axs[0].transAxes, fontsize=6.7, color="#555", va="top", linespacing=1.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G3_congression_hazard_over_metaphase.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G3_congression_hazard_over_metaphase",
                    ["n_sisterless", "bin_lo", "bin_hi", "n_congressions", "n_at_risk", "hazard"], rows,
                    {"fb13b": "congression count vs per-kinetochore hazard across metaphase",
                     "hazard": "congressions in bin / KTs still un-congressed at the start of the bin",
                     "n_bins": NBINS},
                    SCRIPT, "Congression hazard across metaphase, single vs triple", key_column="n_sisterless")
    for m in msg: print("   FB13b " + m)


# ── FB13d: she asked whether the anaphase pole-speed plot already exists ──────────────────────────
def fb13d_check():
    p = f"{ROOT}/ablation_plots/data/G6_anaphase_kt_speed_single_vs_triple.csv"
    if not os.path.exists(p):
        print("   FB13d: G6_anaphase_kt_speed_single_vs_triple NOT found — needs building"); return
    v = collections.defaultdict(list)
    for r in csv.DictReader(open(p)):
        if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
        try: v[(r.get("n_sisterless") or "").strip()].append(float(r["median_speed_um_per_min"]))
        except Exception: pass
    a, c = v.get("1", []), v.get("3", [])
    if len(a) >= 3 and len(c) >= 3:
        pv = float(st.mannwhitneyu(a, c, alternative="two-sided")[1])
        print(f"   FB13d: ALREADY BUILT as G6_anaphase_kt_speed_single_vs_triple — "
              f"1-sis median {np.median(a):.2f} um/min (n={len(a)}) vs 3-sis {np.median(c):.2f} um/min "
              f"(n={len(c)}), Mann-Whitney p={pv:.3g}")
    else:
        print(f"   FB13d: plot exists but is thin (n={len(a)}/{len(c)})")


if __name__ == "__main__":
    fb13a_length_vs_timing()
    fb13b_hazard()
    fb13d_check()
    print("congression dynamics: done")
