"""Pole-to-plate behaviour of the sisterless chromosome vs metaphase duration, per ablation group.

Source of truth = annotations/SISTERLESS_PLATE_JOIN_TIMES.csv (per-chromosome plate-join annotation) +
the master's metaphase duration. Each sisterless chromosome is annotated as:
  '0'         -> stayed at the metaphase plate the whole time (join time 0)
  '<time>'    -> moved from pole to plate at that time
  'anaphase'  -> stayed polar until anaphase (never rejoined the plate)
Per CELL we summarise: any-polar-to-anaphase -> 'Stayed polar (to anaphase)'; else if any timed rejoin ->
'Rejoined plate' (representative time = the LAST/latest chromosome to rejoin, i.e. the rate-limiting one);
else 'Stayed at plate throughout'.

Outputs (PNG + editable PDF + CSV):
  pole_to_plate_behavior_vs_duration.png   — metaphase duration by behaviour category, split by ablation group
  pole_to_plate_jointime_vs_duration.png   — plate-join time vs metaphase duration scatter (rejoined cells)
  data/pole_to_plate_UNSPECIFIED_onTarget.csv — on-target 1/2/3-sisterless cells with NO pole/plate annotation
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os
import numpy as np, matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy import stats as _st
import lib
lib.apply_style()

OUT = "/Volumes/4 MB/ablation_figures_20260625/group1"; SCRIPT = __file__
DATADIR = "/Volumes/4 MB/ablation_plots/data"
PJ_CSV = "/Volumes/4 MB/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv"

data, _ = lib.load_master()
_DBL = lib.double_chromosome_batches()
mr = {r["Batch Name"]: r for r in data}

def dur_min(batch):
    r = mr.get(batch)
    if not r: return None
    v, ok = lib.mitotic_duration_min(r)
    return v if ok else None

def parse_join(v, s):
    """Return ('plate'|'rejoin'|'polar'|None, join_seconds_or_None)."""
    v = (v or "").strip().lower()
    if v in ("", "n/a", "na"): return (None, None)
    if v == "anaphase": return ("polar", None)
    if v in ("0", "0:00", "0:00:00", "plate"): return ("plate", 0.0)
    sec = None
    try: sec = float(s)
    except (TypeError, ValueError): sec = lib.parse_time(v)
    if sec is not None: return ("rejoin", float(sec))
    return (None, None)

# ---- categorise each annotated cell ----
cells = {}   # batch -> {group, behavior, join_min, dur}
for row in csv.DictReader(open(PJ_CSV)):
    b = row["batch"].strip()
    if (row.get("exclude_this_data", "") or "").strip().lower() in ("yes", "y", "true", "1"):
        continue
    r = mr.get(b)
    if not r or r.get("On-Target / Off-Target", "").lower() != "on-target": continue
    if lib.plot_excluded(r["Batch Name"]): continue   # USER 2026-07-16: metaphase/4-sis/drug/excluded out
    if lib.is_mad1(b) or b in _DBL: continue
    grp = str(r.get("# Sisterless KTs", "")).strip()
    if grp not in ("1", "2", "3"): continue
    cats = []; times = []
    for i in ("1", "2", "3"):
        cat, sec = parse_join(row.get(f"chromosome_{i}_plate_join"), row.get(f"chromosome_{i}_plate_join_s"))
        if cat: cats.append(cat)
        if cat == "rejoin" and sec is not None: times.append(sec)
    if not cats: continue
    # USER 2026-08-11: CONGRESSION WINS. Previously "any chromosome polar to anaphase" took precedence, so a
    # cell with both a congression and a polar chromosome was filed as polar — which put 17 of the 23
    # three-sisterless "polar" cells in a bin whose label had to admit they had ALSO congressed. The
    # priority is now: any congression -> congressed; else any polar-to-anaphase -> polar; else all at plate.
    if times: behavior = "Rejoined plate"; jmin = max(times) / 60.0
    elif "polar" in cats: behavior = "Stayed polar (to anaphase)"; jmin = None
    else: behavior = "Stayed at plate throughout"; jmin = 0.0
    cells[b] = {"group": grp, "behavior": behavior, "join_min": jmin, "dur": dur_min(b), "src": "plate_join"}

# ── ITEM 14 (user 2026-08-04): "should have more data for one and three since the outcome is described
# for all chromosomes in both of these groups." Correct — this figure read ONLY
# SISTERLESS_PLATE_JOIN_TIMES.csv, but the same per-chromosome outcome is also recorded in
# CHROMOSOME_MASTER.csv (`behavior`, + `congression_time_s` for the join time). Cells described there but
# absent from the plate-join sheet were silently missing: 45 cells plotted where 75 have an outcome.
# CHROMOSOME_MASTER is used as a SECOND source, only for batches the plate-join sheet does not already
# cover, so no cell is counted twice and the existing rows are untouched.
_BEH_MAP = {"noncongression": "Stayed polar (to anaphase)",
            "at_plate":       "Stayed at plate throughout",
            "congressed":     "Rejoined plate"}
_cm = {}
for _r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    _cm.setdefault(_r["batch"].strip(), []).append(_r)
_gained = []
for b, rs in _cm.items():
    if b in cells: continue                       # plate-join sheet wins where it exists
    r = mr.get(b)
    if not r or r.get("On-Target / Off-Target", "").lower() != "on-target": continue
    if lib.plot_excluded(b) or lib.is_mad1(b) or b in _DBL: continue
    grp = str(r.get("# Sisterless KTs", "")).strip()
    if grp not in ("1", "2", "3"): continue
    behs = [(x.get("behavior") or "").strip() for x in rs]
    behs = [x for x in behs if x in _BEH_MAP]
    if not behs: continue
    _ms = lib.parse_time((r.get("Metaphase Start (s)", "") or "").strip())
    # same congression-first priority as the plate-join branch above (user 2026-08-11)
    if "congressed" in behs:
        behavior = _BEH_MAP["congressed"]; jmin = None
        _t = []
        for x in rs:
            if (x.get("behavior") or "").strip() != "congressed": continue
            _s = (x.get("congression_time_s") or "").strip()
            if _s and _ms is not None:
                try:
                    _d = (float(_s) - _ms) / 60.0
                    if _d >= 0: _t.append(_d)
                except ValueError: pass
        jmin = max(_t) if _t else None
    elif "noncongression" in behs:
        behavior = _BEH_MAP["noncongression"]; jmin = None
    else:
        behavior = _BEH_MAP["at_plate"]; jmin = 0.0
    cells[b] = {"group": grp, "behavior": behavior, "join_min": jmin, "dur": dur_min(b), "src": "chromo_master"}
    _gained.append(b)
from collections import Counter as _C14
print(f"ITEM 14: +{len(_gained)} cells from CHROMOSOME_MASTER "
      f"(by group {dict(_C14(cells[b]['group'] for b in _gained))}); "
      f"total {len(cells)} by group {dict(_C14(c['group'] for c in cells.values()))}")

# ================= PLOT A: metaphase duration by behaviour, split by ablation group =================
# USER 2026-08-05 asked what these categories actually mean, and the honest answer is that they are
# PER-CELL and HIERARCHICAL (see the classifier above): "any chromosome polar to anaphase" wins over
# "any rejoined", which wins over "all at plate". So "Stayed polar" does NOT mean the cell had no
# congression — measured 2026-08-05, of the 23 three-sisterless cells in that bin, 17 ALSO had a
# congressed chromosome and 4 also had one at the plate; only 2 were polar-only. The axis labels now say
# so, because the short names read as mutually exclusive descriptions and they are not.
BEHAV = ["Stayed at plate throughout", "Rejoined plate", "Stayed polar (to anaphase)"]
BLAB = {"Stayed at plate throughout": "all at plate throughout\n(none polar, none congressed)",
        "Rejoined plate":             "\u22651 congressed\n(may ALSO have one stay polar)",
        "Stayed polar (to anaphase)": "\u22651 stayed polar to anaphase\n(none congressed)"}
BCOL = {"Stayed at plate throughout": "#2b8a3e", "Rejoined plate": "#f6a600", "Stayed polar (to anaphase)": "#b2182b"}
GROUPS = ["1", "3"]   # USER 2026-08-05: "it should just show data for 1 and 3 sisterless groups"
fig, ax = plt.subplots(figsize=(11, 5.6))
xt, xl = [], []; pos = 0; recA = []
for grp in GROUPS:
    for bh in BEHAV:
        d = [c["dur"] for c in cells.values() if c["group"] == grp and c["behavior"] == bh and c["dur"] is not None]
        xt.append(pos); xl.append(f"{grp}-sisterless\n{BLAB[bh]}")
        if d:
            col = BCOL[bh]
            lib.journal_violin(ax, d, pos, col, alpha=0.30, lw=1.0)
            jit = (np.random.RandomState(int(pos * 10)).rand(len(d)) - 0.5) * 0.22
            ax.scatter(np.full(len(d), pos) + jit, d, s=15, color=col, alpha=0.85, edgecolor="white", linewidth=0.3, zorder=3)
            m = float(np.mean(d))
            ax.hlines(np.median(d), pos - 0.32, pos + 0.32, color=col, lw=2.2, zorder=4)
            ax.scatter([pos], [m], marker="D", s=30, facecolor="white", edgecolor=col, lw=1.3, zorder=5)
            ax.text(pos, max(d) + 1.5, f"n={len(d)}", ha="center", va="bottom", fontsize=7, color="#444")
            for v in d: recA.append([grp, bh, round(v, 3)])
        pos += 1
    pos += 0.6   # gap between ablation groups
for grp in GROUPS:
    if not any(c["group"]==grp for c in cells.values()):
        xs=[xt[i] for i in range(len(xl)) if xl[i].startswith(f"{grp}-sis")]
        if xs: ax.text(sum(xs)/len(xs), ax.get_ylim()[1]*0.5, f"{grp}-sisterless:\nno plate-join\nannotation", ha="center", va="center", fontsize=8, color="#999", style="italic")
ax.set_xticks(xt); ax.set_xticklabels(xl, fontsize=6.6)
ax.set_ylabel("Metaphase duration (MM:SS)")
from matplotlib.ticker import FuncFormatter
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("Sisterless chromosome pole-to-plate behaviour vs metaphase duration, by ablation group",
             loc="left", fontweight="bold", fontsize=11)
ax.legend(handles=[Line2D([0], [0], marker="s", color="none", markerfacecolor=BCOL[b], markersize=9, label=b) for b in BEHAV],
          loc="upper left", fontsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/pole_to_plate_behavior_vs_duration.png", bbox_inches="tight"); plt.close()
lib.record_plot("pole_to_plate_behavior_vs_duration", ["ablation_group", "behavior", "metaphase_duration_min"], recA,
    {"type": "violin+points", "source": "SISTERLESS_PLATE_JOIN_TIMES.csv + master duration",
     "behaviors": "stayed-at-plate / rejoined / stayed-polar-to-anaphase", "split": "ablation group 1/2/3-sisterless"},
    SCRIPT, "Pole-to-plate behaviour vs metaphase duration, by ablation group")

# ================= PLOT B: plate-join time vs metaphase duration (rejoined cells) =================
GCOL = {"1": "#4477aa", "2": "#66ccee", "3": "#ee6677"}
fig, ax = plt.subplots(figsize=(8.4, 5.6)); recB = []
allx, ally = [], []
for grp in GROUPS:
    pts = [(c["join_min"], c["dur"]) for c in cells.values()
           if c["group"] == grp and c["behavior"] == "Rejoined plate" and c["join_min"] is not None and c["dur"] is not None]
    if not pts: continue
    xs, ys = zip(*pts); allx += list(xs); ally += list(ys)
    ax.scatter(xs, ys, s=34, color=GCOL[grp], alpha=0.8, edgecolor="white", linewidth=0.4, label=f"{grp}-sisterless (n={len(pts)})", zorder=3)
    for x, y in pts: recB.append([grp, round(x, 3), round(y, 3)])
if len(allx) >= 3:
    r, p = _st.spearmanr(allx, ally)
    sl, ic = np.polyfit(allx, ally, 1)
    xx = np.linspace(min(allx), max(allx), 50)
    ax.plot(xx, sl * xx + ic, color="#444", lw=1.4, ls="--", zorder=2)
    ax.text(0.98, 0.03, f"Spearman ρ={r:.2f}, p={p:.2g}  (N={len(allx)})", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#333")
ax.set_xlabel("Pole-to-plate rejoin time (minutes after ablation-frame 0)")
ax.set_ylabel("Metaphase duration (MM:SS)")
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lib.mmss(v) if v >= 0 else ""))
ax.set_title("Later pole-to-plate rejoining vs longer metaphase? (cells whose sisterless KT rejoined the plate)",
             loc="left", fontweight="bold", fontsize=10.5)
ax.legend(fontsize=8, loc="upper left")
plt.tight_layout(); plt.savefig(f"{OUT}/pole_to_plate_jointime_vs_duration.png", bbox_inches="tight"); plt.close()
lib.record_plot("pole_to_plate_jointime_vs_duration", ["ablation_group", "rejoin_min", "metaphase_duration_min"], recB,
    {"type": "scatter+trend", "test": "Spearman", "subset": "cells whose sisterless KT rejoined the plate at a time"},
    SCRIPT, "Pole-to-plate rejoin time vs metaphase duration")

# ================= UNSPECIFIED list: on-target 1/2/3-sisterless with NO pole/plate annotation =================
annotated = set(cells.keys())
# also treat a master Notes '[POLAR to PLATE]' tag as specified
tagged = {r["Batch Name"] for r in data if "[polar to plate]" in (r.get("Notes", "") or "").lower()}
specified = annotated | tagged
unspecified = []
for r in data:
    b = r["Batch Name"]
    if r.get("On-Target / Off-Target", "").lower() != "on-target": continue
    if str(r.get("# Sisterless KTs", "")).strip() not in ("1", "2", "3"): continue
    if r.get("Exclude") in ("Yes", "yes"): continue
    if lib.plot_excluded(b): continue   # USER 2026-07-16: metaphase/4-sis/drug/excluded out (UNSPECIFIED list too)
    if lib.is_mad1(b) or b in _DBL: continue
    if b in specified: continue
    unspecified.append((b, str(r.get("# Sisterless KTs", "")).strip(), r.get("Phase of Ablations", "")))
os.makedirs(DATADIR, exist_ok=True)
with open(f"{DATADIR}/pole_to_plate_UNSPECIFIED_onTarget.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["batch", "n_sisterless", "phase_of_ablations"])
    for row in sorted(unspecified): w.writerow(row)

from collections import Counter
print("cells annotated (in plate-join CSV, on-target 1/2/3):", len(cells),
      "| behavior:", dict(Counter(c["behavior"] for c in cells.values())),
      "| by group:", dict(Counter(c["group"] for c in cells.values())))
print("UNSPECIFIED on-target 1/2/3-sisterless:", len(unspecified),
      "| by group:", dict(Counter(u[1] for u in unspecified)),
      "-> data/pole_to_plate_UNSPECIFIED_onTarget.csv")
