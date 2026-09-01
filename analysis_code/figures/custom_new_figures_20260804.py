#!/usr/bin/env python3
"""NEW figures created in response to the 2026-08-04 feedback.

Per her 2026-08-04 routing rule, figures that do NOT already exist on META_FIGURES_*.ai or supplemental.ai
go into a dedicated new-figures deck so she can decide afterwards where each belongs. This script builds
those figures; placement into NEW_FIGURES_20260804.ai happens in the Illustrator pass.

  item 20  Among chromosomes that DO congress, does chromosome size predict how long / what fraction of
           metaphase that chromosome takes to congress?

DATA NOTE (corrected 2026-08-04 after she pushed back twice, and she was right both times):
  * every chromosome with behavior=="congressed" HAS a congression_time_s — 66/66, none missing. An earlier
    count of "58 missing" came from matching the substring "congress", which also matches "noncongression".
  * no batch is blocked by a missing metaphase duration: where the master's `Meta Duration (s)` cell is
    blank it is recoverable as `Anaphase Onset - Metaphase Start`, the same fallback the other builders use.
    Reading the column without that fallback cut N from 57 to 12 and hid a real, significant effect.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib
import canon_labels

lib.apply_style()
ROOT = "/Volumes/4 MB"
OUT = f"{ROOT}/ablation_figures_20260625/new_figures_20260804"
os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
CHROMO = f"{ROOT}/annotations/CHROMOSOME_MASTER.csv"

master, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

def meta_dur_min(b):
    """Metaphase duration in minutes, with the standard fallback where the stored column is blank."""
    d = lib.parse_time(gv(b, "Meta Duration (s)"))
    if d is None or d <= 0:
        m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        d = (a0 - m0) if (m0 is not None and a0 is not None) else None
    return d / 60.0 if d and d > 0 else None


# ── ITEM 20 ───────────────────────────────────────────────────────────────────────────────────────
rows = [r for r in csv.DictReader(open(CHROMO)) if r["behavior"].strip().lower() == "congressed"]
SISPAL = {"1": lib.PALETTE["1-Sister"], "2": lib.PALETTE["2-Sister"], "3": lib.PALETTE["3-Sister"]}
X, Tmin, Frac, G, B = [], [], [], [], []
skip = collections.Counter()
for r in rows:
    b = r["batch"].strip()
    if lib.is_mad1(b) or lib.plot_excluded(b): skip["cohort-excluded"] += 1; continue
    try:
        L = float(r["length_um"]); ct = float(r["congression_time_s"])
    except Exception:
        skip["unparseable length/time"] += 1; continue
    ms = lib.parse_time(gv(b, "Metaphase Start (s)")); dur = meta_dur_min(b)
    if ms is None or dur is None: skip["no metaphase start/duration"] += 1; continue
    t = (ct - ms) / 60.0
    if t < 0: skip["congressed before metaphase start"] += 1; continue
    fr = t / dur
    if fr > 1.05: skip["congressed after anaphase"] += 1; continue
    X.append(L); Tmin.append(t); Frac.append(min(fr, 1.0))
    G.append((r.get("n_sisterless", "") or "").strip()); B.append(b)
print(f"item 20: congressed rows={len(rows)}  usable={len(X)}  skips={dict(skip)}")

if len(X) >= 6:
    X = np.array(X); Tmin = np.array(Tmin); Frac = np.array(Frac); G = np.array(G)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    stats_out = {}
    for ax, Y, ylab, key in ((axes[0], Tmin, "Time to congress (min after metaphase onset)", "time_min"),
                             (axes[1], Frac, "Fraction of metaphase elapsed at congression\n(0 = onset, 1 = anaphase)", "fraction")):
        for g in ("1", "2", "3"):
            m = G == g
            if m.any():
                ax.scatter(X[m], Y[m], s=46, color=SISPAL.get(g, "#888"), alpha=.85,
                           edgecolor="white", lw=.5, label=f"{lib.lbl(g+'-Sister')} (n={int(m.sum())})")
        rho, p = st.spearmanr(X, Y)
        stats_out[key] = {"spearman_rho": round(float(rho), 4), "p": float(p), "N": int(len(X))}
        sl, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
        ax.plot(xr, sl * xr + c0, "--", color="#b30000", lw=1.8)
        ax.set_xlabel("Sisterless chromosome length (µm)"); ax.set_ylabel(ylab)
        ax.set_title(f"Spearman rho={rho:+.2f}, p={p:.3g}, N={len(X)}", loc="left", fontweight="bold", fontsize=10)
        ax.legend(fontsize=7.5)
    axes[1].set_ylim(-0.03, 1.03)
    fig.suptitle("ITEM 20 — among chromosomes that DO congress, bigger chromosomes take longer to reach the plate\n"
                 "One point per congressed sisterless chromosome (CHROMOSOME_MASTER). Left: absolute time. "
                 "Right: as a fraction of that cell's own metaphase, so 1- and 3-sisterless cells are comparable.",
                 x=.01, ha="left", fontweight="bold", fontsize=9)
    plt.tight_layout()
    fig.savefig(f"{OUT}/G3_length_vs_congression_time.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    lib.record_plot("G3_length_vs_congression_time",
                    ["batch", "n_sisterless", "length_um", "t_to_congress_min", "frac_meta_to_ana"],
                    [[b, g, round(float(x), 4), round(float(t), 3), round(float(f), 4)]
                     for b, g, x, t, f in zip(B, G, X, Tmin, Frac)],
                    {"unit": "one congressed sisterless chromosome",
                     "stats": stats_out,
                     "x_label": "Sisterless chromosome length (um)",
                     "y_label": "Time to congress (min) / fraction of metaphase",
                     "note": "all 66 congressed chromosomes carry a congression_time_s; metaphase duration "
                             "recovered as Anaphase Onset - Metaphase Start where the stored column is blank"},
                    SCRIPT, "Chromosome length vs time and fraction of metaphase taken to congress",
                    source=[CHROMO, f"{ROOT}/ABLATION_MASTER.csv"])
    for k, v in stats_out.items():
        print(f"  {k}: rho={v['spearman_rho']:+.3f} p={v['p']:.3g} N={v['N']}")
print("done new figures 20260804")


# ── ITEM 28 (user 2026-08-04) ─────────────────────────────────────────────────────────────────────
# "Cell midpoint movement during metaphase anaphase vs # sisterless kts: use this same plot format on
#  metaphase plate rotation. Use magnitude for rotation (as opposed to positive/negative)."
# The existing metaplate_rotation_by_sisterless figure is a TIME-SERIES (one line per cell), not the
# centroid figure's format. This rebuilds it in the centroid format: one point per CELL, boxplot per
# sisterless group, jitter, linear fit + Spearman — two panels matching the centroid pair
#   (rate  <- centroid speed;  total <- net displacement)
# but using MAGNITUDE: rotation is summed as |step| so a plate that turns +20 then -20 scores 40 deg of
# turning, not 0. Source = the rotation builder's own recorded per-frame CSV, so the two figures cannot drift.
# ── ITEM 28 (superseded by NF1 below; kept because its output id is still recorded) ──
def _item28_rotation_magnitude():
    import csv as _csv, collections as _c
    from scipy import stats as _st
    src = "/Volumes/4 MB/ablation_plots/data/metaplate_rotation_by_sisterless.csv"
    if not os.path.exists(src):
        print("ITEM 28 skipped — run metaplate_rotation_by_sisterless.py first"); return
    per = _c.defaultdict(list); sis = {}
    for r in _csv.DictReader(open(src)):
        b = r["batch"].strip()
        try:
            t = float(r["t_min"]); d = float(r["degrees_turned_net"])
        except ValueError:
            continue
        per[b].append((t, d)); sis[b] = int(r["sisterless"]) if r["sisterless"].strip().isdigit() else None
    recs = []
    for b, pts in per.items():
        if sis.get(b) is None or len(pts) < 3: continue
        pts.sort()
        t = np.array([p[0] for p in pts]); d = np.array([p[1] for p in pts])
        total_mag = float(np.abs(np.diff(d)).sum())      # MAGNITUDE: sum of |step|, not net
        dur = float(t[-1] - t[0])
        if dur <= 0: continue
        recs.append((sis[b], total_mag / dur, total_mag, b))
    if len(recs) < 4:
        print(f"ITEM 28 skipped — only {len(recs)} cells"); return
    S = np.array([r[0] for r in recs]); RATE = np.array([r[1] for r in recs]); TOT = np.array([r[2] for r in recs])
    rho, p = _st.spearmanr(S, RATE); rho2, p2 = _st.spearmanr(S, TOT)
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    for ax, (vals, lab, rr, pp) in zip(axs, [
            (RATE, "Plate rotation RATE, metaphase to anaphase (deg turned /min)", rho, p),
            (TOT,  "TOTAL plate rotation, metaphase to anaphase (deg turned)",     rho2, p2)]):
        groups = sorted(set(S.astype(int))); data_g = [vals[S == g] for g in groups]
        bp = ax.boxplot(data_g, positions=groups, widths=.6, showfliers=False, patch_artist=True)
        for pa in bp["boxes"]: pa.set_facecolor("#4a90d9"); pa.set_alpha(.35)
        for g in groups:
            v = vals[S == g]; xj = np.random.default_rng(g).normal(g, 0.07, len(v))
            ax.scatter(xj, v, s=26, color="#1f5c9e", alpha=.8, edgecolor="white", lw=.3, zorder=3)
        if len(S) >= 2:
            a_, b_ = np.polyfit(S, vals, 1); xx = np.linspace(min(groups), max(groups), 20)
            ax.plot(xx, a_ * xx + b_, "k--", lw=2, zorder=4)
        ax.set_xlabel("# Sisterless kinetochores"); ax.set_ylabel(lab)
        ax.set_title(f"{lab.split('(')[0].strip()}\nSpearman rho={rr:.2f}, p={pp:.2g}, N={len(vals)}", fontsize=10)
    fig.suptitle("ITEM 28 — metaphase-plate ROTATION MAGNITUDE during METAPHASE to ANAPHASE vs # sisterless KTs\n"
                 "same format as the cell-midpoint figure; rotation summed as |step| so opposing turns add "
                 "rather than cancel", fontsize=10.5, y=1.03)
    fig.tight_layout()
    fig.savefig(f"{OUT}/metaplate_rotation_magnitude_vs_sisterless.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    lib.record_plot("metaplate_rotation_magnitude_vs_sisterless",
                    ["batch", "n_sisterless", "rotation_rate_deg_per_min", "total_rotation_deg"],
                    [[b, s, round(rt, 3), round(tt, 3)] for s, rt, tt, b in recs],
                    {"item28": "centroid-figure format applied to plate rotation; MAGNITUDE (sum of |step|)",
                     "window": "Metaphase Start -> Anaphase Onset",
                     "x_label": "# Sisterless kinetochores",
                     "y_label": "Plate rotation magnitude (deg turned; rate and total)"},
                    SCRIPT, "Metaphase-plate rotation magnitude vs # sisterless KTs",
                    source=[src, f"{ROOT}/ABLATION_MASTER.csv"])
    print(f"ITEM 28: N={len(recs)} cells; rate rho={rho:.2f} p={p:.2g}; total rho={rho2:.2f} p={p2:.2g}")
    for g in sorted(set(S.astype(int))):
        m = S == g
        print(f"   {g}-sis N={int(m.sum())}: total median={np.median(TOT[m]):.1f} deg, "
              f"rate median={np.median(RATE[m]):.2f} deg/min")



# ── NF1 (user 2026-08-04, feedback on the new-figures deck) ───────────────────────────────────────
# "remove trendlines. Remove 0 group. There should definitely be more than the shown # of groups for both
#  1 and 3 sisterless kinetochores."
# Cause of the missing cells: the previous version read ablation_plots/data/metaplate_rotation_by_sisterless.csv
# — a PRESERVED data file holding only 12 batches — instead of the annotations. 60 cells in the
# 1/3-sisterless cohort actually have drawn metaphase plates. Rotation is now recomputed from
# annotations/meta_plates.csv directly, so the figure is limited by the annotation, not by a frozen CSV.
# Rotation is MAGNITUDE: per-frame |change in plate angle| summed, with +/-90 deg unwrapping because the
# plate axis is undirected. Trendlines removed; the 0/unmodified group is dropped.
def _nf1_rotation_from_source():
    import csv as _csv, json as _json, collections as _c
    from scipy import stats as _st
    _csv.field_size_limit(10**9)
    PL = _c.defaultdict(dict); PT = _c.defaultdict(dict)
    for r in _csv.DictReader(open(f"{ROOT}/annotations/meta_plates.csv")):
        b = (r.get("batch") or "").strip()
        try:
            P = np.array(_json.loads(r["points"]), float); f = int(float(r["frame"])); t = float(r["t_sec"])
        except Exception: continue
        if len(P) >= 2: PL[b][f] = P; PT[b][f] = t
    recs = []
    for b in sorted(PL):
        if lib.plot_excluded(b) or lib.is_mad1(b): continue
        g = gv(b, "# Sisterless KTs")
        if g not in ("1", "3"): continue                      # NF1: 0/unmodified group removed
        ms = lib.parse_time(gv(b, "Metaphase Start (s)")); ao = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        if ms is None or ao is None or ao <= ms: continue
        fr = sorted(f for f in PL[b] if ms <= PT[b][f] <= ao)
        if len(fr) < 2: continue
        ang = []
        for f in fr:
            P = PL[b][f] - PL[b][f].mean(0)
            _u, _s2, vt = np.linalg.svd(P, full_matrices=False)
            ang.append((PT[b][f], np.degrees(np.arctan2(vt[0][1], vt[0][0])) % 180.0))
        tot = 0.0
        for (t0, a0), (t1, a1) in zip(ang[:-1], ang[1:]):
            d = (a1 - a0 + 90) % 180 - 90                     # undirected axis -> unwrap to +/-90
            tot += abs(d)
        dur = (ang[-1][0] - ang[0][0]) / 60.0
        if dur <= 0: continue
        recs.append((g, tot / dur, tot, b, len(fr)))
    if len(recs) < 4:
        print(f"NF1: only {len(recs)} cells — not built"); return
    G = np.array([r[0] for r in recs]); RATE = np.array([r[1] for r in recs]); TOT = np.array([r[2] for r in recs])
    COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}
    fig, axs = plt.subplots(1, 2, figsize=(11.6, 5.2))
    txt = []
    for ax, (vals, lab) in zip(axs, [(RATE, "Plate rotation RATE, metaphase to anaphase (deg turned /min)"),
                                     (TOT,  "TOTAL plate rotation, metaphase to anaphase (deg turned)")]):
        for i, g in enumerate(("1", "3")):
            v = vals[G == g]
            if not len(v): continue
            ax.boxplot([v], positions=[i], widths=.55, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor=COL[g], alpha=.30, color=COL[g]),
                       medianprops=dict(color=COL[g], lw=2.2))
            jit = (np.random.RandomState(i).rand(len(v)) - .5) * .22
            ax.scatter(np.full(len(v), i) + jit, v, s=34, color=COL[g], alpha=.85, edgecolor="white", lw=.4)
            ax.text(i, max(v) * 1.02, f"med {np.median(v):.1f}\nn={len(v)}", ha="center", va="bottom", fontsize=8)
        a_, b_ = vals[G == "1"], vals[G == "3"]
        pv = _st.mannwhitneyu(a_, b_, alternative="two-sided")[1] if (len(a_) >= 3 and len(b_) >= 3) else None
        ax.set_xticks([0, 1]); ax.set_xticklabels([f"1-sisterless\n(n={int((G=='1').sum())})",
                                                   f"3-sisterless\n(n={int((G=='3').sum())})"])
        # 2026-08-04: two fixes. (a) headroom, so the "med / n=" labels drawn just above each group's max
        # stop printing through the panel title. (b) the y label is long enough to be clipped at the figure
        # edge, so wrap it at the unit parenthesis.
        if len(vals):
            _lo, _hi = float(np.min(vals)), float(np.max(vals))
            _rng = (_hi - _lo) or (abs(_hi) or 1.0)
            ax.set_ylim(_lo - _rng * 0.08, _hi + _rng * 0.28)
        ax.set_ylabel(lab.replace(" (", "\n(", 1), fontsize=9)
        ax.set_title((lab.split("(")[0].strip()) + (f"   Mann-Whitney p={pv:.3g}" if pv else ""),
                     loc="left", fontweight="bold", fontsize=9.5)
        if pv: txt.append(f"{lab.split('(')[0].strip()}: p={pv:.3g}")
    fig.suptitle("NF1 — metaphase-plate ROTATION MAGNITUDE during metaphase to anaphase, 1 vs 3 sisterless\n"
                 f"Recomputed from annotations/meta_plates.csv ({len(recs)} cells) — the earlier version read a "
                 "preserved 12-batch data CSV. No trendlines; 0/unmodified group removed.\n"
                 "Rotation summed as |step| with ±90° unwrapping, so opposing turns add rather than cancel.",
                 x=.01, ha="left", fontweight="bold", fontsize=8.5)
    plt.tight_layout()
    fig.savefig(f"{OUT}/metaplate_rotation_magnitude_vs_sisterless.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    lib.record_plot("metaplate_rotation_magnitude_vs_sisterless",
                    ["batch", "n_sisterless", "rotation_rate_deg_per_min", "total_rotation_deg", "n_plate_frames"],
                    [[b, g, round(rt, 3), round(tt, 3), nf] for g, rt, tt, b, nf in recs],
                    {"nf1": "recomputed from meta_plates.csv; no trendlines; 0-group removed",
                     "window": "Metaphase Start -> Anaphase Onset",
                     "x_label": "# Sisterless kinetochores",
                     "y_label": "Plate rotation magnitude (deg turned; rate and total)"},
                    SCRIPT, "Metaphase-plate rotation magnitude, 1 vs 3 sisterless",
                    source=[f"{ROOT}/annotations/meta_plates.csv", f"{ROOT}/ABLATION_MASTER.csv"])
    import collections as _c2
    print(f"NF1: {len(recs)} cells (was 12) — by group {dict(_c2.Counter(G))}; " + "; ".join(txt))

_item28_rotation_magnitude()
_nf1_rotation_from_source()



# ── ITEM 16 (user 2026-08-04) ─────────────────────────────────────────────────────────────────────
# "Is there a spindle dimension measurement plot - i.e. pole-pole measurement over metaphase for single and
#  for triple?"  There is not, and it cannot be measured directly: annotations/poles.csv is HEADER-ONLY (zero
#  rows) and kt_points carries no pole/spindle label.
# Her proposal: "estimate pole-pole distance using the axis perpendicular to the metaphase plate that should
#  approx run through the long axis of the cell outline."  Checked before building — the plate NORMAL and the
#  cell outline's long axis agree to a median of 16.8 deg (IQR 7-32; <30 deg in 72% of frames), so the two
#  definitions do track each other.
# WHAT THIS MEASURES: the CELL's extent along the plate-normal (spindle) axis. The spindle poles sit inside
# the cell, so this is an UPPER BOUND on pole-pole separation and a proxy for spindle length — not the poles
# themselves. Labelled that way on the figure so it is never read as a direct measurement.
def _item16_spindle_axis_extent():
    import csv as _csv, json as _json, collections as _c
    from scipy import stats as _st
    _csv.field_size_limit(10**9)
    def load(fn):
        d = _c.defaultdict(dict); t = _c.defaultdict(dict)
        for r in _csv.DictReader(open(f"{ROOT}/annotations/{fn}")):
            b = (r.get("batch") or "").strip()
            try:
                p = np.array(_json.loads(r["points"]), float); f = int(float(r["frame"]))
            except Exception:
                continue
            if len(p) >= 2:
                d[b][f] = p
                try: t[b][f] = float(r.get("t_sec") or "nan")
                except Exception: pass
        return d, t
    PL, PT = load("meta_plates.csv"); OU, OT = load("cell_outlines.csv")
    def axis(p):
        c = p - p.mean(0); _u, _s, vt = np.linalg.svd(c, full_matrices=False); return vt[0]
    def px(b):
        try:
            v = float(gv(b, "Pixel Size (um)")); return v if v > 0 else 0.062
        except Exception: return 0.062
    series = {}; angs = []
    for b in sorted(set(PL) & set(OU)):
        if lib.plot_excluded(b) or lib.is_mad1(b): continue
        ms = lib.parse_time(gv(b, "Metaphase Start (s)")); ao = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        if ms is None or ao is None or ao <= ms: continue
        # COVERAGE FIX (2026-08-04, her: "nearly all cells should have outlines in the metaphase window").
        # Requiring the plate polyline and the cell outline on the SAME frame was the binding constraint, not
        # outline availability: of 62 cohort cells with outlines, 24 shared <3 frames with a plate and 3 never
        # shared one at all — 27 cells lost to frame matching alone. The plate's ORIENTATION changes slowly,
        # so the axis is taken from the NEAREST-IN-TIME plate polyline instead (the same nearest-plate rule
        # used elsewhere in this codebase), capped at a 300 s gap so a stale plate can never define the axis.
        MAX_PLATE_GAP_S = 300.0
        _pf = sorted(PL[b])
        _pt = {f: PT[b].get(f) for f in _pf}
        _pf = [f for f in _pf if _pt.get(f) is not None and np.isfinite(_pt[f])]
        pts = []
        for f in sorted(OU[b]):
            ts = OT[b].get(f, PT[b].get(f))
            if ts is None or not np.isfinite(ts): continue
            if not (ms <= ts <= ao): continue                 # metaphase window only
            if f in PL[b]:
                _pfr = f
            elif _pf:
                _pfr = min(_pf, key=lambda q: abs(_pt[q] - ts))
                if abs(_pt[_pfr] - ts) > MAX_PLATE_GAP_S: continue
            else:
                continue
            pa = axis(PL[b][_pfr]); n = np.array([-pa[1], pa[0]])   # plate normal = spindle axis
            o = OU[b][f]
            proj = o @ n
            ext = float(proj.max() - proj.min()) * px(b)         # cell extent along the spindle axis (um)
            angs.append(np.degrees(np.arccos(abs(float(np.dot(n, axis(o)))))))
            pts.append(((ts - ms) / (ao - ms), ext))             # x = fraction of metaphase elapsed
        _ot = {f: OT[b].get(f) for f in OU[b]}
        _ot = {f: v for f, v in _ot.items() if v is not None and np.isfinite(v)}
        # PLATE-DRIVEN FRAMES (her 2026-08-04: "if plates exist on non-outline frames, use the temporally
        # nearest outline (can be either before or after) so long as it's gated by the outline at the start of
        # metaphase and the outline at the start of anaphase"). The loop above walks OUTLINE frames and pulls
        # the nearest plate; this walks the PLATE frames inside the metaphase window and pulls the nearest
        # outline in either direction, with the outline required to lie within the metaphase-start ->
        # anaphase-onset outline bracket so a pre-metaphase or post-anaphase cell shape can never be used.
        _ob = sorted(_ot, key=lambda q: _ot[q]) if _ot else []
        if _ob:
            _f_ms = min(_ob, key=lambda q: abs(_ot[q] - ms))
            _f_ao = min(_ob, key=lambda q: abs(_ot[q] - ao))
            _lo, _hi = sorted((_ot[_f_ms], _ot[_f_ao]))
            for _pfr in _pf:
                _pts_t = _pt[_pfr]
                if not (ms <= _pts_t <= ao): continue
                if _pfr in OU[b]: continue                 # already covered by the outline-driven loop
                _cand = [q for q in _ob if _lo - 1e-6 <= _ot[q] <= _hi + 1e-6]
                if not _cand: continue
                _f = min(_cand, key=lambda q: abs(_ot[q] - _pts_t))
                _fr = (_pts_t - ms) / (ao - ms)
                if any(abs(x - _fr) < 1e-4 for x, _ in pts): continue
                _pa = axis(PL[b][_pfr]); _n = np.array([-_pa[1], _pa[0]])
                _o = OU[b][_f]; _pr = _o @ _n
                pts.append((_fr, float(_pr.max() - _pr.min()) * px(b)))

        # BOUNDARY OUTLINES (her 2026-08-04: "if no outlines in metaphase itself there should be one at the
        # start of metaphase and at the start of anaphase - use those"). Outlines are typically drawn AT the
        # mitotic events rather than sprinkled through metaphase, so a strict ms<=t<=ao test threw those cells
        # away entirely. Take the outline nearest metaphase start (pinned to fraction 0) and nearest anaphase
        # onset (pinned to fraction 1), within a 300 s tolerance, and add them if not already present.
        BOUNDARY_TOL_S = 300.0
        for _target, _frac in ((ms, 0.0), (ao, 1.0)):
            if not _ot: break
            if any(abs(x - _frac) < 1e-6 for x, _ in pts): continue
            _f = min(_ot, key=lambda q: abs(_ot[q] - _target))
            if abs(_ot[_f] - _target) > BOUNDARY_TOL_S: continue
            if f in PL[b] if False else (_f in PL[b]):
                _pfr = _f
            elif _pf:
                _pfr = min(_pf, key=lambda q: abs(_pt[q] - _ot[_f]))
                if abs(_pt[_pfr] - _ot[_f]) > MAX_PLATE_GAP_S: continue
            else:
                continue
            _pa = axis(PL[b][_pfr]); _n = np.array([-_pa[1], _pa[0]])
            _o = OU[b][_f]; _pr = _o @ _n
            pts.append((_frac, float(_pr.max() - _pr.min()) * px(b)))
        # Outlines exist for nearly every cell, but few sit strictly inside metaphase, so the per-cell
        # threshold is 1: the trace panel still needs >=3 points to draw a line; the single-vs-triple
        # comparison only needs one. Both Ns are stated on the figure.
        if len(pts) >= 1: series[b] = sorted(pts)
    if len(series) < 6:
        print(f"ITEM 16: only {len(series)} cells with >=3 in-metaphase frames — not built"); return
    print(f"ITEM 16 coverage: {len(series)} cells with >=3 in-metaphase frames "
          f"(nearest-plate matching, {MAX_PLATE_GAP_S:.0f}s cap)")
    grp = {b: gv(b, "# Sisterless KTs") for b in series}
    COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}
    # Her spec (2026-08-04): ONE plot — the pole-pole approximation for the 1- and 3-sisterless groups over
    # time, each drawn from METAPHASE ONSET to ANAPHASE ONSET only. Nothing before or beyond that window.
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    rows = []; ncell = {"1": 0, "3": 0}
    for b, pts in series.items():
        g = grp.get(b)
        if g not in COL: continue
        pts = [(min(max(x, 0.0), 1.0), y) for x, y in pts]     # hard-bound to the metaphase window
        ncell[g] += 1
        if len(pts) >= 3:
            ax.plot([q[0] for q in pts], [q[1] for q in pts], "-", lw=0.8, alpha=.28, color=COL[g], zorder=1)
        for x, y in pts: rows.append([b, g, round(x, 4), round(y, 3)])
    stats_txt = []
    for g in ("1", "3"):
        allp = [(x, y) for b, pts in series.items() if grp.get(b) == g
                for x, y in [(min(max(a, 0.0), 1.0), c) for a, c in pts]]
        if len(allp) < 6: continue
        X = np.array([q[0] for q in allp]); Y = np.array([q[1] for q in allp])
        bins = np.linspace(0, 1, 9); idx = np.digitize(X, bins)
        bx, bm, blo, bhi = [], [], [], []
        for i2 in range(1, len(bins)):
            sel = Y[idx == i2]
            if len(sel) >= 3:
                bx.append((bins[i2-1] + bins[i2]) / 2); bm.append(np.median(sel))
                blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
        if bx:
            ax.fill_between(bx, blo, bhi, color=COL[g], alpha=.16, zorder=2)
            ax.plot(bx, bm, "-o", color=COL[g], lw=2.8, ms=5.5, zorder=4,
                    label=f"{lib.lbl(g+'-Sister')} — {ncell[g]} cells, {len(allp)} points")
        _r, _p = st.spearmanr(X, Y)
        stats_txt.append(f"{g}-sis: {np.median(Y):.1f} µm median, trend over metaphase rho={_r:+.2f} p={_p:.2g}")
    med = {g: [float(np.median([y for _x, y in pts])) for b, pts in series.items() if grp.get(b) == g]
           for g in ("1", "3")}
    ptxt = ""
    if len(med["1"]) >= 3 and len(med["3"]) >= 3:
        _u, _pv = st.mannwhitneyu(med["1"], med["3"], alternative="two-sided")
        ptxt = (f"per-cell medians {np.median(med['1']):.1f} vs {np.median(med['3']):.1f} µm, "
                f"Mann-Whitney p={_pv:.3g}")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction of metaphase elapsed")
    ax.set_ylabel("Pole-to-pole approximation (µm)")
    ax.set_title("Pole-to-pole approximation over metaphase — 1- vs 3-sisterless\n" + ptxt,
                 loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=8.5, title="thick line = group median, band = IQR")
    ax.text(0.0, -0.155,
            "APPROXIMATION, not a direct measurement: annotations/poles.csv is empty, so the poles are never "
            "annotated. The spindle axis is taken as the\nNORMAL to the drawn metaphase plate (which runs near "
            f"the cell's long axis, median {np.median(angs):.1f}° here) and the value is the cell outline's "
            "extent along that axis —\nan UPPER BOUND on pole separation. Plate and outline are matched "
            "nearest-in-time (300 s cap), gated by the metaphase-onset and anaphase-onset outlines.\n"
            + "   |   ".join(stats_txt),
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.55)
    plt.tight_layout()
    fig.savefig(f"{OUT}/G6_polepole_approx_over_metaphase.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    lib.record_plot("G6_polepole_approx_over_metaphase",
                    ["batch", "n_sisterless", "frac_meta_to_ana", "polepole_approx_um"], rows,
                    {"item16": "pole-pole APPROXIMATION: cell outline extent along the metaphase-plate normal",
                     "window": "metaphase onset -> anaphase onset only",
                     "caveat": "upper bound; poles.csv is empty so poles are not annotated",
                     "plate_normal_vs_cell_long_axis_median_deg": round(float(np.median(angs)), 1),
                     "per_group": {g: {"cells": ncell[g]} for g in ncell},
                     "x_label": "Fraction of metaphase elapsed",
                     "y_label": "Pole-to-pole approximation (um)"},
                    SCRIPT, "Pole-to-pole approximation over metaphase, 1- vs 3-sisterless",
                    source=[f"{ROOT}/annotations/meta_plates.csv", f"{ROOT}/annotations/cell_outlines.csv"])
    print(f"ITEM 16: cells 1-sis={ncell['1']} 3-sis={ncell['3']}, {len(rows)} points; {ptxt}")
    for t in stats_txt: print("   " + t)


_item16_spindle_axis_extent()


# ── ITEM 29 (user 2026-08-04) ─────────────────────────────────────────────────────────────────────
# "Create a plot that looks at, for single and triple batches, if major changes in centroid movement or plate
#  rotation or cell roundness or cross-sectional area correspond with events like congression to the plate."
# Built as an EVENT-TRIGGERED AVERAGE: for every congression event, each cell-shape/motion metric is measured
# as its per-minute rate of change, aligned so t=0 is that congression, and averaged across events. If a
# congression coincides with a real change, the |rate| rises at t=0 above the cell's own baseline.
# Each metric is tested by comparing |rate| inside a +/-2 min window around congression against all other
# in-metaphase timepoints for the same cells (Mann-Whitney), so "major change" is measured, not eyeballed.
def _item29_shape_events_vs_congression():
    import csv as _csv, json as _json, collections as _c
    from scipy import stats as _st
    _csv.field_size_limit(10**9)
    def poly_area(P):
        x, y = P[:, 0], P[:, 1]
        return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)
    def poly_perim(P):
        d = np.diff(np.vstack([P, P[:1]]), axis=0)
        return float(np.hypot(d[:, 0], d[:, 1]).sum())
    OUTL = _c.defaultdict(dict); OT = _c.defaultdict(dict)
    for r in _csv.DictReader(open(f"{ROOT}/annotations/cell_outlines.csv")):
        b = (r.get("batch") or "").strip()
        try:
            P = np.array(_json.loads(r["points"]), float); f = int(float(r["frame"])); t = float(r["t_sec"])
        except Exception: continue
        if len(P) >= 6: OUTL[b][f] = P; OT[b][f] = t
    PLT = _c.defaultdict(dict); PT = _c.defaultdict(dict)
    for r in _csv.DictReader(open(f"{ROOT}/annotations/meta_plates.csv")):
        b = (r.get("batch") or "").strip()
        try:
            P = np.array(_json.loads(r["points"]), float); f = int(float(r["frame"])); t = float(r["t_sec"])
        except Exception: continue
        if len(P) >= 2: PLT[b][f] = P; PT[b][f] = t
    CONG = _c.defaultdict(list)
    for r in _csv.DictReader(open(CHROMO)):
        if (r.get("behavior") or "").strip().lower() != "congressed": continue
        b = r["batch"].strip()
        try: CONG[b].append(float(r["congression_time_s"]))
        except Exception: pass

    METRICS = ["centroid speed (µm/min)", "plate rotation (deg/min)",
               "cell roundness change (/min)", "cross-sectional area change (µm²/min)"]
    prof = {m: _c.defaultdict(list) for m in METRICS}      # group -> list of (dt_min, |rate|)
    base = {m: _c.defaultdict(list) for m in METRICS}      # group -> baseline |rate| away from events
    near = {m: _c.defaultdict(list) for m in METRICS}      # group -> |rate| within +/-2 min of an event
    WIN = 2.0
    ncell = _c.Counter()
    for b in sorted(set(OUTL) & set(CONG)):
        if lib.plot_excluded(b) or lib.is_mad1(b): continue
        g = gv(b, "# Sisterless KTs")
        if g not in ("1", "3"): continue
        ms = lib.parse_time(gv(b, "Metaphase Start (s)")); ao = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        if ms is None or ao is None or ao <= ms: continue
        pxs = 0.062
        try:
            v = float(gv(b, "Pixel Size (um)")); pxs = v if v > 0 else 0.062
        except Exception: pass
        # NF2 (user 2026-08-04): "only 1 triple plotted and one point from single on most plots ... Should be
        # able to be plotted for each cell with congressing chromosome." The >=3-strictly-inside-metaphase rule
        # was the gate, exactly as in NF1/item16. Outlines are drawn AT the mitotic events far more often than
        # through metaphase, so also admit the outlines nearest metaphase onset and anaphase onset (within
        # 300 s) and drop the floor to 2 frames — 2 is the minimum that yields one rate of change.
        fr = sorted(f for f in OUTL[b] if ms <= OT[b][f] <= ao)
        _all = sorted(OUTL[b], key=lambda q: OT[b][q])
        for _tgt in (ms, ao):
            if not _all: break
            _n = min(_all, key=lambda q: abs(OT[b][q] - _tgt))
            if abs(OT[b][_n] - _tgt) <= 300.0 and _n not in fr: fr.append(_n)
        fr = sorted(set(fr), key=lambda q: OT[b][q])
        if len(fr) < 2: continue
        cen = {f: OUTL[b][f].mean(0) for f in fr}
        rnd = {f: (4 * np.pi * poly_area(OUTL[b][f]) / max(poly_perim(OUTL[b][f]) ** 2, 1e-9)) for f in fr}
        ar = {f: poly_area(OUTL[b][f]) * pxs * pxs for f in fr}
        ang = {}
        for f in sorted(PLT[b]):
            if not (ms <= PT[b][f] <= ao): continue
            P = PLT[b][f] - PLT[b][f].mean(0)
            _u, _s, vt = np.linalg.svd(P, full_matrices=False)
            ang[f] = np.degrees(np.arctan2(vt[0][1], vt[0][0])) % 180.0
        events = [e for e in CONG[b] if ms <= e <= ao]
        if not events: continue
        ncell[g] += 1
        def emit(seq, tmap, label, scale=1.0, angular=False):
            ks = sorted(seq)
            for a_, b_ in zip(ks[:-1], ks[1:]):
                dt = (tmap[b_] - tmap[a_]) / 60.0
                if dt <= 0: continue
                d = seq[b_] - seq[a_]
                if angular:
                    d = (d + 90) % 180 - 90
                    rate = abs(float(d)) / dt
                elif np.ndim(d) > 0:
                    rate = float(np.hypot(*d)) * scale / dt
                else:
                    rate = abs(float(d)) * scale / dt
                tmid = (tmap[a_] + tmap[b_]) / 2.0
                dts = [(tmid - e) / 60.0 for e in events]
                nearest = min(dts, key=abs)
                prof[label][g].append((nearest, rate))
                (near if abs(nearest) <= WIN else base)[label][g].append(rate)
        emit(cen, OT[b], METRICS[0], scale=pxs)
        if len(ang) >= 2: emit(ang, PT[b], METRICS[1], angular=True)
        emit(rnd, OT[b], METRICS[2])
        emit(ar,  OT[b], METRICS[3])

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.6))
    COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}
    lines = []
    for ax, m in zip(axes.flat, METRICS):
        for g in ("1", "3"):
            pts = prof[m][g]
            if len(pts) < 8: continue
            X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
            k = np.abs(X) <= 10
            X, Y = X[k], Y[k]
            if len(X) < 8: continue
            bins = np.arange(-10, 11, 2.0); idx = np.digitize(X, bins)
            bx, bm = [], []
            for i2 in range(1, len(bins)):
                sel = Y[idx == i2]
                if len(sel) >= 3: bx.append((bins[i2-1]+bins[i2])/2); bm.append(np.median(sel))
            if bx: ax.plot(bx, bm, "-o", color=COL[g], lw=2.2, ms=4,
                           label=f"{lib.lbl(g+'-Sister')} ({ncell[g]} cells)")
            a_, b_ = near[m][g], base[m][g]
            if len(a_) >= 5 and len(b_) >= 5:
                _u, _p = _st.mannwhitneyu(a_, b_, alternative="two-sided")
                lines.append(f"{m.split('(')[0].strip()} · {g}-sis: |rate| near congression "
                             f"{np.median(a_):.3g} vs baseline {np.median(b_):.3g}, p={_p:.3g}")
        ax.axvline(0, ls="--", color="#b30000", lw=1.3)
        ax.set_xlabel("Minutes relative to a congression event")
        ax.set_ylabel(f"|{m}|"); ax.set_title(m, loc="left", fontweight="bold", fontsize=9.5)
        ax.legend(fontsize=7.5)
    fig.suptitle("ITEM 29 — do major changes in cell motion/shape coincide with congression to the plate?\n"
                 "Event-triggered average: each metric's per-minute |rate of change| aligned to t=0 = a "
                 "congression event (red line), metaphase window only, single vs triple.",
                 x=.01, ha="left", fontweight="bold", fontsize=9.5)
    # stats printed as a WRAPPED block under the axes. Joining them into the suptitle made one enormous
    # single line, and bbox_inches="tight" then stretched the canvas to 4846x1185 — a warped figure, which is
    # exactly the fault item 1 is about.
    if lines:
        fig.text(0.01, -0.005, "\n".join(lines), ha="left", va="top", fontsize=7.2,
                 color="#444", linespacing=1.5)
    plt.tight_layout(rect=[0, 0.02, 1, 0.93])
    fig.savefig(f"{OUT}/G4_shape_change_vs_congression_events.png", bbox_inches="tight", dpi=140)
    plt.close(fig)
    rows = [[m, g, round(float(dt), 3), round(float(v), 5)]
            for m in METRICS for g in ("1", "3") for dt, v in prof[m][g]]
    lib.record_plot("G4_shape_change_vs_congression_events",
                    ["metric", "n_sisterless", "min_from_congression", "abs_rate"], rows,
                    {"item29": "event-triggered average of cell motion/shape rates around congression",
                     "window_for_test_min": WIN, "cells": dict(ncell),
                     "x_label": "Minutes relative to a congression event", "y_label": "|rate of change|"},
                    SCRIPT, "Cell motion/shape change around congression events, single vs triple",
                    source=[f"{ROOT}/annotations/cell_outlines.csv", f"{ROOT}/annotations/meta_plates.csv", CHROMO])
    print(f"ITEM 29: cells {dict(ncell)}; {len(rows)} rate samples")
    for l in lines: print("   " + l)
_item29_shape_events_vs_congression()

# ══════════════════════════════════════════════════════════════════════════════════════════════════
#  NF batch 2026-08-04 — NF2..NF8. All figures render to new_figures_20260804/ only; no .ai is touched.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
import csv as _c2, json as _j2, collections as _cc
from scipy import stats as _S
_c2.field_size_limit(10**9)
_DBL = set(lib.double_chromosome_batches())
def _sis(b): return gv(b, "# Sisterless KTs")
def _cohort_ok(b): return (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in _DBL
PAL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}

def _box2(ax, a, b, ylab, title, labs=("1-sisterless", "3-sisterless")):
    """Two-group box+strip with Mann-Whitney. Returns p."""
    p = None
    for i, (v, g) in enumerate(((a, "1"), (b, "3"))):
        if not len(v): continue
        ax.boxplot([v], positions=[i], widths=.55, showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor=PAL[g], alpha=.30, color=PAL[g]),
                   medianprops=dict(color=PAL[g], lw=2.2))
        jit = (np.random.RandomState(i).rand(len(v)) - .5) * .22
        ax.scatter(np.full(len(v), i) + jit, v, s=34, color=PAL[g], alpha=.85, edgecolor="white", lw=.4)
        ax.text(i, max(v) * 1.02, f"med {np.median(v):.3g}\nn={len(v)}", ha="center", va="bottom", fontsize=8)
    if len(a) >= 3 and len(b) >= 3:
        p = float(_S.mannwhitneyu(a, b, alternative="two-sided")[1])
    # 2026-08-04: the "med / n=" labels are drawn just above each group's maximum, and with the axis auto-
    # scaled to the data they ran into the title. Give the axis headroom for them.
    _allv = list(a) + list(b)
    if _allv:
        _lo, _hi = min(_allv), max(_allv)
        _rng = (_hi - _lo) or (abs(_hi) or 1.0)
        ax.set_ylim(_lo - _rng * 0.08, _hi + _rng * 0.30)
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"{labs[0]}\n(n={len(a)})", f"{labs[1]}\n(n={len(b)})"])
    ax.set_ylabel(ylab)
    ax.set_title(title + (f"   Mann-Whitney p={p:.3g}" if p is not None else ""),
                 loc="left", fontweight="bold", fontsize=9.5)
    return p


# ── NF5: pole-time — the fraction axis inverts the trend; show both, absolute time first ──────────
def _nf5_pole_time():
    rows = list(_c2.reader(open(f"{ROOT}/annotations/SISTERLESS_PLATE_JOIN_TIMES.csv")))
    ix = {c: i for i, c in enumerate(rows[0])}
    R = []
    for row in rows[1:]:
        if row[ix['exclude_this_data']].strip(): continue
        b = row[ix['batch']].strip(); n = row[ix['n_sisterless']].strip()
        if n not in ("1", "2", "3") or not _cohort_ok(b): continue
        meta = lib.parse_time(gv(b, "Metaphase Start (s)"))
        if b not in mr: continue
        dur, ok = lib.mitotic_duration_min(mr[b])
        if meta is None or not ok: continue
        for k in (1, 2, 3):
            v = row[ix[f'chromosome_{k}_plate_join']].strip(); s = row[ix[f'chromosome_{k}_plate_join_s']].strip()
            if not v or v.lower() in ("n/a", "anaphase") or v in ("0", "0:00:00"): continue
            try: jt = float(s)
            except Exception: continue
            pole = (jt - meta) / 60.0
            if pole < 0: continue
            fr = pole / dur
            if fr > 1.05: continue
            R.append((b, n, k, pole, dur, min(fr, 1.0)))
    if len(R) < 6: print("NF5: too few points"); return
    DUR = np.array([r[4] for r in R]); ABS = np.array([r[3] for r in R]); FR = np.array([r[5] for r in R])
    G = np.array([r[1] for r in R])
    fig, axs = plt.subplots(1, 2, figsize=(12.4, 5.2))
    out = {}
    for ax, Y, ylab, key in ((axs[0], ABS, "Time at pole before congression (min after metaphase onset)", "absolute"),
                             (axs[1], FR, "Fraction of metaphase elapsed at congression (0=onset, 1=anaphase)", "fraction")):
        for g in ("1", "3"):
            m = G == g
            if m.any():
                ax.scatter(DUR[m], Y[m], s=36, color=PAL[g], alpha=.85, edgecolor="white", lw=.4,
                           label=f"{lib.lbl(g+'-Sister')} (n={int(m.sum())} KTs)")
        rho, pv = _S.spearmanr(DUR, Y); out[key] = (float(rho), float(pv))
        sl, c0 = np.polyfit(DUR, Y, 1); xr = np.linspace(DUR.min(), DUR.max(), 20)
        ax.plot(xr, sl * xr + c0, "--", color="#333", lw=1.5)
        ax.set_xlabel("Metaphase duration (min)"); ax.set_ylabel(ylab)
        ax.set_title(f"Spearman rho={rho:+.2f}, p={pv:.3g}, N={len(DUR)}", loc="left", fontweight="bold", fontsize=9.5)
        ax.legend(fontsize=8)
    axs[1].set_ylim(-0.03, 1.03)
    n3 = int((G == "3").sum()); c3 = len({r[0] for r in R if r[1] == "3"})
    # 2026-08-04: this was a four-line suptitle over a tight_layout that reserves no room for one, so it
    # printed straight through both panel titles. Headline stays up top; the explanation moves below the
    # axes where it has the full figure width.
    fig.suptitle("NF5 — when does a sisterless kinetochore congress?  ABSOLUTE time (left) vs FRACTION of metaphase (right)",
                 x=.01, ha="left", fontweight="bold", fontsize=10)
    fig.text(0.01, -0.02,
             f"The two panels disagree because the fraction DIVIDES BY duration: a longer metaphase shrinks the "
             f"fraction mechanically.\n"
             f"Absolute time (rho={out['absolute'][0]:+.2f}, p={out['absolute'][1]:.3g}) agrees with the other "
             f"congression plots — congression happens LATER in longer metaphases.\n"
             f"The fraction axis (rho={out['fraction'][0]:+.2f}, p={out['fraction'][1]:.3g}) reverses the apparent "
             f"sign.  Verified: {n3} congressed 3-sisterless KTs from {c3} cells, none >3 per cell.",
             ha="left", va="top", fontsize=7.4, color="#555", linespacing=1.5)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(f"{OUT}/G3_pole_time_absolute_vs_fraction.png", bbox_inches="tight", dpi=150); plt.close(fig)
    lib.record_plot("G3_pole_time_absolute_vs_fraction",
                    ["batch", "n_sisterless", "chromosome", "pole_time_min", "meta_duration_min", "frac_meta_to_ana"],
                    [[r[0], r[1], r[2], round(r[3], 3), round(r[4], 3), round(r[5], 4)] for r in R],
                    {"nf5": "absolute vs fraction; the fraction axis inverts the trend by construction",
                     "stats": out, "n_triple_KTs": n3, "n_triple_cells": c3,
                     "x_label": "Metaphase duration (min)"},
                    SCRIPT, "Congression timing vs metaphase duration: absolute time vs fraction")
    print(f"NF5: N={len(R)}  absolute rho={out['absolute'][0]:+.3f} p={out['absolute'][1]:.3g} | "
          f"fraction rho={out['fraction'][0]:+.3f} p={out['fraction'][1]:.3g} | triple {n3} KTs / {c3} cells")


# ── NF6: kinetochore speed during ANAPHASE, single vs triple ──────────────────────────────────────
def _nf6_anaphase_speed():
    LM = list(_c2.DictReader(open(f"{ROOT}/annotations/KT_LANDMARK_ANALYSIS_20260723.csv")))
    per = _cc.defaultdict(list); percell = _cc.defaultdict(list)
    for r in LM:
        if r.get("phase") != "anaphase": continue
        # USER 2026-08-05: "make sure that the kinetochores being used in NF6 ... are paired, not lagging
        # or polar". There was no label filter at all: of the 1430 anaphase rows carrying a speed, 713 were
        # LAGGING, 247 polar and 27 other — so the figure was mostly measuring lagging chromosomes, which
        # move differently in anaphase, and only 443 rows were the paired kinetochores it claimed.
        if (r.get("label") or "").strip() != "paired": continue
        b = (r.get("batch") or "").strip()
        if not _cohort_ok(b) or _sis(b) not in ("1", "3"): continue
        try: v = float(r["speed_um_s"]) * 60.0
        except Exception: continue
        # USER 2026-08-10: "one point per kinetochore, not one point per batch ... if a movie has multiple
        # marked paired kientochores into anaphase, theyre plotted seperately". It was keyed by BATCH, so a
        # cell with four tracked kinetochores contributed exactly as much as a cell with one, and the
        # pooling hid the effect: per batch n=12/8 p=0.238, per kinetochore n=21/20 p=0.0127. 16 of the 20
        # cells have more than one kinetochore tracked into anaphase, and the triple group suffered most
        # (n 8 -> 20). Keyed by TRACK now; the per-cell test is still reported as the conservative number.
        per[(b, _sis(b), r.get("track_id") or "")].append(v)
        percell[(b, _sis(b))].append(v)
    a = [float(np.median(v)) for k, v in per.items() if k[1] == "1" and len(v) >= 3]
    c = [float(np.median(v)) for k, v in per.items() if k[1] == "3" and len(v) >= 3]
    ac = [float(np.median(v)) for k, v in percell.items() if k[1] == "1" and len(v) >= 3]
    cc = [float(np.median(v)) for k, v in percell.items() if k[1] == "3" and len(v) >= 3]
    p_cell = (st.mannwhitneyu(ac, cc, alternative="two-sided")[1]
              if len(ac) >= 3 and len(cc) >= 3 else float("nan"))
    if len(a) < 3 or len(c) < 3: print(f"NF6: too few cells ({len(a)}/{len(c)})"); return
    # 🔴 HER 2026-08-20, board-8 item 7: *"this plot, as you can tell, has very messed up formatting"*.
    # Two causes, both text: (1) the y-label was a SENTENCE ("Median speed during anaphase (µm/min), per
    # KINETOCHORE"), taller than the axes, so it was clipped; (2) the footnote was unwrapped, and
    # bbox_inches="tight" grows the canvas to the widest artist, so the axes ended up in the left quarter
    # of a very wide page and the two tick labels collided. Axis label is now the quantity and its unit
    # (her board-8 item 6: "no more than 4 words and then units"); the footnote is wrapped.
    import textwrap as _tw
    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    p = _box2(ax, a, c, "Anaphase kinetochore speed (µm/min)",
              "Kinetochore speed during anaphase (one point per kinetochore)")
    _note = ("One point per KINETOCHORE (median over its anaphase frames), from her outlines; "
             "KT_LANDMARK_ANALYSIS speed_um_s, phase=anaphase. Per-CELL test, the conservative number "
             f"(kinetochores from one cell are not independent): n={len(ac)} vs {len(cc)} cells, "
             f"p={p_cell:.3g}")
    ax.text(0.0, -0.16, "\n".join(_tw.wrap(_note, 92)),
            transform=ax.transAxes, fontsize=7, color="#555", va="top", linespacing=1.5)
    plt.tight_layout(); fig.savefig(f"{OUT}/G6_anaphase_kt_speed_single_vs_triple.png",
                                    bbox_inches="tight", dpi=150); plt.close(fig)
    lib.record_plot("G6_anaphase_kt_speed_single_vs_triple",
                    ["batch", "track_id", "n_sisterless", "median_speed_um_per_min", "n_frames"],
                    [[k[0], k[2], k[1], round(float(np.median(v)), 4), len(v)] for k, v in per.items() if len(v) >= 3],
                    {"nf6": "PAIRED KT speed during anaphase, single vs triple (lagging/polar excluded 2026-08-05)",
                     "mannwhitney_p": p, "mannwhitney_p_percell": p_cell,
                     "unit": "one row per KINETOCHORE (track_id), not per cell — user 2026-08-10",
                     "y_label": "Median KT speed during anaphase (um/min)"},
                    SCRIPT, "Kinetochore speed during anaphase, single vs triple (per kinetochore)",
                    key_column="batch")
    print(f"NF6 per-KT: 1-sis n={len(a)} med={np.median(a):.2f} | 3-sis n={len(c)} med={np.median(c):.2f} | p={p}")
    print(f"NF6 per-cell (conservative): n={len(ac)}/{len(cc)} p={p_cell}")


# ── NF7: sister oscillation, single vs triple (1 vs 3, not 2/3 pooled) ────────────────────────────
def _nf7_sister_oscillation():
    src = f"{ROOT}/ablation_plots/data/kk_osc_refined.csv"
    if not os.path.exists(src): print("NF7: kk_osc_refined.csv missing"); return
    amp = _cc.defaultdict(list); per = _cc.defaultdict(list); _ident = []
    for r in _c2.DictReader(open(src)):
        b = (r.get("cell") or "").strip()
        if not b or not _cohort_ok(b): continue
        g = _sis(b)
        if g not in ("1", "3"): continue
        # 2026-08-10: kk_osc_refined.csv now carries TWO labelled units -- "pair" rows (mean k-k) and
        # "kinetochore" rows (amplitude/period, one per KT, per user). Oscillation is a per-KINETOCHORE
        # quantity, so take only those rows; the old code read every row and a now-renamed `period_s`,
        # which would have left the PERIOD panel silently empty.
        if (r.get("unit") or "").strip() != "kinetochore": continue
        for key, store in (("amp_um", amp), ("period_min", per)):
            try: store[g].append(float(r[key]))
            except Exception: continue
            # Carry the CELL + kinetochore identity through to record_plot. Without it this figure's CSV was
            # panel/series/mark/x/y with no batch column, so it could not be audited for cohort leakage at
            # all -- the exact check that caught the prophase problem could not be run on it.
            _ident.append([b, (r.get("pair") or "").strip(), (r.get("kinetochore") or "").strip(),
                           g, {"amp_um": "amplitude_um", "period_min": "period_min"}[key],
                           round(float(r[key]), 5)])
    if len(amp["1"]) < 3 or len(amp["3"]) < 3:
        print(f"NF7: too few pairs ({len(amp['1'])}/{len(amp['3'])})"); return
    fig, axs = plt.subplots(1, 2, figsize=(11.6, 5.2))
    p1 = _box2(axs[0], amp["1"], amp["3"], "Oscillation amplitude (µm)", "Sister-KT oscillation AMPLITUDE")
    p2 = _box2(axs[1], per["1"], per["3"], "Oscillation period (min)", "Sister-KT oscillation PERIOD")
    fig.suptitle("NF7 — sister-kinetochore oscillation, single vs triple (1 vs 3 sisterless, not 2/3 pooled)\n"
                 "metaphase window; plate-relative position, PER KINETOCHORE",
                 x=.01, ha="left", fontweight="bold", fontsize=9)
    plt.tight_layout(); fig.savefig(f"{OUT}/G6_sister_oscillation_single_vs_triple.png",
                                    bbox_inches="tight", dpi=150); plt.close(fig)
    lib.record_plot("G6_sister_oscillation_single_vs_triple",
                    ["cell", "pair", "kinetochore", "n_sisterless", "metric", "value"], _ident,
                    {"nf7": "sister oscillation split 1 vs 3", "amplitude_p": p1, "period_p": p2,
                     "unit": "one row per KINETOCHORE per metric", "key_column": "cell"},
                    SCRIPT, "Sister-KT oscillation amplitude and period, single vs triple",
                    key_column="cell")
    print(f"NF7: amplitude p={p1} | period p={p2}  (n {len(amp['1'])}/{len(amp['3'])})")


# ── NF8 (REBUILT 2026-08-05) — polar DISTORTION along the spindle axis, single vs triple ─────────
# USER: "polar equivalent tension vs paired k-k over metaphase plot is now marked as retired. where is its
# revised/replacemen version?" and "i think ive said this before but im weary that the data in NF8 is
# correct, as intiutively i think that triple sisterless tension should be lower than 1 sisterless".
#
# Her doubt was right. The old NF8 plotted `equivalent k-k` = A_FIT + B_FIT*spindle_strain, a calibration
# fitted at r=0.035, R2=0.0012, p=0.309 — effectively a constant, so it CANNOT express a cohort difference
# no matter what the cells do. That is why single and triple looked alike.
#
# This version measures the polar kinetochore's own outline along its LOADING axis (sister-pair axis where
# a sister exists, else the windowed displacement axis — 6.5 deg and 12 deg from the plate normal, against
# 58.5 deg for the outline long axis the retired metric used). Per her rules: outliers are kept in the
# table but excluded here, and only metaphase-onset-to-anaphase-onset frames are used.
def _nf8_polar_distortion():
    src = f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv"
    if not os.path.exists(src): print("NF8: distortion csv missing"); return
    per = _cc.defaultdict(list)
    for r in _c2.DictReader(open(src)):
        if r.get("label") != "polar": continue
        if r.get("in_window") != "1" or r.get("outlier") != "0": continue
        b = (r.get("batch") or "").strip(); g = _sis(b)
        if g not in ("1", "3") or not _cohort_ok(b): continue
        try: per[(b, g)].append(float(r["spindle_strain"]))
        except Exception: pass
    a = [float(np.median(v)) for (b, g), v in per.items() if g == "1" and len(v) >= 3]
    c = [float(np.median(v)) for (b, g), v in per.items() if g == "3" and len(v) >= 3]
    if len(a) < 3 or len(c) < 3: print(f"NF8: too few cells ({len(a)}/{len(c)})"); return
    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    # HER 2026-08-19 board 7 item 4 / board 8 item 6: one canonical y-axis label, "no more than 4 words and
    # then units". This one read "Polar-KT distortion along the spindle axis\n(extent across the plate /
    # extent along it)" and only LOOKED fixed because the publication render was clipping it; once
    # pub_strip stopped clipping (2026-08-21) the full sentence came back. Route it through canon_axis so
    # the short form is what is drawn, not what survives a crop. The axis definition lives in Methods.
    p = _box2(ax, a, c, canon_labels.canon_axis("polar-KT distortion along the spindle axis"),
              "NF8 — POLAR kinetochore DISTORTION along the spindle axis, single vs triple")
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.text(0.0, -0.16, "one point per cell (median over its metaphase frames, >=3 frames required); "
            "spindle axis = normal to that frame's metaphase plate, the same axis for polar and paired.\n"
            "REPLACES the retired `equivalent k-k`, which was a fitted constant (R2=0.001) and could not "
            "differ between cohorts. Outliers kept in the table, excluded here.",
            transform=ax.transAxes, fontsize=7, color="#555", va="top")
    plt.tight_layout()
    fig.savefig(f"{OUT}/G6_polar_distortion_single_vs_triple.png", bbox_inches="tight", dpi=150)
    # ALSO write it under the LEGACY filename. NEW_FIGURES links this figure by name, so emitting only the
    # new name would leave the deck pointing at the retired-metric image with nothing to show it is stale.
    # Same bytes, two names: the deck self-corrects on relink, and the descriptive name exists going forward.
    fig.savefig(f"{OUT}/G6_polar_equivalent_kk_single_vs_triple.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    lib.record_plot("G6_polar_distortion_single_vs_triple",
                    ["batch", "n_sisterless", "median_distortion", "n_frames"],
                    [[b, g, round(float(np.median(v)), 4), len(v)] for (b, g), v in per.items() if len(v) >= 3],
                    {"nf8": "polar spindle-axis distortion, single vs triple (replaces equivalent k-k)",
                     "mannwhitney_p": p, "y_label": "Polar-KT spindle-axis distortion",
                     "supersedes": "G6_polar_equivalent_kk_single_vs_triple"},
                    SCRIPT, "Polar-kinetochore distortion along the spindle axis, single vs triple",
                    source=[src], key_column="batch")
    print(f"NF8: 1-sis n={len(a)} med={np.median(a):.3f} | 3-sis n={len(c)} med={np.median(c):.3f} | p={p}")


# ── NF8 (OLD, retired 2026-08-05) — kept for provenance; its source series no longer exists ───────
def _nf8_polar_equivalent_kk():
    src = f"{ROOT}/ablation_plots/data/G6tenM_equivalent_kk_over_time.csv"
    if not os.path.exists(src): print("NF8: source csv missing"); return
    per = _cc.defaultdict(list)
    for r in _c2.DictReader(open(src)):
        if not str(r.get("group", "")).lower().startswith("polar"): continue
        b = (r.get("batch") or "").strip(); g = (r.get("n_sisterless") or "").strip()
        if g not in ("1", "3") or not _cohort_ok(b): continue
        try: per[(b, g)].append(float(r["kk_or_equiv_um"]))
        except Exception: pass
    a = [float(np.median(v)) for (b, g), v in per.items() if g == "1"]
    c = [float(np.median(v)) for (b, g), v in per.items() if g == "3"]
    if len(a) < 3 or len(c) < 3: print(f"NF8: too few cells ({len(a)}/{len(c)})"); return
    fig, ax = plt.subplots(figsize=(6.8, 5.2))
    p = _box2(ax, a, c, "Polar-KT equivalent k–k (µm)", "NF8 — POLAR equivalent k–k, single vs triple")
    ax.text(0.0, -0.14, "one point per cell (median over its metaphase frames); equivalent k-k = the "
            "strain to k-k calibration applied to the polar KT's spindle strain",
            transform=ax.transAxes, fontsize=7, color="#555", va="top")
    plt.tight_layout(); fig.savefig(f"{OUT}/G6_polar_equivalent_kk_single_vs_triple.png",
                                    bbox_inches="tight", dpi=150); plt.close(fig)
    lib.record_plot("G6_polar_equivalent_kk_single_vs_triple", ["batch", "n_sisterless", "median_equiv_kk_um"],
                    [[b, g, round(float(np.median(v)), 4)] for (b, g), v in per.items()],
                    {"nf8": "polar equivalent k-k, single vs triple", "mannwhitney_p": p,
                     "y_label": "Polar-KT equivalent k-k (um)"},
                    SCRIPT, "Polar-kinetochore equivalent k-k, single vs triple")
    print(f"NF8: 1-sis n={len(a)} med={np.median(a):.2f} | 3-sis n={len(c)} med={np.median(c):.2f} | p={p}")

for _fn in (_nf5_pole_time, _nf6_anaphase_speed, _nf7_sister_oscillation, _nf8_polar_distortion):
    try: _fn()
    except Exception as _e:
        import traceback; print(f"{_fn.__name__} FAILED: {_e}"); traceback.print_exc()


# ── NF3 (user 2026-08-04) ─────────────────────────────────────────────────────────────────────────
# "Pole-to-pole approximation over metaphase: also plot with just metaphase time, not proportion. Does this
#  make the difference between single and double tracks over time significant? If no, what's needed?"
# Same measurement as G6_polepole_approx_over_metaphase, but x = ABSOLUTE minutes since metaphase onset.
# The group comparison is done properly for repeated measures: a per-cell SLOPE (um/min) is fitted for each
# cell, then the two groups' slopes are compared (Mann-Whitney). Comparing raw points would treat ~40 frames
# from one cell as 40 independent observations and manufacture significance.
def _nf3_polepole_absolute():
    """USER 2026-08-19 (to-do list 0819 1pm), two items on this one figure:
         item 7  — "Change the plot here to be change in pole-pole distance on the y-axis (and again because
                    its 'change in' and not just plain value, both lines should start at a y-axis value of 0
                    at minutes since metaphase onset =0"
         item 15 — "Omit individual traces from the spindle length plot (shown below) and instead use the
                    error region as in other line plots on that artboard."
       So: y is now DELTA pole-to-pole distance, each cell zeroed on its own sample nearest metaphase onset;
       the per-cell spaghetti is gone and the group trend carries an SEM-across-CELLS band, drawn by the same
       `trendlib` helpers the artboard-4 line plots use; and the trend is anchored at (0, 0) and stops on its
       group's median-metaphase line, which comes from the artboard-2 violin (`metaphase_medians`) so this
       figure and the artboard-4 family mark the same time for the same group.
       The per-cell SLOPE comparison is unchanged and is still the group test — a slope is unaffected by the
       baseline subtraction, so the statistic is identical to the version she has seen."""
    import csv as _csv, collections as _c
    from scipy import stats as _st
    from trendlib import trend_to_mean_sem, sem_band
    from matplotlib.lines import Line2D
    import metaphase_medians
    _csv.field_size_limit(10**9)
    src = f"{ROOT}/ablation_plots/data/G6_polepole_approx_over_metaphase.csv"
    if not os.path.exists(src): print("NF3: source csv missing — run item 16 first"); return
    per = _c.defaultdict(list); grp = {}
    for r in _csv.DictReader(open(src)):
        b = r["batch"].strip()
        try: fr = float(r["frac_meta_to_ana"]); y = float(r["polepole_approx_um"])
        except Exception: continue
        dur = meta_dur_min(b)
        if dur is None: continue
        per[b].append((fr * dur, y))          # fraction -> ABSOLUTE minutes since metaphase onset
        grp[b] = (r.get("n_sisterless") or "").strip()
    COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}
    MED = metaphase_medians.medians()
    CAP = {"1": MED.get("1-Sisterless"), "3": MED.get("3-Sisterless")}
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    slopes = _c.defaultdict(list); rows = []; ncell = _c.Counter()
    pts3 = _c.defaultdict(list)               # group -> [(t, delta_um, cell)]
    for b, pts in per.items():
        g = grp.get(b)
        if g not in COL: continue
        pts.sort(); X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
        ncell[g] += 1
        base = Y[int(np.argmin(np.abs(X)))]   # this cell's pole-to-pole distance AT metaphase onset
        for x, y in zip(X, Y):
            pts3[g].append((float(x), float(y - base), b))
            rows.append([b, g, round(float(x), 3), round(float(y - base), 3)])
        if len(X) >= 3 and X.max() > X.min():
            slopes[g].append(float(np.polyfit(X, Y, 1)[0]))
    for g in ("1", "3"):
        p3 = pts3.get(g)
        if not p3 or len(p3) < 6: continue
        cap = CAP.get(g)
        if cap is None or cap <= 0: cap = float(np.percentile([q[0] for q in p3], 95))
        bx, by, bs = trend_to_mean_sem(p3, cap, start=0.0)
        if len(bx) < 2: continue
        if bx[0] > 1e-9:                       # item 7: the line starts at (0, 0)
            bx = [0.0] + list(bx); by = [0.0] + list(by); bs = [0.0] + list(bs)
        sem_band(ax, bx, by, bs, COL[g])       # item 15: error region instead of individual traces
        ax.plot(bx, by, "-o", color=COL[g], lw=2.8, ms=5.0, zorder=4,
                label=f"{lib.lbl(g+'-Sister')} — {ncell[g]} cells")
        # the trend runs to this line and stops on it; no on-plot text (2026-08-19 item 5)
        ax.axvline(cap, color=COL[g], ls=(0, (2, 1.5)), lw=1.2, zorder=2)
    ax.axhline(0, color="#888", ls=":", lw=1.0, zorder=1)
    ax.set_xlim(left=0)
    ps = None
    if len(slopes["1"]) >= 3 and len(slopes["3"]) >= 3:
        ps = float(_st.mannwhitneyu(slopes["1"], slopes["3"], alternative="two-sided")[1])
    med1 = np.median(slopes["1"]) if slopes["1"] else float("nan")
    med3 = np.median(slopes["3"]) if slopes["3"] else float("nan")
    need = ""
    if slopes["1"] and slopes["3"]:
        a = np.array(slopes["1"]); b_ = np.array(slopes["3"])
        sd = np.sqrt((a.var(ddof=1) + b_.var(ddof=1)) / 2)
        d = abs(np.mean(a) - np.mean(b_)) / sd if sd > 0 else 0
        if d > 0:
            n_needed = int(np.ceil(2 * ((1.96 + 0.84) / d) ** 2))
            need = (f"Observed effect size d={d:.2f} on per-cell slope. At this effect, ~{n_needed} cells PER GROUP "
                    f"would be needed for 80% power (have {len(a)} and {len(b_)}).")
        else:
            need = "The two groups' slopes are essentially identical; no sample size would make this significant."
    ax.set_xlabel("Minutes since metaphase onset")
    ax.set_ylabel("\u0394 pole-to-pole distance (\u00b5m)")
    _h, _l = ax.get_legend_handles_labels()
    _h.append(Line2D([0], [0], color="#555", ls=(0, (2, 1.5)), lw=1.2))
    _l.append("median metaphase duration (artboard-2 violin)")
    ax.legend(_h, _l, fontsize=8.5, title="line = group mean, shaded = SEM across cells")
    ax.set_title("Change in pole-to-pole distance vs absolute metaphase time, 1 vs 3 sisterless\n"
                 + (f"per-cell slope: 1-sis {med1:+.3f} vs 3-sis {med3:+.3f} \u00b5m/min, Mann-Whitney p={ps:.3g}"
                    if ps is not None else "too few cells for a slope comparison"),
                 loc="left", fontweight="bold", fontsize=10)
    ax.text(0.0, -0.145,
            "Groups compared by PER-CELL SLOPE, not by raw points: one cell contributes many frames, and pooling\n"
            "them would treat those as independent observations and inflate significance.\n" + need,
            transform=ax.transAxes, fontsize=6.9, color="#555", va="top", linespacing=1.5)
    plt.tight_layout()
    fig.savefig(f"{OUT}/G6_polepole_approx_absolute_time.png", bbox_inches="tight", dpi=150); plt.close(fig)
    lib.record_plot("G6_polepole_approx_absolute_time",
                    ["batch", "n_sisterless", "min_since_metaphase_onset", "delta_polepole_um"], rows,
                    {"nf3": "absolute metaphase time; groups compared by per-cell slope",
                     "y": "CHANGE in pole-to-pole distance, each cell zeroed at its own metaphase onset (2026-08-19 item 7)",
                     "traces": "individual cell traces omitted; SEM-across-cells band instead (2026-08-19 item 15)",
                     "median_line": "median metaphase duration from G1_violin2_no_dc_offtarget_journal",
                     "slope_median_1sis": None if not slopes["1"] else round(float(med1), 5),
                     "slope_median_3sis": None if not slopes["3"] else round(float(med3), 5),
                     "slope_mannwhitney_p": ps, "power_note": need,
                     "x_label": "Minutes since metaphase onset",
                     "y_label": "Delta pole-to-pole distance (um)"},
                    SCRIPT, "Change in pole-to-pole distance vs absolute metaphase time, 1 vs 3 sisterless")
    print(f"NF3: slopes 1-sis n={len(slopes['1'])} med={med1:+.4f} | 3-sis n={len(slopes['3'])} med={med3:+.4f} | p={ps}")
    print("   " + need)
_nf3_polepole_absolute()


# ══ FB9 / FB10 (user 2026-08-04) ══════════════════════════════════════════════════════════════════
# "9. Polar equivalent k-k over metaphase for single and triple"
# "10. Oscillations over metaphase for single and triple. Do oscillation patterns change over time?"
# Both are the same shape of question as the pole-to-pole figure above, so they use the same convention she
# has asked for repeatedly: metaphase is scaled 0-1 PER CELL (0 = metaphase onset, 1 = anaphase onset), so
# cells with different metaphase durations are comparable on one axis.
#
# The group comparison is done on PER-CELL SLOPES, never on raw points: each cell contributes many frames,
# and treating those as independent observations inflates significance (the mistake NF3 was written to avoid).
def _over_metaphase(src_csv, batch_col, time_col, value_col, group_col,
                    plot_id, ylab, title, note, extra_filter=None):
    """Shared builder: <value> vs metaphase progress (0-1), 1-sisterless vs 3-sisterless.

    Draws each cell's own trace faintly, the per-group binned median + IQR band on top, and reports both
    (a) whether the value TRENDS across metaphase within each group and (b) whether the two groups' per-cell
    trends differ. Returns the recorded row list."""
    if not os.path.exists(src_csv):
        print(f"{plot_id}: source csv missing ({src_csv})"); return []
    COL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}
    series = _cc.defaultdict(list)      # batch -> [(frac, value)]
    grp = {}
    for r in _c2.DictReader(open(src_csv)):
        if extra_filter is not None and not extra_filter(r): continue
        b = (r.get(batch_col) or "").strip()
        if not b or not _cohort_ok(b): continue
        g = (r.get(group_col) or "").strip()
        if g not in ("1", "3"):                       # some CSVs store the cohort label, not the count
            g = _sis(b)
        if g not in ("1", "3"): continue
        dur = meta_dur_min(b)
        if not dur: continue
        try:
            t = float(r[time_col]); v = float(r[value_col])
        except Exception:
            continue
        frac = t / dur
        if not (0.0 <= frac <= 1.0): continue         # metaphase window only
        series[b].append((frac, v)); grp[b] = g

    if not series:
        print(f"{plot_id}: no rows survived the cohort/metaphase filter"); return []

    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    bins = np.linspace(0, 1, 9)
    stats_txt, slopes, ncell, npts = [], _cc.defaultdict(list), _cc.Counter(), _cc.Counter()
    rows_out = []
    for b, pts in series.items():
        g = grp[b]; pts = sorted(pts)
        X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
        ncell[g] += 1; npts[g] += len(pts)
        ax.plot(X, Y, "-", color=COL[g], lw=.7, alpha=.22, zorder=1)
        if len(X) >= 3 and X.max() > X.min():
            slopes[g].append(float(np.polyfit(X, Y, 1)[0]))       # value change per full metaphase
        rows_out += [[b, g, round(float(x), 4), round(float(y), 5)] for x, y in pts]
    for g in ("1", "3"):
        allp = [p for b, pts in series.items() if grp[b] == g for p in pts]
        if not allp: continue
        X = np.array([p[0] for p in allp]); Y = np.array([p[1] for p in allp])
        idx = np.digitize(X, bins)
        bx, bm, blo, bhi = [], [], [], []
        for i2 in range(1, len(bins)):
            sel = Y[idx == i2]
            if len(sel) >= 3:
                bx.append((bins[i2-1] + bins[i2]) / 2); bm.append(np.median(sel))
                blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
        if bx:
            ax.fill_between(bx, blo, bhi, color=COL[g], alpha=.16, zorder=2)
            ax.plot(bx, bm, "-o", color=COL[g], lw=2.8, ms=5.5, zorder=4,
                    label=f"{lib.lbl(g+'-Sister')} — {ncell[g]} cells, {npts[g]} points")
        _r, _p = st.spearmanr(X, Y)
        _sl = slopes[g]
        _sltxt = (f"per-cell slope median {np.median(_sl):+.2f}/metaphase (n={len(_sl)})") if _sl else "slope n/a"
        stats_txt.append(f"{g}-sis: median {np.median(Y):.2f}, pooled trend rho={_r:+.2f} p={_p:.2g}; {_sltxt}")

    # do the two groups CHANGE differently across metaphase? compare per-cell slopes, not raw points
    ptxt = "too few cells for a group comparison of trends"
    if len(slopes["1"]) >= 3 and len(slopes["3"]) >= 3:
        _u, _pv = st.mannwhitneyu(slopes["1"], slopes["3"], alternative="two-sided")
        ptxt = (f"change across metaphase (per-cell slope): 1-sis {np.median(slopes['1']):+.2f} vs "
                f"3-sis {np.median(slopes['3']):+.2f} per metaphase, Mann-Whitney p={_pv:.3g}")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction of metaphase elapsed")
    ax.set_ylabel(ylab)
    ax.set_title(f"{title}\n{ptxt}", loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=8.5, title="thick line = group median, band = IQR; thin lines = individual cells")
    ax.text(0.0, -0.155, note + "\n" + "   |   ".join(stats_txt),
            transform=ax.transAxes, fontsize=6.6, color="#555", va="top", linespacing=1.55)
    plt.tight_layout()
    fig.savefig(f"{OUT}/{plot_id}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"{plot_id}: 1-sis {ncell['1']} cells / {npts['1']} pts | 3-sis {ncell['3']} cells / {npts['3']} pts | {ptxt}")
    return rows_out


def _fb9_polar_equiv_kk_over_metaphase():
    # USER 2026-08-05. This read the POLAR rows of G6tenM_equivalent_kk_over_time.csv — the retired
    # `equivalent k-k` (A_FIT + B_FIT*spindle_strain, R2=0.001). When that series was removed from its
    # source, this figure silently produced NOTHING: the filter matched zero rows and the plot vanished
    # without raising. Re-sourced onto DISTORTION along the spindle axis, from G6tenM_strain_over_time.
    #
    # plot_id and therefore the FILENAME are deliberately unchanged, so the deck relinks to the corrected
    # figure by itself. The name says "equivalent_kk" for continuity only; the axis states what it is.
    rows_out = _over_metaphase(
        f"{ROOT}/ablation_plots/data/G6tenM_strain_over_time.csv",
        batch_col="batch", time_col="t_min_from_meta", value_col="spindle_strain",
        group_col="n_sisterless",
        plot_id="G6_polar_equivalent_kk_over_metaphase",
        ylab="Polar-KT distortion along the spindle axis\n(extent across the plate / extent along it)",
        title="POLAR kinetochore DISTORTION over metaphase — 1- vs 3-sisterless",
        note=("Distortion = the outline's extent across the metaphase plate over its extent along the plate, "
              "on the per-frame plate normal — the SAME axis\nfor polar and paired, so the two are comparable. "
              "It is NOT converted to a k-k distance; that conversion was a calibration fitted at R2=0.001. "
              "Metaphase is\nscaled 0-1 per cell so cells of different duration are comparable. Few triple "
              "cells carry polar outlines, so the 3-sisterless trend is weak."),
        extra_filter=lambda r: str(r.get("label", "")).lower() == "polar")
    if rows_out:
        lib.record_plot("G6_polar_equivalent_kk_over_metaphase",
                        ["batch", "n_sisterless", "frac_meta_to_ana", "distortion"], rows_out,
                        {"fb9": "polar spindle-axis distortion across metaphase progress, 1 vs 3 sisterless",
                         "filename_note": "the `equivalent_kk` filename is legacy; the metric is distortion",
                         "x": "fraction of metaphase elapsed, 0-1 (per cell)",
                         "group_test": "per-cell slope, Mann-Whitney (never raw points)"},
                        SCRIPT, "Polar-KT equivalent k-k over metaphase, single vs triple")


def _fb10_oscillation_over_metaphase():
    rows_out = _over_metaphase(
        f"{ROOT}/ablation_plots/data/G4_oscillation_chronological.csv",
        batch_col="batch", time_col="t_min_from_meta", value_col="value",
        group_col="sisterless_group",
        plot_id="G6_oscillation_over_metaphase",
        ylab="Oscillation (µm)",
        title="Oscillation over metaphase — 1- vs 3-sisterless  (do oscillation patterns change over time?)",
        note=("Answers 'do oscillation patterns change over time?' two ways: the pooled Spearman says whether "
              "oscillation drifts across metaphase\nwithin each group, and the per-cell slope comparison says "
              "whether the two groups drift DIFFERENTLY. Metaphase is scaled 0-1 per cell."))
    if rows_out:
        lib.record_plot("G6_oscillation_over_metaphase",
                        ["batch", "n_sisterless", "frac_meta_to_ana", "oscillation_um"], rows_out,
                        {"fb10": "oscillation across metaphase progress, 1 vs 3 sisterless",
                         "x": "fraction of metaphase elapsed, 0-1 (per cell)",
                         "group_test": "per-cell slope, Mann-Whitney (never raw points)"},
                        SCRIPT, "Oscillation over metaphase, single vs triple")


for _fn in (_fb9_polar_equiv_kk_over_metaphase, _fb10_oscillation_over_metaphase):
    try: _fn()
    except Exception as _e:
        import traceback; print(f"{_fn.__name__} FAILED: {_e}"); traceback.print_exc()
