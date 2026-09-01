#!/usr/bin/env python3
"""Plots 182, 183, 184, 185, 187 rebuilt from the TRACED KINETOCHORE OUTLINES (user 2026-07-28).

Same change as 186: no circle/disk regions, no TrackMate positions. Every intensity here is measured INSIDE
her traced kt_outline polygon, with the PER-FRAME cytosol level subtracted, and out-of-focus frames already
dropped upstream. Source: annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv.

  182  G4_kt_intensity_time                 polar KT signal vs time since first ablation
  183  G4_kt_intensity_time_trendscaled     the same, axes fit to the TRENDS (points may run off-plot)
  183b G4_kt_intensity_metaphase_trendscaled  NEW — metaphase onset -> anaphase only. Trendlines are REFIT on
       that window and each cohort's line is drawn only out to THAT cohort's mean metaphase duration.
  184  G4_kt_intensity_time_scaled01        per-cell normalised to its own first measured value
  185  G4_kt_intensity_diff                 polar - plate-aligned difference over time (time-matched frames)
  187  G4_kt_intensity_polar_vs_plate_MANUAL   per-FRAME polar vs plate distribution (186 is the per-CELL view)

Pre-rebuild figures are copied to _retired_figs/*_PRE_OUTLINE_20260728.*
"""
import sys, os, csv, collections, shutil, glob
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
SRC = f"{ROOT}/annotations/KT_FLUOR_CYTOSOLNORM_20260728.csv"
OUT = f"{ROOT}/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
RET = f"{ROOT}/ablation_figures_20260625/_retired_figs"; os.makedirs(RET, exist_ok=True)
CCOL = {"1": "#3b6fb6", "2": "#7a5cff", "3": "#d1495b"}
COHORTS = ["1", "2", "3"]

for base in ["G4_kt_intensity_time", "G4_kt_intensity_time_trendscaled", "G4_kt_intensity_time_scaled01",
             "G4_kt_intensity_diff", "G4_kt_intensity_polar_vs_plate_MANUAL"]:
    for f in glob.glob(f"{ROOT}/ablation_figures_20260625/**/{base}.png", recursive=True):
        dst = f"{RET}/{base}_PRE_OUTLINE_20260728.png"
        if not os.path.exists(dst): shutil.copy2(f, dst)

master, _ = lib.load_master(); M = {r["Batch Name"]: r for r in master}
def mg(b, k): return (M.get(b, {}) or {}).get(k, "") or ""
def coh(b):
    n = mg(b, "# Sisterless KTs").strip()
    return n if n in COHORTS else None
def hms(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try: q = [float(x) for x in s.split(":")]
    except ValueError: return None
    v = q[0]*3600 + q[1]*60 + q[2] if len(q) == 3 else (q[0]*60 + q[1] if len(q) == 2 else q[0])
    return -v if neg else v

rows = []
for r in csv.DictReader(open(SRC, newline="")):
    try: sig = float(r["signal"]); t = float(r["t_sec"])
    except Exception: continue
    tm = None
    try: tm = float(r["tmeta"])
    except Exception: pass
    c = coh(r["batch"])
    if c is None: continue
    # USER 2026-08-10: standing cohort exclusion (prophase / drug / metaphase-abl / 4-sis / Mad1).
    if lib.plot_excluded(r["batch"]) or lib.is_mad1(r["batch"]): continue
    rows.append(dict(batch=r["batch"], label=r["label"], frame=r["frame"], t_min=t/60.0,
                     tmeta=tm, sig=sig, coh=c))
POL = [r for r in rows if r["label"] == "polar"]
print(f"{len(rows)} outline measurements ({len(POL)} polar) across {len({r['batch'] for r in rows})} cells")

# per-cell mean metaphase duration, by cohort
metadur = collections.defaultdict(list)
for b in {r["batch"] for r in rows}:
    mt, at = hms(mg(b, "Metaphase Start (s)")), hms(mg(b, "Anaphase Onset (s)"))
    c = coh(b)
    if mt is not None and at is not None and at > mt and c:
        metadur[c].append((at - mt) / 60.0)
# USER 2026-08-10: cap each cohort trend at its MEDIAN metaphase duration (was the MEAN, which sits past
# the median and let the trend overrun).
MEDIAN_DUR = {c: float(np.median(v)) for c, v in metadur.items() if v}
print("  median metaphase duration per cohort:", {k: round(v, 1) for k, v in MEDIAN_DUR.items()})


def save(fig, name, cap, header, data):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try: lib.record_plot(name, header, data, {"family": "kt_intensity"}, script=__file__,
                         caption=cap, source=[SRC], key_column="batch")
    except Exception: pass
    print("  " + name)


def scatter_trend(ax, subset, xkey, trendscaled=False, xcap=None):
    """scatter + per-cohort linear fit; returns the y-range spanned by the fits only."""
    ylo, yhi = np.inf, -np.inf
    for c in COHORTS:
        d = [r for r in subset if r["coh"] == c and r[xkey] is not None]
        if len(d) < 8: continue
        x = np.array([r[xkey] for r in d]); y = np.array([r["sig"] for r in d])
        keep = lib.robust_keep(x, y); x, y = x[keep], y[keep]
        ax.scatter(x, y, s=6, color=CCOL[c], alpha=0.16, lw=0)
        b_, a_ = np.polyfit(x, y, 1)
        xmax = min(x.max(), xcap[c]) if (xcap and c in xcap) else x.max()
        xf = np.linspace(max(0, x.min()), xmax, 20)
        yf = a_ + b_*xf
        ax.plot(xf, yf, "-", color=CCOL[c], lw=2.6, zorder=5)
        ylo = min(ylo, yf.min()); yhi = max(yhi, yf.max())
        rho, pv = st.spearmanr(x, y)
        ax.plot([], [], color=CCOL[c], lw=2.6,
                label=f"{c}-sisterless: slope={b_:+.2f}/min, ρ={rho:+.2f}, p={pv:.1g} (n={len(x)})")
    if trendscaled and np.isfinite(ylo):
        pad = (yhi - ylo) * 0.35 or 5
        ax.set_ylim(ylo - pad, yhi + pad)
    return ylo, yhi


# ── 182 ───────────────────────────────────────────────────────────────────────────────────────────

# ── 183 (kept: time since first ablation, trend-scaled) ──────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7.8, 5.2))
scatter_trend(ax, POL, "t_min", trendscaled=True)
ax.set_xlabel("time since first ablation (min)")
ax.set_ylabel("polar KT eYFP-Cdc20 signal")
ax.set_title("Polar/sisterless-KT intensity vs time (trend-scaled) — TRACED OUTLINES\n"
             "axes fit the trend lines; individual points may run off-plot",
             loc="left", fontweight="bold", fontsize=9.5)
ax.legend(fontsize=7.5)
save(fig, "G4_kt_intensity_time_trendscaled", "Polar KT intensity vs time, trend-scaled (traced outlines)",
     ["batch", "t_min", "signal", "cohort"], [])

# ── the METAPHASE ONSET -> ANAPHASE subset, used by 182 / 183b / 184 / 185 ───────────────────────
sub = [r for r in POL if r["tmeta"] is not None and r["tmeta"] >= 0]
sub = [r for r in sub
       if (lambda mt, at: mt is not None and at is not None and at > mt
           and r["tmeta"] <= (at - mt)/60.0)(hms(mg(r["batch"], "Metaphase Start (s)")),
                                             hms(mg(r["batch"], "Anaphase Onset (s)")))]
# ── 182 — METAPHASE ONSET to ANAPHASE (user 2026-07-28: only 183 keeps the ablation axis) ───────
fig, ax = plt.subplots(figsize=(7.8, 5.2))
scatter_trend(ax, sub, "tmeta", xcap=MEDIAN_DUR)
for c in COHORTS:
    if c in MEDIAN_DUR: ax.axvline(MEDIAN_DUR[c], ls=":", color=CCOL[c], lw=1.1, alpha=0.8)
ax.set_xlim(left=0)
ax.set_xlabel("minutes from metaphase onset (each cell cut at its own anaphase onset)")
ax.set_ylabel("polar KT eYFP-Cdc20 signal\n(inside outline, - per-frame cytosol)")
ax.set_title("Polar/sisterless-KT intensity, METAPHASE ONSET to ANAPHASE - TRACED OUTLINES\n"
             "trendlines fit on this window; each cohort's line stops at its MEAN metaphase duration",
             loc="left", fontweight="bold", fontsize=9.2)
ax.legend(fontsize=7.5)
save(fig, "G4_kt_intensity_time", "Polar KT intensity, metaphase onset to anaphase (traced outlines)",
     ["batch", "t_from_metaphase_min", "signal", "cohort"],
     [[r["batch"], round(r["tmeta"], 2), r["sig"], r["coh"]] for r in sub])

fig, ax = plt.subplots(figsize=(7.8, 5.2))
scatter_trend(ax, sub, "tmeta", trendscaled=True, xcap=MEDIAN_DUR)
for c in COHORTS:
    if c in MEDIAN_DUR:
        ax.axvline(MEDIAN_DUR[c], ls=":", color=CCOL[c], lw=1.1, alpha=0.8)
ax.set_xlim(left=0)
ax.set_xlabel("minutes from metaphase onset (each cell cut at its own anaphase onset)")
ax.set_ylabel("polar KT eYFP-Cdc20 signal")
ax.set_title("Polar-KT intensity, METAPHASE ONSET to ANAPHASE (trend-scaled) — TRACED OUTLINES\n"
             "trendlines refit on this window; each cohort's line stops at that cohort's MEAN metaphase duration "
             + ", ".join(f"{c}-sis={MEDIAN_DUR[c]:.1f}min" for c in COHORTS if c in MEDIAN_DUR),
             loc="left", fontweight="bold", fontsize=8.6)
ax.legend(fontsize=7.5)
save(fig, "G4_kt_intensity_metaphase_trendscaled",
     "Polar KT intensity metaphase->anaphase, trend-scaled, capped at each cohort's mean duration",
     ["batch", "t_from_metaphase_min", "signal", "cohort"],
     [[r["batch"], round(r["tmeta"], 2), r["sig"], r["coh"]] for r in sub])

# ── 184 per-cell normalised to its own first value ───────────────────────────────────────────────
firstm = {}
for r in sorted(sub, key=lambda r: (r["batch"], r["tmeta"])):
    firstm.setdefault(r["batch"], r["sig"])
normm = [dict(r, sig=(r["sig"] / firstm[r["batch"]] if firstm.get(r["batch"]) else np.nan)) for r in sub]
normm = [r for r in normm if np.isfinite(r["sig"])]
fig, ax = plt.subplots(figsize=(7.8, 5.2))
scatter_trend(ax, normm, "tmeta", xcap=MEDIAN_DUR)
for c in COHORTS:
    if c in MEDIAN_DUR: ax.axvline(MEDIAN_DUR[c], ls=":", color=CCOL[c], lw=1.1, alpha=0.8)
ax.axhline(1.0, ls="--", color="#666", lw=1.0)
ax.set_xlim(left=0)
ax.set_xlabel("minutes from metaphase onset (each cell cut at its own anaphase onset)")
ax.set_ylabel("polar KT signal / that cell's value at metaphase onset")
ax.set_title("Polar-KT intensity per-cell normalised, METAPHASE ONSET to ANAPHASE - TRACED OUTLINES\n"
             "baseline = metaphase onset; trendlines fit on this window, capped at each cohort's mean duration",
             loc="left", fontweight="bold", fontsize=9.0)
ax.legend(fontsize=7.5)
save(fig, "G4_kt_intensity_time_scaled01", "Polar KT intensity per-cell normalised, metaphase onset to anaphase",
     ["batch", "t_from_metaphase_min", "signal_ratio", "cohort"],
     [[r["batch"], round(r["tmeta"], 2), round(r["sig"], 4), r["coh"]] for r in normm])

# ── 185 polar − plate difference over time (time-matched frames) ─────────────────────────────────
byf = collections.defaultdict(lambda: {"polar": [], "paired": []})
for r in rows:
    byf[(r["batch"], r["frame"])][r["label"]].append(r)
diff = []
for (b, f), v in byf.items():
    if not v["polar"] or not v["paired"]: continue
    d = float(np.median([z["sig"] for z in v["polar"]]) - np.median([z["sig"] for z in v["paired"]]))
    diff.append(dict(batch=b, t_min=v["polar"][0]["t_min"], sig=d, coh=v["polar"][0]["coh"], tmeta=v["polar"][0]["tmeta"]))
diffm_all = []
for _d in diff:
    if _d["tmeta"] is None or _d["tmeta"] < 0: continue
    _mt, _at = hms(mg(_d["batch"], "Metaphase Start (s)")), hms(mg(_d["batch"], "Anaphase Onset (s)"))
    if _mt is None or _at is None or _at <= _mt: continue
    if _d["tmeta"] <= (_at - _mt) / 60.0: diffm_all.append(_d)
fig, ax = plt.subplots(figsize=(7.8, 5.2))
scatter_trend(ax, diffm_all, "tmeta", xcap=MEDIAN_DUR)
for c in COHORTS:
    if c in MEDIAN_DUR: ax.axvline(MEDIAN_DUR[c], ls=":", color=CCOL[c], lw=1.1, alpha=0.8)
ax.set_xlim(left=0)
ax.axhline(0, ls="--", color="#666", lw=1.2)
ax.set_xlabel("minutes from metaphase onset (each cell cut at its own anaphase onset)")
ax.set_ylabel("polar − plate-aligned signal (a.u.)")
med = float(np.median([d["sig"] for d in diffm_all])) if diffm_all else float("nan")
ax.set_title(f"Polar - plate-aligned KT signal, METAPHASE ONSET to ANAPHASE - time-matched frames\n"
             f"{len(diffm_all)} matched frames, {len({d['batch'] for d in diffm_all})} cells; median {med:+.1f} a.u.; "
             f"trendlines fit here, capped at each cohort's mean metaphase duration",
             loc="left", fontweight="bold", fontsize=9.2)
ax.legend(fontsize=7.5)
save(fig, "G4_kt_intensity_diff", "Polar minus plate-aligned KT signal over time (traced outlines, time-matched)",
     ["batch", "t_from_metaphase_min", "diff", "cohort"],
     [[d["batch"], round(d["tmeta"], 2), round(d["sig"], 2), d["coh"]] for d in diffm_all])

# ── 187 per-FRAME polar vs plate distribution (186 is the per-CELL view) ─────────────────────────
pol_f = [np.median([z["sig"] for z in v["polar"]]) for v in byf.values() if v["polar"] and v["paired"]]
pla_f = [np.median([z["sig"] for z in v["paired"]]) for v in byf.values() if v["polar"] and v["paired"]]
fig, ax = plt.subplots(figsize=(6.4, 5.2))
for i, (d, c, lab) in enumerate(((pla_f, "#1b5e20", "plate-aligned KT"), (pol_f, "#762a83", "polar KT"))):
    lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0, min_n=3)
    ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .22, d, s=lib.VIOLIN_DOT_S, color=c, alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
    ax.hlines(np.median(d), i - 0.32, i + 0.32, color=c, lw=2.6)
pw = st.wilcoxon(pol_f, pla_f)[1]
ax.set_xticks([0, 1]); ax.set_xticklabels([f"plate-aligned KT\n(traced outline)\nn={len(pla_f)}",
                                           f"polar KT\n(traced outline)\nn={len(pol_f)}"])
ax.set_ylabel("eYFP-Cdc20 signal inside the outline")
ax.set_title(f"eYFP-Cdc20 polar vs plate KT — ALL MANUAL, per FRAME (paired within cell+frame)\n"
             f"Wilcoxon p={pw:.2g}; med {np.median(pol_f):.1f} vs {np.median(pla_f):.1f} a.u. "
             f"(186 is the per-CELL view of the same data)",
             loc="left", fontweight="bold", fontsize=8.6)
save(fig, "G4_kt_intensity_polar_vs_plate_MANUAL",
     "Polar vs plate-aligned KT signal, all manual outlines, per matched frame",
     ["frame_index", "plate_signal", "polar_signal"],
     [[i, round(q, 2), round(p, 2)] for i, (q, p) in enumerate(zip(pla_f, pol_f))])
print("done")
