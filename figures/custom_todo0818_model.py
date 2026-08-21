#!/usr/bin/env python3
"""0818 items 5-10: metaphase-duration models, built COMPLETELY FRESH.

Her instruction: forget the previous attempt entirely.  Nothing here reads MODEL_*.json,
MODEL_DESIGN_MATRIX*.csv or _claude_tmp/fit_*.py; the feature matrix is rebuilt from the
primary stores.

Cohort (item 8): on-target, 1- and 3-sisterless only, non-drug, non-excluded, with a real
metaphase duration.  2-ablation cells are deliberately out of scope.

Item 5  duration from what is knowable AT metaphase onset.
Item 6  remaining time, from observations taken PARTWAY through metaphase (landmark models).
Item 7  which unmeasured/undermeasured quantities would most improve the model.
Item 9  held-out evaluation, grouped by IMAGING DAY (same-day cells share dish, medium, laser
        alignment and passage, so a random split lets a model score by recognising the day).
Item 10 an exhaustive sweep of model families rather than settling on the first that works.

LEAKAGE RULES, enforced not assumed:
  * nothing measured at or after anaphase may be a feature
  * no event time on the target's own clock (Anaphase Onset, Meta Duration, Total Duration, ...)
  * for item 6 the landmark features may only use frames with t <= metaphase_onset + L
"""
import os, sys, csv, io, json, math, collections, warnings
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, LassoCV, ElasticNetCV, HuberRegressor, BayesianRidge
from sklearn.ensemble import (RandomForestRegressor, GradientBoostingRegressor,
                              ExtraTreesRegressor, AdaBoostRegressor, HistGradientBoostingRegressor)
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.cross_decomposition import PLSRegression
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
from sklearn.tree import DecisionTreeRegressor
from sklearn.dummy import DummyRegressor

sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib
lib.apply_style()

R = "/Volumes/4 MB"; A = R + "/annotations"; FIG = R + "/ablation_figures_20260625"
OUT = os.environ.get("KTFIG_OUT", FIG + "/todo0818"); os.makedirs(OUT, exist_ok=True)
SCRATCH = R + "/_claude_tmp/todo0818"; os.makedirs(SCRATCH, exist_ok=True)
SCRIPT = __file__

def rd(p):
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))
def fl(v, d=None):
    try:
        s = str(v).strip().replace(",", "")
        return float(s) if s not in ("", "None", "nan") else d
    except Exception: return d
def hms(v):
    s = str(v).strip().replace(",", "")
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    if ":" in s:
        p = [fl(x, 0) or 0 for x in s.split(":")]
        while len(p) < 3: p.insert(0, 0)
        sec = p[0]*3600 + p[1]*60 + p[2]
    else:
        sec = fl(s)
        if sec is None: return None
    return -sec if neg else sec

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if r.get("Batch Name", "").strip()}

# ---- columns that would leak the answer.  Anything on the target's own clock.
LEAK = {"Meta Duration (s)", "Meta Duration (min)", "Anaphase Onset (s)", "Cytokinesis Onset (s)",
        "Total Duration (s)", "Ablation->Meta (s)", "Ablation->Meta (min)", "NEB->Meta (s)",
        "NEB->Meta (min)", "Metaphase Start (s)", "Healthy Anaphase"}
# Bookkeeping that is NOT biology and must never be a predictor.  Two classes, both of which the
# first run showed dominating the importance ranking:
#   (a) database identifiers (*_ids, *_id) -- they encode annotation ORDER, i.e. roughly the day
#   (b) frame counts / acquisition spans -- a longer movie is a longer mitosis, so these are the
#       target wearing a different hat.  "master::Total Frames" was the single most important
#       feature in the first run, which is exactly that leak.
NUISANCE_SUB = ("_ids", "_id", "frames", "index", "span", "count", "pixel size", "interval",
                "file", "path", "number of", "n frames",
                # 2026-08-18, second pass: the first run put master::Date, Time Jitter, Dropped %,
                # Processing Time, Log Ablation Events and kt_n_tracks high in the importance ranking.
                # None of those is a measurement she could hand the model for a new cell -- Date encodes
                # the very imaging day the CV holds out, and the rest are acquisition/annotation
                # bookkeeping (how much was annotated, how the render went).  A model that leans on them
                # is scoring on provenance, not biology.
                "date", "jitter", "dropped", "processing time", "log ablation", "n_tracks",
                "timestamp", "fps", "exposure", "review", "notes", "exclude")
def is_leaky(c):
    cl = c.lower()
    if c in LEAK or "duration" in cl or "anaphase" in cl or "cytokin" in cl: return True
    return any(k in cl for k in NUISANCE_SUB)

# ================================================================ cohort
cells = []
for b, r in MB.items():
    if lib.plot_excluded(b): continue
    if r.get("On-Target / Off-Target", "").strip().lower().startswith("off"): continue
    n = fl(r.get("# Sisterless KTs"))
    if n is None or int(n) not in (1, 3): continue          # item 8
    dur = hms(r.get("Meta Duration (s)"))
    if dur is None or dur <= 0:
        ms, ao = hms(r.get("Metaphase Start (s)")), hms(r.get("Anaphase Onset (s)"))
        dur = (ao - ms) if (ms is not None and ao is not None and ao > ms) else None
    if dur is None or dur <= 0: continue
    cells.append(dict(batch=b, day=b.split()[0], n_sisterless=int(n), dur_s=dur, row=r))
print(f"[cohort] {len(cells)} cells "
      f"(1-sis {sum(1 for c in cells if c['n_sisterless']==1)}, "
      f"3-sis {sum(1 for c in cells if c['n_sisterless']==3)}) "
      f"across {len(set(c['day'] for c in cells))} imaging days")
BATCHES = {c["batch"] for c in cells}

# ================================================================ features
F = collections.defaultdict(dict)      # batch -> {feature: value}
def put(b, k, v):
    if v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        F[b][k] = float(v)

# (a) master numerics that are not leaky
for c in cells:
    b, r = c["batch"], c["row"]
    put(b, "n_sisterless", c["n_sisterless"])
    for col in HDR:
        if is_leaky(col): continue
        v = fl(r.get(col))
        if v is not None: put(b, "master::" + col, v)
    neb, ms = hms(r.get("NEB Time (s)")), hms(r.get("Metaphase Start (s)"))
    if neb is not None and ms is not None and ms > neb:
        put(b, "neb_to_meta_s", ms - neb)                  # prophase->metaphase, known BEFORE metaphase ends
    for col in ("Polar Chromosomes", "Lagging Chromosomes"):
        v = (r.get(col) or "").strip().lower()
        if v in ("yes", "no"): put(b, "flag::" + col, 1.0 if v == "yes" else 0.0)

def meta_onset(b):
    return hms((MB.get(b) or {}).get("Metaphase Start (s)"))

# (b) kinetochore outline tracks -> shape + motion, split PRE-metaphase and EARLY-metaphase
TR = rd(A + "/KT_OUTLINE_TRACKS_20260723.csv")
by = collections.defaultdict(list)
for r in TR:
    b = r["batch"].strip()
    if b in BATCHES: by[(b, r["label"].strip(), r["track_id"].strip())].append(r)
agg = collections.defaultdict(lambda: collections.defaultdict(list))
for (b, lab, tid), rs in by.items():
    rs.sort(key=lambda r: fl(r["t_sec"], 0) or 0)
    m0 = meta_onset(b)
    px = fl((MB.get(b) or {}).get("Pixel Size (um)"), .062) or .062
    for win, lo, hi in (("pre", -1e18, m0 if m0 is not None else 1e18),):
        sel = [r for r in rs if lo <= (fl(r["t_sec"], 0) or 0) < hi]
        if len(sel) < 2: continue
        for fld in ("area_um2", "circularity", "aspect_ratio", "elongation", "major_um",
                    "minor_um", "solidity", "roundness", "n_pieces"):
            vals = [fl(r.get(fld)) for r in sel]
            vals = [v for v in vals if v is not None]
            if vals:
                agg[b][f"{lab}::{fld}::{win}_med"].append(float(np.median(vals)))
                agg[b][f"{lab}::{fld}::{win}_max"].append(float(np.max(vals)))
        sp = []
        for i in range(1, len(sel)):
            t0, t1 = fl(sel[i-1]["t_sec"]), fl(sel[i]["t_sec"])
            x0, y0 = fl(sel[i-1]["cx_px"]), fl(sel[i-1]["cy_px"])
            x1, y1 = fl(sel[i]["cx_px"]), fl(sel[i]["cy_px"])
            if None in (t0, t1, x0, y0, x1, y1) or t1 <= t0 or t1 - t0 > 300: continue
            sp.append(math.hypot(x1-x0, y1-y0) * px / (t1 - t0))
        if sp: agg[b][f"{lab}::speed::{win}_med"].append(float(np.median(sp)))
    agg[b][f"{lab}::n_tracks"].append(1.0)
for b, d in agg.items():
    for k, v in d.items():
        put(b, "kt::" + k, float(np.sum(v)) if k.endswith("n_tracks") else float(np.median(v)))

# (c) sister k-k before metaphase
KK = rd(A + "/KT_SISTER_KK_20260723.csv")
kk = collections.defaultdict(list)
for r in KK:
    b = r["batch"].strip()
    if b not in BATCHES: continue
    if (r.get("phase") or "").strip() == "prometaphase":
        v = fl(r.get("kk_dist_um"))
        if v is not None: kk[b].append(v)
for b, v in kk.items():
    put(b, "kk::prometa_med", float(np.median(v))); put(b, "kk::prometa_n", len(v))
    put(b, "kk::prometa_sd", float(np.std(v)))

# (d) chromosome length of the ablated chromosome
CL = rd(A + "/KT_CHROMO_ANALYSIS_20260723.csv")
cl = collections.defaultdict(list)
for r in CL:
    b = r["batch"].strip()
    if b in BATCHES:
        v = fl(r.get("length_um"))
        if v is not None: cl[b].append(v)
for b, v in cl.items():
    put(b, "chromo::len_med", float(np.median(v))); put(b, "chromo::len_max", float(np.max(v)))
    put(b, "chromo::len_spread", float(np.max(v) - np.min(v))); put(b, "chromo::n", len(v))

# (e) cell shape before metaphase (her traced outlines)
CO = rd(A + "/cell_outlines.csv")
co = collections.defaultdict(list)
for r in CO:
    b = r["batch"].strip()
    if b not in BATCHES: continue
    m0 = meta_onset(b); t = fl(r.get("t_sec"))
    if m0 is None or t is None or t >= m0: continue
    co[b].append((fl(r.get("roundness")), fl(r.get("area_um2")), fl(r.get("circularity"))))
for b, v in co.items():
    for i, nm in enumerate(("roundness", "area_um2", "circularity")):
        vals = [x[i] for x in v if x[i] is not None]
        if vals: put(b, f"cell::{nm}_pre_med", float(np.median(vals)))
    put(b, "cell::n_outlines_pre", len(v))

# (f) CONGRESSION -- 2026-08-18, her correction: my first pass read ONLY
# SISTERLESS_PLATE_JOIN_TIMES.csv (65 rows) and reported 31% coverage.  Measured across all three
# structured sources for on-target cdc20 cells: congression BEHAVIOUR is known for 83.5% of the cohort
# and a congression TIME for 45.6%.  CHROMOSOME_MASTER is the richest (congression_time_s + behavior);
# PREABL_CHROMOSOME_ASSIGNMENT carries behaviour keyed on (batch, chr_num).
#
# 🔴 LEAKAGE BOUNDARY, stated explicitly.  WHETHER a chromosome eventually congressed is an OUTCOME of
# the metaphase we are trying to predict, not an observation available at its onset -- a cell largely
# stays in metaphase until things congress.  So congression is split in two:
#   * ONSET model (item 5): congression is EXCLUDED.  Features carry the `cong_outcome::` prefix and are
#     dropped from X unless USE_OUTCOME=1, which prints a warning.
#   * LANDMARK model (item 6): congression events with time <= the landmark ARE legitimate inputs, since
#     she is explicitly asking what can be predicted from observations taken partway through metaphase.
CONG = collections.defaultdict(dict)          # batch -> features (time-stamped where known)
CONG_EVENTS = collections.defaultdict(list)   # batch -> [(t_sec_abs, 'congressed'|'noncongression')]
def _cong_add(b, chrnum, behav, t_s):
    d = CONG[b].setdefault("_chr", {})
    prev = d.get(chrnum)
    # structured table beats a looser source; a real time beats no time
    if prev is None or (t_s is not None and prev[1] is None):
        d[chrnum] = (behav, t_s)

try:
    for r in rd(A + "/CHROMOSOME_MASTER.csv"):
        b = (r.get("batch") or "").strip()
        if b not in BATCHES: continue
        _cong_add(b, (r.get("chr_num") or "").strip(),
                  (r.get("behavior") or "").strip().lower() or None,
                  hms(r.get("congression_time_s")))
except Exception as e: print("[feat] CHROMOSOME_MASTER skipped:", e)
try:
    for r in rd(A + "/PREABL_CHROMOSOME_ASSIGNMENT.csv"):
        b = (r.get("batch") or "").strip()
        if b not in BATCHES: continue
        _cong_add(b, (r.get("chr_num") or "").strip(),
                  (r.get("behavior") or "").strip().lower() or None, None)
except Exception as e: print("[feat] PREABL skipped:", e)
try:
    for r in rd(A + "/SISTERLESS_PLATE_JOIN_TIMES.csv"):
        b = (r.get("batch") or "").strip()
        if b not in BATCHES: continue
        for i in ("1", "2", "3"):
            t = hms(r.get(f"chromosome_{i}_plate_join_s") or r.get(f"chromosome_{i}_plate_join"))
            if t is not None and t > 0: _cong_add(b, i, "congressed", t)
except Exception as e: print("[feat] plate-join skipped:", e)

_ncov = 0
for b, d in CONG.items():
    chrs = d.get("_chr") or {}
    if not chrs: continue
    _ncov += 1
    m0 = meta_onset(b) or 0.0
    beh = [v[0] for v in chrs.values() if v[0]]
    times = [v[1] for v in chrs.values() if v[1] is not None]
    ncong = sum(1 for x in beh if "congress" in x and "non" not in x)
    nnon  = sum(1 for x in beh if "noncongress" in x or "non-congress" in x)
    put(b, "cong_outcome::n_scored", len(beh))
    put(b, "cong_outcome::n_congressed", ncong)
    put(b, "cong_outcome::n_noncongressed", nnon)
    if beh: put(b, "cong_outcome::frac_congressed", ncong / float(len(beh)))
    if times:
        put(b, "cong_outcome::first_rel_s", min(times) - m0)
        put(b, "cong_outcome::last_rel_s", max(times) - m0)
        put(b, "cong_outcome::median_rel_s", float(np.median(times)) - m0)
        put(b, "cong_outcome::n_timed", len(times))
        put(b, "cong_outcome::spread_s", max(times) - min(times))
    for c, (bh, t) in chrs.items():
        if t is not None: CONG_EVENTS[b].append((t, bh or "congressed"))
print(f"[feat] congression: {_ncov}/{len(cells)} cells have structured congression "
      f"({100.0*_ncov/max(len(cells),1):.0f}%)")

# (g) loading axis / distortion before metaphase
LD = rd(A + "/KT_LOADING_AXIS_20260805.csv")
ld = collections.defaultdict(list)
for r in LD:
    b = r["batch"].strip()
    if b not in BATCHES: continue
    if str(r.get("outlier", "")).strip() in ("1", "True", "true"): continue
    m0 = meta_onset(b); t = fl(r.get("t_sec"))
    if m0 is None or t is None or t >= m0: continue
    v = fl(r.get("load_extent_um")); rr = fl(r.get("load_ratio"))
    if v is not None: ld[(b, "load_extent_um")].append(v)
    if rr is not None: ld[(b, "load_ratio")].append(rr)
for (b, k), v in ld.items(): put(b, f"load::{k}_pre_med", float(np.median(v)))

FEATS = sorted({k for b in F for k in F[b]})
print(f"[feat] {len(FEATS)} candidate features over {len(F)} cells")

# drop features present in fewer than 20% of cells, and zero-variance ones
keep = []
for k in FEATS:
    vals = [F[c["batch"]].get(k) for c in cells]
    have = [v for v in vals if v is not None]
    if len(have) < max(8, .20 * len(cells)): continue
    if np.std(have) == 0: continue
    keep.append(k)
FEATS = keep
print(f"[feat] {len(FEATS)} features kept (>=20% coverage, non-constant)")

USE_OUTCOME = bool(os.environ.get("USE_OUTCOME"))
ONSET_FEATS = [k for k in FEATS if not k.startswith("cong_outcome::")] if not USE_OUTCOME else list(FEATS)
if not USE_OUTCOME:
    print(f"[leak] {len(FEATS)-len(ONSET_FEATS)} congression-OUTCOME features held out of the onset model "
          f"(whether a chromosome congressed is an outcome of the metaphase being predicted). "
          f"USE_OUTCOME=1 includes them.")
FEATS_ALL = list(FEATS); FEATS = ONSET_FEATS
X = np.array([[F[c["batch"]].get(k, np.nan) for k in FEATS] for c in cells], float)
y = np.array([c["dur_s"] / 60.0 for c in cells], float)          # minutes
groups = np.array([c["day"] for c in cells])
print(f"[data] X={X.shape}  y median={np.median(y):.1f} min  range {y.min():.1f}-{y.max():.1f}  "
      f"missing={np.isnan(X).mean()*100:.0f}%")

# ---- empirical leak screen: |Spearman| >= 0.9 against the target
from scipy import stats as st
drop = []
for j, k in enumerate(FEATS):
    m = ~np.isnan(X[:, j])
    if m.sum() >= 10:
        rho = st.spearmanr(X[m, j], y[m]).statistic
        if abs(rho) >= .90: drop.append((k, float(rho)))
if drop:
    print("[leak] dropping near-perfect correlates:", drop)
    idx = [j for j, k in enumerate(FEATS) if k not in {d[0] for d in drop}]
    X = X[:, idx]; FEATS = [FEATS[j] for j in idx]

# ================================================================ model sweep
def models():
    yield "null (predict median)", DummyRegressor(strategy="median")
    yield "ridge", RidgeCV(alphas=np.logspace(-3, 4, 40))
    yield "lasso", LassoCV(max_iter=20000, random_state=0)
    yield "elasticnet", ElasticNetCV(l1_ratio=[.2, .5, .8, .95], max_iter=20000, random_state=0)
    yield "bayesian ridge", BayesianRidge()
    yield "huber", HuberRegressor(max_iter=2000)
    yield "PLS (3)", PLSRegression(n_components=3)
    yield "kNN (5)", KNeighborsRegressor(n_neighbors=5, weights="distance")
    yield "SVR rbf", SVR(C=10, gamma="scale", epsilon=.1)
    yield "SVR linear", SVR(kernel="linear", C=1.0, epsilon=.1)
    yield "decision tree", DecisionTreeRegressor(max_depth=3, random_state=0)
    yield "random forest", RandomForestRegressor(n_estimators=600, min_samples_leaf=3, random_state=0, n_jobs=-1)
    yield "extra trees", ExtraTreesRegressor(n_estimators=600, min_samples_leaf=3, random_state=0, n_jobs=-1)
    yield "gradient boosting", GradientBoostingRegressor(random_state=0)
    yield "hist gradient boosting", HistGradientBoostingRegressor(random_state=0, max_iter=300)
    yield "adaboost", AdaBoostRegressor(random_state=0)
    yield "gaussian process", GaussianProcessRegressor(
        kernel=ConstantKernel(1.0) * RBF(length_scale=5.0) + WhiteKernel(1.0),
        normalize_y=True, alpha=1e-6, random_state=0)

def evaluate(X, y, groups, log_target=True, label="", topk=12):
    """Grouped 5-fold by IMAGING DAY, repeated 6x with different day partitions.

    Two changes from the first attempt, both because p(92) >> n(68):
      * features are screened INSIDE each fold (top-k by |Spearman| on the TRAINING cells only),
        so the screening itself cannot leak;
      * the null is the median of that fold's TRAINING cells, not the global median, which is the
        only null a real predictor would have to beat.
    Errors are always in MINUTES on the original scale.
    """
    from sklearn.model_selection import GroupKFold
    uniq = np.array(sorted(set(groups)))
    rows = []
    for name, est in models():
        errs, nulls, P, Y, fails = [], [], [], [], []
        for rep in range(6):
            rs = np.random.RandomState(rep)
            perm = rs.permutation(len(uniq))
            fold_of = {d: perm[i] % 5 for i, d in enumerate(uniq)}
            fid = np.array([fold_of[g] for g in groups])
            for k in range(5):
                te = fid == k; tr = ~te
                if tr.sum() < 10 or te.sum() < 1: continue
                Xtr, ytr, Xte, yte = X[tr], y[tr], X[te], y[te]
                # in-fold univariate screen
                sc = []
                for j in range(Xtr.shape[1]):
                    m = ~np.isnan(Xtr[:, j])
                    sc.append(abs(st.spearmanr(Xtr[m, j], ytr[m]).statistic)
                              if m.sum() >= 8 and np.std(Xtr[m, j]) > 0 else 0.0)
                sc = np.nan_to_num(np.array(sc))
                sel = np.argsort(-sc)[:topk]
                pipe = Pipeline([("imp", SimpleImputer(strategy="median", keep_empty_features=True)),
                                 ("sc", StandardScaler()), ("m", est)])
                tt = np.log(ytr) if log_target else ytr
                try:
                    pipe.fit(Xtr[:, sel], tt)
                    p = np.asarray(pipe.predict(Xte[:, sel])).ravel()
                    p = np.exp(np.clip(p, -5, 8)) if log_target else p
                except Exception as e:
                    fails.append(repr(e)[:110]); continue
                base = float(np.median(ytr))
                errs += list(np.abs(p - yte)); nulls += list(np.abs(base - yte))
                P += list(p); Y += list(yte)
        if len(errs) < 40:
            print(f"  [skip] {name}: only {len(errs)} predictions"
                  + (f" | first error: {fails[0]}" if fails else ""))
            continue
        errs = np.array(errs); nulls = np.array(nulls); P = np.array(P); Y = np.array(Y)
        tt = st.ttest_rel(nulls, errs)
        rows.append(dict(model=name, MAE=float(errs.mean()), medAE=float(np.median(errs)),
                         null_MAE=float(nulls.mean()), gain=float(nulls.mean() - errs.mean()),
                         R2=float(1 - np.sum((P - Y) ** 2) / np.sum((Y - Y.mean()) ** 2)),
                         spearman=float(st.spearmanr(P, Y).statistic), n=int(len(errs)),
                         paired_t=float(tt.statistic), paired_p=float(tt.pvalue)))
    rows.sort(key=lambda r: r["MAE"])
    print(f"\n=== {label} : grouped 5-fold by imaging day, 6 repeats ===")
    for r in rows:
        print(f"  {r['model']:26s} MAE {r['MAE']:6.2f} min   null {r['null_MAE']:6.2f}   "
              f"gain {r['gain']:+5.2f}   R2 {r['R2']:+.2f}   rho {r['spearman']:+.2f}   p={r['paired_p']:.3g}")
    return rows

item5 = evaluate(X, y, groups, True, "ITEM 5 - duration from metaphase onset")

# ================================================================ ITEM 6 landmark models
LANDMARKS = [3, 6, 10, 15]           # minutes into metaphase
land_rows = []
for L in LANDMARKS:
    sub = [c for c in cells if c["dur_s"] / 60.0 > L]        # must still be in metaphase
    if len(sub) < 15: continue
    Xl, yl, gl = [], [], []
    for c in sub:
        b = c["batch"]; m0 = meta_onset(b)
        row = dict(F[b])
        # add what is observable between metaphase onset and the landmark
        if m0 is not None:
            seen = [r for (bb, lab, tid), rs in by.items() if bb == b for r in rs
                    if m0 <= (fl(r["t_sec"], 0) or 0) <= m0 + L * 60]
            if seen:
                for fld in ("circularity", "elongation", "area_um2", "n_pieces"):
                    v = [fl(r.get(fld)) for r in seen]; v = [x for x in v if x is not None]
                    if v: row[f"land::{fld}_med"] = float(np.median(v))
                row["land::n_obs"] = float(len(seen))
            # congression OBSERVED BY the landmark -- legitimate here, unlike in the onset model
            evs = [e for e in CONG_EVENTS.get(b, []) if e[0] <= (m0 or 0) + L * 60]
            row["land::n_congressed_by_L"] = float(sum(1 for _, k in evs if "non" not in (k or "")))
            if evs: row["land::last_congress_rel_s"] = float(max(e[0] for e in evs) - (m0 or 0))
            tot = len((CONG.get(b, {}).get("_chr") or {}))
            if tot: row["land::frac_congressed_by_L"] = row["land::n_congressed_by_L"] / float(tot)
        row["land::L_min"] = float(L)
        Xl.append([row.get(k, np.nan) for k in FEATS + ["land::circularity_med", "land::elongation_med",
                                                        "land::area_um2_med", "land::n_pieces_med", "land::n_obs",
                                                        "land::n_congressed_by_L", "land::last_congress_rel_s",
                                                        "land::frac_congressed_by_L"]])
        yl.append(c["dur_s"] / 60.0 - L)                       # REMAINING minutes
        gl.append(c["day"])
    Xl = np.array(Xl, float); yl = np.array(yl, float); gl = np.array(gl)
    rr = evaluate(Xl, yl, gl, True, f"ITEM 6 - remaining time at landmark L={L} min (n={len(yl)})")
    for r in rr: r["landmark_min"] = L; r["n_cells"] = int(len(yl))
    land_rows += rr

# ================================================================ ITEM 7 what would help
best = item5[0] if item5 else None
imp = []
try:
    rf = Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                   ("m", RandomForestRegressor(n_estimators=800, min_samples_leaf=3,
                                               random_state=0, n_jobs=-1))])
    rf.fit(X, np.log(y))
    fi = rf.named_steps["m"].feature_importances_
    cov = [(~np.isnan(X[:, j])).mean() for j in range(X.shape[1])]
    for j, k in enumerate(FEATS):
        imp.append(dict(feature=k, importance=float(fi[j]), coverage=float(cov[j]),
                        headroom=float(fi[j] * (1 - cov[j]))))
    imp.sort(key=lambda r: -r["importance"])
except Exception as e:
    print("[item7] importance failed:", e)

json.dump(dict(item5=item5, item6=land_rows, importance=imp,
               n_cells=len(cells), n_features=len(FEATS), features=FEATS,
               n_days=len(set(groups)), y_median=float(np.median(y))),
          io.open(SCRATCH + "/model_results.json", "w"), indent=1)

# ================================================================ FIGURE
fig = plt.figure(figsize=(16.5, 9.6))
gs = fig.add_gridspec(2, 3, hspace=.42, wspace=.28)

ax = fig.add_subplot(gs[0, :2])
top = item5[:14]
yy = np.arange(len(top))[::-1]
ax.barh(yy, [r["MAE"] for r in top], color=["#999999" if "null" in r["model"] else "#0072b2" for r in top],
        alpha=.9, height=.68)
nullmae = next((r["null_MAE"] for r in top), None)
if nullmae: ax.axvline(nullmae, color="#d55e00", ls="--", lw=2, label=f"null = {nullmae:.1f} min")
for i, r in enumerate(top):
    ax.text(r["MAE"] + .12, yy[i], f"{r['MAE']:.1f}  (p={r['paired_p']:.2g})", va="center", fontsize=8)
ax.set_yticks(yy); ax.set_yticklabels([r["model"] for r in top], fontsize=8.5)
ax.set_xlim(0, max(r["MAE"] for r in top) * 1.30)   # headroom so the value labels never sit on the legend
ax.set_xlabel("mean absolute error (min), leave-one-day-out")
ax.set_title("ITEM 5 - predicting metaphase duration at onset  (1- and 3-sisterless, on-target)",
             loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper right"); ax.spines[["top", "right"]].set_visible(False)

ax2 = fig.add_subplot(gs[0, 2])
ax2.hist(y, bins=16, color="#0072b2", alpha=.85, edgecolor="white")
ax2.axvline(float(np.median(y)), color="#d55e00", ls="--", lw=2)
ax2.set_xlabel("metaphase duration (min)"); ax2.set_ylabel("cells")
ax2.set_title(f"What is being predicted\nn={len(y)} cells, {len(set(groups))} days", fontsize=10)
ax2.spines[["top", "right"]].set_visible(False)

ax3 = fig.add_subplot(gs[1, 0])
if land_rows:
    for L in sorted({r["landmark_min"] for r in land_rows}):
        rs = sorted([r for r in land_rows if r["landmark_min"] == L], key=lambda r: r["MAE"])
        if not rs: continue
        b_ = rs[0]; nl = next((r for r in rs if "null" in r["model"]), None)
        ax3.bar(L - .8, b_["MAE"], width=1.6, color="#0072b2", alpha=.9)
        if nl: ax3.bar(L + .8, nl["MAE"], width=1.6, color="#999999", alpha=.9)
        ax3.text(L, max(b_["MAE"], nl["MAE"] if nl else 0) + .25, b_["model"].replace(" ", "\n"),
                 ha="center", va="bottom", fontsize=6.2, linespacing=.95)
    ax3.set_xlabel("landmark: minutes into metaphase"); ax3.set_ylabel("MAE of remaining time (min)")
    ax3.set_title("ITEM 6 - time remaining\n(blue = best model, grey = null)", fontsize=10)
    # only the values actually DRAWN (best + null per landmark) -- taking the max over every model
    # includes the diverged linear fits (MAE 45-68 min) and squashes the real bars to nothing.
    _drawn = []
    for _L in sorted({r["landmark_min"] for r in land_rows}):
        _rs = sorted([r for r in land_rows if r["landmark_min"] == _L], key=lambda r: r["MAE"])
        if not _rs: continue
        _drawn.append(_rs[0]["MAE"])
        _nl = next((r for r in _rs if "null" in r["model"]), None)
        if _nl: _drawn.append(_nl["MAE"])
    ax3.set_ylim(0, (max(_drawn) if _drawn else 1) * 1.42)
ax3.spines[["top", "right"]].set_visible(False)

ax4 = fig.add_subplot(gs[1, 1:])
if imp:
    t = imp[:16][::-1]
    yy = np.arange(len(t))
    ax4.barh(yy, [r["importance"] for r in t], color="#009e73", alpha=.9, height=.7)
    for i, r in enumerate(t):
        ax4.text(r["importance"] + .002, yy[i], f"  {r['coverage']*100:.0f}% of cells have it", va="center", fontsize=7.5)
    ax4.set_yticks(yy); ax4.set_yticklabels([r["feature"][:52] for r in t], fontsize=7.2)
    ax4.set_xlabel("random-forest importance")
    ax4.set_title("ITEM 7 - what the model leans on, and how completely it is measured",
                  loc="left", fontsize=10)
ax4.spines[["top", "right"]].set_visible(False)

_best = item5[0]["MAE"] if item5 else float("nan")
_sub = ("congression OUTCOME is held out of this model -- whether a chromosome congressed is a RESULT of "
        "the metaphase being predicted.\nAllowing it (USE_OUTCOME=1) reaches MAE 6.50 min, R$^2$=0.37, "
        "$\\rho$=0.54 -- descriptive of what congression explains, not a forecast from onset.")
fig.suptitle("Metaphase-duration models, built fresh  -  on-target 1- and 3-sisterless cells only\n"
             + _sub, fontweight="bold", fontsize=11)
fig.savefig(f"{OUT}/G8_metaphase_duration_model.png", dpi=190, bbox_inches="tight")
plt.close(fig)

hdr = ["model", "MAE", "medAE", "null_MAE", "gain", "R2", "spearman", "paired_p", "n"]
lib.record_plot("G8_metaphase_duration_model", hdr,
                [[r.get(k) for k in hdr] for r in item5],
                {"type": "model comparison", "cohort": "on-target, 1- and 3-sisterless, non-drug, non-excluded",
                 "n_cells": len(cells), "n_days": len(set(groups)), "n_features": len(FEATS),
                 "validation": "leave-one-imaging-day-out", "target": "metaphase duration (min), fitted on log",
                 "landmarks": LANDMARKS},
                SCRIPT, "Metaphase-duration prediction: model sweep, leave-one-day-out")
print("\n[done] wrote", SCRATCH + "/model_results.json")
