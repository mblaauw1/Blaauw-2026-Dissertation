"""custom_rtf_questions_20260722.py — the "plots that should exist" questions that had no figure.

Built 2026-07-22 from `~/Documents/plots that should exist.rtf` after a cross-check against copy.ai found
these uncovered. Every metric below is either (a) copied from an existing builder, or (b) derived from the
user's own annotations and VALIDATED against a value she recorded. Nothing here is a guessed definition —
that failure mode retired four figures on 2026-07-22 (see NOTES §14 / HANDOFF §17).

  Q4  G4_oscillation_vs_plate_distance          oscillation magnitude vs distance to the plate
  Q5  G3_length_vs_precongression_plate_distance chromosome length vs how close it sits before congressing
  Q6  G4_oscillation_vs_time_to_event           oscillation magnitude approaching congression / anaphase
  Q7  G4_polar_position_vs_time_to_anaphase     permanent-polar position over the run-up to anaphase
  Q3b G3_position_along_plate_normal_vs_behavior position on the spindle axis defined as the PLATE NORMAL
      (the existing G3_ablation_location_vs_behavior uses the cell-SHAPE axis; the RTF explicitly asks for
       "perpendicular to metaphase plate" as the alternative definition — that is the uncovered half)

SOURCES (all manual annotations, per the standing manual-over-TrackMate rule):
  kt_points.csv  label polar/sisterless  -> KT track          (loader copied from group4_movement.py)
  meta_plates.csv                        -> plate polyline     (nearest-frame, pt_poly perpendicular distance)
  cell_outlines.csv                      -> cell frame         (cell_frame() copied from custom_plate_pole_model_v3.py)
  CHROMOSOME_MASTER.csv                  -> length, behavior, congression time
  ABLATION_MASTER.csv                    -> metaphase / anaphase times
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, json, os, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"
OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
SCRIPT = __file__
lib.apply_style()

data, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in data}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()
def ps(b):
    try: return float(gv(b, "Pixel Size (um)"))
    except Exception: return 0.062

INTERVAL = 20.0
OSC_HI = 8.0            # same implausible-step cap as group4_movement.py


def disp20(dx_um, dy_um, dt):
    if dt is None or dt <= 0 or dt > 120: return None
    return np.hypot(dx_um, dy_um) * (INTERVAL / dt)


# ---------------- KT tracks (loader mirrors group4_movement.py) ----------------
rows = list(csv.reader(open("/Volumes/4 MB/annotations/kt_points.csv")))
ix = {c: i for i, c in enumerate(rows[0])}
trk = defaultdict(lambda: defaultdict(list))
for r in rows[1:]:
    lab = r[ix['label']].strip()
    if lab not in ("polar", "sisterless"): continue
    b = r[ix['batch']].strip()
    if lib.is_mad1(b) or lib.plot_excluded(b): continue
    if lib.is_misplaced_id(r[ix['id']]): continue
    try: trk[b][lab].append((int(r[ix['frame']]), float(r[ix['t_sec']]), float(r[ix['x']]), float(r[ix['y']])))
    except Exception: pass


def sister(b):
    a = trk[b].get('polar', []); c = trk[b].get('sisterless', [])
    return sorted(a if len(a) >= len(c) else c)


LONG_SAMPLE = "20250401 ptk_yfpcdc20_28"       # same temporal outlier group4_movement drops
MIN_SPAN_S = 300.0     # a "track" must actually span time
MIN_TPTS = 5           # ...at >=5 DISTINCT timepoints


def track_ok(b):
    """A mark count alone is not a track. Several cells carry 5+ marks that all sit within a few SECONDS
    of each other (e.g. 20250410 ptk_yfpcdc20_11: 5 marks spanning 8 s) — those are a single timepoint,
    and any time-derived quantity computed from them is meaningless. Found 2026-07-22 when the
    track-derived congression time disagreed with the recorded one on exactly those cells."""
    tr = sister(b)
    ts = sorted({round(t, 1) for (_f, t, _x, _y) in tr})
    return len(ts) >= MIN_TPTS and (ts[-1] - ts[0]) >= MIN_SPAN_S


usable = [b for b in trk if track_ok(b) and b != LONG_SAMPLE and not lib.excluded(b)]

# ---------------- metaphase plate ----------------
mp = list(csv.reader(open("/Volumes/4 MB/annotations/meta_plates.csv")))
jx = {c: i for i, c in enumerate(mp[0])}
plates = defaultdict(dict)
for r in mp[1:]:
    try: plates[r[jx['batch']].strip()][int(r[jx['frame']])] = np.array(json.loads(r[jx['points']]), float)
    except Exception: pass


def plate_at(b, f):
    pmv = plates.get(b)
    if not pmv: return None
    return pmv[f] if f in pmv else pmv[min(pmv, key=lambda k: abs(k - f))]


def pt_poly(p, poly):
    p = np.array(p, float); d = 1e18
    for i in range(len(poly) - 1):
        a, bb = poly[i], poly[i + 1]; ab = bb - a; L = float(np.dot(ab, ab))
        t = 0 if L < 1e-9 else float(np.clip(np.dot(p - a, ab) / L, 0, 1))
        d = min(d, float(np.hypot(*(a + t * ab - p))))
    return d


def plate_dist_um(b, f, x, y):
    poly = plate_at(b, f)
    if poly is None or len(poly) < 2: return None
    return pt_poly((x, y), poly) * ps(b)


# ---------------- cell frame (copied from custom_plate_pole_model_v3.py) ----------------
_co = list(csv.reader(open("/Volumes/4 MB/annotations/cell_outlines.csv")))
cx = {c: i for i, c in enumerate(_co[0])}
outl = defaultdict(dict)
for r in _co[1:]:
    try:
        b = r[cx['batch']].strip(); p = np.array(json.loads(r[cx['points']]), float)
        if len(p) >= 6: outl[b][int(r[cx['frame']])] = p
    except Exception: pass


def cell_frame(poly):
    c = poly.mean(0); _, _, vt = np.linalg.svd(poly - c); d1 = vt[0]
    if d1[0] < 0 or (d1[0] == 0 and d1[1] < 0): d1 = -d1
    d2 = np.array([-d1[1], d1[0]])
    e1 = np.abs((poly - c) @ d1).max() or 1.0
    e2 = np.abs((poly - c) @ d2).max() or 1.0
    return c, d1, d2, e1, e2


def outline_at(b, f):
    o = outl.get(b)
    if not o: return None
    return o[f] if f in o else o[min(o, key=lambda k: abs(k - f))]


# ---------------- per-chromosome table ----------------
chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    chromo[r["batch"].strip()].append(r)


def single_length(b):
    """Chromosome length for a cell where the KT track is unambiguously ONE chromosome.
    Multi-sisterless cells have several chromosomes and one merged track, so a length cannot be
    attributed — those are skipped rather than guessed."""
    rs = [r for r in chromo.get(b, []) if (r.get("length_um") or "").strip()]
    if gv(b, "# Sisterless KTs") != "1" or len(rs) != 1: return None
    try: return float(rs[0]["length_um"])
    except Exception: return None


def behavior(b):
    rs = chromo.get(b, [])
    return rs[0].get("behavior", "").strip() if len(rs) == 1 else ""


def ev(b, col):
    return lib.parse_time(gv(b, col))


# ---------------- congression from the track, VALIDATED against her recorded time ----------------
CONG_UM = 2.0          # a KT is "at the plate" within 2 µm of the drawn plate line
CONG_HOLD = 2          # and must stay there for >= 2 consecutive marks


def congression_t(b):
    """First time the KT reaches and HOLDS the plate. Derived from the track + the drawn plate rather
    than read from a column, because the recorded congression times live on a different clock. Validated
    below against CHROMOSOME_MASTER.congression_time_s for every cell that has one."""
    tr = sister(b)
    ta = ev(b, "Anaphase Onset (s)")
    hits = []
    for (f, t, x, y) in tr:
        if ta is not None and t > ta: continue   # after anaphase the "plate" has split — not a congression
        d = plate_dist_um(b, f, x, y)
        if d is None: continue
        hits.append((t, d))
    for i in range(len(hits) - CONG_HOLD + 1):
        if all(hits[i + k][1] <= CONG_UM for k in range(CONG_HOLD)):
            return hits[i][0]
    return None


def validate_congression():
    pairs = []
    for b in usable:
        rs = [r for r in chromo.get(b, []) if (r.get("congression_time_s") or "").strip()]
        if len(rs) != 1: continue
        tc = congression_t(b)
        if tc is None: continue
        try: rec = float(rs[0]["congression_time_s"])
        except Exception: continue
        pairs.append((b, tc, rec))
    if len(pairs) >= 3:
        a = np.array([p[1] for p in pairs]); c = np.array([p[2] for p in pairs])
        rho, pv = stats.spearmanr(a, c)
        print(f"[validate] track-derived vs recorded congression time: N={len(pairs)} "
              f"rho={rho:.3f} p={pv:.4g} median|diff|={np.median(np.abs(a-c))/60:.1f} min")
    else:
        print(f"[validate] only {len(pairs)} cells have BOTH a track-derived and a recorded congression time")
    return pairs


# ================================================================= Q4
def q4():
    xs, ys, cells = [], [], []
    for b in usable:
        tr = sister(b)
        for (f0, t0, x0, y0), (f1, t1, x1, y1) in zip(tr, tr[1:]):
            if f1 == f0: continue
            d = disp20((x1 - x0) * ps(b), (y1 - y0) * ps(b), t1 - t0)
            if d is None or d > OSC_HI: continue
            pd0 = plate_dist_um(b, f0, x0, y0); pd1 = plate_dist_um(b, f1, x1, y1)
            if pd0 is None or pd1 is None: continue
            xs.append(0.5 * (pd0 + pd1)); ys.append(d); cells.append(b)
    if len(xs) < 10:
        print("Q4: too few steps"); return
    xs = np.array(xs); ys = np.array(ys)
    rho, pv = stats.spearmanr(xs, ys)
    fig, ax = plt.subplots(figsize=(6.6, 5))
    ax.scatter(xs, ys, s=13, alpha=.45, color="#762a83", edgecolor="none")
    # binned median trend
    bins = np.linspace(0, np.percentile(xs, 98), 9)
    bc, bm = [], []
    for i in range(len(bins) - 1):
        m = (xs >= bins[i]) & (xs < bins[i + 1])
        if m.sum() >= 5: bc.append(.5 * (bins[i] + bins[i + 1])); bm.append(np.median(ys[m]))
    if bc: ax.plot(bc, bm, "-o", color="#b30000", lw=2, ms=5, label="binned median")
    ax.set_xlabel("Distance to metaphase plate (µm)")
    ax.set_ylabel(f"Oscillation — displacement per {INTERVAL:.0f}s (µm)")
    ax.set_title(f"Kinetochore oscillation vs distance from the plate\n"
                 f"polar/sisterless KTs, manual marks — N={len(xs)} steps, {len(set(cells))} cells; "
                 f"Spearman ρ={rho:.2f}, p={pv:.3g}", loc="left", fontweight="bold", fontsize=10)
    ax.legend(fontsize=8)
    plt.tight_layout(); fig.savefig(f"{OUT4}/G4_oscillation_vs_plate_distance.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G4_oscillation_vs_plate_distance", ["plate_dist_um", "disp_um_per_20s", "batch"],
                    [[round(a, 3), round(c, 4), d] for a, c, d in zip(xs, ys, cells)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N_steps": len(xs),
                     "N_cells": len(set(cells))}, SCRIPT,
                    "Oscillation magnitude vs distance to the metaphase plate (Q4)")
    print(f"Q4: N={len(xs)} steps rho={rho:.3f} p={pv:.3g}")


# ================================================================= Q5
def q5():
    L, D, cells = [], [], []
    for b in usable:
        ln = single_length(b)
        if ln is None: continue
        tc = congression_t(b)
        if tc is None: continue                 # only congressing chromosomes have a "before congressing"
        pre = []
        for (f, t, x, y) in sister(b):
            if not (tc - 600 <= t < tc): continue      # the 10 min before it reaches the plate
            d = plate_dist_um(b, f, x, y)
            if d is not None: pre.append(d)
        if len(pre) < 3: continue
        L.append(ln); D.append(float(np.median(pre))); cells.append(b)
    # USER 2026-07-29: "keep making it". The old floor was len(L) < 5, and the qualifying set fell to 4
    # after the label/centering work, so the figure silently stopped regenerating while a PRE-FIX
    # version stayed placed in the deck - the worst outcome, because it looks current. Plot at N>=3
    # (the minimum for a Spearman) and put N in the title, which it already does, so a small N is
    # visible on the figure instead of hidden in a log line.
    if len(L) < 3:
        print(f"Q5: only {len(L)} cells qualify (need 3) — not plotted"); return
    if len(L) < 5:
        print(f"Q5: WARNING plotting with only {len(L)} cells — treat rho as indicative")
    L = np.array(L); D = np.array(D)
    rho, pv = stats.spearmanr(L, D)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.scatter(L, D, s=42, color="#1b7837", alpha=.8, edgecolor="#0b3d1b")
    if len(L) >= 4:
        m, c0 = np.polyfit(L, D, 1); xr = np.linspace(L.min(), L.max(), 20)
        ax.plot(xr, m * xr + c0, "--", color="#b30000", lw=1.6)
    for x, y, b in zip(L, D, cells):
        ax.annotate(b.split()[-1], (x, y), fontsize=6, color="#555", xytext=(3, 3), textcoords="offset points")
    ax.set_xlabel("Chromosome length (µm)")
    ax.set_ylabel("Median distance to plate in the 10 min\nbefore congression (µm)")
    ax.set_title(f"Do longer chromosomes sit closer to the plate before congressing?\n"
                 f"1-sisterless cells with an unambiguous length — N={len(L)}; "
                 f"Spearman ρ={rho:.2f}, p={pv:.3g}", loc="left", fontweight="bold", fontsize=10)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_length_vs_precongression_plate_distance.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G3_length_vs_precongression_plate_distance",
                    ["length_um", "median_plate_dist_pre_um", "batch"],
                    [[round(a, 3), round(c, 3), d] for a, c, d in zip(L, D, cells)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(L),
                     "window_s": 600, "cong_thresh_um": CONG_UM}, SCRIPT,
                    "Chromosome length vs pre-congression plate distance (Q5)")
    print(f"Q5: N={len(L)} rho={rho:.3f} p={pv:.3g}")


# ================================================================= Q6
def q6():
    series = {"to congression": [], "to anaphase": []}
    for b in usable:
        tr = sister(b)
        tc = congression_t(b); ta = ev(b, "Anaphase Onset (s)")
        for (f0, t0, x0, y0), (f1, t1, x1, y1) in zip(tr, tr[1:]):
            if f1 == f0: continue
            d = disp20((x1 - x0) * ps(b), (y1 - y0) * ps(b), t1 - t0)
            if d is None or d > OSC_HI: continue
            tm = .5 * (t0 + t1)
            if tc is not None and tm <= tc:
                series["to congression"].append(((tm - tc) / 60.0, d, b))
            if ta is not None and tm <= ta:
                series["to anaphase"].append(((tm - ta) / 60.0, d, b))
    # USER 2026-08-03: "omit all points above a displacement of 2um; then replot and remake trend lines.
    # Dont make the 'to congression' one anymore. Just make the 'to anaphase' one and make sure that each
    # group has its own trendline." That was applied to the _traces companion on 2026-07-29 but NOT here,
    # so this parent kept drawing the congression panel and a single pooled binned median -- and both
    # figures sit on M5, so she was still looking at the panel she asked to stop making.
    # Groups are the SAME chromosome-size tertiles the _traces companion uses, so the pair agrees.
    DISP_MAX = 2.0
    EVENT = "to anaphase"
    length = {}
    for b, rs in chromo.items():
        vals = [float(x["length_um"]) for x in rs if (x.get("length_um") or "").strip()]
        if vals: length[b] = float(np.mean(vals))
    q1, q2 = (np.quantile(list(length.values()), [1/3, 2/3]) if len(length) >= 3 else (None, None))
    def cls(b):
        v = length.get(b)
        if v is None or q1 is None: return None
        return "small" if v <= q1 else ("medium" if v <= q2 else "large")
    CLSCOL = {"large": "#0b3d91", "medium": "#2ec4b6", "small": "#9ecae1"}

    v = [p for p in series[EVENT] if p[1] <= DISP_MAX]
    n_over = len(series[EVENT]) - len(v)
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    stats_out = {}
    if len(v) < 10:
        ax.text(.5, .5, f"too few steps ({len(v)})", ha="center", transform=ax.transAxes)
    else:
        pts = [(a, c, cls(b)) for a, c, b in v if a >= -30]
        for cgrp in ("large", "medium", "small"):
            g = [p for p in pts if p[2] == cgrp]
            if not g: continue
            gx = np.array([p[0] for p in g]); gy = np.array([p[1] for p in g])
            ax.scatter(gx, gy, s=11, alpha=.45, color=CLSCOL[cgrp], edgecolor="none",
                       label=f"{cgrp} chromosome (n={len(g)})")
            if len(gx) >= 3 and gx.max() - gx.min() > 1e-9:
                grho, gp = stats.spearmanr(gx, gy)
                m, c0 = np.polyfit(gx, gy, 1)
                xx = np.linspace(gx.min(), gx.max(), 60)
                ax.plot(xx, m * xx + c0, ls="--", lw=2.0, color=CLSCOL[cgrp],
                        label=f"{cgrp} trend (ρ={grho:.2f}, p={gp:.2g})")
                stats_out[cgrp] = {"rho": round(float(grho), 3), "p": float(gp), "N": int(len(gx))}
        allx = np.array([p[0] for p in pts]); ally = np.array([p[1] for p in pts])
        rho, pv = stats.spearmanr(allx, ally)
        stats_out["pooled"] = {"rho": round(float(rho), 3), "p": float(pv), "N": int(len(allx))}
        ax.axvline(0, color="#444", lw=1, ls=":")
        ax.set_xlabel("Minutes relative to anaphase onset (0 = anaphase)")
        ax.set_ylabel(f"Displacement per {INTERVAL:.0f}s (µm)")
        ax.set_title(f"Oscillation approaching anaphase — pooled ρ={rho:.2f}, p={pv:.3g}, N={len(allx)}",
                     loc="left", fontsize=9.5, fontweight="bold")
        ax.legend(fontsize=7.5)
    fig.suptitle("Does kinetochore oscillation intensify approaching anaphase? (movement only)",
                 fontweight="bold", fontsize=11, x=.01, ha="left")
    fig.text(.01, -.02, f"points above {DISP_MAX:.0f} µm per {INTERVAL:.0f}s omitted ({n_over} removed); "
                        f"one trendline per chromosome-size tertile; the 'to congression' panel is no longer produced",
             fontsize=7.2, color="#555")
    plt.tight_layout(rect=[0, 0, 1, .94])
    fig.savefig(f"{OUT4}/G4_oscillation_vs_time_to_event.png", bbox_inches="tight", dpi=130); plt.close(fig)
    allrows = [[EVENT, round(a, 3), round(c, 4), b, cls(b) or ""] for a, c, b in v]
    lib.record_plot("G4_oscillation_vs_time_to_event",
                    ["event", "min_to_event", "disp_um_per_20s", "batch", "chromosome_size_group"],
                    allrows, dict(stats_out, disp_max_um_per_20s=DISP_MAX, n_omitted_over_max=n_over,
                                  event=EVENT, tertiles_um=[round(float(q1), 3), round(float(q2), 3)] if q1 is not None else None),
                    SCRIPT, "Oscillation magnitude approaching anaphase, by chromosome size (Q6)")
    print(f"Q6: {stats_out}  ({n_over} points over {DISP_MAX} µm omitted)")


# ================================================================= Q7
def q7():
    pts, cells = [], []
    for b in usable:
        if behavior(b) != "noncongression": continue      # permanent polar only
        ta = ev(b, "Anaphase Onset (s)")
        if ta is None: continue
        for (f, t, x, y) in sister(b):
            if t > ta: continue
            d = plate_dist_um(b, f, x, y)
            if d is None: continue
            o = outline_at(b, f)
            pa = np.nan
            if o is not None:
                c, d1, d2, e1, e2 = cell_frame(o)
                pa = abs(float((np.array([x, y]) - c) @ d1 / e1))
            pts.append(((t - ta) / 60.0, d, pa, b)); cells.append(b)
    if len(pts) < 10:
        print(f"Q7: only {len(pts)} points — not plotted"); return
    x = np.array([p[0] for p in pts]); dd = np.array([p[1] for p in pts]); pa = np.array([p[2] for p in pts])
    keep = x >= -40; x, dd, pa = x[keep], dd[keep], pa[keep]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8))
    out = {}
    for ax, (y, lab, col) in zip(axes, [(dd, "Distance to metaphase plate (µm)", "#762a83"),
                                        (pa, "Position on the cell long axis\n(0 = equator, 1 = pole)", "#e08214")]):
        m = ~np.isnan(y)
        if m.sum() < 10:
            ax.text(.5, .5, "no data", ha="center", transform=ax.transAxes); continue
        ax.scatter(x[m], y[m], s=14, alpha=.45, color=col, edgecolor="none")
        bins = np.linspace(x[m].min(), 0, 10); bc, bm = [], []
        for i in range(len(bins) - 1):
            mm = (x >= bins[i]) & (x < bins[i + 1]) & m
            if mm.sum() >= 4: bc.append(.5 * (bins[i] + bins[i + 1])); bm.append(np.median(y[mm]))
        if bc: ax.plot(bc, bm, "-o", color="#b30000", lw=2, ms=5, label="binned median")
        rho, pv = stats.spearmanr(x[m], y[m])
        out[lab.splitlines()[0]] = {"rho": round(float(rho), 3), "p": float(pv), "N": int(m.sum())}
        ax.axvline(0, color="#444", lw=1, ls=":")
        ax.set_xlabel("Minutes relative to anaphase onset (0 = anaphase)")
        ax.set_ylabel(lab)
        ax.set_title(f"ρ={rho:.2f}, p={pv:.3g}, N={int(m.sum())}", loc="left", fontsize=9.5, fontweight="bold")
        ax.legend(fontsize=8)
    fig.suptitle("Permanently-polar kinetochores: does their position change approaching anaphase?\n"
                 "NOTE: poles.csv is empty, so 'pole' is the CELL LONG AXIS from the manual outline "
                 "(the same proxy the plate/pole model uses), not a marked spindle pole.",
                 fontweight="bold", fontsize=10, x=.01, ha="left")
    plt.tight_layout(rect=[0, 0, 1, .90])
    fig.savefig(f"{OUT4}/G4_polar_position_vs_time_to_anaphase.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G4_polar_position_vs_time_to_anaphase",
                    ["min_to_anaphase", "plate_dist_um", "pole_axis_frac", "batch"],
                    [[round(p[0], 3), round(p[1], 3), (None if np.isnan(p[2]) else round(p[2], 3)), p[3]] for p in pts],
                    out, SCRIPT, "Permanent-polar KT position vs time to anaphase (Q7)")
    print(f"Q7: {out}  cells={len(set(cells))}")


# ================================================================= Q3b
def q3b():
    groups = defaultdict(list); rowsout = []
    for b in usable:
        beh = behavior(b)
        if beh not in ("congressed", "noncongression", "at_plate"): continue
        tr = sister(b)
        if not tr: continue
        f, t, x, y = tr[0]                       # earliest mark = position when first followed
        poly = plate_at(b, f)
        o = outline_at(b, f)
        if poly is None or len(poly) < 2 or o is None: continue
        # SPINDLE AXIS = normal to the metaphase plate (the RTF's alternative definition)
        c = poly.mean(0); _, _, vt = np.linalg.svd(poly - c); d1 = vt[0]
        n = np.array([-d1[1], d1[0]]); n = n / (np.linalg.norm(n) or 1)
        # normalise by the cell's half-extent along that same normal, so cells of different size compare
        ext = np.abs((o - o.mean(0)) @ n).max() or 1.0
        a = abs(float((np.array([x, y]) - c) @ n)) / ext
        groups[beh].append(a); rowsout.append([beh, round(a, 4), b])
    if sum(len(v) for v in groups.values()) < 6:
        print("Q3b: too few cells"); return
    order = [g for g in ("at_plate", "congressed", "noncongression") if len(groups.get(g, [])) >= 2]
    fig, ax = plt.subplots(figsize=(6.6, 5))
    cols = {"at_plate": "#1b7837", "congressed": "#2166ac", "noncongression": "#b2182b"}
    for i, g in enumerate(order):
        v = np.array(groups[g])
        for bd in ax.violinplot([v], positions=[i], widths=.7, showextrema=False)['bodies']:
            bd.set_facecolor(cols[g]); bd.set_alpha(.25); bd.set_edgecolor(cols[g])
        ax.scatter(np.zeros(len(v)) + i + (np.random.RandomState(0).rand(len(v)) - .5) * .18, v,
                   s=26, color=cols[g], alpha=.8, edgecolor="none")
        ax.hlines(np.median(v), i - .3, i + .3, color=cols[g], lw=2.2)
        ax.text(i, 1.02, f"N={len(v)}", ha="center", fontsize=8, transform=ax.get_xaxis_transform())
    ttl = ""
    if len(order) >= 2:
        a, bb = groups[order[0]], groups[order[-1]]
        if len(a) >= 3 and len(bb) >= 3:
            u, p = stats.mannwhitneyu(a, bb)
            ttl = f"  |  {order[0]} vs {order[-1]}: MW p={p:.3g}"
    ax.set_xticks(range(len(order))); ax.set_xticklabels([o.replace("_", " ") for o in order])
    ax.set_ylabel("Position along the PLATE-NORMAL (spindle) axis\n0 = on the plate, 1 = cell edge")
    ax.set_title("Position on the spindle axis defined as PERPENDICULAR TO THE METAPHASE PLATE, by outcome\n"
                 "(companion to G3_ablation_location_vs_behavior, which uses the cell-SHAPE axis)" + ttl,
                 loc="left", fontweight="bold", fontsize=9.5)
    plt.tight_layout(); fig.savefig(f"{OUT3}/G3_position_along_plate_normal_vs_behavior.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot("G3_position_along_plate_normal_vs_behavior", ["behavior", "plate_normal_frac", "batch"],
                    rowsout, {g: len(v) for g, v in groups.items()}, SCRIPT,
                    "KT position on the plate-normal spindle axis vs behaviour (Q3, uncovered half)")
    print(f"Q3b: {[(g, len(v)) for g, v in groups.items()]}")


if __name__ == "__main__":
    print(f"usable cells with a KT track: {len(usable)}")
    validate_congression()
    q4(); q5(); q6(); q7(); q3b()
