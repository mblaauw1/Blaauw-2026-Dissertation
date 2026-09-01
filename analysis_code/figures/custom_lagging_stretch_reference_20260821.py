#!/usr/bin/env python3
"""G5_lagging_stretch_reference — how stretched a LAGGING kinetochore is, against her own references.

USER 2026-08-20 (artboard 5, item 3), verbatim:
    "Is there a plot that can be put my this timestrip then quantifying the kinetochore stretch with
     respect to some reference, like typical stretches seen in a polar kinetochore or in a paired
     kinetochore, and so on."

WHAT IS PLOTTED
    Stretch = `major_um`, the long axis of HER traced kinetochore outline (KT_OUTLINE_TRACKS, computed per
    polygon by calipers -- no shape is fitted, per the standing rule). One point per KINETOCHORE: the median
    of that kinetochore's own frames, so a KT traced on 80 frames does not outvote one traced on 8.

    Three references, all from her own labels: `paired` (a bioriented sister KT), `polar` (uncongressed),
    and `lagging` -- the group the timestrip is about.

WHY THE TEST IS PER CELL AND THE POINTS ARE PER KINETOCHORE
    Kinetochores within one cell share that cell's spindle, so they are not independent. The points show
    the per-KT spread, which is what "typical stretch" means visually, but every p-value is computed on
    PER-CELL medians (standing rule: aggregate to the cell before any cohort test).

WINDOW
    Metaphase onset -> anaphase onset for paired and polar. Lagging is NOT clipped to metaphase: a lagging
    kinetochore is by definition still being stretched after anaphase onset, and clipping it there would
    remove the very frames the timestrip shows. That difference is stated on the figure rather than hidden.
"""
import csv, io, os, sys, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
lib.apply_style()

ANN = "/Volumes/4 MB/annotations"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group4"; os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
PLOT_ID = "G5_lagging_stretch_reference"
# the two cells whose lagging strips sit on artboard 5 -- called out so she can find them on the plot
STRIP_CELLS = {"20260108 two_sisterless_kinetochores_14": "fractured (strip on AB5)",
               "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52": "stretch-rebound (strip on AB5)"}
COL = {"paired": "#2a7fff", "polar": "#e6820e", "lagging": "#7b3fa0"}   # no red beside a green (rule 30)

def parse_time(s):
    s = (s or "").strip()
    if not s: return None
    if ":" in s:
        p = [float(x) for x in s.split(":")]
        while len(p) < 3: p.insert(0, 0.0)
        return p[0]*3600 + p[1]*60 + p[2]
    try: return float(s)
    except Exception: return None

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
def win(b):
    r = MR.get(b, {})
    return parse_time(r.get("Metaphase Start (s)", "")), parse_time(r.get("Anaphase Onset (s)", ""))

per_kt = collections.defaultdict(list)          # (label, batch, track) -> [major_um]
for r in csv.DictReader(io.open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv", encoding="utf-8", errors="replace")):
    lab = (r.get("label") or "").strip()
    if lab not in COL: continue
    b = (r.get("batch") or "").strip()
    if lib.plot_excluded(b) or lib.is_mad1(b): continue
    try:
        v = float(r.get("major_um") or ""); t = float(r.get("t_sec") or "")
    except Exception:
        continue
    lo, hi = win(b)
    if lab != "lagging":                       # references are metaphase-only
        if lo is None or hi is None or not (lo <= t <= hi): continue
    per_kt[(lab, b, (r.get("track_id") or "").strip())].append(v)

pts = collections.defaultdict(list); cells = collections.defaultdict(lambda: collections.defaultdict(list))
for (lab, b, tr), vals in per_kt.items():
    if len(vals) < 3: continue                 # a KT needs a few frames for a median to mean anything
    m = float(np.median(vals))
    pts[lab].append((b, tr, m)); cells[lab][b].append(m)

ORDER = ["paired", "polar", "lagging"]
fig, ax = plt.subplots(figsize=(7.8, 5.4))
_nlab = []
_hits = 0
for i, lab in enumerate(ORDER):
    v = np.array([p[2] for p in pts[lab]], float)
    if not len(v): continue
    vp = ax.violinplot([v], positions=[i], widths=0.62, showextrema=False)
    for bdy in vp["bodies"]:
        bdy.set_facecolor(COL[lab]); bdy.set_edgecolor("none"); bdy.set_alpha(0.26)
    ax.scatter(np.random.default_rng(i).normal(i, 0.055, len(v)), v, s=26, color=COL[lab],
               alpha=0.8, edgecolor="w", lw=0.4, zorder=3)
    ax.hlines(float(np.median(v)), i-0.24, i+0.24, color="k", lw=2.4, zorder=4)
    # n label placed in AXES fraction AFTER all series are drawn (below) -- reading ax.get_ylim() inside
    # this loop gave the first group a y from before the axis had autoscaled, so its label fell off-axis.
    _nlab.append((i, f"n={len(v)} KTs\n{len(cells[lab])} cells", COL[lab]))
    for b, tr, m in pts[lab]:                  # call out the cells whose strips are on the board
        if lab == "lagging" and b in STRIP_CELLS:
            ax.scatter([i], [m], s=95, facecolors="none", edgecolors="k", lw=1.6, zorder=5); _hits += 1
            ax.annotate(STRIP_CELLS[b], (i, m), textcoords="offset points", xytext=(14, 0),
                        fontsize=7.5, va="center")

def med(lab): return {b: float(np.median(v)) for b, v in cells[lab].items()}
from scipy.stats import mannwhitneyu
lines = []
for a, bb in (("lagging", "paired"), ("lagging", "polar")):
    A, B = list(med(a).values()), list(med(bb).values())
    if len(A) >= 3 and len(B) >= 3:
        p = mannwhitneyu(A, B, alternative="two-sided").pvalue
        lines.append(f"{a} vs {bb}: {np.median(A):.2f} vs {np.median(B):.2f} um, MW p={p:.3g} "
                     f"(per CELL, n={len(A)} vs {len(B)})")
for _i, _t, _c in _nlab:
    ax.text(_i, 0.012, _t, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
            fontsize=7.5, color=_c)
# If a strip cell cannot appear on the plot, SAY SO on the figure -- a silently absent callout reads as
# "that cell is unremarkable" when the truth is that it is excluded from every plot by a standing rule.
_why = []
for _b, _lab in STRIP_CELLS.items():
    if lib.plot_excluded(_b): _why.append(f"{_lab}: cell is Exclude=Yes, so it is in no plot")
    elif lib.is_mad1(_b):     _why.append(f"{_lab}: Mad1 cell, outside this cdc20 comparison")
    elif not any(b == _b for b, _, _ in pts["lagging"]):
                              _why.append(f"{_lab}: no `lagging` kinetochore traced on it")
if _why:
    ax.text(0.0, 1.005, "Not shown — " + "; ".join(_why), transform=ax.transAxes,
            ha="left", va="bottom", fontsize=7, color="#a33")
print(f"   strip-cell callouts drawn: {_hits}; not shown: {_why}")
ax.set_xticks(range(len(ORDER)))
ax.set_xticklabels(["paired\n(bioriented)", "polar\n(uncongressed)", "lagging"])
ax.set_ylabel("Kinetochore long axis (µm)")
ax.set_title("How stretched is a lagging kinetochore? — her traced outlines, one point per kinetochore\n"
             + ("   |   ".join(lines) if lines else ""), loc="left", fontweight="bold", fontsize=9)
ax.text(0.0, -0.155,
        "Stretch = long axis of her traced outline (calipers, no fitted shape). Point = one kinetochore "
        "(median of its own frames);\np-values on PER-CELL medians, never per frame. paired/polar are "
        "metaphase-onset->anaphase-onset; lagging is NOT clipped at\nanaphase onset, because that is where "
        "a lagging kinetochore is stretched and is what the artboard-5 strips show.",
        transform=ax.transAxes, ha="left", va="top", fontsize=7, color="#444", linespacing=1.5)
ax.legend(handles=[Line2D([0], [0], marker="o", ls="none", markerfacecolor="none",
                          markeredgecolor="k", markersize=9, label="cell shown as a timestrip on artboard 5")],
          fontsize=7.5, loc="upper left")
fig.tight_layout()
fig.savefig(f"{OUT}/{PLOT_ID}.png", dpi=190, bbox_inches="tight")
plt.close(fig)
lib.record_plot(PLOT_ID, ["label", "batch", "track_id", "median_major_um"],
                [[lab, b, tr, round(m, 4)] for lab in ORDER for (b, tr, m) in pts[lab]],
                {"metric": "major_um (long axis) of her traced KT outline",
                 "unit": "one point per kinetochore = median over its frames",
                 "test": "Mann-Whitney on PER-CELL medians",
                 "window": "paired/polar metaphase->anaphase; lagging unclipped (see figure note)",
                 "why": "user 2026-08-20 artboard 5 item 3 -- quantify lagging KT stretch against "
                        "polar and paired references, to sit beside the lagging timestrip"},
                SCRIPT, "Lagging kinetochore stretch against polar and paired references",
                key_column="batch")
print(f"wrote {PLOT_ID}: " + ", ".join(f"{k} {len(v)} KTs/{len(cells[k])} cells" for k, v in pts.items()))
for l in lines: print("   ", l)
