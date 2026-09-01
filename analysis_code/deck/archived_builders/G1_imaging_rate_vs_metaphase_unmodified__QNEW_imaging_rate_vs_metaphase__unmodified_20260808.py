"""Imaging rate vs metaphase duration, unModified cells.

USER 2026-08-08: "you'll notice there are two groups of unmodified cells: those imaged every minute, and
those imaged more frequently. plot the imaging rate against the metaphase duration."

WHY THIS MATTERS: if the faster-imaged group sits at longer metaphase durations, that is a phototoxicity
signal, and it would mean imaging rate is a confound in every metaphase-duration comparison that pools the
two groups. So the plot is built to answer that directly: the two rate groups side by side, with the test.

GROUPING IS DATA-DRIVEN, NOT ASSUMED. "Every minute" is read from the master `Time Interval (s)` column
rather than hard-coded: rows at ~60 s form the 1-minute group, anything meaningfully faster forms the
other. The split point is reported in the caption so it is auditable, and the raw interval is kept on the
scatter so the grouping can never hide structure.

No anaphase data is involved (metaphase duration is a scalar per cell), per her 2026-08-08 standing rule.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G1_imaging_rate_vs_metaphase_unmodified"
SCRIPT = __file__

data, _ = lib.load_master_plots()
mr = {r["Batch Name"]: r for r in data}
_dbl = lib.double_chromosome_batches()
_manual = set(lib.manual_plot_exclusions(PLOT_ID))

# ---- cohort: unModified only -------------------------------------------------------------------
coh = lib.assign_cohorts()
unmod = [b for b, _v in coh.get("unModified", [])]

rows = []
for b in sorted(unmod):
    if lib.plot_excluded(b) or lib.is_mad1(b) or b in _dbl or b in _manual:
        continue
    r = mr.get(b, {})
    iv = (r.get("Time Interval (s)", "") or "").strip()
    md = lib.parse_time(r.get("Meta Duration (s)", ""))
    try:
        iv = float(iv)
    except Exception:
        continue                      # no recorded interval -> cannot place it on a rate axis
    if md is None or iv <= 0:
        continue
    rows.append([b, iv, md / 60.0])

if not rows:
    raise SystemExit("no unModified rows with both Time Interval and Meta Duration")

ivs = np.array([r[1] for r in rows], float)
mds = np.array([r[2] for r in rows], float)

# ---- the split: "every minute" vs faster ---------------------------------------------------------
# The recorded intervals are FOUR discrete values, not two: 3 s (n=2), 20 s (n=22), 60 s (n=38),
# 120 s (n=4). Her two groups are "every minute" and "more frequently", so:
#     every minute  = 60 s exactly
#     more frequent = anything < 60 s (3 s and 20 s)
#     120 s is every TWO minutes -- LESS frequent, so it belongs to NEITHER group. It is kept in the
#     data and drawn on the scatter, but held out of the two-group test rather than silently folded
#     into the 1-minute group (an interval >= 45 s cutoff did exactly that and was wrong).
ONE_MIN = 60.0
is_min = ivs == ONE_MIN
is_fast = ivs < ONE_MIN
is_slow = ivs > ONE_MIN                      # 120 s: reported, not tested
grp = np.where(is_min, "1 min", np.where(is_fast, "faster than 1 min", "slower than 1 min"))
for i, r in enumerate(rows):
    r.append(str(grp[i]))

print(f"unModified cells with both fields: {len(rows)}")
print(f"  interval values present: {sorted(set(ivs.tolist()))}")
print(f"  1 min (60s): {int(is_min.sum())}   faster (<60s): {int(is_fast.sum())}"
      f"   slower (>60s, held out): {int(is_slow.sum())}")

# ---- stats -------------------------------------------------------------------------------------
a, bb, sl = mds[is_min], mds[is_fast], mds[is_slow]
p_txt, r_txt = "", ""
if len(a) >= 3 and len(bb) >= 3:
    try:
        from scipy import stats
        u, p = stats.mannwhitneyu(a, bb, alternative="two-sided")
        p_txt = f"1 min vs faster: Mann-Whitney p = {p:.3g}"
        # correlation over the TESTED cells only, so the 4 held-out 120 s cells cannot drive it
        m = is_min | is_fast
        rho, prho = stats.spearmanr(ivs[m], mds[m])
        r_txt = f"Spearman rho = {rho:.2f} (p = {prho:.3g}), 60 s + faster only"
    except Exception as e:
        p_txt = f"(stats unavailable: {e})"

# ---- figure ------------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 4.8), width_ratios=[1.25, 1])

# left: the raw relationship, so the grouping cannot hide structure
ax1.scatter(ivs[is_fast], mds[is_fast], s=42, c="#d6604d", edgecolor="k", lw=.5,
            label=f"faster than 1 min (n={int(is_fast.sum())})", zorder=3)
ax1.scatter(ivs[is_min], mds[is_min], s=42, c="#2166ac", edgecolor="k", lw=.5,
            label=f"1 min (n={int(is_min.sum())})", zorder=3)
if is_slow.any():
    ax1.scatter(ivs[is_slow], mds[is_slow], s=42, c="#999999", edgecolor="k", lw=.5, marker="s",
                label=f"slower, held out (n={int(is_slow.sum())})", zorder=3)
ax1.axvline(ONE_MIN, color="#888", ls="--", lw=1, zorder=1)
ax1.set_xscale("log")
ax1.set_xticks(sorted(set(ivs.tolist())))
ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda v, _p: f"{v:g}"))
ax1.set_xlabel("imaging interval (s per frame)")
ax1.set_ylabel("metaphase duration (min)")
ax1.set_title("unModified: imaging rate vs metaphase duration", fontsize=10)
ax1.legend(frameon=False, fontsize=8)
if r_txt:
    # sits just under the legend, clear of the 60 s marker line and the x tick labels
    ax1.text(.02, .70, r_txt, transform=ax1.transAxes, ha="left", va="top", fontsize=8, color="#444")

# right: the two groups as distributions
parts = [bb, a] + ([sl] if len(sl) else [])
labels = [f"faster\nthan 1 min\nn={len(bb)}", f"1 min\nn={len(a)}"] + ([f"slower\n(held out)\nn={len(sl)}"] if len(sl) else [])
cols = ["#d6604d", "#2166ac"] + (["#999999"] if len(sl) else [])
bp = ax2.boxplot(parts, widths=.55, patch_artist=True, showfliers=False,
                 medianprops=dict(color="k", lw=1.4))
for patch, c in zip(bp["boxes"], cols):
    patch.set_facecolor(c); patch.set_alpha(.35); patch.set_edgecolor("k")
rng = np.random.default_rng(0)
for i, (vals, c) in enumerate(zip(parts, cols), start=1):
    if len(vals):
        ax2.scatter(np.full(len(vals), i) + rng.uniform(-.11, .11, len(vals)), vals,
                    s=26, c=c, edgecolor="k", lw=.4, zorder=3)
ax2.set_xticks(list(range(1, len(parts) + 1))); ax2.set_xticklabels(labels, fontsize=8)
ax2.set_ylabel("metaphase duration (min)")
ax2.set_title("by imaging-rate group", fontsize=10)
if p_txt:
    ax2.text(.5, .97, p_txt, transform=ax2.transAxes, ha="center", va="top", fontsize=9)

fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200); plt.close(fig)
print("wrote", png)

lib.record_plot(
    PLOT_ID,
    ["batch", "imaging_interval_s", "metaphase_duration_min", "rate_group"],
    rows,
    {"kind": "scatter+box", "one_min_s": ONE_MIN, "cohort": "unModified"},
    script=SCRIPT,
    caption=(f"unModified cells, imaging interval from master 'Time Interval (s)'. Four discrete rates are "
             f"present: 3 s, 20 s, 60 s, 120 s. 'Every minute' = 60 s (n={int(is_min.sum())}); 'more "
             f"frequently' = 3 s + 20 s (n={int(is_fast.sum())}). The {int(is_slow.sum())} cells at 120 s "
             f"are every TWO minutes -- less frequent than either group -- so they are drawn but held out "
             f"of the test. {p_txt}. {r_txt}."),
    source=["/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch",
    fig=png,
)
print("recorded", PLOT_ID)
