#!/usr/bin/env python3
"""DELTA-axis siblings of the artboard-4 line plots.

USER 2026-08-16: "maybe the axes on the plots should be changed to (delta rounding) or (delta cross
sectional area), etc etc to allow for all lines to have the same 'starting position' of 0".

USER 2026-08-19 (to-do list 0819 1pm) rewrote how they are DRAWN. Her figure item 5, verbatim:
    "Incorrectly made in that: these plots dont have error region as other plots do, and dont start at a
     y-value of 0 at metaphase start; lines dont mark horizontal median lines for groups at correct time
     (it seems it marks the median time for the samples used to build the actual line, and thats not what
     I want. I want the median from the main violin plot on the second art board.) and then you must make
     sure that a line continues until but stops at its corresponding median line. For these plots starting
     at metaphase onset, you must also make sure the trendline starts at t=0. Also some of these horizontal
     lines are labeled with text saying the line's time and thats not necessary..."
and her figure item 6:
    "1,2,and 3 off-target groups arent plotted as a single group in the plots above as they should be"

WHAT THAT MEANT IN CODE — the old version drew a bare binned MEDIAN line per RAW cohort with no band and no
median marker at all. It now goes through the SAME maths as the parent figures:
  * `trendlib.trend_to_mean_sem` + `sem_band`  -> identical binning and an SEM-across-CELLS band (item 5a).
  * the trend is anchored at (0, 0) explicitly -> every group leaves metaphase onset at zero (item 5b/5e).
    Zero is not approximate here: each trace is baselined on its own sample nearest t=0, so a group mean of
    those zeroed traces is zero at t=0 by construction; the anchor point makes the drawn line say so.
  * the group's vertical median line is `metaphase_medians` -- the median metaphase duration from the MAIN
    VIOLIN PLOT on artboard 2 (G1_violin2_no_dc_offtarget_journal), not the median of whichever cells this
    figure happens to contain (item 5c), and the trend runs to exactly that x and stops (item 5d).
  * no MM:SS text on the median lines (item 5f).
  * raw cohorts are folded into the SAME five groups as `group1_roundness.FAM`, so the three off-target
    control cohorts become one off-target line (item 6).

DECISIONS CARRIED FORWARD FROM 2026-08-16
  * Built as SIBLINGS, not replacements. The absolute-value plots carry information a delta destroys.
  * Subtracted per TRACE (per cell), never per group.
  * Built from each parent's RECORDED data CSV (batch, cohort, t_min, value), so the delta figure is
    guaranteed to describe exactly the cells its parent plots.

THE `_abl2meta` PARENTS (new 2026-08-19, figure item 1) are the ablation -> metaphase run-up versions. There
t=0 is metaphase onset at the RIGHT edge, so the trend runs from the left edge up to 0 and there is no median
line to draw -- the right edge IS metaphase onset for every group. The baseline stays the sample nearest t=0
for the same reason it is used everywhere else: it is the one time point every trace shares.
"""
import os, sys, csv, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
import metaphase_medians
from trendlib import trend_to_mean_sem, trend_percell_mean_sem, sem_band

lib.apply_style()
ROOT = "/Volumes/4 MB"
DATA = f"{ROOT}/ablation_plots/data"
OUT  = f"{ROOT}/ablation_figures_20260625/group1"
SCRIPT = __file__

COLLAGEN_KEY = metaphase_medians.COLLAGEN_KEY
OFFTARGET    = metaphase_medians.OFFTARGET_KEY
CANON_MED    = metaphase_medians.medians()

# raw cohort (as recorded in the parent data CSV) -> the group title used on the figure.
# Identical to group1_roundness.FAM; 2-Sisterless is absent by design (removed 2026-08-16).
FAM_OF = {
    "1-Sister": "1-Sisterless",
    "3-Sister": "3-Sisterless",
    COLLAGEN_KEY: COLLAGEN_KEY,
    "1-Sister Controls": OFFTARGET, "2-Sister Controls": OFFTARGET, "3-Sister Controls": OFFTARGET,
    "unModified": "unmodified",
}
ORDER = ["1-Sisterless", "3-Sisterless", COLLAGEN_KEY, OFFTARGET, "unmodified"]
COLOR = {"1-Sisterless": lib.PALETTE.get("1-Sister", "#009E73"),
         "3-Sisterless": lib.PALETTE.get("3-Sister", "#8e44ad"),
         COLLAGEN_KEY:   lib.PALETTE.get(COLLAGEN_KEY, "#e69f00"),
         OFFTARGET:      lib.PALETTE.get("1-Sister Controls", "#6a6a6a"),
         "unmodified":   lib.PALETTE.get("unModified", "#555555")}

# parent plot id -> (y-axis label, anchoring mode)
#   "meta"     : metaphase onset at t=0, window runs forward to the group's median metaphase duration
#   "abl2meta" : ablation -> metaphase onset, metaphase onset at t=0 on the RIGHT edge (item 1)
PARENTS = {
    "G1_roundness_combined_meta_trendscaled":         ("Δ roundness", "meta"),
    "G1_area_combined_meta_trendscaled":              ("Δ cell cross-sectional area (µm²)", "meta"),
    "G1_centroid_movement_combined_meta_trendscaled": ("Δ centroid movement (µm)", "meta"),
    "G1_plate_rotation_combined_meta_trendscaled":    ("Δ cumulative plate rotation (°)", "meta"),
    "G1_roundness_combined_abl2meta_trendscaled":         ("Δ roundness", "abl2meta"),
    "G1_area_combined_abl2meta_trendscaled":              ("Δ cell cross-sectional area (µm²)", "abl2meta"),
    "G1_centroid_movement_combined_abl2meta_trendscaled": ("Δ centroid movement (µm)", "abl2meta"),
    "G1_plate_rotation_combined_abl2meta_trendscaled":    ("Δ cumulative plate rotation (°)", "abl2meta"),
}


def build(pid, ylab, mode, only=None, suffix="", subtitle=""):
    """`only` restricts the figure to a subset of group titles; `suffix` names the variant.

    🔴 HER 2026-08-20, board-4 item 6: *"I also think the collagen characteristics that i could easily see in
    the previous versions of these figures arent clear anymore now that the collagen group is plotted with
    many groups, not just 3mb. Redo the four plots i paste below so that they dont include collagen, and then
    theres a similar four made with the collagen samples and the 3 on-target samples."*

    So each of the four metaphase-anchored plots now emits THREE renders from the same maths: the existing
    all-cohort one, a `_nocollagen` one, and a `_collagen_vs_3` one carrying only collagen against
    3-Sisterless. Done with a group filter rather than a forked builder so the binning, the SEM band, the
    artboard-2 median lines and the zeroing cannot drift between the variants.
    """
    src = f"{DATA}/{pid}.csv"
    if not os.path.exists(src):
        print(f"  skip (no data csv): {pid}"); return None
    rows = list(csv.DictReader(open(src)))
    if not rows:
        print(f"  skip (empty): {pid}"); return None

    per = collections.defaultdict(list)          # (group, batch) -> [(t, value)]
    for r in rows:
        fam = FAM_OF.get((r.get("cohort") or "").strip())
        if fam is None:                          # a cohort this plot family does not show
            continue
        if only is not None and fam not in only:
            continue
        try: per[(fam, r["batch"])].append((float(r["t_min"]), float(r["value"])))
        except Exception: continue

    pts3 = collections.defaultdict(list)         # group -> [(t, delta, cell)]
    cells = collections.defaultdict(set)
    recs = []
    for (fam, b), v in per.items():
        v.sort()
        if len(v) < 2: continue
        base = min(v, key=lambda q: abs(q[0]))[1]      # the sample nearest the alignment point t=0
        cells[fam].add(b)
        for t, val in v:
            pts3[fam].append((t, val - base, b))
            recs.append([b, fam, round(t, 4), round(val - base, 5)])
    if not pts3:
        print(f"  skip (no traces): {pid}"); return None

    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    slopes = {}
    for fam in ORDER:
        p3 = pts3.get(fam)
        if not p3 or len(p3) < 5: continue
        col = COLOR[fam]
        if mode == "abl2meta":
            md = 0.0; start = min(q[0] for q in p3)
        else:
            md = CANON_MED.get(fam)                    # item 5c: from the artboard-2 violin
            if md is None or md <= 0: continue
            start = 0.0                                # item 5e: the trend starts at t=0
        # 🔴 PER-CELL, not pooled (her 2026-08-25, "the lines ... jump up and down quite strangely").
        # Pooling every point in a bin let the cohort MEMBERSHIP change between neighbouring points -- on
        # this very figure the 3-sisterless line ran -21, -79, -303, -146, -325 off bins holding 10, 8, 5,
        # 7 and 7 cells with 5-7 cells replaced each step. Interpolating each cell onto the shared grid
        # inside its own measured range and averaging across cells gives -62, -122, -203, -281, -349: the
        # steady area loss that was there all along, with the zigzag gone.
        bx, by, bs, bn = trend_percell_mean_sem(p3, md, start=start)
        if len(bx) < 2: continue
        # item 5b: the line leaves metaphase onset at exactly zero. Every trace is baselined on its own t=0
        # sample, so the group mean there IS zero; the anchor makes the drawn polyline start (or, for the
        # run-up plots, finish) on it rather than at the first bin CENTRE, which sits a bin-half to the side.
        if mode == "abl2meta":
            if bx[-1] < -1e-9: bx = list(bx) + [0.0]; by = list(by) + [0.0]; bs = list(bs) + [0.0]
        else:
            if bx[0] > 1e-9: bx = [0.0] + list(bx); by = [0.0] + list(by); bs = [0.0] + list(bs)
        sem_band(ax, bx, by, bs, col)
        ax.plot(bx, by, color=col, lw=2.8, marker="o", ms=4, zorder=3,
                label=f"{fam} (N={len(cells[fam])}, {min(bn)}-{max(bn)} cells per point)" if bn
                else f"{fam} (N={len(cells[fam])})")
        if mode != "abl2meta":
            # item 5d: the trend runs to this line and stops on it. No text label (item 5f).
            ax.axvline(md, color=col, ls=(0, (2, 1.5)), lw=1.2)
        if len(bx) >= 2 and (bx[-1] - bx[0]) > 0:
            slopes[fam] = (by[-1] - by[0]) / (bx[-1] - bx[0])

    ax.axhline(0, color="#888", ls=":", lw=1.0, zorder=1)
    if mode == "abl2meta": ax.set_xlim(right=0.0)
    else:                  ax.set_xlim(left=0.0)
    ax.set_xlabel("Time from metaphase onset (min)")
    ax.set_ylabel(ylab)
    h, l = ax.get_legend_handles_labels()
    if mode != "abl2meta":
        h.append(Line2D([0], [0], color="#555", ls=(0, (2, 1.5)), lw=1.2))
        l.append("median metaphase duration (artboard-2 violin)")
    ax.legend(h, l, fontsize=7, ncol=2)
    ax.set_title(
        f"{ylab} — every trace zeroed at metaphase onset (group mean, shaded = SEM across cells)"
        + (f"\n{subtitle}" if subtitle else "")
        + ("\n(ablation → metaphase onset; t=0 is metaphase onset)" if mode == "abl2meta" else ""),
        loc="left", fontweight="bold", fontsize=9.5)
    fig.tight_layout()
    name = pid + "_delta" + suffix   # base name unchanged so existing deck placements just refresh
    # lib.apply_style() wraps savefig so a PNG written here is automatically mirrored to
    # _ai_relink/pdf/<name>.pdf AND (since 2026-08-18i) to the publication twin in pdf_pub/.
    fig.savefig(f"{OUT}/{name}.png", dpi=190, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot(name, ["batch", "cohort", "t_min", "delta_value"], recs,
                    {"type": "delta sibling (mean +/- SEM band)", "parent": pid,
                     "baseline": "each trace's own value at t=0 (metaphase onset)",
                     "median_line": "median metaphase duration from G1_violin2_no_dc_offtarget_journal"
                                    if mode != "abl2meta" else "none (window ends at metaphase onset)",
                     "grouping": "1/2/3 off-target controls pooled into one group (user 2026-08-19 item 6)",
                     "variant": (suffix.lstrip("_") or "all cohorts"),
                     "groups_shown": (", ".join(only) if only else "all")},
                    SCRIPT, f"{ylab} (delta sibling of {pid})", source=[src], key_column="batch")
    print(f"  wrote {name}.png  ({len(recs)} points, {len(pts3)} groups)")
    return name, slopes


if __name__ == "__main__":
    made = {}
    for pid, (ylab, mode) in PARENTS.items():
        r = build(pid, ylab, mode)
        if r: made[r[0]] = r[1]
        # her board-4 item 6: the metaphase-anchored four also get a collagen-free version and a
        # collagen-vs-3-on-target version, so the collagen behaviour is readable again
        if mode == "meta":
            r = build(pid, ylab, mode,
                      only=["1-Sisterless", "3-Sisterless", OFFTARGET, "unmodified"],
                      suffix="_nocollagen", subtitle="collagen cells excluded")
            if r: made[r[0]] = r[1]
            r = build(pid, ylab, mode,
                      only=[COLLAGEN_KEY, "3-Sisterless"],
                      suffix="_collagen_vs_3",
                      subtitle="collagen (2/3-sisterless on-target) against 3-sisterless on-target")
            if r: made[r[0]] = r[1]
    print(f"{len(made)} delta figures written")
