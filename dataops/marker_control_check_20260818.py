#!/usr/bin/env python3
"""Does the fluorescent marker itself perturb mitosis?  An internal control from our own data.

HER ASK (2026-08-18): a Results sentence citing papers that use these lines without an overexpression
artifact, "as a parallel method to my own controls"; and "if mad1 cells and cdc20 cells have similar
mitotic timings then that's also good support".

This compares mitotic timing between the three labelled lines using ONLY unmanipulated cells --
no ablation of any kind, no drug, not excluded -- so any difference is the marker, not the experiment.
Metrics: NEB->metaphase, metaphase duration, NEB->anaphase.  One value per CELL.
"""
import sys, collections
import numpy as np
from scipy import stats as st
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625"); import lib

M, HDR = lib.load_master()

def hms(v):
    s = str(v or "").strip().replace(",", "")
    if not s: return None
    neg = s.startswith("-"); s = s.lstrip("-")
    try:
        if ":" in s:
            p = [float(x or 0) for x in s.split(":")]
            while len(p) < 3: p.insert(0, 0)
            sec = p[0] * 3600 + p[1] * 60 + p[2]
        else:
            sec = float(s)
    except ValueError:
        return None
    return -sec if neg else sec

def unmanipulated(r):
    b = (r.get("Batch Name") or "").strip()
    if not b: return False
    if (r.get("Exclude") or "").strip().lower() in ("yes", "true", "1"): return False
    if lib.is_drug(b): return False
    n = (r.get("# Sisterless KTs") or "").strip()
    if n not in ("", "0"): return False
    ev = (r.get("Log Ablation Events") or "").strip()
    fa = hms(r.get("First Ablation (s)"))
    if fa is not None or (ev not in ("", "0")): return False
    tgt = (r.get("On-Target / Off-Target") or "").strip()
    if tgt: return False                       # a target means an ablation was attempted
    return True

groups = collections.defaultdict(lambda: collections.defaultdict(list))
for r in M:
    if not unmanipulated(r): continue
    ct = (r.get("Cell Type") or "").strip() or "(blank)"
    neb, ms, ao = hms(r.get("NEB Time (s)")), hms(r.get("Metaphase Start (s)")), hms(r.get("Anaphase Onset (s)"))
    dur = hms(r.get("Meta Duration (s)"))
    if dur is None and ms is not None and ao is not None and ao > ms: dur = ao - ms
    if neb is not None and ms is not None and ms > neb: groups[ct]["neb_to_meta_min"].append((ms - neb) / 60)
    if dur is not None and dur > 0: groups[ct]["meta_duration_min"].append(dur / 60)
    if neb is not None and ao is not None and ao > neb: groups[ct]["neb_to_ana_min"].append((ao - neb) / 60)
    groups[ct]["cells"].append((r.get("Batch Name") or "").strip())

print("UNMANIPULATED CELLS (no ablation attempt, no drug, not excluded) -- one value per cell\n")
for ct, d in sorted(groups.items(), key=lambda kv: -len(kv[1]["cells"])):
    print(f"{ct:26s} cells={len(set(d['cells']))}")
    for k in ("neb_to_meta_min", "meta_duration_min", "neb_to_ana_min"):
        v = d[k]
        if len(v) >= 3:
            print(f"    {k:20s} n={len(v):3d}  median {np.median(v):6.1f} min  "
                  f"IQR {np.percentile(v,25):.1f}-{np.percentile(v,75):.1f}")
        else:
            print(f"    {k:20s} n={len(v)}  (too few)")

print("\nPAIRWISE, Mann-Whitney (two-sided):")
cts = [c for c in groups if len(set(groups[c]["cells"])) >= 3]
for i in range(len(cts)):
    for j in range(i + 1, len(cts)):
        a, b = cts[i], cts[j]
        for k in ("neb_to_meta_min", "meta_duration_min", "neb_to_ana_min"):
            x, y = groups[a][k], groups[b][k]
            if len(x) >= 4 and len(y) >= 4:
                p = st.mannwhitneyu(x, y, alternative="two-sided").pvalue
                flag = "  <-- DIFFERENT" if p < .05 else ""
                print(f"  {k:20s} {a[:20]:22s} (n={len(x):3d}, med {np.median(x):5.1f}) vs "
                      f"{b[:20]:22s} (n={len(y):3d}, med {np.median(y):5.1f})   p={p:.3g}{flag}")
