#!/usr/bin/env python3
"""Prometaphase ablations: time from first ablation to metaphase onset vs metaphase duration.

USER 2026-08-05: "make a plot for ablations done in prometaphase: x-axis is time between first ablation
and metaphase onset; y-axis is metaphase duration (make one plot for single and one plot for triple, and
for each batch there should just be 1 point)"

ONE POINT PER BATCH. Both quantities are per-cell (the cell has one metaphase onset, one anaphase onset,
one first ablation), so no chromosome-level stacking — the failure mode called out on G3_chromo_length,
where several chromosomes from one cell stacked vertically at that cell's single duration.

x  ablation -> metaphase onset, via lib.abl_to_meta_min (stored master interval first, then the
   metastart fallback, tagged so recovered points are distinguishable)
y  metaphase duration = Anaphase Onset - Metaphase Start (lib.mitotic_duration_min)
Cohorts split by "# Sisterless KTs" (1 vs 3), never by batch name. Drugs, Mad1, double-chromosome and
the standing review exclusions are dropped.
"""
import sys, os, csv
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from scipy import stats as st
import lib

lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group2"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__

data, _ = lib.load_master_plots()
dbl = lib.double_chromosome_batches()
COL = {"1": "#1b7837", "3": "#762a83"}

def keep(r):
    b = r["Batch Name"]
    return (r.get("Exclude") not in ("Yes", "yes") and b not in dbl
            and not lib.is_drug(b) and not lib.is_mad1(b) and not lib.excluded(b))

pts = {"1": [], "3": []}; rows = []; nfall = 0
for r in data:
    if not keep(r): continue
    if not (r.get("Phase of Ablations", "") or "").strip().lower().startswith("promet"): continue
    ns = (r.get("# Sisterless KTs") or "").strip()
    if ns not in ("1", "3"): continue
    x, src = lib.abl_to_meta_min(r, fallback_metastart=True)
    d, ok = lib.mitotic_duration_min(r)
    if x is None or not ok: continue
    if src == "metastart": nfall += 1
    pts[ns].append((x, d, r["Batch Name"], src))
    rows.append([r["Batch Name"], ns, round(x, 3), round(d, 3), src])

print(f"prometaphase cells with both values: 1-sis={len(pts['1'])}  3-sis={len(pts['3'])}  "
      f"({nfall} via the metastart fallback)")

stats_out = {}
for ns in ("1", "3"):
    v = pts[ns]
    if len(v) < 3:
        print(f"  skip {ns}-sisterless (n={len(v)})"); continue
    x = np.array([p[0] for p in v]); y = np.array([p[1] for p in v])
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    for xi, yi, _b, src in v:
        ax.scatter([xi], [yi], s=46, color=COL[ns], alpha=.85,
                   edgecolor=("k" if src == "metastart" else "white"),
                   linewidth=(0.9 if src == "metastart" else 0.4), zorder=3)
    rho, p = st.spearmanr(x, y)
    if len(x) >= 3:
        m, c = np.polyfit(x, y, 1); xr = np.linspace(x.min(), x.max(), 20)
        ax.plot(xr, m * xr + c, "--", color=COL[ns], lw=2.0, zorder=4)
    ax.set_xlabel("first ablation to metaphase onset (min)")
    ax.set_ylabel("Metaphase duration (MM:SS)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v_, _: lib.mmss(v_) if v_ >= 0 else ""))
    lab = "single" if ns == "1" else "triple"
    ax.set_title(f"Prometaphase ablations — {lab} ({ns}-sisterless)\n"
                 f"one point per cell · n={len(x)} · Spearman ρ={rho:+.2f}, p={p:.3g}"
                 + ("  · black-edged = interval recovered from Metaphase Start" if any(s == "metastart" for *_x, s in v) else ""),
                 loc="left", fontweight="bold", fontsize=9.5)
    fig.tight_layout()
    pid = f"G2_ablmeta_vs_duration_{lab}"
    fig.savefig(f"{OUT}/{pid}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    stats_out[lab] = {"n": len(x), "rho": round(float(rho), 3), "p": float(p),
                      "median_x_min": round(float(np.median(x)), 2), "median_y_min": round(float(np.median(y)), 2)}
    lib.record_plot(pid, ["batch", "n_sisterless", "abl_to_meta_min", "metaphase_duration_min", "x_source"],
                    [r_ for r_ in rows if r_[1] == ns],
                    {"unit": "one point per cell", "phase": "prometaphase ablations only",
                     "x": "first ablation -> metaphase onset", "y": "metaphase duration",
                     "spearman": stats_out[lab]}, SCRIPT,
                    f"Prometaphase ablations: ablation-to-metaphase interval vs metaphase duration ({lab})")
    print(f"  {lab:6s} n={len(x):3d}  rho={rho:+.3f}  p={p:.3g}  -> {pid}.png")
