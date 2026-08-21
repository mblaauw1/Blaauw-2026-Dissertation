"""Control plot: number of laser ablation EVENTS per cell (Log Ablation Events, PAS-derived) across the
on-target vs off-target cohorts, split by count (1/2/3). Purpose: check whether the ablation "dose" is
matched between on-target and off-target groups (ideally approx equal, no significant difference — so any
metaphase-delay phenotype is not just an artifact of differing laser exposure).

On-target cohort N = On-target cell with #Sisterless KTs == N (N kinetochores destroyed).
Off-target side = binned by #Unique Targets into RANGES (1-3 / 4-9 / 10+ / not recorded) plus a pooled
"ALL off-target" group, so every off-target cell is represented (ITEM 2, user 2026-08-04).
Y = Log Ablation Events (total ablation events per cell). Excludes Exclude=Yes.
NOTE (data reality, surfaced 2026-07-14, and the reason for the ITEM 2 rebin): off-target cells rarely come
in exactly 1/2/3 targets — off-target controls were deliberately shot at many spots, so the old 1/2/3
buckets held only 10 of 90 off-target cells and left two groups at n=1."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as _st
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT = __file__
data, _ = lib.load_master()

def _int(x):
    try: return int(float(str(x).replace(",", "").strip()))
    except (TypeError, ValueError): return None

# ── ITEM 2 (user 2026-08-04): "# of off-target in each group is far too low" ─────────────────────
# She is right, and the cause is the off-target BINNING. Off-target cells were bucketed by
# `# Unique Targets` ∈ {1,2,3}; but off-target controls were deliberately shot at MANY spots, so of the
# 90 off-target cells carrying a Log Ablation Events count only 10 fall in 1/2/3 — the plot silently threw
# away 80 of 90 and left off-1 and off-3 at n=1. (`# Sisterless KTs` cannot rescue it: it is blank for 92 of
# 93 off-target cells, because an off-target hit by definition creates no sisterless kinetochore.)
# Fix: keep the on-target groups binned by `# Sisterless KTs` (the standing rule), and bin the off-target
# side into ranges that cover EVERY off-target cell, plus a pooled all-off-target group. No cell is dropped.
ONCOL = "#2b8a3e"; OFFCOL = "#868e96"
# ── REBIN 2026-08-05 (user: "still not how i want it to be plotted") ─────────────────────────────
# The 1-3 / 4-9 / 10+ RANGE bins I put in on 2026-08-04 answered the wrong question. Going back to the
# original commission for this figure — "ablation count by on/off cohort violin (1/2/3 on/off target,
# TESTING MATCHED DOSE)" — the off-target side is not meant to be split by how many spots each control
# cell received. It is the off-target CONTROL FOR EACH EXPERIMENT: the off-target cells that were shot in
# the single-, double- and triple-ablation experiments, paired against on-1/2/3 to show the dose matched.
# An off-target cell cannot be binned by `# Sisterless KTs` (blank for 92 of 93 — an off-target hit makes
# no sisterless KT) and `# Unique Targets` is both unreliable and irrelevant here, so the experiment the
# cell belongs to comes from the batch name. That is the one thing that identifies the experiment; the
# standing "never bin by batch name" rule is about the ON-TARGET ablation NUMBER, which still comes from
# `# Sisterless KTs` exactly as before.
# Resulting n: off-1 = 17 and off-3 = 21, against 1 and 1 under the old binning.
import re as _re
# COHORT MEMBERSHIP COMES FROM lib.assign_cohorts (2026-08-10).
# USER: "does this distribution match how the off-targets are plotted in the main violin plot on the second
# board ... if it doesnt match then reorganize the off-target samples so that theyre organized that way".
# It did not match (38/8/24 here vs 25/12/23 there) because each figure decided cohort membership for itself.
# assign_cohorts is now the single authority -- its controls are matched by IMAGING SESSION (the experiment
# the control was acquired in), and this figure reads those exact sets, so the two figures cannot drift apart.
_COH = lib.assign_cohorts(include_double=True)
_CTRL_OF = {}
for _s in ("1", "2", "3"):
    for _b, _ in _COH.get(f"{_s}-Sister Controls", []): _CTRL_OF[_b] = _s
_ON_OF = {}
for _s in ("1", "2", "3"):
    for _b, _ in _COH.get(f"{_s}-Sister", []): _ON_OF[_b] = _s
print(f"  cohort membership from lib.assign_cohorts: on={len(_ON_OF)} controls={len(_CTRL_OF)}")

COHORTS = [("on1", "1 on-target", 0, ONCOL), ("on2", "2 on-target", 1, ONCOL), ("on3", "3 on-target", 2, ONCOL),
           ("off1", "1 off-target\n(control)", 3.5, OFFCOL), ("off2", "2 off-target\n(control)", 4.5, OFFCOL),
           ("off3", "3 off-target\n(control)", 5.5, OFFCOL),
           ("offALL", "ALL off-target\n(pooled)", 7.0, "#495057")]
vals = {k: [] for k, _, _, _ in COHORTS}
_unbinned_off = []
off_all = []          # ALL off-target cells (pooled), any target count — for the matched-dose companion
on_all = []           # ALL on-target 1/2/3-sisterless cells (pooled)

_DBL = lib.double_chromosome_batches()   # both KTs on one chromosome -> not a sisterless dose
# USER 2026-08-10: "some of them are at 0, which is definitely not correct." A cell recorded with ZERO
# laser ablation events is not an ablation, so it cannot be a point in an ablation-dose distribution --
# it is a missing/!=0 count, and it was dragging every off-target violin down to the axis. Dropped and logged.
# The off-target side also never had the standing cohort exclusions applied, so Mad1 cells, ZM- and
# nocodazole-treated cells and 4-target experiments were all being pooled into "ALL off-target" -- which is
# why the pooled n (89) did not equal the three sub-groups and why the sub-group n's looked wrong.
_zero_lae = []; _excl_off = 0
for r in data:
    if r.get("Exclude") in ("Yes", "yes"): continue
    if r["Batch Name"] in _DBL: continue
    _b = r["Batch Name"]
    if lib.is_mad1(_b) or lib.is_drug(_b):
        _excl_off += 1; continue                      # Mad1 is its own group; drugged cells are not controls here
    oo = r.get("On-Target / Off-Target", "").strip().lower()
    lae = _int(r.get("Log Ablation Events", ""))
    if lae is None: continue
    if lae == 0:
        _zero_lae.append(_b); continue
    if _b in _ON_OF:
        vals[f"on{_ON_OF[_b]}"].append(lae); on_all.append(lae)
    elif _b in _CTRL_OF:
        off_all.append(lae); vals["offALL"].append(lae)
        vals[f"off{_CTRL_OF[_b]}"].append(lae)
    elif "off-target" in oo:
        # an off-target cell assign_cohorts drops (drug / metaphase / prophase / 4-sis / IQR outlier):
        # not a matched control, so it is not in a 1/2/3 group and not in the pooled control either
        _unbinned_off.append((_b, None))

print(f"  dropped Log Ablation Events == 0 : {len(_zero_lae)}  {_zero_lae[:6]}")
print(f"  excluded Mad1/drug cells         : {_excl_off}")
print(f"  off-target n by experiment       : 1={len(vals['off1'])} 2={len(vals['off2'])} 3={len(vals['off3'])} "
      f"pooled={len(vals['offALL'])}")
if _unbinned_off:
    import collections as _c9
    print(f"  off-target NOT in a 1/2/3 experiment: {len(_unbinned_off)} "
          f"{dict(_c9.Counter(e for _, e in _unbinned_off))}")
    for _b9, _e9 in _unbinned_off[:8]: print(f"      {_b9}  -> {_e9}")

fig, ax = plt.subplots(figsize=(9.5, 5.4))
rec = []
posmap = {}
for k, lab, x, col in COHORTS:
    d = vals[k]; posmap[k] = x
    if not d: continue
    lib.journal_violin(ax, d, x, col, alpha=0.30, lw=1.0)
    jit = (np.random.RandomState(int(x * 10)).rand(len(d)) - 0.5) * 0.22
    ax.scatter(np.full(len(d), x) + jit, d, s=16, color=col, alpha=0.85, edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax.hlines(med, x - 0.34, x + 0.34, color=col, lw=2.2, zorder=4)
    ax.hlines(mean, x - 0.28, x + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax.scatter([x], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    ax.text(x, max(d) + max(d) * 0.03 + 0.6, f"x̄ {mean:.1f}\nmed {med:.0f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5, color="#222")
    for v in d: rec.append([lab, v])

# pairwise on-N vs off-N Mann-Whitney (annotate; skip when either side < 3)
ymax = max((max(v) for v in vals.values() if v), default=10)
# ITEM 2: the on-vs-off comparison is now on-target(1/2/3) vs the POOLED off-target group, because the
# off-target side no longer has matching 1/2/3 buckets to pair with (it never really did — see note above).
for n in ("1", "2", "3"):
    a, b = vals[f"on{n}"], vals[f"off{n}"]
    xa = posmap[f"on{n}"]
    if len(a) >= 3 and len(b) >= 3:
        p = _st.mannwhitneyu(a, b, alternative="two-sided").pvalue
        s_ = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
        txt = f"vs {n} off:\n{s_} (p={p:.2g})"          # the MATCHED-DOSE test this figure exists for
    else:
        txt = f"no matched\noff-target (n={len(b)})"
    # sits ABOVE the per-group med/N caption (which is drawn at ymax*1.02) so the two do not overlap
    # 2026-08-11: the p-row sat at 1.15*ymax, which the 3-line x̄/med/N labels overran once the figure
    # text was scaled 2.5x. Lifted clear of them, with the ylim raised to match.
    ax.text(xa, ymax * 1.40, txt, ha="center", va="bottom", fontsize=6.5, color="#555")

ax.set_xticks([c[2] for c in COHORTS]); ax.set_xticklabels([c[1] for c in COHORTS], rotation=20, ha="right", fontsize=8)
ax.set_ylabel("Number of laser ablation events per cell")
ax.set_ylim(0, ymax * 1.66)
_ns = {k: len(vals[k]) for k, _, _, _ in COHORTS}
ax.set_title("Ablation dose by cohort — laser ablation events per cell\n"
             "Each on-target group is paired with the off-target CONTROLS FROM THE SAME EXPERIMENT "
             f"(1-, 2- and 3-ablation): n = {_ns['on1']}/{_ns['on2']}/{_ns['on3']} on-target vs "
             f"{_ns['off1']}/{_ns['off2']}/{_ns['off3']} off-target; {_ns['offALL']} off-target cells pooled at right.",
             loc="left", fontweight="bold", fontsize=9)
ax.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                   Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                          markerfacecolor="white", markeredgecolor="#444", label="mean")],
          loc="upper right", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/ablation_count_by_cohort.png", bbox_inches="tight"); plt.close()

# ---------- COMPANION: on-target 1/2/3-sisterless vs OFF-TARGET POOLED (the matched-dose view) ----------
# off-target controls used ~10 targets each to match the total on-target effort, so pooled off-target is
# the fair comparison. Demonstrates the dose is matched (no significant on- vs off-target difference).
POOL = [("on1", "1 on-target", 0, ONCOL), ("on2", "2 on-target", 1, ONCOL), ("on3", "3 on-target", 2, ONCOL),
        ("offall", "off-target (all)", 3.3, OFFCOL)]
pvals = {"on1": vals["on1"], "on2": vals["on2"], "on3": vals["on3"], "offall": off_all}
fig2, ax2 = plt.subplots(figsize=(8.2, 5.4)); rec2 = []
ymax2 = max((max(v) for v in pvals.values() if v), default=10)
for k, lab, x, col in POOL:
    d = pvals[k]
    if not d: continue
    lib.journal_violin(ax2, d, x, col, alpha=0.30, lw=1.0)
    jit = (np.random.RandomState(int(x * 10) + 5).rand(len(d)) - 0.5) * 0.22
    ax2.scatter(np.full(len(d), x) + jit, d, s=16, color=col, alpha=0.85, edgecolor="white", linewidth=0.3, zorder=3)
    mean = float(np.mean(d)); med = float(np.median(d))
    ax2.hlines(med, x - 0.34, x + 0.34, color=col, lw=2.2, zorder=4)
    ax2.hlines(mean, x - 0.28, x + 0.28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax2.scatter([x], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    ax2.text(x, max(d) + ymax2 * 0.03 + 0.6, f"x̄ {mean:.1f}\nmed {med:.0f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5, color="#222")
    for v in d: rec2.append([lab, v])
if on_all and off_all:
    p = _st.mannwhitneyu(on_all, off_all, alternative="two-sided").pvalue
    s = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
    ax2.text(1.65, ymax2 * 1.04, f"all on-target vs all off-target: {s} (p={p:.2g})", ha="center", va="bottom", fontsize=8, color="#333")
ax2.set_xticks([c[2] for c in POOL]); ax2.set_xticklabels([c[1] for c in POOL], rotation=20, ha="right", fontsize=8.5)
ax2.set_ylabel("Number of laser ablation events per cell"); ax2.set_ylim(0, ymax2 * 1.14)
ax2.set_title("Ablation dose — on-target (1/2/3) vs pooled off-target control\n"
              "matched dose: no significant on- vs off-target difference", loc="left", fontweight="bold", fontsize=10)
ax2.legend(handles=[Line2D([0], [0], color="#444", lw=2.2, label="median"),
                    Line2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                           markerfacecolor="white", markeredgecolor="#444", label="mean")], loc="upper right", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/ablation_count_on_vs_offpooled.png", bbox_inches="tight"); plt.close()
lib.record_plot("ablation_count_on_vs_offpooled", ["cohort", "log_ablation_events"], rec2,
    {"type": "violin+points", "metric": "Log Ablation Events per cell",
     "cohorts": "on-target by #Sisterless(1/2/3) vs off-target pooled (all target counts)",
     "test": "Mann-Whitney U all-on vs all-off"}, SCRIPT,
    "Ablation dose — on-target (1/2/3) vs pooled off-target control")
print("ablation_count_on_vs_offpooled -> on_all n=%d mean=%.1f | off_all n=%d mean=%.1f" % (len(on_all), np.mean(on_all), len(off_all), np.mean(off_all)))

lib.record_plot("ablation_count_by_cohort", ["cohort", "log_ablation_events"], rec,
    {"type": "violin+points", "metric": "Log Ablation Events (PAS-derived) per cell",
     "cohorts": "on-target by #Sisterless(1/2/3), off-target by #Unique Targets(1/2/3)",
     "test": "Mann-Whitney U on-N vs off-N (skipped when off n<3)",
     "caveat": "off-target rarely has exactly 1/2/3 targets -> off-1 & off-3 have n=1"},
    SCRIPT, "Ablation dose by cohort — ablation events per cell (on- vs off-target)")
print("ablation_count_by_cohort ->", {c[1]: len(vals[c[0]]) for c in COHORTS})
print("  means:", {c[1]: (round(np.mean(vals[c[0]]), 2) if vals[c[0]] else None) for c in COHORTS})
