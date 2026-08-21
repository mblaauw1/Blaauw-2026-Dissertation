#!/usr/bin/env python3
"""Do kinetochores SHRINK over metaphase, and does that shrinkage track their DISTORTION?

USER 2026-08-05: "well the paired sisters start out bigger too, right? and then shrink as they spend time
oscillating at the metaphase plate. does that shrink in size correlate with any change in the distortion
pattern?"

Her premise holds, and the answer is yes for paired kinetochores and no for polar ones.

THE CONFOUND THIS FIGURE EXISTS TO RULE OUT
-------------------------------------------
Distortion is a ratio of two extents, so it is size-normalised in principle. But it is measured on a
diffraction-limited object: the PSF blurs both axes by a similar absolute amount, which compresses the
measured ratio TOWARD 1 more strongly the smaller the object. So "small kinetochores have different
distortion" is exactly what pure optics would produce, and an area-distortion correlation could be an
artefact rather than biology.

The test is directional. If the PSF drives it, smaller area must read NEARER to 1, i.e. rho(area, |d-1|)
must be POSITIVE. Measured: rho = -0.128, p=1.4e-06 — the OPPOSITE sign. Smaller paired kinetochores sit
FURTHER from 1. Whatever produces the relationship, it is not the compression the PSF imposes.

WHAT IT CANNOT RULE OUT (stated on the figure, not just here)
Area and distortion are derived from the SAME traced outline, so they are not independent measurements. A
trace that clips the object shrinks its area and changes its extents together. The opposite-to-PSF
direction argues against that being the whole story, but it does not eliminate it.

Panels:
  A  area over metaphase, per state, with per-track slopes (the premise)
  B  within-track rho(area, distortion) per state — one point per kinetochore
  C  the PSF confound test: distortion vs area by quartile, against the direction optics predicts
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
from kt_landmark_analysis import phase_times

lib.apply_style()
csv.field_size_limit(10 ** 9)
ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
MIN_FRAMES = 8

T = list(csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv")))
L = list(csv.DictReader(open(f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv")))
# USER 2026-08-06: prophase ablations are excluded from every plot that has no prophase group.
# This file reads annotation CSVs directly, so the shared gates do not reach it.
T = [r for r in T if not lib.is_prophase_ablation(r.get("batch",""))]
L = [r for r in L if not lib.is_prophase_ablation(r.get("batch",""))]

AREA = {(r["track_id"], r["frame"]): r for r in L}
ph = phase_times(sorted({r["batch"] for r in T}))


def f(r, k):
    try: return float(r[k])
    except Exception: return None


rec = collections.defaultdict(list)      # track_id -> [(t_min, area, distortion, label, batch)]
for r in T:
    if r.get("outlier") == "1": continue
    a = AREA.get((r["track_id"], r["frame"]))
    if not a: continue
    ar = f(a, "area_um2"); d = f(r, "spindle_strain"); t = f(r, "t_sec")
    mt, at = ph.get(r["batch"], (None, None))
    if None in (ar, d, t, mt, at) or not (mt <= t <= at): continue
    rec[r["track_id"]].append(((t - mt) / 60.0, ar, d, r["label"], r["batch"]))

rows = [[tid, x[4], x[3], round(x[0], 4), round(x[1], 5), round(x[2], 5)]
        for tid, v in rec.items() for x in v]
print(f"tracks={len(rec)}  frames={len(rows)}")

fig, axs = plt.subplots(1, 3, figsize=(16.2, 5.2))
stats_out = {}

# ---- A: area over metaphase ---------------------------------------------------------------------
axA = axs[0]
for lab in ("paired", "polar", "lagging"):
    pts = [(x[0], x[1]) for v in rec.values() for x in v if x[3] == lab]
    if len(pts) < 20: continue
    X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
    axA.scatter(X, Y, s=4, color=COL[lab], alpha=0.10, lw=0)
    bins = np.linspace(0, np.percentile(X, 97), 12); idx = np.digitize(X, bins)
    bx, bm = [], []
    for bi in range(1, len(bins)):
        sel = Y[idx == bi]
        if len(sel) >= 5: bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
    slopes = []
    for tid, v in rec.items():
        vv = [x for x in v if x[3] == lab]
        if len(vv) >= 6:
            slopes.append(float(np.polyfit([x[0] for x in vv], [x[1] for x in vv], 1)[0]))
    w = st.wilcoxon(slopes)[1] if len(slopes) >= 6 else float("nan")
    if bx: axA.plot(bx, bm, "-o", color=COL[lab], lw=2.2, ms=4)
    axA.plot([], [], "-o", color=COL[lab], lw=2.2, ms=4,
             label=f"{lab} (n={len(X)}, {len(slopes)} tracks)\n  median slope {np.median(slopes):+.4f} µm²/min, "
                   f"shrinking in {sum(1 for s_ in slopes if s_ < 0)}/{len(slopes)}, p={w:.3g}")
    stats_out[f"{lab}_area"] = {"n_frames": len(X), "n_tracks": len(slopes),
                                "median_area_um2": round(float(np.median(Y)), 4),
                                "median_slope_um2_per_min": round(float(np.median(slopes)), 5),
                                "wilcoxon_p": float(w)}
axA.set_xlabel("minutes from metaphase onset"); axA.set_ylabel("kinetochore area (µm²)")
axA.set_title("A · Do kinetochores shrink over metaphase?", loc="left", fontweight="bold", fontsize=9.5)
axA.legend(fontsize=6.2, loc="upper right")

# ---- B: within-track area vs distortion -----------------------------------------------------------
axB = axs[1]; pos = 0; xt, xl = [], []
for lab in ("paired", "polar"):
    rs = []
    for tid, v in rec.items():
        vv = [x for x in v if x[3] == lab]
        if len(vv) >= MIN_FRAMES:
            r_ = st.spearmanr([x[1] for x in vv], [x[2] for x in vv])[0]
            if np.isfinite(r_): rs.append(r_)
    if len(rs) < 4: continue
    lib.journal_violin(axB, rs, pos, COL[lab], alpha=0.30, lw=1.0)
    axB.scatter(np.full(len(rs), pos) + (np.random.RandomState(pos).rand(len(rs))-.5)*0.22, rs,
                s=lib.VIOLIN_DOT_S, color=COL[lab], alpha=.85, edgecolor="white", lw=.4, zorder=3)
    lib.violin_stats(axB, rs, pos, COL[lab])
    npos = sum(1 for r_ in rs if r_ > 0)
    p = st.binomtest(npos, len(rs)).pvalue
    axB.text(pos, max(rs), f"med {np.median(rs):+.2f}\n{npos}/{len(rs)} +ve\np={p:.3g}",
             ha="center", va="bottom", fontsize=7)
    stats_out[f"{lab}_within_track_rho"] = {"n_tracks": len(rs), "median_rho": round(float(np.median(rs)), 4),
                                            "n_positive": npos, "sign_test_p": float(p)}
    xt.append(pos); xl.append(f"{lab}\n({len(rs)} KTs)"); pos += 1
axB.axhline(0, color="#888", ls=":", lw=1.0)
# the per-violin "med / n +ve / p" labels are drawn just above each violin's maximum and ran into the
# two-line title; give the axis headroom for them instead of shrinking the labels
_yl = axB.get_ylim()
axB.set_ylim(_yl[0], _yl[1] + (_yl[1] - _yl[0]) * 0.30)
axB.set_xticks(xt); axB.set_xticklabels(xl, fontsize=9)
axB.set_ylabel("within-kinetochore Spearman ρ (area vs distortion)")
axB.set_title("B · Does a shrinking kinetochore change its distortion?\n"
              "one point per kinetochore, over its own metaphase frames",
              loc="left", fontweight="bold", fontsize=9.5)

# ---- C: the PSF confound test ---------------------------------------------------------------------
axC = axs[2]
allp = [(x[1], x[2]) for v in rec.values() for x in v if x[3] == "paired"]
A = np.array([p[0] for p in allp]); D = np.array([p[1] for p in allp])
rho_d, p_d = st.spearmanr(A, D)
rho_a, p_a = st.spearmanr(A, np.abs(D - 1))
q = np.quantile(A, [0, .25, .5, .75, 1.])
mids, meds, absd = [], [], []
for i in range(4):
    m = (A >= q[i]) & (A <= q[i+1])
    mids.append(float(np.median(A[m]))); meds.append(float(np.median(D[m])))
    absd.append(float(np.median(np.abs(D[m] - 1))))
axC.scatter(A, D, s=4, color=COL["paired"], alpha=0.10, lw=0)
axC.plot(mids, meds, "-o", color=COL["paired"], lw=2.4, ms=6, label="median distortion by area quartile")
axC.plot(mids, absd, "--s", color="#a33", lw=2.0, ms=5, label="median |distortion − 1| (the PSF test)")
axC.axhline(1.0, color="#888", ls=":", lw=1.0)
axC.set_xlabel("kinetochore area (µm²)")
axC.set_ylabel("distortion along the spindle axis")
axC.set_title("C · Is it just the PSF?  NO — the sign is wrong for that\n"
              f"ρ(area, distortion)={rho_d:+.2f} (p={p_d:.1g})   "
              f"ρ(area, |d−1|)={rho_a:+.2f} (p={p_a:.1g})",
              loc="left", fontweight="bold", fontsize=9.5)
axC.legend(fontsize=7, loc="best")
axC.text(0.0, -0.145,
         "The PSF compresses a SMALLER object's ratio toward 1, so if optics drove this, ρ(area, |d−1|) "
         "would be POSITIVE. It is negative: smaller paired\nkinetochores sit FURTHER from 1. "
         "Not ruled out: area and distortion come from the same traced outline, so a clipped trace moves "
         "both together.",
         transform=axC.transAxes, fontsize=6.8, color="#555", va="top", linespacing=1.5)
stats_out["psf_test"] = {"rho_area_distortion": round(float(rho_d), 4), "p": float(p_d),
                         "rho_area_abs_dev_from_1": round(float(rho_a), 4), "p_abs": float(p_a),
                         "psf_prediction": "positive rho(area,|d-1|); observed NEGATIVE, so not the PSF"}

fig.suptitle("Kinetochore SIZE over metaphase, and whether shrinking changes DISTORTION",
             x=.005, ha="left", fontweight="bold", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.955))
fig.savefig(f"{OUT}/G6_area_vs_distortion_over_metaphase.png", dpi=180, bbox_inches="tight")
plt.close(fig)
lib.record_plot("G6_area_vs_distortion_over_metaphase",
                ["track_id", "batch", "label", "t_min_from_meta", "area_um2", "distortion"], rows,
                stats_out, SCRIPT,
                "Kinetochore area over metaphase and its relationship to spindle-axis distortion",
                source=[f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv",
                        f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv"], key_column="batch")
for k, v in stats_out.items(): print(f"  {k}: {v}")
print(f"-> {OUT}/G6_area_vs_distortion_over_metaphase.png")
