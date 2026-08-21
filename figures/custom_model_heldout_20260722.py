"""custom_model_heldout_20260722.py — train/test evaluation of the sisterless-KT model (user 2026-07-22).

TWO TASKS
  A. CLASSIFY   per chromosome: does it reach the plate, or stay polar?
  B. REGRESS    per cell: how long is metaphase, given the initial conditions?

HELD-OUT DESIGN (user spec)
  * 30% held out, drawn SEPARATELY from each sisterless group (1-sis, 2-sis, 3-sis) so every group is
    represented in both train and test in its own proportion — not 30% of the pooled set, which would
    under-sample the small 2-sisterless group.
  * the split is by CELL, never by chromosome: a cell's chromosomes all land on the same side, otherwise
    the model can memorise the cell rather than learn the biology (multi-sisterless cells share a metaphase).
  * repeated 200x with different random splits, because one split of ~80 cells is noise. We report the
    distribution, not a single lucky number.
  * every score is shown against baselines it must beat: predict-the-mean / majority class, the single
    strongest feature alone, and a shuffled-label control that MUST land at chance.

"Initial conditions" = what is knowable at ablation: how many sisterless kinetochores, the chromosome
lengths involved, and the phase the cell was ablated in.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, numpy as np, matplotlib.pyplot as plt
from collections import defaultdict
from scipy import stats
import lib
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, mean_absolute_error, r2_score

OUT3 = "/Volumes/4 MB/ablation_figures_20260625/group3"; SCRIPT = __file__
lib.apply_style()
RNG = np.random.RandomState(0)
N_REPEATS = 200
TEST_FRAC = 0.30

master, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()

chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    chromo[r["batch"].strip()].append(r)


def nsis(b):
    v = gv(b, "# Sisterless KTs")
    return v if v in ("1", "2", "3") else None


def phase01(b):
    if lib.is_v2_prometaphase(b): return 1.0   # USER RULE: v2 binning is the standard (2026-07-22 sweep)
    p = gv(b, "Phase of Ablations").lower()
    return 1.0 if p.startswith("promet") else (0.0 if p.startswith("proph") else np.nan)


def meta_min(b):
    d = lib.parse_time(gv(b, "Meta Duration (s)"))
    if d is None:
        m0 = lib.parse_time(gv(b, "Metaphase Start (s)")); a0 = lib.parse_time(gv(b, "Anaphase Onset (s)"))
        d = (a0 - m0) if (m0 is not None and a0 is not None) else None
    return d / 60.0 if d and d > 0 else None


def lengths(b):
    out = []
    for r in chromo.get(b, []):
        try: out.append(float(r.get("length_um") or ""))
        except Exception: pass
    return out


def stratified_cell_split(cells, groups, frac, rng):
    """hold out `frac` of the cells WITHIN EACH sisterless group (user spec)."""
    test = set()
    for g in sorted(set(groups.values())):
        members = [c for c in cells if groups[c] == g]
        rng.shuffle(members)
        k = max(1, int(round(frac * len(members))))
        test.update(members[:k])
    return [c for c in cells if c not in test], [c for c in cells if c in test]


# =============================================================== B. REGRESSION
def regression():
    rows = []
    for b in chromo:
        if lib.plot_excluded(b): continue
        n = nsis(b); y = meta_min(b); L = lengths(b)
        if n is None or y is None or not L: continue
        rows.append({
            "b": b, "g": n, "y": y,
            "n_sis": float(n),
            "sum_len": float(np.sum(L)),
            "mean_len": float(np.mean(L)),
            "spread": float(max(L) - min(L)) if len(L) > 1 else 0.0,
            "phase": phase01(b),
        })
    if len(rows) < 25:
        print(f"B regression: only {len(rows)} cells"); return None
    FEATS = ["n_sis", "sum_len", "mean_len", "spread", "phase"]
    cells = [r["b"] for r in rows]
    groups = {r["b"]: r["g"] for r in rows}
    byb = {r["b"]: r for r in rows}
    print(f"\nB. REGRESSION — predict metaphase duration.  N={len(rows)} cells "
          f"({ {g: sum(1 for r in rows if r['g']==g) for g in '123'} })")

    def design(cs, feats):
        X = np.array([[byb[c][f] for f in feats] for c in cs], float)
        y = np.array([byb[c]["y"] for c in cs], float)
        return X, y

    scores = defaultdict(list)
    for rep in range(N_REPEATS):
        rng = np.random.RandomState(rep)
        tr, te = stratified_cell_split(list(cells), groups, TEST_FRAC, rng)
        if len(te) < 5 or len(tr) < 10: continue
        Xtr, ytr = design(tr, FEATS); Xte, yte = design(te, FEATS)
        for nm, mdl, feats in (("full (ridge)", make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=1.0)), FEATS),
                               ("full (forest)", make_pipeline(SimpleImputer(), RandomForestRegressor(
                                   n_estimators=200, random_state=rep, min_samples_leaf=3)), FEATS),
                               ("sum_len only", make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=1.0)), ["sum_len"]),
                               ("n_sis only", make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=1.0)), ["n_sis"])):
            A, ay = design(tr, feats); B, by = design(te, feats)
            mdl.fit(A, ay); p = mdl.predict(B)
            scores[nm + "|R2"].append(r2_score(by, p)); scores[nm + "|MAE"].append(mean_absolute_error(by, p))
        # baselines
        scores["predict-mean|R2"].append(r2_score(yte, np.full(len(yte), ytr.mean())))
        scores["predict-mean|MAE"].append(mean_absolute_error(yte, np.full(len(yte), ytr.mean())))
        yshuf = ytr.copy(); rng.shuffle(yshuf)
        m = make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=1.0)).fit(Xtr, yshuf)
        scores["shuffled control|R2"].append(r2_score(yte, m.predict(Xte)))
    order = ["full (forest)", "full (ridge)", "sum_len only", "n_sis only", "predict-mean", "shuffled control"]
    print(f"   {'model':22s} {'R2 median':>10s} {'[10-90%]':>18s} {'MAE min':>9s}")
    res = {}
    for nm in order:
        r2 = scores.get(nm + "|R2"); mae = scores.get(nm + "|MAE")
        if not r2: continue
        lo, hi = np.percentile(r2, [10, 90])
        res[nm] = {"R2_median": round(float(np.median(r2)), 3), "R2_p10": round(float(lo), 3),
                   "R2_p90": round(float(hi), 3),
                   "MAE_median": round(float(np.median(mae)), 2) if mae else None}
        print(f"   {nm:22s} {np.median(r2):10.3f} {f'[{lo:.2f}, {hi:.2f}]':>18s} "
              f"{(np.median(mae) if mae else float('nan')):9.2f}")
    return {"rows": rows, "scores": scores, "res": res, "order": order}


# =============================================================== A. CLASSIFICATION
def classification():
    rows = []
    for b, rs in chromo.items():
        if lib.plot_excluded(b): continue
        n = nsis(b)
        if n is None: continue
        for r in rs:
            beh = (r.get("behavior") or "").strip()
            if beh not in ("congressed", "at_plate", "noncongression"): continue
            try: L = float(r.get("length_um") or "")
            except Exception: continue
            rows.append({"b": b, "g": n, "y": 0 if beh == "noncongression" else 1,
                         "len": L, "n_sis": float(n), "phase": phase01(b)})
    if len(rows) < 30:
        print(f"A classification: only {len(rows)} chromosomes"); return None
    cells = sorted({r["b"] for r in rows})
    groups = {r["b"]: r["g"] for r in rows}
    print(f"\nA. CLASSIFICATION — plate vs polar.  N={len(rows)} chromosomes from {len(cells)} cells")
    FEATS = ["len", "n_sis", "phase"]
    def design(cs, feats):
        sub = [r for r in rows if r["b"] in set(cs)]
        return (np.array([[r[f] for f in feats] for r in sub], float),
                np.array([r["y"] for r in sub], int))
    aucs = defaultdict(list)
    for rep in range(N_REPEATS):
        rng = np.random.RandomState(rep)
        tr, te = stratified_cell_split(list(cells), groups, TEST_FRAC, rng)
        Xtr, ytr = design(tr, FEATS); Xte, yte = design(te, FEATS)
        if len(set(yte)) < 2 or len(set(ytr)) < 2: continue
        for nm, feats in (("full", FEATS), ("length only", ["len"]), ("n_sis only", ["n_sis"])):
            A, ay = design(tr, feats); B, by = design(te, feats)
            if len(set(ay)) < 2: continue
            m = make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(max_iter=1000)).fit(A, ay)
            aucs[nm].append(roc_auc_score(by, m.predict_proba(B)[:, 1]))
        ysh = ytr.copy(); rng.shuffle(ysh)
        m = make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ysh)
        aucs["shuffled control"].append(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))
    print(f"   {'model':22s} {'AUC median':>11s} {'[10-90%]':>18s}")
    res = {}
    for nm in ("full", "length only", "n_sis only", "shuffled control"):
        v = aucs.get(nm)
        if not v: continue
        lo, hi = np.percentile(v, [10, 90])
        res[nm] = {"AUC_median": round(float(np.median(v)), 3), "p10": round(float(lo), 3), "p90": round(float(hi), 3)}
        print(f"   {nm:22s} {np.median(v):11.3f} {f'[{lo:.2f}, {hi:.2f}]':>18s}")
    return {"aucs": aucs, "res": res}


if __name__ == "__main__":
    print(f"held-out {TEST_FRAC:.0%} of EACH sisterless group, split by CELL, {N_REPEATS} repeats")
    C = classification()
    R = regression()

    # ---- figure: both tasks, distribution of held-out scores vs baselines ----
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.2))
    if C:
        names = [n for n in ("full", "length only", "n_sis only", "shuffled control") if C["aucs"].get(n)]
        axes[0].boxplot([C["aucs"][n] for n in names], labels=[n.replace(" ", "\n") for n in names],
                        showfliers=False)
        axes[0].axhline(0.5, color="#b30000", ls="--", lw=1.3, label="chance")
        axes[0].set_ylabel("Held-out AUC"); axes[0].legend(fontsize=8)
        axes[0].set_title("A. Plate vs polar (per chromosome)", loc="left", fontweight="bold", fontsize=10)
    if R:
        names = [n for n in R["order"] if R["scores"].get(n + "|R2")]
        axes[1].boxplot([R["scores"][n + "|R2"] for n in names],
                        labels=[n.replace(" ", "\n") for n in names], showfliers=False)
        axes[1].axhline(0, color="#b30000", ls="--", lw=1.3, label="no better than the mean")
        axes[1].set_ylabel("Held-out R²"); axes[1].legend(fontsize=8)
        axes[1].set_title("B. Metaphase duration (per cell)", loc="left", fontweight="bold", fontsize=10)
    fig.suptitle(f"Held-out performance — {TEST_FRAC:.0%} of EACH sisterless group held out, split by cell, "
                 f"{N_REPEATS} random repeats", fontweight="bold", fontsize=11, x=.01, ha="left")
    plt.tight_layout(rect=[0, 0, 1, .93])
    fig.savefig(f"{OUT3}/G3_model_heldout_performance.png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    lib.record_plot("G3_model_heldout_performance", ["task", "model", "metric", "value"],
                    ([["classify", n, "AUC", round(float(np.median(v)), 4)] for n, v in (C["aucs"].items() if C else [])] +
                     [["regress", k.split("|")[0], k.split("|")[1], round(float(np.median(v)), 4)]
                      for k, v in (R["scores"].items() if R else [])]),
                    {"test_fraction": TEST_FRAC, "repeats": N_REPEATS,
                     "split": "by cell, stratified within each sisterless group",
                     "classification": (C or {}).get("res"), "regression": (R or {}).get("res")},
                    SCRIPT, "Held-out model performance: behaviour + metaphase duration")
    print("\n-> G3_model_heldout_performance")
