#!/usr/bin/env python3
"""Does EARLY prometaphase resemble triple-sisterless metaphase more closely than full prometaphase does?

USER 2026-08-10: "Something about filtering prometaphase points to only include points from the time at
least five minutes before metaphase onset (so early prometapahse) was a set of points that more closely
resembled the oscillation and amplitude of triple sisterless metaphase?"

NOTHING LIKE THIS WAS ON RECORD. Searched every builder, NOTES.md and PLOT_SETTINGS: no 5-minute filter, no
early-prometaphase split, and the prometaphase window everywhere is the whole of [NEB or first annotation,
Metaphase Start). So this is not a re-run of an earlier result -- it is the test itself, run now.

THE IDEA BEING TESTED. A single-sisterless cell approaching metaphase is progressively congressing, so the
minutes immediately before metaphase onset are the LEAST prometaphase-like part of prometaphase. Cutting
them away should leave behaviour that is more genuinely uncongressed -- and the question is whether that
looks more like a triple-sisterless cell held in metaphase, or less.

HOW. Exactly one thing changes: the prometaphase window's upper bound moves from Metaphase Start to
Metaphase Start - LEAD. Cohorts, pairing, per-kinetochore unit, paired-only filter and both metaphase
windows are the imported originals, so any difference is the lead time and nothing else. Several lead times
are swept (0 = the current definition, through 10 min) rather than just 5, because a claim that survives
only at one arbitrary cutoff is a claim about the cutoff.

READ-OUT. For each lead time: amplitude and period, and the distance from triple metaphase measured two
ways -- Cliff's delta (does the contrast shrink?) and the median ratio (do the central values converge?).
"Resembles more closely" means |delta| falls TOWARD 0 as the lead grows.
"""
import sys, os, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

import lib
import custom_prometa_vs_meta_20260810 as SRC
import custom_osc_metric_sensitivity_20260810 as SENS

OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group6"
os.makedirs(OUT, exist_ok=True)

LEADS_MIN = [0, 2, 5, 7.5, 10]
_orig_window = SRC.window


def make_window(lead_s):
    def w(b, mode):
        if mode != "prometa_early":
            return _orig_window(b, mode)
        r = _orig_window(b, "prometa")
        if r is None: return None
        lo, hi = r
        hi2 = hi - lead_s
        return (lo, hi2) if hi2 > lo else None
    return w


AMP = SRC.STATS["SD (current)"]
PER_CUR = SENS.PERIODS["zero-cross (current)"]
PER_DET = SENS.PERIODS["zero-cross detrended"]

# reference groups (unchanged)
M3_amp = [AMP(k["pos"], k["t"]) for k in SRC.kt_triple_meta]
M3_pc = [x for x in (PER_CUR(k["t"], k["pos"]) for k in SRC.kt_triple_meta) if x is not None]
M3_pd = [x for x in (PER_DET(k["t"], k["pos"]) for k in SRC.kt_triple_meta) if x is not None]
M1_amp = [AMP(k["pos"], k["t"]) for k in SRC.kt_single_meta]


def mw(a, b):
    return mannwhitneyu(a, b, alternative="two-sided").pvalue if len(a) >= 3 and len(b) >= 3 else float("nan")


rows = []
for lead in LEADS_MIN:
    SRC.window = make_window(lead * 60.0)
    try:
        kts, prs = SRC.collect("prometa_early", "1")
    finally:
        SRC.window = _orig_window
    if not kts:
        print(f"lead {lead}: no kinetochores left"); continue
    amp = [AMP(k["pos"], k["t"]) for k in kts]
    pc = [x for x in (PER_CUR(k["t"], k["pos"]) for k in kts) if x is not None]
    pd_ = [x for x in (PER_DET(k["t"], k["pos"]) for k in kts) if x is not None]
    row = dict(lead=lead, n_kt=len(kts), n_cell=len({k["cell"] for k in kts}),
               n_frames_med=float(np.median([len(k["pos"]) for k in kts])))
    for nm, v, ref in (("amplitude", amp, M3_amp), ("period (current)", pc, M3_pc),
                       ("period (detrended)", pd_, M3_pd)):
        row[nm] = dict(n=len(v),
                       med=float(np.median(v)) if v else float("nan"),
                       med_ref=float(np.median(ref)) if ref else float("nan"),
                       ratio=(float(np.median(v)) / float(np.median(ref))) if v and ref else float("nan"),
                       d=SRC.cliffs_delta(v, ref), p=mw(v, ref), vals=v)
    rows.append(row)

print("\n=================== EARLY PROMETAPHASE vs TRIPLE METAPHASE ===================")
print("lead = how much time before Metaphase Start is CUT from the prometaphase window")
print(f"{'lead':>6s} {'nKT':>4s} {'cells':>6s} {'frames':>7s}   " +
      "   ".join(f"{m:>26s}" for m in ("amplitude", "period (current)", "period (detrended)")))
print(f"{'':>6s} {'':>4s} {'':>6s} {'':>7s}   " + "   ".join(f"{'med  ratio   d      p':>26s}" for _ in range(3)))
for r in rows:
    line = f"{r['lead']:6.1f} {r['n_kt']:4d} {r['n_cell']:6d} {r['n_frames_med']:7.0f}   "
    line += "   ".join(f"{r[m]['med']:5.2f} {r[m]['ratio']:5.2f} {r[m]['d']:+6.2f} {r[m]['p']:7.3g}"
                       for m in ("amplitude", "period (current)", "period (detrended)"))
    print(line)

print("\n  reference (triple metaphase): "
      f"amplitude med={np.median(M3_amp):.2f}  period_cur med={np.median(M3_pc):.2f}  "
      f"period_det med={np.median(M3_pd):.2f}")
print("\nDoes cutting the pre-metaphase minutes move prometaphase TOWARD triple metaphase?")
for m in ("amplitude", "period (current)", "period (detrended)"):
    d0 = abs(rows[0][m]["d"])
    for r in rows[1:]:
        arrow = "closer" if abs(r[m]["d"]) < d0 - 1e-9 else ("further" if abs(r[m]["d"]) > d0 + 1e-9 else "same")
        print(f"   {m:20s} lead {r['lead']:4.1f} min: |d| {d0:.3f} -> {abs(r[m]['d']):.3f}  {arrow}"
              f"   (n {rows[0][m]['n']} -> {r[m]['n']})")

# ---- figure ---------------------------------------------------------------------------------------
fig, axs = plt.subplots(1, 3, figsize=(16.2, 5.4))
for ai, m in enumerate(("amplitude", "period (current)", "period (detrended)")):
    ax = axs[ai]
    x = [r["lead"] for r in rows]
    ax.plot(x, [abs(r[m]["d"]) for r in rows], "o-", color="#2a7fff", lw=2, ms=7)
    for r in rows:
        ax.annotate(f"n={r[m]['n']}", (r["lead"], abs(r[m]["d"])), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=7.5, color="#555")
    ax.axhline(0, color="#999", lw=.8, ls=":")
    ax.set_xlabel("minutes cut before Metaphase Start")
    ax.set_ylabel("|Cliff's delta| vs triple metaphase\n(0 = indistinguishable)")
    ax.set_title(m, fontsize=11, fontweight="bold")
    ax.grid(alpha=.3)
    ax.set_ylim(bottom=0)
fig.suptitle("Does EARLY prometaphase resemble triple-sisterless metaphase more closely?\n"
             "single-sisterless prometaphase, per kinetochore, paired KTs only — lower = more similar",
             fontweight="bold", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.9])
p = os.path.join(OUT, "G6_early_prometa_vs_triple_meta.png")
fig.savefig(p, dpi=200)
print(f"\nwrote {p}")

lib.record_plot("G6_early_prometa_vs_triple_meta",
                ["lead_min", "n_kt", "n_cells", "metric", "median_early_prometa", "median_triple_meta",
                 "ratio", "cliffs_delta", "mannwhitney_p"],
                [[r["lead"], r["n_kt"], r["n_cell"], m, round(r[m]["med"], 5), round(r[m]["med_ref"], 5),
                  round(r[m]["ratio"], 4), round(r[m]["d"], 4), r[m]["p"]]
                 for r in rows for m in ("amplitude", "period (current)", "period (detrended)")],
                {"kind": "lead-time sweep of the prometaphase window against triple metaphase",
                 "window": "prometaphase = [NEB or first annotation, Metaphase Start - lead)",
                 "unit": "one point per KINETOCHORE, paired only",
                 "note": "lead 0 = the current prometaphase definition"},
                __file__,
                "Cutting the last N minutes before metaphase onset from the prometaphase window, and asking "
                "whether what remains is more similar to triple-sisterless metaphase.",
                key_column=None)
