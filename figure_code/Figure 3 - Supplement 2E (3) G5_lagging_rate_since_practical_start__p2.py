"""Lagging-chromosome dynamics — user feedback 2026-08-04 (her items 11 and 13).

Everything here is built on the SAME smoothed envelopes as G5shape_lagging_stretch_time so the numbers on
these figures can be read straight off that plot. Reusing kt_shape_plots' own builder rather than
re-deriving the smoothing is deliberate: two different definitions of "the peak" would make the rate plots
disagree with the trace plot they are supposed to describe.

FB11b — "practical start" and the two rate plots:
    Once a portion of the smoothed trace has 3+ points within a 5 min span AND those points are within
    10 min of the peak, the FIRST of those three points is the practical start. From there:
      * rate of elongation over time since practical start (fitted, not assumed linear)
      * rate of shortening after the peak, over time from peak
FB11c — do laggards in 1- vs 3-sisterless cells differ: peak length, recovery to starting length,
    lengthening rate, recovery rate, and time of peak from anaphase onset.
FB13c — number of pieces a lagging chromosome is in vs time after anaphase, smoothed the same way.
FB13e — laggards that stay in ONE piece until peak and then shorten while moving poleward: peak length and
    shape, end shape, transition time -> a recoverable-strain estimate, and whether it stiffens with strain.

NOTE ON WHAT CAN AND CANNOT BE CLAIMED: these are shape measurements of a chromosome under load, not a
rheology experiment. "Recoverable strain" here means (peak length - end length) / (peak length - start
length) — how much of the imposed stretch was given back. It is a descriptive ratio, not a modulus; no
force is measured anywhere in this dataset, so nothing here can state an elasticity in physical units.
"""
import sys, os, csv, math, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import scipy.stats as st
import lib

SCRIPT = __file__
OUT = "/Volumes/4 MB/ablation_figures_20260625/new_figures_20260804"
os.makedirs(OUT, exist_ok=True)
lib.apply_style()

master, _ = lib.load_master_plots(); MR = {r["Batch Name"]: r for r in master}
def sis(b): return str((MR.get(b, {}) or {}).get("# Sisterless KTs", "") or "").strip()
def fam(b):
    v = sis(b)
    return "1" if v == "1" else ("23" if v in ("2", "3") else "other")

COL = {"1": "#2171b5", "23": "#d94801", "other": "#969696"}
LBL = {"1": "1-sisterless", "23": "2/3-sisterless"}

# ── the smoothed envelopes, straight from the figure builder ──────────────────────────────────────
import kt_shape_plots as ksp        # importing runs its plots; that is also what refreshes them
PEAKS = ksp.lagging_since_anaphase("G5shape_lagging_stretch_time")
print(f"lagging dynamics: {len(PEAKS)} smoothed tracks in hand")


# ── FB11b: practical start ────────────────────────────────────────────────────────────────────────
WIN_MIN, NEED_PTS, NEAR_PEAK_MIN = 5.0, 3, 10.0
MIN_RATE_DUR = 0.5      # min; shorter intervals make a rate meaningless (see the rate guard below)

def practical_start(xs, ys, t_peak):
    """Index of the first point of the earliest run of >=3 points inside a 5-min window whose points all
    sit within 10 min of the peak. None when no run qualifies (short or sparse tracks)."""
    n = len(xs)
    for i in range(n):
        j = i
        while j + 1 < n and xs[j + 1] - xs[i] <= WIN_MIN:
            j += 1
        if (j - i + 1) >= NEED_PTS and all(abs(xs[k] - t_peak) <= NEAR_PEAK_MIN for k in range(i, j + 1)):
            return i
    return None


TRACKS = []      # one dict per lagging kinetochore, everything downstream reads this
for b, g, f, t_peak, y_peak, xs, ys in PEAKS:
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    ip = int(np.argmax(ys))
    i0 = practical_start(xs, ys, t_peak)
    rec = {"batch": b, "grp": g, "fam": f, "t_peak": float(t_peak), "y_peak": float(y_peak),
           "xs": xs, "ys": ys, "ip": ip, "i0": i0,
           "y_start": float(ys[i0]) if i0 is not None else None,
           "y_end": float(ys[-1]), "t_end": float(xs[-1])}
    # rise: practical start -> peak.  fall: peak -> last point
    # A rate needs a real interval to be divided by: over a few seconds the division blows up and produces
    # values like 110 um/min, which is a measurement artefact rather than a fast chromosome. Rates are only
    # computed across MIN_RATE_DUR or more (2026-08-04).
    if i0 is not None and ip > i0 and (xs[ip] - xs[i0]) >= MIN_RATE_DUR:
        rec["rise_rate"] = (ys[ip] - ys[i0]) / (xs[ip] - xs[i0])          # um/min
        rec["rise_dur"] = float(xs[ip] - xs[i0])
    if ip < len(xs) - 1 and (xs[-1] - xs[ip]) >= MIN_RATE_DUR:
        rec["fall_rate"] = (ys[ip] - ys[-1]) / (xs[-1] - xs[ip])          # um/min shortening (positive)
        rec["fall_dur"] = float(xs[-1] - xs[ip])
    if i0 is not None and ys[ip] > ys[i0]:
        rec["recovered_frac"] = (ys[ip] - ys[-1]) / (ys[ip] - ys[i0])     # 1.0 = back to starting length
    TRACKS.append(rec)

n_ps = sum(1 for t in TRACKS if t["i0"] is not None)
print(f"FB11b: practical start found for {n_ps}/{len(TRACKS)} tracks "
      f"(needs {NEED_PTS}+ points in {WIN_MIN:g} min, all within {NEAR_PEAK_MIN:g} min of the peak)")


def _fit_note(x, y):
    """Compare a straight line against a quadratic; report which describes the rate better. She said the
    trend line 'doesn't have to be linear', so the figure should say which one it actually is."""
    if len(x) < 4: return None, ""
    lin = np.polyfit(x, y, 1); quad = np.polyfit(x, y, 2)
    rl = y - np.polyval(lin, x); rq = y - np.polyval(quad, x)
    ssl, ssq = float(rl @ rl), float(rq @ rq)
    sst = float(((y - y.mean()) ** 2).sum()) or 1.0
    better = "quadratic" if ssq < ssl * 0.9 else "linear"
    return (quad if better == "quadratic" else lin), \
           f"{better} fit (R²={1 - (ssq if better == 'quadratic' else ssl) / sst:.2f})"


def fb11b_rate_plots():
    """Two panels: elongation since practical start, and shortening since peak."""
    fig, axs = plt.subplots(1, 2, figsize=(12.4, 5.2))
    rows = []
    for ax, phase, ttl, xlab in (
            (axs[0], "rise", "Elongation since PRACTICAL START", "Time since practical start (min)"),
            (axs[1], "fall", "Shortening since PEAK", "Time since peak (min)")):
        allx, ally = [], []
        for t in TRACKS:
            if phase == "rise":
                if t["i0"] is None or t["ip"] <= t["i0"]: continue
                sl = slice(t["i0"], t["ip"] + 1); x0 = t["xs"][t["i0"]]
            else:
                if t["ip"] >= len(t["xs"]) - 1: continue
                sl = slice(t["ip"], len(t["xs"])); x0 = t["xs"][t["ip"]]
            x = t["xs"][sl] - x0; y = t["ys"][sl]
            ax.plot(x, y, "-o", ms=3, lw=1.0, alpha=.55, color=COL[t["fam"]])
            allx += list(x); ally += list(y)
            rows += [[t["batch"], t["grp"], t["fam"], phase, round(float(a), 3), round(float(c), 4)]
                     for a, c in zip(x, y)]
        if len(allx) >= 4:
            ax_ = np.array(allx); ay_ = np.array(ally)
            fitp, ftxt = _fit_note(ax_, ay_)
            if fitp is not None:
                xr = np.linspace(ax_.min(), ax_.max(), 80)
                ax.plot(xr, np.polyval(fitp, xr), "-", color="#111", lw=2.4, zorder=5, label=ftxt)
                ax.legend(fontsize=8, loc="best")
        ax.set_xlabel(xlab); ax.set_ylabel("Kinetochore length, major axis (µm)")
        ax.set_title(ttl, loc="left", fontweight="bold", fontsize=10)
    axs[0].legend(handles=[Line2D([0], [0], color=COL["1"], lw=2.4, label=LBL["1"]),
                           Line2D([0], [0], color=COL["23"], lw=2.4, label=LBL["23"])] +
                          axs[0].get_legend().legend_handles if axs[0].get_legend() else
                          [Line2D([0], [0], color=COL["1"], lw=2.4, label=LBL["1"]),
                           Line2D([0], [0], color=COL["23"], lw=2.4, label=LBL["23"])], fontsize=8)
    fig.suptitle("Lagging-chromosome elongation and recovery rates (user 2026-08-04)\n"
                 f"PRACTICAL START = first of {NEED_PTS}+ smoothed points within {WIN_MIN:g} min that all lie "
                 f"within {NEAR_PEAK_MIN:g} min of the peak — found for {n_ps} of {len(TRACKS)} tracks",
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G5_lagging_rate_since_practical_start.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G5_lagging_rate_since_practical_start",
                    ["batch", "grp", "family", "phase", "t_rel_min", "major_um"], rows,
                    {"fb11b": "elongation since practical start; shortening since peak",
                     "practical_start": f"{NEED_PTS}+ points in {WIN_MIN}min, all within {NEAR_PEAK_MIN}min of peak",
                     "n_with_practical_start": n_ps, "n_tracks": len(TRACKS)},
                    SCRIPT, "Lagging elongation and recovery rates", key_column="batch")
    print(f"FB11b: wrote rate plots ({len(rows)} points)")


# ── FB11c: 1-sisterless vs 3-sisterless ───────────────────────────────────────────────────────────
def fb11c_group_compare():
    """Peak length, recovery fraction, rise rate, fall rate, and peak timing — 1 vs 2/3 sisterless."""
    METRICS = [("y_peak", "Peak length (µm)", "Peak length reached"),
               ("recovered_frac", "Fraction of stretch given back", "Recovery toward starting length"),
               ("rise_rate", "Elongation rate (µm/min)", "Rate of lengthening"),
               ("fall_rate", "Shortening rate (µm/min)", "Rate of recovery"),
               ("t_peak", "Time of peak (min after anaphase)", "Timing of peak")]
    # 2026-08-04: five panels at 3.05in each left the titles and tick labels cramped. Widen.
    fig, axs = plt.subplots(1, len(METRICS), figsize=(3.7 * len(METRICS), 5.2))
    rows, summary = [], []
    for ax, (key, ylab, ttl) in zip(axs, METRICS):
        a = [t[key] for t in TRACKS if t["fam"] == "1" and t.get(key) is not None]
        c = [t[key] for t in TRACKS if t["fam"] == "23" and t.get(key) is not None]
        for i, (vals, f) in enumerate(((a, "1"), (c, "23"))):
            if vals:
                ax.boxplot([vals], positions=[i], widths=.6, showfliers=False)
                ax.scatter(np.full(len(vals), i) + np.random.RandomState(4).uniform(-.13, .13, len(vals)),
                           vals, s=26, color=COL[f], alpha=.85, edgecolor="white", lw=.4, zorder=3)
            rows += [[f, key, round(float(v), 5)] for v in vals]
        p = None
        if len(a) >= 3 and len(c) >= 3:
            p = float(st.mannwhitneyu(a, c, alternative="two-sided")[1])
        ax.set_xticks([0, 1]); ax.set_xticklabels([f"1-sis\nn={len(a)}", f"2/3-sis\nn={len(c)}"], fontsize=8)
        ax.set_ylabel(ylab, fontsize=8.5)
        ax.set_title(f"{ttl}\n" + (f"p={p:.3g}" if p is not None else "too few tracks"),
                     fontsize=8.5, fontweight="bold")
        summary.append(f"{ttl}: 1-sis med "
                       f"{np.median(a):.2f}" if a else f"{ttl}: 1-sis n/a")
        if a and c:
            summary[-1] += f" vs 2/3-sis {np.median(c):.2f}" + (f", p={p:.3g}" if p is not None else "")
    fig.suptitle("Do lagging chromosomes behave differently in 1- vs 2/3-sisterless cells?  (user 2026-08-04)\n"
                 "one point per lagging kinetochore; all quantities read off the same smoothed envelopes as "
                 "G5shape_lagging_stretch_time",
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G5_lagging_behaviour_1_vs_3.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G5_lagging_behaviour_1_vs_3", ["family", "metric", "value"], rows,
                    {"fb11c": "lagging behaviour, 1 vs 2/3 sisterless", "metrics": [m[0] for m in METRICS]},
                    SCRIPT, "Lagging behaviour compared across ablation number", key_column="family")
    for s in summary: print("   FB11c " + s)


# ── FB13c: how many pieces is the laggard in, over time after anaphase ────────────────────────────
def fb13c_piece_count():
    """One traced lagging chromosome can be annotated as several polygons on a frame — that count IS the
    number of pieces. Smoothed the same way as the length plot (monotone envelope around the maximum)."""
    from kt_landmark_analysis import phase_times
    per = collections.defaultdict(lambda: collections.defaultdict(int))
    for r in ksp.ROWS:
        if r.get("label") != "lagging": continue
        try: t = float(r["t_sec"])
        except Exception: continue
        per[(r["batch"], r.get("grp") or "")][round(t, 1)] += 1
    ph = phase_times(sorted({b for b, _ in per}))
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    rows = []; n = 0; seen = collections.Counter()
    for (b, g), d in per.items():
        at = ph.get(b, (None, None))[1]
        if at is None: continue
        pts = sorted((t, c) for t, c in d.items())
        keep = [((t - at) / 60.0, c) for t, c in pts if (t - at) >= 0]
        if len(keep) < 3: continue
        x = np.array([p[0] for p in keep], float); y = np.array([p[1] for p in keep], float)
        _ce = len(y) - 2
        ip = int(np.argmax(y[:_ce])) if _ce >= 1 else int(np.argmax(y))
        sel = [ip]; run = y[ip]
        for i in range(ip - 1, -1, -1):
            if y[i] <= run: sel.append(i); run = y[i]
        run = y[ip]
        for i in range(ip + 1, len(y)):
            if y[i] <= run: sel.append(i); run = y[i]
        sel = sorted(set(sel)); xs, ys = x[sel], y[sel]
        f = fam(b)
        ax.plot(xs, ys, "-o", ms=3, lw=1.1, alpha=.8, color=COL[f]); seen[f] += 1; n += 1
        rows += [[b, g, f, round(float(a), 3), int(c)] for a, c in zip(xs, ys)]
    ax.set_xlim(left=0); ax.set_xlabel("Time since anaphase onset (min)")
    ax.set_ylabel("Number of pieces the lagging chromosome is traced in")
    ax.set_title(f"Lagging-chromosome PIECE COUNT after anaphase onset — {n} kinetochores",
                 loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(handles=[Line2D([0], [0], color=COL["1"], lw=2.4, label=f"{LBL['1']} (n={seen['1']})"),
                       Line2D([0], [0], color=COL["23"], lw=2.4, label=f"{LBL['23']} (n={seen['23']})")],
              fontsize=8)
    ax.text(0.0, -0.145,
            "Pieces = how many separate polygons that lagging chromosome is traced as on a frame. Smoothed "
            "exactly like the length plot\n(monotone envelope around the maximum), so the two figures can be "
            "read against each other.",
            transform=ax.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.5)
    fig.tight_layout(); fig.savefig(f"{OUT}/G5_lagging_piece_count_after_anaphase.png",
                                    dpi=150, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G5_lagging_piece_count_after_anaphase",
                    ["batch", "grp", "family", "t_since_anaphase_min", "n_pieces"], rows,
                    {"fb13c": "piece count vs time after anaphase, smoothed like the length plot"},
                    SCRIPT, "Lagging-chromosome piece count after anaphase", key_column="batch")
    print(f"FB13c: {n} tracks, {len(rows)} points")
    return per


# ── FB13e: single-piece laggards -> recoverable strain, and does it stiffen? ──────────────────────
def fb13e_material(per_pieces):
    """Laggards that stay in ONE piece up to their peak, then shorten. For each: the strain imposed
    (peak/start length), the fraction of that stretch given back, and how long the recovery took.
    Strain-stiffening would show as the shortening rate FALLING as peak strain rises (a stiffer object
    gives back less per unit time under the same recovery); the test is stated on the figure either way."""
    ok = []
    for t in TRACKS:
        if t["i0"] is None or t.get("fall_rate") is None or t.get("recovered_frac") is None: continue
        d = per_pieces.get((t["batch"], t["grp"]), {})
        # every frame from practical start through peak must be a single traced polygon
        t0, t1 = t["xs"][t["i0"]], t["xs"][t["ip"]]
        from kt_landmark_analysis import phase_times
        counts = [c for _tt, c in d.items()]
        if not counts: continue
        single = max(counts) == 1 if counts else False
        strain = t["y_peak"] / t["y_start"] if t["y_start"] else None
        if strain is None or strain <= 0: continue
        ok.append({**t, "single_piece": single, "strain": strain})
    if not ok:
        print("FB13e: no tracks qualified"); return
    singles = [r for r in ok if r["single_piece"]]
    fig, axs = plt.subplots(1, 3, figsize=(13.2, 4.8))
    # (1) recoverable fraction vs imposed strain
    for ax, (xk, yk, xl, yl, ttl) in zip(axs, [
            ("strain", "recovered_frac", "Peak strain  (peak length / start length)",
             "Fraction of stretch given back", "Recoverable strain"),
            ("strain", "fall_rate", "Peak strain  (peak length / start length)",
             "Shortening rate (µm/min)", "Does it stiffen with strain?"),
            ("strain", "fall_dur", "Peak strain  (peak length / start length)",
             "Time from peak to end (min)", "Transition time")]):
        for r in ok:
            ax.scatter(r[xk], r[yk], s=48 if r["single_piece"] else 26,
                       color=COL[r["fam"]], alpha=.9 if r["single_piece"] else .35,
                       edgecolor="k" if r["single_piece"] else "none", lw=.7, zorder=3)
        X = np.array([r[xk] for r in singles], float); Y = np.array([r[yk] for r in singles], float)
        if len(X) >= 4:
            rho, p = st.spearmanr(X, Y)
            ax.set_title(f"{ttl}\nsingle-piece only: rho={rho:+.2f}, p={p:.3g}, n={len(X)}",
                         fontsize=9, fontweight="bold")
        else:
            ax.set_title(f"{ttl}\nsingle-piece n={len(X)} — too few to test", fontsize=9, fontweight="bold")
        ax.set_xlabel(xl, fontsize=8.5); ax.set_ylabel(yl, fontsize=8.5)
    fig.suptitle("Lagging chromosomes that stay in ONE piece to their peak, then shorten (user 2026-08-04)\n"
                 f"{len(singles)} of {len(ok)} tracks are single-piece throughout (filled, outlined); the rest "
                 "are drawn faint for context",
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    axs[0].text(0.0, -0.20,
                "Recoverable strain = (peak length − end length) / (peak length − start length): how much of "
                "the imposed stretch was given back.\nThis is a DESCRIPTIVE ratio from shape measurements. No "
                "force is measured anywhere in this dataset, so no elastic modulus can be\nstated in physical "
                "units — strain-stiffening can only be read here as a trend of recovery against imposed strain.",
                transform=axs[0].transAxes, fontsize=6.6, color="#8b3a00", va="top", linespacing=1.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G5_lagging_recoverable_strain.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G5_lagging_recoverable_strain",
                    ["batch", "grp", "family", "single_piece", "peak_strain", "recovered_frac",
                     "fall_rate_um_per_min", "fall_dur_min"],
                    [[r["batch"], r["grp"], r["fam"], int(r["single_piece"]), round(r["strain"], 4),
                      round(r["recovered_frac"], 4), round(r["fall_rate"], 4), round(r["fall_dur"], 3)]
                     for r in ok],
                    {"fb13e": "recoverable strain of single-piece laggards",
                     "n_single_piece": len(singles), "n_total": len(ok),
                     "caveat": "descriptive ratio only; no force measured, so no modulus"},
                    SCRIPT, "Recoverable strain of single-piece lagging chromosomes", key_column="batch")
    print(f"FB13e: {len(singles)} single-piece of {len(ok)} tracks")


if __name__ == "__main__":
    fb11b_rate_plots()
    fb11c_group_compare()
    _per = fb13c_piece_count()
    fb13e_material(_per)
    print("lagging dynamics: done")
