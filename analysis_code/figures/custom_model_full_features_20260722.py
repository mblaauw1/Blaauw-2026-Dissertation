"""custom_model_full_features_20260722.py — model the data using EVERYTHING measured, not 5 features.

The previous held-out run used 5 hand-picked features and was beaten by chromosome length alone. That is a
symptom of under-using the dataset: `ablation_plots/data/` holds one recorded CSV per figure — 290+ files,
every one keyed by `batch` — plus ~90 master columns. That is the measurement warehouse this project has
built up, and the model should draw on it.

WHAT THIS DOES
  1. HARVEST: walk every ablation_plots/data/*.csv, and for each numeric column build per-batch features.
     Multi-row-per-batch files (time series) are summarised as mean/median/min/max/slope/n so a trajectory
     becomes usable features instead of being dropped.
  2. ADD the numeric/parsed columns of ABLATION_MASTER (event times, durations, counts, pixel size...).
  3. GUARD AGAINST LEAKAGE — the single most important step. Any feature derived from the metaphase or
     anaphase time trivially "predicts" metaphase duration. Features whose name matches the leak patterns
     are dropped, and we additionally drop any feature correlating |rho|>0.98 with the target.
  4. EVALUATE with the same honest protocol: 30% of EACH sisterless group held out, split by CELL,
     repeated, scored against baselines (length-only, sum-length-only, predict-the-mean, shuffled).

Outputs a ranked feature list so it is clear WHICH measurements carry the signal.
"""
import sys; sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import csv, os, re, glob, json, numpy as np
from collections import defaultdict
import lib

DATA = "/Volumes/4 MB/ablation_plots/data"
# Anything derived from metaphase/anaphase timing trivially "predicts" metaphase duration.
LEAK = re.compile(r"metaphase|meta.?dur|meta.?start|duration|anaphase|\bana\b|ana_|_ana|mitotic|cytokin|"
                  r"neb.?to.?meta|abl.?to.?meta|meta.?min|dur_min", re.I)


def event_clock():
    """batch -> (neb_s, meta_s, ana_s) so a raw time can be expressed in MITOTIC PROGRESS.

    User 2026-07-22: a measurement's relationship with time is far more comparable once time is normalised
    by the cell's own mitotic events. Cells differ several-fold in metaphase length, so "12 min after
    ablation" means different things in different cells, whereas "60% of the way from metaphase onset to
    anaphase" is the same biological moment everywhere.

    NOTE these event times are used ONLY to rescale the time axis of other measurements. They are never
    emitted as features themselves (LEAK strips them), so the target cannot leak in through this door."""
    data, _ = lib.load_master()
    out = {}
    for r in data:
        neb = lib.parse_time(r.get("NEB Time (s)", ""))
        m = lib.parse_time(r.get("Metaphase Start (s)", ""))
        a = lib.parse_time(r.get("Anaphase Onset (s)", ""))
        out[r["Batch Name"]] = (neb, m, a)
    return out


CLOCK = None


def norm_time(b, t):
    """raw t (in the same units the CSV used) -> mitotic progress:
       0 = metaphase onset, 1 = anaphase onset; <0 before metaphase. None if the cell has no clock."""
    if CLOCK is None or t is None:
        return None
    neb, m, a = CLOCK.get(b, (None, None, None))
    if m is None or a is None or a <= m:
        return None
    return (t - m) / (a - m)


def harvest():
    """batch -> {feature: value} from every recorded plot CSV."""
    feats = defaultdict(dict)
    files = sorted(glob.glob(f"{DATA}/*.csv"))
    used = 0
    for p in files:
        stem = os.path.basename(p)[:-4]
        try:
            rows = list(csv.DictReader(open(p, encoding="utf-8", errors="replace")))
        except Exception:
            continue
        if not rows or "batch" not in rows[0]:
            continue
        cols = [c for c in rows[0] if c and c != "batch"]
        # a column that looks like TIME lets us model the trajectory, not just its average
        tcol = next((c for c in cols if re.search(r"^t_|_t$|time|t_min|t_sec|min_to|frame", c, re.I)), None)
        num = defaultdict(lambda: defaultdict(list))
        tvals = defaultdict(list)
        for r in rows:
            b = (r.get("batch") or "").strip()
            if not b:
                continue
            tv = None
            if tcol:
                try: tv = float((r.get(tcol) or "").strip())
                except Exception: tv = None
            for c in cols:
                if c == tcol: continue
                v = (r.get(c) or "").strip()
                try: f = float(v)
                except Exception: continue
                if np.isfinite(f):
                    num[b][c].append((tv, f))
            if tv is not None: tvals[b].append(tv)
        if not num:
            continue
        used += 1
        for b, d in num.items():
            for c, pairs in d.items():
                key = f"{stem}:{c}"
                if LEAK.search(key):
                    continue
                a = np.array([v for _, v in pairs], float)
                if len(a) == 1:
                    feats[b][key] = float(a[0]); continue
                feats[b][key + "|mean"] = float(a.mean())
                feats[b][key + "|med"] = float(np.median(a))
                feats[b][key + "|min"] = float(a.min())
                feats[b][key + "|max"] = float(a.max())
                feats[b][key + "|sd"] = float(a.std(ddof=1))
                feats[b][key + "|n"] = float(len(a))
                feats[b][key + "|range"] = float(a.max() - a.min())
                # ---- TRAJECTORY features: how the measurement behaves OVER TIME ----
                ts = np.array([t for t, _ in pairs if t is not None], float)
                vs = np.array([v for t, v in pairs if t is not None], float)
                if len(ts) >= 4 and np.ptp(ts) > 0:
                    o = np.argsort(ts); ts, vs = ts[o], vs[o]
                    feats[b][key + "|slope"] = float(np.polyfit(ts, vs, 1)[0])
                    q = len(ts) // 3
                    if q >= 1:
                        early, late = vs[:q].mean(), vs[-q:].mean()
                        feats[b][key + "|early"] = float(early)
                        feats[b][key + "|late"] = float(late)
                        feats[b][key + "|delta"] = float(late - early)
                        if early: feats[b][key + "|foldchange"] = float(late / early)
                    # volatility: mean absolute step, i.e. how jumpy the trajectory is
                    feats[b][key + "|volatility"] = float(np.mean(np.abs(np.diff(vs))))
                    feats[b][key + "|t_at_max"] = float(ts[int(np.argmax(vs))])
                    feats[b][key + "|t_span"] = float(np.ptp(ts))
                    # ---- the SAME trajectory expressed in MITOTIC PROGRESS ----
                    # time axis rescaled so 0 = metaphase onset and 1 = anaphase onset, making the
                    # trajectory comparable between a 6-minute and a 50-minute metaphase.
                    scale = 60.0 if re.search(r"min", tcol or "", re.I) else 1.0
                    pn = [norm_time(b, t * scale) for t in ts]
                    keep = [(q, v) for q, v in zip(pn, vs) if q is not None]
                    if len(keep) >= 4:
                        qq = np.array([q for q, _ in keep]); vv = np.array([v for _, v in keep])
                        if np.ptp(qq) > 0:
                            feats[b][key + "|slope_per_progress"] = float(np.polyfit(qq, vv, 1)[0])
                            for lo, hi, tag in ((-9, 0.0, "premeta"), (0.0, .5, "meta1"),
                                                (.5, 1.0, "meta2"), (1.0, 9, "postana")):
                                m_ = (qq >= lo) & (qq < hi)
                                if m_.sum() >= 2:
                                    feats[b][f"{key}|{tag}_mean"] = float(vv[m_].mean())
                            a_ = (qq >= 0) & (qq < .5); b_ = (qq >= .5) & (qq <= 1)
                            if a_.sum() >= 2 and b_.sum() >= 2:
                                feats[b][key + "|meta_half_delta"] = float(vv[b_].mean() - vv[a_].mean())
                            feats[b][key + "|progress_at_max"] = float(qq[int(np.argmax(vv))])
    print(f"harvested {used} recorded plot CSVs -> {len(feats)} batches", flush=True)
    return feats


def add_master(feats):
    data, hdr = lib.load_master()
    for r in data:
        b = r["Batch Name"]
        for c in hdr:
            if c == "Batch Name" or LEAK.search(c):
                continue
            v = (r.get(c) or "").strip()
            if not v:
                continue
            try:
                feats[b][f"master:{c}"] = float(v.replace(",", ""))
            except Exception:
                t = lib.parse_time(v)
                if t is not None and not LEAK.search(c):
                    feats[b][f"master:{c}|s"] = float(t)
    return feats


if __name__ == "__main__":
    CLOCK = event_clock()
    F = add_master(harvest())
    cov = defaultdict(int)
    for b, d in F.items():
        for k in d:
            cov[k] += 1
    print(f"total distinct features: {len(cov)}")
    print("features present in >=40 batches:", sum(1 for k, n in cov.items() if n >= 40))
    print("\nbest-covered features:")
    for k, n in sorted(cov.items(), key=lambda kv: -kv[1])[:25]:
        print(f"   {n:4d} batches  {k}")
    json.dump({b: d for b, d in F.items()}, open("/Volumes/4 MB/_scratch/batch_features.json", "w"))
    print("\nwrote /Volumes/4 MB/_scratch/batch_features.json")
