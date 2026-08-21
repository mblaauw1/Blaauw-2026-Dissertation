#!/usr/bin/env python3
"""ANNOTATION slide for the Hec1/Mad1 quantification cell, so she can mark the KINETOCHORE POSITIONS.

USER 2026-08-06: "ok ive made metaphase plate marks on the three batches. open a slide with the three
frames used from xy5 so i can mark the kinetochore positions" — and, decisively:
"this is why the measurement is failing, its your auto-detect method. thats not acceptable to use for this."

The three frames the quantification uses (monitoring clock):
    t =  85.0 s  -> 1:25   unaligned
    t = 442.7 s  -> 7:22   complete biorientation
    t = 904.2 s  -> 15:04  anaphase onset
Her existing 11 cytosol_bg marks sit on frames 1-11 of this same monitoring clip, one per frame, so the
frame numbering lines up: the measured frames are #1, #4 and #7.
"""
import os, sys, json, subprocess

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
B = "20260313 ptk_eyfp_mad1_Hec1halo_640_4_xy5"
INDEX = os.path.join(PKG_ROOT, "index_xy5_kt_20260806.html")

specs = [{"name": B, "pkg_dir": os.path.join(PKG_ROOT, B)}]
subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
print("INDEX:", INDEX)
