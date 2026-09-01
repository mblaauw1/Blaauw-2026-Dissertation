"""custom_length_spread_20260722.py — chromosome-length summaries vs metaphase duration (user 2026-07-22).

Three per-cell summaries of the SISTERLESS chromosome lengths, each against metaphase duration:
  G3_length_spread_maxmin_vs_metaphase   max - min   (the retired plot's most likely definition)
  G3_length_spread_sd_vs_metaphase       standard deviation
  G3_length_sum_vs_metaphase             SUM of the sisterless chromosome lengths in the cell

The retired `G3_length_spread_vs_metaphase_duration` recorded rho=0.300 p=0.0571 N=41 but never recorded
WHICH spread statistic it used; max-min and SD both land near it (0.312 / 0.283 on today's data, N=42),
so both are built rather than one being guessed.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT = __file__
lib.apply_style()
master, _ = lib.load_master_plots(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

ch = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    if lib.is_prophase_ablation(r.get("batch","")): continue   # prophase excluded (no prophase group)
    ch[r["batch"].strip()].append(r)

def meta_min(b):
    d = lib.parse_time(gv(b, "Meta Duration (s)"))
    if d is None:
        m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        d = (a0 - m0) if (m0 is not None and a0 is not None) else None
    return d / 60.0 if d and d > 0 else None

STATS = [("maxmin", lambda L: max(L) - min(L), "Length spread: max - min (µm)",
          "Does a WIDER spread of sisterless chromosome lengths prolong metaphase?", 2),
         ("sd", lambda L: float(np.std(L, ddof=1)), "Length spread: SD (µm)",
          "Does a more VARIABLE set of sisterless chromosome lengths prolong metaphase?", 2),
         ("sum", lambda L: float(np.sum(L)), "Summed sisterless chromosome length (µm)",
          "Does a bigger TOTAL sisterless chromosome load prolong metaphase?", 1)]

# ITEM 26 (user 2026-08-04, REPEAT of earlier feedback): the sd and sum plots must be SPLIT by sisterless
# number — "lumped together its meaningless". 1- and 3-sisterless only; 2-sisterless left out for simplicity.
# The sisterless count comes from the master "# Sisterless KTs" column (never from batch/file names).
SPLIT_GROUPS = ("1", "3")
SPLIT_KEYS   = {"sd", "sum"}
PAL = {"1": lib.PALETTE["1-Sister"], "3": lib.PALETTE["3-Sister"]}

def nsis(b): return gv(b, "# Sisterless KTs")

for key, fn, xlab, title, minn in STATS:
    X, Y, C, G = [], [], [], []
    for b, rs in ch.items():
        if lib.plot_excluded(b): continue
        L = []
        for r in rs:
            try: L.append(float(r.get("length_um") or ""))
            except Exception: pass
        if len(L) < minn: continue
        m = meta_min(b)
        if m is None: continue
        X.append(fn(L)); Y.append(m); C.append(b); G.append(nsis(b))
    if len(X) < 5:
        print(f"{key}: only {len(X)} cells"); continue
    X = np.array(X); Y = np.array(Y); G = np.array(G)
    name = {"maxmin": "G3_length_spread_maxmin_vs_metaphase",
            "sd": "G3_length_spread_sd_vs_metaphase",
            "sum": "G3_length_sum_vs_metaphase"}[key]

    if key in SPLIT_KEYS:
        keep = np.isin(G, SPLIT_GROUPS)
        Xs, Ys, Gs = X[keep], Y[keep], G[keep]
        Cs = [c for c, k in zip(C, keep) if k]
        # A 1-sisterless cell has ONE sisterless chromosome, so a within-cell SPREAD (sd / max-min) does not
        # exist for it — N=0 is structural, not missing data. Drop the empty panel rather than draw a blank one,
        # and say so on the figure: the pre-split "pooled" SD plot therefore never contained a 1-sisterless cell.
        present = [g for g in SPLIT_GROUPS if (Gs == g).sum() > 0]
        absent  = [g for g in SPLIT_GROUPS if (Gs == g).sum() == 0]
        fig, axes = plt.subplots(1, len(present), figsize=(5.6 * len(present), 5), sharey=True, squeeze=False)
        axes = axes[0]
        stat_by_group = {g: {"N": 0, "rho": None, "p": None} for g in absent}
        for ax, g in zip(axes, present):
            m = Gs == g
            gx, gy = Xs[m], Ys[m]
            ax.scatter(gx, gy, s=44, color=PAL[g], alpha=.85, edgecolor="white", lw=.5)
            rr = pp = float("nan")
            if m.sum() >= 4:
                rr, pp = stats.spearmanr(gx, gy)
                sl, c0 = np.polyfit(gx, gy, 1); xr = np.linspace(gx.min(), gx.max(), 20)
                ax.plot(xr, sl * xr + c0, "--", color=PAL[g], lw=1.6)
            stat_by_group[g] = {"N": int(m.sum()), "rho": None if np.isnan(rr) else round(float(rr), 3),
                                "p": None if np.isnan(pp) else float(pp)}
            ax.set_xlabel(xlab)
            ax.set_title(f"{lib.lbl(g+'-Sister')}  ·  N={m.sum()}"
                         + ("" if np.isnan(rr) else f"; rho={rr:.2f}, p={pp:.3g}"),
                         loc="left", fontweight="bold", fontsize=10)
        axes[0].set_ylabel("Metaphase duration (min)")
        _note = ("" if not absent else
                 f"  {'/'.join(absent)}-sisterless has no panel: a within-cell length SPREAD needs >=2 sisterless "
                 f"chromosomes, so it is undefined for a 1-sisterless cell — the previously POOLED version of this "
                 f"plot therefore contained no 1-sisterless cells at all.")
        fig.suptitle(f"{title}\nSPLIT by sisterless number (item 26) — 2-sisterless omitted; pooling these groups is "
                     f"uninterpretable because their metaphase durations differ systematically.{_note}",
                     x=.01, ha="left", fontweight="bold", fontsize=9)
        plt.tight_layout(); fig.savefig(f"{OUT3}/{name}.png", bbox_inches="tight", dpi=130); plt.close(fig)
        lib.record_plot(name, ["batch", "n_sisterless", "x_um", "meta_min"],
                        [[c, g, round(a, 3), round(y, 2)] for c, g, a, y in zip(Cs, Gs, Xs, Ys)],
                        {"statistic": key, "split": "by # Sisterless KTs (1 vs 3); 2-sisterless omitted",
                         "per_group": stat_by_group, "N": int(len(Xs)),
                         "x_label": xlab, "y_label": "Metaphase duration (min)"},
                        SCRIPT, title + " — split by sisterless number")
        print(f"{name}: SPLIT " + "  ".join(
            f"{g}-sis N={stat_by_group[g]['N']} rho={stat_by_group[g]['rho']} p={stat_by_group[g]['p']}"
            for g in SPLIT_GROUPS))
        continue

    rho, pv = stats.spearmanr(X, Y)
    fig, ax = plt.subplots(figsize=(6.4, 5))
    ax.scatter(X, Y, s=44, color="#1b7837", alpha=.85, edgecolor="#0b3d1b")
    if len(X) >= 4:
        m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(X.min(), X.max(), 20)
        ax.plot(xr, m * xr + c0, "--", color="#b30000", lw=1.6)
    ax.set_xlabel(xlab); ax.set_ylabel("Metaphase duration (min)")
    ax.set_title(f"{title}\nN={len(X)} cells; Spearman rho={rho:.2f}, p={pv:.3g}",
                 loc="left", fontweight="bold", fontsize=10)
    plt.tight_layout(); fig.savefig(f"{OUT3}/{name}.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot(name, ["batch", "x_um", "meta_min"],
                    [[c, round(a, 3), round(y, 2)] for c, a, y in zip(C, X, Y)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X), "statistic": key},
                    SCRIPT, title)
    print(f"{name}: N={len(X)} rho={rho:.3f} p={pv:.3g}")
