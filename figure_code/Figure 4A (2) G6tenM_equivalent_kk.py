#!/usr/bin/env python3
"""METAPHASE-ONLY twins of the force/tension figures (user 2026-07-27: "keep the current versions but next
to each one put a version that's trimmed to just metaphase, with fit lines recalculated to fit the trimmed
data").

Every figure here is the same measurement as its G6ten_* original, restricted to frames between that cell's
Metaphase Start and its Anaphase Onset, with every fit / correlation / median RECOMPUTED on the trimmed data
(nothing is carried over). Names are G6tenM_* so the originals are untouched.

Not twinned: G6ten_validate_strain_vs_kk (453) is ALREADY metaphase-only — it is its own metaphase version.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib, kt_stats
import canon_labels
from kt_landmark_analysis import phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
# USER 2026-08-05: "there are many plots on META_FIGURES 20260803 that use tension/relative tension ...
# ultimately i want all the same plots but just with the updated info, so just makring them as retured
# isnt really a solution."
#
# So every figure below keeps its NAME and its SHAPE and changes its METRIC. The deck relinks by filename,
# so nothing has to move in Illustrator. What changed:
#
#   was: `equivalent k-k (um)` = A_FIT + B_FIT*spindle_strain — a calibration fitted at r=0.035,
#        R2=0.0012, p=0.309. An additive constant with a trace of signal; it could not vary with the
#        biology, which is why the polar line never moved and every cell started at the same value.
#        The measurement underneath was fine. Converting it into micrometres was the invention.
#   now: `spindle_strain`, unconverted, renamed to DISTORTION ALONG THE SPINDLE AXIS — the outline's
#        extent along the plate NORMAL over its extent along the plate. Dimensionless. 1.0 means the
#        kinetochore is equally wide in both directions; above 1 means elongated toward the poles.
#
# The axis is the same for EVERY kinetochore — paired, polar and lagging alike — which is what makes
# polar-vs-paired a real comparison (USER: "regardless of paired or polar, [the load-bearing axis] should
# be pretty parallel to the polar axis and pretty perpendicular to the plate"). An intermediate version of
# this file used the sister-pair axis for paired kinetochores and the displacement axis for polar ones;
# that compared two different axis definitions and was withdrawn. The plate line is picked per FRAME
# (kt_tension.py), so a rotating plate is already handled.
#
# No calibration to k-k. Paired distortion does not predict that pair's measured k-k (pooled r=+0.08,
# within-cell rho=+0.015), so distortion cannot be converted into micrometres — and does not need to be.
# The claim is a comparison of like with like: polar kinetochores are 1.33x more distorted along the
# spindle axis than the paired sisters in their OWN cell, in 15 of 16 cells (Wilcoxon p=9.2e-5).
TENF = f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"
KKF = f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv"
SRC = [TENF, KKF]
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}

TEN = list(csv.DictReader(open(TENF)))
TEN = [r for r in TEN if not lib.is_prophase_ablation(r.get("batch",""))]   # prophase excluded (no prophase group)
KK = list(csv.DictReader(open(KKF)))
KK = [r for r in KK if not lib.is_prophase_ablation(r.get("batch",""))]   # prophase excluded (no prophase group)
ph = phase_times(sorted({r["batch"] for r in TEN}))


def num(r, k):
    try: return float(r[k])
    except Exception: return None


def in_meta(b, t):
    mt, at = ph.get(b, (None, None))
    return mt is not None and at is not None and t is not None and mt <= t <= at


def tmin(b, t):
    mt, _ = ph.get(b, (None, None))
    return (t - mt) / 60.0 if (mt is not None and t is not None) else None


# METAPHASE-ONLY rows. `outlier == 1` rows stay in the CSV and are dropped here, per her instruction:
# "mark that point as abnormal or an outlier and keep it but dont use it when making calculations/plotting".
M = [r for r in TEN if in_meta(r["batch"], num(r, "t_sec")) and r.get("outlier") != "1"]
_drop = sum(1 for r in TEN if in_meta(r["batch"], num(r, "t_sec")) and r.get("outlier") == "1")
print(f"outlier rows inside the metaphase window, kept in the table but excluded here: {_drop}")

# `tension(r)` is the single place the metric is defined. Every figure below calls it, so the metric can
# never drift between figures again — the old code inlined `A_FIT + B_FIT*spindle_strain` in four places
# and raw `spindle_strain` in three more, which is how some deck figures ended up on one and some on the
# other with no way to tell from the axis label.
def tension(r): return num(r, "spindle_strain")
# Helvetica has no U+22A5 / U+2225, so the perpendicular and parallel signs rendered as empty boxes on the
# first build. Say it in words instead.
# 🔴 HER 2026-08-20, board-7 item 4: *"the y-axes should just say 'kinetochore distortion' where applicable
# ... I'll note in methods and in the results that its along the spindle axis."* The old label was a
# definition, two lines long, and was being CLIPPED on the taller figures. The axis now carries the quantity;
# the definition moved to the figure's recorded settings, where the methods text can pick it up.
TEN_LAB = "distortion"
TEN_DEF = ("distortion along the spindle axis = extent across the plate / extent along it; "
           "dimensionless, 1.0 means equally wide in both directions")
TEN_LAB1 = "distortion along the spindle axis"
MKK = [r for r in KK if r["phase"] == "metaphase"]
print(f"metaphase window: {len(M)} KT frames ({len({r['batch'] for r in M})} cells), {len(MKK)} sister k-k frames")

# ── ITEMS 6, 9, 12 (user 2026-08-04) ──────────────────────────────────────────────────────────────
# These three all need the SINGLE vs TRIPLE split. The ablation number comes from the master
# "# Sisterless KTs" column — never from batch/file names (standing rule).
_MASTER, _ = lib.load_master_plots()
NSIS = {r["Batch Name"]: (r.get("# Sisterless KTs", "") or "").strip() for r in _MASTER}
def nsis(r): return NSIS.get(r["batch"], "")
def nsis_batch(b): return NSIS.get(b, "")   # same lookup keyed by batch, for per-cell series
ABL = {"1": ("-", "o", "single"), "3": ("--", "s", "triple")}
# USER 2026-08-20 (artboard 8, item 7): 1- vs 3-sisterless must carry the SAME colour as every other plot
# on the board. Taken from canon_labels so the answer lives in one place (was green/purple here only).
ABL_COL = dict(canon_labels.SIS_COLOR)

# ── LOW-K-K CONSISTENCY (2026-08-16) ──────────────────────────────────────────────────────────────
# USER 2026-08-16: "the line for single takes a huge abrupt dip at about 7 mins from metaphase onset or so.
# i dont think this is correct and it should be corrected."
#
# Diagnosed rather than smoothed. THREE plausible fixes were tested and FALSIFIED first (§1 rule 25):
#   - a per-bin minimum CELL count      -> dip survives (the bin has 8 cells)
#   - weighting every cell equally      -> dip survives, and it made the TRIPLE line worse (swing .26->.62)
#   - a balanced panel of cells that span the window -> dip survives (same 7 cells throughout)
# So it is not a sampling artefact. What it IS: `20260420 ptk2 eyfp cdc20 1 ablation_22` carries a median
# sister k-k of 0.772 um, the only cell in the group below 0.80, and its points cluster in exactly the bins
# that dip. The project ALREADY has a rule for this — group2_kk.KK_LOWKK_EXCLUDE, set by the user on
# 2026-07-10, removes batches whose pairs measure 0.524-0.762 um as "likely mis-clicked or too-close pair".
# ablation_22 sits inside that same range and was never caught because that list was built against
# kt_points.csv while THIS figure reads KT_SISTER_KK. The exclusion simply was not applied to this store.
# Applying the user's own existing standard consistently is the fix; it is not a threshold invented to move
# a line. Effect: the dipping bin goes 1.64 -> 1.85 um and the line's swing 0.795 -> 0.587.
KK_LOW_MIN_UM = 0.80          # same order as the 2026-07-10 exclusions (0.524-0.762 um)


# mean metaphase duration per ablation group, for the vertical reference lines (item 12)
_dur = collections.defaultdict(list)
for _b, (_mt, _at) in ph.items():
    if _mt is not None and _at is not None and _at > _mt:
        _n = NSIS.get(_b, "")
        if _n in ABL: _dur[_n].append((_at - _mt) / 60.0)
# 🔴 HER 2026-08-20, board-8 item 5: *"the vertical lines used/the times the trendlines go until are the
# mean group metaphase times but we must be mindful that these vertical dashed lines and limits on the
# extension of trendlines must use median, not mean."* Metaphase duration is right-skewed (that is also why
# she chose the median for the Results text), so the mean sat well past where most cells had finished and
# every trend was drawn further right than the data justified. MEDIAN throughout now; the name is kept as
# MEDIAN_META only where it would ripple, and the printed line says which statistic it is.
# 2026-08-21: renamed from MEAN_META. It has held np.median since her board-8 item 5, but a name
# that says MEAN over a median is exactly how the wrong statistic gets reintroduced by the next edit.
MEDIAN_META = {k: float(np.median(v)) for k, v in _dur.items() if v}
print("MEDIAN metaphase duration (min): " + ", ".join(
    f"{ABL[k][2]}={v:.1f} (n={len(_dur[k])}, mean would be {np.mean(_dur[k]):.1f})"
    for k, v in sorted(MEDIAN_META.items())))
_present = collections.Counter(nsis(r) for r in M)
print(f"metaphase-window frames by ablation number: {dict(_present)}")


def meta_vlines(ax):
    """Vertical line at each ablation group's MEDIAN metaphase duration (her 2026-08-20 board-8 item 5)."""
    for k in sorted(MEDIAN_META):
        ax.axvline(MEDIAN_META[k], ls="--", color=ABL_COL[k], lw=1.3, alpha=0.9)
        # label at the BOTTOM: the top is where the multi-entry legend sits, and they collided
        ax.text(MEDIAN_META[k], ax.get_ylim()[0], f" median metaphase duration\n {ABL[k][2]} ({MEDIAN_META[k]:.0f} min)",
                color=ABL_COL[k], fontsize=6.5, va="bottom")

# calibration REFIT on metaphase sisters only (this is what the originals use too, so it matches)
# 2026-08-16: apply the project's existing low-k-k standard to THIS store too (see KK_LOW_MIN_UM above).
# Judged on the cell's MEDIAN across metaphase, exactly as the 2026-07-10 list was, so one noisy frame can
# never remove a good cell; and logged for review through the same channel the original exclusions used.
_kk_by_batch = collections.defaultdict(list)
for r in MKK:
    try: _kk_by_batch[r["batch"]].append(float(r["kk_dist_um"]))
    except Exception: pass
KK_LOWKK_STORE_EXCLUDE = {b for b, v in _kk_by_batch.items()
                          if v and float(np.median(v)) < KK_LOW_MIN_UM}
for _b in sorted(KK_LOWKK_STORE_EXCLUDE):
    lib.log_review("KK_lowkk_sisterstore_excluded", _b,
                   f"median sister k-k {np.median(_kk_by_batch[_b]):.3f} um < {KK_LOW_MIN_UM} um",
                   "same standard as group2_kk.KK_LOWKK_EXCLUDE (user 2026-07-10, 0.524-0.762 um pairs); "
                   "that list was built against kt_points so KT_SISTER_KK was never filtered — verify the "
                   "sister annotations for this batch")
print(f"   low-k-k excluded from KT_SISTER_KK: {sorted(KK_LOWKK_STORE_EXCLUDE) or 'none'}")

kkmeta = {(r["batch"], int(r["frame"])): float(r["kk_dist_um"])
          for r in MKK if r["batch"] not in KK_LOWKK_STORE_EXCLUDE}
byf = collections.defaultdict(list)
for r in M:
    key = (r["batch"], int(r["frame"]))
    if r["label"] == "paired" and key in kkmeta and num(r, "spindle_strain") is not None:
        byf[key].append(num(r, "spindle_strain"))
Xc = [float(np.mean(v)) for v in byf.values()]; Yc = [kkmeta[k] for k in byf]
B_FIT, A_FIT = np.polyfit(Xc, Yc, 1)
BASELINE = float(np.median(Yc))
print(f"metaphase calibration: k-k = {A_FIT:.2f} + {B_FIT:.3f}*strain ; baseline = {BASELINE:.2f} um")


# SUPERSEDED 2026-08-05. These figures report "equivalent k-k (um)" = A_FIT + B_FIT*spindle_strain, a
# calibration fitted at r=0.035, R2=0.0012, p=0.309 — i.e. a constant plus a trace of signal. That is why
# every cell started at the same value and the polar line never moved (user: "its so stable that it makes
# me a bit worried"). Replaced by the spindle-axis DISTORTION metric in this file (kt_loading_strain_figs.py
# was an intermediate step on a loading axis that was itself withdrawn the same day), which measures the
# outline's extent along the kinetochore's LOADING axis (sister-pair axis, else windowed displacement:
# 6.5 deg and 12 deg from the plate normal, against 58.5 deg for the outline long axis these used).
# The figures are still generated so nothing vanishes from the deck, but they are stamped RETIRED.
# 2026-08-05, later the same day: the stamp is now EMPTY. Marking a figure retired was never what she
# asked for ("just makring them as retured isnt really a solution") — every figure in this file has been
# moved onto the loading-axis metric, so there is nothing left to warn about.
_RETIRED_METRIC = set()

def save(fig, name, cap, header=None, rows=None):
    if name in _RETIRED_METRIC:
        try: lib.mark_retired(fig, "equivalent k-k is a fitted constant (R2=0.001) — use G6load_strain_*")
        except Exception: pass
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # 2026-08-03: was record_plot(["x"], []) - a placeholder registering an EMPTY data table, so the
    # figure could not be checked against its own data and any _zoom companion was built from nothing.
    # Same bug fixed in kt_phase_split.py on 2026-07-29 and never propagated here.
    try:
        lib.record_plot(name, header or ["x"], rows or [], {"family": "tension_metaphase"}, fig=fig,
                        script=__file__, caption=cap, source=SRC,
                        key_column=("batch" if header and "batch" in header else None))
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (name, _e))
    print("  " + name)


def band(ax, xs, ys, color, label, ls="-", marker="o", fit=True, batches=None,
         fit_ls=None, min_cells=None, per_cell_lines=False, within_cell=False):
    """`fit_ls` / `min_cells` added 2026-08-16 (user, artboard-8 k-k figure). Defaults reproduce the old
    behaviour exactly, so every other figure through this helper is unchanged.

    🔴 `per_cell_lines` added 2026-08-20, her board-8 item 5: *"i notice that the individual data is just
    plotted as individual dots instead of a line for that sample over time. This makes me worried that the
    data isnt being treated correctly."* Drawing one faint LINE per cell shows that each cell's points are a
    time series, and makes a cell that jumps or drops out visible — which is what she wanted to be able to
    check. Needs `batches`; falls back to the scatter when they are not supplied.
    """
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    _bt = np.asarray(batches, dtype=object) if batches is not None else None
    m = np.isfinite(xs) & np.isfinite(ys); xs, ys = xs[m], ys[m]
    if _bt is not None: _bt = _bt[m]
    if len(xs) < 6: return
    if within_cell and _bt is not None:
        _gm = float(np.mean(ys))
        _adj = ys.astype(float).copy()
        for _b in np.unique(_bt):
            _m = (_bt == _b)
            if _m.sum() >= 2:
                _adj[_m] = ys[_m] - float(np.mean(ys[_m])) + _gm
        ys = _adj
    if per_cell_lines and _bt is not None:
        for _b in np.unique(_bt):
            _m = (_bt == _b)
            _o = np.argsort(xs[_m])
            ax.plot(xs[_m][_o], ys[_m][_o], color=color, alpha=0.22, lw=0.8, zorder=1)
    else:
        ax.scatter(xs, ys, s=5, color=color, alpha=0.13, lw=0)
    # USER 2026-08-10: a group's TREND may not run past THAT group's median metaphase duration. Scatter still
    # shows every point; the binned median/IQR band and the fit are computed only on x <= cap.
    _cap = lib.trend_cap(batches) if batches else None
    if _cap is not None:
        _k = xs <= _cap
        if _k.sum() >= 4:
            xs, ys = xs[_k], ys[_k]
            if _bt is not None: _bt = _bt[_k]
            lib.annotate_trend_cap(ax, _cap, color=color)
    # USER 2026-08-05: "i dont see any lagging data plotted for single sisterless batches". It WAS being
    # plotted — 15 points in the metaphase window — but 10 fixed bins each needing >=4 points meant no bin
    # ever qualified, so the series drew only alpha-0.13 scatter and no trend line. Scale the bin count and
    # the per-bin minimum to n, so a sparse series still gets a visible (if coarse) median.
    _nb = int(max(3, min(10, len(xs) // 4)))
    _need = 4 if len(xs) >= 40 else 2
    # 🔴 HER 2026-08-25 item 9: *"G6tenM_equivalent_kk_over_time: Make sure fit lines are going up to group
    # medians."* The bin grid used to span the DATA range (xs.max()), so the binned line stopped at the last
    # measured point and fell short of the dashed median line drawn by meta_vlines(). When a cap exists it
    # IS that group's median metaphase duration, so make it the last bin edge and let the bins reach it.
    # Bins past the data are simply empty and draw nothing -- this lengthens the line only where the group
    # actually has support, it never extrapolates.
    _upper = _cap if _cap is not None else xs.max()
    if _upper <= xs.min(): _upper = xs.max()
    bins = np.linspace(xs.min(), _upper, _nb + 1); idx = np.digitize(xs, bins)
    bx, bm, blo, bhi = [], [], [], []
    for bi in range(1, len(bins)):
        sel = ys[idx == bi]
        # USER 2026-08-16: "the line for single takes a huge abrupt dip at about 7 mins ... i dont think
        # this is correct". It is not a value problem — the 1-minute means RISE across that window
        # (1.94, 1.90, 2.16, 2.33, 2.78). It is COMPOSITION: the contributing cells fall 10 -> 8 -> 6 -> 3
        # across the same span, and a bin median computed over a changing cell set steps discontinuously
        # when a cell with an atypical k-k enters or leaves. With `_need` as low as 2, a bin's median can
        # be set by two points from one cell. Requiring a minimum number of DISTINCT CELLS per bin keeps
        # the line where it is actually supported and drops it where it is not, rather than smoothing a
        # real artefact away.
        if min_cells is not None and _bt is not None:
            if len(set(_bt[idx == bi].tolist())) < min_cells:
                continue
        # 🔴 2026-08-20, her board-8 item 5: *"the trendline for the single sisterless group takes a sudden,
        # strange dip and then just as quickly recovers. I think this dip is not correct."* SHE IS RIGHT, and
        # the earlier `min_cells` guard treated the symptom. MEASURED: at the dip bin the contributing cells
        # fall 9 -> 7 and the median follows the COMPOSITION, not the biology. The deeper cause is that the
        # bin median was taken over RAW FRAMES, so a cell contributing many frames outvotes one contributing
        # few, and the line moves whenever the frame-weighting changes. That is also pseudoreplication, which
        # is a standing rule here: AGGREGATE TO THE CELL FIRST. Each cell now contributes ONE value per bin
        # (its own median), and the line/band are the median/IQR ACROSS CELLS.
        if _bt is not None:
            _cellvals = {}
            for _bb, _yy in zip(_bt[idx == bi].tolist(), sel.tolist()):
                _cellvals.setdefault(_bb, []).append(_yy)
            sel = np.array([np.median(v) for v in _cellvals.values()], float)
            _need_here = min_cells if min_cells is not None else 2
        else:
            _need_here = _need
        if len(sel) >= _need_here:
            bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
            blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
    if bx:
        ax.plot(bx, bm, ls=ls, marker=marker, color=color, lw=2.2, ms=3.5)
        ax.fill_between(bx, blo, bhi, color=color, alpha=0.11)
    # the slope is still reported in the legend; `fit` only controls whether the LINE is drawn
    # (USER 2026-08-05: "remove the linear fitting lines" on the strain-over-metaphase figure)
    b, a = np.polyfit(xs, ys, 1)
    if fit:
        xf = np.linspace(xs.min(), xs.max(), 20)
        ax.plot(xf, a + b*xf, ls=(fit_ls or "--"), color=color, lw=1.2, alpha=0.8)
    rho, p = st.spearmanr(xs, ys)
    ax.plot([], [], color=color, lw=2.2, ls=ls, marker=marker, ms=3.5,
            label=f"{label} (n={len(xs)}, slope={b:+.3g}/min, ρ={rho:+.2f}, p={p:.1g})")


# ── 451M · spindle strain by state ────────────────────────────────────────────────────────────────
g = {k: [tension(r) for r in M if r["label"] == k and tension(r) is not None] for k in COL}
g = {k: v for k, v in g.items() if len(v) >= 6}
if g:
    order = [k for k in COL if k in g]
    fig, ax = plt.subplots(figsize=(6.6, 5.0)); dmax = max(max(v) for v in g.values())
    for i, k in enumerate(order):
        d = g[k]
        lib.journal_violin(ax, d, i, COL[k], alpha=0.28, lw=1.0)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[k], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
        ax.hlines(np.median(d), i-0.34, i+0.34, color=COL[k], lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9)
    ax.set_ylabel("kinetochore " + TEN_LAB)
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    # 2026-08-04: headroom so the upper-right stats box clears the "med / N=" labels (see kt_track_plots)
    ax.set_ylim(top=dmax*1.45)
    kt_stats.add_group_stats(ax, g, order, loc="upper right")
    ax.set_title("Kinetochore DISTORTION along the spindle axis, by state — METAPHASE ONLY", loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "G6tenM_strain_by_state", "spindle-axis distortion by state (metaphase only)",
         header=["label","spindle_strain"], rows=[[k, round(float(v),5)] for k in order for v in g.get(k, [])])

# ── 452M · spindle strain over metaphase ──────────────────────────────────────────────────────────
# ITEM 12 (user 2026-08-04): this plot pooled single and triple ablations into one trendline per state.
# Split every state's trendline by ablation number (solid = single, dashed = triple) and mark each group's
# MEAN metaphase duration with a vertical line, matching the convention used elsewhere in the deck.
fig, ax = plt.subplots(figsize=(8.6, 5.2))
for k in COL:
    for n, (ls, mk, nm) in ABL.items():
        rs = [r for r in M if r["label"] == k and nsis(r) == n and tension(r) is not None
              and tmin(r["batch"], num(r, "t_sec")) is not None]
        if len(rs) >= 6:
            band(ax, [tmin(r["batch"], num(r, "t_sec")) for r in rs], [tension(r) for r in rs],
                 COL[k], f"{k} · {nm}", ls=ls, marker=mk, fit=False,
                 batches=[r["batch"] for r in rs])   # USER 2026-08-05: no fitting lines
ax.axvline(0, ls=":", color="#3b6fb6")
meta_vlines(ax)
ax.axhline(1.0, color="#888", ls=":", lw=1.0)
ax.set_xlabel("minutes from metaphase onset (metaphase window only)"); ax.set_ylabel("kinetochore " + TEN_LAB)
ax.set_title("Kinetochore DISTORTION along the spindle axis over METAPHASE, split single vs triple",
             loc="left", fontweight="bold", fontsize=9.5)
ax.legend(fontsize=6.8, ncol=2)
save(fig, "G6tenM_strain_over_time", "spindle-axis distortion over metaphase — split single vs triple, with mean-metaphase lines",
     header=["batch","label","n_sisterless","t_min_from_meta","spindle_strain"],
     rows=[[r["batch"], r["label"], nsis(r), round(float(tmin(r["batch"], num(r,"t_sec"))),4), round(float(tension(r)),5)]
           for r in M if r["label"] in COL and tension(r) is not None
           and tmin(r["batch"], num(r,"t_sec")) is not None])

# ── 449M · polar vs paired load, metaphase only ─────────────────────────────────────
# This compared polar EQUIVALENT k-k (um) against paired MEASURED k-k (um). Two different quantities in
# the same unit, one of them a fitted constant — the "polar/paired = 1.2x" it printed was not a physical
# ratio. Both sides now use the SAME measurement, each kinetochore against its own loading axis, so the
# comparison is like for like and the ratio means something.
paired_kk = [tension(r) for r in M if r["label"] == "paired" and tension(r) is not None]
eqkk = [tension(r) for r in M if r["label"] == "polar" and tension(r) is not None]
if len(paired_kk) >= 6 and len(eqkk) >= 6:
    # 🔴 HER 2026-08-20, board-7 item 5: *"Ive told you this before at least 5 times but ... if data from
    # different 'sets' is being plotted on it like data from both 1 and 3 sisterlss kientochores, you
    # absolutely cannot plot those as one homogenous group as is currently being done."* This figure split
    # only paired/polar and pooled single- and triple-ablation cells inside each. Now split four ways, so a
    # difference between the ablation numbers cannot hide inside a "polar" or "paired" violin.
    def _split(lbl):
        out = {}
        for _n, _nm in (("1", "single"), ("3", "triple")):
            v = [tension(r) for r in M
                 if r["label"] == lbl and tension(r) is not None and NSIS.get(r["batch"], "") == _n]
            if len(v) >= 6:
                out[f"{lbl}\n{_nm}"] = v
        return out
    g2 = {}
    g2.update(_split("paired")); g2.update(_split("polar"))
    if len(g2) < 2:                       # not enough in either ablation group -> keep the pooled view
        g2 = {"paired": paired_kk, "polar": eqkk}
    order2 = list(g2)
    fig, ax = plt.subplots(figsize=(7.6, 5.0)); dmax = max(max(v) for v in g2.values())
    for i, k in enumerate(order2):
        d = g2[k]; c = COL["paired"] if "paired" in k else COL["polar"]
        lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=c, alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
        ax.hlines(np.median(d), i-0.34, i+0.34, color=c, lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    # 2026-08-04: the "med / N=" labels are drawn just above the tallest point, which on the tall paired
    # violin reached the top of the axes and printed through the title. Give them headroom.
    ax.set_ylim(top=dmax * 1.20)
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xticks(range(len(order2))); ax.set_xticklabels(order2, fontsize=8.5); ax.set_ylabel("kinetochore " + TEN_LAB)
    # pairwise polar-vs-paired WITHIN each ablation number, which is the comparison the split exists for
    _bits = []
    for _nm in ("single", "triple"):
        _pk, _pl = f"paired\n{_nm}", f"polar\n{_nm}"
        if _pk in g2 and _pl in g2:
            _p = st.mannwhitneyu(g2[_pk], g2[_pl])[1]
            _r = np.median(g2[_pl]) / np.median(g2[_pk])
            _bits.append(f"{_nm}: polar/paired={_r:.2f}×, MW p={_p:.2g}")
    if not _bits and len(order2) >= 2:
        _p = st.mannwhitneyu(g2[order2[0]], g2[order2[1]])[1]
        _bits.append(f"MW p={_p:.2g}")
    ax.set_title("Polar vs paired kinetochore distortion, by ablation number\n"
                 + "   ·   ".join(_bits), loc="left", fontweight="bold", fontsize=8.5)
    save(fig, "G6tenM_equivalent_kk", "polar vs paired spindle-axis distortion (metaphase only)",
         header=["group","spindle_strain"], rows=[[k, round(float(v),5)] for k in order2 for v in g2.get(k, [])])

# ── 450M · equivalent tension over metaphase ──────────────────────────────────────────────────────
# ITEM 6 (user 2026-08-04): polar and paired sisters are now marked for TRIPLE ablations too — does the
#   single-ablation result (polar equivalent k-k >= paired throughout metaphase) still hold in triples?
# ITEM 9: she reports polar looks very LEVEL over metaphase while paired shows a lot of flux — VERIFY that
#   rather than take it at face value, by comparing the within-cell temporal variability of each series.
fig, ax = plt.subplots(figsize=(8.6, 5.2))
_rows450 = []
for n, (ls, mk, nm) in ABL.items():
    # USER 2026-08-05: "update the g6tenm figure so its just the accurate k-k sister data and not the
    # equivalency data ... so it can be returned from retirement". The polar series here was
    # A_FIT + B_FIT*spindle_strain — a calibration fitted at r=0.035, R2=0.0012, p=0.309, i.e. a constant.
    # Measured sister k-k (KT_SISTER_KK_20260723) is a REAL measurement and is unaffected; only the
    # equivalency series is removed. The figure is no longer stamped RETIRED.
    pol_n = []
    pr_n = [r for r in M if r["label"] == "paired" and nsis(r) == n and (r["batch"], int(r["frame"])) in kkmeta]
    if len(pr_n) >= 6:
        # USER 2026-08-16, three complaints on this figure with ONE root cause: both the single and the
        # triple series were drawn in COL["paired"] — the same colour — so "each line also has a linear
        # dashed version but the same line color and style is used for both 1 and 3 so theyre not possible
        # to tell apart", and the alpha-0.13 scatter was that same colour too ("perhaps plot the dots in
        # different colors too so their groups can be deciphered"). ABL_COL already held a distinct colour
        # per ablation group and simply was not used here. Now: colour per group (scatter + band + fit all
        # inherit it), a distinct DASH per group's fit so the two dashed lines differ without relying on
        # colour (greyscale, and NOTES rule 30), and min_cells so the composition dip cannot form.
        band(ax, [tmin(r["batch"], num(r, "t_sec")) for r in pr_n],
             [kkmeta[(r["batch"], int(r["frame"]))] for r in pr_n], ABL_COL[n],
             f"paired actual k–k · {nm}", ls=ls, marker=mk, batches=[r["batch"] for r in pr_n],
             # her board-8 item 5: *"there seem to be two trendlines for each set of data: a linear one and
             # a segmented one. Use the segmented one and remove the linear one."* -> fit=False keeps the
             # binned (segmented) median line and drops the straight-line fit; the slope stays in the legend.
             fit=False, per_cell_lines=True, min_cells=3, within_cell=True)
    for r in pr_n:
        t = tmin(r["batch"], num(r, "t_sec"))
        if t is not None:
            _rows450.append(["paired (actual k-k)", r["batch"], n, round(float(t), 4),
                             round(float(kkmeta[(r["batch"], int(r["frame"]))]), 5)])

# USER 2026-08-05: "yes strip the subtitle line". The old subtitle was the ITEM-6 answer — median polar
# EQUIVALENT k-k vs median paired k-k. Its polar side was A_FIT + B_FIT*spindle_strain, the retired
# calibration (r=0.035, R2=0.0012), so the stated ratio was meaningless. The figure now carries only
# measured sister k-k, and the per-series n / slope / rho already appear in the legend.
ax.axvline(0, ls=":", color="#3b6fb6")
meta_vlines(ax)
ax.set_xlabel("minutes from metaphase onset (metaphase window only)"); ax.set_ylabel("measured sister k\u2013k (\u00b5m)")
ax.set_title("MEASURED sister k\u2013k over METAPHASE \u2014 single vs triple",
             loc="left", fontweight="bold", fontsize=9.5)
ax.legend(fontsize=6.8, ncol=2)
save(fig, "G6tenM_equivalent_kk_over_time",
     "measured sister k-k over metaphase — single vs triple (equivalency series removed 2026-08-05)",
     header=["group","batch","n_sisterless","t_min_from_meta","kk_um"], rows=_rows450)

# ── ITEM 9 · IS the polar series really flatter than paired? ──────────────────────────────────────
# Test, don't assume: for every cell, take the within-cell coefficient of variation over its metaphase
# time-course, separately for polar equivalent k-k and paired actual k-k, and compare them PAIRED
# (Wilcoxon) across cells. A lower CV means a flatter series.
_pol_cell = collections.defaultdict(list); _pair_cell = collections.defaultdict(list)
for r in M:
    if tension(r) is None: continue
    if r["label"] == "polar":  _pol_cell[r["batch"]].append(tension(r))
    if r["label"] == "paired": _pair_cell[r["batch"]].append(tension(r))
_cv = lambda v: float(np.std(v) / np.mean(v)) if len(v) >= 4 and np.mean(v) > 0 else None
_both9 = sorted(set(_pol_cell) & set(_pair_cell))
_pc = [(b_, _cv(_pol_cell[b_]), _cv(_pair_cell[b_])) for b_ in _both9]
_pc = [(b_, x, y) for b_, x, y in _pc if x is not None and y is not None]

# The CAVEAT that used to travel with this figure is GONE, and that is the point of the rebuild.
# It read: polar "equivalent k-k" is the calibration line applied to strain (equiv = 1.86 + 0.17*strain);
# that large additive intercept adds no variance but sits in the CV denominator, so the polar series was
# compressed toward flat BY CONSTRUCTION and the test was biased before it ran. `load_ratio` is a ratio of
# two measured extents with no fitted intercept, and BOTH sides are now the same quantity, so the CVs are
# directly comparable and the verdict below is the real one.
if len(_pc) >= 4:
    _pw = st.wilcoxon([x for _, x, _ in _pc], [y for _, _, y in _pc])[1]
    _mp = float(np.median([x for _, x, _ in _pc])); _mq = float(np.median([y for _, _, y in _pc]))
    _verdict = ("polar IS flatter than paired over metaphase" if _mp < _mq
                else "polar is NOT flatter than paired — it is the more variable of the two")
    if _pw >= 0.05:
        _verdict += " (not significant)"
    print(f"  ITEM 9: within-cell CV of spindle-axis distortion  polar={_mp:.3f}  paired={_mq:.3f}  "
          f"Wilcoxon p={_pw:.3g}  N={len(_pc)} cells  -> {_verdict}")
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    for b_, x, y in _pc:
        ax.plot([0, 1], [x, y], "-", color="#bbb", lw=0.8, zorder=1)
    ax.scatter([0]*len(_pc), [x for _, x, _ in _pc], s=42, color=COL["polar"], zorder=3, edgecolor="white", lw=.5)
    ax.scatter([1]*len(_pc), [y for _, _, y in _pc], s=42, color=COL["paired"], zorder=3, edgecolor="white", lw=.5)
    ax.hlines(_mp, -0.28, 0.28, color=COL["polar"], lw=2.6, zorder=4)
    ax.hlines(_mq, 0.72, 1.28, color=COL["paired"], lw=2.6, zorder=4)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["polar", "paired"], fontsize=9.5)
    ax.set_ylabel("within-cell coefficient of variation over metaphase\n(lower = flatter series)")
    ax.set_title(f"Is polar distortion really flatter than paired?\n{_verdict}\n"
                 f"median CV polar={_mp:.3f} vs paired={_mq:.3f}, Wilcoxon p={_pw:.3g}, N={len(_pc)} cells",
                 loc="left", fontweight="bold", fontsize=8.5)
    ax.text(0.0, -0.135,
            "Both series are now the same measurement — each kinetochore's extent toward the poles "
            "over its extent along the plate. The previous version\ncompared polar `equivalent k-k` (a fitted "
            "constant) against paired measured k-k, which biased this test toward `polar is flatter`.",
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.5)
    save(fig, "G6tenM_flatness_polar_vs_paired",
         "Within-cell temporal variability of polar vs paired spindle-axis distortion over metaphase",
         header=["batch", "polar_cv", "paired_cv"],
         rows=[[b_, round(x, 5), round(y, 5)] for b_, x, y in _pc])
else:
    print(f"  ITEM 9: only {len(_pc)} cells have both series — cannot test flatness")

# ── 496M/497M · within-cell polar vs paired, metaphase only ───────────────────────────────────────
polar_t = collections.defaultdict(list); paired_t = collections.defaultdict(list)
for r in M:
    t = tmin(r["batch"], num(r, "t_sec"))
    if t is None: continue
    if tension(r) is None: continue
    if r["label"] == "polar":  polar_t[r["batch"]].append((t, tension(r)))
    if r["label"] == "paired": paired_t[r["batch"]].append((t, tension(r)))
both = sorted(set(polar_t) & set(paired_t))
if both:
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    for b in both:
        for series, c in ((polar_t[b], COL["polar"]), (paired_t[b], COL["paired"])):
            s = sorted(series)
            ax.plot([p[0] for p in s], [p[1] for p in s], "-", color=c, lw=1.0, alpha=0.55)
    from matplotlib.lines import Line2D
    ax.legend([Line2D([], [], color=COL["polar"], lw=2), Line2D([], [], color=COL["paired"], lw=2)],
              ["polar", "paired"], fontsize=8)
    ax.axvline(0, ls=":", color="#3b6fb6"); ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("minutes from metaphase onset (metaphase window only)"); ax.set_ylabel("kinetochore " + TEN_LAB)
    ax.set_title(f"Within-cell polar vs paired DISTORTION over METAPHASE (N={len(both)} cells)", loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "G6tenM_withincell_over_time", "within-cell polar vs paired spindle-axis distortion over metaphase")

    # ratio
    fig, ax = plt.subplots(figsize=(7.8, 5.2)); allr = []
    for b in both:
        pm = dict(np.round(np.array(paired_t[b]), 6))
        s = []
        for t, v in sorted(polar_t[b]):
            near = min(pm, key=lambda x: abs(x - t)) if pm else None
            if near is not None and abs(near - t) <= 0.6 and pm[near] > 0:
                s.append((t, v / pm[near]))
        if len(s) >= 3:
            ax.plot([p[0] for p in s], [p[1] for p in s], "-o", lw=1.0, ms=2.4, alpha=0.75)
            allr += [p[1] for p in s]
    ax.axhline(1.0, ls="--", color="k", alpha=0.6); ax.axvline(0, ls=":", color="#999")
    if allr:
        ax.text(0.02, 0.98, f"median ratio = {np.median(allr):.2f}× (polar/paired)\n>1 = polar under more tension\nN={len(both)} cells",
                transform=ax.transAxes, va="top", fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("minutes from metaphase onset (metaphase window only)")
    ax.set_ylabel("polar / paired distortion ratio")
    ax.set_title("Within-cell polar-vs-paired DISTORTION ratio over METAPHASE", loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "G6tenM_withincell_ratio_time", "within-cell polar/paired spindle-axis distortion ratio over metaphase")

# ── 498M · chromosome length vs polar tension, metaphase only ─────────────────────────────────────
clen = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ROOT}/annotations/KT_CHROMO_ANALYSIS_20260723.csv")):
    try: clen[r["batch"]].append((int(r["frame"]), float(r["length_um"])))
    except Exception: pass
xs, ys = [], []
for b in sorted({r["batch"] for r in M if r["label"] == "polar"}):
    sel = [tension(r) for r in M if r["batch"] == b and r["label"] == "polar" and tension(r) is not None]
    if len(sel) < 3 or b not in clen: continue
    xs.append(sorted(clen[b])[0][1]); ys.append(float(np.median(sel)))
if len(xs) >= 6:
    xs = np.array(xs); ys = np.array(ys)
    rho, pv = st.spearmanr(xs, ys); rr, pp = st.pearsonr(xs, ys)
    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    ax.scatter(xs, ys, s=52, color=COL["polar"], alpha=0.85, edgecolor="white", lw=0.4)
    bb, aa = np.polyfit(xs, ys, 1); xf = np.linspace(xs.min(), xs.max(), 20)
    ax.plot(xf, aa + bb*xf, "--", color=COL["polar"], lw=1.8)
    ax.text(0.98, 0.98, f"Spearman rho={rho:.2f}, p={pv:.2g}\nPearson r={rr:.2f}, p={pp:.2g}\nN={len(xs)} polar cells",
            transform=ax.transAxes, ha="right", va="top", fontsize=7.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("sisterless chromosome length (µm)"); ax.set_ylabel("polar-KT " + TEN_LAB)
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_title(f"Chromosome length vs polar-KT tension — METAPHASE ONLY ({'relationship' if pv < 0.05 else 'no relationship'})",
                 loc="left", fontweight="bold", fontsize=10)
    save(fig, "G6tenM_chromolen_vs_tension", "chromosome length vs polar KT spindle-axis distortion (metaphase only)",
         header=["batch", "chromo_len_um", "spindle_strain"],
         rows=[[b, round(float(x), 4), round(float(y), 5)] for b, x, y in
               zip(sorted({r["batch"] for r in M if r["label"] == "polar"} & set(clen)), xs, ys)]
         if len(xs) == len(sorted({r["batch"] for r in M if r["label"] == "polar"} & set(clen))) else None)

    # ── ITEM 7 (user 2026-08-04) ──────────────────────────────────────────────────────────────────
    # "Very surprising — I'd expect longer chromosomes to have higher relative k-k tension. What differs
    # between short and long polar chromosomes that could explain how this value stays the same despite the
    # arm-size difference (path length, distance from the plate, etc.)?"
    # Approach: for the SAME polar cells, test whether chromosome length predicts the candidate covariates
    # she names. If length buys a longer arm but ALSO a proportionally greater distance from the plate (or a
    # longer travelled path), the pull per unit length — which is what equivalent k-k measures — can stay flat.
    _cand = {}
    _LM = list(csv.DictReader(open(f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv")))
    _meta_lm = [r for r in _LM if r.get("label") == "polar" and in_meta(r.get("batch"), num(r, "t_sec"))]
    for _key, _lab in [("dist_to_plate_um", "distance from metaphase plate (µm)"),
                       ("R_toward_um", "toward-plate reach (µm)"),
                       ("major_um", "KT major-axis length (µm)"),
                       ("aspect_ratio", "KT aspect ratio (stretch)"),
                       ("speed_um_s", "KT speed (µm/s)")]:
        _per = collections.defaultdict(list)
        for r in _meta_lm:
            v = num(r, _key)
            if v is not None: _per[r["batch"]].append(v)
        _cand[_key] = (_lab, {b: float(np.median(v)) for b, v in _per.items() if len(v) >= 3})
    # per-cell chromosome length, same definition as the main panel
    _len_by = {b: sorted(clen[b])[0][1] for b in clen}
    _cells = sorted({r["batch"] for r in M if r["label"] == "polar"})
    _res = []
    for _key, (_lab, _mp) in _cand.items():
        _bb = [b for b in _cells if b in _mp and b in _len_by]
        if len(_bb) >= 6:
            _x = np.array([_len_by[b] for b in _bb]); _y = np.array([_mp[b] for b in _bb])
            _r, _p = st.spearmanr(_x, _y)
            _res.append((_key, _lab, float(_r), float(_p), len(_bb)))
    if _res:
        _res.sort(key=lambda t: -abs(t[2]))
        print("  ITEM 7 covariates vs chromosome length (polar cells, metaphase):")
        for _k, _l, _r, _p, _n in _res:
            print(f"    {_l:38s} rho={_r:+.2f}  p={_p:.3g}  N={_n}")
        _ncol = min(len(_res), 3)
        fig, axs = plt.subplots(1, _ncol, figsize=(4.5*_ncol, 4.4), squeeze=False)
        for _ax, (_k, _l, _r, _p, _n) in zip(axs[0], _res[:_ncol]):
            _mp = _cand[_k][1]
            _bb = [b for b in _cells if b in _mp and b in _len_by]
            _x = np.array([_len_by[b] for b in _bb]); _y = np.array([_mp[b] for b in _bb])
            _ax.scatter(_x, _y, s=46, color=COL["polar"], alpha=.85, edgecolor="white", lw=.4)
            if len(_x) >= 4:
                _b2, _a2 = np.polyfit(_x, _y, 1); _xf = np.linspace(_x.min(), _x.max(), 20)
                _ax.plot(_xf, _a2 + _b2*_xf, "--", color=COL["polar"], lw=1.6)
            _ax.set_xlabel("sisterless chromosome length (µm)"); _ax.set_ylabel(_l)
            _ax.set_title(f"rho={_r:+.2f}, p={_p:.3g}, N={_n}", loc="left", fontsize=9, fontweight="bold")
        _sig = [t for t in _res if t[3] < 0.05]
        fig.suptitle(
            "ITEM 7 — why can equivalent k–k tension stay flat as chromosome length rises?\n"
            "Equivalent k–k measures the pull ACROSS the kinetochore, not the total force on the arm. These are the "
            "covariates that DO scale with length in the same polar cells"
            + ("; " + "; ".join(f"{t[1]} rho={t[2]:+.2f} (p={t[3]:.2g})" for t in _sig)
               if _sig else " — none reached p<0.05, so length buys no measured geometric change either."),
            x=.01, ha="left", fontweight="bold", fontsize=8.5)
        save(fig, "G6tenM_chromolen_covariates",
             "What scales with chromosome length in polar cells, if equivalent k-k tension does not (item 7)",
             header=["covariate", "spearman_rho", "p", "N"],
             rows=[[_l, round(_r, 4), float(_p), _n] for _k, _l, _r, _p, _n in _res])

# ── 499M · polar relative-tension timelines, metaphase only ───────────────────────────────────────
# "Relative tension" keeps its exact meaning — the polar kinetochore's load expressed as a multiple of
# what a normal metaphase sister carries — but both halves of that ratio are now the same measurement.
# It used to be (fitted constant) / (median measured k-k in um), which is a ratio of two different things.
LOAD_BASELINE = float(np.median([tension(r) for r in M
                                 if r["label"] == "paired" and tension(r) is not None]))
print(f"paired metaphase baseline distortion = {LOAD_BASELINE:.3f}")
tl = collections.defaultdict(list)
for r in M:
    if r["label"] != "polar" or tension(r) is None: continue
    t = tmin(r["batch"], num(r, "t_sec"))
    if t is not None:
        tl[r["batch"]].append((t, tension(r) / LOAD_BASELINE))
if tl:
    # 🔴 HER 2026-08-19, board 7 item 5: *"I've told you this before at least 5 times but the two plots that
    # I copied below for your reference, if data from different 'sets' is being plotted on it like data from
    # both 1 and 3 sisterlss kientochores, you absolutely cannot plot those as one homogenous group as is
    # currently being done."* The violin beside it was split by ablation number; THIS one was not -- every
    # cell was drawn in one colour, so single and triple were indistinguishable. Colour per ablation number,
    # using the same ABL_COL the rest of this file uses, and count the cells per group in the title.
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    _per_grp = collections.Counter()
    for b, v in tl.items():
        v = sorted(v)
        _n = nsis_batch(b)
        _c = ABL_COL.get(_n, COL["polar"])
        _per_grp[_n] += 1
        ax.plot([p[0] for p in v], [p[1] for p in v], "-", color=_c, lw=1.0, alpha=0.6)
    for _n in sorted(_per_grp):
        if _n in ABL:
            ax.plot([], [], "-", color=ABL_COL[_n], lw=2.0, label=f"{ABL[_n][2]} (n={_per_grp[_n]} cells)")
    # 🔴 HER 2026-08-25 item 1: *"G6tenM_polar_tension_timelines: add trendlines"*. One per ablation group,
    # built PER CELL (trendlib.trend_percell_mean_sem: each cell interpolated onto the shared grid strictly
    # inside its own measured range, then averaged across cells) so neighbouring points share their cells
    # and the line cannot zigzag from changing composition. Capped at that group's median metaphase
    # duration, the same cap the dashed lines mark.
    try:
        from trendlib import trend_percell_mean_sem as _tp, sem_band as _sb
        for _n in sorted(_per_grp):
            if _n not in ABL: continue
            _p3 = [(p[0], p[1], b) for b, v in tl.items() if nsis_batch(b) == _n for p in sorted(v)]
            _md = MEDIAN_META.get(_n)
            if not _p3 or not _md: continue
            _bx, _by, _bs, _bn = _tp(_p3, _md, start=0.0)
            if len(_bx) >= 2:
                _sb(ax, _bx, _by, _bs, ABL_COL[_n])
                ax.plot(_bx, _by, "-", color=ABL_COL[_n], lw=3.0, marker="o", ms=4.5, zorder=5)
                ax.plot(_bx, _by, "-", color="white", lw=4.6, zorder=4)   # halo so it reads over the traces
                ax.plot(_bx, _by, "-", color=ABL_COL[_n], lw=3.0, marker="o", ms=4.5, zorder=5)
    except Exception as _e:
        print("trendline skipped:", _e)
    if _per_grp: ax.legend(fontsize=7.5)
    ax.axhline(1.0, ls=":", color="#999"); ax.axvline(0, ls="--", color="#666", lw=1.0)
    ax.set_xlabel("minutes from metaphase onset (metaphase window only)")
    ax.set_ylabel("Relative distortion")
    ax.set_title("Polar-KT relative tension over METAPHASE, per cell   ·   "
                 + ", ".join(f"{ABL[k][2]} n={v}" for k, v in sorted(_per_grp.items()) if k in ABL),
                 loc="left", fontweight="bold", fontsize=9.5)
    save(fig, "G6tenM_polar_tension_timelines", "polar relative distortion timelines, spindle axis (metaphase only)")

    # per-cell grid
    bs = sorted(tl); ncol = 5; nrow = int(np.ceil(len(bs)/ncol))
    fig, axs = plt.subplots(nrow, ncol, figsize=(2.5*ncol, 1.9*nrow), sharex=True, sharey=True)
    axs = np.atleast_2d(axs)
    for i, b in enumerate(bs):
        a2 = axs[i//ncol][i % ncol]; v = sorted(tl[b])
        a2.plot([p[0] for p in v], [p[1] for p in v], "-", color=COL["polar"], lw=1.2)
        a2.axhline(1.0, ls=":", color="#999", lw=0.8)
        # USER 2026-08-04: "on each individual plot mark metaphase onset (0s) and anaphase onset".
        # 0 is metaphase onset; the cell's anaphase onset is the right edge of its own window.
        a2.axvline(0, ls="--", color="#3b6fb6", lw=0.9)
        _mt, _at = ph.get(b, (None, None))
        if _mt is not None and _at is not None:
            a2.axvline((_at - _mt) / 60.0, ls="--", color="#d1495b", lw=0.9)
        a2.set_title(b[:26], fontsize=6)
        a2.tick_params(labelsize=6)
    for j in range(len(bs), nrow*ncol):
        axs[j//ncol][j % ncol].axis("off")
    fig.suptitle("Polar-KT relative distortion over METAPHASE — per cell   "
                 "(blue = metaphase onset, red = anaphase onset)", fontsize=10, fontweight="bold")
    save(fig, "G6tenM_polar_tension_timelines_grid", "polar relative distortion per cell, spindle axis (metaphase only); blue = metaphase onset, red = anaphase onset")

# ── NEW 2026-08-05 · per-cell polar/paired distortion ratio ───────────────────────────────────────
# USER: "look at the outlines for paired sisters and the k-k distance between them, and then look at the
# outline for a polar and compare the tension its under based on its distortion relative to the distortion
# of the paired."
#
# This is the cleanest form of that comparison, and it is the headline result of the family. Each cell
# supplies BOTH its own polar kinetochore and its own paired sisters, measured on the same per-frame plate
# normal, so the cell is its own control — imaging conditions, plate quality, cell geometry and tracing
# style all cancel. A pooled polar-vs-paired violin cannot do that: cells contribute unequal numbers of
# frames, so it is partly a comparison between cells.
_pp = collections.defaultdict(lambda: collections.defaultdict(list))
for r in M:
    v = tension(r)
    if v is not None and r["label"] in ("polar", "paired"):
        _pp[r["batch"]][r["label"]].append(v)
_rat = [(b, float(np.median(d["polar"])), float(np.median(d["paired"])), NSIS.get(b, ""))
        for b, d in _pp.items() if len(d.get("polar", [])) >= 4 and len(d.get("paired", [])) >= 4]
if len(_rat) >= 5:
    _rv = [p / q for _b, p, q, _n in _rat]
    _w = st.wilcoxon([x - 1 for x in _rv])[1]
    _above = sum(1 for x in _rv if x > 1)
    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    for i, (b, p_, q_, n_) in enumerate(sorted(_rat, key=lambda z: z[1] / z[2])):
        c = ABL_COL.get(n_, "#888")
        ax.plot([0, 1], [q_, p_], "-", color=c, lw=1.0, alpha=0.65, zorder=1)
        ax.scatter([0], [q_], s=40, color=COL["paired"], edgecolor="white", lw=.5, zorder=3)
        ax.scatter([1], [p_], s=40, color=COL["polar"], edgecolor="white", lw=.5, zorder=3)
    ax.hlines(np.median([q for _b, _p, q, _n in _rat]), -0.3, 0.3, color=COL["paired"], lw=2.6, zorder=4)
    ax.hlines(np.median([p for _b, p, _q, _n in _rat]), 0.7, 1.3, color=COL["polar"], lw=2.6, zorder=4)
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["paired sisters\n(same cell)", "polar KT\n(same cell)"], fontsize=9.5)
    ax.set_ylabel("kinetochore " + TEN_LAB)
    ax.set_title("Polar kinetochores are more DISTORTED along the spindle axis than the paired sisters\n"
                 f"in their own cell — median {np.median(_rv):.2f}x, higher in {_above} of {len(_rat)} cells, "
                 f"Wilcoxon p={_w:.2g}   (line colour: green = single, purple = triple)",
                 loc="left", fontweight="bold", fontsize=9)
    ax.text(0.0, -0.145,
            "One line per cell, each cell its own control: same movie, same plate fit, same tracing. "
            "Distortion is dimensionless and NOT converted to k-k —\npaired distortion does not predict "
            "that pair's measured k-k (pooled r=+0.08, within-cell rho=+0.015), so no calibration to "
            "micrometres is claimed.",
            transform=ax.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.5)
    save(fig, "G6tenM_polar_vs_paired_percell",
         "per-cell polar/paired spindle-axis distortion ratio (each cell its own control)",
         header=["batch", "n_sisterless", "polar_distortion", "paired_distortion", "ratio"],
         rows=[[b, n_, round(p_, 4), round(q_, 4), round(p_ / q_, 4)] for b, p_, q_, n_ in _rat])
    print(f"  PER-CELL polar/paired distortion: median {np.median(_rv):.2f}x, "
          f"above 1 in {_above}/{len(_rat)} cells, Wilcoxon p={_w:.3g}")
    for _g in ("1", "3"):
        _v = [p / q for _b, p, q, n_ in _rat if n_ == _g]
        if len(_v) >= 3:
            print(f"    {ABL[_g][2]}: n={len(_v)} cells, median ratio={np.median(_v):.2f}")
else:
    print(f"  PER-CELL polar/paired distortion: only {len(_rat)} cells have both series")

print("done metaphase tension twins")
