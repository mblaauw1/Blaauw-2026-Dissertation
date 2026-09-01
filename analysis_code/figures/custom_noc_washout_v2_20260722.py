#!/usr/bin/env python3
"""G2_noc_washout_vs_prophase -- rebuilt in the G2_phase_split_violin_v2_tripledouble format.
# USER 2026-08-06: prophase ablations are excluded from every cohort by default. This file DRAWS a
# prophase group, so it opts back in with include_prophase=True. Nothing else may.

USER 2026-07-22: "this plots all noc washout batches as one group, all prophase batches as one group
(and I don't think you use the v2 classification here), and all the prometaphase batches as one group.
This should instead be displayed like the G2_phase_split_violin_v2_tripledouble violin plot."

Changes from the old version:
  * v2 binning everywhere -- a batch flagged `v2=prometaphase` in Notes counts as PROMETAPHASE even when
    its `Phase of Ablations` column still says prophase (lib.is_v2_prometaphase; NOTES §1 rule 16 era).
    The old plot read the raw column, so v2-flagged cells sat in the prophase bucket.
  * the ablation side is split the way the tripledouble violin splits it: 1-Sisterless and
    Triple+Double (on-target cdc20) each shown Prophase vs Prometaphase, rather than one pooled
    "prophase" and one pooled "prometaphase" group whose composition differs.
  * journal violin conventions (lib.journal_violin: scale=width, width 0.8, cut 0, points-only for N<6).

Noc washout stays ONE group: 294 of the 299 washout batches carry no ablation phase at all (they are
washouts, not ablations), so there is nothing to split them by -- stating that rather than inventing one.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT = "/Volumes/4 MB/ablation_figures_20260625/group2"
SCRIPT = __file__
lib.apply_style()

data, HDR = lib.load_master()
mr = {r["Batch Name"]: r for r in data}
coh = lib.assign_cohorts(include_prophase=True)


def phase_v2(b):
    """prophase / prometaphase under the v2 rule; None if the batch has no ablation phase."""
    if lib.is_v2_prometaphase(b):
        return "Prometaphase"
    p = (mr.get(b, {}).get("Phase of Ablations", "") or "").strip().lower()
    if p.startswith("promet"):
        return "Prometaphase"
    if p.startswith("proph"):
        return "Prophase"
    return None


def ontarget_cdc20(b):
    r = mr.get(b, {})
    ct = (r.get("Cell Type", "") or "").lower()
    if "cdc20" not in ct or "hec1" in ct or "mad1" in ct:
        return False
    return (r.get("On-Target / Off-Target", "") or "").strip().lower() == "on-target"


# ---- noc washout (one group; no ablation phase exists to split on) ----
noc = []
for r in data:
    b = r["Batch Name"]
    low = b.lower()
    if "noc" not in low or not ("washout" in low or "wash" in low):
        continue
    d = lib.parse_time(r.get("Meta Duration (s)", ""))
    if d and d > 0:
        noc.append(d / 60.0)

# ---- ablation side, exactly the tripledouble split ----
TD_OUTLIER = {"20260107 two_sisterless_kinetochores_3"}      # same exclusion as the reference violin
combined = [(b, v) for b, v in (coh["2-Sister"] + coh["3-Sister"])
            if ontarget_cdc20(b) and b not in TD_OUTLIER]

G = [("Noc washout", noc, "#ef8a62")]
# HER 2026-08-19, board 9 item 1: *"Some of the text on this plot is overlapping with other things, fix"*.
# The culprit was these tick labels: "Triple+Double\n(on-target cdc20)\nProphase" wraps to THREE lines and
# the two three-line labels ran into each other under the axis. Use her canonical cohort abbreviations
# (canon_labels: "3-Sisterless" -> "3-sis"), which fit on two lines, and keep the "on-target cdc20"
# qualifier in the recorded caption where it is not competing for space.
for ph in ("Prophase", "Prometaphase"):
    G.append((f"1-sis\n{ph}",
              [v for b, v in coh["1-Sister"] if phase_v2(b) == ph], lib.PALETTE["1-Sister"]))
for ph in ("Prophase", "Prometaphase"):
    G.append((f"2+3-sis\n{ph}",
              [v for b, v in combined if phase_v2(b) == ph], lib.PALETTE["3-Sister"]))

# ── ITEM 34 (user 2026-08-04, REPEAT of feedback that was not actioned) ───────────────────────────
# "In previous feedback I told you to combine G2_noc_washout_vs_prophase and
#  G2_noc_washout_metaphase_by_sisterless. You ignored this previous feedback."
# The two figures answer one question between them: this one shows noc washout as a SINGLE pooled group
# beside the ablation phase groups, while the other breaks the washout side down by how many sisterless
# kinetochores the washout created. Pooling on the left panel throws away exactly the split the right panel
# supplies. Combined here into one figure: LEFT = washout by # sisterless KTs created, RIGHT = washout vs the
# phase-split ablation groups. Same curation as the standalone by-sisterless plot (noc_washout_metaphase.py,
# user 2026-07-21): 4-ablation reclassified as 3, lowest-3 control dropped, highest-4 of group-3 dropped,
# 2-ablation group excluded, only spindle-competent short-time (0<t<45min) 20251102 cells.
import csv as _csv, re as _re
def _sec(h):
    h = str(h).replace("\\", "").strip(); neg = h.startswith("-"); h = h.lstrip("-").strip()
    p = [int(x) for x in h.split(":")]
    while len(p) < 3: p = [0] + p
    s = p[0]*3600 + p[1]*60 + p[2]
    return -s if neg else s
def _nsis_from(l):
    l = l.lower()
    for w, n in [("four", 4), ("three", 3), ("one", 1), ("two", 2)]:
        if w in l: return n
    m = _re.search(r"(\d+)\s*abl", l)
    return int(m.group(1)) if m else 0
def _bucket(typ, n): return 0 if typ == "control" else (3 if n >= 4 else n)
_ND = [[], [], [], []]
for _r in _csv.DictReader(open("/Volumes/4 MB/annotations/NOC_WASHOUT_20251102_TIMES.tsv"), delimiter="\t"):
    _t = (_r.get("time_to_anaphase", "") or "").strip()
    if not _t: continue
    _mm = _sec(_t) / 60.0; _note = (_r.get("notes", "") or "").lower()
    if not (0 < _mm < 45) or "dead" in _note or "anaphase before" in _note or "before noc" in _note: continue
    _typ = "on-target" if "on-target" in _r["batch"] else "control"
    _m = _re.search(r"(\d+)abl", _r["batch"]); _b = _bucket(_typ, int(_m.group(1)) if _m else 0)
    if 0 <= _b <= 3: _ND[_b].append(_mm)
for _r in _csv.DictReader(open("/Volumes/4 MB/annotations/NOC_WASHOUT_METAPHASE_LINKED.csv")):
    try: _mm = float(_r.get("meta_dur_min") or 0)
    except Exception: _mm = 0
    if _mm <= 0: continue
    _lab = _r.get("label", ""); _typ = "control" if "control" in _lab.lower() else "on-target"
    _b = _bucket(_typ, _nsis_from(_lab))
    if 0 <= _b <= 3: _ND[_b].append(_mm)
_ND[0] = sorted(_ND[0])[3:]
_ND[3] = sorted(_ND[3])[:-4]
NOC_BY_SIS = [(0, "control", "#888"), (1, "1", "#4a90e2"), (3, "3", "#b2182b")]

# ── USER 2026-08-05: one axes, and drop the pooled washout violin ─────────────────────────────────
# "merge the two axes into one, drop the pooled violin".
#
# The two panels shared a y-axis and a question, so splitting them forced the eye to jump a panel gap to
# compare a washout group against an ablation group. And panel B's first violin was the washout POOLED
# across 0/1/3 sisterless — the exact collapse panel A existed to undo, sitting right next to the split
# version of itself. Dropping it (G[1:]) removes the double-counting rather than hiding it.
#
# Everything is now on one axes, washout groups first, then the phase-split ablation groups, with a
# divider and a spacer between the two families so they stay visually distinct.
# USER 2026-08-10: draw a body down to N=3 here so the PROPHASE groups get violins instead of bare
# points. Applied to every group in this figure, so no cohort is treated differently.
NOC_MIN_N = 3
fig, ax = plt.subplots(figsize=(13.0, 5.6))
_pos = 0.0; _ticks = []; _tlabs = []

def _violin_annot(ax, d, pos, col):
    """Annotate ONE violin exactly as the artboard-2 violin does (her 2026-08-20 instruction: *"the violins
    need to have the same labeling as standard for the violins on artboard 2; so mean and median, etc"*).

    The artboard-2 convention, read off `g1_violin2.py` rather than guessed: MEDIAN is a solid horizontal
    bar, MEAN is a dashed bar plus a white-filled diamond, and the text block above the violin carries
    x̄, med and N. Only the number FORMAT differs -- artboard 2 is MM:SS because it plots a duration in
    those units; this figure is already in minutes, so it stays decimal minutes and the axis says so.
    """
    import numpy as _np
    mean = float(_np.mean(d)); med = float(_np.median(d))
    ax.hlines(med, pos - .34, pos + .34, color=col, lw=2.2, zorder=4)
    ax.hlines(mean, pos - .28, pos + .28, color=col, lw=1.4, ls=(0, (2, 1.5)), zorder=4)
    ax.scatter([pos], [mean], marker="D", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
    ax.text(pos, max(d) * 1.03, f"x\u0304 {mean:.1f}\nmed {med:.1f}\nN={len(d)}",
            ha="center", va="bottom", fontsize=7.6, color=col, linespacing=1.25)


# ---- the phase-split ablation groups FIRST (user 2026-08-10: nocodazole moved to the right) ----
for i, (lab, d, col) in enumerate(G[1:]):        # G[0] is the POOLED washout violin — dropped
    d = [x for x in d if x is not None]
    if not d: continue
    alpha = 0.45 if "Prometaphase" in lab else 0.28
    lib.journal_violin(ax, d, _pos, col, width=0.8, min_n=NOC_MIN_N, alpha=alpha)
    jit = (np.random.RandomState(i).rand(len(d)) - .5) * .28
    ax.scatter(np.full(len(d), _pos) + jit, d, s=22, color=col, alpha=.85, edgecolor="white", lw=.3, zorder=3)
    _violin_annot(ax, d, _pos, col)
    _ticks.append(_pos); _tlabs.append(lab)
    _pos += 1.0

# ---- divider, then the washout groups on the RIGHT ----
_div = _pos - 0.1
ax.axvline(_div, color="#bbb", lw=1.2, ls="--", zorder=1)
_pos += 0.5

_noc_stats = []
if len(_ND[0]) >= 3 and len(_ND[3]) >= 3:
    _noc_stats.append("washout control vs 3: p=%.3g"
                      % stats.mannwhitneyu(_ND[0], _ND[3], alternative="two-sided").pvalue)
if len(_ND[0]) >= 3 and len(_ND[1]) >= 3:
    _noc_stats.append("washout control vs 1: p=%.3g"
                      % stats.mannwhitneyu(_ND[0], _ND[1], alternative="two-sided").pvalue)

# ---- washout, split by # sisterless kinetochores created (now rightmost) ----
for _gi, _lab, _c in NOC_BY_SIS:
    _v = _ND[_gi]
    if not _v: continue
    lib.journal_violin(ax, _v, _pos, _c, width=0.8, min_n=NOC_MIN_N, alpha=.28)
    _jit = (np.random.RandomState(_gi).rand(len(_v)) - .5) * .30
    ax.scatter(np.full(len(_v), _pos) + _jit, _v, s=32, color=_c, alpha=.8, edgecolor="white", lw=.4, zorder=3)
    _violin_annot(ax, _v, _pos, _c)   # same convention as artboard 2, on the washout violins too
    _ticks.append(_pos); _tlabs.append(f"Noc washout\n{_lab}")
    _pos += 1.0

from matplotlib.lines import Line2D as _L2D
ax.legend(handles=[_L2D([0], [0], color="#444", lw=2.2, label="median"),
                   _L2D([0], [0], marker="D", color="#444", lw=1.4, ls=(0, (2, 1.5)),
                        markerfacecolor="white", markeredgecolor="#444", label="mean")],
          fontsize=7.5, frameon=False, loc="upper left")
ax.set_xticks(_ticks); ax.set_xticklabels(_tlabs, fontsize=8)
ax.set_ylabel("Metaphase duration (min)")   # her 2026-08-20: canonical label + units, no window prose
_yt = ax.get_ylim()[1]
ax.text(_div - 0.15, _yt, "ablations ", ha="right", va="top", fontsize=8.5, color="#555", style="italic")
ax.text(_div + 0.15, _yt, " noc washout", ha="left", va="top", fontsize=8.5, color="#555", style="italic")

# stats: washout vs each ablation group it can be compared with
notes = []
for lab, d, _ in G[1:]:
    if len(noc) >= 3 and len(d) >= 3:
        p = stats.mannwhitneyu(noc, d, alternative="two-sided").pvalue
        notes.append(f"washout vs {lab.replace(chr(10),' ')}: p={p:.3g}")
pro = G[1][1] + G[3][1]
pmt = G[2][1] + G[4][1]
if len(pro) >= 3 and len(pmt) >= 3:
    notes.append("pooled prophase vs prometaphase (v2): p=%.3g"
                 % stats.mannwhitneyu(pro, pmt, alternative="two-sided").pvalue)
fig.suptitle("Does a noc washout behave like a PROPHASE ablation? ('memory')\n"
             "washout split by how many sisterless KTs it created, beside the phase-split ablations, on ONE axis. "
             "The pooled-washout violin is gone: it collapsed the same cells the split already shows.\n"
             "v2 prometaphase binning · 1-sisterless and triple+double shown separately, as in "
             "G2_phase_split_violin_v2_tripledouble · washout curation per user 2026-07-21",
             x=.01, ha="left", fontweight="bold", fontsize=8.5)
fig.text(0.005, 0.004, "   ·   ".join(_noc_stats + notes), fontsize=7, color="#222", ha="left", va="bottom")
plt.tight_layout()
fig.savefig(f"{OUT}/G2_noc_washout_vs_prophase.png", bbox_inches="tight", dpi=130)
plt.close(fig)

lib.record_plot("G2_noc_washout_vs_prophase", ["panel", "group", "meta_min"],
                [["A · washout by #sisterless", lab, round(v, 2)] for _gi, lab, _c in NOC_BY_SIS for v in _ND[_gi]]
                + [["B · washout vs ablation phase", lab.replace("\n", " "), round(v, 2)] for lab, d, _ in G for v in d],
                {"type": "2-panel violin (journal)", "binning": "v2=prometaphase rule",
                 "item34": "combined with G2_noc_washout_metaphase_by_sisterless per repeat feedback",
                 "panelA_groups": {lab: len(_ND[gi]) for gi, lab, _ in NOC_BY_SIS},
                 "panelB_groups": {lab.replace(chr(10), ' '): len(d) for lab, d, _ in G},
                 "outlier_excluded": sorted(TD_OUTLIER),
                 "y_label": "Metaphase duration, Meta-to-Ana (min)"},
                SCRIPT, "Noc washout by # sisterless KTs, and vs prophase/prometaphase ablation (combined)")
print("panel A (washout by #sisterless):", [(lab, len(_ND[gi])) for gi, lab, _ in NOC_BY_SIS])
print("panel B groups:", [(lab.replace(chr(10), ' '), len(d)) for lab, d, _ in G])
print("  " + " · ".join(_noc_stats + notes))
