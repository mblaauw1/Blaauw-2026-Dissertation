#!/usr/bin/env python3
"""Relative tension / force on a POLAR (sisterless) kinetochore vs a bi-oriented sister pair (user 2026-07-23).

WHY it's hard: k-k (inter-kinetochore) distance is the classic tension readout, but it needs TWO sisters — a
polar KT is sisterless (its sister was ablated) so k-k is undefined. The single-KT force reporter in the
literature is INTRA-kinetochore stretch ('delta', inner-vs-outer marker; Maresca & Salmon 2009) — but these
cells carry ONE outer marker (eYFP-Cdc20 / Mad1), so delta isn't measurable live. What IS measurable from the
outline is the KT's DEFORMATION: under its poleward attachment load the KT elongates along the SPINDLE axis.
That is a coarse single-marker strain and it works for a sisterless KT.

Pipeline:
  1. spindle-axis strain per KT frame = outline elongation along the plate-NORMAL (spindle) axis
     (spindle_extent / cross_extent), from the traced polygon + the metaphase-plate line.
  2. VALIDATE strain as a tension proxy: in sister pairs, does the pair's mean spindle strain track its k-k
     distance (per frame)? Positive correlation ⇒ strain reports tension.
  3. CALIBRATE: fit k-k ≈ a + b·strain on sisters; read each polar KT's EQUIVALENT k-k (equivalent tension)
     from its strain.
  4. Relative tension = polar strain / paired-sister strain (dimensionless; needs no spring constant). An
     ABSOLUTE force needs a centromere stiffness κ from the literature — reported with that assumption flagged.
Emphasis on TIME-RESOLVED views (everything is frame-by-frame): strain and equivalent-k-k over mitotic
progress, per state.
"""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib, kt_stats
import kt_tracks as KT
from kt_landmark_analysis import load_plates, phase_times
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group6_tracks"
SRC = [f"{ROOT}/annotations/KT_OUTLINE_TRACKS_20260723.csv", f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv"]
COL = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
# literature centromere/chromatin stiffness for the OPTIONAL absolute-force estimate (order-of-magnitude;
# mammalian centromere spring ~ tens-to-hundreds pN/µm — used only for a flagged illustrative number).
KAPPA_PN_PER_UM = 100.0


def spindle_strain(pieces, plate_line, px):
    """Outline elongation along the plate-NORMAL (spindle) axis: spindle_extent/cross_extent (dimensionless),
    plus the absolute spindle extent (µm)."""
    p = np.vstack([np.asarray(q, float) for q in pieces])
    a = np.asarray(plate_line[0], float); b = np.asarray(plate_line[-1], float)
    d = b - a; n = np.hypot(*d)
    if n < 1e-6:
        return None
    dirv = d / n                       # along the plate line
    norm = np.array([-dirv[1], dirv[0]])  # spindle axis = plate normal
    c = p - p.mean(0)
    spindle_ext = float(np.ptp(c @ norm)) * px
    cross_ext = float(np.ptp(c @ dirv)) * px
    if cross_ext <= 0:
        return None
    return spindle_ext / cross_ext, spindle_ext, cross_ext


def build():
    objs = KT.tracked_objects()
    plates = load_plates()
    ph = phase_times(sorted({o["batch"] for o in objs}))
    # sister k-k per (batch, frame): mean k-k over pairs on that frame
    kk = collections.defaultdict(dict)
    for r in csv.DictReader(open(f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv")):
        kk[r["batch"]][int(r["frame"])] = float(r["kk_dist_um"])
    rows = []
    for o in objs:
        plist = plates.get(o["batch"], [])
        if not plist:
            continue
        line = min(plist, key=lambda z: abs(z[0] - o["t_sec"]))[1]
        s = spindle_strain(o["points"], line, o["px"])
        if s is None:
            continue
        strain, sp, cr = s
        mt, at = ph.get(o["batch"], (None, None))
        prog = ""
        if mt is not None and at is not None and at > mt and np.isfinite(o["t_sec"]):
            prog = round((o["t_sec"] - mt) / (at - mt), 4)
        rows.append(dict(batch=o["batch"], track_id=o["track_id"], label=o["label"], frame=o["frame"],
                         t_sec=round(o["t_sec"], 2) if np.isfinite(o["t_sec"]) else "",
                         progress=prog, spindle_strain=round(strain, 4), spindle_extent_um=round(sp, 4),
                         cross_extent_um=round(cr, 4),
                         pair_kk_um=(round(kk[o["batch"]][o["frame"]], 4) if o["frame"] in kk.get(o["batch"], {}) else "")))
    return rows


def _save(fig, name, cap, header=None, rows=None):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    # 2026-08-03: was record_plot(["x"], []) - a placeholder registering an EMPTY data table, so
    # the figure could not be checked against its own data and any _zoom companion was built from
    # nothing. Same bug fixed in kt_phase_split.py on 2026-07-29 and never propagated here.
    try:
        lib.record_plot(name, header or ["x"], rows or [], {"family": "tension"},
                        script=__file__, caption=cap, source=SRC,
                        key_column=("batch" if header and "batch" in header else None))
    except Exception as _e:
        print("    record_plot(%s) failed: %s" % (name, _e))
    print("  " + name)


def band(ax, xs, ys, color, label):
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    m = np.isfinite(xs) & np.isfinite(ys); xs, ys = xs[m], ys[m]
    if len(xs) < 6: return
    ax.scatter(xs, ys, s=6, color=color, alpha=0.18, lw=0)
    bins = np.linspace(-0.2, 1.4, 10); idx = np.digitize(xs, bins)
    bx, bm, blo, bhi = [], [], [], []
    for bi in range(1, len(bins)):
        sel = ys[idx == bi]
        if len(sel) >= 4:
            bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
            blo.append(np.percentile(sel, 25)); bhi.append(np.percentile(sel, 75))
    if bx:
        ax.plot(bx, bm, "-o", color=color, lw=2.2, ms=4, label=label)
        ax.fill_between(bx, blo, bhi, color=color, alpha=0.15)


if __name__ == "__main__":
    R = build()
    outcsv = f"{ROOT}/annotations/KT_TENSION_20260723.csv"
    cols = ["batch", "track_id", "label", "frame", "t_sec", "progress", "spindle_strain",
            "spindle_extent_um", "cross_extent_um", "pair_kk_um"]
    with open(outcsv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(R)
    print(f"wrote {len(R)} rows -> {outcsv}")

    # USER 2026-08-05: "i want all the same plots but just with the updated info", and the load-bearing
    # axis "regardless of paired or polar, should be pretty parallel to the polar axis and pretty
    # perpendicular to the plate". That is `spindle_strain` — which build() already computes against the
    # plate line nearest IN TIME to each frame, so a rotating plate is handled. What changes is the
    # DELIVERABLE: it is reported as DISTORTION, unconverted, instead of being pushed through the
    # R2=0.001 calibration into a fake "equivalent k-k" in micrometres.
    #
    # The graft below re-reads it from the joined table only to pick up the outline-quality outlier flags
    # (multi-piece, degenerate, spindle-extent jump) and the metaphase-window column. Figure names are
    # unchanged so META_FIGURES relinks by filename.
    _LOAD = {}
    try:
        for _r in csv.DictReader(open(f"{ROOT}/annotations/KT_TENSION_LOADAXIS_20260805.csv")):
            _LOAD[(_r["track_id"], _r["frame"])] = ("" if _r.get("outlier") == "1"
                                                    else _r.get("spindle_strain", ""))
    except FileNotFoundError:
        print("  WARNING: loading-axis table missing — run kt_loading_axis.py first")
    _ng = 0
    for _r in R:
        _r["distortion"] = _LOAD.get((_r["track_id"], str(_r["frame"])), "")
        if _r["distortion"] != "": _ng += 1
    print(f"  distortion available on {_ng}/{len(R)} rows ({_ng/max(1,len(R))*100:.1f}%) after outline-quality flags")

    def col(rs, k):
        out = []
        for r in rs:
            try: out.append(float(r[k]))
            except Exception: out.append(np.nan)
        return np.array(out)

    # 1) VALIDATION — METAPHASE ONLY (k-k reports tension only for a bi-oriented pair; anaphase k-k = the
    # segregation distance, not spring tension, so it must be excluded).
    metaframe = set()   # (batch,frame) that are metaphase per the sister k-k table
    for r in csv.DictReader(open(f"{ROOT}/annotations/KT_SISTER_KK_20260723.csv")):
        if r["phase"] == "metaphase":
            metaframe.add((r["batch"], int(r["frame"])))
    pair = [r for r in R if r["label"] == "paired" and r["pair_kk_um"] != "" and (r["batch"], r["frame"]) in metaframe]
    byf = collections.defaultdict(list)
    for r in pair: byf[(r["batch"], r["frame"])].append(float(r["spindle_strain"]))
    X, Y = [], []
    for key in byf:
        X.append(np.mean(byf[key]))
        Y.append(next(float(r["pair_kk_um"]) for r in pair if (r["batch"], r["frame"]) == key))
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    ax.scatter(X, Y, s=16, color=COL["paired"], alpha=0.5, edgecolor="white", lw=0.2)
    valid = False
    if len(X) > 6:
        kt_stats.add_corr_stats(ax, X, Y, loc="upper right")
        rho, pv = st.spearmanr(X, Y)
        valid = (rho > 0 and pv < 0.05)
    ax.set_xlabel("sister-KT spindle strain (elongation along spindle)"); ax.set_ylabel("metaphase pair k–k (µm)")
    ax.set_title(f"Does KT shape-strain report tension? strain vs k–k, METAPHASE sisters  [{'VALIDATED' if valid else 'NOT validated'}]",
                 loc="left", fontweight="bold", fontsize=9)
    _save(fig, "G6ten_validate_strain_vs_kk", "strain vs k-k validation (metaphase)",
          header=["spindle_strain","pair_kk_um"], rows=[[round(float(a),5), round(float(b),5)] for a,b in zip(X, Y)])

    # calibrate ONLY if the metaphase validation is positive+significant; else the strain to tension map is unsupported
    a_fit = b_fit = None
    if valid:
        b_fit, a_fit = np.polyfit(X, Y, 1)

    # 2) polar vs paired spindle strain (violin) with thorough stats
    # ITEM 11 (user 2026-08-04): PHASE-MATCH per state — paired/polar measured during METAPHASE, lagging
    # during ANAPHASE. Pooling all phases compared a mostly-anaphase population (lagging, which cannot be
    # scored before anaphase onset) against mostly-metaphase paired/polar populations.
    PHASE_BY_LABEL = {"paired": "metaphase", "polar": "metaphase", "lagging": "anaphase"}
    PHASE_MATCH_NOTE = ("phase-matched: paired & polar during METAPHASE, lagging during ANAPHASE — each "
                        "state scored in the window where that label describes the kinetochore")
    # NOTE: build() rows carry no `phase` column (the r["phase"] used in the validation block above comes from
    # KT_SISTER_KK, a different table). Derive the phase from `progress`, which build() already computes as
    # 0 = metaphase onset, 1 = anaphase onset.
    def _row_phase(r):
        try: p = float(r.get("progress"))
        except Exception: return None
        if p >= 1.0: return "anaphase"
        if p >= 0.0: return "metaphase"
        return "prometaphase"
    def _pm(r):
        want = PHASE_BY_LABEL.get(r.get("label"))
        return want is None or _row_phase(r) == want
    g = {k: [float(r["distortion"]) for r in R if r["label"] == k and _pm(r) and r.get("distortion") not in (None, "")]
         for k in COL}
    print("  G6ten_strain_by_state phase-matched N: " + ", ".join(f"{k}={len(v)}" for k, v in g.items()))
    fig, ax = plt.subplots(figsize=(6.6, 5.0)); dmax = max((max(v) for v in g.values() if v), default=2)
    for i, k in enumerate(COL):
        d = g[k]
        if len(d) < 6: continue
        lib.journal_violin(ax, d, i, COL[k], alpha=0.28, lw=1.0)
        ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=COL[k], alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
        ax.hlines(np.median(d), i-0.34, i+0.34, color=COL[k], lw=2.4)
        ax.text(i, dmax*1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(COL))); ax.set_xticklabels(list(COL), fontsize=9)
    ax.set_ylabel("distortion along the spindle axis (extent across the plate / extent along it)")
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    # med/N captions sit at dmax*1.02, which collided with the upper-right stats box — give more headroom
    # and move the box left of them.
    ax.set_ylim(top=dmax*1.42); kt_stats.add_group_stats(ax, g, list(COL), loc="upper left")
    ax.set_title("Kinetochore DISTORTION along the spindle axis, by state (phase-matched)", loc="left", fontweight="bold", fontsize=11)
    ax.text(0.0, -0.145, PHASE_MATCH_NOTE, transform=ax.transAxes, fontsize=7, color="#555", va="top")
    _save(fig, "G6ten_strain_by_state", "spindle-axis distortion by state — " + PHASE_MATCH_NOTE,
          header=["label","distortion"], rows=[[k, round(float(v),5)] for k in COL for v in g.get(k, [])])

    # 3) TIME: spindle strain over mitotic progress, per state (trajectory bands)
    fig, ax = plt.subplots(figsize=(7.8, 5.2))
    for k in COL:
        rs = [r for r in R if r["label"] == k and r["progress"] != "" and r.get("distortion") not in (None, "")]
        band(ax, [float(r["progress"]) for r in rs], [float(r["distortion"]) for r in rs], COL[k], f"{k} (n={len(rs)})")
    ax.axvline(0, ls=":", color="#3b6fb6"); ax.axvline(1, ls="--", color="#d1495b")
    ax.axhline(1.0, color="#888", ls=":", lw=1.0)
    ax.set_xlabel("mitotic progress (0=metaphase onset, 1=anaphase onset)")
    ax.set_ylabel("distortion along the spindle axis (extent across the plate / extent along it)")
    ax.set_title("Kinetochore DISTORTION along the spindle axis over mitosis (median ± IQR)", loc="left", fontweight="bold", fontsize=10.5)
    ax.legend(fontsize=8)
    _save(fig, "G6ten_strain_over_time", "spindle-axis distortion over mitosis",
          header=["label","progress","distortion"],
          rows=[[k, round(float(r["progress"]),5), round(float(r["distortion"]),5)]
                for k in COL for r in R if r["label"]==k and r["progress"] != "" and r.get("distortion") not in (None, "")])

    # 4) EQUIVALENT k-k / tension for polar from calibration, vs paired actual k-k — violin + over time
    # USER 2026-08-05: this compared polar EQUIVALENT k-k (the fitted constant) against paired MEASURED
    # k-k. Two different quantities sharing a unit, so the printed "polar/paired" ratio was not physical.
    # Both sides are now the same measurement — each kinetochore against its own loading axis. It no longer
    # depends on the calibration succeeding, so it is not gated on a_fit either.
    if True:
        polar = [r for r in R if r["label"] == "polar"]
        eqkk = col(polar, "distortion")
        paired_kk = col([r for r in R if r["label"] == "paired"], "distortion")
        g2 = {"paired": [v for v in paired_kk if np.isfinite(v)],
              "polar": [v for v in eqkk if np.isfinite(v)]}
        fig, ax = plt.subplots(figsize=(6.2, 5.0)); order2 = list(g2); dmax = max(max(v) for v in g2.values())
        for i, k in enumerate(order2):
            d = g2[k]; c = COL["paired"] if "paired" in k else COL["polar"]
            lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0)
            ax.scatter(np.full(len(d), i)+(np.random.RandomState(i).rand(len(d))-0.5)*0.2, d, s=lib.VIOLIN_DOT_S, color=c, alpha=lib.VIOLIN_DOT_ALPHA_DENSE, lw=0)
            ax.hlines(np.median(d), i-0.34, i+0.34, color=c, lw=2.4)
            ax.text(i, dmax*1.02, f"med {np.median(d):.2f}\nN={len(d)}", ha="center", va="bottom", fontsize=7.5)
        ax.axhline(1.0, color="#888", ls=":", lw=1.0)
        ax.set_xticks([0, 1]); ax.set_xticklabels(order2, fontsize=8.5)
        ax.set_ylabel("distortion along the spindle axis (extent across the plate / extent along it)")
        try: p = st.mannwhitneyu(g2[order2[0]], g2[order2[1]])[1]
        except Exception: p = np.nan
        rel = np.median(g2[order2[1]]) / np.median(g2[order2[0]])
        ax.set_title(f"Polar vs paired kinetochore DISTORTION (MW p={p:.2g}; polar/paired={rel:.2f}×)", loc="left", fontweight="bold", fontsize=9.5)
        _save(fig, "G6ten_equivalent_kk", "polar vs paired spindle-axis distortion",
              header=["group","distortion"], rows=[[k, round(float(v),5)] for k in order2 for v in g2.get(k, [])])

        # over time
        fig, ax = plt.subplots(figsize=(7.8, 5.2))
        pol = [r for r in R if r["label"] == "polar" and r["progress"] != "" and r.get("distortion") not in (None, "")]
        band(ax, [float(r["progress"]) for r in pol], [float(r["distortion"]) for r in pol], COL["polar"], "polar")
        pr = [r for r in R if r["label"] == "paired" and r["progress"] != "" and r.get("distortion") not in (None, "")]
        band(ax, [float(r["progress"]) for r in pr], [float(r["distortion"]) for r in pr], COL["paired"], "paired")
        ax.axvline(0, ls=":", color="#3b6fb6"); ax.axvline(1, ls="--", color="#d1495b")
        ax.axhline(1.0, color="#888", ls=":", lw=1.0)
        ax.set_xlabel("mitotic progress (0=metaphase, 1=anaphase)")
        ax.set_ylabel("distortion along the spindle axis (extent across the plate / extent along it)")
        ax.set_title("Kinetochore DISTORTION over mitosis: polar vs paired", loc="left", fontweight="bold", fontsize=10)
        ax.legend(fontsize=8)
        _save(fig, "G6ten_equivalent_kk_over_time", "spindle-axis distortion over mitosis, polar vs paired",
              header=["group","progress","distortion"],
              rows=[["polar", round(float(r["progress"]),5), round(float(r["distortion"]),5)] for r in pol]
                   + [["paired", round(float(r["progress"]),5), round(float(r["distortion"]),5)] for r in pr])

        # 5) does the sisterless chromosome's LENGTH set its polar KT's tension?  (fig 498)
        # Restored 2026-07-27: it had dropped out of this script and was going stale in the deck. Window is
        # METAPHASE->ANAPHASE (the phase the question is about); one point per cell, median strain.
        ph = phase_times(sorted({r["batch"] for r in R}))
        clen = collections.defaultdict(list)
        for r in csv.DictReader(open(f"{ROOT}/annotations/KT_CHROMO_ANALYSIS_20260723.csv")):
            try: clen[r["batch"]].append((int(r["frame"]), float(r["length_um"])))
            except Exception: pass
        xs, ys = [], []
        for b in sorted({r["batch"] for r in R if r["label"] == "polar"}):
            mt, at = ph.get(b, (None, None))
            sel = [float(r["distortion"]) for r in R
                   if r["batch"] == b and r["label"] == "polar" and r["t_sec"] != ""
                   and r.get("distortion") not in (None, "")
                   and mt is not None and at is not None and mt <= float(r["t_sec"]) <= at]
            if len(sel) < 3 or b not in clen: continue
            xs.append(sorted(clen[b])[0][1]); ys.append(float(np.median(sel)))
        if len(xs) >= 6:
            xs = np.array(xs); ys = np.array(ys)
            rho, pv = st.spearmanr(xs, ys); rr, pp = st.pearsonr(xs, ys)
            fig, ax = plt.subplots(figsize=(6.8, 5.2))
            ax.scatter(xs, ys, s=52, color=COL["polar"], alpha=0.85, edgecolor="white", lw=0.4)
            if pv < 0.05:
                bb, aa = np.polyfit(xs, ys, 1); xf = np.linspace(xs.min(), xs.max(), 20)
                ax.plot(xf, aa + bb * xf, "-", color=COL["polar"], lw=2.0)
            ax.text(0.98, 0.98, f"Spearman rho={rho:.2f}, p={pv:.2g}\nPearson r={rr:.2f}, p={pp:.2g}\nN={len(xs)} polar cells",
                    transform=ax.transAxes, ha="right", va="top", fontsize=7.5, family="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
            ax.set_xlabel("sisterless chromosome length (µm; first chromosome-line annotation)")
            ax.set_ylabel("polar-KT distortion along the spindle axis (extent across the plate / extent along it)")
            ax.axhline(1.0, color="#888", ls=":", lw=1.0)
            ax.set_title(f"Does chromosome length set polar-KT tension?  — {'relationship' if pv < 0.05 else 'no relationship'} "
                         f"(metaphase to anaphase)", loc="left", fontweight="bold", fontsize=10)
            _save(fig, "G6ten_chromolen_vs_tension", "chromosome length vs polar KT spindle-axis distortion",
                  header=["chromosome_length_um","polar_distortion"],
                  rows=[[round(float(a),5), round(float(b),5)] for a, b in zip(xs, ys)])

    # relative tension summary (dimensionless strain ratio + flagged absolute force)
    _pv = [float(r["distortion"]) for r in R if r["label"] == "paired" and r.get("distortion") not in (None, "")]
    _ov = [float(r["distortion"]) for r in R if r["label"] == "polar" and r.get("distortion") not in (None, "")]
    if _pv and _ov:
        mp, mpo = np.median(_pv), np.median(_ov)
        print(f"\n  RELATIVE DISTORTION (median spindle-axis distortion): polar/paired = {mpo/mp:.2f} "
              f"(polar {mpo:.2f}, paired {mp:.2f})")
    if a_fit is not None:
        print(f"  calibration k-k = {a_fit:.2f} + {b_fit:.3f}*strain (from sisters)")
        print(f"  ABSOLUTE (illustrative, κ={KAPPA_PN_PER_UM} pN/µm, rest k-k~0.8µm): flagged assumption-dependent")
    print("done tension")
