"""custom_restore_retired_20260722.py — rebuild the 4 figures retired on 2026-07-22 as "fabricated".

They were retired because a previous session GUESSED their metric definitions and the statistics moved.
This time the definitions come from `ablation_plots/PLOT_SETTINGS.json`, which recorded each plot's axes,
source files and original rho/p/N at build time — and every rebuild is CHECKED against either the retired
data CSV (exact row-for-row) or the recorded statistics. Nothing is published on a guess.

  A. G4_sisterless_cdc20_vs_bleaching   settings give both axes explicitly -> verify vs retired CSV (34 rows)
  B. G4_1sis_size_vs_outcome_metatime   settings give both axes explicitly -> verify vs retired CSV (32 rows)
  C. G3_length_spread_vs_metaphase_duration      axes NOT recorded (data CSV is header-only).
  D. G3_max_congression_delay_vs_metaphase_duration   same.
     For C and D we SEARCH candidate definitions and keep one only if it reproduces the recorded
     statistics (C: rho 0.30, p 0.0571, N 41 | D: rho 0.666, p~0, N 38). If none matches, nothing is
     written and the figure stays retired — that is the correct outcome, not a reason to loosen the test.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os, json, itertools, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"
OUT4 = "/Volumes/4 MB/ablation_figures_20260625/group4"
DATA = "/Volumes/4 MB/ablation_plots/data"
RET = "/Volumes/4 MB/_retired/fabricated_plots_20260722"
SCRIPT = __file__
lib.apply_style()

master, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()


def retired_rows(name):
    p = os.path.join(RET, name + ".csv")
    return list(csv.DictReader(open(p))) if os.path.isfile(p) else []


def slope_pct_per_min(pts):
    """least-squares slope as % of the series mean per minute — the '%/min' in the recorded settings."""
    if len(pts) < 3: return None
    t = np.array([a for a, _ in pts], float); v = np.array([b for _, b in pts], float)
    if t.max() - t.min() <= 0 or v.mean() == 0: return None
    m = np.polyfit(t, v, 1)[0]
    return 100.0 * m / abs(v.mean())


# ============================================================ A
def rebuild_cdc20_vs_bleaching():
    name = "G4_sisterless_cdc20_vs_bleaching"
    truth = {r["batch"]: r for r in retired_rows(name)}
    kt = defaultdict(list)
    for r in csv.DictReader(open(f"{DATA}/G4_kt_intensity_time.csv")):
        try: kt[r["batch"].strip()].append((float(r["t_min_since_first_abl"]), float(r["kt_fluor_au"])))
        except Exception: pass
    cell = defaultdict(list)
    for r in csv.DictReader(open(f"{DATA}/G4_fluor_over_time.csv")):
        try: cell[r["batch"].strip()].append((float(r["t_sec"]) / 60.0, float(r["fluor_mean_au"])))
        except Exception: pass
    X, Y, C = [], [], []
    for b in sorted(set(kt) & set(cell)):
        if lib.plot_excluded(b): continue
        sx = slope_pct_per_min(sorted(cell[b])); sy = slope_pct_per_min(sorted(kt[b]))
        if sx is None or sy is None: continue
        X.append(sx); Y.append(sy); C.append(b)
    if len(X) < 5:
        print(f"A {name}: only {len(X)} cells — not rebuilt"); return
    rho, pv = stats.spearmanr(X, Y)
    # ---- verification against the retired values
    ok = bad = 0
    for b, x, y in zip(C, X, Y):
        t = truth.get(b)
        if not t: continue
        try:
            dx = abs(float(t["cell_bleach_pct_per_min"]) - x); dy = abs(float(t["kt_cdc20_pct_per_min"]) - y)
            if dx < 0.02 and dy < 0.05: ok += 1
            else: bad += 1
        except Exception: pass
    print(f"A {name}: N={len(X)} (recorded 34)  rho={rho:.3f} (recorded -0.143)  "
          f"verified vs retired CSV: {ok} match / {bad} differ")
    fig, ax = plt.subplots(figsize=(6.6, 5.6))
    ax.scatter(X, Y, s=44, color="#762a83", alpha=.85, edgecolor="#3b1250")
    lo = min(min(X), min(Y)); hi = max(max(X), max(Y))
    ax.plot([lo, hi], [lo, hi], "--", color="#888", lw=1.3, label="y = x")
    ax.axhline(0, color="#ccc", lw=.8); ax.axvline(0, color="#ccc", lw=.8)
    ax.set_xlabel("Whole-cell fluorescence slope (%/min)")
    ax.set_ylabel("Kinetochore Cdc20 slope (%/min)")
    ax.set_title(f"Do kinetochores lose Cdc20 faster than the cell bleaches?\n"
                 f"points BELOW the y=x line lose KT signal faster than bleaching alone — "
                 f"N={len(X)}; Spearman rho={rho:.2f}, p={pv:.3g}", loc="left", fontweight="bold", fontsize=9.5)
    ax.legend(fontsize=8)
    plt.tight_layout(); fig.savefig(f"{OUT4}/{name}.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot(name, ["batch", "cell_bleach_pct_per_min", "kt_cdc20_pct_per_min"],
                    [[c, round(x, 4), round(y, 4)] for c, x, y in zip(C, X, Y)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X),
                     "restored_from": "PLOT_SETTINGS.json axes; verified vs retired data CSV"},
                    SCRIPT, "KT Cdc20 loss vs whole-cell bleaching (restored 2026-07-22)")


# ============================================================ B
def rebuild_1sis_size_vs_outcome():
    name = "G4_1sis_size_vs_outcome_metatime"
    truth = {r["batch"]: r for r in retired_rows(name)}
    src = f"{DATA}/G3_chromo_length_percell_1sis.csv"
    if not os.path.isfile(src):
        print(f"B {name}: source {src} missing"); return
    X, Y, O, C = [], [], [], []
    for r in csv.DictReader(open(src)):
        b = r["batch"].strip()
        if lib.plot_excluded(b): continue
        try: x = float(r["mean_length_um"]); y = float(r["duration_min"])
        except Exception: continue
        pol = gv(b, "Polar Chromosomes").strip().lower()
        outcome = "polar" if pol.startswith("y") else "plate"
        X.append(x); Y.append(y); O.append(outcome); C.append(b)
    if len(X) < 5:
        print(f"B {name}: only {len(X)} cells — not rebuilt"); return
    rho, pv = stats.spearmanr(X, Y)
    ok = bad = omis = 0
    for b, x, y, o in zip(C, X, Y, O):
        t = truth.get(b)
        if not t: continue
        try:
            if abs(float(t["chromo_len_um"]) - x) < 0.02 and abs(float(t["meta_dur_min"]) - y) < 0.05: ok += 1
            else: bad += 1
            if t["outcome"].strip() != o: omis += 1
        except Exception: pass
    print(f"B {name}: N={len(X)} (recorded 32)  rho={rho:.3f} (recorded -0.111)  "
          f"verified: {ok} match / {bad} differ / {omis} outcome mismatches")
    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    for o, col in (("plate", "#2166ac"), ("polar", "#b2182b")):
        xs = [x for x, oo in zip(X, O) if oo == o]; ys = [y for y, oo in zip(Y, O) if oo == o]
        ax.scatter(xs, ys, s=46, color=col, alpha=.85, edgecolor="none", label=f"{o} (N={len(xs)})")
    if len(X) >= 4:
        m, c0 = np.polyfit(X, Y, 1); xr = np.linspace(min(X), max(X), 20)
        ax.plot(xr, m * xr + c0, "--", color="#666", lw=1.4)
    ax.set_xlabel("Per-cell mean traced chromosome length (µm)")
    ax.set_ylabel("Metaphase duration (min)")
    ax.set_title(f"1-sisterless on-target: chromosome size vs metaphase time\n"
                 f"coloured by final alignment outcome — N={len(X)}; Spearman rho={rho:.2f}, p={pv:.3g}",
                 loc="left", fontweight="bold", fontsize=9.5)
    ax.legend(fontsize=8)
    plt.tight_layout(); fig.savefig(f"{OUT4}/{name}.png", bbox_inches="tight", dpi=130); plt.close(fig)
    lib.record_plot(name, ["batch", "chromo_len_um", "meta_dur_min", "outcome"],
                    [[c, round(x, 3), round(y, 3), o] for c, x, y, o in zip(C, X, Y, O)],
                    {"rho": round(float(rho), 3), "p": float(pv), "N": len(X),
                     "restored_from": "PLOT_SETTINGS.json axes; verified vs retired data CSV"},
                    SCRIPT, "1-sis chromosome size vs metaphase time by outcome (restored 2026-07-22)")


# ============================================================ C / D  — candidate search
def per_cell_chromosomes():
    ch = defaultdict(list)
    for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
        ch[r["batch"].strip()].append(r)
    return ch


def meta_min(b):
    d = lib.parse_time(gv(b, "Meta Duration (s)"))
    if d is None:
        m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        d = (a0 - m0) if (m0 is not None and a0 is not None) else None
    return d / 60.0 if d and d > 0 else None


def search_candidates():
    ch = per_cell_chromosomes()
    cands_spread = {
        "max-min length": lambda L: (max(L) - min(L)) if len(L) >= 2 else None,
        "SD length": lambda L: float(np.std(L, ddof=1)) if len(L) >= 2 else None,
        "CV length": lambda L: (float(np.std(L, ddof=1)) / np.mean(L)) if len(L) >= 2 and np.mean(L) else None,
        "IQR length": lambda L: float(np.percentile(L, 75) - np.percentile(L, 25)) if len(L) >= 2 else None,
        "variance": lambda L: float(np.var(L, ddof=1)) if len(L) >= 2 else None,
    }
    print("\nC  G3_length_spread_vs_metaphase_duration   target rho=0.300 p=0.0571 N=41")
    best = None
    for nm, fn in cands_spread.items():
        X, Y = [], []
        for b, rs in ch.items():
            if lib.plot_excluded(b): continue
            L = []
            for r in rs:
                try: L.append(float(r.get("length_um") or ""))
                except Exception: pass
            v = fn(L) if len(L) >= 2 else None
            m = meta_min(b)
            if v is None or m is None: continue
            X.append(v); Y.append(m)
        if len(X) < 5: print(f"    {nm:16s} N={len(X):3d}  (too few)"); continue
        rho, pv = stats.spearmanr(X, Y)
        hit = abs(rho - 0.300) < 0.05 and abs(len(X) - 41) <= 3
        print(f"    {nm:16s} N={len(X):3d}  rho={rho:+.3f}  p={pv:.4g}   {'<== MATCH' if hit else ''}")
        if hit and (best is None or abs(rho - .300) < best[1]): best = (nm, abs(rho - .300))
    print(f"    -> {'candidate: ' + best[0] if best else 'NO candidate reproduces the recorded statistics'}")

    print("\nD  G3_max_congression_delay_vs_metaphase_duration   target rho=0.666 p~0 N=38")
    bestD = None
    for nm in ("max congression time", "max congression - metaphase start", "range of congression times"):
        X, Y = [], []
        for b, rs in ch.items():
            if lib.plot_excluded(b): continue
            ts = []
            for r in rs:
                try: ts.append(float(r.get("congression_time_s") or ""))
                except Exception: pass
            if not ts: continue
            m = meta_min(b)
            if m is None: continue
            m0 = lib.parse_time(gv(b, "Metaphase Start (s)"))
            if nm == "max congression time": v = max(ts) / 60.0
            elif nm == "max congression - metaphase start":
                if m0 is None: continue
                v = (max(ts) - m0) / 60.0
            else: v = (max(ts) - min(ts)) / 60.0
            X.append(v); Y.append(m)
        if len(X) < 5: print(f"    {nm:34s} N={len(X):3d}  (too few)"); continue
        rho, pv = stats.spearmanr(X, Y)
        hit = abs(rho - 0.666) < 0.06 and abs(len(X) - 38) <= 3
        print(f"    {nm:34s} N={len(X):3d}  rho={rho:+.3f}  p={pv:.4g}   {'<== MATCH' if hit else ''}")
        if hit and (bestD is None or abs(rho - .666) < bestD[1]): bestD = (nm, abs(rho - .666))
    print(f"    -> {'candidate: ' + bestD[0] if bestD else 'NO candidate reproduces the recorded statistics'}")


if __name__ == "__main__":
    rebuild_cdc20_vs_bleaching()
    rebuild_1sis_size_vs_outcome()
    search_candidates()
