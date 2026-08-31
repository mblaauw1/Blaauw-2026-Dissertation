#!/usr/bin/env python3
"""Single-sisterless PROMETAPHASE vs triple-sisterless METAPHASE — oscillation, period, k-k.

USER 2026-08-10: "look at the prometaphase data you have for single sisterless. calculate the
oscillation/amplitudes/k-k distances. then plot it with the triple ablation metaphase data in the box plot
format and the model wave format."

WHY THE PAIRING IS THE POINT. A single-sisterless cell spends its prometaphase doing what a triple cell is
still doing during ITS metaphase, so this compares the two on the phase where each is actually congressing,
rather than on the clock. Two comparison SETS are produced from one code path so they stay directly
comparable:

    SET A  metaphase : metaphase      single METAPHASE     vs triple METAPHASE   (the existing comparison)
    SET B  prometaphase : metaphase   single PROMETAPHASE  vs triple METAPHASE   (what she asked for)

WINDOWS, from master, per cell:
    metaphase     [Metaphase Start, Anaphase Onset]
    prometaphase  [NEB Time or first annotated frame, Metaphase Start)  -- restricted to cells whose
                  master "Phase of Ablations" IS prometaphase, where everything before metaphase is
                  prometaphase by designation and no NEB timestamp is needed (user 2026-08-10).

MEASUREMENTS (identical to the metaphase family, so nothing is redefined mid-comparison):
  * amplitude and period are PER KINETOCHORE (user 2026-08-10) -- the plate-relative position of each sister
    separately, never the pair midpoint, which cancels the very motion being measured.
  * mean k-k is PER SISTER PAIR -- it is a distance between two sisters and is undefined for one.
  * PAIRED kinetochores only. No polar, no lagging.
  * the standing cohort gate (plot_excluded + Mad1 + double-chromosome) applies, so prophase ablations,
    drug-treated, metaphase ablations and 4-sisterless stay out.

SECOND HALF — WHICH SUMMARY STATISTIC?  (her question)
"right now on these plots you're plotting standard deviation or something, right? ... how would it affect
the data if another summary measurement ... were used for the points instead? which would maximize the
difference between groups, and which would minimize it? does one measurement cause a maximum difference in
the metaphase:metaphase data but very close group values in the prometaphase:metaphase plot set?"

Amplitude is currently the SD of each kinetochore's plate-relative position. That is one of many ways to
summarise the spread of a series, and they are NOT interchangeable: SD and half-range are dominated by the
single largest excursion, while MAD and IQR ignore it almost entirely. So a group difference that lives in
the extremes shows up under SD and vanishes under MAD, and vice versa. This script therefore recomputes
every point under seven summary statistics and reports, for BOTH sets, the group separation each produces —
so the choice is made on evidence instead of habit, and any statistic that flatters one set while flattening
the other is visible rather than hidden.
"""
import sys, os, csv, json, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu
import lib
import osclib   # validated plate reconstruction (user 2026-08-20, board 8 item 2)

lib.apply_style()
csv.field_size_limit(10 ** 9)
ANN = "/Volumes/4 MB/annotations"
OUT = "/Volumes/4 MB/ablation_figures_20260625/group6_tracks"
RELINK = "/Volumes/4 MB/ablation_figures_20260625/_ai_relink/pdf"
os.makedirs(OUT, exist_ok=True); os.makedirs(RELINK, exist_ok=True)
PX = 0.062
MIN_USABLE = 4

data, _ = lib.load_master(); mrow = {r["Batch Name"]: r for r in data}
DBL = set(lib.double_chromosome_batches())
_okc = {}
def cohort_ok(b):
    if b not in _okc:
        _okc[b] = (not lib.plot_excluded(b)) and (not lib.is_mad1(b)) and b not in DBL
    return _okc[b]
def nsis(b): return (mrow.get(b, {}).get("# Sisterless KTs", "") or "").strip()
def T(b, col): return lib.parse_time(mrow.get(b, {}).get(col, ""))

def phase_of(b):
    return (mrow.get(b, {}).get("Phase of Ablations", "") or "").strip().lower()

_FIRST_T = {}          # cell -> earliest annotated t_sec (filled once outlines are loaded)

def window(b, mode):
    """(lo, hi) in seconds for this cell, or None.

    USER 2026-08-10: "as long as youre using batches with an ablation designation of prometaphase, then it
    doesnt need an nebd to work for this." So for a PROMETAPHASE-designated ablation, everything annotated
    before Metaphase Start IS prometaphase by designation, and the window opens at the cell's first
    annotated frame rather than at NEB. Requiring NEB Time was costing 12 of 18 single-sisterless cells,
    since master carries no NEB for them. NEB is still used as the lower bound when it exists (it is the
    tighter, more literal bound); otherwise the first annotation opens the window.
    """
    if mode == "meta":
        lo, hi = T(b, "Metaphase Start (s)"), T(b, "Anaphase Onset (s)")
        if lo is None or hi is None or hi <= lo: return None
        return (lo, hi)
    # prometaphase
    hi = T(b, "Metaphase Start (s)")
    if hi is None: return None
    if "prometaphase" not in phase_of(b):
        return None                              # only cells DESIGNATED prometaphase qualify
    lo = T(b, "NEB Time (s)")
    if lo is None: lo = _FIRST_T.get(b)
    if lo is None or hi <= lo: return None
    return (lo, hi)

# ---- her manual outlines + curated sister pairs ---------------------------------------------------
SIS = {}
for r in csv.DictReader(open(f"{ANN}/KT_SISTERS_20260723.csv")):
    if r["sister_pair_id"]: SIS[r["track_id"]] = r["sister_pair_id"]
outs = collections.defaultdict(list)
for r in csv.DictReader(open(f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv")):
    if r["label"] != "paired" or not r["t_sec"] or not r["frame"].isdigit(): continue
    outs[r["batch"]].append(dict(frame=int(r["frame"]), t=float(r["t_sec"]), grp=r["track_id"],
                                 pair=SIS.get(r["track_id"], ""),
                                 c=np.array([float(r["cx_px"]), float(r["cy_px"])])))
for _b, _rs in outs.items():
    _ts = [r["t"] for r in _rs]
    if _ts: _FIRST_T[_b] = min(_ts)

plates = collections.defaultdict(dict)
for r in csv.DictReader(open(f"{ANN}/meta_plates.csv")):
    if not r["points"] or not r["frame"].isdigit(): continue
    P = np.array(json.loads(r["points"]), float)
    if len(P) < 2: continue
    ctr = P.mean(0); _, _, vt = np.linalg.svd(P - ctr)
    plates[r["batch"]][int(r["frame"])] = (ctr, vt[1])
def plate_at(b, f):
    """Her DRAWN plate for this frame, else the plate RECONSTRUCTED from her own sister pairs.

    USER 2026-08-20 (artboard 8, item 2): "there should definitely be more annotated data that should be
    in these - the n for all groups on both plots is far too small".

    WHY THE n WAS SMALL. The k-k metric needs only two kinetochores, so it kept ~16/14/13 cells. The
    position metrics (oscillation amplitude and period) additionally required a HAND-DRAWN metaphase
    plate within 6 frames, because position is measured along the plate normal -- and that requirement
    alone cut single-sisterless PROMETAPHASE from 16 usable cells to 4. It is not missing annotation:
    she drew plates on the metaphase frames, and prometaphase is exactly where she had least reason to.

    The reconstruction is not an invention -- it is her own annotation read a second way: the sister k-k
    axis IS the plate normal, and the paired-KT centroid is the plate centre. Validated in osclib against
    1,045 frames where she DID draw a plate: 6.9 deg median disagreement, 0.87 um median centre offset.
    Used ONLY where she drew nothing, never to override a drawn plate.
    """
    d = plates.get(b)
    if d:
        if f in d: return d[f]
        nf = min(d, key=lambda x: abs(x - f))
        if abs(nf - f) <= 6: return d[nf]
    return osclib._reconstructed_plate(b, f)

def oriented(cell, frames):
    out = {}; prev = None
    for f in sorted(frames):
        pl = plate_at(cell, f)
        if pl is None: continue
        ctr, nrm = pl
        if prev is not None and np.dot(nrm, prev) < 0: nrm = -nrm
        prev = nrm; out[f] = (ctr, nrm)
    return out

def est_period_min(T_, POS):
    ts = sorted((t, p) for t, p in zip(T_, POS) if p is not None)
    if len(ts) < 5: return None
    t = np.array([x[0] for x in ts]); y = np.array([x[1] for x in ts]) - np.mean([x[1] for x in ts])
    if np.std(y) == 0: return None
    s = np.sign(y); s[s == 0] = 1
    nc = int(np.sum(np.abs(np.diff(s)) > 0))
    if nc < 1: return None
    return 2.0 * (t.max() - t.min()) / nc

def collect(mode, want_group):
    """-> (kts, pairs): per-KINETOCHORE position series and per-PAIR k-k series, inside `mode`'s window."""
    kts, pairs = [], []
    for b, rs in outs.items():
        g = nsis(b)
        if g != want_group or not cohort_ok(b): continue
        w = window(b, mode)
        if w is None: continue
        lo, hi = w
        byp = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
        for r in rs:
            if r["pair"]: byp[r["pair"]][r["frame"]][r["grp"]].append(r["c"])
        ft = {r["frame"]: r["t"] for r in rs}
        for pid, frs in byp.items():
            pl = oriented(b, frs.keys())
            kk = []; per = collections.defaultdict(list)
            for f in sorted(frs):
                t = ft.get(f)
                if t is None or not (lo <= t <= hi): continue
                tm = (t - lo) / 60.0
                gd = {gg: np.mean(v, axis=0) for gg, v in frs[f].items()}
                if f in pl:
                    ctr, nrm = pl[f]
                    for gg, c in gd.items():
                        per[gg].append((tm, float(np.dot(c - ctr, nrm)) * PX))
                if len(gd) == 2:
                    c1, c2 = list(gd.values())
                    kk.append((tm, float(np.hypot(c1[0] - c2[0], c1[1] - c2[1]) * PX)))
            sp = str(pid).split("|")[-1]
            if len(kk) >= MIN_USABLE:
                pairs.append(dict(cell=b, pair=sp, kk=[v for _, v in kk], n=len(kk)))
            for gg, ser in per.items():
                if len(ser) >= MIN_USABLE:
                    kts.append(dict(cell=b, pair=sp, kt=str(gg).split("|")[-1],
                                    t=[a for a, _ in ser], pos=[v for _, v in ser], n=len(ser)))
    return kts, pairs

# ---- the seven ways to summarise one kinetochore's excursion --------------------------------------
def _detrended(v, t):
    v = np.asarray(v, float); t = np.asarray(t, float)
    if len(v) < 3 or np.ptp(t) == 0: return v - v.mean()
    m, b_ = np.polyfit(t, v, 1)
    return v - (m * t + b_)
STATS = {
    "SD (current)":        lambda v, t: float(np.std(v)),
    "MAD":                 lambda v, t: float(np.median(np.abs(np.asarray(v) - np.median(v)))),
    "IQR":                 lambda v, t: float(np.percentile(v, 75) - np.percentile(v, 25)),
    "mean abs deviation":  lambda v, t: float(np.mean(np.abs(np.asarray(v) - np.mean(v)))),
    "half peak-to-peak":   lambda v, t: float((np.max(v) - np.min(v)) / 2.0),
    "RMS about median":    lambda v, t: float(np.sqrt(np.mean((np.asarray(v) - np.median(v)) ** 2))),
    "detrended SD":        lambda v, t: float(np.std(_detrended(v, t))),
}

def cliffs_delta(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if not len(a) or not len(b): return float("nan")
    gt = sum((x > b).sum() for x in a); lt = sum((x < b).sum() for x in a)
    return (gt - lt) / (len(a) * len(b))

def mw(a, b):
    return mannwhitneyu(a, b, alternative="two-sided").pvalue if len(a) >= 3 and len(b) >= 3 else float("nan")

# ---- assemble both sets ---------------------------------------------------------------------------
kt_single_meta,    pr_single_meta    = collect("meta",    "1")
kt_single_prometa, pr_single_prometa = collect("prometa", "1")
kt_triple_meta,    pr_triple_meta    = collect("meta",    "3")
print(f"single METAPHASE    : {len(kt_single_meta)} KTs / {len({k['cell'] for k in kt_single_meta})} cells")
print(f"single PROMETAPHASE : {len(kt_single_prometa)} KTs / {len({k['cell'] for k in kt_single_prometa})} cells")
print(f"triple METAPHASE    : {len(kt_triple_meta)} KTs / {len({k['cell'] for k in kt_triple_meta})} cells")

SETS = {
    "A · metaphase : metaphase":      (kt_single_meta,    pr_single_meta,    "single metaphase"),
    "B · prometaphase : metaphase":   (kt_single_prometa, pr_single_prometa, "single prometaphase"),
}
TRI_KT, TRI_PR = kt_triple_meta, pr_triple_meta

# ================= FIGURES for SET B (box + model wave), in the metaphase family's format ==========
COL = {"L": "#2a7fff", "R": "#ff5a3c"}
def boxstrip(ax, a, b, la, lb, ylab, title, p):
    for i, (v, c) in enumerate(((a, COL["L"]), (b, COL["R"]))):
        if not len(v): continue
        x = np.random.default_rng(i).normal(i, 0.06, len(v))
        ax.scatter(x, v, c=c, s=45, alpha=.75, edgecolor="k", lw=.4, zorder=3)
        ax.boxplot(v, positions=[i], widths=.5, showfliers=False)
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"{la}\n(n={len(a)})", f"{lb}\n(n={len(b)})"])
    ax.set_ylabel(ylab); ax.set_title(title + (f"   MW p={p:.3g}" if p == p else ""))
    ax.grid(alpha=.3, axis="y")

def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=150, bbox_inches="tight")
    fig.savefig(os.path.join(RELINK, name + ".pdf"), bbox_inches="tight")
    plt.close(fig); print(f"  wrote {name}.png (+ deck-linked PDF)")

def _keep_early(K, plot_id):
    ex = lib.manual_point_exclusions(plot_id)
    return [k for k in K if (k["cell"], str(k["kt"])) not in ex] if ex else K

AMP = STATS["SD (current)"]
sp_amp = [AMP(k["pos"], k["t"]) for k in kt_single_prometa]
tm_amp = [AMP(k["pos"], k["t"]) for k in TRI_KT]
sp_per = [p for p in (est_period_min(k["t"], k["pos"])
                      for k in _keep_early(kt_single_prometa, "G6_prometa_vs_meta_period")) if p is not None]
tm_per = [p for p in (est_period_min(k["t"], k["pos"]) for k in TRI_KT) if p is not None]
sp_kk = [float(np.mean(p["kk"])) for p in pr_single_prometa]
tm_kk = [float(np.mean(p["kk"])) for p in TRI_PR]

fig, ax = plt.subplots(figsize=(7.6, 5.6))
boxstrip(ax, sp_amp, tm_amp, "single\nPROMETAPHASE", "3-sisterless\nMETAPHASE",
         "amplitude (um)", "Oscillation amplitude, per kinetochore\nsingle prometaphase vs triple metaphase",
         mw(sp_amp, tm_amp))
save(fig, "G6_prometa_vs_meta_amplitude")

fig, ax = plt.subplots(figsize=(7.6, 5.6))
boxstrip(ax, sp_per, tm_per, "single\nPROMETAPHASE", "3-sisterless\nMETAPHASE",
         "period (min)", "Oscillation period, per kinetochore\nsingle prometaphase vs triple metaphase",
         mw(sp_per, tm_per))
save(fig, "G6_prometa_vs_meta_period")

fig, ax = plt.subplots(figsize=(7.6, 5.6))
boxstrip(ax, sp_kk, tm_kk, "single\nPROMETAPHASE", "3-sisterless\nMETAPHASE",
         "k-k distance (um)", "Mean k-k per sister pair\nsingle prometaphase vs triple metaphase",
         mw(sp_kk, tm_kk))
save(fig, "G6_prometa_vs_meta_meankk")

# model wave — median amplitude & period per group, phase arbitrary (same as the metaphase family)
fig, ax = plt.subplots(figsize=(7.6, 5.6))
tt = np.linspace(0, 10, 500)
for v_amp, v_per, lab, c in ((sp_amp, sp_per, "single prometaphase", COL["L"]),
                             (tm_amp, tm_per, "3-sisterless metaphase", COL["R"])):
    if len(v_amp) and len(v_per):
        A = float(np.median(v_amp)); P = float(np.median(v_per))
        if np.isfinite(A) and np.isfinite(P) and P > 0:
            ax.plot(tt, A * np.sin(2 * np.pi * tt / P), color=c, lw=2.5,
                    label=f"{lab}: A={A:.2f}um, T={P:.1f}min")
ax.axhline(0, ls="--", c="k", alpha=.5); ax.set_xlabel("time (min)"); ax.set_ylabel("model pos (um)")
ax.set_title("Model oscillation (median amplitude & period; phase arbitrary)\n"
             "single prometaphase vs triple metaphase")
ax.legend(); ax.grid(alpha=.3)
save(fig, "G6_prometa_vs_meta_model")

# ================= SUMMARY-STATISTIC SENSITIVITY, both sets =======================================
rows = []
for setname, (kt_left, pr_left, leftlab) in SETS.items():
    for sname, fn in STATS.items():
        a = [fn(k["pos"], k["t"]) for k in kt_left]
        b = [fn(k["pos"], k["t"]) for k in TRI_KT]
        if len(a) < 3 or len(b) < 3: continue
        ma, mb = float(np.median(a)), float(np.median(b))
        rows.append(dict(set=setname, stat=sname, n_left=len(a), n_right=len(b),
                         med_left=ma, med_right=mb,
                         ratio=(mb / ma if ma else float("nan")),
                         delta=cliffs_delta(a, b), p=mw(a, b)))

print("\n================ SUMMARY-STATISTIC SENSITIVITY (amplitude) ================")
print(f"{'set':30s} {'statistic':20s} {'single':>8s} {'triple':>8s} {'ratio':>6s} {'Cliff d':>8s} {'p':>10s}")
for r in rows:
    print(f"{r['set'][:29]:30s} {r['stat']:20s} {r['med_left']:8.3f} {r['med_right']:8.3f} "
          f"{r['ratio']:6.2f} {r['delta']:+8.3f} {r['p']:10.4g}")

def pick(setname, key, want_max):
    sub = [r for r in rows if r["set"] == setname]
    if not sub: return None
    return (max if want_max else min)(sub, key=lambda r: abs(r[key]))
print()
for sn in SETS:
    hi = pick(sn, "delta", True); lo = pick(sn, "delta", False)
    if hi and lo:
        print(f"{sn}\n   MAXIMISES separation: {hi['stat']} (|Cliff d|={abs(hi['delta']):.3f}, p={hi['p']:.3g})"
              f"\n   MINIMISES separation: {lo['stat']} (|Cliff d|={abs(lo['delta']):.3f}, p={lo['p']:.3g})")
# the specific question: big in A, flat in B
byname = collections.defaultdict(dict)
for r in rows: byname[r["stat"]][r["set"]] = r
A = "A · metaphase : metaphase"; B = "B · prometaphase : metaphase"
cand = [(s, d[A]["delta"], d[B]["delta"]) for s, d in byname.items() if A in d and B in d]
if cand:
    cand.sort(key=lambda x: abs(x[1]) - abs(x[2]), reverse=True)
    s, da, db = cand[0]
    print(f"\nLARGEST A-minus-B gap: {s}  |d| A={abs(da):.3f} vs B={abs(db):.3f}"
          f"   -> separates the metaphase:metaphase groups most while leaving prometaphase:metaphase closest")
    for s2, da2, db2 in cand:
        print(f"   {s2:20s} |d|A={abs(da2):.3f}  |d|B={abs(db2):.3f}   gap={abs(da2)-abs(db2):+.3f}")

# sensitivity figure
fig, ax = plt.subplots(figsize=(9.2, 5.4))
names = [s for s, _, _ in cand]
xa = [abs(d) for _, d, _ in cand]; xb = [abs(d) for _, _, d in cand]
yy = np.arange(len(names))
ax.barh(yy - 0.2, xa, height=0.38, color="#2a7fff", label="A · metaphase : metaphase")
ax.barh(yy + 0.2, xb, height=0.38, color="#ff5a3c", label="B · prometaphase : metaphase")
ax.set_yticks(yy); ax.set_yticklabels(names)
ax.set_xlabel("|Cliff's delta| between groups  (0 = identical, 1 = complete separation)")
ax.set_title("Which summary statistic separates the groups?\n"
             "amplitude recomputed seven ways, per kinetochore", loc="left", fontweight="bold", fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=.3, axis="x")
save(fig, "G6_amplitude_summary_statistic_sensitivity")

lib.record_plot("G6_amplitude_summary_statistic_sensitivity",
                ["set", "statistic", "n_single", "n_triple", "median_single", "median_triple",
                 "ratio_triple_over_single", "cliffs_delta", "mannwhitney_p"],
                [[r["set"], r["stat"], r["n_left"], r["n_right"], round(r["med_left"], 5),
                  round(r["med_right"], 5), round(r["ratio"], 4), round(r["delta"], 4), r["p"]] for r in rows],
                {"kind": "summary-statistic sensitivity of oscillation amplitude",
                 "sets": "A = single metaphase vs triple metaphase; B = single PROMETAPHASE vs triple metaphase",
                 "unit": "one value per KINETOCHORE"},
                __file__,
                "Oscillation amplitude recomputed under seven summary statistics, for both the "
                "metaphase:metaphase and prometaphase:metaphase comparisons.",
                source=[f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv", f"{ANN}/KT_SISTERS_20260723.csv"],
                key_column=None)

_rows_b = ([[ "amplitude", "single_prometaphase", k["cell"], k["pair"], k["kt"], round(AMP(k["pos"], k["t"]), 5)]
            for k in kt_single_prometa] +
           [[ "amplitude", "triple_metaphase", k["cell"], k["pair"], k["kt"], round(AMP(k["pos"], k["t"]), 5)]
            for k in TRI_KT] +
           [[ "mean_kk", "single_prometaphase", p["cell"], p["pair"], "", round(float(np.mean(p["kk"])), 5)]
            for p in pr_single_prometa] +
           [[ "mean_kk", "triple_metaphase", p["cell"], p["pair"], "", round(float(np.mean(p["kk"])), 5)]
            for p in TRI_PR])
lib.record_plot("G6_prometa_vs_meta_amplitude",
                ["measure", "group", "cell", "pair", "kinetochore", "value"], _rows_b,
                {"kind": "single PROMETAPHASE vs triple METAPHASE",
                 "windows": "single [NEB Time, Metaphase Start); triple [Metaphase Start, Anaphase Onset]",
                 "unit": "amplitude per KINETOCHORE, mean k-k per SISTER PAIR",
                 "amplitude_stat": "SD of plate-relative position"},
                __file__,
                "Oscillation amplitude and mean k-k, single-sisterless PROMETAPHASE vs triple-sisterless "
                "METAPHASE. Paired kinetochores only.",
                source=[f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv", f"{ANN}/KT_SISTERS_20260723.csv"],
                key_column="cell")
print("\ndone prometaphase-vs-metaphase")


# ================= THREE-GROUP VERSION: single prometaphase | single metaphase | triple metaphase =====
# USER 2026-08-10: "did you make the revised 1-prometaphase/3-metaphase plots to include the 1-metaphase
# data for comparision?"
#
# The two-group figures above answer "does a triple in metaphase behave like a single in prometaphase?" but
# they cannot show the thing that makes the answer interesting: whether single PROMETAPHASE differs from
# the SAME cells' own metaphase. Putting all three on one axis does, and it is the honest layout, because
# the reader can see at once that the single group appears twice -- as its own prometaphase and its own
# metaphase -- rather than being asked to hold two separate figures in mind.
G3 = [("single PROMETAPHASE", kt_single_prometa, pr_single_prometa, "#2a7fff"),
      ("single METAPHASE",    kt_single_meta,    pr_single_meta,    "#7fb2ff"),
      ("3-sisterless METAPHASE", TRI_KT,         TRI_PR,            "#ff5a3c")]

# USER 2026-08-10: "in the 'oscillation period per kinetochore' plot, single prometa has one really huge
# outlier thats messing up the scale of the plot. remove it and rescale the yaxis accordingly."
#
# Recorded in annotations/MANUAL_PLOT_EXCLUSIONS.csv with a `kt` column and read back through
# lib.manual_point_exclusions, so the decision lives in her exclusions file rather than being hard-coded
# here, and so it applies to every period plot listed there rather than just the one she was looking at.
# It is a POINT exclusion, not a batch one: 20250930 four_ablation_57 kt 4 goes, kt 3 of the same cell stays.
def _keep(K, plot_id):
    ex = lib.manual_point_exclusions(plot_id)
    if not ex: return K
    out = [k for k in K if (k["cell"], str(k["kt"])) not in ex]
    if len(out) != len(K):
        print(f"     {plot_id}: dropped {len(K)-len(out)} manually-excluded kinetochore(s)")
    return out

def _amp(K): return [AMP(k["pos"], k["t"]) for k in K]
def _per(K): return [x for x in (est_period_min(k["t"], k["pos"]) for k in K) if x is not None]
def _kk(P):  return [float(np.mean(p["kk"])) for p in P]

from scipy.stats import kruskal
def three_panel(getter, ylab, title, name):
    vals = [getter(_keep(k, name), p) for _, k, p, _ in G3]
    if any(len(v) < 3 for v in vals):
        print(f"  {name}: too few"); return
    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    for i, ((lab, _k, _p, col), v) in enumerate(zip(G3, vals)):
        x = np.random.default_rng(i).normal(i, 0.07, len(v))
        ax.scatter(x, v, c=col, s=44, alpha=.72, edgecolor="k", lw=.35, zorder=3)
        ax.boxplot(v, positions=[i], widths=.55, showfliers=False)
    kw = kruskal(*vals).pvalue
    pAB = mw(vals[0], vals[1]); pAC = mw(vals[0], vals[2]); pBC = mw(vals[1], vals[2])
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{lab}\n(n={len(v)})" for (lab, _, _, _), v in zip(G3, vals)], fontsize=9)
    ax.set_ylabel(ylab)
    ax.set_title(f"{title}\nKruskal-Wallis p={kw:.3g}", fontsize=11)
    ax.text(0.0, -0.155,
            f"pairwise Mann-Whitney:   single prometa vs single meta p={pAB:.3g}   ·   "
            f"single prometa vs triple meta p={pAC:.3g}   ·   single meta vs triple meta p={pBC:.3g}",
            transform=ax.transAxes, fontsize=7.5, color="#555", va="top")
    ax.grid(alpha=.3, axis="y")
    save(fig, name)
    print(f"  {name}: n={[len(v) for v in vals]}  KW p={kw:.4g}  "
          f"pro-vs-meta p={pAB:.4g}  pro-vs-triple p={pAC:.4g}  meta-vs-triple p={pBC:.4g}")
    lib.record_plot(name, ["group", "value"],
                    [[lab, round(float(x), 5)] for (lab, _, _, _), v in zip(G3, vals) for x in v],
                    {"kind": "three-group comparison", "kruskal_p": kw,
                     "p_single_prometa_vs_single_meta": pAB,
                     "p_single_prometa_vs_triple_meta": pAC,
                     "p_single_meta_vs_triple_meta": pBC,
                     "unit": "one point per KINETOCHORE (amplitude/period) or per SISTER PAIR (k-k)"},
                    __file__, f"{title}; single appears twice, as its own prometaphase and its own metaphase.",
                    source=[f"{ANN}/KT_OUTLINE_TRACKS_20260723.csv"], key_column=None)

three_panel(lambda k, p: _amp(k), "amplitude (um)",
            "Oscillation amplitude per kinetochore", "G6_three_group_amplitude")
three_panel(lambda k, p: _per(k), "period (min)",
            "Oscillation period per kinetochore", "G6_three_group_period")
three_panel(lambda k, p: _kk(p), "k-k distance (um)",
            "Mean k-k per sister pair", "G6_three_group_meankk")

# model waves, all three on one axis
fig, ax = plt.subplots(figsize=(8.4, 5.8))
tt = np.linspace(0, 10, 500)
for lab, K, P, col in G3:
    a_, p_ = _amp(K), _per(K)
    if not a_ or not p_: continue
    # NOT `T`: that is this module's time-lookup helper, T(batch, column), defined at the top. Binding a
    # float to it here left window() raising "'float' object is not callable" for anything that imported
    # this module and then called it -- which is exactly how the early-prometaphase sweep first failed.
    A = float(np.median(a_)); T_per = float(np.median(p_))
    if np.isfinite(A) and np.isfinite(T_per) and T_per > 0:
        ax.plot(tt, A * np.sin(2 * np.pi * tt / T_per), color=col, lw=2.5,
                label=f"{lab}: A={A:.2f}um, T={T_per:.1f}min")
ax.axhline(0, ls="--", c="k", alpha=.5); ax.set_xlabel("time (min)"); ax.set_ylabel("model pos (um)")
ax.set_title("Model oscillation (median amplitude & period; phase arbitrary)\n"
             "single prometaphase vs single metaphase vs triple metaphase")
ax.legend(fontsize=8); ax.grid(alpha=.3)
save(fig, "G6_three_group_model")
# 2026-08-18: the model-wave panel was placed but never registered -> no provenance, no legend.
try:
    lib.register_panel("G6_three_group_model", "G6_three_group_amplitude",
                       caption="Model waves built from each group's median oscillation amplitude and "
                               "period: single-sisterless prometaphase, single-sisterless metaphase, "
                               "triple-sisterless metaphase.",
                       settings={"kind": "model wave", "groups": 3}, script=__file__)
except Exception as _e:
    print("register_panel(G6_three_group_model) skipped: %s" % _e)
