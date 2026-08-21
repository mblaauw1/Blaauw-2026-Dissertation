#!/usr/bin/env python3
"""Should the collagen-plated cells be pooled with the 3-sisterless group, or shown separately?

HER ASK (2026-08-18): "should I include the batches from the collagen-coated plates in other
analyses/figures, either grouped with the 3 ablation group or as its own group? would it be
interesting / show different behaviours / reveal additional information anywhere?"

Collagen is a plating SUBSTRATE, not a drug (feedback_collagen_not_a_drug_exclusion), and the collagen
cells are on-target 2/3-sisterless ablations.  The test is therefore simple: for every headline metric,
is collagen distinguishable from the non-collagen cells of the SAME ablation class?  Where it is not,
pooling is safe and gains n.  Where it is, collagen is its own group and that difference is the finding.
One value per CELL everywhere (NOTES 2026-08-18 item 20).
"""
import csv, io, os, sys, collections
import numpy as np
from scipy import stats as st
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

ROOT = "/Volumes/4 MB"
DATA = ROOT + "/ablation_plots/data"
OUT = ROOT + "/4_TABLES_AND_REPORTS/COLLAGEN_GROUPING_20260818.csv"

def rd(p):
    if not os.path.exists(p): return []
    with io.open(p, encoding="utf-8", errors="replace") as f: return list(csv.DictReader(f))
def fl(x, d=None):
    try:
        s = str(x).strip(); return float(s) if s not in ("", "None", "nan") else d
    except Exception: return d
def hms(v):
    s = str(v or "").strip()
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try:
        if ":" in s:
            p = [float(x or 0) for x in s.split(":")]
            while len(p) < 3: p.insert(0, 0)
            sec = p[0]*3600 + p[1]*60 + p[2]
        else: sec = float(s)
    except ValueError: return None
    return -sec if neg else sec

M, HDR = lib.load_master()
MB = {r["Batch Name"].strip(): r for r in M if (r.get("Batch Name") or "").strip()}
is_col = lambda b: "collagen" in b.lower()

def group_of(b):
    r = MB.get(b)
    if not r: return None
    if (r.get("Exclude") or "").strip().lower() in ("yes", "true", "1"): return None
    if lib.is_drug(b): return None
    if (r.get("On-Target / Off-Target") or "").strip().lower().startswith("off"): return None
    n = (r.get("# Sisterless KTs") or "").strip()
    if n not in ("1", "2", "3"): return None
    if is_col(b): return "collagen (on-target 2/3-sis)"
    return f"{n}-sisterless"

rows = []
def compare(metric, values):           # values: batch -> value (one per cell)
    g = collections.defaultdict(list)
    for b, v in values.items():
        k = group_of(b)
        if k and v is not None: g[k].append(v)
    col = g.get("collagen (on-target 2/3-sis)", [])
    if len(col) < 3: return
    for other in ("3-sisterless", "2-sisterless", "1-sisterless"):
        o = g.get(other, [])
        if len(o) < 4: continue
        p = st.mannwhitneyu(col, o, alternative="two-sided").pvalue
        rows.append(dict(metric=metric, vs=other, n_collagen=len(col), n_other=len(o),
                         median_collagen=round(float(np.median(col)), 4),
                         median_other=round(float(np.median(o)), 4),
                         p=round(float(p), 6),
                         verdict="DIFFERENT — keep separate" if p < .05 else "indistinguishable — safe to pool"))

# ---- 1. master timing
for name, col in (("metaphase duration (min)", "Meta Duration (s)"),
                  ("NEB->metaphase (min)", None)):
    vals = {}
    for b, r in MB.items():
        if name.startswith("metaphase"):
            v = hms(r.get("Meta Duration (s)"))
            if v is None:
                ms, ao = hms(r.get("Metaphase Start (s)")), hms(r.get("Anaphase Onset (s)"))
                v = (ao - ms) if (ms is not None and ao is not None and ao > ms) else None
        else:
            neb, ms = hms(r.get("NEB Time (s)")), hms(r.get("Metaphase Start (s)"))
            v = (ms - neb) if (neb is not None and ms is not None and ms > neb) else None
        if v and v > 0: vals[b] = v / 60
    compare(name, vals)

# ---- 2. recorded plot data: any figure with batch + a numeric column, per cell
def from_csv(pid, valcol, filt=None, label=None):
    r = rd(f"{DATA}/{pid}.csv")
    if not r: return
    per = collections.defaultdict(list)
    for x in r:
        if filt and not filt(x): continue
        v = fl(x.get(valcol))
        b = (x.get("batch") or "").strip()
        if v is not None and b: per[b].append(v)
    compare(label or f"{pid}:{valcol}", {b: float(np.median(v)) for b, v in per.items()})

from_csv("KT_SISTER_KK", "kk_dist_um")
kk = rd(ROOT + "/annotations/KT_SISTER_KK_20260723.csv")
if kk:
    per = collections.defaultdict(list)
    for x in kk:
        if (x.get("phase") or "").strip() != "metaphase": continue
        v = fl(x.get("kk_dist_um")); b = (x.get("batch") or "").strip()
        if v is not None and b: per[b].append(v)
    compare("sister k-k, metaphase (um)", {b: float(np.median(v)) for b, v in per.items()})

from_csv("G8_kt_speed_paired_vs_sisterless", "speed_um_s",
         filt=lambda x: x.get("label") == "paired" and x.get("phase") == "metaphase",
         label="paired KT speed, metaphase (um/s)")
from_csv("G1_area_combined", "value", label="cell area over mitosis")
from_csv("G1_roundness_combined", "value", label="cell roundness over mitosis")
from_csv("G8_polar_chromosome_angle", "angle_deg", label="chromosome angle vs plate (deg)")
from_csv("KT_LOADING_AXIS", "load_extent_um", label="KT distortion along spindle axis (um)")
lo = rd(ROOT + "/annotations/KT_LOADING_AXIS_20260805.csv")
if lo:
    per = collections.defaultdict(list)
    for x in lo:
        v = fl(x.get("load_extent_um")); b = (x.get("batch") or "").strip()
        if v is not None and b: per[b].append(v)
    compare("KT distortion along spindle axis (um)", {b: float(np.median(v)) for b, v in per.items()})

# ---- 3. incidence metrics (fractions per cell -> chi-square style via MW on 0/1)
for name, col in (("polar chromosomes present", "Polar Chromosomes"),
                  ("lagging chromosomes present", "Lagging Chromosomes")):
    vals = {}
    for b, r in MB.items():
        v = (r.get(col) or "").strip().lower()
        if v in ("yes", "true", "1"): vals[b] = 1.0
        elif v in ("no", "false", "0"): vals[b] = 0.0
    compare(name, vals)

seen = set(); uniq = []
for r in rows:
    k = (r["metric"], r["vs"])
    if k in seen: continue
    seen.add(k); uniq.append(r)
with open(OUT, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(uniq[0].keys())); w.writeheader(); w.writerows(uniq)
print(f"{'metric':40s} {'vs':14s} nCol nOth  medCol   medOth    p        verdict")
for r in uniq:
    print(f"{r['metric'][:39]:40s} {r['vs']:14s} {r['n_collagen']:4d} {r['n_other']:4d} "
          f"{r['median_collagen']:8.3f} {r['median_other']:8.3f}  {r['p']:.4g}   {r['verdict']}")
print(f"\n[done] -> {OUT}")
