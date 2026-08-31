#!/usr/bin/env python3
"""Spindle pole-to-pole distance over time, single- vs triple-sisterless, with a fit line per group.

USER 2026-08-09: "some cells have marked poles - pole 1 and pole 2, across many frames. should be a set
for single batchas and a set for triple batches. make a plot that shows the pole distance over time for
the batches with the annotations, and then put a fit line for single and triple groups."

DATA. `annotations/poles.csv` -- her manual pole marks, label `pole`, track identity in `notes` as
`grp:1` / `grp:2` (the same convention kt_outline uses). All marks are on the MONITORING clip. Pole-pole
distance per frame = ||pole1 - pole2|| * that batch's pixel size, taken only on frames where BOTH poles
are marked.

TIME BASE. t = 0 at Metaphase Start, so cells are comparable; negative values are pre-metaphase.

NO ANAPHASE (her standing rule 2026-08-08: "dont include anaphase data on a plot unless it specifically
calls for it"). Frames at or after Anaphase Onset are dropped -- which matters here more than usual,
because pole-pole distance rises steeply in anaphase B and would otherwise dominate any fit.

COHORT. `# Sisterless KTs` == 1 or 3, excluding Mad1 (its own group, per her rule) and anything
`lib.plot_excluded` drops. The fit is an ordinary least-squares line per group over all per-frame points,
with the slope and its p-value reported; per-cell traces are drawn faintly behind it so a single cell
driving the trend is visible rather than hidden.
"""
import sys, os, csv, re, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
import lib

lib.apply_style()
csv.field_size_limit(10 ** 9)
A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group8"
os.makedirs(OUT, exist_ok=True)

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}


def nsis(b):
    v = (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


def px(b):
    try:
        return float((MR.get(b, {}).get("Pixel Size (um)", "") or 0.062))
    except Exception:
        return 0.062


# ---- her pole marks ------------------------------------------------------------------------------
poles = collections.defaultdict(lambda: collections.defaultdict(dict))   # batch -> frame -> grp -> (x,y,t)
for r in csv.DictReader(open(A + "poles.csv", newline="", encoding="utf-8", errors="replace")):
    b = (r.get("batch") or "").strip()
    m = re.search(r"grp:(\d+)", (r.get("notes") or "") or "")
    if not m:
        continue
    try:
        x = float(r["x"]); y = float(r["y"]); t = float(r["t_sec"])
    except Exception:
        continue
    poles[b][int(r["frame"])][m.group(1)] = (x, y, t)

GROUPS = {1: ("single sisterless", "#2166ac"), 3: ("triple sisterless", "#b2182b")}
rows, per_cell = [], collections.defaultdict(list)
skipped = collections.Counter()

for b, frames in poles.items():
    n = nsis(b)
    if n not in GROUPS:
        skipped["not 1- or 3-sisterless"] += 1; continue
    if lib.is_mad1(b):
        skipped["Mad1 (its own group)"] += 1; continue
    if lib.plot_excluded(b):
        skipped["plot_excluded"] += 1; continue
    ms = lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", ""))
    ana = lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", ""))
    if ms is None:
        skipped["no Metaphase Start"] += 1; continue
    ps = px(b)
    for fr, g in sorted(frames.items()):
        if "1" not in g or "2" not in g:
            continue
        (x1, y1, t1), (x2, y2, _) = g["1"], g["2"]
        if ana is not None and t1 >= ana:
            continue                                   # NO ANAPHASE — her standing rule
        d = float(np.hypot(x1 - x2, y1 - y2) * ps)
        tm = (t1 - ms) / 60.0
        per_cell[(n, b)].append((tm, d))
        rows.append([b, n, fr, f"{t1:.2f}", f"{tm:.3f}", f"{d:.3f}"])

print(f"batches used: {len({b for _, b in per_cell})}   points: {len(rows)}")
for k, v in skipped.most_common():
    print(f"   skipped {v}: {k}")
for n, (lab, _) in GROUPS.items():
    cells = [b for (nn, b) in per_cell if nn == n]
    pts = sum(len(v) for (nn, _), v in per_cell.items() if nn == n)
    print(f"   {lab}: {len(cells)} cells, {pts} frames")

# ---- plot ----------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 6.0))
stat_lines = []
from scipy import stats as st

for n, (lab, col) in GROUPS.items():
    xs_all, ys_all = [], []
    cells = sorted(b for (nn, b) in per_cell if nn == n)
    for b in cells:
        v = sorted(per_cell[(n, b)])
        ax.plot([p[0] for p in v], [p[1] for p in v], lw=.8, color=col, alpha=.28, zorder=1)
        xs_all += [p[0] for p in v]; ys_all += [p[1] for p in v]
    if len(xs_all) < 3:
        continue
    xs = np.array(xs_all); ys = np.array(ys_all)
    sl, ic, r, p, se = st.linregress(xs, ys)
    # USER 2026-08-10: a metaphase-aligned trend may not run past THIS group's median metaphase duration --
    # beyond it most of the group is already in anaphase and the line is carried by the longest-metaphase
    # cells alone. Points still show; only the fit stops. Cap is per group (single ~10 min, triple ~17).
    _cap = lib.trend_cap(cells)
    _hi = min(xs.max(), _cap) if _cap is not None else xs.max()
    gx = np.linspace(xs.min(), _hi, 100)
    # PER-CELL SLOPES ARE THE HONEST TEST. The pooled fit above treats every frame as an independent
    # observation -- 650 frames from 12 cells is not 650 facts, and that inflates the pooled p-value.
    # So the line she asked for is drawn from the pooled fit, but the statistic REPORTED is the median
    # of the per-cell slopes with a Wilcoxon test against zero, n = cells.
    percell = []
    for b in cells:
        v = sorted(per_cell[(n, b)])
        if len(v) >= 5 and len({q[0] for q in v}) >= 3:
            s2 = st.linregress([q[0] for q in v], [q[1] for q in v]).slope
            if s2 == s2:
                percell.append(s2)
    if len(percell) >= 5:
        med = float(np.median(percell)); wp = st.wilcoxon(percell).pvalue
        cellstat = f"per-cell slope median {med:+.3f} µm/min (Wilcoxon p={wp:.2g}, n={len(percell)} cells)"
    else:
        med, wp = float("nan"), float("nan")
        cellstat = f"per-cell slopes n={len(percell)} (too few to test)"
    lib.annotate_trend_cap(ax, _cap, color=col, label=f"median metaphase ({lab})")
    ax.plot(gx, ic + sl * gx, lw=2.6, color=col, zorder=4,
            label=f"{lab} — {len(cells)} cells, {len(xs)} frames\n"
                  f"pooled fit {sl:+.3f} µm/min · {cellstat}")
    stat_lines.append(f"{lab}: n={len(cells)} cells / {len(xs)} frames; pooled slope {sl:+.4f} um/min "
                      f"(r={r:.3f}, pooled p={p:.3g} — frames are NOT independent); {cellstat}")

ax.set_xlabel("time from metaphase start (min)")
ax.set_ylabel("pole-to-pole distance (µm)")
ax.set_title("Spindle pole separation over time\n(her manual pole marks; anaphase excluded)", fontsize=12)
ax.axvline(0, color="#555", ls=":", lw=1)
ax.legend(fontsize=8, loc="best")
fig.tight_layout()
png = os.path.join(OUT, "G8_pole_distance_over_time.png")
fig.savefig(png, dpi=200, bbox_inches="tight"); plt.close(fig)
print("wrote", png)
for s in stat_lines:
    print("   " + s)

lib.record_plot(
    "G8_pole_distance_over_time",
    ["batch", "n_sisterless", "frame", "t_sec", "t_from_metaphase_min", "pole_distance_um"],
    rows,
    {"kind": "trace + OLS fit per group", "cohort": "1- and 3-sisterless",
     "anaphase": "excluded", "time_base": "t=0 at Metaphase Start",
     "trend_cap": "per-group median metaphase duration (user 2026-08-10)",
     "source_marks": "poles.csv label=pole, track identity grp:1 / grp:2, monitoring clip"},
    script=__file__,
    caption=("Spindle pole-to-pole distance over time in cells where both poles were manually marked, "
             "split into single- and triple-sisterless groups with an ordinary least-squares fit per "
             "group. Distance is measured only on frames carrying both pole marks. Anaphase excluded. "
             + " | ".join(stat_lines)),
    source=[A + "poles.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch", fig=png,
)
print("recorded G8_pole_distance_over_time")
