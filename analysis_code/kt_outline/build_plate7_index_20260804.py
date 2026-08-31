#!/usr/bin/env python3
"""Annotation slides for the 7 triple-on-target cells that have NO metaphase-plate line (2026-08-04).

She is certain these cells have plate lines defined. I could not find one in `meta_plates.csv`, its 14
backups, `META_PLATE_NORMALIZED`, the master `meta_plate_ids` mirror (a verified 1:1 mirror, blank for all
7), 98 browser exports, or any other geometry store on the drive. Rather than keep asserting that, serve the
cells so she can open them and look — the annotation viewer prefills from disk via `GET /load`, so whatever
the store actually holds for these cells is what will appear on the canvas.

The per-batch packages already exist in the 2/3-sisterless on-target root (built 2026-07-25 and served on
port 8816), so nothing is re-encoded here: this writes only an index over those 7.

Monitoring only, matching where plate marks live everywhere else in the store (mon 454 of 462 marks that
carry a role; the other 8 are on the ablation clip).
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_plate7_20260804.html")

BATCHES = [
    "20250918 triple_ablation_29",
    "20250923 triple_ablation_collagen_2",
    "20250925 triple_ablation_7",
    "20251006 triple_ablation_15",
    "20251029 triple_ablation_4",
    "20251029 triple_ablation_26",
    "20251104 ablations_3",
]


def main():
    specs, missing = [], []
    for b in BATCHES:
        pkg = os.path.join(PKG_ROOT, b)
        (specs if os.path.isfile(os.path.join(pkg, "index.html")) else missing).append(
            {"name": b, "pkg_dir": pkg} if os.path.isfile(os.path.join(pkg, "index.html")) else b)
    print(f"{len(specs)} of {len(BATCHES)} packages present")
    for b in missing:
        print(f"  MISSING PACKAGE: {b}")
    if not specs:
        sys.exit("no packages — nothing to serve")
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
    print(f"index -> {INDEX}")


if __name__ == "__main__":
    main()
