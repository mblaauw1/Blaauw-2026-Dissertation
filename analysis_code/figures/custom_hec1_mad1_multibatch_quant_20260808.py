"""Hec1 / Mad1 at kinetochores — ALL batches with the corrected readout, not just one.

USER 2026-08-08: "we recently did a lot of work on the hec1/mad1 files to get better readouts across
multiple of those batches (maybe 2 or three if i remember correctly?) so update the plot for that ... so it
includes the updated data nd not just from one group but from the multiple groups"

The corrected readout is `G5_hec1_mad1_TRUE_quant.csv` (built 2026-08-06 by `_claude_tmp/quant_true_20260806.py`
after the flat-page-offset and z-major page-order bugs were fixed). It spans **xy2 + xy5**, 308 rows,
6 timepoints, both channels — whereas the existing figure `G5_hec1_mad1_dot_quant` is fed by a single
batch, and the older `G5_hec1_mad1_final_quant` / `_zslice_quant` are single-batch too.

Of the three Hec1/Mad1 batches, **xy8 carries only cytosol_bg marks and no paired_kt**, so it cannot
contribute a kinetochore measurement — "2 or three" resolves to **two** measurable batches.

DELIBERATELY A NEW PLOT ID. NOTES §8 records that two scripts writing the same plot_id silently fight and
the last one wins, and that the fix is to remove the superseded write rather than to rely on ordering.
Retiring the single-batch write inside `group5_hec1_timestrip.py` is a separate, reversible step; until
then this stands alongside it and is the one to place on META.

Metric: `fold_over_her_bg` — her own cytosol background on the same z-slice, as recorded by the corrected
quantification. No anaphase frames are involved (the 6 timepoints are pre-anaphase).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()

SRC = "/Volumes/4 MB/ablation_plots/data/G5_hec1_mad1_TRUE_quant.csv"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group5"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G5_hec1_mad1_multibatch_quant"
SCRIPT = __file__

rows = list(csv.DictReader(open(SRC, newline="", encoding="utf-8", errors="replace")))
print(f"{len(rows)} rows from {SRC}")


def f(v):
    try:
        return float(v)
    except Exception:
        return None


bybatch = collections.Counter(r["batch"] for r in rows)
print("  batches:", dict(bybatch))

# per (batch, channel, timepoint)
groups = collections.defaultdict(list)
for r in rows:
    v = f(r.get("fold_over_her_bg"))
    if v is None:
        continue
    groups[(r["batch"], r["channel"], r["t_mmss"])].append(v)

tps = sorted({k[2] for k in groups}, key=lambda s: [int(x) for x in s.split(":")])
batches = sorted({k[0] for k in groups})
CH = {"mad1": "#d62728", "hec1": "#1f77b4"}
MK = {"xy2": "o", "xy5": "^"}
print(f"  timepoints: {tps}")

fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.6, 5.0), width_ratios=[1.5, 1])

# --- A: fold-over-background vs time, per batch and channel
for b in batches:
    for ch, c in CH.items():
        xs, ys, es = [], [], []
        for i, tp in enumerate(tps):
            v = groups.get((b, ch, tp), [])
            if v:
                xs.append(i); ys.append(np.mean(v)); es.append(np.std(v) / max(np.sqrt(len(v)), 1))
        if xs:
            axA.errorbar(xs, ys, yerr=es, marker=MK.get(b, "s"), color=c, lw=1.6, capsize=3,
                         label=f"{ch} — {b}", alpha=.9)
axA.axhline(1.0, color="#888", ls="--", lw=1)
axA.set_xticks(range(len(tps))); axA.set_xticklabels(tps)
axA.set_xlabel("timepoint (mm:ss)")
axA.set_ylabel("fold over her cytosol background")
axA.set_title("Hec1 / Mad1 at kinetochores — both batches", fontsize=10)
axA.legend(frameon=False, fontsize=8, ncol=2)

# --- B: the two channels pooled across batches, per timepoint
w = .36
for j, (ch, c) in enumerate(CH.items()):
    pos, vals = [], []
    for i, tp in enumerate(tps):
        v = [x for b in batches for x in groups.get((b, ch, tp), [])]
        if v:
            pos.append(i + (j - .5) * w); vals.append(v)
    if vals:
        bp = axB.boxplot(vals, positions=pos, widths=w * .85, patch_artist=True, showfliers=False,
                         medianprops=dict(color="k", lw=1.2))
        for patch in bp["boxes"]:
            patch.set_facecolor(c); patch.set_alpha(.38); patch.set_edgecolor("k")
        for p, v in zip(pos, vals):
            axB.scatter(np.full(len(v), p), v, s=13, c=c, edgecolor="k", lw=.3, zorder=3)
axB.axhline(1.0, color="#888", ls="--", lw=1)
axB.set_xticks(range(len(tps))); axB.set_xticklabels(tps, fontsize=8)
axB.set_xlabel("timepoint (mm:ss)")
axB.set_ylabel("fold over background")
axB.set_title("both batches pooled", fontsize=10)
axB.plot([], [], color=CH["mad1"], lw=6, alpha=.4, label="mad1")
axB.plot([], [], color=CH["hec1"], lw=6, alpha=.4, label="hec1")
axB.legend(frameon=False, fontsize=8)

fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200); plt.close(fig)
print("wrote", png)

out = [[r["batch"], r["channel"], r["t_mmss"], r.get("t_sec", ""), r.get("z_from_hec1", ""),
        r.get("value_au", ""), r.get("her_cytosol_bg_same_slice", ""), r.get("fold_over_her_bg", "")]
       for r in rows]
lib.record_plot(
    PLOT_ID,
    ["batch", "channel", "t_mmss", "t_sec", "z_from_hec1", "value_au", "cytosol_bg_au", "fold_over_bg"],
    out,
    {"kind": "timeseries+box", "metric": "fold over her cytosol background", "batches": batches},
    script=SCRIPT,
    caption=("Hec1 and Mad1 at her kinetochore marks across BOTH measurable batches (xy2 and xy5), from "
             "the corrected quantification G5_hec1_mad1_TRUE_quant.csv. xy8 has only background marks and "
             "no paired_kt, so it contributes no kinetochore measurement. Fold is over her own cytosol "
             "background on the same z-slice. Supersedes the single-batch G5_hec1_mad1_dot_quant."),
    source=[SRC, "/Volumes/4 MB/annotations/kt_points.csv"],
    key_column="batch",
    fig=png,
)
print("recorded", PLOT_ID)
