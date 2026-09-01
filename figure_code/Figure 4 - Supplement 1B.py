#!/usr/bin/env python3
"""Track / landmark / phase figure family (NEW 2026-07-23). Reads KT_LANDMARK_ANALYSIS_20260723.csv
(per tracked KT per frame, plate-anchored) + KT_OUTLINE_TRACKS_20260723.csv. Answers the user's set:
perimeter + distance-to-plate by state; speed by mitotic phase; post-anaphase poleward speed; distance
traveled (total + per-20s); fracture count; shape vs time-to-anaphase (predictive); chromosome-length
correlations; stretch DIRECTION relative to the plate; and the landmark descriptors (vase / asymmetry /
anisotropy). All saved to group6_tracks/ -> lib savefig emits the deck PDF; each registered via record_plot."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as st
import lib
import kt_stats
lib.apply_style()

ROOT = "/Volumes/4 MB"
csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"; os.makedirs(OUT, exist_ok=True)
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv", f"{ROOT}/annotations/kt_outlines.csv"]
SCRIPT = __file__

R = list(csv.DictReader(open(f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv")))
R = [r for r in R if not lib.is_prophase_ablation(r.get("batch",""))]   # prophase excluded (no prophase group)
def num(r, k):
    v = r.get(k, "")
    try: return float(v)
    except Exception: return None

LAB = ["paired", "polar", "lagging"]
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
PHASE = ["prometaphase", "metaphase", "anaphase"]
PHCOL = {"prometaphase": "#7a7a7a", "metaphase": "#3b6fb6", "anaphase": "#d1495b"}

# ITEM 11 (user 2026-08-04): the phase-matching rule is PER STATE, not one phase for everybody.
#   paired / polar  -> use only rows from that cell's METAPHASE
#   lagging         -> use only rows from ANAPHASE
# Rationale (hers): "paired" and "polar" are metaphase descriptions of a kinetochore's behaviour, whereas a
# kinetochore can only be scored "lagging" after anaphase onset. The 2026-08-03 fix restricted the
# distance-to-plate figure to anaphase for ALL THREE states, which fixed the lagging comparison but pushed
# paired/polar into a window where those labels no longer describe what the KT is doing.
PHASE_BY_LABEL = {"paired": "metaphase", "polar": "metaphase", "lagging": "anaphase"}
def phase_matched(r):
    """True if this row is in the phase where its own state label is meaningful."""
    want = PHASE_BY_LABEL.get(r.get("label"))
    return want is None or r.get("phase") == want
PHASE_MATCH_NOTE = ("phase-matched: paired & polar measured during METAPHASE, lagging during ANAPHASE — "
                    "each state scored in the window where that label describes the kinetochore")


def _violin(ax, groups, order, cols, fmt="{:.2f}", label_own_max=False):
    """label_own_max: place each group's med/N label just above ITS OWN max instead of the shared dmax row.
    Needed for G6trk_dist_to_plate (2026-08-03 item-1 fix): once lagging is restricted to anaphase-only its
    max drops well below paired/polar's, so the old shared-height label row sits right under the upper-right
    kt_stats box and the two overlap. Default False keeps every other _violin caller's layout unchanged."""
    dmax = max((max(g) for g in groups.values() if g), default=1)
    for i, k in enumerate(order):
        d = [v for v in groups.get(k, []) if v is not None and np.isfinite(v)]
        if not d: continue
        c = cols[k]
        lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0, min_n=6)
        jit = (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.2
        ax.scatter(np.full(len(d), i) + jit, d, s=8, color=c, alpha=0.4, edgecolor="white", linewidth=0.2, zorder=3)
        med = float(np.median(d))
        ax.hlines(med, i - 0.34, i + 0.34, color=c, lw=2.4, zorder=4)
        ytxt = (max(d) * 1.05) if label_own_max else (dmax * 1.02)
        ax.text(i, ytxt, f"med {fmt.format(med)}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9)
    # 2026-08-04: at 1.25 the upper-right statistics box landed on the "med / N=" labels above the
    # right-hand violins (visible on G6trk_dist_to_plate, _distance_per20s and _distance_total). The labels
    # sit at ~1.02-1.05 of the data max, so the axis needs enough headroom for both.
    ax.set_ylim(top=dmax * 1.45)
    kt_stats.add_group_stats(ax, {k: groups.get(k, []) for k in order}, order, loc="upper right")


def violin_by_state(metric, ylabel, title, outname, labels=LAB, rowfilter=None, fmt="{:.2f}", label_own_max=False):
    g = {k: [] for k in labels}
    for r in R:
        if r["label"] in g and (rowfilter is None or rowfilter(r)):
            v = num(r, metric)
            if v is not None: g[r["label"]].append(v)
    fig, ax = plt.subplots(figsize=(6.8, 5.0))
    _violin(ax, g, labels, COL, fmt, label_own_max=label_own_max)
    p = _kw([g[k] for k in labels if len(g[k]) >= 3])
    ax.set_ylabel(ylabel); ax.set_title(title + (f"   ({p})" if p else ""), loc="left", fontweight="bold", fontsize=10.5)
    # BUGFIX (2026-08-03, found while adding the anaphase-only rowfilter for G6trk_dist_to_plate): this used
    # to record ALL rows with a valid `metric`, ignoring `rowfilter` entirely -- harmless while no caller
    # passed a rowfilter, but now that one does, the recorded CSV must match what's actually drawn or the
    # provenance is lying about the figure's own data (same class of problem as the empty-CSV systemic finding
    # in REVIEW_MESSAGE2_IDENTIFICATION.md).
    _save(fig, outname, ["label", metric],
          [[r["label"], num(r, metric)] for r in R if num(r, metric) is not None and (rowfilter is None or rowfilter(r))],
          title)


def _kw(groups):
    gs = [np.asarray(g, float) for g in groups if len(g) >= 3]
    if len(gs) < 2: return ""
    try:
        H, p = (st.kruskal(*gs) if len(gs) >= 3 else st.mannwhitneyu(gs[0], gs[1]))
        return f"Kruskal p={p:.2g}" if len(gs) >= 3 else f"MW p={p:.2g}"
    except Exception: return ""


def _save(fig, outname, header, rows, title, key="label"):
    fig.tight_layout(); fig.savefig(f"{OUT}/{outname}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try:
        lib.record_plot(outname, header, [x for x in rows if x is not None], {"family": "tracks"},
                        script=SCRIPT, caption=title, source=SRC, key_column=key)
    except Exception as e:
        print("  record_plot warn", outname, e)
    print("  " + outname)


# per-track aggregates
def tracks():
    by = collections.defaultdict(list)
    for r in R:
        by[r["track_id"]].append(r)
    for tid in by:
        by[tid].sort(key=lambda r: (int(r["frame"]), num(r, "t_sec") or 0))
    return by


def speed_by_phase(outname):
    """Kinetochore centroid speed by mitotic phase, per state. Highlights poleward motion after anaphase."""
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    xs = []; xt = []
    pos = 0
    csv_rows = []
    for lab in LAB:
        for ph in PHASE:
            d = [num(r, "speed_um_s") for r in R if r["label"] == lab and r["phase"] == ph and num(r, "speed_um_s") is not None]
            d = [v * 60 for v in d if v is not None]  # um/min
            if len(d) >= 3:
                lib.journal_violin(ax, d, pos, PHCOL[ph], alpha=0.28, lw=1.0, min_n=6)
                jit = (np.random.RandomState(int(round(pos * 10))).rand(len(d)) - 0.5) * 0.2
                ax.scatter(np.full(len(d), pos) + jit, d, s=7, color=PHCOL[ph], alpha=0.4, edgecolor="white", lw=0.2, zorder=3)
                ax.hlines(np.median(d), pos - 0.34, pos + 0.34, color=PHCOL[ph], lw=2.2, zorder=4)
                ax.text(pos, max(d) * 1.02, f"{np.median(d):.1f}\nN={len(d)}", ha="center", va="bottom", fontsize=6.5)
                for v in d: csv_rows.append([lab, ph, v])
            xt.append(f"{lab}\n{ph[:5]}"); xs.append(pos); pos += 1
        pos += 0.6
    ax.set_xticks(xs); ax.set_xticklabels(xt, fontsize=7)
    ax.set_ylabel("centroid speed (µm/min)")
    ax.set_title("Kinetochore speed by mitotic phase and state", loc="left", fontweight="bold", fontsize=11)
    ax.legend(handles=[Line2D([0], [0], color=PHCOL[p], lw=3, label=p) for p in PHASE], fontsize=8)
    _save(fig, outname, ["label", "phase", "speed_um_min"], csv_rows, "Kinetochore speed by phase", key="label")


def per_track_violin(agg, ylabel, title, outname, labels=LAB, fmt="{:.2f}", perframe=None):
    by = tracks()
    g = {k: [] for k in labels}
    csv_rows = []
    for tid, rs in by.items():
        lab = rs[0]["label"]
        if lab not in g: continue
        val = agg(rs)
        if val is not None and np.isfinite(val):
            g[lab].append(val); csv_rows.append([lab, tid, val])
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    _violin(ax, g, labels, COL, fmt)
    p = _kw([g[k] for k in labels if len(g[k]) >= 3])
    ax.set_ylabel(ylabel); ax.set_title(title + (f"   ({p})" if p else ""), loc="left", fontweight="bold", fontsize=10.5)
    _save(fig, outname, ["label", "track_id", "value"], csv_rows, title, key="track_id")


def _total_dist(rs):
    d = 0; last = None
    for r in rs:
        x, y = num(r, "R_toward_um"), None  # placeholder
    # use centroid from tracks file? recompute from dist? use cx via kt_outlines tracks
    return None


def dist_traveled(outname_total, outname_rate):
    """Total path length + per-20s step, per track, from KT_OUTLINE_TRACKS centroids.

    ITEM 11 (user 2026-08-04): distance travelled must be measured in the phase where each state's label
    applies — paired/polar over METAPHASE, lagging over ANAPHASE. The outline-tracks file has no `phase`
    column, so the phase is looked up per (track_id, frame) from the landmark table, which does."""
    trk = list(csv.DictReader(open(f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv")))
    PH = {(r["track_id"], r["frame"]): r.get("phase") for r in R}
    by = collections.defaultdict(list)
    for r in trk:
        by[r["track_id"]].append(r)
    tot = {k: [] for k in LAB}; rate = {k: [] for k in LAB}
    rows_t = []; rows_r = []
    n_dropped = 0
    for tid, rs in by.items():
        rs.sort(key=lambda r: (int(r["frame"]), float(r["t_sec"]) if r["t_sec"] else 0))
        lab = rs[0]["label"]
        if lab not in tot: continue
        want = PHASE_BY_LABEL.get(lab)
        if want is not None:
            _before = len(rs)
            rs = [r for r in rs if PH.get((r["track_id"], r["frame"])) == want]
            n_dropped += _before - len(rs)
            if len(rs) < 2: continue
        D = 0; T = 0; steps = []
        for a, b in zip(rs[:-1], rs[1:]):
            try:
                dx = float(b["cx_um"]) - float(a["cx_um"]); dy = float(b["cy_um"]) - float(a["cy_um"])
                dt = float(b["t_sec"]) - float(a["t_sec"])
            except Exception:
                continue
            step = np.hypot(dx, dy); D += step; T += max(dt, 0)
            if dt > 0: steps.append(step / dt * 20.0)  # µm per 20 s
        if D > 0:
            tot[lab].append(D); rows_t.append([lab, tid, D])
        if steps:
            rate[lab].append(float(np.median(steps))); rows_r.append([lab, tid, float(np.median(steps))])
    print(f"  dist_traveled: {n_dropped} frames dropped by the per-state phase match")
    for grp, name, ylab, ttl, rws in [(tot, outname_total, "total path length (µm)", "Total distance travelled per kinetochore", rows_t),
                                      (rate, outname_rate, "median step (µm / 20 s)", "Kinetochore step size (per 20 s) by state", rows_r)]:
        fig, ax = plt.subplots(figsize=(6.4, 5.0)); _violin(ax, grp, LAB, COL)
        p = _kw([grp[k] for k in LAB if len(grp[k]) >= 3])
        ax.set_ylabel(ylab)
        ax.set_title(ttl + (f"   ({p})" if p else ""), loc="left", fontweight="bold", fontsize=10.5)
        ax.text(0.0, -0.145, PHASE_MATCH_NOTE, transform=ax.transAxes, fontsize=7, color="#555", va="top")
        _save(fig, name, ["label", "track_id", "value"], rws, ttl + " — " + PHASE_MATCH_NOTE, key="track_id")


def distance_4group(outname_rate, outname_cum):
    """USER 2026-08-05, on the G4_velocity outlier-trimmed zoom figure: "i want a version of this plot that
    is the total distance moved per kinetochore for 1 and 3 sisterless kinetochore groups over a minute ...
    you can make 4 groups ... and then make another version of the plot thats the distance covered by a
    kinetochore over time".

    Two figures from one pass over the tracks:
      * outname_rate — violin of distance travelled PER MINUTE, one point per kinetochore, four groups
        (polar & paired x single & triple). Per-minute rather than total, so a track that happens to be
        followed for longer does not read as a faster-moving kinetochore. Total path length is exactly
        what G6trk_distance_total already shows.
      * outname_cum  — CUMULATIVE distance covered by each kinetochore against time since its own first
        tracked frame, with a binned-median trendline per group. This is the "over time" version: the
        slope IS the speed, and a kinetochore that stalls shows as a flattening.

    Same phase matching as dist_traveled (paired/polar scored over metaphase, lagging over anaphase), and
    the cohort comes from the master # Sisterless KTs column."""
    trk = list(csv.DictReader(open(f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv")))
    PH = {(r["track_id"], r["frame"]): r.get("phase") for r in R}
    by = collections.defaultdict(list)
    for r in trk: by[r["track_id"]].append(r)

    rate = {}; cum = {}; rows_r = []; rows_c = []
    for lab, ns, col, ls, mk, disp in G4_SERIES:
        rate[(lab, ns)] = []; cum[(lab, ns)] = []
    for tid, rs in by.items():
        rs.sort(key=lambda r: (int(r["frame"]), float(r["t_sec"]) if r["t_sec"] else 0))
        lab = rs[0]["label"]; b = rs[0]["batch"]; ns = NSIS_KT.get(b, "")
        if (lab, ns) not in rate: continue
        want = PHASE_BY_LABEL.get(lab)
        if want is not None:
            rs = [r for r in rs if PH.get((r["track_id"], r["frame"])) == want]
        if len(rs) < 3: continue
        D = 0.0; t0 = None; track_pts = []
        for a, b_ in zip(rs[:-1], rs[1:]):
            try:
                dx = float(b_["cx_um"]) - float(a["cx_um"]); dy = float(b_["cy_um"]) - float(a["cy_um"])
                ta = float(a["t_sec"]); tb = float(b_["t_sec"])
            except Exception:
                continue
            if t0 is None: t0 = ta
            D += float(np.hypot(dx, dy))
            track_pts.append(((tb - t0) / 60.0, D))
        if not track_pts or t0 is None: continue
        span_min = track_pts[-1][0]
        if span_min <= 0.2: continue
        per_min = D / span_min
        rate[(lab, ns)].append(per_min)
        rows_r.append([b, lab, ns, tid, round(per_min, 4), round(span_min, 3), round(D, 4)])
        for tm, d in track_pts:
            cum[(lab, ns)].append((tm, d, tid))
            rows_c.append([b, lab, ns, tid, round(tm, 4), round(d, 4)])

    # ---- FIG 1: distance per minute, four violins ----
    fig, ax = plt.subplots(figsize=(7.4, 5.2)); pos = 0; xt = []; xl = []; stats_out = {}
    for lab, ns, col, ls, mk, disp in G4_SERIES:
        v = rate[(lab, ns)]
        if len(v) < 3:
            xt.append(pos); xl.append(f"{disp}\n(n={len(v)})"); pos += 1; continue
        lib.journal_violin(ax, v, pos, col, alpha=0.30, lw=1.0)
        ax.scatter(np.full(len(v), pos) + (np.random.RandomState(pos).rand(len(v)) - .5) * 0.22, v,
                   s=lib.VIOLIN_DOT_S, color=col, alpha=.85, edgecolor="white", lw=.4, zorder=3)
        ax.hlines(np.median(v), pos - .32, pos + .32, color=col, lw=2.4, zorder=4)
        ax.hlines(np.mean(v), pos - .26, pos + .26, color=col, lw=1.3, ls=(0, (2, 1.5)), zorder=4)
        ax.scatter([pos], [np.mean(v)], marker="D", s=28, facecolor="white", edgecolor=col, lw=1.2, zorder=5)
        ax.text(pos, max(v), f"med {np.median(v):.2f}\nn={len(v)}", ha="center", va="bottom", fontsize=7.5)
        stats_out[disp] = {"n_kt": len(v), "median_um_per_min": round(float(np.median(v)), 4)}
        xt.append(pos); xl.append(f"{disp}\n(n={len(v)})"); pos += 1
    ax.set_xticks(xt); ax.set_xticklabels(xl, fontsize=8)
    ax.set_ylabel("distance travelled per kinetochore (µm / min)")
    ax.set_title("Distance travelled per kinetochore, per minute — polar & paired, single & triple\n"
                 "one point per kinetochore; solid = median, dashed + diamond = mean",
                 loc="left", fontweight="bold", fontsize=9.5)
    ax.text(0.0, -0.155, PHASE_MATCH_NOTE, transform=ax.transAxes, fontsize=7, color="#555", va="top")
    _save(fig, outname_rate, ["batch", "label", "n_sisterless", "track_id", "um_per_min", "span_min", "total_um"],
          rows_r, "Distance travelled per kinetochore per minute, four groups", key="track_id")
    print("  " + outname_rate + ": " + str(stats_out))

    # ---- FIG 2: cumulative distance over time ----
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    for lab, ns, col, ls, mk, disp in G4_SERIES:
        pts = cum[(lab, ns)]
        if len(pts) < 12: continue
        xs = np.array([q[0] for q in pts]); ys = np.array([q[1] for q in pts])
        tids = np.array([q[2] for q in pts])
        ax.scatter(xs, ys, s=4, color=col, alpha=0.10, lw=0)
        hi = float(np.percentile(xs, 98))
        bins = np.linspace(0, max(hi, 1.0), 14); idx = np.digitize(xs, bins)
        # SURVIVORSHIP. A cumulative curve only rises for a given kinetochore, but the MEDIAN across
        # kinetochores can fall, because late bins are computed over a different, smaller set of tracks
        # than early ones — the first build showed paired-single dropping 35 -> 11 um at ~17 min purely
        # because its long-lived tracks happened to be slower. That is an artefact of the changing
        # denominator, not a stall. Two guards: a bin must retain at least MIN_FRAC of the group's tracks,
        # and the line stops at the last bin that qualifies rather than continuing on a thin tail.
        MIN_FRAC = 0.40; MIN_TRACKS = 4
        _all_t = len(set(tids))
        bx, bm, bn = [], [], []
        for bi in range(1, len(bins)):
            m = idx == bi
            sel = ys[m]; ntk = len(set(tids[m]))
            if len(sel) >= 4 and ntk >= MIN_TRACKS and ntk >= MIN_FRAC * _all_t:
                bx.append((bins[bi-1] + bins[bi]) / 2); bm.append(np.median(sel)); bn.append(ntk)
            else:
                break                      # stop at the first bin that thins out; do not resume later
        if bx: ax.plot(bx, bm, ls=ls, marker=mk, color=col, lw=2.2, ms=4)
        _nkt = len({r_[3] for r_ in rows_c if r_[1] == lab and r_[2] == ns})
        _upto = f", trend to {bx[-1]:.0f} min while >={MIN_TRACKS} KTs remain" if bx else ", trend not drawn"
        ax.plot([], [], ls=ls, marker=mk, color=col, lw=2.2, ms=4,
                label=f"{disp} ({_nkt} KTs, {len(xs)} frames{_upto})")
    ax.set_xlabel("time since that kinetochore's first tracked frame (min)")
    ax.set_ylabel("cumulative distance covered (µm)")
    ax.set_title("Distance covered by a kinetochore over time — polar & paired, single & triple\n"
                 "cumulative path length per kinetochore; the slope is its speed. Each trend stops once "
                 "fewer than 40% of that group's\nkinetochores are still tracked, so a shrinking cohort "
                 "cannot masquerade as a stall.",
                 loc="left", fontweight="bold", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="best")
    _save(fig, outname_cum, ["batch", "label", "n_sisterless", "track_id", "t_min_from_track_start", "cum_um"],
          rows_c, "Cumulative distance covered per kinetochore over time, four groups", key="track_id")


# ── USER 2026-08-05: four groups on these plots, not one ──────────────────────────────────────────
# "on this plot include the paired circularity data for both single and triple with trendlines (four
#  groups on one plot)" and, for speed, "make a plot like this with anaphase onset at time of 0 and then
#  the same 4 groups".
# The cohort comes from the master "# Sisterless KTs" column — never from the batch name (standing rule).
_MASTER_KT, _ = lib.load_master_plots()
NSIS_KT = {r["Batch Name"]: (r.get("# Sisterless KTs", "") or "").strip() for r in _MASTER_KT}
# polar = warm, paired = cool; single = solid/light, triple = dashed/dark. Same convention as the tension family.
G4_SERIES = [("polar",  "1", "#e6820e", "-",  "o", "polar · single"),
             ("polar",  "3", "#8a4b00", "--", "s", "polar · triple"),
             ("paired", "1", "#3b6fb6", "-",  "o", "paired · single"),
             ("paired", "3", "#14385f", "--", "s", "paired · triple")]


def _anaphase_times():
    """anaphase t_sec per batch, from the first row whose phase is 'anaphase'."""
    ana = {}
    for r in R:
        if r["phase"] == "anaphase" and r["batch"] not in ana:
            t = num(r, "t_sec")
            if t is not None: ana[r["batch"]] = t
    return ana


def _vs_time_to_anaphase_4(metric, ylabel, title, outname, scale=1.0, lo=-40, hi=10, note=""):
    # WINDOW: the single-cohort version uses -20..+10 min. At -20 the polar-TRIPLE series vanished
    # entirely — not for lack of data (189 frames from 3 cells) but because triple cells sit in metaphase
    # for ~25 min on average, so almost all of their polar frames are earlier than 20 min before anaphase.
    # A window shorter than the cohort's own metaphase silently deletes the cohort. -40 covers it.
    """`metric` vs time relative to ANAPHASE ONSET (0 = anaphase), four cohort x state series.

    One binned-median trendline per series, plus faint per-frame points. `scale` converts the stored unit
    (e.g. speed is um/s in the table, plotted as um/min)."""
    ana = _anaphase_times()
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    csv_rows = []; stats_txt = []; _skipped = []
    for lab, ns, col, ls, mk, disp in G4_SERIES:
        xs, ys = [], []
        for r in R:
            if r["label"] != lab: continue
            b = r["batch"]
            if NSIS_KT.get(b, "") != ns or b not in ana: continue
            t = num(r, "t_sec"); v = num(r, metric)
            if t is None or v is None: continue
            ttoa = (t - ana[b]) / 60.0
            if lo <= ttoa <= hi:
                xs.append(ttoa); ys.append(v * scale); csv_rows.append([b, lab, ns, round(ttoa, 4), round(v * scale, 5)])
        if len(xs) < 12:
            # never drop a series silently — say so on the figure
            _skipped.append(f"{disp}: only {len(xs)} frames in window, not drawn")
            continue
        xs = np.array(xs); ys = np.array(ys)
        ax.scatter(xs, ys, s=5, color=col, alpha=0.13, lw=0)
        bins = np.arange(lo, hi + 0.001, 2.5); idx = np.digitize(xs, bins)
        bx, bm = [], []
        for bi in range(1, len(bins)):
            sel = ys[idx == bi]
            if len(sel) >= 3:
                bx.append((bins[bi-1] + bins[bi]) / 2); bm.append(np.median(sel))
        if bx: ax.plot(bx, bm, ls=ls, marker=mk, color=col, lw=2.2, ms=4)
        rho, pv = st.spearmanr(xs, ys)
        ncell = len({r_[0] for r_ in csv_rows if r_[1] == lab and r_[2] == ns})
        ax.plot([], [], ls=ls, marker=mk, color=col, lw=2.2, ms=4,
                label=f"{disp} (n={len(xs)}, {ncell} cells, rho={rho:+.2f}, p={pv:.1g})")
        stats_txt.append(f"{disp}: n={len(xs)}, {ncell} cells, rho={rho:+.2f}, p={pv:.2g}")
    ax.axvline(0, ls="--", color="#d1495b", lw=1.4)
    ax.text(0, ax.get_ylim()[1], " anaphase onset", color="#d1495b", fontsize=7.5, va="top")
    ax.set_xlabel("time relative to anaphase onset (min; 0 = anaphase)")
    ax.set_ylabel(ylabel)
    ax.set_title(title + ("\n" + note if note else ""), loc="left", fontweight="bold", fontsize=10)
    ax.legend(fontsize=7, loc="best")
    if _skipped:
        ax.text(0.0, -0.13, "NOT DRAWN — " + "; ".join(_skipped), transform=ax.transAxes,
                fontsize=7, color="#a33", va="top")
    print("  " + outname + ": " + " | ".join(stats_txt) + ("   SKIPPED: " + "; ".join(_skipped) if _skipped else ""))
    _save(fig, outname, ["batch", "label", "n_sisterless", "t_to_anaphase_min", metric], csv_rows, title, key="batch")


def shape_vs_time_to_anaphase(metric, ylabel, title, outname, labels=("polar",)):
    """Per-frame `metric` vs time-to-anaphase (min), polar tracks. Tests whether a shape change LEADS anaphase."""
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    # need anaphase t_sec per batch: from phase transition in the data (first 'anaphase' row's t_sec)
    ana = _anaphase_times()
    xs_all, ys_all = [], []; csv_rows = []
    for r in R:
        if r["label"] not in labels: continue
        b = r["batch"]
        if b not in ana: continue
        t = num(r, "t_sec"); v = num(r, metric)
        if t is None or v is None: continue
        ttoa = (t - ana[b]) / 60.0  # min relative to anaphase (neg = before)
        if -20 <= ttoa <= 10:
            xs_all.append(ttoa); ys_all.append(v); csv_rows.append([b, ttoa, v])
    ax.scatter(xs_all, ys_all, s=9, color=COL["polar"], alpha=0.35, edgecolor="white", lw=0.2)
    # binned median trend
    xs_all = np.array(xs_all); ys_all = np.array(ys_all)
    if len(xs_all) > 10:
        bins = np.arange(-20, 11, 2.5)
        idx = np.digitize(xs_all, bins)
        bx, bm = [], []
        for bi in range(1, len(bins)):
            sel = ys_all[idx == bi]
            if len(sel) >= 3: bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
        ax.plot(bx, bm, "-o", color="#222", lw=2, ms=4, label="binned median")
    ax.axvline(0, ls="--", color="#d1495b", lw=1.2, label="anaphase onset")
    if len(xs_all): kt_stats.add_corr_stats(ax, xs_all, ys_all, loc="upper left")
    ax.set_xlabel("time relative to anaphase onset (min)"); ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=10.5); ax.legend(fontsize=8)
    _save(fig, outname, ["batch", "t_to_anaphase_min", metric], csv_rows, title, key="batch")


def chromolen_corr(metric, agg, xlabel, title, outname, labels=("polar",)):
    """Per-cell: chromosome length vs an aggregate of `metric` over that cell's polar track(s). Spearman."""
    by = tracks()
    pts = []
    for tid, rs in by.items():
        if rs[0]["label"] not in labels: continue
        cl = num(rs[0], "chromo_len_um")
        vals = [num(r, metric) for r in rs if num(r, metric) is not None]
        if cl is None or not vals: continue
        pts.append((rs[0]["batch"], cl, agg(vals)))
    # one point per cell (median across its tracks)
    bycell = collections.defaultdict(list)
    for b, cl, v in pts: bycell[(b, cl)].append(v)
    X = [cl for (b, cl) in bycell]; Y = [float(np.median(v)) for v in bycell.values()]
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    ax.scatter(X, Y, s=40, color=COL["polar"], alpha=0.85, edgecolor="white", lw=0.4)
    if len(X): kt_stats.add_corr_stats(ax, X, Y, loc="upper right")
    ttl = title
    if len(X) >= 4:
        rho, p = st.spearmanr(X, Y)
        ttl += f"   (Spearman ρ={rho:.2f}, p={p:.2g}, N={len(X)} cells)"
    ax.set_xlabel(xlabel); ax.set_ylabel(title.split(" vs ")[0]); ax.set_title(ttl, loc="left", fontweight="bold", fontsize=9.5)
    _save(fig, outname, ["chromo_len_um", "value"], [[x, y] for x, y in zip(X, Y)], title, key=None)


def toward_vs_away(outname):
    """Polar frames split by whether the KT leads TOWARD the plate (R_toward>R_away) or AWAY. Compare shape."""
    tw = collections.defaultdict(list); aw = collections.defaultdict(list)
    for r in R:
        if r["label"] != "polar": continue
        rt, ra = num(r, "R_toward_um"), num(r, "R_away_um")
        if rt is None or ra is None: continue
        tgt = tw if rt >= ra else aw
        for k in ("aspect_ratio", "circularity", "area_um2", "reflection_asym_perp", "near_far_area_ratio"):
            v = num(r, k)
            if v is not None: tgt[k].append(v)
    metrics = ["aspect_ratio", "circularity", "area_um2", "reflection_asym_perp", "near_far_area_ratio"]
    fig, axs = plt.subplots(1, len(metrics), figsize=(3.0 * len(metrics), 4.6))
    csv_rows = []
    for ax, k in zip(axs, metrics):
        for i, (grp, name, c) in enumerate([(tw, "toward", "#e6820e"), (aw, "away", "#6a51a3")]):
            d = grp.get(k, [])
            if len(d) >= 3:
                lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0, min_n=6)
                ax.hlines(np.median(d), i - 0.3, i + 0.3, color=c, lw=2.2)
                ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=c, alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
                for v in d: csv_rows.append([k, name, v])
        try:
            p = st.mannwhitneyu(tw.get(k, [0]), aw.get(k, [0]))[1]; ax.set_title(f"{k}\nMW p={p:.2g}", fontsize=8)
        except Exception: ax.set_title(k, fontsize=8)
        ax.set_xticks([0, 1]); ax.set_xticklabels(["toward", "away"], fontsize=8)
        # USER 2026-08-03: "explain near_far area ratio" - the metric name alone is unreadable, so the panel
        # that shows it carries its definition and how to read the two directions.
        if k == "near_far_area_ratio":
            ax.set_ylabel("near / far area ratio", fontsize=8)
            ax.axhline(1.0, ls=":", lw=1.0, color="#777", zorder=0)
            ax.text(0.5, 0.985,
                    "1.0 = symmetric about the centroid",
                    transform=ax.transAxes, ha="center", va="top", fontsize=6.4, color="#777")
    fig.suptitle("Polar kinetochores: shape when leading TOWARD vs AWAY from the plate", fontweight="bold", fontsize=11)
    # placed BELOW the figure box (negative y): _save() calls tight_layout(), which would undo any
    # subplots_adjust, and bbox_inches="tight" expands the saved canvas to include this text.
    fig.text(0.005, -0.06,
             "NEAR/FAR AREA RATIO — the kinetochore outline is filled and split through its own centroid by the "
             "line pointing at the nearest point of the metaphase plate.  NEAR = the outline's area on the "
             "plate-facing side, FAR = the area on the side away from the plate; the metric is NEAR / FAR.\n"
             "= 1 symmetric  |  < 1 mass held AWAY from the plate (the 'vase' shape)  |  > 1 mass leaning "
             "TOWARD the plate.  Computed per frame in kt_landmark_analysis.py from the traced outline raster, "
             "so it is a shape measure, not a position measure — a KT far from the plate can still be symmetric.\n"
             "TOWARD vs AWAY (the x groups) is a different thing: it splits polar frames by which end reaches "
             "further, R_toward_um >= R_away_um.",
             fontsize=6.6, color="#444", ha="left", va="top", linespacing=1.5)
    _save(fig, outname, ["metric", "direction", "value"], csv_rows, "Polar toward vs away from plate", key=None)


if __name__ == "__main__":
    print("=== simple size/shape by state ===")
    violin_by_state("perimeter_um", "outline perimeter (µm)", "Kinetochore perimeter by state (tracked)", "G6trk_perimeter")
    # ITEM 22 (user 2026-08-04): remove the LAGGING group from the tracked kinetochore-area plot.
    violin_by_state("area_um2", "area (µm²)", "Kinetochore area by state (tracked; lagging removed)",
                    "G6trk_area", labels=["paired", "polar"])
    # ITEM 1 (2026-08-03, her M2-16 complaint "lagging should be very near 0, much closer to 0 than polar or
    # paired"): the pooled ALL-PHASE version of this plot showed lagging (med 1.70um, n=342) almost identical
    # to paired (med 1.89um, n=2769), which is wrong on its face -- a lagging KT sits at/near the midzone.
    #
    # Root-cause investigation (see kt_landmark_analysis.py for the metric definition):
    #   a. Label check: "lagging" rows really are the her-annotated lagging traces (label comes straight from
    #      the KT.tracked_objects() track label, sourced from her manual kt_points annotations) -- not a
    #      mislabeling bug.
    #   b/c. Phase check: lagging tracks are 76% anaphase-phase rows (261/342) because a KT literally cannot
    #      be scored "lagging" before anaphase onset -- the category only exists once the bulk chromatin has
    #      segregated and this one hasn't. "paired" tracks are the opposite: 53% metaphase-phase (1472/2769,
    #      congressed AT the plate, trivially small distance) and only 17% anaphase. So the OLD all-phase-pooled
    #      medians were comparing a mostly-anaphase population (lagging) against a mostly-metaphase population
    #      (paired) and calling it one number each -- an apples-to-oranges phase-composition confound, not a
    #      biological equivalence. Checked and ruled out as the dominant cause: stale/extrapolated plate
    #      polylines (nearest-in-time plate frame far from the KT's frame) -- lagging rows do have a longer
    #      mean time-gap to their nearest plate annotation (283s vs ~78s for polar/paired), but restricting to
    #      gap<=300s barely moves the anaphase-lagging median (1.79 vs 1.80um), so this is at most a minor
    #      contributor, not the root cause.
    #   Phase-matched (anaphase-only, the only phase where "lagging" is a meaningful, contemporaneous label)
    #      medians: polar 7.75um (n=216), paired 5.63um (n=460), lagging 1.80um (n=261) -- lagging IS much
    #      closer to 0 than both, exactly as she expects. The measurement (dist_to_plate_um) is fine; the bug
    #      was comparing phase-mismatched populations. Fix: restrict this figure to anaphase-phase rows only,
    #      the one window where all three labels co-occur and are directly comparable.
    #   ITEM 11 (user 2026-08-04) REFINES that fix: anaphase-only for ALL states put paired/polar in the wrong
    #   window. Use the per-state rule instead — paired/polar from METAPHASE, lagging from ANAPHASE.
    violin_by_state("dist_to_plate_um", "distance to metaphase plate (µm)",
                     "Kinetochore distance from the plate by state (phase-matched: paired/polar metaphase, lagging anaphase)",
                     "G6trk_dist_to_plate", rowfilter=phase_matched, label_own_max=True)
    print("=== landmark (plate-anchored) descriptors ===")
    violin_by_state("stretch_radial_deg", "major-axis angle vs plate normal (°: 0=radial, 90=tangential)", "Stretch DIRECTION relative to plate by state", "G6trk_stretch_radial", fmt="{:.0f}")
    violin_by_state("anisotropy_par_perp", "anisotropy (parallel / perpendicular extent)", "Stretch anisotropy (toward-plate vs across) by state", "G6trk_anisotropy")
    violin_by_state("near_far_area_ratio", "near/far area ratio (<1 = 'vase', mass away from plate)", "Vase asymmetry (near/far area) by state", "G6trk_vase")
    # 2026-08-17: "⟂" (U+27C2) as MATHTEXT, not a literal glyph. It is absent from Arial, Helvetica AND
    # DejaVu Sans, so as a literal it rendered a tofu box in every font the house style can reach; mathtext
    # draws it from matplotlib's own math font regardless of font.sans-serif. (This is the one label in the
    # whole tree that hit that case — the audit's other missing glyphs are in comments, docstrings, recorded
    # metadata, a dead branch, or non-matplotlib deck placeholders, so none of them ever render.)
    violin_by_state("reflection_asym_perp", r"reflection asymmetry $\perp$ to stretch (crookedness)", "Reflection asymmetry by state", "G6trk_reflection_asym")
    print("=== motion ===")
    speed_by_phase("G6trk_speed_by_phase")
    per_track_violin(lambda rs: np.nanmedian([num(r, "radial_speed_um_s")*60 for r in rs if r["phase"]=="anaphase" and num(r,"radial_speed_um_s") is not None]) if any(r["phase"]=="anaphase" and num(r,"radial_speed_um_s") is not None for r in rs) else None,
                     "median poleward speed after anaphase (µm/min; + = toward pole)", "Post-anaphase poleward speed per KT", "G6trk_postanaphase_speed", fmt="{:.1f}")
    dist_traveled("G6trk_distance_total", "G6trk_distance_per20s")
    # USER 2026-08-05: the four-group distance companions
    distance_4group("G6trk_distance_per_min_4group", "G6trk_distance_cumulative_4group")
    print("=== fractures ===")
    per_track_violin(lambda rs: max(int(r["n_pieces"]) for r in rs), "max # fracture pieces in a frame", "Kinetochore fracturing (max pieces) by state", "G6trk_fractures", fmt="{:.0f}")
    print("=== shape vs time-to-anaphase (polar; predictive) ===")
    shape_vs_time_to_anaphase("circularity", "circularity", "Polar-KT circularity vs time to anaphase", "G6trk_circ_vs_ttana")
    # USER 2026-08-05: the four-group companions (polar & paired x single & triple)
    _vs_time_to_anaphase_4("circularity", "circularity",
                           "Kinetochore circularity vs time to anaphase — polar & paired, single & triple",
                           "G6trk_circ_vs_ttana_4group",
                           note="one binned-median trendline per group; cohort from the master # Sisterless KTs column")
    _vs_time_to_anaphase_4("speed_um_s", "kinetochore speed (µm/min)",
                           "Kinetochore speed vs time to anaphase — polar & paired, single & triple",
                           "G6trk_speed_vs_ttana_4group", scale=60.0,
                           note="anaphase onset at t=0; companion to the mitotic-time speed plots")
    shape_vs_time_to_anaphase("aspect_ratio", "aspect ratio", "Polar-KT stretch vs time to anaphase", "G6trk_aspect_vs_ttana")
    shape_vs_time_to_anaphase("area_um2", "area (µm²)", "Polar-KT area vs time to anaphase", "G6trk_area_vs_ttana")
    print("=== chromosome-length correlations (polar, per cell) ===")
    chromolen_corr("speed_um_s", lambda v: np.median(v)*60, "chromosome length (µm)", "median speed (µm/min) vs chromosome length", "G6trk_chromolen_vs_speed")
    chromolen_corr("circularity", np.median, "chromosome length (µm)", "median circularity vs chromosome length", "G6trk_chromolen_vs_circ")
    chromolen_corr("aspect_ratio", np.median, "chromosome length (µm)", "median stretch vs chromosome length", "G6trk_chromolen_vs_aspect")
    print("=== polar: stretch toward vs away from plate ===")
    toward_vs_away("G6trk_toward_vs_away")
    print(f"\nAll track/landmark figures -> {OUT}")
