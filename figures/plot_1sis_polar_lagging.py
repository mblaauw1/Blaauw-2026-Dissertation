"""1-sisterless ON-TARGET cells: metaphase duration split by (polar / no-polar) and (lagging / no-lagging),
four groups on one plot, dots colored by ablation phase (prophase vs prometaphase vs metaphase)."""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.lines import Line2D
from scipy import stats as _st
import lib
lib.apply_style()
OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"
data, _ = lib.load_master()

def yn(v):
    v = (v or "").strip().lower()
    return "Yes" if v == "yes" else "No" if v == "no" else None
def mdur(r):
    d, ok = lib.mitotic_duration_min(r); return d if ok else None
def phase(r):
    p = (r.get("Phase of Ablations", "") or "").strip().lower()
    ph="Prophase" if p.startswith("proph") else "Prometaphase" if p.startswith("promet") else "Metaphase" if p.startswith("metaph") else None
    return "Prometaphase" if (ph=="Prophase" and lib.is_v2_prometaphase(r.get("Batch Name",""))) else ph   # USER 2026-07-16: v2 binning
def is_1sis_ontarget(r):
    return (r.get("# Sisterless KTs", "").strip() == "1"
            and r.get("On-Target / Off-Target", "").strip() == "On-target"
            and r.get("Exclude") not in ("Yes", "yes")
            and not lib.is_mad1(r["Batch Name"])
            and not lib.plot_excluded(r["Batch Name"]))   # +drug/Exclude/REVIEW_EXCLUDE (low-dose-noc leaked in)

cells = [r for r in data if is_1sis_ontarget(r)]
PHCOL = {"Prophase": "#1b7837", "Prometaphase": "#2166ac", "Metaphase": "#762a83"}
GROUPS = [
    ("Polar",       lambda r: yn(r.get("Polar Chromosomes", "")) == "Yes"),
    ("No polar",    lambda r: yn(r.get("Polar Chromosomes", "")) == "No"),
    ("Lagging",     lambda r: yn(r.get("Lagging Chromosomes", "")) == "Yes"),
    ("No lagging",  lambda r: yn(r.get("Lagging Chromosomes", "")) == "No"),
]
fig, ax = plt.subplots(figsize=(9, 5.8)); rows = []
by = {}
for i, (lab, filt) in enumerate(GROUPS):
    d = []; ph = []
    for r in cells:
        if not filt(r): continue
        m = mdur(r); p = phase(r)
        if m is None or p not in ("Prophase", "Prometaphase"): continue   # exclude metaphase-ablated (and unknown-phase)
        d.append(m); ph.append(p); rows.append([lab, r["Batch Name"], round(m, 3), p])
    by[lab] = d
    if len(d) >= 2:
        for bd in ax.violinplot([d], positions=[i], widths=.7, showextrema=False)['bodies']:
            bd.set_facecolor("#cccccc"); bd.set_alpha(.22); bd.set_edgecolor("#999")
    xs = np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .24
    for x, y, p in zip(xs, d, ph):
        ax.scatter(x, y, s=30, color=PHCOL.get(p, "#888"), alpha=.85, edgecolor="white", lw=.4, zorder=3)
    if d:
        ax.hlines(np.median(d), i - .3, i + .3, color="#222", lw=2.4, zorder=4)
        ax.hlines(np.mean(d), i - .24, i + .24, color="#222", lw=1.2, ls=(0, (2, 1.5)), zorder=4)
        ax.text(i, max(d) + 1, f"med {lib.mmss(np.median(d))}\nN={len(d)}", ha="center", va="bottom", fontsize=8)

# stats: Polar vs No-polar, Lagging vs No-lagging (Mann-Whitney)
_ymax = max((r[2] for r in rows), default=1); _yr = _ymax * 0.05; _top = _ymax
def _stars(p): return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
for k, (a, b, ai, bi) in enumerate([("Polar", "No polar", 0, 1), ("Lagging", "No lagging", 2, 3)]):
    da, db = by.get(a, []), by.get(b, [])
    if len(da) >= 2 and len(db) >= 2:
        _, pv = _st.mannwhitneyu(da, db, alternative="two-sided")
        yy = _ymax + _yr * (1.6 + k * 2.4)
        ax.plot([ai, ai, bi, bi], [yy, yy + _yr * .3, yy + _yr * .3, yy], color="#333", lw=1.0, clip_on=False)
        ax.text((ai + bi) / 2, yy + _yr * .34, f"{a} vs {b}: {_stars(pv)} p={pv:.2g}", ha="center", va="bottom", fontsize=7.5)
        _top = max(_top, yy + _yr)
ax.set_ylim(top=_top + _yr * 1.5)
ax.set_xticks(range(4)); ax.set_xticklabels([g[0] for g in GROUPS], fontsize=10)
ax.set_ylabel("Metaphase duration (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.legend(handles=[Line2D([0], [0], marker='o', color='w', markerfacecolor=PHCOL[p], label=p) for p in ["Prophase", "Prometaphase"]]
          + [Line2D([0], [0], color="#222", lw=2.4, label="median"), Line2D([0], [0], color="#222", lw=1.2, ls=(0, (2, 1.5)), label="mean")],
          fontsize=8, loc="upper right", title="ablation phase", title_fontsize=8)
ax.set_title("1-Sisterless ON-TARGET (prophase/prometaphase ablations only) — metaphase duration\nby polar / lagging presence (dots colored by ablation phase)", loc="left", fontweight="bold", fontsize=10.5)
plt.tight_layout(); plt.savefig(f"{OUT}/G4_1sis_polar_lagging_duration.png", bbox_inches="tight"); plt.close()
lib.record_plot("G4_1sis_polar_lagging_duration", ["group", "batch", "metaphase_duration_min", "phase"], rows,
    {"type": "4-group violin+strip", "cohort": "1-sisterless on-target", "groups": [g[0] for g in GROUPS], "color": "ablation phase"},
    __file__, "1-sisterless on-target metaphase duration by polar/lagging, colored by phase")
print("groups N:", {lab: len(by[lab]) for lab, _ in GROUPS})
print("-> G4_1sis_polar_lagging_duration.png")
