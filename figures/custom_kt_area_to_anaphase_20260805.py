#!/usr/bin/env python3
"""Kinetochore area over mitosis, cut at anaphase onset, with a HINGE trendline at metaphase onset.

USER 2026-08-05, exactly:
  "basically the kinetochore area over mitosis plot but without the data for lagging, just showing data
   (and basing trendlines) on data until anaphase onset. its ok to include the data from before metaphase
   onset but when building the trendline, the data before and after the start of metaphase should each
   contribute to its own portion of a trendline (like the trendline shouldn't jump at t=0 and it should
   remain continuous, but it should be determined completely from pre-metaphase data before t=0 and
   completely from post-metaphase data after t=0 (and again, data after anaphase onset should be left out."

THE TRENDLINE. Two independent straight lines, one per side, generally disagree at t=0 and the trend jumps
there — which she explicitly does not want. A continuous fit with a knot at t=0 gives both properties:

    y = a + b1*min(t,0) + b2*max(t,0)

b1 is identified ONLY by the points at t<0 and b2 ONLY by the points at t>0 (each side's slope is estimated
from that side alone), while the single shared value `a` at t=0 is what makes the two segments meet. That
shared join is the price of continuity and is unavoidable: two lines fitted with completely independent
intercepts cannot be made to touch.

Also per her earlier message the same day, split by ablation number (single vs triple) as well as state, so
this carries four series rather than two. Lagging is excluded. Every point after that cell's OWN anaphase
onset is dropped, never a cohort median.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
from kt_landmark_analysis import phase_times

lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"; os.makedirs(OUT, exist_ok=True)
SRC = [f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"]
SCRIPT = __file__

# USER 2026-08-05: "trim huge outliers, like trim the time to only be from -15mins before metaphase onset
# and onwards, and the area y-axis to just be 2um2 and below (so that the fitting of the plot can be good
# and visible)". These are applied to the DATA, not just the axes, so the hinge fit is computed on exactly
# what is drawn — trimming only the view would leave the trendline pulled by points off-screen.
TMIN = -15.0    # minutes before metaphase onset (user revised from -10 to -15, 2026-08-05)
AMAX = 2.0      # um^2

LM = list(csv.DictReader(open(SRC[0])))
ph = phase_times(sorted({r["batch"] for r in LM}))
_MASTER, _ = lib.load_master()
_NSIS = {r["Batch Name"]: (r.get("# Sisterless KTs", "") or "").strip() for r in _MASTER}

for r in LM:
    mt, at = ph.get(r["batch"], (None, None))
    try: tt = float(r["t_sec"])
    except Exception: tt = None
    r["tmeta"] = ((tt - mt) / 60.0) if (mt is not None and tt is not None) else None
    r["ana_min"] = ((at - mt) / 60.0) if (mt is not None and at is not None and at > mt) else None

def num(r, k):
    try: return float(r[k])
    except Exception: return None

# the window: everything up to that cell's OWN anaphase onset (pre-metaphase data KEPT), no lagging
WIN = [r for r in LM
       if r["label"] in ("paired", "polar")
       and r["tmeta"] is not None and r["ana_min"] is not None
       and r["tmeta"] <= r["ana_min"]
       and r["tmeta"] >= TMIN and num(r, "area_um2") is not None
       and num(r, "area_um2") <= AMAX]
NC = len({r["batch"] for r in WIN})
print(f"trim: t >= {TMIN} min, area <= {AMAX} um^2")
print(f"window: {len(WIN)} frames, {NC} cells, {len({r['track_id'] for r in WIN})} tracks "
      f"(lagging excluded; everything after each cell's own anaphase dropped)")

def hinge_fit(x, y):
    """y = a + b1*min(x,0) + b2*max(x,0). Returns (a, b1, b2, p1, p2, n_pre, n_post)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.column_stack([np.ones_like(x), np.minimum(x, 0.0), np.maximum(x, 0.0)])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    dof = max(1, len(y) - 3)
    s2 = float(resid @ resid) / dof
    try:
        cov = s2 * np.linalg.inv(A.T @ A); se = np.sqrt(np.diag(cov))
        p1 = 2 * (1 - st.t.cdf(abs(coef[1] / se[1]), dof)) if se[1] > 0 else np.nan
        p2 = 2 * (1 - st.t.cdf(abs(coef[2] / se[2]), dof)) if se[2] > 0 else np.nan
    except Exception:
        p1 = p2 = np.nan
    return coef[0], coef[1], coef[2], p1, p2, int((x < 0).sum()), int((x >= 0).sum())

GROUPS = [("polar", "1", "#e6820e", "-",  "o"), ("polar", "3", "#8a4b00", "--", "s"),
          ("paired", "1", "#3b6fb6", "-",  "o"), ("paired", "3", "#14385f", "--", "s")]
fig, ax = plt.subplots(figsize=(9.2, 5.6))
rows = []; notes = []
for lab, ns, col, ls, mk in GROUPS:
    # USER 2026-08-10: apply the standing cohort exclusion (prophase/drug/metaphase-abl/4-sis/Mad1).
    rs = [r for r in WIN if r["label"] == lab and _NSIS.get(r["batch"], "") == ns
          and not lib.plot_excluded(r["batch"]) and not lib.is_mad1(r["batch"])]
    if len(rs) < 8:
        notes.append(f"{ns}-sis {lab}: n={len(rs)} — too few to fit"); continue
    x = np.array([r["tmeta"] for r in rs], float); y = np.array([num(r, "area_um2") for r in rs], float)
    ax.scatter(x, y, s=4, color=col, alpha=0.10, lw=0)
    # USER 2026-08-10: a group's trend stops at THAT group's median metaphase duration.
    _cap = lib.trend_cap([r["batch"] for r in rs])
    if _cap is not None:
        _k = x <= _cap
        if _k.sum() >= 4:
            x, y = x[_k], y[_k]; lib.annotate_trend_cap(ax, _cap, color=col)
    # binned median + IQR
    lo, hi = np.percentile(x, [2, 98]); bins = np.linspace(lo, hi, 12); idx = np.digitize(x, bins)
    bx, bm, blo, bhi = [], [], [], []
    for bi in range(1, len(bins)):
        sel = y[idx == bi]
        if len(sel) >= 4:
            bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
            blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
    if bx:
        ax.plot(bx, bm, ls=ls, marker=mk, color=col, lw=1.6, ms=3.0, alpha=0.55)
        ax.fill_between(bx, blo, bhi, color=col, alpha=0.08)
    a, b1, b2, p1, p2, npre, npost = hinge_fit(x, y)
    xs_pre = np.linspace(min(x.min(), 0.0), 0.0, 20); xs_post = np.linspace(0.0, x.max(), 20)
    if npre >= 4:
        ax.plot(xs_pre, a + b1*xs_pre, color=col, lw=2.8, zorder=5)
    ax.plot(xs_post, a + b2*xs_post, color=col, lw=2.8, zorder=5)
    ax.plot([], [], color=col, lw=2.6, ls=ls, marker=mk, ms=3.5,
            label=f"{ns}-sis {lab} (n={len(x)}): pre {b1:+.4f}/min (p={p1:.2g}, n={npre}) · "
                  f"post {b2:+.4f}/min (p={p2:.2g}, n={npost})")
    for r in rs:
        rows.append([r["batch"], lab, ns, round(float(r["tmeta"]), 4), round(float(num(r, "area_um2")), 5)])
    print(f"  {ns}-sis {lab:7s}: n={len(x):5d}  pre-slope={b1:+.4f}/min (p={p1:.3g}, n={npre})  "
          f"post-slope={b2:+.4f}/min (p={p2:.3g}, n={npost})  join at t=0: {a:.3f} um^2")
    # coverage: where does this group's data actually stop, as a fraction of metaphase?
    fr = [r["tmeta"]/r["ana_min"] for r in rs if r["ana_min"]]
    if fr: notes.append(f"{ns}-sis {lab}: data ends at {np.percentile(fr,95):.2f} of metaphase")

ax.axvline(0, color="#333", ls=":", lw=1.2)
ax.text(0, ax.get_ylim()[1], " metaphase onset", ha="left", va="top", fontsize=7.5, color="#333")
ax.set_xlim(TMIN, None); ax.set_ylim(0, AMAX)
ax.set_xlabel(f"minutes from metaphase onset  (kept: {TMIN:g} min to that cell's own anaphase onset)")
ax.set_ylabel("kinetochore area (µm²)")
ax.set_title("Kinetochore area over mitosis — to anaphase onset, lagging excluded\n"
             "trendline is continuous at t=0; the slope each side is fitted ONLY from that side's data",
             loc="left", fontweight="bold", fontsize=10)
ax.legend(fontsize=6.6, loc="upper right")
if notes:
    ax.text(0.005, -0.155, "  ·  ".join(notes[:4]), transform=ax.transAxes, fontsize=6.6, color="#666")
fig.tight_layout(); fig.savefig(f"{OUT}/G6time_area_to_anaphase.png", dpi=200, bbox_inches="tight"); plt.close(fig)
lib.record_plot("G6time_area_to_anaphase",
                ["batch", "label", "n_sisterless", "t_min_from_meta", "area_um2"], rows,
                {"window": "up to each cell's OWN anaphase onset; pre-metaphase data retained",
                 "lagging": "excluded", "states": "polar + paired, split by # Sisterless KTs (1/3)",
                 "trendline": "continuous hinge at t=0: y = a + b1*min(t,0) + b2*max(t,0); b1 from pre-metaphase "
                              "points only, b2 from post-metaphase points only, shared join value at t=0"},
                script=SCRIPT, caption="Kinetochore area over mitosis to anaphase (hinged at metaphase onset)",
                source=SRC, key_column="batch")
print(f"-> {OUT}/G6time_area_to_anaphase.png")
