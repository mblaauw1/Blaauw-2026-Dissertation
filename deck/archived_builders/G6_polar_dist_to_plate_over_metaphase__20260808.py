"""Polar-kinetochore distance from the metaphase plate over metaphase: triple vs single sisterless.

USER 2026-08-08: "plot the distance a polar kinetochore is from the cell's metaphase plate over the course
of metaphase in a cell, and then also include on that plot the same for single sisterless cells."

DRIFT-IMMUNE BY CONSTRUCTION. She warned that the microscope stage sometimes moves in x-y, shifting the
cell inside the ROI, and that raw pixel movement must not be contaminated by it. The per-frame stage trace
is NOT available (see 2_TABLES_AND_REPORTS/PLOT_QUEUE_20260808.md §STAGE DRIFT: the columns exist but are blank in all 73
cached frame_data.csv, and the raw sidecars are on unmounted drives). This plot sidesteps the problem
entirely rather than correcting for it: BOTH the kinetochore centroid and the metaphase plate are her
marks in the SAME image frame, so a rigid stage translation moves them together and their separation is
unchanged. No auto-detection, no drift model needed.

METAPHASE WINDOW ONLY, and NO ANAPHASE (her standing rule 2026-08-08): frames are kept only in
[Metaphase Start, Anaphase Onset).

Cohort is by **# Sisterless KTs**, never by batch name (her rule: "you should determine whats a triple by
the # of sisterless kinetochores specified, not by the name").
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import os, csv, json, collections, numpy as np, matplotlib.pyplot as plt
import lib
lib.apply_style()
csv.field_size_limit(10 ** 9)

A = "/Volumes/4 MB/annotations/"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group6"; os.makedirs(OUT, exist_ok=True)
PLOT_ID = "G6_polar_dist_to_plate_over_metaphase"
SCRIPT = __file__

full, _ = lib.load_master(); MR = {r["Batch Name"]: r for r in full}
_dbl = lib.double_chromosome_batches()
_manual = set(lib.manual_plot_exclusions(PLOT_ID))


def nsis(b):
    v = (MR.get(b, {}).get("# Sisterless KTs", "") or "").strip()
    try:
        return int(float(v))
    except Exception:
        return None


# ---- her metaphase plate, per (batch, frame): the normalized line ---------------------------------
PLATE = {}
for r in csv.DictReader(open(A + "META_PLATE_NORMALIZED_20260728.csv", newline="", encoding="utf-8",
                             errors="replace")):
    try:
        key = (r["batch"].strip(), int(r["frame"]))
        PLATE[key] = (float(r["norm_x1"]), float(r["norm_y1"]),
                      float(r["norm_x2"]), float(r["norm_y2"]))
    except Exception:
        pass
print(f"plate lines: {len(PLATE)} (batch,frame) keys")


def dist_to_segment(px, py, x1, y1, x2, y2):
    """Perpendicular distance from the KT centroid to her plate LINE SEGMENT (not the infinite line --
    beyond the traced ends the nearest point on the plate is its end, which is what 'distance from the
    plate' means physically)."""
    vx, vy = x2 - x1, y2 - y1
    L2 = vx * vx + vy * vy
    if L2 <= 0:
        return float(np.hypot(px - x1, py - y1))
    t = max(0.0, min(1.0, ((px - x1) * vx + (py - y1) * vy) / L2))
    return float(np.hypot(px - (x1 + t * vx), py - (y1 + t * vy)))


# ---- polar tracks ---------------------------------------------------------------------------------
TR = [r for r in csv.DictReader(open(A + "KT_OUTLINE_TRACKS_20260723.csv", newline="", encoding="utf-8",
                                     errors="replace"))
      if (r.get("label") or "").strip() == "polar"]
print(f"polar track rows: {len(TR)}")

by_track = collections.defaultdict(list)
for r in TR:
    by_track[(r["batch"].strip(), r["track_id"])].append(r)

COH = {1: ("single sisterless", "#2166ac"), 3: ("triple sisterless", "#b2182b")}
rows, series = [], collections.defaultdict(list)
skip = collections.Counter()

for (b, tid), rs in by_track.items():
    n = nsis(b)
    if n not in COH:
        skip["cohort not 1 or 3 sisterless"] += 1; continue
    if lib.plot_excluded(b) or lib.is_mad1(b) or b in _dbl or b in _manual:
        skip["excluded batch"] += 1; continue
    ms = lib.parse_time(MR.get(b, {}).get("Metaphase Start (s)", ""))
    ana = lib.parse_time(MR.get(b, {}).get("Anaphase Onset (s)", ""))
    if ms is None:
        skip["no Metaphase Start"] += 1; continue
    ps = float(MR.get(b, {}).get("Pixel Size (um)", "") or 0.062)
    pts = []
    for r in sorted(rs, key=lambda x: float(x["t_sec"])):
        t = float(r["t_sec"])
        if t < ms:
            continue                              # before metaphase -> outside the requested window
        if ana is not None and t >= ana:
            continue                              # NO ANAPHASE (her rule)
        pl = PLATE.get((b, int(r["frame"])))
        if pl is None:
            continue                              # no plate traced on that frame -> nothing to measure against
        d_px = dist_to_segment(float(r["cx_px"]), float(r["cy_px"]), *pl)
        d_um = d_px * ps
        pts.append(((t - ms) / 60.0, d_um))
        rows.append([b, tid, n, f"{(t-ms)/60.0:.3f}", f"{d_um:.3f}"])
    if len(pts) >= 2:
        series[(b, tid, n)] = sorted(pts)
    else:
        skip["fewer than 2 usable frames"] += 1

print(f"polar tracks plotted: {len(series)}   rows: {len(rows)}")
for k, v in skip.items():
    print(f"   skipped {v:3d}  {k}")

# ---- figure ---------------------------------------------------------------------------------------
fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.4, 5.2), width_ratios=[1.4, 1])

seen = set()
for (b, tid, n), pts in sorted(series.items()):
    lab, c = COH[n]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    axA.plot(xs, ys, "-", color=c, lw=1.1, alpha=.62, zorder=2,
             label=(lab if lab not in seen else None))
    seen.add(lab)
axA.axhline(0, color="#444", lw=.9)
axA.set_xlabel("time from metaphase start (min)")
axA.set_ylabel("polar KT distance from metaphase plate (um)")
axA.set_title("Polar kinetochore distance from the plate, over metaphase", fontsize=10)
axA.legend(frameon=False, fontsize=8)
axA.text(.99, .01, "distance is between two of HER marks in the same frame,\n"
                   "so rigid stage drift cancels", transform=axA.transAxes,
         ha="right", va="bottom", fontsize=7, color="#555")

# binned mean per cohort, so the two groups are comparable despite different track counts
BIN = 2.0
MIN_TRACKS = 3        # a bin must be supported by >=3 DISTINCT tracks, not just >=3 points -- otherwise the
                      # long tail is one surviving cell drawn as if it were a cohort mean.
for n, (lab, c) in COH.items():
    allp = [(p[0], p[1], (bb, tt)) for (bb, tt, nn), pts in series.items() if nn == n for p in pts]
    if not allp:
        continue
    xs = np.array([p[0] for p in allp]); ys = np.array([p[1] for p in allp])
    tids = [p[2] for p in allp]
    edges = np.arange(0, max(xs.max(), BIN) + BIN, BIN)
    cx, cy, ce = [], [], []
    for i in range(len(edges) - 1):
        m = (xs >= edges[i]) & (xs < edges[i + 1])
        ntr = len({t for t, keep in zip(tids, m) if keep})
        if m.sum() >= 3 and ntr >= MIN_TRACKS:
            cx.append((edges[i] + edges[i + 1]) / 2); cy.append(ys[m].mean())
            ce.append(ys[m].std() / np.sqrt(m.sum()))
    if cx:
        axB.errorbar(cx, cy, yerr=ce, marker="o", color=c, lw=1.8, capsize=3,
                     label=f"{lab} (n={sum(1 for k in series if k[2]==n)} tracks)")
        print(f"   {lab}: binned to {cx[-1]:.0f} min (bins with >={MIN_TRACKS} tracks)")
axB.set_xlabel("time from metaphase start (min)")
axB.set_ylabel("mean distance from plate (um)")
axB.set_title(f"cohort mean, {BIN:.0f}-min bins (SEM; bins with >={MIN_TRACKS} tracks)", fontsize=9)
axB.legend(frameon=False, fontsize=8)

fig.tight_layout()
png = os.path.join(OUT, PLOT_ID + ".png")
fig.savefig(png, dpi=200); plt.close(fig)
print("wrote", png)

lib.record_plot(
    PLOT_ID,
    ["batch", "track_id", "n_sisterless", "t_rel_metaphase_min", "dist_to_plate_um"],
    rows,
    {"kind": "timeseries+binned", "window": "metaphase only", "anaphase": "excluded", "bin_min": BIN},
    script=SCRIPT,
    caption=("Perpendicular distance from each polar-kinetochore track centroid to her traced metaphase "
             "plate segment, over metaphase (t=0 metaphase start, cut at anaphase onset). Single- and "
             "triple-sisterless cohorts assigned by master '# Sisterless KTs', not by batch name. Both "
             "quantities are her marks in the same image frame, so rigid stage drift cancels exactly."),
    source=[A + "KT_OUTLINE_TRACKS_20260723.csv", A + "META_PLATE_NORMALIZED_20260728.csv",
            "/Volumes/4 MB/ABLATION_MASTER.csv"],
    key_column="batch",
    fig=png,
)
print("recorded", PLOT_ID)
