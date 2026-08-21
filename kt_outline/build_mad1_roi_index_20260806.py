#!/usr/bin/env python3
"""ANNOTATION slides (make_annotation_html.py drawing/canvas viewer) for the 3 Mad1 timestrips on META
whose ROI still relies on the blind tracker.

USER 2026-08-06: "just open ablation_8, Mad1_ablation_10, ptk2_eyfp_mad1_8 in annotation slides ... and
ill make some quick metaphase plate marks on each or something".

ANNOTATION, not review: she is going to MARK, and the rule is "review" -> combined_review.html,
"annotate/mark/outline/measure" -> make_annotation_html.py. (She asked me to check myself on this; checked.)

Why these 3: after 2026-08-06 the Mad1 timestrip ROI follows her manual annotations when they exist —
cell outlines first, then kinetochore marks (manual_centres / manual_kt_anchors in group5_mad1_examples.py).
These 3 have neither, so they keep the template tracker, which locks onto a brighter neighbouring cell
(ablation_8 walks out of frame by 24:18). ANY mark inside the target cell fixes the ROI automatically.

Packages already exist for 2 of the 3, so only the missing one is built — re-running the tool per batch
re-extracts the movie and costs ~30 s for nothing.
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_mad1_roi_20260806.html")
BATCHES = ["20260304 Mad1_ablation_8", "20260304 Mad1_ablation_10", "20260310 ptk2_eyfp_mad1_8"]

import lib
mr = {r["Batch Name"]: r for r in lib.load_master()[0]}

specs = []
for b in BATCHES:
    pkg = os.path.join(PKG_ROOT, b)
    if not os.path.isdir(pkg):
        dp = (mr.get(b, {}).get("Drive Path", "") or "").strip()
        if not dp or not os.path.isdir(dp):
            print(f"  SKIP {b}: no render dir"); continue
        os.makedirs(pkg, exist_ok=True)
        print(f"  building missing package: {b}", flush=True)
        p = subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", dp, "--pkg-dir", pkg,
                            "--phases", "mon"], capture_output=True, text=True)
        if p.returncode != 0 or not os.path.isfile(os.path.join(pkg, "index.html")):
            print(f"  FAIL {b}: {(p.stderr or p.stdout)[-200:]}"); continue
    else:
        print(f"  package already exists: {b}")
    specs.append({"name": b, "pkg_dir": pkg})

subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
print(f"\n{len(specs)} batches -> {INDEX}")
