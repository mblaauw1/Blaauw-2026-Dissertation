#!/usr/bin/env python3
"""ANNOTATION slides for every Mad1 timestrip batch, labelled so the META ones stand out.

USER 2026-08-06: "the mad1 timestrips - open slides with them (and label the ones that are on the meta so
i can tell them apart) in annotation style slides. you can include the whole movies, as opposed to just
including the frames of each used in the timestrip".

Whole movies (--phases abl,mon), not the timestrip's selected frames.

META membership is tested against the FULL figure id including the `_aligned` suffix. A bare-name test
gives a false positive: `..._Eyfpmad1_ablation_1` is a prefix of `..._Eyfpmad1_ablation_10`, which made
ablation_1 look placed when it is not. 5 batches are on META, not 6.
"""
import os, sys, json, subprocess, glob, re

R = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
SRC = "/Volumes/4 MB/pipeline_session_output"
META = "/Volumes/4 MB/ablation_plots/META_FIGURES_20260805.ai"
FIG = "/Volumes/4 MB/ablation_figures_20260625/group4"
INDEX = os.path.join(R, "index_mad1_timestrips_20260806.html")

names = sorted({os.path.basename(p)[len("G5_mad1_timestrip_"):-4].replace("_aligned", "")
                for p in glob.glob(f"{FIG}/G5_mad1_timestrip_*.png") if "_notext" not in p})

links = subprocess.run(["strings", META], capture_output=True, text=True, errors="replace").stdout
on_meta = set()
for n in names:
    # match the exact placed id, with the _aligned suffix, so a prefix cannot false-positive
    if re.search(rf"G5_mad1_timestrip_{re.escape(n)}_aligned\.(pdf|png)", links):
        on_meta.add(n)
print(f"{len(names)} Mad1 timestrip batches; {len(on_meta)} on META: {sorted(on_meta)}\n")

specs, missing = [], []
for n in names:
    batch = n.replace("_", " ", 1)          # "20260304_Mad1_ablation_8" -> "20260304 Mad1_ablation_8"
    pkg = os.path.join(R, batch)
    if not os.path.isdir(pkg):
        d = os.path.join(SRC, batch.split()[0], batch)
        if not os.path.isdir(d):
            print(f"  no render dir: {batch}"); missing.append(batch); continue
        os.makedirs(pkg, exist_ok=True)
        print(f"  building: {batch}", flush=True)
        subprocess.run([sys.executable, "-u", TOOL, "--batch-dir", d, "--pkg-dir", pkg,
                        "--phases", "abl,mon"], capture_output=True, text=True)
        if not os.path.isfile(os.path.join(pkg, "index.html")):
            print(f"   FAIL {batch}"); missing.append(batch); continue
    else:
        print(f"  exists: {batch}")
    specs.append({"name": batch, "pkg_dir": pkg, "_meta": n in on_meta})   # `name` = saved batch identity

# META ones first so they are easy to find
specs.sort(key=lambda s: (0 if s.pop("_meta", False) else 1, s["name"]))   # META first, then name
subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", R, "--phases", "abl,mon"], check=False)
print(f"\n{len(specs)} batches -> {INDEX}")
for b in missing: print(f"  MISSING: {b}")
