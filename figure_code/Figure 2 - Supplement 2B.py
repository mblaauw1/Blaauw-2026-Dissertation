#!/usr/bin/env python3
"""EARLY vs LATE metaphase ablation (user 2026-08-04, priority request).

Some metaphase batches record "early metaphase" / "mid metaphase" / "late metaphase" in `Metaphase Start (s)`
instead of a timestamp. Those were unusable by every builder that parses that column as a time, so they were
silently dropped from metaphase plotting. Her instruction: RESCUE them and bin by ablation timing.

BINNING
  * text "early metaphase" or "mid metaphase"  -> EARLY   (she said put mid in the early bin)
  * text "late metaphase"                      -> LATE
  * numeric metaphase start -> fraction of that cell's own metaphase already elapsed at the ablation:
        frac = |Metaphase Start| / (Anaphase Onset - Metaphase Start)
        frac < 0.5 -> EARLY,  frac >= 0.5 -> LATE
    (for a metaphase ablation the clock is ablation-anchored: Metaphase Start is NEGATIVE because metaphase
     began before the ablation, Anaphase Onset is positive. A negative value is the NORM here and is not a
     reason to exclude — 17 of these batches carry one.)

WHAT IS PLOTTED
  Remaining metaphase after the ablation (abl->anaphase = Anaphase Onset) is the primary readout, because it
  is computable for EVERY batch including the rescued ones, which have no numeric metaphase start. Total
  metaphase duration is shown alongside for the subset where it is computable.
"""
import sys, re, os; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats
import lib
lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
data, HDR = lib.load_master()
def g(r, c): return (r.get(c, "") or "").strip()
def psec(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); v = lib.parse_time(s.lstrip("-"))
    return None if v is None else (-v if neg else v)

TXT = re.compile(r"\b(early|mid|late)\s*metaphase\b", re.I)
# She flagged one cell reclassified metaphase -> PROMETAPHASE; its Phase column already says prometaphase,
# so the phase filter below drops it. Named here so the exclusion is visible rather than incidental.
RECLASSIFIED_TO_PROMETA = "20260303_extra2 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_35"

rows = []; skipped = []
for r in data:
    b = r["Batch Name"]
    if not g(r, "Phase of Ablations").lower().startswith("metaph"):
        continue                                   # includes the reclassified prometaphase cell
    if g(r, "Exclude") in ("Yes", "yes"):
        skipped.append((b, "master Exclude=Yes")); continue
    if lib.is_mad1(b) and False: pass              # Mad1 cells are kept: these ARE the rescued batches
    ao = psec(g(r, "Anaphase Onset (s)"))
    if ao is None or ao <= 0:
        skipped.append((b, "no anaphase onset")); continue
    ms_raw = g(r, "Metaphase Start (s)")
    m = TXT.search(ms_raw)
    if m:
        word = m.group(1).lower()
        if "anaphase" in ms_raw.lower() and word != "late":
            skipped.append((b, f"text says '{ms_raw}' — not a metaphase ablation")); continue
        binn = "LATE" if word == "late" else "EARLY"     # early + mid -> EARLY
        frac = None; dur = None; src = f"text: '{ms_raw}'"
    else:
        ms = psec(ms_raw)
        if ms is None:
            skipped.append((b, "no metaphase start and no early/late label")); continue
        dur = (ao - ms) / 60.0
        if dur <= 0:
            skipped.append((b, "non-positive metaphase duration")); continue
        frac = abs(ms) / (ao - ms)                       # how far through metaphase the ablation happened
        binn = "EARLY" if frac < 0.5 else "LATE"
        src = f"frac={frac:.2f}"
    rows.append(dict(batch=b, bin=binn, remaining=ao / 60.0, dur=dur, frac=frac, src=src,
                     sis=g(r, "# Sisterless KTs")))

E = [x for x in rows if x["bin"] == "EARLY"]; L = [x for x in rows if x["bin"] == "LATE"]
resc = [x for x in rows if x["frac"] is None]
print(f"EARLY n={len(E)}   LATE n={len(L)}   (rescued text-labelled: {len(resc)})")
for x in resc: print(f"   rescued {x['batch'][:52]:52s} -> {x['bin']}  ({x['src']})")
print(f"skipped {len(skipped)}:")
for b, why in skipped[:12]: print(f"   {b[:52]:52s} {why}")

COL = {"EARLY": "#2166ac", "LATE": "#b2182b"}
fig, axs = plt.subplots(1, 2, figsize=(12, 5.4))
def panel(ax, key, ylab, title):
    a = [x[key] for x in E if x[key] is not None]; b = [x[key] for x in L if x[key] is not None]
    p = None
    for i, (v, k) in enumerate(((a, "EARLY"), (b, "LATE"))):
        if not v: continue
        ax.boxplot([v], positions=[i], widths=.55, showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor=COL[k], alpha=.30, color=COL[k]),
                   medianprops=dict(color=COL[k], lw=2.2))
        jit = (np.random.RandomState(i).rand(len(v)) - .5) * .22
        ax.scatter(np.full(len(v), i) + jit, v, s=42, color=COL[k], alpha=.85, edgecolor="white", lw=.5)
        ax.text(i, max(v) * 1.02, f"med {np.median(v):.1f}\nn={len(v)}", ha="center", va="bottom", fontsize=8.5)
    ax.set_ylim(top=max([x for v_,_k in ((a,"E"),(b,"L")) for x in v_] or [1]) * 1.22)
    if len(a) >= 3 and len(b) >= 3:
        p = float(stats.mannwhitneyu(a, b, alternative="two-sided")[1])
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"EARLY metaphase\nablation (n={len(a)})",
                                               f"LATE metaphase\nablation (n={len(b)})"])
    ax.set_ylabel(ylab)
    ax.set_title(title + (f"   Mann-Whitney p={p:.3g}" if p is not None else "   (n too small)"),
                 loc="left", fontweight="bold", fontsize=9.5)
    return p
p1 = panel(axs[0], "remaining", "Metaphase remaining after the ablation (min)",
           "Time LEFT after the ablation")
p2 = panel(axs[1], "dur", "Total metaphase duration (min)", "Total metaphase duration")
fig.suptitle("EARLY vs LATE metaphase ablation — including the RESCUED batches labelled "
             "'early/mid/late metaphase'\n"
             f"{len(resc)} rescued cells had a text label instead of a timestamp and were previously dropped by "
             "every builder that parses that column as a time.\n"
             "Binning: text early/mid -> EARLY, late -> LATE; numeric -> ablation before/after the halfway point "
             "of that cell's own metaphase. Negative metaphase starts are normal here (ablation-anchored clock) "
             "and are NOT excluded.",
             x=.01, ha="left", fontweight="bold", fontsize=8.5)
plt.tight_layout()
fig.savefig(f"{OUT}/G2_metaphase_early_vs_late_ablation.png", bbox_inches="tight", dpi=150)
plt.close(fig)
lib.record_plot("G2_metaphase_early_vs_late_ablation",
                ["batch", "bin", "remaining_min", "total_duration_min", "frac_of_metaphase_at_ablation", "source", "n_sisterless"],
                [[x["batch"], x["bin"], round(x["remaining"], 3),
                  round(x["dur"], 3) if x["dur"] is not None else "",
                  round(x["frac"], 4) if x["frac"] is not None else "", x["src"], x["sis"]] for x in rows],
                {"binning": "text early/mid->EARLY, late->LATE; numeric frac<0.5->EARLY else LATE",
                 "rescued_text_labelled": len(resc),
                 "reclassified_to_prometaphase_excluded": RECLASSIFIED_TO_PROMETA,
                 "negative_metaphase_start": "normal on the ablation-anchored clock; not an exclusion reason",
                 "p_remaining": p1, "p_total_duration": p2,
                 "y_label": "Metaphase remaining after ablation (min) / total duration (min)"},
                SCRIPT, "Early vs late metaphase ablation, including rescued text-labelled batches")
print(f"remaining p={p1}   total-duration p={p2}")
