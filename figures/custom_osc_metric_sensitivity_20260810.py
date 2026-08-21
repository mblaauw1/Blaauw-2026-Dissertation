#!/usr/bin/env python3
"""How much do the three groups' oscillation differences depend on HOW amplitude and period are defined?

USER 2026-08-10: "How do different ways of quantifying osculation period and amplitude vary the
relationships between the three groups?"

THE THREE GROUPS are the ones already on the board as G6_three_group_*:
    P   single-sisterless, PROMETAPHASE window
    M1  single-sisterless, METAPHASE window
    M3  triple-sisterless, METAPHASE window

The cohort/window/series code is IMPORTED from custom_prometa_vs_meta_20260810.py rather than reimplemented,
so these are the same kinetochores, the same paired-only filter, the same metaphase and prometaphase windows
and the same per-KINETOCHORE unit as the figures she is already looking at. If that file changes, this
follows it. Re-deriving them here is exactly how two "identical" analyses drift apart.

WHAT VARIES. Amplitude is recomputed 7 ways (the existing STATS) and period 6 ways. Each definition is a
defensible reading of "how far does it swing" / "how fast does it swing", and they differ in what they are
sensitive to: outliers (peak-to-peak vs MAD), slow drift (raw SD vs detrended SD), and, for period,
whether an unevenly-sampled short series is treated as a wave (Lomb-Scargle, ACF) or merely counted
(zero-crossings, reversals).

WHAT IS REPORTED. For every definition: each group's median, Kruskal-Wallis across all three, and all three
pairwise Mann-Whitney p-values with Cliff's delta. The question is not which number is biggest but whether
the RELATIONSHIPS -- the ordering of the three groups and which contrasts reach significance -- survive the
choice of definition. A result that flips with the definition is a result about the statistic, not the cells.

N is per KINETOCHORE, paired kinetochores only, which is the unit she fixed on 2026-08-10: "for amplitude
and period, this refers to oscilation back and forth, so you need to find this for each kinetochore, not
pair of kinetochores".
"""
import sys, os, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, kruskal
from scipy.signal import find_peaks, lombscargle

import lib
import custom_prometa_vs_meta_20260810 as SRC   # cohorts, windows, series, STATS, cliffs_delta

OUT = os.environ.get("KTFIG_OUT") or "/Volumes/4 MB/ablation_figures_20260625/group6"
os.makedirs(OUT, exist_ok=True)


# ---- period estimators ----------------------------------------------------------------------------
def _clean(t, v):
    ts = [(a, b) for a, b in zip(t, v) if b is not None and np.isfinite(b)]
    if len(ts) < 6: return None, None
    ts.sort()
    return np.array([a for a, _ in ts], float), np.array([b for _, b in ts], float)


def _lin_detrend(t, y):
    if len(t) < 3: return y - np.mean(y)
    A = np.polyfit(t, y, 1)
    return y - np.polyval(A, t)


def p_zero_cross(t, v):
    """Current definition: 2 x span / number of mean-crossings."""
    t, y = _clean(t, v)
    if t is None: return None
    y = y - np.mean(y)
    if np.std(y) == 0: return None
    s = np.sign(y); s[s == 0] = 1
    nc = int(np.sum(np.abs(np.diff(s)) > 0))
    return 2.0 * (t.max() - t.min()) / nc if nc >= 1 else None


def p_zero_cross_detrended(t, v):
    """Same count, but after removing a linear drift -- a kinetochore that is slowly migrating crosses its
    own MEAN rarely, which inflates the apparent period even when it is oscillating briskly."""
    t, y = _clean(t, v)
    if t is None: return None
    y = _lin_detrend(t, y)
    if np.std(y) == 0: return None
    s = np.sign(y); s[s == 0] = 1
    nc = int(np.sum(np.abs(np.diff(s)) > 0))
    return 2.0 * (t.max() - t.min()) / nc if nc >= 1 else None


def p_reversals(t, v):
    """Direction reversals: counts turns rather than crossings, so it does not care where the centre is."""
    t, y = _clean(t, v)
    if t is None: return None
    d = np.diff(y)
    d = d[d != 0]
    if len(d) < 2: return None
    nr = int(np.sum(np.diff(np.sign(d)) != 0))
    return 2.0 * (t.max() - t.min()) / nr if nr >= 1 else None


def p_peak_interval(t, v):
    """Mean time between successive prominent maxima -- the most literal reading of 'period'."""
    t, y = _clean(t, v)
    if t is None: return None
    prom = 0.5 * np.std(y)
    if prom <= 0: return None
    pk, _ = find_peaks(y, prominence=prom)
    if len(pk) < 2: return None
    return float(np.mean(np.diff(t[pk])))


def p_acf(t, v):
    """First autocorrelation peak, on a uniform resample. Uses the whole waveform rather than a few
    threshold events, so it is steadier on noisy series -- but needs a real repeat to find."""
    t, y = _clean(t, v)
    if t is None: return None
    n = max(16, len(t))
    ti = np.linspace(t.min(), t.max(), n)
    yi = np.interp(ti, t, y)
    yi = yi - yi.mean()
    if np.std(yi) == 0: return None
    ac = np.correlate(yi, yi, mode="full")[len(yi) - 1:]
    if ac[0] <= 0: return None
    ac = ac / ac[0]
    pk, _ = find_peaks(ac)
    if not len(pk): return None
    dt = (ti[1] - ti[0])
    return float(pk[0] * dt)


def p_lombscargle(t, v, pmin=0.5, pmax=30.0):
    """Dominant Lomb-Scargle period. The one estimator built for UNEVENLY sampled series, which these are."""
    t, y = _clean(t, v)
    if t is None: return None
    y = y - np.mean(y)
    if np.std(y) == 0: return None
    span = t.max() - t.min()
    if span <= 0: return None
    hi = min(pmax, span)
    if hi <= pmin: return None
    periods = np.linspace(pmin, hi, 400)
    ang = 2.0 * np.pi / periods
    try:
        pw = lombscargle(t, y, ang, normalize=True)
    except Exception:
        return None
    if not np.isfinite(pw).any(): return None
    return float(periods[int(np.nanargmax(pw))])


PERIODS = {
    "zero-cross (current)":   p_zero_cross,
    "zero-cross detrended":   p_zero_cross_detrended,
    "direction reversals":    p_reversals,
    "peak-to-peak interval":  p_peak_interval,
    "autocorrelation":        p_acf,
    "Lomb-Scargle":           p_lombscargle,
}


# ---- groups ---------------------------------------------------------------------------------------
G = collections.OrderedDict([
    ("P  single prometa", SRC.kt_single_prometa),
    ("M1 single meta",    SRC.kt_single_meta),
    ("M3 triple meta",    SRC.kt_triple_meta),
])
KEYS = list(G.keys())
print("\nunit = KINETOCHORE (paired only), as fixed 2026-08-10")
for k, v in G.items():
    print(f"   {k:20s} {len(v):3d} kinetochores / {len({x['cell'] for x in v})} cells")


def stat_block(label, fn, is_amp):
    vals = {}
    for k, kts in G.items():
        out = []
        for x in kts:
            try:
                r = fn(x["pos"], x["t"]) if is_amp else fn(x["t"], x["pos"])
            except Exception:
                r = None
            if r is not None and np.isfinite(r): out.append(float(r))
        vals[k] = out
    row = {"stat": label, "n": {k: len(v) for k, v in vals.items()},
           "med": {k: (float(np.median(v)) if v else float("nan")) for k, v in vals.items()}}
    have = [vals[k] for k in KEYS if len(vals[k]) >= 3]
    row["kw"] = kruskal(*have).pvalue if len(have) == 3 else float("nan")
    row["pair"] = {}
    for i in range(len(KEYS)):
        for j in range(i + 1, len(KEYS)):
            a, b = vals[KEYS[i]], vals[KEYS[j]]
            nm = f"{KEYS[i].split()[0]} vs {KEYS[j].split()[0]}"
            p = mannwhitneyu(a, b, alternative="two-sided").pvalue if len(a) >= 3 and len(b) >= 3 else float("nan")
            row["pair"][nm] = (SRC.cliffs_delta(a, b), p)
    order = sorted(KEYS, key=lambda k: row["med"][k])
    row["order"] = " < ".join(k.split()[0] for k in order)
    return row


AMP_ROWS = [stat_block(nm, fn, True) for nm, fn in SRC.STATS.items()]
PER_ROWS = [stat_block(nm, fn, False) for nm, fn in PERIODS.items()]

PAIRNAMES = list(AMP_ROWS[0]["pair"].keys())


def report(title, rows):
    print(f"\n================ {title} ================")
    hdr = f"{'definition':24s} " + " ".join(f"{k.split()[0]:>7s}" for k in KEYS) + f" {'KW p':>9s}  "
    hdr += "  ".join(f"{p:>16s}" for p in PAIRNAMES) + "   ordering"
    print(hdr)
    for r in rows:
        line = f"{r['stat'][:23]:24s} " + " ".join(f"{r['med'][k]:7.2f}" for k in KEYS) + f" {r['kw']:9.3g}  "
        line += "  ".join(f"d={r['pair'][p][0]:+.2f} p={r['pair'][p][1]:6.3g}" for p in PAIRNAMES)
        line += f"   {r['order']}"
        print(line)
    # stability
    orders = collections.Counter(r["order"] for r in rows)
    print(f"\n  group ORDERING across definitions: " +
          "; ".join(f"{o} ({n}/{len(rows)})" for o, n in orders.most_common()))
    for p in PAIRNAMES:
        sig = [r["stat"] for r in rows if np.isfinite(r["pair"][p][1]) and r["pair"][p][1] < 0.05]
        ns = [r["stat"] for r in rows if np.isfinite(r["pair"][p][1]) and r["pair"][p][1] >= 0.05]
        ds = [r["pair"][p][0] for r in rows]
        print(f"  {p}: significant under {len(sig)}/{len(rows)} definitions; "
              f"Cliff d ranges {min(ds):+.2f} to {max(ds):+.2f}"
              + (f"; NOT significant under: {', '.join(ns)}" if ns else ""))


report("AMPLITUDE", AMP_ROWS)
report("PERIOD", PER_ROWS)


# ---- figure ---------------------------------------------------------------------------------------
COLP = {"P vs M1": "#8a5cf6", "P vs M3": "#ff8c1a", "M1 vs M3": "#2a7fff"}
fig, axs = plt.subplots(2, 2, figsize=(15.0, 9.6), gridspec_kw={"width_ratios": [1.25, 1]})
for row, (title, rows) in enumerate((("Amplitude", AMP_ROWS), ("Period", PER_ROWS))):
    ax = axs[row, 0]
    names = [r["stat"] for r in rows]
    yy = np.arange(len(names))
    for pi, p in enumerate(PAIRNAMES):
        off = (pi - 1) * 0.27
        d = [abs(r["pair"][p][0]) for r in rows]
        bars = ax.barh(yy + off, d, height=0.25, color=COLP.get(p, "#888"), label=p)
        for k, r in enumerate(rows):
            if np.isfinite(r["pair"][p][1]) and r["pair"][p][1] < 0.05:
                ax.text(abs(r["pair"][p][0]) + .012, yy[k] + off, "*", va="center", fontsize=11, fontweight="bold")
    ax.set_yticks(yy); ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("|Cliff's delta|   (0 = identical, 1 = complete separation)   * = p < 0.05")
    ax.set_title(f"{title}: does the contrast survive the definition?", loc="left", fontweight="bold", fontsize=11)
    ax.grid(alpha=.3, axis="x"); ax.legend(fontsize=8, loc="lower right")

    ax2 = axs[row, 1]
    for gi, k in enumerate(KEYS):
        med = [r["med"][k] for r in rows]
        base = med[0] if np.isfinite(med[0]) and med[0] != 0 else 1.0
        ax2.plot(range(len(rows)), [m / base for m in med], "o-", label=k, lw=1.8, ms=5)
    ax2.set_xticks(range(len(rows)))
    ax2.set_xticklabels([r["stat"] for r in rows], rotation=35, ha="right", fontsize=8)
    ax2.axhline(1.0, color="#999", lw=.8, ls=":")
    ax2.set_ylabel(f"group median / its own value under\n'{rows[0]['stat']}'")
    ax2.set_title(f"{title}: do the groups move together?", loc="left", fontweight="bold", fontsize=11)
    ax2.grid(alpha=.3); ax2.legend(fontsize=8)

fig.suptitle("Oscillation metrics: how the choice of definition changes the three-group relationships\n"
             "per kinetochore, paired KTs only", fontweight="bold", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
p = os.path.join(OUT, "G6_osc_metric_sensitivity_threegroup.png")
fig.savefig(p, dpi=200)
print(f"\nwrote {p}")

lib.record_plot("G6_osc_metric_sensitivity_threegroup",
                ["family", "definition", "n_P", "n_M1", "n_M3", "med_P", "med_M1", "med_M3",
                 "kruskal_p", "d_P_M1", "p_P_M1", "d_P_M3", "p_P_M3", "d_M1_M3", "p_M1_M3", "ordering"],
                [[fam, r["stat"]] + [r["n"][k] for k in KEYS] + [round(r["med"][k], 5) for k in KEYS] +
                 [r["kw"]] + [x for p_ in PAIRNAMES for x in (round(r["pair"][p_][0], 4), r["pair"][p_][1])] +
                 [r["order"]]
                 for fam, rows in (("amplitude", AMP_ROWS), ("period", PER_ROWS)) for r in rows],
                {"kind": "definition-sensitivity of oscillation amplitude and period across three groups",
                 "unit": "kinetochore (paired only)",
                 "groups": "P = single prometaphase, M1 = single metaphase, M3 = triple metaphase",
                 "note": "cohorts/windows imported from custom_prometa_vs_meta_20260810.py so they match "
                         "the G6_three_group_* figures exactly"},
                __file__,
                "Amplitude recomputed 7 ways and period 6 ways, per kinetochore, to test whether the "
                "three-group relationships depend on the summary statistic.",
                key_column="definition")
