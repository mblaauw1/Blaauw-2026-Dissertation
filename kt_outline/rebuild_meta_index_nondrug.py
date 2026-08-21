#!/usr/bin/env python3
"""Rebuild the multi-batch index over ONLY the 86 non-drugged on-target cdc20 metaphase-ablation batches
(the per-batch packages for all 98 already exist; the 12 drugged ones are simply left out of the index)."""
import os, sys, json, subprocess
PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/meta_ontarget_cdc20_pkgs_20260723"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index.html")
LIST = "/Volumes/4 MB/_scratch/meta_ontarget_cdc20_nondrug.txt"

names = [x for x in open(LIST).read().splitlines() if x.strip()]
specs = [{"name": b, "pkg_dir": os.path.join(PKG_ROOT, b)}
         for b in names if os.path.isfile(os.path.join(PKG_ROOT, b, "index.html"))]
print(f"{len(specs)} of {len(names)} non-drugged packages present -> index")
subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "abl,mon"], check=False)
print("index rebuilt")
