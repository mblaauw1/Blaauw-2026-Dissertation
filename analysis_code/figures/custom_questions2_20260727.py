#!/usr/bin/env python3
"""The four sub-questions left open by custom_questions_20260727.py (user 2026-07-27):

  Q7b  a per-cell ROUNDING score, and does targeted-chromosome size correlate with it?
  Q8b  do PROPHASE-ablated cells round less than PROMETAPHASE-ablated ones (and within 3-ablation cells)?
  Q8c  prophase vs prometaphase KINETOCHORE OSCILLATION at metaphase, polar and paired, vs a control group.
  Q3c  anaphase TOWARD-POLE velocity (signed, not the unsigned speed used in Q3a), single vs triple.

Rounding score = cell-outline circularity 4*pi*A/P^2 (1 = a perfect circle), taken as the per-cell MEDIAN
over the frames inside that cell's metaphase window when it has one, else over all its frames."""
import sys, os, csv, collections, json
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib, kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
A = f"{ROOT}/annotations"
REPORT = []


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
                         source=[f"{A}/cell_outlines.csv"], key_column=None, fig=fig)
    except Exception: pass
    print("  " + name)


def groups_panel(ax, groups, order, colors, ylabel):
    for i, k in enumerate(order):
        d = groups[k]
        if len(d) < 3: continue
        lib.journal_violin(ax, d, i, colors[k], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.18, d,
                   s=lib.VIOLIN_DOT_S, color=colors[k], alpha=0.7, lw=0)
        ax.hlines(np.median(d), i - 0.32, i + 0.32, color=colors[k], lw=2.4)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{k}\n(n={len(groups[k])})" for k in order], fontsize=9)
    ax.set_ylabel(ylabel)
    try: kt_stats.add_group_stats(ax, {k: groups[k] for k in order if len(groups[k]) >= 3},
                                  [k for k in order if len(groups[k]) >= 3], loc="upper left")
    except Exception: pass


master, _ = lib.load_master()
M = {r["Batch Name"]: r for r in master}
def mg(b, k): return (M.get(b, {}).get(k) or "").strip()

# ── the ROUNDING SCORE (new) ──────────────────────────────────────────────────────────────────────
circ_frames = collections.defaultdict(list)
for r in rd(f"{A}/cell_outlines.csv"):
    try: P = np.array(json.loads(r["points"]), float)
    except Exception: continue
    if len(P) < 8: continue
    x, y = P[:, 0], P[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    per = float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]]))))
    if per <= 0 or area <= 0: continue
    circ_frames[r["batch"]].append((num(r.get("t_sec")), 4 * np.pi * area / per ** 2))

ROUND = {}
for b, v in circ_frames.items():
    mt, at = hms(mg(b, "Metaphase Start (s)")), hms(mg(b, "Anaphase Onset (s)"))
    inwin = [c for t, c in v if t is not None and mt is not None and at is not None and mt <= t <= at]
    vals = inwin if len(inwin) >= 2 else [c for _, c in v]
    if vals: ROUND[b] = float(np.median(vals))
with open(f"{A}/CELL_ROUNDING_20260727.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["batch", "rounding_circularity", "n_frames", "window"])
    for b in sorted(ROUND):
        mt, at = hms(mg(b, "Metaphase Start (s)")), hms(mg(b, "Anaphase Onset (s)"))
        n_in = sum(1 for t, _ in circ_frames[b] if t is not None and mt is not None and at is not None and mt <= t <= at)
        w.writerow([b, round(ROUND[b], 4), len(circ_frames[b]), "metaphase" if n_in >= 2 else "all frames"])
print(f"rounding score for {len(ROUND)} cells -> annotations/CELL_ROUNDING_20260727.csv")
REPORT.append(f"ROUNDING SCORE: built for {len(ROUND)} cells (median cell circularity, metaphase window "
              f"where available) -> annotations/CELL_ROUNDING_20260727.csv")

# ── Q7b · targeted-chromosome size vs rounding ────────────────────────────────────────────────────
lens = collections.defaultdict(list)
for r in rd(f"{A}/CHROMOSOME_MASTER.csv"):
    L = num(r["length_um"])
    if L is not None: lens[r["batch"]].append(L)
pairs = [(float(np.mean(lens[b])), ROUND[b], float(np.std(lens[b])) if len(lens[b]) > 1 else np.nan)
         for b in lens if b in ROUND]
if len(pairs) >= 8:
    X = np.array([p[0] for p in pairs]); Y = np.array([p[1] for p in pairs])
    fig, axs = plt.subplots(1, 2, figsize=(11.2, 4.8))
    for ax, xv, xl, tag in ((axs[0], X, "mean targeted-chromosome length (µm)", "mean"),
                            (axs[1], np.array([p[2] for p in pairs]), "SD of targeted-chromosome length (µm)", "SD")):
        m = np.isfinite(xv) & np.isfinite(Y)
        ax.scatter(xv[m], Y[m], s=40, color="#3b6fb6", alpha=0.75, edgecolor="white", lw=0.4)
        rho, pv = st.spearmanr(xv[m], Y[m])
        if pv < 0.05:
            bb, aa = np.polyfit(xv[m], Y[m], 1); xf = np.linspace(xv[m].min(), xv[m].max(), 20)
            ax.plot(xf, aa + bb * xf, "-", color="#3b6fb6", lw=2.0)
        ax.text(0.98, 0.98, f"Spearman rho={rho:.2f}, p={pv:.2g}\nN={int(m.sum())} cells", transform=ax.transAxes,
                ha="right", va="top", fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
        ax.set_xlabel(xl); ax.set_ylabel("cell rounding (circularity)")
        ax.set_title(f"{tag} chromosome length vs rounding", loc="left", fontweight="bold", fontsize=10)
        if tag == "mean": r_mean, p_mean = rho, pv
        else: r_sd, p_sd = rho, pv
    fig.suptitle("Q7b · Does targeted-chromosome size set how round the cell gets?", fontsize=11, fontweight="bold")
    save(fig, "QNEW_q7b_chromosize_vs_rounding", "chromosome size (mean and SD) vs cell rounding")
    REPORT.append(f"Q7b ANSWERED: N={len(pairs)} cells. mean length vs rounding rho={r_mean:.2f} p={p_mean:.2g}; "
                  f"SD of length vs rounding rho={r_sd:.2f} p={p_sd:.2g}")
else:
    REPORT.append(f"Q7b SKIPPED: only {len(pairs)} cells have both chromosome lengths and a rounding score")

# ── Q8b · do prophase-ablated cells round less? ───────────────────────────────────────────────────
def phase_of(b):
    """USER RULE (standing, restated 2026-08-03): v2 binning is the STANDARD for every phase split — a batch
    whose Notes carry "v2=prometaphase" is PROMETAPHASE even though the column still reads prophase. Reading
    the raw column here over-counted prophase (whole master: 125 -> 89 under v2)."""
    p = mg(b, "Phase of Ablations").lower()
    return "prometaphase" if (p == "prophase" and lib.is_v2_prometaphase(b)) else p
G = {"prophase": [], "prometaphase": []}
G3 = {"prophase (3-abl)": [], "prometaphase (3-abl)": []}
for b, v in ROUND.items():
    p = phase_of(b)
    if p in G: G[p].append(v)
    if mg(b, "# Sisterless KTs") == "3" and p in ("prophase", "prometaphase"):
        G3[f"{p} (3-abl)"].append(v)
if len(G["prophase"]) >= 3 and len(G["prometaphase"]) >= 3:
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.8))
    cols = {"prophase": "#3b6fb6", "prometaphase": "#d1495b",
            "prophase (3-abl)": "#3b6fb6", "prometaphase (3-abl)": "#d1495b"}
    groups_panel(axs[0], G, ["prophase", "prometaphase"], cols, "cell rounding (circularity)")
    axs[0].set_title("all ablated cells", loc="left", fontweight="bold", fontsize=10)
    p_all = st.mannwhitneyu(G["prophase"], G["prometaphase"], alternative="two-sided")[1]
    p_3 = None
    if all(len(v) >= 3 for v in G3.values()):
        groups_panel(axs[1], G3, list(G3), cols, "cell rounding (circularity)")
        p_3 = st.mannwhitneyu(*G3.values(), alternative="two-sided")[1]
        axs[1].set_title("3-ablation cells only", loc="left", fontweight="bold", fontsize=10)
    else:
        axs[1].axis("off"); axs[1].text(0.5, 0.5, "too few 3-ablation cells with a rounding score",
                                        ha="center", va="center", fontsize=9)
    fig.suptitle("Q8b · Do prophase-ablated cells round less?", fontsize=11, fontweight="bold")
    save(fig, "QNEW_q8b_rounding_prophase_vs_prometaphase", "cell rounding, prophase vs prometaphase ablation")
    REPORT.append(f"Q8b ANSWERED: all cells prophase n={len(G['prophase'])} med={np.median(G['prophase']):.3f} vs "
                  f"prometaphase n={len(G['prometaphase'])} med={np.median(G['prometaphase']):.3f}, MW p={p_all:.3g}"
                  + (f"; 3-ablation only: n={len(G3['prophase (3-abl)'])}/{len(G3['prometaphase (3-abl)'])}, "
                     f"MW p={p_3:.3g}" if p_3 is not None else "; 3-ablation subset too small"))
else:
    REPORT.append("Q8b SKIPPED: too few cells with both a phase-of-ablation and a rounding score")

# ── Q8c · prophase vs prometaphase oscillation at metaphase (+ control) ───────────────────────────
LM = rd(f"{A}/KT_LANDMARK_ANALYSIS_20260723.csv")
series = collections.defaultdict(list)
for r in LM:
    if r["label"] not in ("polar", "paired") or r.get("phase") != "metaphase":
        continue
    t, d = num(r.get("t_sec")), num(r.get("dist_to_plate_um"))
    if t is None or d is None: continue
    series[(r["batch"], r["track_id"], r["label"])].append((t, d))


def jag_amp(v):
    v = sorted(v); dd = np.diff([p[1] for p in v])
    if len(dd) < 4 or np.std(dd) == 0: return None
    rev = float(np.mean(np.sign(dd[1:]) != np.sign(dd[:-1])))
    return rev, float(np.std([p[1] for p in v]))


def cohort(b):
    ot = mg(b, "On-Target / Off-Target").lower()
    if ot.startswith("unmodified") or ot.startswith("off"):
        return "control (unmodified/off-target)"
    p = phase_of(b)
    return p if p in ("prophase", "prometaphase") else None


JAG = collections.defaultdict(lambda: collections.defaultdict(list))
AMP = collections.defaultdict(lambda: collections.defaultdict(list))
for (b, tid, lab), v in series.items():
    if len(v) < 8: continue
    c = cohort(b)
    if c is None: continue
    ja = jag_amp(v)
    if ja is None: continue
    JAG[lab][c].append(ja[0]); AMP[lab][c].append(ja[1])
order = ["control (unmodified/off-target)", "prophase", "prometaphase"]
cols = {"control (unmodified/off-target)": "#7a7a7a", "prophase": "#3b6fb6", "prometaphase": "#d1495b"}
have = [(lab, c) for lab in ("paired", "polar") for c in order if len(JAG[lab][c]) >= 3]
if len(have) >= 2:
    fig, axs = plt.subplots(2, 2, figsize=(11.0, 8.4))
    for i, lab in enumerate(("paired", "polar")):
        for j, (D, yl) in enumerate(((JAG[lab], "direction-reversal fraction"),
                                     (AMP[lab], "excursion SD (µm)"))):
            oo = [c for c in order if len(D[c]) >= 3]
            if not oo:
                axs[i][j].axis("off"); axs[i][j].text(0.5, 0.5, f"no {lab} data", ha="center", va="center"); continue
            groups_panel(axs[i][j], D, oo, cols, yl)
            axs[i][j].set_title(f"{lab} kinetochores — {yl}", loc="left", fontweight="bold", fontsize=9.5)
            axs[i][j].set_xticklabels([c.replace(" (unmodified/off-target)", "\n(control)") + f"\n(n={len(D[c])})" for c in oo],
                                      fontsize=7.5)
    fig.suptitle("Q8c · Metaphase oscillation by ablation phase"
                 + ("" if any(len(JAG[l][order[0]]) >= 3 for l in ("paired", "polar"))
                    else "  (no control cell has KT outlines yet)"), fontsize=11, fontweight="bold")
    save(fig, "QNEW_q8c_oscillation_by_ablation_phase", "metaphase oscillation, prophase vs prometaphase vs control")
    REPORT.append("Q8c ANSWERED: " + "; ".join(
        f"{lab}/{c.split(' ')[0]} n={len(JAG[lab][c])} rev={np.median(JAG[lab][c]):.2f} amp={np.median(AMP[lab][c]):.2f}um"
        for lab, c in have))
else:
    REPORT.append(f"Q8c SKIPPED: only {len(have)} (state, cohort) cells reach 3 tracks with >=8 metaphase frames")

# ── Q3c · anaphase TOWARD-POLE velocity, single vs triple ─────────────────────────────────────────
pole = collections.defaultdict(list)
for r in LM:
    if r.get("phase") != "anaphase": continue
    v = num(r.get("radial_speed_um_s"))
    if v is None: continue
    pole[r["batch"]].append(-v * 60.0)      # radial is toward-plate +; toward-POLE is its negative
g1 = [float(np.median(v)) for b, v in pole.items() if mg(b, "# Sisterless KTs") == "1" and len(v) >= 3]
g3 = [float(np.median(v)) for b, v in pole.items() if mg(b, "# Sisterless KTs") == "3" and len(v) >= 3]
if len(g1) >= 3 and len(g3) >= 3:
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    GG = {"single ablation": g1, "triple ablation": g3}
    groups_panel(ax, GG, list(GG), {"single ablation": "#3b6fb6", "triple ablation": "#d1495b"},
                 "anaphase toward-pole velocity (µm/min)")
    ax.axhline(0, ls=":", color="#999")
    p = st.mannwhitneyu(g1, g3, alternative="two-sided")[1]
    ax.text(0.98, 0.98, f"MW p={p:.3g}\nmed {np.median(g1):.3f} vs {np.median(g3):.3f}", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_title("Q3c · Anaphase toward-pole velocity (signed), single vs triple", loc="left",
                 fontweight="bold", fontsize=10)
    save(fig, "QNEW_q3c_anaphase_towardpole_velocity", "anaphase toward-pole velocity, single vs triple")
    REPORT.append(f"Q3c ANSWERED: single n={len(g1)} med={np.median(g1):.3f} vs triple n={len(g3)} "
                  f"med={np.median(g3):.3f} um/min toward pole, MW p={p:.3g}")
else:
    REPORT.append(f"Q3c SKIPPED: only {len(g1)} single / {len(g3)} triple cells have anaphase radial-velocity frames")

print("\n=== ANSWERS (round 2) ===")
for line in REPORT: print("  " + line)
open(f"{OUT}/ANSWERS2_20260727.txt", "w").write("\n".join(REPORT) + "\n")
