#!/usr/bin/env python3
"""MAD1 kinetochore-outline figures — the eYFP-Mad1 cells plotted SEPARATELY from the eYFP-Cdc20 deck
(user 2026-07-27: the kt-outline plots must contain only the cdc20 batches; Mad1 gets its own set).

Runs the same readers as the main pipeline but with KT_COHORT=mad1, so `lib.kt_outline_excluded` keeps
ONLY the Mad1 batches. Figures are written to group5_mad1_kt/ with a MAD1kt_ prefix so they can never
collide with, or be pulled into, the Cdc20 deck. Also writes MAD1_KT_OUTLINE_TRACKS_20260727.csv.

Run:  KT_COHORT=mad1 python3 kt_mad1_plots.py
"""
import os, sys, csv, collections
os.environ.setdefault("KT_COHORT", "mad1")
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
import lib, kt_stats
import kt_tracks as KT

assert lib.KT_COHORT == "mad1", "run with KT_COHORT=mad1"
lib.apply_style()
ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/group5_mad1_kt"
os.makedirs(OUT, exist_ok=True)
OUTCSV = f"{ROOT}/annotations/MAD1_KT_OUTLINE_TRACKS_20260727.csv"
STATES = ["polar", "paired", "lagging"]
COL = {"polar": "#e07b39", "paired": "#3b6fb6", "lagging": "#d1495b"}
METRICS = [("area_um2", "area (µm²)"), ("perimeter_um", "perimeter (µm)"), ("circularity", "circularity"),
           ("aspect_ratio", "aspect ratio"), ("major_um", "major axis (µm)"), ("solidity", "solidity")]

objs = KT.tracked_objects()
if not objs:
    raise SystemExit("no Mad1 kt_outline objects found")
mad = [o for o in objs if lib.is_mad1(o["batch"])]
assert len(mad) == len(objs), "cohort filter leaked non-Mad1 batches"

# ── per-frame table (the Mad1 twin of KT_OUTLINE_TRACKS) ──────────────────────────────────────────
cols = ["track_id", "batch", "label", "frame", "t_sec", "cx_px", "cy_px", "n_pieces"] + [m for m, _ in METRICS]
with open(OUTCSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for o in sorted(objs, key=lambda o: (o["batch"], o["label"], o["frame"])):
        row = dict(track_id=o["track_id"], batch=o["batch"], label=o["label"], frame=o["frame"],
                   t_sec=round(o["t_sec"], 2) if np.isfinite(o["t_sec"]) else "",
                   cx_px=round(o["cx"], 2), cy_px=round(o["cy"], 2), n_pieces=o["metrics"].get("n_pieces", 1))
        for m, _ in METRICS:
            v = o["metrics"].get(m)
            row[m] = round(v, 4) if isinstance(v, (int, float)) and np.isfinite(v) else ""
        w.writerow(row)
ntr = len({o["track_id"] for o in objs}); nb = len({o["batch"] for o in objs})
print(f"wrote {len(objs)} Mad1 tracked objects ({ntr} tracks, {nb} cells) -> {OUTCSV}")


def _save(fig, name, cap):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try:
        lib.record_plot(name, ["x"], [], {"family": "mad1_kt"}, script=__file__, caption=cap,
                        source=[OUTCSV], key_column=None, fig=fig)
    except Exception:
        pass
    print("  " + name)


def by_state(metric):
    g = collections.defaultdict(list)
    for o in objs:
        v = o["metrics"].get(metric)
        if isinstance(v, (int, float)) and np.isfinite(v):
            g[o["label"]].append(float(v))
    return {s: g[s] for s in STATES if g[s]}


# ── 1-6. shape metric by kinetochore state ────────────────────────────────────────────────────────
for metric, lab in METRICS:
    g = by_state(metric)
    if not g:
        continue
    order = [s for s in STATES if s in g]
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    dmax = max(max(v) for v in g.values())
    for i, s in enumerate(order):
        d = g[s]
        lib.journal_violin(ax, d, i, COL[s], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.22, d,
                   s=lib.VIOLIN_DOT_S, color=COL[s], alpha=0.45, lw=0)
        ax.hlines(np.median(d), i - 0.34, i + 0.34, color=COL[s], lw=2.4)
        ax.text(i, dmax * 1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9)
    ax.set_ylabel(lab); ax.set_ylim(top=dmax * 1.25)
    try:
        kt_stats.add_group_stats(ax, g, order, loc="upper left")
    except Exception:
        pass
    ax.set_title(f"Mad1 cells — kinetochore {lab} by state", loc="left", fontweight="bold", fontsize=11)
    _save(fig, f"MAD1kt_{metric}", f"Mad1 cohort: kinetochore {lab} by state")

# ── 7. shape over time, one line per track ────────────────────────────────────────────────────────
for metric, lab in [("area_um2", "area (µm²)"), ("aspect_ratio", "aspect ratio")]:
    tr = collections.defaultdict(list)
    for o in objs:
        v = o["metrics"].get(metric)
        if isinstance(v, (int, float)) and np.isfinite(v) and np.isfinite(o["t_sec"]):
            tr[(o["track_id"], o["label"])].append((o["t_sec"] / 60.0, float(v)))
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    for (tid, lb), pts in sorted(tr.items()):
        if len(pts) < 3:
            continue
        pts.sort(); x, y = zip(*pts)
        ax.plot(x, y, "-", lw=1.4, alpha=0.85, color=COL.get(lb, "#888"))
    from matplotlib.lines import Line2D
    ax.legend([Line2D([], [], color=COL[s], lw=2) for s in STATES], STATES, fontsize=8)
    ax.set_xlabel("time (min, t=0 at first ablation)"); ax.set_ylabel(lab)
    ax.set_title(f"Mad1 cells — kinetochore {lab} over time ({len(tr)} tracks)",
                 loc="left", fontweight="bold", fontsize=11)
    _save(fig, f"MAD1kt_{metric}_time", f"Mad1 cohort: {lab} over time, one line per kinetochore")

# ── 8. cohort composition: tracks and frames per cell ─────────────────────────────────────────────
cells = sorted({o["batch"] for o in objs})
cnt = collections.defaultdict(lambda: collections.Counter())
for o in objs:
    cnt[o["batch"]][o["label"]] += 1
fig, ax = plt.subplots(figsize=(8.6, 0.5 * len(cells) + 2.2))
ypos = np.arange(len(cells)); left = np.zeros(len(cells))
for s in STATES:
    vals = np.array([cnt[c][s] for c in cells], float)
    ax.barh(ypos, vals, left=left, color=COL[s], label=s, height=0.62)
    left += vals
def _short(c):   # keep the TAIL: these cells differ only in their trailing _NN
    return c if len(c) <= 46 else c[:12] + "…" + c[-33:]
ax.set_yticks(ypos); ax.set_yticklabels([_short(c) for c in cells], fontsize=7.5)
ax.invert_yaxis(); ax.set_xlabel("kinetochore-frames outlined"); ax.legend(fontsize=8)
ax.set_title(f"Mad1 cohort composition ({len(cells)} cells, {ntr} kinetochore tracks)",
             loc="left", fontweight="bold", fontsize=11)
_save(fig, "MAD1kt_cohort_composition", "Mad1 cohort: outlined kinetochore-frames per cell and state")

print(f"\nAll Mad1 kinetochore figures -> {OUT}")
