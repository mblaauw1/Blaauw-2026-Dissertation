#!/usr/bin/env python3
"""Her 2026-07-27 question list — answered from the data that already exists, one figure per question.
Every panel prints its own N; a question with too little data is reported as SKIPPED rather than plotted
from a handful of points. Figures go to group7_questions/ with a QNEW_ prefix (they are NOT part of the
Cdc20 deck until she numbers them)."""
import sys, os, csv, collections
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import numpy as np, matplotlib.pyplot as plt
from scipy import stats as st
import lib, kt_stats
lib.apply_style()
ROOT = "/Volumes/4 MB"; csv.field_size_limit(10 ** 9)
OUT = f"{ROOT}/ablation_figures_20260625/group7_questions"; os.makedirs(OUT, exist_ok=True)
A = f"{ROOT}/annotations"
COL1, COL3 = "#3b6fb6", "#d1495b"
REPORT = []


def rd(p):
    return list(csv.DictReader(open(p, newline="")))


def num(v):
    try: return float(str(v).strip())
    except Exception: return None


def save(fig, name, cap):
    fig.tight_layout(); fig.savefig(f"{OUT}/{name}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    try: lib.record_plot(name, ["x"], [], {"family": "questions_20260727"}, script=__file__, caption=cap,
                         source=[f"{A}/CHROMOSOME_MASTER.csv"], key_column=None, fig=fig)
    except Exception: pass
    print("  " + name)


def two_group(ax, a, b, la, lb, ylabel):
    for i, (d, c, l) in enumerate(((a, COL1, la), (b, COL3, lb))):
        if not d: continue
        lib.journal_violin(ax, d, i, c, alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.18, d,
                   s=lib.VIOLIN_DOT_S, color=c, alpha=0.7, lw=0)
        ax.hlines(np.median(d), i - 0.32, i + 0.32, color=c, lw=2.4)
    ax.set_xticks([0, 1]); ax.set_xticklabels([f"{la}\n(n={len(a)})", f"{lb}\n(n={len(b)})"], fontsize=9)
    ax.set_ylabel(ylabel)
    if len(a) >= 3 and len(b) >= 3:
        p = st.mannwhitneyu(a, b, alternative="two-sided")[1]
        ax.text(0.98, 0.98, f"MW p={p:.3g}\nmed {np.median(a):.2f} vs {np.median(b):.2f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=8, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
        return p
    return None


master, _ = lib.load_master()
M = {r["Batch Name"]: r for r in master}
def mg(b, k): return (M.get(b, {}).get(k) or "").strip()
def absn(b):
    return mg(b, "# Sisterless KTs")


# ── Q1. length of chromosomes that STAY POLAR: single vs triple ablation ──────────────────────────
CM = rd(f"{A}/CHROMOSOME_MASTER.csv")
pol = collections.defaultdict(list)
for r in CM:
    L = num(r["length_um"])
    if L is None or r["behavior"] != "noncongression":
        continue
    pol[r["n_sisterless"].strip()].append(L)
a, b = pol.get("1", []), pol.get("3", [])
if len(a) >= 3 and len(b) >= 3:
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    p = two_group(ax, a, b, "single ablation", "triple ablation", "chromosome length (µm)")
    ax.set_title("Q1 · Length of chromosomes that stay polar (non-congressing)", loc="left",
                 fontweight="bold", fontsize=10)
    save(fig, "QNEW_q1_polar_chromolen_single_vs_triple", "polar chromosome length, single vs triple")
    REPORT.append(f"Q1 ANSWERED: polar chromosome length single n={len(a)} med={np.median(a):.2f}um vs "
                  f"triple n={len(b)} med={np.median(b):.2f}um, MW p={p:.3g}")
else:
    REPORT.append(f"Q1 SKIPPED: only {len(a)} single / {len(b)} triple non-congressing chromosomes with a length")


# ── Q2. do rounder cells have more lagging kinetochores? ──────────────────────────────────────────
CO = rd(f"{A}/cell_outlines.csv")
circ = collections.defaultdict(list)
for r in CO:
    pts = r.get("points") or ""
    try: P = np.array(eval(pts), float)
    except Exception: continue
    if len(P) < 8: continue
    x, y = P[:, 0], P[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    per = float(np.sum(np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]]))))
    if per > 0 and area > 0:
        circ[r["batch"]].append(4 * np.pi * area / per ** 2)
lagcount = collections.Counter()
for r in rd(f"{A}/kt_outlines.csv"):
    if r["label"] == "lagging":
        lagcount[r["batch"]] += 1
lag_tracks = collections.defaultdict(set)
for r in rd(f"{A}/KT_OUTLINE_TRACKS_20260723.csv"):
    if r["label"] == "lagging":
        lag_tracks[r["batch"]].add(r["track_id"])
cells = [b for b in circ if b in M]
X = [float(np.median(circ[b])) for b in cells]
Y = [len(lag_tracks.get(b, ())) for b in cells]
if len(cells) >= 8:
    fig, ax = plt.subplots(figsize=(6.8, 5.0))
    ax.scatter(X, Y, s=40, color="#3b6fb6", alpha=0.7, edgecolor="white", lw=0.4)
    rho, pv = st.spearmanr(X, Y)
    ax.text(0.98, 0.98, f"Spearman rho={rho:.2f}, p={pv:.2g}\nN={len(cells)} cells",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("cell circularity (median over frames; 1 = perfectly round)")
    ax.set_ylabel("# lagging kinetochore tracks")
    ax.set_title("Q2 · Do rounder cells have more lagging kinetochores?", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q2_roundness_vs_lagging", "cell roundness vs lagging KT count")
    REPORT.append(f"Q2 ANSWERED: N={len(cells)} cells with both, Spearman rho={rho:.2f} p={pv:.2g} "
                  f"({sum(1 for y in Y if y)} of them have any lagging track)")
else:
    REPORT.append(f"Q2 SKIPPED: only {len(cells)} cells have both a cell outline and KT tracks")


# ── Q3a. anaphase KT speed, single vs triple ─────────────────────────────────────────────────────
LMr = rd(f"{A}/KT_LANDMARK_ANALYSIS_20260723.csv")
sp = collections.defaultdict(list)
for r in LMr:
    if r.get("phase") != "anaphase":
        continue
    v = num(r.get("speed_um_s"))
    if v is None:
        continue
    sp[r["batch"]].append(v * 60.0)          # µm/min
g1 = [float(np.median(v)) for b, v in sp.items() if absn(b) == "1" and len(v) >= 3]
g3 = [float(np.median(v)) for b, v in sp.items() if absn(b) == "3" and len(v) >= 3]
if len(g1) >= 3 and len(g3) >= 3:
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    p = two_group(ax, g1, g3, "single ablation", "triple ablation", "anaphase KT speed (µm/min, per-cell median)")
    ax.set_title("Q3a · Anaphase kinetochore speed, single vs triple", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q3a_anaphase_speed_single_vs_triple", "anaphase KT speed single vs triple")
    REPORT.append(f"Q3a ANSWERED: single n={len(g1)} med={np.median(g1):.3f} vs triple n={len(g3)} "
                  f"med={np.median(g3):.3f} um/min, MW p={p:.3g}")
else:
    REPORT.append(f"Q3a SKIPPED: only {len(g1)} single / {len(g3)} triple cells have anaphase KT frames")

# ── Q3b. anaphase -> cytokinesis duration, single vs triple (master times; much larger N) ─────────
def hms(s):
    s = (s or "").strip()
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try: q = [float(x) for x in s.split(":")]
    except ValueError: return None
    v = q[0]*3600 + q[1]*60 + q[2] if len(q) == 3 else (q[0]*60 + q[1] if len(q) == 2 else q[0])
    return -v if neg else v
d1, d3 = [], []
for r in master:
    an, cy = hms(r.get("Anaphase Onset (s)")), hms(r.get("Cytokinesis Onset (s)"))
    if an is None or cy is None or cy <= an:
        continue
    n = (r.get("# Sisterless KTs") or "").strip()
    (d1 if n == "1" else d3 if n == "3" else []).append((cy - an) / 60.0)
if len(d1) >= 3 and len(d3) >= 3:
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    p = two_group(ax, d1, d3, "single ablation", "triple ablation", "anaphase to cytokinesis (min)")
    ax.set_title("Q3b · Time from anaphase onset to cytokinesis", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q3b_ana_to_cyto_single_vs_triple", "anaphase to cytokinesis, single vs triple")
    REPORT.append(f"Q3b ANSWERED: single n={len(d1)} med={np.median(d1):.1f}min vs triple n={len(d3)} "
                  f"med={np.median(d3):.1f}min, MW p={p:.3g}")
else:
    REPORT.append(f"Q3b SKIPPED: only {len(d1)} single / {len(d3)} triple cells have anaphase AND cytokinesis")


# ── Q4. cells with NEITHER lagging NOR polar: shorter sisterless chromosomes? ─────────────────────
def yes(v): return (v or "").strip().lower().startswith("y")
def no(v):  return (v or "").strip().lower().startswith("n")
clean, messy = [], []
lens = collections.defaultdict(list)
for r in CM:
    L = num(r["length_um"])
    if L is not None: lens[r["batch"]].append(L)
for b, L in lens.items():
    pc, lc = mg(b, "Polar Chromosomes"), mg(b, "Lagging Chromosomes")
    if not pc or not lc: continue
    (clean if (no(pc) and no(lc)) else messy if (yes(pc) or yes(lc)) else []).append(float(np.mean(L)))
if len(clean) >= 3 and len(messy) >= 3:
    fig, ax = plt.subplots(figsize=(6.2, 5.0))
    p = two_group(ax, clean, messy, "no polar, no lagging", "polar and/or lagging",
                  "mean sisterless chromosome length (µm)")
    ax.set_title("Q4 · Are 'clean' cells' sisterless chromosomes shorter?", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q4_clean_vs_messy_chromolen", "chromosome length, clean vs polar/lagging cells")
    REPORT.append(f"Q4 ANSWERED: clean n={len(clean)} med={np.median(clean):.2f}um vs "
                  f"polar/lagging n={len(messy)} med={np.median(messy):.2f}um, MW p={p:.3g}")
else:
    REPORT.append(f"Q4 SKIPPED: only {len(clean)} clean / {len(messy)} polar-or-lagging cells have chromosome lengths")


# ── Q5. in 3-ablation cells, how many polar chromosomes at anaphase? ──────────────────────────────
polar_at_ana = {}
for r in LMr:
    if r["label"] != "polar" or r.get("phase") != "anaphase":
        continue
    polar_at_ana.setdefault(r["batch"], set()).add(r["track_id"])
counts3 = [len(v) for b, v in polar_at_ana.items() if absn(b) == "3"]
counts1 = [len(v) for b, v in polar_at_ana.items() if absn(b) == "1"]
if len(counts3) + len(counts1) >= 5:
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    mx = max(counts3 + counts1 + [1])
    bins = np.arange(0.5, mx + 1.5, 1)
    ax.hist([counts1, counts3], bins=bins, color=[COL1, COL3],
            label=[f"single (n={len(counts1)} cells)", f"triple (n={len(counts3)} cells)"])
    ax.set_xticks(range(1, mx + 1)); ax.set_xlabel("# polar KT tracks still present at anaphase")
    ax.set_ylabel("# cells"); ax.legend(fontsize=8)
    ax.set_title("Q5 · How many polar chromosomes survive to anaphase?", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q5_polar_count_at_anaphase", "polar KT count at anaphase, single vs triple")
    REPORT.append(f"Q5 ANSWERED: triple cells with polar-at-anaphase n={len(counts3)}, "
                  f"counts={sorted(counts3)} (median {np.median(counts3) if counts3 else float('nan'):.1f}); "
                  f"single n={len(counts1)}, counts={sorted(counts1)}")
else:
    REPORT.append(f"Q5 SKIPPED: only {len(counts3)} triple / {len(counts1)} single annotated cells keep a polar KT into anaphase")


# ── Q6. are polar oscillations more jagged than paired? ───────────────────────────────────────────
# jaggedness = median |change in step direction| along the plate-normal axis; per track, metaphase window.
series = collections.defaultdict(list)
for r in LMr:
    if r["label"] not in ("polar", "paired", "lagging"):
        continue
    if r.get("phase") != "metaphase":
        continue
    t, d = num(r.get("t_sec")), num(r.get("dist_to_plate_um"))
    if t is None or d is None: continue
    series[(r["track_id"], r["label"])].append((t, d))
jag = collections.defaultdict(list)
for (tid, lab), v in series.items():
    if len(v) < 8: continue
    v.sort(); d = np.diff([p[1] for p in v])
    if len(d) < 4 or np.std(d) == 0: continue
    rev = float(np.mean(np.sign(d[1:]) != np.sign(d[:-1])))        # fraction of direction reversals
    jag[lab].append(rev)
if len(jag.get("polar", [])) >= 3 and len(jag.get("paired", [])) >= 3:
    order = [k for k in ("paired", "polar", "lagging") if len(jag.get(k, [])) >= 3]
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    cols = {"paired": "#3b6fb6", "polar": "#e6820e", "lagging": "#d1495b"}
    for i, k in enumerate(order):
        d = jag[k]
        lib.journal_violin(ax, d, i, cols[k], alpha=0.28, lw=1.0, min_n=3)
        ax.scatter(np.full(len(d), i) + (np.random.RandomState(i).rand(len(d)) - 0.5) * 0.18, d,
                   s=lib.VIOLIN_DOT_S, color=cols[k], alpha=0.7, lw=0)
        ax.hlines(np.median(d), i - 0.32, i + 0.32, color=cols[k], lw=2.4)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"{k}\n(n={len(jag[k])})" for k in order], fontsize=9)
    ax.set_ylabel("direction-reversal fraction (jaggedness)")
    kt_stats.add_group_stats(ax, {k: jag[k] for k in order}, order, loc="upper left")
    ax.set_title("Q6 · Are polar oscillations more jagged? (metaphase, per track)", loc="left",
                 fontweight="bold", fontsize=10)
    save(fig, "QNEW_q6_oscillation_jaggedness", "oscillation jaggedness by state")
    REPORT.append("Q6 ANSWERED: " + "; ".join(f"{k} n={len(jag[k])} med={np.median(jag[k]):.2f}" for k in order))
else:
    REPORT.append(f"Q6 SKIPPED: too few metaphase tracks with >=8 frames "
                  f"(polar {len(jag.get('polar', []))}, paired {len(jag.get('paired', []))})")


# ── Q7. targeted-chromosome size vs metaphase duration ────────────────────────────────────────────
X7, Y7 = [], []
for b, L in lens.items():
    md = None
    an, mt = hms(mg(b, "Anaphase Onset (s)")), hms(mg(b, "Metaphase Start (s)"))
    if an is not None and mt is not None and an > mt: md = (an - mt) / 60.0
    if md is None: continue
    X7.append(float(np.mean(L))); Y7.append(md)
if len(X7) >= 8:
    fig, ax = plt.subplots(figsize=(6.8, 5.0))
    ax.scatter(X7, Y7, s=40, color="#3b6fb6", alpha=0.7, edgecolor="white", lw=0.4)
    rho, pv = st.spearmanr(X7, Y7)
    if pv < 0.05:
        bb, aa = np.polyfit(X7, Y7, 1); xf = np.linspace(min(X7), max(X7), 20)
        ax.plot(xf, aa + bb * xf, "-", color="#3b6fb6", lw=2.0)
    ax.text(0.98, 0.98, f"Spearman rho={rho:.2f}, p={pv:.2g}\nN={len(X7)} cells", transform=ax.transAxes,
            ha="right", va="top", fontsize=8, family="monospace",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    ax.set_xlabel("mean targeted-chromosome length (µm)"); ax.set_ylabel("Metaphase duration (min)")
    ax.set_title("Q7 · Does targeted-chromosome size set time in metaphase?", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q7_chromolen_vs_metaphase_duration", "chromosome length vs metaphase duration")
    REPORT.append(f"Q7 ANSWERED (duration half): N={len(X7)} cells, Spearman rho={rho:.2f} p={pv:.2g}. "
                  f"The ROUNDING half needs a per-cell rounding score — see the report.")
else:
    REPORT.append(f"Q7 SKIPPED: only {len(X7)} cells have both chromosome lengths and a metaphase duration")


# ── Q8. prophase vs prometaphase ablation: sisterless-KT fate distribution ────────────────────────
fate = collections.defaultdict(lambda: collections.Counter())
for r in master:
    # USER RULE (standing, restated 2026-08-03): v2 binning is the STANDARD for every phase split. A batch
    # whose Notes carry "v2=prometaphase" counts as PROMETAPHASE even though its "Phase of Ablations" column
    # still reads prophase. This plot was reading the raw column, which over-counted prophase.
    phv = (r.get("Phase of Ablations") or "").strip().lower()
    if phv == "prophase" and lib.is_v2_prometaphase(r.get("Batch Name", "")): phv = "prometaphase"
    if phv not in ("prophase", "prometaphase"): continue
    pc, lc = r.get("Polar Chromosomes"), r.get("Lagging Chromosomes")
    if not (pc or "").strip() or not (lc or "").strip(): continue
    k = ("polar+lagging" if (yes(pc) and yes(lc)) else "polar only" if yes(pc)
         else "lagging only" if yes(lc) else "neither")
    fate[phv][k] += 1
if sum(sum(v.values()) for v in fate.values()) >= 12:
    order = ["neither", "polar only", "lagging only", "polar+lagging"]
    fig, ax = plt.subplots(figsize=(7.0, 4.8))
    w = 0.38
    for i, phv in enumerate(("prophase", "prometaphase")):
        tot = sum(fate[phv].values()) or 1
        vals = [100.0 * fate[phv][k] / tot for k in order]
        ax.bar(np.arange(len(order)) + (i - 0.5) * w, vals, width=w,
               color=[COL1, COL3][i], label=f"{phv} (n={tot} cells)")
    ax.set_xticks(range(len(order))); ax.set_xticklabels(order, fontsize=9)
    ax.set_ylabel("% of cells"); ax.legend(fontsize=8)
    tab = [[fate["prophase"][k] for k in order], [fate["prometaphase"][k] for k in order]]
    try:
        chi = st.chi2_contingency(np.array(tab) + 0.0)[1]
        ax.text(0.98, 0.98, f"chi-square p={chi:.3g}", transform=ax.transAxes, ha="right", va="top",
                fontsize=8, family="monospace", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#bbb", alpha=0.85))
    except Exception:
        chi = float("nan")
    ax.set_title("Q8 · Sisterless-KT fate: prophase vs prometaphase ablation", loc="left", fontweight="bold", fontsize=10)
    save(fig, "QNEW_q8_fate_prophase_vs_prometaphase", "fate distribution, prophase vs prometaphase ablation")
    REPORT.append(f"Q8 ANSWERED (fate half): prophase n={sum(fate['prophase'].values())}, "
                  f"prometaphase n={sum(fate['prometaphase'].values())}, chi-square p={chi:.3g}")
else:
    REPORT.append("Q8 SKIPPED: too few cells with both a phase-of-ablation and polar/lagging scoring")

print("\n=== ANSWERS ===")
for line in REPORT:
    print("  " + line)
open(f"{OUT}/ANSWERS_20260727.txt", "w").write("\n".join(REPORT) + "\n")
