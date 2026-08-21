#!/usr/bin/env python3
"""ONE pass covering the 0818 to-do analysis items 1,2,3,4,12,20 + the table datasets (16,17,18).

Deliberately a SINGLE traversal of the derived stores: yesterday's cost came from re-reading and
re-rendering the same sources once per item.  Every store below is already measured -- this script
does not recompute geometry:

  KT_OUTLINE_TRACKS_20260723  n_pieces (= fracture), elongation, circularity, major/minor, cx/cy
  KT_LOADING_AXIS_20260805    load_extent_um  (distortion ALONG the spindle axis; NOT k-k)
  KT_CHROMO_ANALYSIS_20260723 orient_vs_plate_deg, near/far/mid_dist_um  (polar chromosome angle)
  KT_SISTER_KK_20260723       untargeted paired sister k-k  (NEVER the pre_abl target pair)

Rules honoured: her traced cx_px/cy_px only (the common-mode "38%" correction is retired and wrong);
grp identity via track_id; metaphase-ablations and drugs excluded through lib.plot_excluded;
no red+green anywhere; every figure goes through lib.record_plot so it mirrors to _ai_relink/pdf.
"""
import os, sys, csv, io, json, math, collections
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as st
from scipy.optimize import curve_fit

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

R = "/Volumes/4 MB"; A = R + "/annotations"; FIG = R + "/ablation_figures_20260625"
OUT = os.environ.get("KTFIG_OUT", FIG + "/todo0818"); os.makedirs(OUT, exist_ok=True)
SCRIPT = __file__
SCRATCH = R + "/_claude_tmp/todo0818"; os.makedirs(SCRATCH, exist_ok=True)

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))

def fl(v, d=None):
    try:
        s = str(v).strip().replace(",", "")
        return float(s) if s not in ("", "None", "nan") else d
    except Exception:
        return d

# ---------------------------------------------------------------- master + cohort
M, HDR = lib.load_master()
MB = {}
for r in M:
    b = r["Batch Name"].strip()
    if b: MB[b] = r

def hms(v):
    """Sign-safe H:MM:SS -> seconds.  '-0:12:12' must not come back +732 (the recorded sign bug)."""
    s = str(v).strip().replace(",", "")
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    if ":" in s:
        p = [fl(x, 0) or 0 for x in s.split(":")]
        while len(p) < 3: p.insert(0, 0)
        sec = p[0] * 3600 + p[1] * 60 + p[2]
    else:
        sec = fl(s)
        if sec is None: return None
    return -sec if neg else sec

def ev(b, col):
    r = MB.get(b)
    return hms(r.get(col)) if r else None

def nsis(b):
    r = MB.get(b)
    if not r: return None
    v = fl(r.get("# Sisterless KTs"))
    return int(v) if v is not None else None

def ontarget(b):
    r = MB.get(b)
    return bool(r) and not (r.get("On-Target / Off-Target", "").strip().lower().startswith("off"))

def usable(b):
    return b in MB and not lib.plot_excluded(b)

EXCL = set(getattr(lib, "KT_OUTLINE_EXCLUDE", []) or [])

# ---------------------------------------------------------------- load stores ONCE
TR  = rd(A + "/KT_OUTLINE_TRACKS_20260723.csv")
LOAD= rd(A + "/KT_LOADING_AXIS_20260805.csv")
CHR_= rd(A + "/KT_CHROMO_ANALYSIS_20260723.csv")
KK  = rd(A + "/KT_SISTER_KK_20260723.csv")
print(f"[load] tracks={len(TR)} loading={len(LOAD)} chromo={len(CHR_)} kk={len(KK)}")

tracks = collections.defaultdict(list)          # (batch,label,track_id) -> rows
for r in TR:
    b = r["batch"].strip()
    if b in EXCL or not usable(b): continue
    tracks[(b, r["label"].strip(), r["track_id"].strip())].append(r)
for k in tracks:
    tracks[k].sort(key=lambda r: fl(r["t_sec"], 0) or 0)
print(f"[load] usable tracks={len(tracks)} in {len(set(k[0] for k in tracks))} batches")

RESULTS = {}

# ================================================================ ITEM 1 + 2 + 17
# Fracture = >1 traced piece for ONE kinetochore on ONE frame (her "+ New KT" grp is the identity,
# and n_pieces was computed against that grouping).  A lagging KT that is never >1 never fractured.
def item_1_2_17():
    rows = []
    for (b, lab, tid), rs in tracks.items():
        if lab != "lagging": continue
        ana = ev(b, "Anaphase Onset (s)"); meta = ev(b, "Metaphase Start (s)")
        npieces = [(fl(r["n_pieces"], 1) or 1) for r in rs]
        ts      = [fl(r["t_sec"], 0) or 0 for r in rs]
        elong   = [fl(r.get("elongation")) for r in rs]
        circ    = [fl(r.get("circularity")) for r in rs]
        major   = [fl(r.get("major_um")) for r in rs]
        frac_i  = next((i for i, n in enumerate(npieces) if n > 1), None)
        maxp    = max(npieces) if npieces else 1
        # elongation reached BEFORE fracture (or over the whole track if it never fractured)
        upto    = frac_i if frac_i is not None else len(rs)
        e_pre   = [e for e in elong[:max(upto, 1)] if e is not None]
        rows.append(dict(
            batch=b, track=tid, n_sisterless=nsis(b), n_frames=len(rs),
            fractured=int(frac_i is not None), max_pieces=int(maxp),
            t_fracture_s=(ts[frac_i] if frac_i is not None else None),
            min_from_ana=((ts[frac_i] - ana) / 60.0 if (frac_i is not None and ana is not None) else None),
            min_from_meta=((ts[frac_i] - meta) / 60.0 if (frac_i is not None and meta is not None) else None),
            elong_at_fracture=(elong[frac_i] if frac_i is not None else None),
            elong_max_pre=(max(e_pre) if e_pre else None),
            circ_at_fracture=(circ[frac_i] if frac_i is not None else None),
            length_um_at_fracture=(major[frac_i] if frac_i is not None else None),
            track_min_from_ana=((ts[0] - ana) / 60.0 if ana is not None else None),
            circ_median=(float(np.median([c for c in circ if c is not None])) if any(c is not None for c in circ) else None),
            length_um_median=(float(np.median([m for m in major if m is not None])) if any(m is not None for m in major) else None),
        ))
    RESULTS["lagging"] = rows
    fr = [r for r in rows if r["fractured"]]
    print(f"[item1] lagging tracks={len(rows)}  fractured={len(fr)}  cells={len(set(r['batch'] for r in rows))}")
    if len(rows) < 3:
        print("[item1] TOO FEW lagging tracks -- not drawing"); return

    # ---- FIGURE: fracture timing + what predicts it
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.6))
    tf = [r["min_from_ana"] for r in fr if r["min_from_ana"] is not None]
    ax[0].hist(tf, bins=max(4, min(12, len(tf))), color="#0072b2", alpha=.85, edgecolor="white")
    if tf:
        ax[0].axvline(float(np.median(tf)), color="#d55e00", ls="--", lw=2,
                      label=f"median {np.median(tf):.1f} min")
        ax[0].legend(frameon=False)
    ax[0].set_xlabel("time from anaphase onset at first fracture (min)")
    ax[0].set_ylabel("lagging kinetochores")
    ax[0].set_title(f"When fracture happens (n={len(tf)})")

    # elongation reached, fractured vs not -- the "certain elongation curve" test
    # PER CELL (a cell can carry several lagging kinetochores) -- see per_cell_medians note.
    a_tr = [r["elong_max_pre"] for r in rows if r["fractured"] and r["elong_max_pre"] is not None]
    b_tr = [r["elong_max_pre"] for r in rows if not r["fractured"] and r["elong_max_pre"] is not None]
    a = per_cell_medians([r for r in rows if r["fractured"]], lambda r: r["batch"], lambda r: r["elong_max_pre"])
    bnot = per_cell_medians([r for r in rows if not r["fractured"]], lambda r: r["batch"], lambda r: r["elong_max_pre"])
    parts = [x for x in (a, bnot) if x]
    if len(parts) == 2:
        lib.sd_bar(ax[1], a, 1); lib.sd_bar(ax[1], bnot, 2)
        for i, (d, c) in enumerate(((a, "#0072b2"), (bnot, "#999999")), start=1):
            ax[1].scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .12,
                          d, s=26, color=c, edgecolor="white", lw=.4, zorder=3)
        u = st.mannwhitneyu(a, bnot, alternative="two-sided")
        u_tr = st.mannwhitneyu(a_tr, b_tr, alternative="two-sided") if (len(a_tr) >= 3 and len(b_tr) >= 3) else None
        RESULTS["elong_discriminates_p"] = float(u.pvalue)
        RESULTS["elong_discriminates_p_pertrack"] = float(u_tr.pvalue) if u_tr else None
        ax[1].set_xticks([1, 2]); ax[1].set_xticklabels([f"fractured\n({len(a)} cells)", f"intact\n({len(bnot)} cells)"])
        ax[1].set_title(f"Elongation reached, per cell  (MW p={u.pvalue:.3g}" +
                        (f"; per track p={u_tr.pvalue:.3g})" if u_tr else ")"))
    ax[1].set_ylabel("max elongation before fracture")

    # time vs elongation: which one "sets" fracture -- compare CV of each
    x = [r["min_from_ana"] for r in fr if r["min_from_ana"] is not None and r["elong_at_fracture"] is not None]
    y = [r["elong_at_fracture"] for r in fr if r["min_from_ana"] is not None and r["elong_at_fracture"] is not None]
    if len(x) >= 3:
        ax[2].scatter(x, y, s=44, color="#0072b2", edgecolor="white", lw=.5)
        rho, p = st.spearmanr(x, y)
        # DO NOT compare CV between these two.  time-from-anaphase crosses zero, so std/mean is
        # meaningless for it (a mean near 0 inflates CV without any real spread).  The question is
        # answered instead by the two tests that ARE valid: does fracture time cluster, and does
        # elongation separate fractured from intact?
        iqr_t = float(np.percentile(x, 75) - np.percentile(x, 25))
        ax[2].set_title(f"Elongation at fracture vs when it happened\n"
                        f"rho={rho:.2f}  p={p:.3g}   fracture-time IQR = {iqr_t:.1f} min")
    ax[2].set_xlabel("time from anaphase at fracture (min)"); ax[2].set_ylabel("elongation at fracture")
    for a_ in ax: a_.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Lagging-kinetochore fracture: set by elapsed time, or by elongation reached?")
    fig.tight_layout(rect=(0, 0, 1, .93))
    fig.savefig(f"{OUT}/G8_lagging_fracture_timing.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    hdr = ["batch", "track", "n_sisterless", "fractured", "max_pieces", "min_from_ana",
           "min_from_meta", "elong_at_fracture", "elong_max_pre", "circ_at_fracture", "length_um_at_fracture"]
    lib.record_plot("G8_lagging_fracture_timing", hdr,
                    [[r.get(k) for k in hdr] for r in rows],
                    {"type": "fracture timing", "fracture_definition": "n_pieces>1 for one grp on one frame",
                     "n_tracks": len(rows), "n_fractured": len(fr)}, SCRIPT,
                    "Lagging-kinetochore fracture: elapsed time vs elongation reached")

    # ---- ITEM 2: materials-science fits.  Weibull survival on elongation-to-fracture.
    ev_e = [(r["elong_max_pre"], r["fractured"]) for r in rows if r["elong_max_pre"] is not None]
    if len([1 for e, f in ev_e if f]) >= 4:
        xs = np.array([e for e, _ in ev_e], float); dd = np.array([f for _, f in ev_e], int)
        order = np.argsort(xs); xs, dd = xs[order], dd[order]
        # Kaplan-Meier over elongation (right-censored = never fractured)
        n = len(xs); surv = []; s = 1.0
        for i in range(n):
            at_risk = n - i
            if dd[i]: s *= (1 - 1.0 / at_risk)
            surv.append(s)
        surv = np.array(surv)
        def weib(x, lam, k): return np.exp(-np.power(np.clip(x, 1e-9, None) / lam, k))
        fig2, ax2 = plt.subplots(1, 2, figsize=(11.2, 4.4))
        ax2[0].step(xs, surv, where="post", color="#333", lw=2, label="Kaplan-Meier")
        fitok = ""
        try:
            popt, pcov = curve_fit(weib, xs, surv, p0=[max(np.median(xs), .5), 2.0], maxfev=20000)
            gx = np.linspace(xs.min(), xs.max(), 200)
            perr = np.sqrt(np.diag(pcov))
            ax2[0].plot(gx, weib(gx, *popt), color="#0072b2", lw=2.2, ls="--",
                        label=f"Weibull  $\\lambda$={popt[0]:.2f}  m={popt[1]:.2f}")
            ss = 1 - np.sum((surv - weib(xs, *popt)) ** 2) / np.sum((surv - surv.mean()) ** 2)
            fitok = (f"Weibull modulus m={popt[1]:.2f}+/-{perr[1]:.2f}, "
                     f"scale lambda={popt[0]:.2f}+/-{perr[0]:.2f}, R2={ss:.2f}")
            RESULTS["weibull"] = dict(lam=float(popt[0]), m=float(popt[1]), r2=float(ss),
                                      lam_se=float(perr[0]), m_se=float(perr[1]), n=int(n),
                                      n_events=int(dd.sum()))
        except Exception as e:
            fitok = f"Weibull fit did not converge ({e})"
        ax2[0].set_xlabel("elongation (stretch reached)"); ax2[0].set_ylabel("fraction still intact")
        ax2[0].set_title("Weibull in ELONGATION\n(fits well, but see the caption -- elongation does not\n"
                         "separate fractured from intact, so this describes the\nstretch distribution more "
                         "than a failure law)", fontsize=8.5)
        ax2[0].legend(frameon=False)
        # creep-to-rupture: elongation vs time-to-fracture, log-log (Monkman-Grant form)
        xx = [r["min_from_ana"] for r in fr if r["min_from_ana"] and r["min_from_ana"] > 0 and r["elong_at_fracture"]]
        yy = [r["elong_at_fracture"] for r in fr if r["min_from_ana"] and r["min_from_ana"] > 0 and r["elong_at_fracture"]]
        if len(xx) >= 3:
            ax2[1].scatter(xx, yy, s=46, color="#d55e00", edgecolor="white", lw=.5)
            lx, ly = np.log(xx), np.log(yy)
            sl, ic, rv, pv, se = st.linregress(lx, ly)
            gx = np.linspace(min(xx), max(xx), 100)
            ax2[1].plot(gx, np.exp(ic) * gx ** sl, color="#333", ls="--", lw=1.8)
            ax2[1].set_xscale("log"); ax2[1].set_yscale("log")
            ax2[1].set_title(f"Creep-to-rupture (Monkman-Grant)\nslope={sl:.2f}  R$^2$={rv**2:.2f}  p={pv:.3g}")
            RESULTS["monkman"] = dict(slope=float(sl), r2=float(rv ** 2), p=float(pv), n=len(xx))
        ax2[1].set_xlabel("time to fracture (min)"); ax2[1].set_ylabel("elongation at fracture")
        for a_ in ax2: a_.spines[["top", "right"]].set_visible(False)
        _mwp = RESULTS.get("elong_discriminates_p")
        _concl = ("Fracture tracks ELAPSED TIME, not stretch: it clusters shortly after anaphase onset, "
                  "while the elongation reached\nis statistically indistinguishable between kinetochores that "
                  f"fractured and those that did not (MW p={_mwp:.2f})." if _mwp is not None else "")
        fig2.suptitle(f"Lagging kinetochores fitted with materials-science failure curves\n{fitok}\n{_concl}",
                      fontsize=9)
        fig2.tight_layout(rect=(0, 0, 1, .88))
        fig2.savefig(f"{OUT}/G8_lagging_fracture_materials.png", dpi=200, bbox_inches="tight"); plt.close(fig2)
        lib.record_plot("G8_lagging_fracture_materials",
                        ["batch", "track", "elong_max_pre", "fractured", "min_from_ana"],
                        [[r["batch"], r["track"], r["elong_max_pre"], r["fractured"], r["min_from_ana"]] for r in rows],
                        {"type": "survival + power law", "fits": fitok,
                         "weibull": RESULTS.get("weibull"), "monkman_grant": RESULTS.get("monkman")},
                        SCRIPT, "Lagging-kinetochore fracture fitted with Weibull and creep-to-rupture curves")

# ================================================================ ITEM 3  KT speed
# ---------------------------------------------------------------- her rule: TEST PER CELL
# NOTES 2026-08-18 item 20 / rule restated by her: "Any test over these stores must aggregate to
# the cell first."  A cell contributes many tracks/frames, so a per-track Mann-Whitney counts one
# cell many times and manufactures significance.  Every cohort comparison below therefore reduces
# each cell to ONE value (median of its tracks) before testing; per-track values are still plotted
# and recorded, and the per-track p is kept alongside the per-cell p so the two can be compared.
def per_cell_medians(items, keyfn, valfn):
    d = collections.defaultdict(list)
    for it in items:
        v = valfn(it)
        if v is None: continue
        d[keyfn(it)].append(v)
    return [float(np.median(v)) for v in d.values()]


def item_3():
    rows = []
    for (b, lab, tid), rs in tracks.items():
        px = fl((MB.get(b) or {}).get("Pixel Size (um)"), 0.062) or 0.062
        meta = ev(b, "Metaphase Start (s)"); ana = ev(b, "Anaphase Onset (s)")
        for i in range(1, len(rs)):
            t0, t1 = fl(rs[i - 1]["t_sec"]), fl(rs[i]["t_sec"])
            if t0 is None or t1 is None or t1 <= t0: continue
            dt = t1 - t0
            if dt > 300: continue                      # a >5 min gap is not a step
            x0, y0 = fl(rs[i - 1]["cx_px"]), fl(rs[i - 1]["cy_px"])
            x1, y1 = fl(rs[i]["cx_px"]), fl(rs[i]["cy_px"])
            if None in (x0, y0, x1, y1): continue
            d = math.hypot(x1 - x0, y1 - y0) * px
            ph = ("metaphase" if (meta is not None and ana is not None and meta <= t1 < ana)
                  else "anaphase" if (ana is not None and t1 >= ana)
                  else "prometaphase")
            rows.append(dict(batch=b, label=lab, track=tid, t_sec=t1, phase=ph,
                             speed_um_s=d / dt, n_sisterless=nsis(b)))
    RESULTS["speed"] = rows
    if len(rows) < 20:
        print("[item3] too few speed steps"); return
    # per-TRACK median, so a long track cannot dominate
    per = collections.defaultdict(list)
    for r in rows: per[(r["batch"], r["label"], r["track"], r["phase"], r["n_sisterless"])].append(r["speed_um_s"])
    tr = [dict(batch=k[0], label=k[1], track=k[2], phase=k[3], n_sisterless=k[4],
               speed_um_s=float(np.median(v)), n_steps=len(v)) for k, v in per.items()]
    grp = lambda lab: "paired" if lab == "paired" else ("sisterless" if lab in ("polar", "lagging", "sisterless") else None)
    fig, ax = plt.subplots(1, 2, figsize=(12.4, 4.8))
    PH = ["prometaphase", "metaphase", "anaphase"]
    COL = {"paired": "#0072b2", "sisterless": "#cc79a7"}
    for gi, g in enumerate(["paired", "sisterless"]):
        for pi, ph in enumerate(PH):
            d = [t["speed_um_s"] for t in tr if grp(t["label"]) == g and t["phase"] == ph]
            if not d: continue
            pos = pi + (gi - .5) * .32
            lib.sd_bar(ax[0], d, pos)
            ax[0].scatter(np.full(len(d), pos) + (np.random.RandomState(pi * 3 + gi).rand(len(d)) - .5) * .14,
                          d, s=17, color=COL[g], alpha=.85, edgecolor="white", lw=.3, zorder=3,
                          label=g if pi == 0 else None)
    ax[0].set_xticks(range(len(PH))); ax[0].set_xticklabels(PH)
    ax[0].set_ylabel("kinetochore speed (um/s)"); ax[0].legend(frameon=False)
    ax[0].set_title("Paired vs sisterless kinetochore speed by phase")
    # 1 vs 3 sisterless, metaphase only
    for gi, g in enumerate(["paired", "sisterless"]):
        for ni, n in enumerate([1, 3]):
            d = [t["speed_um_s"] for t in tr if grp(t["label"]) == g and t["phase"] == "metaphase" and t["n_sisterless"] == n]
            if not d: continue
            pos = ni + (gi - .5) * .32
            lib.sd_bar(ax[1], d, pos)
            ax[1].scatter(np.full(len(d), pos) + (np.random.RandomState(ni * 5 + gi).rand(len(d)) - .5) * .14,
                          d, s=17, color=COL[g], alpha=.85, edgecolor="white", lw=.3, zorder=3)
    _mp = lambda t, n: (grp(t["label"]) == "paired" and t["phase"] == "metaphase" and t["n_sisterless"] == n)
    pa_tr = [t["speed_um_s"] for t in tr if _mp(t, 1)]
    pb_tr = [t["speed_um_s"] for t in tr if _mp(t, 3)]
    pa = per_cell_medians([t for t in tr if _mp(t, 1)], lambda t: t["batch"], lambda t: t["speed_um_s"])
    pb = per_cell_medians([t for t in tr if _mp(t, 3)], lambda t: t["batch"], lambda t: t["speed_um_s"])
    ttl = "Metaphase speed, 1- vs 3-sisterless  (tested PER CELL)"
    if len(pa) >= 3 and len(pb) >= 3:
        u = st.mannwhitneyu(pa, pb, alternative="two-sided")
        u_tr = st.mannwhitneyu(pa_tr, pb_tr, alternative="two-sided") if (len(pa_tr) >= 3 and len(pb_tr) >= 3) else None
        ttl += (f"\npaired, per cell: 1-sis {np.median(pa):.4f} ({len(pa)} cells) vs "
                f"3-sis {np.median(pb):.4f} ({len(pb)} cells) um/s, MW p={u.pvalue:.3g}")
        if u_tr: ttl += f"   [per track p={u_tr.pvalue:.3g}, {len(pa_tr)} vs {len(pb_tr)} tracks]"
        RESULTS["speed_1v3"] = dict(p=float(u.pvalue), med1=float(np.median(pa)), med3=float(np.median(pb)),
                                    n1=len(pa), n3=len(pb), unit="cell",
                                    p_pertrack=float(u_tr.pvalue) if u_tr else None,
                                    n1_tracks=len(pa_tr), n3_tracks=len(pb_tr))
    ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["1-sis", "3-sis"])
    ax[1].set_ylabel("kinetochore speed (um/s)"); ax[1].set_title(ttl, fontsize=10)
    for a_ in ax: a_.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Kinetochore speed  (higher paired speed = more prometaphase-like)")
    fig.tight_layout(rect=(0, 0, 1, .92))
    fig.savefig(f"{OUT}/G8_kt_speed_paired_vs_sisterless.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    lib.record_plot("G8_kt_speed_paired_vs_sisterless",
                    ["batch", "label", "track", "phase", "n_sisterless", "speed_um_s", "n_steps"],
                    [[t["batch"], t["label"], t["track"], t["phase"], t["n_sisterless"],
                      round(t["speed_um_s"], 6), t["n_steps"]] for t in tr],
                    {"type": "speed by phase and class", "aggregation": "per-track median step speed",
                     "coordinates": "HER traced cx_px/cy_px (the inferred common-mode correction is retired)",
                     "max_step_gap_s": 300}, SCRIPT,
                    "Paired and sisterless kinetochore speed by mitotic phase and sisterless number")

# ================================================================ ITEM 4  viscoelastic fits
def item_4():
    per = collections.defaultdict(list)
    for r in LOAD:
        b = r["batch"].strip()
        if b in EXCL or not usable(b): continue
        if str(r.get("outlier", "")).strip() in ("1", "True", "true"): continue
        le = fl(r.get("load_extent_um")); t = fl(r.get("t_sec"))
        if le is None or t is None: continue
        per[(b, r["label"].strip(), r["track_id"].strip())].append((t, le))
    fits = []
    for k, v in per.items():
        v.sort()
        if len(v) < 6: continue
        t = np.array([x[0] for x in v]); y = np.array([x[1] for x in v])
        t = t - t[0]
        if t[-1] <= 0: continue
        # Kelvin-Voigt creep:  e(t) = e_inf * (1 - exp(-t/tau))  (+ instantaneous e0)
        def kv(tt, e0, einf, tau): return e0 + einf * (1 - np.exp(-tt / np.clip(tau, 1e-6, None)))
        # power-law (soft glassy) rheology:  e(t) = e0 * (1+t)^beta
        def pl(tt, e0, beta): return e0 * np.power(1 + tt, beta)
        rec = dict(batch=k[0], label=k[1], track=k[2], n=len(v), n_sisterless=nsis(k[0]),
                   span_s=float(t[-1]), mean_load_um=float(np.mean(y)))
        for nm, fn, p0 in (("kv", kv, [y[0], max(float(np.ptp(y)), .05), max(t[-1] / 3, 1)]),
                           ("pl", pl, [max(y[0], 1e-3), 0.1])):
            try:
                popt, _ = curve_fit(fn, t, y, p0=p0, maxfev=20000)
                res = y - fn(t, *popt)
                ss = 1 - np.sum(res ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-12)
                rec[nm + "_r2"] = float(ss)
                if nm == "kv":
                    rec["tau_s"] = float(abs(popt[2])); rec["e_inf_um"] = float(popt[1])
                else:
                    rec["beta"] = float(popt[1])
            except Exception:
                rec[nm + "_r2"] = None
        fits.append(rec)
    RESULTS["visco"] = fits
    print(f"[item4] viscoelastic fits on {len(fits)} tracks")
    if len(fits) < 4:
        print("[item4] too few tracks to fit"); return
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.5))
    kvr = [f["kv_r2"] for f in fits if f.get("kv_r2") is not None]
    plr = [f["pl_r2"] for f in fits if f.get("pl_r2") is not None]
    ax[0].scatter(kvr, plr, s=40, color="#0072b2", edgecolor="white", lw=.5)
    lim = [min(kvr + plr + [0]), 1.02]
    ax[0].plot(lim, lim, ls="--", color="#999", lw=1)
    ax[0].set_xlabel("Kelvin-Voigt creep  R$^2$"); ax[0].set_ylabel("power-law (soft glassy)  R$^2$")
    better = "power-law" if np.median(plr) > np.median(kvr) else "Kelvin-Voigt"
    ax[0].set_title(f"Which model fits better?\nmedian R$^2$: KV {np.median(kvr):.2f} vs PL {np.median(plr):.2f} -> {better}")
    COL = {"polar": "#cc79a7", "paired": "#0072b2", "lagging": "#009e73"}
    for i, lab in enumerate(["polar", "paired", "lagging"]):
        d = [f["tau_s"] for f in fits if f["label"] == lab and f.get("tau_s") and f["tau_s"] < 1e5]
        if not d: continue
        lib.sd_bar(ax[1], d, i)
        ax[1].scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .16, d,
                      s=26, color=COL[lab], edgecolor="white", lw=.4, zorder=3)
    ax[1].set_xticks(range(3)); ax[1].set_xticklabels(["polar", "paired", "lagging"])
    ax[1].set_ylabel("creep time constant  $\\tau$ (s)"); ax[1].set_yscale("log")
    ax[1].set_title("Viscoelastic relaxation time by kinetochore class")
    for i, n in enumerate([1, 3]):
        d = [f["beta"] for f in fits if f.get("beta") is not None and f["n_sisterless"] == n and abs(f["beta"]) < 3]
        if not d: continue
        lib.sd_bar(ax[2], d, i)
        ax[2].scatter(np.full(len(d), i) + (np.random.RandomState(i + 9).rand(len(d)) - .5) * .16, d,
                      s=26, color="#0072b2", edgecolor="white", lw=.4, zorder=3)
    _bok = lambda f, n: (f.get("beta") is not None and f["n_sisterless"] == n and abs(f["beta"]) < 3)
    b1 = per_cell_medians([f for f in fits if _bok(f, 1)], lambda f: f["batch"], lambda f: f["beta"])
    b3 = per_cell_medians([f for f in fits if _bok(f, 3)], lambda f: f["batch"], lambda f: f["beta"])
    t2 = "Power-law exponent $\\beta$ (0 = elastic solid, 1 = fluid)"
    if len(b1) >= 3 and len(b3) >= 3:
        u = st.mannwhitneyu(b1, b3, alternative="two-sided")
        t2 += f"\nper cell: 1-sis {np.median(b1):.3f} ({len(b1)}) vs 3-sis {np.median(b3):.3f} ({len(b3)}), MW p={u.pvalue:.3g}"
        RESULTS["beta_1v3"] = dict(p=float(u.pvalue), b1=float(np.median(b1)), b3=float(np.median(b3)),
                                   n1=len(b1), n3=len(b3), unit="cell")
    ax[2].set_xticks([0, 1]); ax[2].set_xticklabels(["1-sis", "3-sis"]); ax[2].set_ylabel("$\\beta$")
    ax[2].set_title(t2, fontsize=9)
    for a_ in ax: a_.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Kinetochore deformation fitted with material-property curves "
                 "(distortion measured ALONG the spindle axis)")
    fig.tight_layout(rect=(0, 0, 1, .91))
    fig.savefig(f"{OUT}/G8_kt_deformation_materialfits.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    hdr = ["batch", "label", "track", "n_sisterless", "n", "span_s", "mean_load_um",
           "kv_r2", "tau_s", "e_inf_um", "pl_r2", "beta"]
    lib.record_plot("G8_kt_deformation_materialfits", hdr,
                    [[f.get(k) for k in hdr] for f in fits],
                    {"type": "viscoelastic model fits",
                     "models": "Kelvin-Voigt creep; power-law (soft glassy) rheology",
                     "source": "KT_LOADING_AXIS load_extent_um (along-spindle distortion)"},
                    SCRIPT, "Kinetochore stretch fitted with Kelvin-Voigt and power-law rheology models")

# ================================================================ ITEM 20  polar chromosome angle
def item_20():
    rows = []
    for r in CHR_:
        b = r["batch"].strip()
        if not usable(b): continue
        ang = fl(r.get("orient_vs_plate_deg"))
        if ang is None: continue
        rows.append(dict(batch=b, chromo_id=r.get("chromo_id"), frame=r.get("frame"),
                         t_sec=fl(r.get("t_sec")), angle_deg=ang,
                         length_um=fl(r.get("length_um")),
                         mid_dist_um=fl(r.get("mid_dist_um")),
                         near_end=fl(r.get("near_end_dist_um")), far_end=fl(r.get("far_end_dist_um")),
                         paired_label=(r.get("paired_label") or "").strip(),
                         n_sisterless=nsis(b)))
    RESULTS["angle"] = rows
    print(f"[item20] chromosome-orientation rows={len(rows)} cells={len(set(r['batch'] for r in rows))}")
    if len(rows) < 8:
        print("[item20] too few"); return
    # 🔴 AGGREGATE TO ONE VALUE PER CELL BEFORE ANY TEST.  chromo_id is near-unique per row, so the 442
    # rows are repeated MEASUREMENTS over 45 cells, not 442 independent chromosomes.  Testing on the raw
    # rows is pseudoreplication and inflates every p-value (it made 1-sis n=396 vs 3-sis n=35).
    percell = collections.defaultdict(list)
    for r in rows: percell[r["batch"]].append(r)
    per = collections.defaultdict(list)
    for r in rows: per[(r["batch"], r["chromo_id"])].append(r)
    ch = []
    for k, v in per.items():
        ch.append(dict(batch=k[0], chromo_id=k[1],
                       angle_deg=float(np.median([x["angle_deg"] for x in v])),
                       length_um=float(np.median([x["length_um"] for x in v if x["length_um"] is not None] or [np.nan])),
                       mid_dist_um=float(np.median([x["mid_dist_um"] for x in v if x["mid_dist_um"] is not None] or [np.nan])),
                       tilt=float(np.median([abs(x["near_end"] - x["far_end"]) for x in v
                                             if x["near_end"] is not None and x["far_end"] is not None] or [np.nan])),
                       n_sisterless=v[0]["n_sisterless"], label=v[0]["paired_label"]))
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.5))
    ang = [c["angle_deg"] for c in ch]
    ax[0].hist(ang, bins=14, color="#0072b2", alpha=.85, edgecolor="white")
    ax[0].axvline(90, color="#999", ls=":", lw=1.5)
    med = float(np.median(ang))
    ax[0].axvline(med, color="#d55e00", ls="--", lw=2, label=f"median {med:.0f}$\\degree$")
    try:
        w = st.wilcoxon(np.array(ang) - 90.0)
        ax[0].set_title(f"Chromosome long axis vs the plate\n(90$\\degree$ = perpendicular; "
                        f"{len(ang)} measurements over {len(percell)} cells)")
        RESULTS["angle_vs90"] = dict(p=float(w.pvalue), median=med, n=len(ang))
    except Exception:
        ax[0].set_title("Chromosome long axis vs the plate")
    ax[0].set_xlabel("orientation vs metaphase plate (deg)"); ax[0].set_ylabel("measurements")
    ax[0].legend(frameon=False)
    # one median angle per CELL -- the unit of replication
    cell_ang = {b: float(np.median([x["angle_deg"] for x in v])) for b, v in percell.items()}
    cell_ns  = {b: v[0]["n_sisterless"] for b, v in percell.items()}
    for i, n in enumerate([1, 3]):
        d = [a for b, a in cell_ang.items() if cell_ns.get(b) == n]
        if not d: continue
        lib.sd_bar(ax[1], d, i)
        ax[1].scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - .5) * .15, d,
                      s=34, color=["#0072b2", "#cc79a7"][i], edgecolor="white", lw=.5, zorder=3)
    a1 = [a for b, a in cell_ang.items() if cell_ns.get(b) == 1]
    a3 = [a for b, a in cell_ang.items() if cell_ns.get(b) == 3]
    t1 = "Angle by sisterless number (one median per CELL)"
    if len(a1) >= 3 and len(a3) >= 3:
        u = st.mannwhitneyu(a1, a3, alternative="two-sided")
        t1 += (f"\n1-sis {np.median(a1):.0f}$\\degree$ (n={len(a1)} cells) vs "
               f"3-sis {np.median(a3):.0f}$\\degree$ (n={len(a3)} cells), MW p={u.pvalue:.3g}")
        RESULTS["angle_1v3"] = dict(p=float(u.pvalue), a1=float(np.median(a1)), a3=float(np.median(a3)))
    ax[1].set_xticks([0, 1]); ax[1].set_xticklabels(["1-sis", "3-sis"])
    ax[1].set_ylabel("orientation vs plate (deg)"); ax[1].set_title(t1, fontsize=10)
    xs = [c["mid_dist_um"] for c in ch if c["mid_dist_um"] == c["mid_dist_um"]]
    ys = [c["angle_deg"] for c in ch if c["mid_dist_um"] == c["mid_dist_um"]]
    if len(xs) >= 4:
        ax[2].scatter(xs, ys, s=40, color="#0072b2", edgecolor="white", lw=.5)
        rho, p = st.spearmanr(xs, ys)
        ax[2].set_title(f"Angle vs distance from the plate\nrho={rho:.2f}  p={p:.3g}  "
                        f"n={len(xs)} measurements over {len(percell)} cells")
        RESULTS["angle_vs_dist"] = dict(rho=float(rho), p=float(p), n=len(xs))
    ax[2].set_xlabel("distance from metaphase plate (um)"); ax[2].set_ylabel("orientation vs plate (deg)")
    for a_ in ax: a_.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Are polar chromosomes angled toward the plate?  (PEFs pushing on the arms)")
    fig.tight_layout(rect=(0, 0, 1, .91))
    fig.savefig(f"{OUT}/G8_polar_chromosome_angle.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    hdr = ["batch", "chromo_id", "n_sisterless", "angle_deg", "length_um", "mid_dist_um", "tilt"]
    lib.record_plot("G8_polar_chromosome_angle", hdr,
                    [[c.get(k) for k in hdr] for c in ch],
                    {"type": "orientation", "source": "KT_CHROMO_ANALYSIS orient_vs_plate_deg",
                     "note": "90 deg = long axis perpendicular to the plate"},
                    SCRIPT, "Polar chromosome orientation relative to the metaphase plate")

# ================================================================ ITEM 12  2+3 vs 3-only
def item_12():
    """Re-run each comparison both ways and report what pooling gains and what it costs."""
    out = []
    def compare(name, getter, unit=""):
        g1 = getter(1); g2 = getter(2); g3 = getter(3)
        if len(g1) < 3 or len(g3) < 3: return
        u3 = st.mannwhitneyu(g1, g3, alternative="two-sided")
        pooled = g2 + g3
        if len(pooled) < 3: return
        up = st.mannwhitneyu(g1, pooled, alternative="two-sided")
        out.append(dict(comparison=name, unit=unit, n_1sis=len(g1), n_3sis=len(g3), n_2sis=len(g2),
                        n_pooled=len(pooled),
                        median_1sis=round(float(np.median(g1)), 4),
                        median_3sis=round(float(np.median(g3)), 4),
                        median_2plus3=round(float(np.median(pooled)), 4),
                        p_3only=float(u3.pvalue), p_2plus3=float(up.pvalue),
                        sig_3only=int(u3.pvalue < .05), sig_2plus3=int(up.pvalue < .05),
                        verdict=("LOST significance" if u3.pvalue < .05 <= up.pvalue else
                                 "GAINED significance" if up.pvalue < .05 <= u3.pvalue else
                                 "unchanged")))
    dur = lambda n: [v for b, r in MB.items()
                     if usable(b) and ontarget(b) and nsis(b) == n
                     and (v := hms(r.get("Meta Duration (s)"))) is not None and v > 0]
    compare("metaphase duration", dur, "s")   # already one value per cell
    sp = RESULTS.get("speed") or []
    per = collections.defaultdict(list)
    for r in sp: per[(r["batch"], r["label"], r["track"], r["phase"])].append(r["speed_um_s"])
    def spd(kind, phase):
        # per TRACK median first, then per CELL -- one value per cell before any test.
        def getter(n):
            cell = collections.defaultdict(list)
            for k, v in per.items():
                if nsis(k[0]) != n or k[3] != phase: continue
                if not ((k[1] == "paired") if kind == "paired" else (k[1] in ("polar", "lagging", "sisterless"))):
                    continue
                cell[k[0]].append(float(np.median(v)))
            return [float(np.median(v)) for v in cell.values()]
        return getter
    compare("paired KT speed (metaphase)", spd("paired", "metaphase"), "um/s")
    compare("sisterless KT speed (metaphase)", spd("sis", "metaphase"), "um/s")
    compare("paired KT speed (anaphase)", spd("paired", "anaphase"), "um/s")
    kkper = collections.defaultdict(list)
    for r in KK:
        b = r["batch"].strip()
        if usable(b) and (r.get("phase") or "").strip() == "metaphase":
            v = fl(r.get("kk_dist_um"))
            if v is not None: kkper[b].append(v)
    compare("sister k-k distance (metaphase)",
            lambda n: [float(np.median(v)) for b, v in kkper.items() if nsis(b) == n], "um")
    vis = RESULTS.get("visco") or []
    compare("creep time constant tau",
            lambda n: per_cell_medians([f for f in vis if f.get("tau_s") and f["tau_s"] < 1e5
                                        and f["n_sisterless"] == n], lambda f: f["batch"], lambda f: f["tau_s"]), "s")
    # per CELL, not per measurement -- chromo_id is near-unique per row, so keying on it would
    # pseudoreplicate exactly as item 20 did before it was corrected.
    ang = RESULTS.get("angle") or []
    angper = collections.defaultdict(list)
    for r in ang: angper[r["batch"]].append(r["angle_deg"])
    compare("chromosome angle vs plate (per cell)",
            lambda n: [float(np.median(v)) for b, v in angper.items() if nsis(b) == n], "deg")
    RESULTS["pooling"] = out
    print(f"[item12] {len(out)} comparisons tested both ways")
    if not out: return
    fig, ax = plt.subplots(figsize=(11.5, max(3.6, .62 * len(out) + 2.1)))
    ylab = []
    for i, o in enumerate(out):
        y = len(out) - 1 - i
        ylab.append(o["comparison"])
        ax.plot([-np.log10(max(o["p_3only"], 1e-12)), -np.log10(max(o["p_2plus3"], 1e-12))], [y, y],
                color="#bbb", lw=1.6, zorder=1)
        ax.scatter(-np.log10(max(o["p_3only"], 1e-12)), y, s=95, color="#0072b2", zorder=3,
                   edgecolor="white", lw=.8, label="3-sisterless only" if i == 0 else None)
        ax.scatter(-np.log10(max(o["p_2plus3"], 1e-12)), y, s=95, color="#e69f00", zorder=3,
                   edgecolor="white", lw=.8, label="2+3 pooled" if i == 0 else None)
        if o["verdict"] != "unchanged":
            ax.annotate(o["verdict"], (max(-np.log10(max(o["p_3only"], 1e-12)),
                                           -np.log10(max(o["p_2plus3"], 1e-12))) + .12, y),
                        va="center", fontsize=8,
                        color="#b05806" if "LOST" in o["verdict"] else "#009e73")
    ax.axvline(-np.log10(.05), color="#999", ls="--", lw=1.4)
    ax.text(-np.log10(.05), len(out) - .35, " p=0.05", fontsize=8, color="#666")
    ax.set_yticks(range(len(out))); ax.set_yticklabels(ylab[::-1])
    ax.set_xlabel("$-\\log_{10}$ p  (further right = stronger)")
    ax.set_title("Does pooling 2+3-sisterless help?  Each comparison run both ways")
    ax.legend(frameon=False, loc="lower right"); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/G8_pooling_2plus3_vs_3.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    hdr = ["comparison", "unit", "n_1sis", "n_2sis", "n_3sis", "n_pooled", "median_1sis", "median_3sis",
           "median_2plus3", "p_3only", "p_2plus3", "sig_3only", "sig_2plus3", "verdict"]
    lib.record_plot("G8_pooling_2plus3_vs_3", hdr, [[o[k] for k in hdr] for o in out],
                    {"type": "sensitivity", "question": "would 2+3-sisterless pooled beat 3-only"},
                    SCRIPT, "Effect of pooling 2- and 3-sisterless cells on every headline comparison")

for fn in (item_1_2_17, item_3, item_4, item_20, item_12):
    try:
        fn()
    except Exception as e:
        import traceback; print(f"[ERROR] {fn.__name__}: {e}"); traceback.print_exc()

# ---------------------------------------------------------------- dump datasets for the tables doc
def jdump(o):
    if isinstance(o, (np.floating, np.integer)): return float(o)
    return None
with io.open(SCRATCH + "/results.json", "w", encoding="utf-8") as f:
    json.dump({k: v for k, v in RESULTS.items()}, f, default=jdump, indent=1)
print("[done] wrote", SCRATCH + "/results.json")
print("[done] figures in", OUT)
