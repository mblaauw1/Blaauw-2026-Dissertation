#!/usr/bin/env python3
"""Periodic 'stretch and retreat' + a formal predictive-signal test (user 2026-07-23).
Per tracked KT: Lomb-Scargle periodogram (handles the irregular t_sec) of the toward-plate reach R_toward
and of aspect ratio -> dominant oscillation period; oscillation amplitude. Predictive: does a shape change
LEAD anaphase? Per polar track, slope of circularity / aspect over the last PRE_MIN minutes before anaphase,
tested against 0 (Wilcoxon), and shape-change magnitude vs metaphase duration."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
from scipy.signal import lombscargle
import lib, kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
PMIN, PMAX = 30.0, 600.0     # search oscillation periods 30 s .. 10 min
PRE_MIN = 6.0                # window before anaphase for the predictive slope

R = list(csv.DictReader(open(SRC[0])))
def num(r, k):
    try: return float(r[k])
    except Exception: return None
by_track = collections.defaultdict(list)
for r in R:
    by_track[r["track_id"]].append(r)
for t in by_track:
    by_track[t].sort(key=lambda r: (int(r["frame"]), num(r, "t_sec") or 0))
lab_of = {t: rs[0]["label"] for t, rs in by_track.items()}


def dominant_period(ts, ys):
    ts = np.asarray(ts, float); ys = np.asarray(ys, float)
    m = np.isfinite(ts) & np.isfinite(ys)
    ts, ys = ts[m], ys[m]
    if len(ts) < 8 or (ts.max() - ts.min()) < 2 * PMIN:
        return None, None
    ys = ys - ys.mean()
    if ys.std() == 0:
        return None, None
    periods = np.linspace(PMIN, min(PMAX, (ts.max() - ts.min())), 400)
    ang = 2 * np.pi / periods
    pg = lombscargle(ts, ys, ang, normalize=True)
    k = int(np.argmax(pg))
    return float(periods[k]), float(pg[k])


def _save(fig, name, cap, key="label", header=None, rows=None):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # 2026-08-03: was record_plot(["x"], []) - a placeholder registering an EMPTY data table, so the
    # figure could not be checked against its own data and any _zoom companion was built from nothing.
    # Same bug fixed in kt_phase_split.py on 2026-07-29 and never propagated here.
    try:
        lib.record_plot(name, header or ["x"], rows or [], {"family": "oscillation"},
                        script=__file__, caption=cap, source=SRC,
                        key_column=(key if header and key in header else None))
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (name, _e))
    print("  " + name)


if __name__ == "__main__":
    # 1) example traces: 4 longest polar tracks, aspect + R_toward over time
    # ITEM 4 (user 2026-08-04): "is aspect and movement as shown in these traces correlated? If plotted for a
    # paired sister kinetochore, does it correlate as well? More or less?" -> compute the WITHIN-TRACK
    # Spearman(aspect, R_toward) for every track, print it on each example panel, and compare the polar and
    # paired distributions on the figure (Mann-Whitney). Per her standing preference this ANNOTATES the
    # existing figure rather than spawning another one.
    def asp_move_rho(rs):
        a = [num(r, "aspect_ratio") for r in rs]; m = [num(r, "R_toward_um") for r in rs]
        pair = [(x, y) for x, y in zip(a, m) if x is not None and y is not None]
        if len(pair) < 6: return None
        xa = np.array([p[0] for p in pair]); ym = np.array([p[1] for p in pair])
        if xa.std() == 0 or ym.std() == 0: return None
        return float(st.spearmanr(xa, ym).statistic)

    rho_by_state = {"polar": [], "paired": []}
    for t, rs in by_track.items():
        lb = lab_of[t]
        if lb in rho_by_state:
            rv = asp_move_rho(rs)
            if rv is not None: rho_by_state[lb].append(rv)

    # USER 2026-08-04: "which are polar and which are sisters? Should probably be two of each."
    # The figure previously showed the 4 longest POLAR tracks only, with nothing on the panel saying so -
    # so the paired-sister comparison quoted in the caption had no example to look at. Take the 2 longest
    # of each state and label every panel with its state.
    _pol_tracks   = sorted([t for t in by_track if lab_of[t] == "polar"],  key=lambda t: -len(by_track[t]))[:2]
    _pair_tracks  = sorted([t for t in by_track if lab_of[t] == "paired"], key=lambda t: -len(by_track[t]))[:2]
    polar = _pol_tracks + _pair_tracks          # kept named `polar` - the data CSV below iterates it
    _STATE_OF = {t: "POLAR" for t in _pol_tracks}
    _STATE_OF.update({t: "PAIRED (sisters)" for t in _pair_tracks})
    _STATE_COL = {"POLAR": "#7a2fa0", "PAIRED (sisters)": "#0a7d55"}
    print(f"  example traces: {len(_pol_tracks)} polar + {len(_pair_tracks)} paired")
    fig, axs = plt.subplots(2, 2, figsize=(11, 6.4))
    for ax, t in zip(axs.flat, polar):
        rs = by_track[t]
        ts = np.array([num(r, "t_sec") for r in rs]) / 60.0
        asp = np.array([num(r, "aspect_ratio") for r in rs])
        rt = np.array([num(r, "R_toward_um") for r in rs])
        ax.plot(ts, asp, "-o", ms=2, color="#e6820e", label="aspect")
        ax2 = ax.twinx(); ax2.plot(ts, rt, "-s", ms=2, color="#3b6fb6", alpha=0.7, label="R_toward")
        per, pw = dominant_period([num(r, "t_sec") for r in rs], [num(r, "aspect_ratio") for r in rs])
        _rv = asp_move_rho(rs)
        _rtxt = f" · aspect~R_toward rho={_rv:+.2f}" if _rv is not None else ""
        _st_lbl = _STATE_OF.get(t, "?")
        ax.set_title(f"{_st_lbl}\n"
                     + (f"{t.split('|')[0][:22]} · period≈{per:.0f}s" if per else t.split('|')[0][:22]) + _rtxt,
                     fontsize=8, color=_STATE_COL.get(_st_lbl, "#333"), fontweight="bold")
        for _sp in ax.spines.values():
            _sp.set_edgecolor(_STATE_COL.get(_st_lbl, "#333")); _sp.set_linewidth(1.6)
        ax.set_xlabel("time (min)"); ax.set_ylabel("aspect", color="#e6820e"); ax2.set_ylabel("R_toward µm", color="#3b6fb6")
    # ITEM 4 answer panel: the polar-vs-paired comparison of within-track aspect~movement coupling.
    _pol = rho_by_state["polar"]; _pai = rho_by_state["paired"]
    _mw = ""
    if len(_pol) >= 3 and len(_pai) >= 3:
        try:
            _u, _p = st.mannwhitneyu(_pol, _pai, alternative="two-sided")
            _mw = f"; Mann-Whitney p={_p:.3g}"
        except Exception: pass
    _dirn = ("MORE" if (_pol and _pai and abs(np.median(_pol)) > abs(np.median(_pai))) else "LESS")
    _item4 = (f"ITEM 4 — is aspect correlated with movement?  Within-track Spearman(aspect, R_toward): "
              f"POLAR median rho={np.median(_pol):+.2f} (N={len(_pol)} tracks), "
              f"PAIRED median rho={np.median(_pai):+.2f} (N={len(_pai)}){_mw}.  "
              f"Paired sisters are coupled {('LESS' if _dirn=='MORE' else 'MORE')} strongly than polar KTs."
              if _pol and _pai else "ITEM 4 — too few tracks to compare polar vs paired coupling.")
    fig.suptitle("Kinetochore stretch/retreat traces (aspect + toward-plate reach) — 2 POLAR (purple) vs "
                 "2 PAIRED SISTER (green) tracks\n" + _item4,
                 fontweight="bold", fontsize=9.5)
    # USER 2026-08-03: "what are these traces (what does aspect / toward plate reach mean for kinetochores)".
    # Each panel is ONE tracked polar kinetochore over time, not a group summary - so say that, and define both
    # y-axes in the units a reader can check.
    fig.text(0.005, -0.03,
             "EACH PANEL IS ONE TRACKED KINETOCHORE over mitotic time — the 2 longest POLAR tracks (purple "
             "frame/title) and the 2 longest PAIRED-SISTER tracks (green frame/title). The panel title gives "
             "the track's state, its cell, and its dominant oscillation period.\n"
             "ASPECT (orange, left axis) = the traced kinetochore outline's major-axis length / minor-axis "
             "length. 1.0 = round; higher = more elongated, i.e. the kinetochore is STRETCHED. It is a shape "
             "measure and carries no direction.\n"
             "R_toward (blue, right axis, um) = how far the outline REACHES toward the metaphase plate, "
             "measured from the kinetochore's own centroid to its leading edge along the direction of the "
             "nearest point on the plate. It is a reach/position measure, so it rises when the kinetochore "
             "extends plate-ward and falls when it retreats.\n"
             "Read together: aspect and R_toward rising in step = the kinetochore is stretching toward the "
             "plate; aspect rising while R_toward falls = it is elongating away from the plate. Both are "
             "computed per frame from the manual outline raster in kt_landmark_analysis.py.",
             fontsize=6.8, color="#444", ha="left", va="top", linespacing=1.5)
    _save(fig, "G6osc_example_traces", "Polar stretch/retreat traces",
          header=["track_id","t_min","aspect_ratio","R_toward_um"],
          rows=[[t, round(float(num(r,"t_sec"))/60.0,4), round(float(num(r,"aspect_ratio")),5),
                 round(float(num(r,"R_toward_um")),5)]
                for t in polar for r in by_track[t]
                if num(r,"t_sec") is not None and num(r,"aspect_ratio") is not None and num(r,"R_toward_um") is not None])

    # 2) dominant oscillation period by state
    g = {k: [] for k in COL}
    # A track whose label is not one of the three plotted states (she can tag a trace `other`, `unaligned`,
    # `sisterless`... in the slides) must be SKIPPED, not indexed into `g` — that raised KeyError('other')
    # on 2026-08-03 the moment 28 `other` traces appeared. Report the skip: silently dropping annotated
    # traces is exactly how a figure comes to under-represent her data without anyone noticing.
    skipped = {}
    for t, rs in by_track.items():
        lab = lab_of[t]
        if lab not in g:
            skipped[lab] = skipped.get(lab, 0) + 1
            continue
        per, pw = dominant_period([num(r, "t_sec") for r in rs], [num(r, "aspect_ratio") for r in rs])
        if per and pw and pw > 0.25:   # require a non-trivial peak
            g[lab].append(per)
    if skipped:
        print("  NOTE: tracks skipped, label not plotted here: "
              + ", ".join(f"{v} {k}" for k, v in sorted(skipped.items())))
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    # ITEM 5 (user 2026-08-04): remove the LAGGING group from the period plot. A lagging kinetochore is an
    # anaphase-window object, so its "oscillation period" is measured over a different phase from the
    # metaphase paired/polar tracks and is not comparable. Amplitude plot below is unchanged (not asked).
    PERIOD_ORDER = [k for k in COL if k != "lagging"]
    order = PERIOD_ORDER
    dmax = max((max(g[k]) for k in order if g[k]), default=PMAX)
    for i, k in enumerate(order):
        d = g[k]
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, COL[k], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[k], alpha=0.6, lw=0)
        ax.hlines(np.median(d), i-0.3, i+0.3, color=COL[k], lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.0f}s\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9); ax.set_ylabel("dominant oscillation period (s)")
    # with lagging gone there are only 2 columns, so the upper-right stats box landed on top of the polar
    # "med/N" caption — move it left and add headroom so both stay readable.
    ax.set_ylim(top=dmax * 1.22)
    kt_stats.add_group_stats(ax, {k: g[k] for k in order}, order, loc="upper left")
    ax.set_title("Stretch oscillation period by state (Lomb–Scargle on aspect)", loc="left", fontweight="bold", fontsize=10)
    _save(fig, "G6osc_period_by_state", "Oscillation period by state",
          header=["label","dominant_period_s"], rows=[[k, round(float(v),3)] for k in order for v in g.get(k, [])])

    # 3) oscillation amplitude (detrended CV of aspect) by state
    order = [k for k in COL]        # amplitude keeps all three states (item 5 applied to the period plot only)
    ga = {k: [] for k in COL}
    for t, rs in by_track.items():
        if lab_of[t] not in ga:      # same non-plotted-label guard as above
            continue
        asp = np.array([num(r, "aspect_ratio") for r in rs if num(r, "aspect_ratio") is not None])
        if len(asp) >= 6 and asp.mean() > 0:
            ga[lab_of[t]].append(float(np.std(asp) / asp.mean()))
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    dmax = max((max(v) for v in ga.values() if v), default=1)
    for i, k in enumerate(order):
        d = ga[k]
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, COL[k], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[k], alpha=0.6, lw=0)
        ax.hlines(np.median(d), i-0.3, i+0.3, color=COL[k], lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9); ax.set_ylabel("aspect-ratio CV (oscillation amplitude)")
    kt_stats.add_group_stats(ax, ga, order, loc="upper right")
    ax.set_title("Stretch oscillation amplitude by state", loc="left", fontweight="bold", fontsize=10.5)
    _save(fig, "G6osc_amplitude_by_state", "Oscillation amplitude by state",
          header=["label","aspect_cv"], rows=[[k, round(float(v),5)] for k in order for v in ga.get(k, [])])
    # 4) PREDICTIVE: slope of circularity / aspect over the last PRE_MIN before anaphase, per polar track
    ana = {}
    for r in R:
        if r["phase"] == "anaphase" and r["batch"] not in ana:
            t = num(r, "t_sec")
            if t is not None: ana[r["batch"]] = t
    for metric, name, ttl in [("circularity", "G6pred_preanaphase_circ_slope", "Pre-anaphase circularity slope (polar)"),
                              ("aspect_ratio", "G6pred_preanaphase_aspect_slope", "Pre-anaphase stretch slope (polar)")]:
        slopes = []
        slope_rows = []          # (track_id, slope) -> the figure's data table; see _save note below
        for t, rs in by_track.items():
            if lab_of[t] != "polar": continue
            b = rs[0]["batch"]
            # USER 2026-08-10: standing cohort exclusion (prophase / drug / metaphase-abl / 4-sis / Mad1).
            if lib.plot_excluded(b) or lib.is_mad1(b): continue
            if b not in ana: continue
            xs, ys = [], []
            for r in rs:
                tt = num(r, "t_sec"); v = num(r, metric)
                if tt is None or v is None: continue
                rel = (tt - ana[b]) / 60.0
                if -PRE_MIN <= rel <= 0:
                    xs.append(rel); ys.append(v)
            if len(xs) >= 4:
                sl = np.polyfit(xs, ys, 1)[0]   # per minute
                slopes.append(sl); slope_rows.append([t, b, round(float(sl), 6), len(xs)])
        fig, ax = plt.subplots(figsize=(6.0, 5.0))
        if slopes:
            ax.hist(slopes, bins=12, color=COL["polar"], alpha=0.8, edgecolor="white")
            ax.axvline(0, ls="--", color="#333")
            try: W, p = st.wilcoxon(slopes)
            except Exception: p = np.nan
            ax.text(0.98, 0.98, f"N tracks={len(slopes)}\nmedian slope={np.median(slopes):+.3f}/min\nWilcoxon vs 0: p={p:.2g}",
                    transform=ax.transAxes, ha="right", va="top", fontsize=7.5, family="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
        ax.set_xlabel(f"{metric} slope over last {PRE_MIN:.0f} min before anaphase (/min)"); ax.set_ylabel("# polar tracks")
        ax.set_title(ttl, loc="left", fontweight="bold", fontsize=10.5)
        # 2026-08-03: these two were the last `_save` calls still passing NO data, so they registered an
        # EMPTY table while the figure itself drew ~19 tracks. A figure with no data CSV rows is invisible
        # to every downstream audit (NOTES §8) - pass the slopes.
        _save(fig, name, ttl, key="track_id",
              header=["track_id", "batch", f"{metric}_slope_per_min", "n_points"], rows=slope_rows)
    print("done oscillation+predictive")
