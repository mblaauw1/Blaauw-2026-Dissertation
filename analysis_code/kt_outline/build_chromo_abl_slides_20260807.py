#!/usr/bin/env python3
"""Annotation slides for the 10 single-sisterless batches that lack an AT-ABLATION chromosome trace.

WHY THESE 10: the chromosome length recorded per sisterless chromosome is the line traced on the ABLATION
movie (verified: 72/81 recorded lengths equal that batch's ablation trace). These 10 have no such trace --
6 have monitoring-only traces, 4 have none at all -- so they either sit out of the plot (8) or contribute a
value that matches no trace (2). One traced line on each ablation frame fixes all of them.

WHY REBUILD RATHER THAN INDEX: their existing packages hold ONLY mon_phase/mon_fluor. Without the ablation
movie there is nothing to trace on. Rebuilt with --phases abl,mon (ablation to trace, monitoring for
context). Annotations live in /Volumes/4 MB/annotations/*.csv, not in the package, so rebuilding a package
cannot lose a mark.
"""
import os, sys, json, subprocess, collections

R = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
SRC = "/Volumes/4 MB/pipeline_session_output"
INDEX = os.path.join(R, "index_chromo_abl_trace_20260807.html")

NEED = [  # (batch, group, existing monitoring traces)
    ("20250326 ptk_yfpcdc20__3",                              "C no trace",   0),
    ("20250411 ptk_yfpcdc20_11",                              "B mon-only",   5),
    ("20250930 four_ablation_64",                             "B mon-only",  40),
    ("20251013 max_ablation_18",                              "C no trace",   0),
    ("20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_37",     "C no trace",   0),
    ("20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_50",     "B mon-only",  18),
    ("20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_52",     "B mon-only",   6),
    ("20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_69",     "C no trace",   0),
    ("20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_79",     "B mon-only",  38),
    ("20260303_extra2 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_35","B mon-only", 74),
]
FLAGGED = {"20250326 ptk_yfpcdc20__3": 5.525, "20250411 ptk_yfpcdc20_11": 2.480}

specs, missing = [], []
for batch, grp, nmon in NEED:
    d = None
    for dd in os.listdir(SRC):
        c = os.path.join(SRC, dd, batch)
        if os.path.isdir(c): d = c; break
    if not d:
        print(f"  NO RENDER DIR: {batch}"); missing.append(batch); continue
    pkg = os.path.join(R, batch)
    print(f"  building (abl+mon): {batch}", flush=True)
    p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", d, "--pkg-dir", pkg,
                        "--phases", "abl,mon"], capture_output=True, text=True)
    have_abl = any(f.startswith("abl_") and f.endswith(".mp4") for f in os.listdir(pkg)) if os.path.isdir(pkg) else False
    if not os.path.isfile(os.path.join(pkg, "index.html")):
        print(f"     FAIL {batch}: {p.stderr.strip()[-200:]}"); missing.append(batch); continue
    if not have_abl:
        print(f"     WARNING {batch}: package still has no ablation movie")
    tag = ("*** HAS A FLAGGED LENGTH (%.3f um, matches no trace) *** " % FLAGGED[batch]) if batch in FLAGGED else ""
    specs.append({"name": batch, "pkg_dir": pkg, "_flag": batch in FLAGGED})   # `name` = saved batch identity

specs.sort(key=lambda s: (0 if s.pop("_flag", False) else 1, s["name"]))   # flagged first, then name
subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", R, "--phases", "abl,mon"], check=False)
print(f"\n{len(specs)} batches -> {INDEX}")
for m in missing: print(f"  MISSING: {m}")
