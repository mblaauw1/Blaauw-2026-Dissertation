"""custom_model_structured_20260722.py — model the warehouse WITH its structure, not as a flat bag.

WHY THIS EXISTS (user, 2026-07-22)
  "some measurements are tied to each other because they are measured over time or over space or in
   comparison to something else ... the extra dimensions could help. or some measurements might present one
   way for single sisterless kinetochore batches, and then in 2 or 3 sisterless the same measurement presents
   another way or have a different number of placements in a frame or over an amount of time"
  "because the model built with just length is not good at predicting things, it makes me think that perhaps
   other measurements aren't being treated with the dimensionality and complexity that they could be"

  She is right, and the previous run (custom_model_heldout / custom_model_full_features) got both wrong:

  PROBLEM 1 — THE FEATURES ARE NOT INDEPENDENT.
    `_scratch/batch_features.json` looks like 3794 features but is really 432 BASE MEASUREMENTS each
    expanded into 7-14 summary statistics. Within one block, mean/med/min/max are near-collinear. Flat
    top-K selection therefore spends its whole budget on redundant siblings of a few blocks, and the
    genuinely EXTRA dimensions — the trajectory shape (slope_per_progress, meta_half_delta, volatility)
    and the timing (progress_at_max, t_at_max) — are outvoted by 4 copies of "the average".
    That is a mechanism by which a 3794-feature model loses to one feature.
    FIX: select at BLOCK level, then keep at most ONE representative per STAT FAMILY within the block, so a
    block contributes location AND trend AND timing AND phase-resolved information — its real dimensionality
    — instead of four restatements of its mean. Then prune |r|>0.95 survivors.

  PROBLEM 2 — A MEASUREMENT DOES NOT MEAN THE SAME THING IN EVERY SISTERLESS GROUP.
    Her own established result: chromosome length predicts staying polar in 2/3-sisterless (p=0.019) but NOT
    in 1-sisterless (p=0.79) — length matters only under competition. A pooled coefficient averages a real
    group-specific effect toward zero.
    Also MECHANICAL: the `|n` statistic is the number of recorded rows for that batch, so it partly encodes
    how many sisterless kinetochores there are and how many placements were made per frame / over time.
    Comparing raw `n` across groups compares annotation effort, not biology.
    FIX: (a) emit exposure-normalised companions (`n_per_sis`, and rate = n / t_span) alongside raw n;
         (b) evaluate FOUR model modes — pooled / +group indicator / group x feature interactions /
             separate per-group models — so a group-specific effect is visible instead of averaged away;
         (c) report held-out score PER GROUP, and report each block's univariate direction per group so a
             SIGN FLIP between 1-sis and 2/3-sis is surfaced rather than hidden.

PROTOCOL (unchanged from her spec — this is the honest part)
  30% held out from EACH sisterless group separately, split BY CELL (never splitting a cell), N repeats,
  scored against length-only / sum_len-only / predict-mean / shuffled-label controls.
  *** ALL FEATURE SELECTION HAPPENS INSIDE THE TRAINING FOLD. *** Selecting on the full set would leak and,
  with 432 blocks and ~77 cells, would produce a confident-looking fit that means nothing. The shuffled-label
  control is the instrument that catches that; if it rises above ~0.5 AUC / ~0 R2, the run is invalid.

  Event times (metaphase/anaphase) are NEVER features — the LEAK regex strips them. They are used only to
  rescale other measurements' time axes (that happened upstream in custom_model_full_features).
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os, re, json, warnings
import numpy as np
from collections import defaultdict
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score, mean_absolute_error, roc_auc_score
import lib

warnings.filterwarnings("ignore")
FEATJSON = "/Volumes/4 MB/_scratch/batch_features.json"
OUTDIR = "/Volumes/4 MB/_scratch"
N_REPEATS = int(os.environ.get("N_REPEATS", "200"))
TEST_FRAC = 0.30
TOP_BLOCKS = int(os.environ.get("TOP_BLOCKS", "20"))   # blocks kept per fold (selected on TRAIN only)
MIN_PRESENT = 40                                        # a feature must exist in >= this many batches

# Anything derived from the metaphase/anaphase clock trivially predicts metaphase duration.
LEAK = re.compile(r"metaphase|meta.?dur|meta.?start|duration|anaphase|\bana\b|ana_|_ana|mitotic|cytokin|"
                  r"neb.?to.?meta|abl.?to.?meta|meta.?min|dur_min", re.I)

# ---------------------------------------------------------------- OUTCOME LEAKAGE (found 2026-07-22)
# The FIRST smoke run of this script scored AUC 0.871 / R2 0.782 and the most-selected features gave it away:
#   G4_exhaustion_violin:minutes           = metaphase duration in minutes         -> IS the regression target
#   G3_congression_fraction:fraction       = fraction of chromosomes reaching plate -> IS the classification target
#   G3_lagging_vs_congression_balance:frac_congressed                               -> IS the target again
#   G4_congression_score_ranked:mean_score = a congression outcome score            -> outcome, not initial condition
# The name-based LEAK regex above missed all of them ("minutes", "fraction", "score" are innocuous words).
# A recorded plot CSV is keyed by batch but says nothing about whether its columns are PREDICTORS or RESULTS,
# so leakage has to be excluded by NAME here and re-checked empirically (see leak_audit()).
# RULE: a feature is admissible only if it is knowable WITHOUT knowing how the cell turned out.
OUTCOME = re.compile(
    r"congress|reach|frac_|fraction|\bscore\b|_score|exhaust|behaviou?r|outcome|"
    r"\bpolar\b|lagging|noncong|at_plate|plate_join|rejoin|minutes|\bmins?\b|elapsed|"
    r"time_to|to_ana|to_meta|survival|censored", re.I)

# For a series sampled at a fixed interval, the NUMBER of timepoints and the SPAN of the time axis are the
# movie's duration — which for these movies runs metaphase -> anaphase. So `n`, `t_span`, `t_at_max` and the
# n_per_sis companion are duration in disguise and MUST NOT be offered to the duration regression.
DURATION_PROXY_STATS = {"n", "n_per_sis", "t_span", "t_at_max"}
# Columns that are literally a clock/index rather than a measurement. `x` and `y` are raw plot-axis values —
# in the *_scaled01 figures `x` IS the normalised time axis, so its sd/max/range are the movie's length.
CLOCK_COL = re.compile(r"(^|:)(t_sec|time|frame_idx|frame|timepoint|t|x|y)$", re.I)


def bad_sources():
    """SOURCE-LEVEL admissibility, decided from PLOT_SETTINGS.json — the structural fix.

    The warehouse is harvested from RECORDED FIGURE CSVs. A figure's plotted quantity is very often the very
    thing we are trying to predict (a metaphase-duration violin, a congression-fraction scatter), so its CSV
    columns are the target wearing a different column name. Filtering by column name keeps missing these
    (`minutes`, `fraction`, `zoom_outlier_removed` all slipped through).

    PLOT_SETTINGS.json records each figure's `caption` and `settings.metric`. Judging admissibility from
    WHAT THE FIGURE IS ABOUT is reliable where column names are not.

    Deliberately matched on caption + metric ONLY — never on `settings.x` or `settings.clip`, because almost
    every time-series figure legitimately says "from ablation" / "clip: anaphase onset" while plotting a
    perfectly good predictor (cell area, roundness). Matching those would throw the real features away."""
    try:
        ps = json.load(open("/Volumes/4 MB/ablation_plots/PLOT_SETTINGS.json"))
    except Exception:
        return set()
    bad = set()
    for name, v in ps.items():
        s = v.get("settings") or {}
        text = " ".join(str(t) for t in (v.get("caption", ""), s.get("metric", ""), s.get("type", "")))
        if LEAK.search(text) or OUTCOME.search(text):
            bad.add(name)
    return bad, set(ps)


BAD_SOURCES, VETTED_SOURCES = bad_sources()

# ---------------------------------------------------------------- BLOCK VETTING TABLE
# `ablation_plots/MODEL_FEATURE_VETTING_20260722.csv` records a per-BLOCK decision (predictor / outcome /
# acquisition / clock / raw_pixel / unknown) with the grounds for each, produced by inspecting every source
# CSV's sibling columns and value distribution. It supersedes the source-level PLOT_SETTINGS heuristic:
# 49 blocks that were excluded only because their figure had no PLOT_SETTINGS entry are legitimate
# measurements, and several that the heuristic ADMITTED are not — notably `master:*_ids`, comma-separated
# ID lists whose numeric value encodes annotation order. The model was selecting
# `master:preabl_chromosome_ids` in 195 of 200 folds on that artefact.
# The `admit` column is authoritative and hand-editable: her decision overrides the classifier.
VETTING_CSV = "/Volumes/4 MB/ablation_plots/MODEL_FEATURE_VETTING_20260722.csv"


def admitted_blocks():
    ok, seen = set(), 0
    try:
        with open(VETTING_CSV, encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                seen += 1
                if (r.get("admit") or "").strip().lower() == "yes":
                    ok.add((r.get("block") or "").strip())
    except FileNotFoundError:
        return None
    print(f"vetting table: {len(ok)} of {seen} blocks admitted")
    return ok


ADMITTED = admitted_blocks()
# FAIL CLOSED. `G1_violin2_no_dc_offtarget_journal_zoom` was selected in 19 of 25 folds not because it passed
# the caption filter but because it has NO PLOT_SETTINGS entry to filter on — it is a metaphase-duration
# violin, i.e. the target. A source we cannot vet is a source we cannot admit; guessing what an unrecorded
# figure plots is exactly the class of inference that got four figures retired.
# `master:` features are vetted by name instead (BAD_MASTER + LEAK + OUTCOME) since they have no figure.
# Master columns that are movie length in disguise — ALL frame counts, not just "Total Frames".
BAD_MASTER = re.compile(r"frames?\b|frame\s*count|movie\s*len|crop\s*start", re.I)

# ---------------------------------------------------------------- STAT FAMILIES
# The whole point of PROBLEM 1: these are the genuinely different KINDS of information a single measured
# quantity carries. One representative from each is allowed per block; siblings inside a family are
# redundant restatements and compete only with each other.
FAMILY = {
    "location":   ["med", "mean", "max", "min"],
    "dispersion": ["sd", "range", "volatility"],
    "trend":      ["slope_per_progress", "slope", "meta_half_delta", "delta", "foldchange", "early", "late"],
    "timing":     ["progress_at_max", "t_at_max", "t_span"],
    "phase":      ["meta2_mean", "meta1_mean", "premeta_mean", "postana_mean"],
    "exposure":   ["n_per_sis", "n_rate", "n"],
}
STAT2FAM = {s: f for f, ss in FAMILY.items() for s in ss}


def split_feat(f):
    """'G4_frap:intensity|slope' -> ('G4_frap:intensity', 'slope')"""
    return tuple(f.rsplit("|", 1)) if "|" in f else (f, "_bare")


# ---------------------------------------------------------------- LOAD
master, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in master}
def gv(b, c): return (mr.get(b, {}).get(c, "") or "").strip()


# ---------------------------------------------------------------- COHORT GATE (user, 2026-07-22)
# "when you determine the total batches that you're going to use (before separating out 30% for testing),
#  this should not include batches where the cell has not gone into anaphase, or batches where there have
#  been two kinetochore ablations on one chromosome ... don't assume from a batch name ... if the batch is
#  not included in what's plotted for G1_violin2_mitotic_duration, don't use it (and also limit ... by
#  on-target samples only)."
#
# So membership is TAKEN from that figure's recorded data rather than re-derived here: the violin already
# encodes both exclusions (no-anaphase cells and double-kinetochore-on-one-chromosome cells), and
# re-implementing them from the master or — worse — from batch names would be a second, divergent
# definition. The gate is applied to the FULL cell set BEFORE any train/test split, so the held-out 30%
# is drawn from the same population as the training rows.
VIOLIN_CSV = "/Volumes/4 MB/ablation_plots/data/G1_violin2_mitotic_duration.csv"
ON_TARGET_COHORTS = {"1-Sister", "2-Sister", "3-Sister"}


def cohort_gate():
    """batches plotted in G1_violin2_mitotic_duration under an ON-TARGET cohort."""
    keep, seen = set(), set()
    with open(VIOLIN_CSV, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            b = (r.get("batch") or "").strip()
            c = (r.get("cohort") or "").strip()
            if not b:
                continue
            seen.add(b)
            if c in ON_TARGET_COHORTS:
                keep.add(b)
    if not keep:
        raise SystemExit(f"cohort gate empty — check {VIOLIN_CSV}")
    print(f"cohort gate: {len(seen)} batches in G1_violin2_mitotic_duration, "
          f"{len(keep)} of them on-target ({'/'.join(sorted(ON_TARGET_COHORTS))})")
    return keep


COHORT = cohort_gate()


def in_cohort(b):
    return b in COHORT


def lagging_flag(b):
    """1 / 0 / nan from the master's recorded `Lagging Chromosomes` column.

    User 2026-07-22: "it's more just taking into account that there are lagging chromosomes — they really
    don't differ in position too much relative to where the former metaphase plate was." So lagging enters
    the model as PRESENCE, not geometry. That is also the only defensible option: lagging chromosomes are
    marked AFTER anaphase onset, when the plate no longer exists (163 of the 235 post-anaphase kinetochore
    marks are lagging), so a plate-relative coordinate cannot be computed for them at all.

    Taken from the master column, not from the manual marks: `Lagging Chromosomes` is recorded for 79 of the
    82 on-target cohort batches (43 Yes / 36 No), whereas manual `lagging` kinetochore marks exist in only
    10. Using the marks would silently score 'not marked' as 'no lagging'.

    CAVEAT, stated because it changes how the number should be read: lagging is OBSERVED AT ANAPHASE, so it
    is not knowable at ablation time. It is therefore not an initial condition, and for the metaphase-duration
    regression it is contemporaneous with the end of the target interval rather than upstream of it. The
    model is reported BOTH WITH AND WITHOUT it so the contribution is visible rather than baked in."""
    v = gv(b, "Lagging Chromosomes").lower()
    if v.startswith("y"):
        return 1.0
    if v.startswith("n"):
        return 0.0
    return np.nan

chromo = defaultdict(list)
for r in csv.DictReader(open("/Volumes/4 MB/annotations/CHROMOSOME_MASTER.csv")):
    chromo[r["batch"].strip()].append(r)


def nsis(b):
    v = gv(b, "# Sisterless KTs")
    return v if v in ("1", "2", "3") else None


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


def load_features():
    """batch -> {feature: value}, with the leaky features stripped and EXPOSURE-NORMALISED companions added.

    PROBLEM 2(a): `|n` is how many rows that batch contributed — annotation effort and sisterless count,
    not biology. Raw n is kept (it is sometimes legitimately informative) but two normalised companions are
    added so the model can use 'per kinetochore' and 'per unit time' versions instead:
        n_per_sis = n / (# sisterless KTs)          -> removes the group's mechanical row multiplier
        n_rate    = n / t_span                      -> placements per unit time, comparable across cells
    """
    raw = json.load(open(FEATJSON))
    out = {}
    for b, d in raw.items():
        ns = nsis(b)
        keep = {}
        for f, v in d.items():
            blk = split_feat(f)[0]
            src = blk.split(":", 1)[0]
            if LEAK.search(f) or OUTCOME.search(f) or CLOCK_COL.search(blk):
                continue
            if ADMITTED is not None:
                if blk not in ADMITTED:
                    continue        # vetting table is authoritative
            elif src == "master":
                if BAD_MASTER.search(f):
                    continue
            elif src in BAD_SOURCES or src not in VETTED_SOURCES:
                continue   # fail closed: unvetted figure == inadmissible
            try: fv = float(v)
            except (TypeError, ValueError): continue
            if not np.isfinite(fv): continue
            keep[f] = fv
        add = {}
        for f, v in keep.items():
            blk, st = split_feat(f)
            if st != "n":
                continue
            if ns:
                add[f"{blk}|n_per_sis"] = v / float(ns)
            ts = keep.get(f"{blk}|t_span")
            if ts and ts > 0:
                add[f"{blk}|n_rate"] = v / ts
        keep.update(add)
        out[b] = keep
    return out


FEATS_ALL = load_features()


def usable_features(batches, drop_duration_proxies=False):
    """features present (finite) in >= MIN_PRESENT of the modelled batches.

    drop_duration_proxies: set True for the metaphase-duration regression, where `n` / `t_span` /
    `t_at_max` / `n_per_sis` are the number of frames and the length of the time axis — i.e. the target."""
    cnt = defaultdict(int)
    for b in batches:
        for f in FEATS_ALL.get(b, {}):
            cnt[f] += 1
    out = [f for f, n in cnt.items() if n >= MIN_PRESENT]
    if drop_duration_proxies:
        out = [f for f in out if split_feat(f)[1] not in DURATION_PROXY_STATS]
    return sorted(out)


def leak_audit(feats, batches, yby, binary, label):
    """EMPIRICAL TRIPWIRE for leakage the name filters missed.

    Computed on ALL rows deliberately: a feature that is nearly a copy of the target on the full dataset is
    a leak regardless of how the folds are drawn. This is a DIAGNOSTIC — it does not select anything, so it
    cannot leak into the held-out scores. Anything it flags gets read by a human before the result is
    believed. This is exactly what caught G4_exhaustion_violin:minutes."""
    flagged = []
    for f in feats:
        xs = [(FEATS_ALL.get(b, {}).get(f), yby[b]) for b in batches]
        xs = [(x, y) for x, y in xs if x is not None and np.isfinite(x)]
        if len(xs) < 20:
            continue
        a = np.array([x for x, _ in xs], float); c = np.array([y for _, y in xs], float)
        if np.std(a) == 0:
            continue
        if binary:
            if len(set(c.tolist())) < 2: continue
            s = abs(roc_auc_score(c, a) - 0.5) * 2
        else:
            if np.std(c) == 0: continue
            s = abs(float(np.corrcoef(a, c)[0, 1]))
        if s > 0.80:
            flagged.append((f, round(s, 3), len(xs)))
    flagged.sort(key=lambda t: -t[1])
    if flagged:
        print(f"\n   !! LEAK TRIPWIRE ({label}) — {len(flagged)} feature(s) score >0.80 against the target "
              f"on the FULL dataset. Read these before believing anything below:")
        for f, s, n in flagged[:15]:
            print(f"        {s:.3f}  (n={n})  {f}")
    else:
        print(f"\n   leak tripwire ({label}): clean — no feature exceeds 0.80 against the target")
    return flagged


def stratified_cell_split(cells, groups, frac, rng):
    """hold out `frac` of the cells WITHIN EACH sisterless group (her spec)."""
    test = set()
    for g in sorted(set(groups.values())):
        members = [c for c in cells if groups[c] == g]
        rng.shuffle(members)
        k = max(1, int(round(frac * len(members))))
        test.update(members[:k])
    return [c for c in cells if c not in test], [c for c in cells if c in test]


# ---------------------------------------------------------------- IN-FOLD STRUCTURED SELECTION
def _score_col(x, y, binary):
    """univariate strength of one column on the TRAINING rows only."""
    ok = np.isfinite(x)
    if ok.sum() < 12:
        return 0.0
    xv, yv = x[ok], y[ok]
    if np.std(xv) == 0:
        return 0.0
    if binary:
        if len(set(yv.tolist())) < 2:
            return 0.0
        try: return abs(roc_auc_score(yv, xv) - 0.5) * 2
        except Exception: return 0.0
    if np.std(yv) == 0:
        return 0.0
    return abs(float(np.corrcoef(xv, yv)[0, 1]))


def select_structured(Xtr, ytr, feats, binary, top_blocks=TOP_BLOCKS, rmax=0.95):
    """THE CORE OF PROBLEM 1. Runs on TRAINING DATA ONLY.

    1. score every feature univariately on train
    2. a BLOCK's score = its best feature's score  -> rank blocks, keep top_blocks
       (so 'G4_frap:intensity' competes with 'G3_kk:dist' ONCE, not 14 times)
    3. inside each kept block keep the best feature of EACH stat family — location, dispersion, trend,
       timing, phase, exposure. This is what lets a measurement contribute its extra dimensions.
    4. drop any survivor correlating |r|>rmax with an already-kept survivor (collinearity across blocks)
    """
    s = np.array([_score_col(Xtr[:, j], ytr, binary) for j in range(Xtr.shape[1])])
    by_block = defaultdict(list)
    for j, f in enumerate(feats):
        by_block[split_feat(f)[0]].append(j)
    ranked = sorted(by_block, key=lambda b: -max(s[j] for j in by_block[b]))[:top_blocks]

    cand = []
    for blk in ranked:
        best = {}
        for j in by_block[blk]:
            fam = STAT2FAM.get(split_feat(feats[j])[1], "location")
            if fam not in best or s[j] > s[best[fam]]:
                best[fam] = j
        cand.extend(best.values())
    cand.sort(key=lambda j: -s[j])

    kept = []
    for j in cand:
        if s[j] <= 0:
            continue
        xj = Xtr[:, j]
        red = False
        for k in kept:
            ok = np.isfinite(xj) & np.isfinite(Xtr[:, k])
            if ok.sum() < 12:
                continue
            a, b = xj[ok], Xtr[ok, k]
            if np.std(a) == 0 or np.std(b) == 0:
                continue
            if abs(float(np.corrcoef(a, b)[0, 1])) > rmax:
                red = True; break
        if not red:
            kept.append(j)
    return kept, s


def add_interactions(X, gcode):
    """PROBLEM 2(b): group x feature interactions.

    gcode is 0 for 1-sisterless, 1 for 2/3-sisterless (pooling 2+3 is defensible — she established
    2 vs 3 p=0.181, and pooling STRENGTHENS 1-vs-rest to p=8.71e-6).
    Emitting [X, g, X*g] lets one measurement carry a DIFFERENT slope in each group, which is precisely
    the 'presents another way in 2 or 3 sisterless' case.
    """
    g = gcode.reshape(-1, 1).astype(float)
    return np.hstack([X, g, X * g])


# ---------------------------------------------------------------- BUILD MATRICES
def matrix(batches, feats):
    X = np.full((len(batches), len(feats)), np.nan)
    for i, b in enumerate(batches):
        d = FEATS_ALL.get(b, {})
        for j, f in enumerate(feats):
            v = d.get(f)
            if v is not None:
                X[i, j] = v
    return X


def imp_scale_fit(Xtr, Xte):
    """median-impute + standardise, FIT ON TRAIN ONLY."""
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    A = np.where(np.isfinite(Xtr), Xtr, med)
    B = np.where(np.isfinite(Xte), Xte, med)
    mu, sd = A.mean(0), A.std(0)
    # sd > 0 is not enough: a column with sd ~1e-12 (e.g. a constant that survived imputation with one
    # stray value) divides to ~1e12 and the ridge fit explodes — that is what produced an R2 10th-percentile
    # of -8029 in the first 200-repeat run. Treat anything below 1e-8 as constant.
    sd = np.where(sd > 1e-8, sd, 1.0)
    A = (A - mu) / sd; B = (B - mu) / sd
    # held-out rows can still sit far outside the training range; clip so one extreme cell cannot dominate.
    return np.clip(A, -8, 8), np.clip(B, -8, 8)


# =============================================================== B. REGRESSION — metaphase duration
def regression():
    rows = []
    for b in chromo:
        if lib.plot_excluded(b) or not in_cohort(b): continue
        n = nsis(b); y = meta_min(b); L = lengths(b)
        if n is None or y is None or not L: continue
        rows.append({"b": b, "g": n, "y": y, "sum_len": float(np.sum(L)), "n_sis": float(n),
                     "lag": lagging_flag(b)})
    cells = [r["b"] for r in rows]
    groups = {r["b"]: r["g"] for r in rows}
    byb = {r["b"]: r for r in rows}
    # duration proxies dropped: for a fixed-interval series, n and t_span ARE the metaphase duration
    feats = usable_features(cells, drop_duration_proxies=True)
    print(f"\n{'='*78}\nB. REGRESSION — predict metaphase duration (minutes)")
    print(f"   N={len(rows)} cells  " + str({g: sum(1 for r in rows if r['g'] == g) for g in '123'}))
    print(f"   candidate features={len(feats)} in {len({split_feat(f)[0] for f in feats})} blocks "
          f"(n/t_span/t_at_max/n_per_sis excluded as duration proxies)")
    leaks_b = leak_audit(feats, cells, {r["b"]: r["y"] for r in rows}, False, "metaphase duration")

    scores = defaultdict(list); chosen = defaultdict(int); pergroup = defaultdict(lambda: defaultdict(list)); tuned = {}
    for rep in range(N_REPEATS):
        rng = np.random.RandomState(rep)
        tr, te = stratified_cell_split(list(cells), groups, TEST_FRAC, rng)
        if len(te) < 5 or len(tr) < 15: continue
        ytr = np.array([byb[c]["y"] for c in tr]); yte = np.array([byb[c]["y"] for c in te])
        gtr = np.array([0 if byb[c]["g"] == "1" else 1 for c in tr])
        gte = np.array([0 if byb[c]["g"] == "1" else 1 for c in te])

        Xtr_all, Xte_all = matrix(tr, feats), matrix(te, feats)
        # IN-FOLD HYPERPARAMETER TUNING (was fixed at TOP_BLOCKS=20, alpha=1.0).
        # Widening the admitted pool from 46 to 64 blocks COLLAPSED the ridge (R2 0.398 -> 0.085) while the
        # forest held, which is the signature of selection noise: with 74 cells, "keep 20 blocks" is too
        # many when there are more blocks to choose from. So the selection size and the ridge penalty are
        # now chosen INSIDE the training fold on an inner split, never using held-out rows.
        best, bestsc = (TOP_BLOCKS, 1.0), -9e9
        itr, ite = stratified_cell_split(list(tr), groups, 0.3, np.random.RandomState(rep + 5000))
        if len(ite) >= 4 and len(itr) >= 10:
            iy = np.array([byb[c]["y"] for c in itr]); jy = np.array([byb[c]["y"] for c in ite])
            IX, JX = matrix(itr, feats), matrix(ite, feats)
            for tb in (5, 10, 20, 40):
                kk, _ = select_structured(IX, iy, feats, binary=False, top_blocks=tb)
                if not kk: continue
                a_, b_ = imp_scale_fit(IX[:, kk], JX[:, kk])
                for al in (1.0, 10.0, 100.0):
                    sc = r2_score(jy, Ridge(alpha=al).fit(a_, iy).predict(b_))
                    if sc > bestsc: bestsc, best = sc, (tb, al)
        TB, ALPHA = best
        tuned[best] = tuned.get(best, 0) + 1
        keep, _ = select_structured(Xtr_all, ytr, feats, binary=False, top_blocks=TB)
        if not keep: continue
        for j in keep: chosen[feats[j]] += 1
        A, B = imp_scale_fit(Xtr_all[:, keep], Xte_all[:, keep])

        SL_tr = np.array([[byb[c]["sum_len"]] for c in tr]); SL_te = np.array([[byb[c]["sum_len"]] for c in te])

        def rec(nm, p):
            scores[nm].append(r2_score(yte, p)); scores[nm + "|MAE"].append(mean_absolute_error(yte, p))
            for gc, gname in ((0, "1-sis"), (1, "2/3-sis")):
                m = gte == gc
                if m.sum() >= 4 and np.std(yte[m]) > 0:
                    pergroup[nm][gname].append(r2_score(yte[m], p[m]))

        # lagging PRESENCE appended after selection (see lagging_flag): a single recorded flag, not geometry
        Ltr = np.array([[byb[c]["lag"]] for c in tr]); Lte = np.array([[byb[c]["lag"]] for c in te])
        Al, Bl = imp_scale_fit(np.hstack([Xtr_all[:, keep], Ltr]), np.hstack([Xte_all[:, keep], Lte]))
        rec("structured + lagging", Ridge(alpha=1.0).fit(Al, ytr).predict(Bl))
        la_, lb_ = imp_scale_fit(Ltr, Lte)
        rec("lagging only", Ridge(alpha=1.0).fit(la_, ytr).predict(lb_))
        rec("structured (ridge)", Ridge(alpha=ALPHA).fit(A, ytr).predict(B))
        rec("structured (forest)", RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                                         random_state=rep).fit(A, ytr).predict(B))
        rec("structured + group", Ridge(alpha=1.0).fit(np.hstack([A, gtr.reshape(-1, 1)]), ytr)
            .predict(np.hstack([B, gte.reshape(-1, 1)])))
        rec("structured x group", Ridge(alpha=2.0).fit(add_interactions(A, gtr), ytr)
            .predict(add_interactions(B, gte)))

        # per-group SEPARATE models (PROBLEM 2 taken to its limit: nothing shared between groups)
        psep = np.full(len(te), np.nan)
        for gc in (0, 1):
            mtr, mte = gtr == gc, gte == gc
            if mtr.sum() >= 12 and mte.sum() >= 1:
                Ag, Bg = imp_scale_fit(Xtr_all[np.ix_(mtr, keep)], Xte_all[np.ix_(mte, keep)])
                psep[mte] = Ridge(alpha=1.0).fit(Ag, ytr[mtr]).predict(Bg)
        if np.isfinite(psep).all():
            rec("per-group models", psep)

        sa, sb = imp_scale_fit(SL_tr, SL_te)
        rec("sum_len only", Ridge(alpha=1.0).fit(sa, ytr).predict(sb))
        rec("predict-mean", np.full(len(te), ytr.mean()))
        ysh = ytr.copy(); rng.shuffle(ysh)
        scores["shuffled control"].append(r2_score(yte, Ridge(alpha=1.0).fit(A, ysh).predict(B)))

    order = ["structured (ridge)", "structured + lagging", "structured (forest)", "structured + group",
             "structured x group", "per-group models", "sum_len only", "lagging only", "predict-mean",
             "shuffled control"]
    print(f"\n   {'model':22s} {'R2 med':>8s} {'[10-90%]':>16s} {'MAE':>7s}  {'R2 1-sis':>9s} {'R2 2/3':>8s}")
    res = {}
    for nm in order:
        v = scores.get(nm)
        if not v: continue
        lo, hi = np.percentile(v, [10, 90]); mae = scores.get(nm + "|MAE")
        g1 = pergroup[nm].get("1-sis"); g2 = pergroup[nm].get("2/3-sis")
        res[nm] = {"R2_median": round(float(np.median(v)), 3), "p10": round(float(lo), 3),
                   "p90": round(float(hi), 3),
                   "MAE": round(float(np.median(mae)), 2) if mae else None,
                   "R2_1sis": round(float(np.median(g1)), 3) if g1 else None,
                   "R2_23sis": round(float(np.median(g2)), 3) if g2 else None}
        print(f"   {nm:22s} {np.median(v):8.3f} {f'[{lo:.2f},{hi:.2f}]':>16s} "
              f"{(np.median(mae) if mae else float('nan')):7.2f}  "
              f"{(np.median(g1) if g1 else float('nan')):9.3f} {(np.median(g2) if g2 else float('nan')):8.3f}")
    print("\n   tuned (top_blocks, alpha) chosen per fold: " +
          ", ".join(f"{k}x{v}" for k, v in sorted(tuned.items(), key=lambda kv: -kv[1])[:5]))
    top = sorted(chosen.items(), key=lambda kv: -kv[1])[:25]
    print(f"\n   MOST-SELECTED FEATURES (times chosen out of {len(scores['sum_len only'])} folds):")
    for f, c in top:
        print(f"     {c:4d}  {f}")
    return {"res": res, "chosen": top, "n": len(rows)}


# =============================================================== A. CLASSIFICATION — plate vs polar

# ---- within-cell RANK features (2026-07-22) --------------------------------------------------------
# Her established result: length predicts staying polar in 2/3-sisterless (p=0.019) but NOT in
# 1-sisterless (p=0.79) -- length matters under COMPETITION, which is a statement about a chromosome's
# rank INSIDE its cell, not about micrometres. A model given only absolute length cannot express
# "the longest chromosome in THIS cell", so it cannot represent the effect. These are per-chromosome,
# so like `len` they are appended AFTER block selection, never fed to it.
RANK_COLS = ["length_rank", "length_rank_frac", "length_z_in_cell", "length_over_cell_max",
             "length_over_cell_mean", "length_minus_cell_mean", "is_largest_length",
             "is_smallest_length", "cell_spread_length", "n_in_cell_length"]
_RANKS = {}
try:
    for _r in csv.DictReader(open("/Volumes/4 MB/_scratch/primary_chromosome_ranks.csv")):
        _v = []
        for _c in RANK_COLS:
            try: _v.append(float(_r.get(_c, "")))
            except Exception: _v.append(np.nan)
        _RANKS[(_r["batch"].strip(), str(_r["chr_num"]).strip())] = _v
except Exception as _e:
    print("rank features unavailable:", _e)
def rank_vec(b, chr_num):
    return _RANKS.get((b, str(chr_num)), [np.nan] * len(RANK_COLS))
print(f"rank features loaded for {len(_RANKS)} chromosomes")


def classification():
    rows = []
    for b, rs in chromo.items():
        if lib.plot_excluded(b) or not in_cohort(b): continue
        n = nsis(b)
        if n is None: continue
        for r in rs:
            beh = (r.get("behavior") or "").strip()
            if beh not in ("congressed", "at_plate", "noncongression"): continue
            try: L = float(r.get("length_um") or "")
            except Exception: continue
            rows.append({"b": b, "g": n, "y": 0 if beh == "noncongression" else 1, "len": L,
                         "lag": lagging_flag(b),
                         "rank": rank_vec(b, (r.get("chr_num") or "").strip())})
    cells = sorted({r["b"] for r in rows})
    groups = {r["b"]: r["g"] for r in rows}
    feats = usable_features(cells)
    print(f"\n{'='*78}\nA. CLASSIFICATION — plate vs polar")
    print(f"   N={len(rows)} chromosomes from {len(cells)} cells")
    print(f"   candidate features={len(feats)} in {len({split_feat(f)[0] for f in feats})} blocks")
    # cell-level tripwire: fraction of that cell's chromosomes that reached the plate
    _cellfrac = {c: float(np.mean([r["y"] for r in rows if r["b"] == c])) for c in cells}
    leaks_a = leak_audit(feats, cells, _cellfrac, False, "plate-vs-polar (cell-level)")

    aucs = defaultdict(list); chosen = defaultdict(int); pergroup = defaultdict(lambda: defaultdict(list))
    for rep in range(N_REPEATS):
        rng = np.random.RandomState(rep)
        tr, te = stratified_cell_split(list(cells), groups, TEST_FRAC, rng)
        rtr = [r for r in rows if r["b"] in set(tr)]; rte = [r for r in rows if r["b"] in set(te)]
        ytr = np.array([r["y"] for r in rtr]); yte = np.array([r["y"] for r in rte])
        if len(set(ytr)) < 2 or len(set(yte)) < 2: continue
        gtr = np.array([0 if r["g"] == "1" else 1 for r in rtr])
        gte = np.array([0 if r["g"] == "1" else 1 for r in rte])

        # cell-level warehouse features broadcast onto that cell's chromosomes
        Xtr_all = matrix([r["b"] for r in rtr], feats); Xte_all = matrix([r["b"] for r in rte], feats)
        # chromosome-level length is a real per-chromosome feature, appended after selection
        Ltr = np.array([[r["len"]] for r in rtr]); Lte = np.array([[r["len"]] for r in rte])
        Rtr = np.array([r["rank"] for r in rtr], float); Rte = np.array([r["rank"] for r in rte], float)

        keep, _ = select_structured(Xtr_all, ytr, feats, binary=True)
        if not keep: continue
        for j in keep: chosen[feats[j]] += 1
        A, B = imp_scale_fit(np.hstack([Xtr_all[:, keep], Ltr]), np.hstack([Xte_all[:, keep], Lte]))

        def rec(nm, p):
            aucs[nm].append(roc_auc_score(yte, p))
            for gc, gname in ((0, "1-sis"), (1, "2/3-sis")):
                m = gte == gc
                if m.sum() >= 8 and len(set(yte[m].tolist())) == 2:
                    pergroup[nm][gname].append(roc_auc_score(yte[m], p[m]))

        LGtr = np.array([[r["lag"]] for r in rtr]); LGte = np.array([[r["lag"]] for r in rte])
        Al, Bl = imp_scale_fit(np.hstack([Xtr_all[:, keep], Ltr, LGtr]),
                               np.hstack([Xte_all[:, keep], Lte, LGte]))
        rec("structured + lagging", LogisticRegression(max_iter=2000).fit(Al, ytr).predict_proba(Bl)[:, 1])
        rec("structured", LogisticRegression(max_iter=2000).fit(A, ytr).predict_proba(B)[:, 1])
        Ar, Br = imp_scale_fit(np.hstack([Xtr_all[:, keep], Ltr, Rtr]),
                               np.hstack([Xte_all[:, keep], Lte, Rte]))
        rec("structured + within-cell rank", LogisticRegression(max_iter=2000).fit(Ar, ytr).predict_proba(Br)[:, 1])
        rec("structured + rank (forest)", RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                                 random_state=rep).fit(Ar, ytr).predict_proba(Br)[:, 1])
        Aro, Bro = imp_scale_fit(np.hstack([Ltr, Rtr]), np.hstack([Lte, Rte]))
        rec("length + rank only", LogisticRegression(max_iter=2000).fit(Aro, ytr).predict_proba(Bro)[:, 1])
        Arr, Brr = imp_scale_fit(Rtr, Rte)
        rec("rank only", LogisticRegression(max_iter=2000).fit(Arr, ytr).predict_proba(Brr)[:, 1])
        rec("structured (forest)", RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                          random_state=rep).fit(A, ytr).predict_proba(B)[:, 1])
        rec("structured + group", LogisticRegression(max_iter=2000)
            .fit(np.hstack([A, gtr.reshape(-1, 1)]), ytr)
            .predict_proba(np.hstack([B, gte.reshape(-1, 1)]))[:, 1])
        rec("structured x group", LogisticRegression(max_iter=3000, C=0.5)
            .fit(add_interactions(A, gtr), ytr).predict_proba(add_interactions(B, gte))[:, 1])

        psep = np.full(len(rte), np.nan)
        for gc in (0, 1):
            mtr, mte = gtr == gc, gte == gc
            if mtr.sum() >= 15 and mte.sum() >= 1 and len(set(ytr[mtr].tolist())) == 2:
                Ag, Bg = imp_scale_fit(np.hstack([Xtr_all[:, keep], Ltr])[mtr],
                                       np.hstack([Xte_all[:, keep], Lte])[mte])
                psep[mte] = LogisticRegression(max_iter=2000).fit(Ag, ytr[mtr]).predict_proba(Bg)[:, 1]
        if np.isfinite(psep).all():
            rec("per-group models", psep)

        la, lb = imp_scale_fit(Ltr, Lte)
        rec("length only", LogisticRegression(max_iter=1000).fit(la, ytr).predict_proba(lb)[:, 1])
        ysh = ytr.copy(); rng.shuffle(ysh)
        aucs["shuffled control"].append(
            roc_auc_score(yte, LogisticRegression(max_iter=2000).fit(A, ysh).predict_proba(B)[:, 1]))

    order = ["structured", "structured + within-cell rank", "structured + rank (forest)",
             "structured + lagging", "structured (forest)", "structured + group",
             "structured x group", "per-group models", "length only", "length + rank only",
             "rank only", "shuffled control"]
    print(f"\n   {'model':22s} {'AUC med':>8s} {'[10-90%]':>16s}  {'1-sis':>7s} {'2/3-sis':>8s}")
    res = {}
    for nm in order:
        v = aucs.get(nm)
        if not v: continue
        lo, hi = np.percentile(v, [10, 90])
        g1 = pergroup[nm].get("1-sis"); g2 = pergroup[nm].get("2/3-sis")
        res[nm] = {"AUC_median": round(float(np.median(v)), 3), "p10": round(float(lo), 3),
                   "p90": round(float(hi), 3),
                   "AUC_1sis": round(float(np.median(g1)), 3) if g1 else None,
                   "AUC_23sis": round(float(np.median(g2)), 3) if g2 else None}
        print(f"   {nm:22s} {np.median(v):8.3f} {f'[{lo:.2f},{hi:.2f}]':>16s}  "
              f"{(np.median(g1) if g1 else float('nan')):7.3f} {(np.median(g2) if g2 else float('nan')):8.3f}")
    top = sorted(chosen.items(), key=lambda kv: -kv[1])[:25]
    print(f"\n   MOST-SELECTED FEATURES (times chosen out of {len(aucs['length only'])} folds):")
    for f, c in top:
        print(f"     {c:4d}  {f}")
    return {"res": res, "chosen": top, "n_chrom": len(rows), "n_cells": len(cells)}


# =============================================================== SIGN-FLIP REPORT
def sign_flips():
    """PROBLEM 2(c): does a measurement point the OPPOSITE way in 1-sis vs 2/3-sis?

    Computed on ALL data — this is DESCRIPTIVE, not a model input, so it cannot leak into the held-out
    scores above. It exists to answer 'the same measurement presents another way in 2 or 3 sisterless'.
    """
    rows = []
    for b in chromo:
        if lib.plot_excluded(b) or not in_cohort(b): continue
        n = nsis(b); y = meta_min(b)
        if n is None or y is None: continue
        rows.append((b, 0 if n == "1" else 1, y))
    feats = usable_features([r[0] for r in rows])
    out = []
    for f in feats:
        rr = {}
        for gc in (0, 1):
            xs = [(FEATS_ALL.get(b, {}).get(f), y) for b, g, y in rows if g == gc]
            xs = [(x, y) for x, y in xs if x is not None and np.isfinite(x)]
            if len(xs) < 12: rr = {}; break
            a = np.array([x for x, _ in xs]); c = np.array([y for _, y in xs])
            if np.std(a) == 0 or np.std(c) == 0: rr = {}; break
            rr[gc] = float(np.corrcoef(a, c)[0, 1])
        if len(rr) == 2 and rr[0] * rr[1] < 0 and min(abs(rr[0]), abs(rr[1])) > 0.25:
            out.append((f, round(rr[0], 3), round(rr[1], 3), round(abs(rr[0] - rr[1]), 3)))
    out.sort(key=lambda t: -t[3])
    print(f"\n{'='*78}\nC. SIGN FLIPS vs metaphase duration — 1-sis rho vs 2/3-sis rho")
    print(f"   {len(out)} measurements reverse direction between groups (both |rho|>0.25)")
    for f, a, b_, d in out[:20]:
        print(f"     1-sis {a:+.3f}   2/3-sis {b_:+.3f}   gap {d:.3f}   {f}")
    return out[:40]


if __name__ == "__main__":
    print(f"STRUCTURED MODEL — {N_REPEATS} repeats, {TEST_FRAC:.0%} held out per sisterless group, "
          f"split by cell\nselection INSIDE each training fold: top {TOP_BLOCKS} blocks, "
          f"one feature per stat family, |r|>0.95 pruned")
    A = classification()
    B = regression()
    C = sign_flips()
    json.dump({"classification": A, "regression": B, "sign_flips": C,
               "n_repeats": N_REPEATS, "top_blocks": TOP_BLOCKS},
              open(f"{OUTDIR}/model_structured_results.json", "w"), indent=1)
    print(f"\nwrote {OUTDIR}/model_structured_results.json")
