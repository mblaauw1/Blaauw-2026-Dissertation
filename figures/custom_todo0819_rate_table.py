#!/usr/bin/env python3
"""G1_shape_rate_table — average rate (slope) of every group's line, in all four shape/movement categories.

USER 2026-08-19 (to-do list 0819 1pm), figure item 8:
    "Move the two plots below to the supplemental. Then, on the main figures artboard where they were, make a
     table listing the overall average rates (slopes) as plotted on the plots starting at metaphase onset
     (not the ones with prometaphase data) for each group's line in the four categories"

WHICH PLOTS: "starting at metaphase onset, not the ones with prometaphase data" is the `*_combined_meta_*`
family -- metaphase onset -> anaphase. The ablation->metaphase run-up versions built for her item 1
(`*_abl2meta_*`) are deliberately EXCLUDED here: those are the ones that carry the prometaphase data, and
they move to the supplemental deck.

THE FOUR CATEGORIES are the four metrics she names in item 1: roundness, cross-sectional area, plate
rotation, centroid movement.

WHAT THE NUMBER IS: the overall rate of the line as drawn -- (value at the group's median metaphase duration
minus value at metaphase onset) / that duration -- computed from the SAME binned-mean trend the figure plots,
through the same `trendlib` call, so the table cannot drift from the picture.

A SECOND number per cell gives the PER-CELL median slope. Her standing rule is that a cohort comparison must
aggregate to the CELL (per-track/per-point pooling is pseudoreplication and has already killed one result
here), so the honest summary statistic sits beside the descriptive one rather than replacing it.
"""
import collections
import csv
import os
import sys

import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import metaphase_medians
from trendlib import trend_to_mean_sem, anchor_trend

lib.apply_style()
ROOT = "/Volumes/4 MB"
DATA = f"{ROOT}/ablation_plots/data"
OUT = f"{ROOT}/ablation_figures_20260625/group1"
SCRIPT = __file__

COLLAGEN_KEY = metaphase_medians.COLLAGEN_KEY
OFFTARGET = metaphase_medians.OFFTARGET_KEY
CANON_MED = metaphase_medians.medians()

FAM_OF = {
    "1-Sister": "1-Sisterless", "3-Sister": "3-Sisterless", COLLAGEN_KEY: COLLAGEN_KEY,
    "1-Sister Controls": OFFTARGET, "2-Sister Controls": OFFTARGET, "3-Sister Controls": OFFTARGET,
    "unModified": "unmodified",
}
ROWS = ["1-Sisterless", "3-Sisterless", COLLAGEN_KEY, OFFTARGET, "unmodified"]

# column header -> (parent plot id, unit of the rate)
COLS = [
    ("Roundness",              "G1_roundness_combined_meta_trendscaled",         "1/min"),
    ("Cross-sectional area",   "G1_area_combined_meta_trendscaled",              "µm²/min"),
    ("Cumulative plate rotation", "G1_plate_rotation_combined_meta_trendscaled", "°/min"),
    ("Cumulative centroid movement", "G1_centroid_movement_combined_meta_trendscaled", "µm/min"),
]


def per_group(pid):
    """-> {group: [(t, value, cell), ...]} from a parent figure's recorded data CSV."""
    src = f"{DATA}/{pid}.csv"
    if not os.path.exists(src):
        return {}
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(src)):
        fam = FAM_OF.get((r.get("cohort") or "").strip())
        if fam is None:
            continue
        try:
            out[fam].append((float(r["t_min"]), float(r["value"]), r["batch"]))
        except Exception:
            continue
    return out


def rates(pid):
    """-> {group: (trend_slope, percell_median_slope, n_cells)} over [0, that group's median metaphase]."""
    data = per_group(pid)
    out = {}
    for fam, p3 in data.items():
        md = CANON_MED.get(fam)
        if md is None or md <= 0:
            continue
        win = [q for q in p3 if 0.0 <= q[0] <= md + 1e-9]
        cells = {q[2] for q in win}
        if len(win) < 5 or not cells:
            continue
        bx, by, bs = trend_to_mean_sem(win, md, start=0.0)
        bx, by, bs = anchor_trend(bx, by, bs, 0.0, at_start=True)
        trend = (by[-1] - by[0]) / (bx[-1] - bx[0]) if len(bx) >= 2 and bx[-1] > bx[0] else None
        # per-cell slopes, then the median across cells (her cell-level aggregation rule)
        pc = []
        by_cell = collections.defaultdict(list)
        for t, v, c in win:
            by_cell[c].append((t, v))
        for c, v in by_cell.items():
            v.sort()
            if len(v) >= 2 and v[-1][0] > v[0][0]:   # 2 points inside the window still define a slope;
                #  requiring 3 silently emptied the off-target column, whose window is only ~10 min
                pc.append(float(np.polyfit([q[0] for q in v], [q[1] for q in v], 1)[0]))
        out[fam] = (trend, float(np.median(pc)) if pc else None, len(cells))
    return out


def fmt(v, unit):
    if v is None:
        return "—"
    a = abs(v)
    if a >= 100:   return f"{v:+.0f}"
    if a >= 1:     return f"{v:+.2f}"
    if a >= 0.01:  return f"{v:+.3f}"
    return f"{v:+.2e}"


def main():
    table = {c[0]: rates(c[1]) for c in COLS}
    present = [r for r in ROWS if any(r in table[c[0]] for c in COLS)]

    fig, ax = plt.subplots(figsize=(11.4, 0.78 * (len(present) + 1) + 1.35))
    ax.axis("off")
    header = ["Group"] + [f"{name}\n({unit})" for name, _, unit in COLS]
    body = []
    recs = []
    for fam in present:
        row = [f"{lib.LABEL.get(fam, fam)}"]
        for name, pid, unit in COLS:
            cell = table[name].get(fam)
            if cell is None:
                row.append("—")
                continue
            tr, pcm, n = cell
            row.append(f"{fmt(tr, unit)}\n(per-cell {fmt(pcm, unit)}, n={n})")
            recs.append([fam, name, unit,
                         None if tr is None else round(tr, 6),
                         None if pcm is None else round(pcm, 6), n,
                         round(CANON_MED.get(fam, float('nan')), 3)])
        body.append(row)

    t = ax.table(cellText=body, colLabels=header, cellLoc="center", loc="upper center")
    t.auto_set_font_size(False); t.set_fontsize(8.2); t.scale(1, 2.0)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#cfcfcf")
        if r == 0:
            cell.set_facecolor("#f2f2f2"); cell.set_text_props(fontweight="bold")
        elif c == 0:
            cell.set_text_props(fontweight="bold", ha="left"); cell.PAD = 0.04
        if r > 0 and c == 0:
            fam = present[r - 1]
            cell.set_facecolor("#ffffff")
            import matplotlib.colors as _mc
            _c = lib.PALETTE.get({"1-Sisterless": "1-Sister", "3-Sisterless": "3-Sister",
                                  OFFTARGET: "1-Sister Controls", "unmodified": "unModified"}.get(fam, fam), "#333")
            _r, _g, _b = _mc.to_rgb(_c)          # darkened: the pale control green was unreadable as text
            cell.set_text_props(color=(_r * .68, _g * .68, _b * .68), fontweight="bold")

    ax.set_title("Average rate of change over metaphase, by group\n"
                 "metaphase onset → that group's median metaphase duration (from the artboard-2 violin)",
                 loc="left", fontweight="bold", fontsize=11)
    fig.text(0.005, -0.02,
             "Top figure in each cell: the overall rate of the group's plotted line "
             "(value at the median metaphase duration minus value at metaphase onset, divided by that duration) "
             "— the same binned-mean trend the line plots draw.\n"
             "In brackets: the median of the PER-CELL slopes, with the number of cells. The per-cell figure is "
             "the one to compare between groups: pooling every frame would treat one cell's many outlines as "
             "independent observations.\n"
             "Built from the metaphase-onset plots only; the ablation→metaphase run-up versions "
             "(prometaphase data) are on the supplemental deck and are not summarised here.",
             fontsize=6.6, color="#555", va="bottom", ha="left", linespacing=1.5)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G1_shape_rate_table.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("G1_shape_rate_table",
                    ["group", "category", "unit", "trend_slope", "percell_median_slope", "n_cells",
                     "median_metaphase_min"],
                    recs,
                    {"type": "summary table",
                     "window": "metaphase onset -> that group's median metaphase duration",
                     "median_source": "G1_violin2_no_dc_offtarget_journal (artboard-2 violin)",
                     "excludes": "the *_abl2meta_* run-up versions (prometaphase data), per item 8"},
                    SCRIPT, "Average rate of change over metaphase, by group, in four categories")
    print(f"wrote G1_shape_rate_table.png  ({len(present)} groups x {len(COLS)} categories, {len(recs)} cells)")


if __name__ == "__main__":
    main()
