#!/usr/bin/env python3
"""Kinetochore-outline slides for the TRIPLE-sisterless / on-target / PROMETAPHASE / cdc20 / non-excluded set.

USER 2026-08-06: "open the triple sisterless on target prometaphase cdc20 non-excluded batches in
kinetochore outline format slides" — then, when a rebuild was slow: "it shouldnt take that long. it should
build nearly instantaneously."

She is right, and this is the fix. The per-batch packages ALREADY EXIST in the 2/3-sisterless on-target
root built 2026-07-25 — all 29 of them, checked. So nothing is re-encoded here; this writes only an INDEX
over those existing packages, exactly like build_plate7_index_20260804.py does. Re-running
make_annotation_html.py per batch re-extracts the monitoring movie and takes ~30 s each for no gain.

SET (each filter straight from her sentence):
    Cell Type == 'eYFP cdc20' · On-target · # Sisterless KTs == '3' · Phase of Ablations == prometaphase
    · not lib.plot_excluded (Exclude=Yes, drugs, review outliers, metaphase AND prophase, 4-sisterless)
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_triple_prometa_20260806.html")


def gv(r, c): return (r.get(c, "") or "").strip()


data, _ = lib.load_master()
sel = [r["Batch Name"] for r in data
       if gv(r, "Cell Type").lower() == "eyfp cdc20"
       and gv(r, "On-Target / Off-Target").lower() == "on-target"
       and gv(r, "# Sisterless KTs") == "3"
       and gv(r, "Phase of Ablations").lower().startswith("promet")
       and not lib.plot_excluded(r["Batch Name"])]

specs, missing = [], []
for b in sel:
    pkg = os.path.join(PKG_ROOT, b)
    (specs if os.path.isdir(pkg) else missing).append({"name": b, "pkg_dir": pkg} if os.path.isdir(pkg) else b)

print(f"{len(sel)} batches in the set · {len(specs)} already packaged · {len(missing)} missing")
for b in missing: print("   MISSING PACKAGE:", b)

subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
print("INDEX:", INDEX)
