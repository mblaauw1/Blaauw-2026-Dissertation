#!/usr/bin/env python3
"""Her 2026-07-27 round-3 requests, the ones the existing data can answer:

  R1  velocity in the FIRST 2 min of metaphase vs the LAST 2 min before anaphase,
      split 1- vs 3-sisterless, polar vs paired  (8 groups)
  R2  oscillation (displacement per 20 s) with POLAR split by cohort: 1- / 2- / 3-sisterless
  R3  distance-to-plate over time, SEPARATE lines for 1- and 3-sisterless, t=0 at metaphase onset,
      each trace cut at its own anaphase onset, trendlines refit on that window
  R4  lagging kinetochore: how far it gets stretched and how fast, 1- vs 3-sisterless
  R5  total movement magnitude for stayed-polar / paired x single / triple, and vs chromosome length
  R6  VERIFY her doubt: is there really no 3-sisterless cell without a lagging or polar chromosome?
  R7  metaphase duration vs the FRACTION of sisterless KTs that became lagging / stayed polar
      (reports what is and is not annotated)

Figures -> group7_questions/ with an R prefix."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib, kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
A = f"{ROOT}/annotations"
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
REPORT = []
C1, C3 = "#3b6fb6", "#d1495b"
CST = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}


def rd(p): return list(csv.DictReader(open(p, newline="")))
def num(v):
    try: return float(str(v).strip())
    except Exception: return None


def hms(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try: q = [float(x) for x in s.split(":")]
    except ValueError: return None
    v = q[0]*3600 + q[1]*60 + q[2] if len(q) == 3 else (q[0]*60 + q[1] if len(q) == 2 else q[0])
    return -v if neg else v


def save(fig, name, cap):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try: lib.record_plot(name, ["x"], [], {"family": "questions_20260727"}, script=__file__, caption=cap,
                         source=[f"{A}/KT_LANDMARK_ANALYSIS_20260723.csv"], key_column=None, fig=fig)
    except Exception: pass
    print("  " + name)


def violins(ax, groups, order, colors, ylabel, rot=0):
    for i, k in enumerate(order):
        d = groups.get(k, [])
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, colors[k], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.18, d,
                   s=lib.VIOLIN_DOT_S, color=colors[k], alpha=0.65, lw=0)
        ax.hlines(np.median(d), i - 0.32, i + 0.32, color=colors[k], lw=2.4)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{k}\n(n={len(groups.get(k, []))})" for k in order], fontsize=7.5, rotation=rot)
    ax.set_ylabel(ylabel)


master, _ = lib.load_master()
M = {r["Batch Name"]: r for r in master}
def mg(b, k): return (M.get(b, {}).get(k) or "").strip()
def cohort(b):
    n = mg(b, "# Sisterless KTs")
    return n if n in ("1", "2", "3") else None

LM = rd(f"{A}/KT_LANDMARK_ANALYSIS_20260723.csv")
for r in LM:
    b = r["batch"]
    mt, at = hms(mg(b, "Metaphase Start (s)")), hms(mg(b, "Anaphase Onset (s)"))
    t = num(r.get("t_sec"))
    r["_t"] = t; r["_mt"] = mt; r["_at"] = at
    r["_tmeta"] = ((t - mt) / 60.0) if (mt is not None and t is not None) else None
    r["_tana"] = ((t - at) / 60.0) if (at is not None and t is not None) else None

# ── R1 · velocity in the first 2 min of metaphase vs the last 2 min before anaphase ───────────────
buckets = collections.defaultdict(list)
per_track = collections.defaultdict(list)
for r in LM:
    if r["label"] not in ("polar", "paired"): continue
    v = num(r.get("speed_um_s"))
    co = cohort(r["batch"])
    if v is None or co not in ("1", "3") or r["_tmeta"] is None or r["_tana"] is None: continue
    if 0.0 <= r["_tmeta"] <= 2.0:
        per_track[(r["track_id"], co, r["label"], "first 2 min of metaphase")].append(v * 60.0)
    if -2.0 <= r["_tana"] <= 0.0:
        per_track[(r["track_id"], co, r["label"], "last 2 min before anaphase")].append(v * 60.0)
for (tid, co, lab, win), v in per_track.items():
    if len(v) >= 2:
        buckets[f"{co}-sis {lab}\n{win.split(' ')[0]}"].append(float(np.mean(v)))
KEYS = [f"{co}-sis {lab}\n{w}" for co in ("1", "3") for lab in ("paired", "polar") for w in ("first", "last")]
have = {k: buckets.get(k, []) for k in KEYS}
if sum(len(v) >= 3 for v in have.values()) >= 4:
    cols = {k: (C1 if k.startswith("1") else C3) for k in KEYS}
    fig, ax = plt.subplots(figsize=(11.0, 5.2))
    violins(ax, have, KEYS, cols, "KT velocity (µm/min, per-track mean)", rot=0)
    ax.set_title("R1 · Velocity at the START of metaphase vs just BEFORE anaphase, by cohort and state",
                 loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "RNEW_r1_velocity_start_vs_end_metaphase", "velocity first 2 min vs last 2 min, 1 vs 3 sisterless")
    REPORT.append("R1 ANSWERED: " + "; ".join(f"{k.replace(chr(10),' ')} n={len(v)} med={np.median(v):.2f}"
                                              for k, v in have.items() if len(v) >= 3))
else:
    REPORT.append(f"R1 SKIPPED: only {sum(len(v)>=3 for v in have.values())}/8 groups reach 3 tracks")

# ── R2 · oscillation (displacement per 20 s) with polar split by cohort ───────────────────────────
step = collections.defaultdict(list)
tracks = collections.defaultdict(list)
for r in LM:
    if r["label"] not in ("polar", "paired"): continue
    if r["_t"] is None or num(r.get("dist_to_plate_um")) is None: continue
    tracks[(r["batch"], r["track_id"], r["label"])].append((r["_t"], num(r["dist_to_plate_um"])))
for (b, tid, lab), v in tracks.items():
    co = cohort(b)
    v.sort()
    for (t0, d0), (t1, d1) in zip(v, v[1:]):
        dt = t1 - t0
        if not (5 <= dt <= 120): continue
        disp = abs(d1 - d0) * (20.0 / dt)                 # normalised to a 20 s interval
        if lab == "polar" and co:
            step[f"polar {co}-sisterless"].append(disp)
        elif lab == "paired":
            step["plate-aligned (paired)"].append(disp)
order = ["plate-aligned (paired)", "polar 1-sisterless", "polar 2-sisterless", "polar 3-sisterless"]
have2 = {k: step.get(k, []) for k in order if len(step.get(k, [])) >= 5}
if len(have2) >= 3:
    cols = {"plate-aligned (paired)": "#3b6fb6", "polar 1-sisterless": "#f0a04b",
            "polar 2-sisterless": "#e6820e", "polar 3-sisterless": "#a85a00"}
    oo = [k for k in order if k in have2]
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    violins(ax, have2, oo, cols, "displacement per 20 s (µm)")
    kt_stats.add_group_stats(ax, have2, oo, loc="upper right")
    ax.set_title("R2 · Kinetochore oscillation — polar split by cohort", loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "RNEW_r2_oscillation_polar_by_cohort", "oscillation displacement per 20s, polar by cohort")
    REPORT.append("R2 ANSWERED: " + "; ".join(f"{k} n={len(v)} med={np.median(v):.3f}um" for k, v in have2.items()))
else:
    REPORT.append(f"R2 SKIPPED: only {len(have2)} cohort groups have >=5 steps")

# ── R3 · distance-to-plate over metaphase, separate 1- and 3-sisterless lines ─────────────────────
fig, ax = plt.subplots(figsize=(8.4, 5.4))
ok = 0
for co, colr in (("1", C1), ("3", C3)):
    pts, ntr = [], 0
    for (b, tid, lab), v in tracks.items():
        if lab != "polar" or cohort(b) != co: continue
        mt, at = hms(mg(b, "Metaphase Start (s)")), hms(mg(b, "Anaphase Onset (s)"))
        if mt is None or at is None or at <= mt: continue
        s = sorted((t, d) for t, d in v if mt <= t <= at)
        if len(s) < 3: continue
        ntr += 1
        xs = [(t - mt) / 60.0 for t, _ in s]; ys = [d for _, d in s]
        ax.plot(xs, ys, "-", color=colr, lw=0.9, alpha=0.35)
        pts += list(zip(xs, ys))
    if len(pts) >= 10:
        ok += 1
        X = np.array([p[0] for p in pts]); Y = np.array([p[1] for p in pts])
        b_, a_ = np.polyfit(X, Y, 1); xf = np.linspace(0, X.max(), 20)
        ax.plot(xf, a_ + b_*xf, "--", color=colr, lw=2.6)
        bins = np.linspace(0, X.max(), 9); idx = np.digitize(X, bins)
        bx, bm = [], []
        for bi in range(1, len(bins)):
            sel = Y[idx == bi]
            if len(sel) >= 4: bx.append((bins[bi-1]+bins[bi])/2); bm.append(np.median(sel))
        if bx: ax.plot(bx, bm, "-o", color=colr, lw=2.4, ms=4)
        rho, pv = st.spearmanr(X, Y)
        ax.plot([], [], color=colr, lw=2.4,
                label=f"{co}-sisterless: {ntr} tracks, slope={b_:+.3f} µm/min, ρ={rho:+.2f}, p={pv:.1g}")
if ok:
    ax.axvline(0, ls=":", color="#999")
    ax.set_xlabel("minutes from metaphase onset (each trace cut at its own anaphase onset)")
    ax.set_ylabel("polar KT distance to plate (µm)")
    ax.legend(fontsize=8)
    ax.set_title("R3 · Polar KT distance-to-plate over metaphase, 1- vs 3-sisterless", loc="left",
                 fontweight="bold", fontsize=10.5)
    save(fig, "RNEW_r3_dist_to_plate_1vs3", "polar distance-to-plate over metaphase, 1 vs 3 sisterless")
    REPORT.append(f"R3 ANSWERED: {ok} cohort(s) plotted with refit trendlines")
else:
    plt.close(fig); REPORT.append("R3 SKIPPED: no cohort had enough in-window polar frames")

# ── R4 · lagging stretch: how far and how fast, 1 vs 3 ────────────────────────────────────────────
lag = collections.defaultdict(list)
for r in LM:
    if r["label"] != "lagging": continue
    co = cohort(r["batch"]); mj = num(r.get("major_um"))
    if co not in ("1", "3") or mj is None or r["_t"] is None: continue
    lag[(r["batch"], r["track_id"], co)].append((r["_t"], mj))
maxs, rates = collections.defaultdict(list), collections.defaultdict(list)
for (b, tid, co), v in lag.items():
    v.sort()
    if len(v) < 4: continue
    mj = [x[1] for x in v]; ts = [x[0] for x in v]
    maxs[co].append(float(np.max(mj)))
    dur = (ts[-1] - ts[0]) / 60.0
    if dur > 0: rates[co].append((np.max(mj) - mj[0]) / dur)
if len(maxs.get("1", [])) >= 3 and len(maxs.get("3", [])) >= 3:
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.8))
    for ax, D, yl in ((axs[0], maxs, "max lagging KT length (µm)"),
                      (axs[1], rates, "stretch rate (µm/min)")):
        g = {"single ablation": D.get("1", []), "triple ablation": D.get("3", [])}
        violins(ax, g, list(g), {"single ablation": C1, "triple ablation": C3}, yl)
        if all(len(v) >= 3 for v in g.values()):
            p = st.mannwhitneyu(*g.values(), alternative="two-sided")[1]
            ax.set_title(f"MW p={p:.3g}", loc="left", fontsize=9)
    fig.suptitle("R4 · Lagging kinetochore: how far and how fast it stretches", fontsize=11, fontweight="bold")
    save(fig, "RNEW_r4_lagging_stretch_1vs3", "lagging stretch extent and rate, 1 vs 3 sisterless")
    REPORT.append(f"R4 ANSWERED: max length single n={len(maxs['1'])} med={np.median(maxs['1']):.2f}um vs "
                  f"triple n={len(maxs['3'])} med={np.median(maxs['3']):.2f}um")
else:
    REPORT.append(f"R4 SKIPPED: only {len(maxs.get('1', []))} single / {len(maxs.get('3', []))} triple lagging tracks")

# ── R5 · total movement magnitude, 4 groups, and vs chromosome length ─────────────────────────────
tot = {}
for (b, tid, lab), v in tracks.items():
    co = cohort(b)
    if lab not in ("polar", "paired") or co not in ("1", "3"): continue
    v.sort()
    d = sum(abs(y1 - y0) for (_, y0), (_, y1) in zip(v, v[1:]))
    if len(v) >= 4:
        tot[(b, tid)] = (f"{'stayed polar' if lab == 'polar' else 'paired'} {'single' if co == '1' else 'three'} sisterless", d, co)
G5 = collections.defaultdict(list)
for k, (grp, d, co) in tot.items(): G5[grp].append(d)
o5 = ["stayed polar single sisterless", "paired single sisterless",
      "stayed polar three sisterless", "paired three sisterless"]
if sum(len(G5.get(k, [])) >= 3 for k in o5) >= 3:
    cols5 = {o5[0]: "#f0a04b", o5[1]: "#3b6fb6", o5[2]: "#a85a00", o5[3]: "#1f4e79"}
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    violins(ax, G5, o5, cols5, "total plate-normal movement over the track (µm)")
    kt_stats.add_group_stats(ax, {k: G5[k] for k in o5 if len(G5.get(k, [])) >= 3},
                             [k for k in o5 if len(G5.get(k, [])) >= 3], loc="upper right")
    ax.set_title("R5 · Total kinetochore movement, by state and cohort", loc="left", fontweight="bold", fontsize=10.5)
    save(fig, "RNEW_r5_total_movement_by_group", "total movement, polar/paired x single/triple")
    REPORT.append("R5 ANSWERED: " + "; ".join(f"{k} n={len(G5[k])} med={np.median(G5[k]):.1f}um"
                                              for k in o5 if len(G5.get(k, [])) >= 3))
    # vs chromosome length
    lens = collections.defaultdict(list)
    for r in rd(f"{A}/CHROMOSOME_MASTER.csv"):
        L = num(r["length_um"])
        if L is not None: lens[r["batch"]].append(L)
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    anyfit = False
    for grp, colr in ((o5[0], cols5[o5[0]]), (o5[2], cols5[o5[2]])):
        X, Y = [], []
        for (b, tid), (g, d, co) in tot.items():
            if g != grp or b not in lens: continue
            X.append(float(np.mean(lens[b]))); Y.append(d)
        if len(X) >= 5:
            anyfit = True
            ax.scatter(X, Y, s=34, color=colr, alpha=0.75, edgecolor="white", lw=0.4)
            rho, pv = st.spearmanr(X, Y)
            bb, aa = np.polyfit(X, Y, 1); xf = np.linspace(min(X), max(X), 20)
            ax.plot(xf, aa + bb*xf, "-", color=colr, lw=2.0,
                    label=f"{grp}: ρ={rho:+.2f}, p={pv:.2g} (n={len(X)})")
    if anyfit:
        ax.set_xlabel("mean sisterless chromosome length (µm)"); ax.set_ylabel("total movement (µm)")
        ax.legend(fontsize=8)
        ax.set_title("R5b · Total movement vs chromosome length (polar tracks)", loc="left", fontweight="bold", fontsize=10.5)
        save(fig, "RNEW_r5b_total_movement_vs_length", "total movement vs chromosome length")
    else:
        plt.close(fig)
else:
    REPORT.append("R5 SKIPPED: fewer than 3 of the 4 groups reach 3 tracks")

# ── R6 · verify: is there really no 3-sisterless cell without lagging or polar? ───────────────────
def yes(v): return (v or "").strip().lower().startswith("y")
def no(v):  return (v or "").strip().lower().startswith("n")
rows6 = []
for r in master:
    if (r.get("# Sisterless KTs") or "").strip() != "3": continue
    if lib.is_drug(r["Batch Name"]) or lib.is_mad1(r["Batch Name"]): continue
    if (r.get("Exclude") or "").strip().lower() in ("yes", "true", "1"): continue
    pc, lc = r.get("Polar Chromosomes"), r.get("Lagging Chromosomes")
    rows6.append((r["Batch Name"], (pc or "").strip(), (lc or "").strip()))
scored = [x for x in rows6 if x[1] and x[2]]
clean = [x for x in scored if no(x[1]) and no(x[2])]
REPORT.append(f"R6 VERIFIED: {len(rows6)} eligible 3-sisterless cells, {len(scored)} scored for BOTH polar and "
              f"lagging, and **{len(clean)} of them have NEITHER** -> {[x[0] for x in clean][:8]}"
              + (f" ; {len(rows6)-len(scored)} cells are UNSCORED so the claim rests on partial data" if len(scored) < len(rows6) else ""))

# ── R7 · what is annotated for the fate fractions ────────────────────────────────────────────────
n_pol = sum(1 for r in master if (r.get("Polar Chromosomes") or "").strip())
n_lag = sum(1 for r in master if (r.get("Lagging Chromosomes") or "").strip())
n_multi = sum(1 for r in master if (r.get("# Sisterless KTs") or "").strip() in ("2", "3"))
n_multi_sc = sum(1 for r in master if (r.get("# Sisterless KTs") or "").strip() in ("2", "3")
                 and (r.get("Polar Chromosomes") or "").strip() and (r.get("Lagging Chromosomes") or "").strip())
REPORT.append(f"R7 STATUS: Polar Chromosomes scored on {n_pol} cells, Lagging on {n_lag}. Of {n_multi} multi-sisterless "
              f"cells, {n_multi_sc} have BOTH scored — but both columns are YES/NO, not a COUNT, so a FRACTION of "
              f"sisterless KTs that lagged / stayed polar cannot be computed from the master. It needs a per-KT fate "
              f"column (or the kt_outline tracks, which cover only 31 cells).")

print("\n=== ANSWERS (round 3) ===")
for line in REPORT: print("  " + line)
open(f"{OUT}/ANSWERS3_20260727.txt", "w").write("\n".join(REPORT) + "\n")
