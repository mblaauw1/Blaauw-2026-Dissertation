#!/usr/bin/env python3
"""Filtered KT-OUTLINE slide index over the DOUBLE + TRIPLE cdc20 on-target set, restricted to the
cells that HAVE LAGGING CHROMOSOMES (user 2026-08-03).

The per-batch packages already exist for the whole 46-cell set in
`_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725` (built 2026-07-25, served on port 8816).
Nothing is re-encoded here — this only writes a SECOND index HTML into that same package root, listing
the lagging subset. The existing `index.html` is untouched, so both work queues stay available and the
packages are not duplicated on a drive that has run short of space.

SET (base set == build_cdc20_two_three_ontarget_slides.py, verbatim):
    Cell Type == 'eYFP cdc20'  AND  On-Target  AND  # Sisterless KTs in {2,3}
    AND not lib.plot_excluded  (drops Exclude=Yes, drugs incl. ZM, review outliers,
        metaphase-ablations, 4-sisterless)   AND Metaphase Start (s) + Anaphase Onset (s) defined
  PLUS the lagging filter:
    master `Lagging Chromosomes` == Yes.

  `Lagging Chromosomes` is the BEHAVIOURAL master flag, which is the right source here (NOTES §1
  rule 27: the outline label is the kinetochore's identity, the master column is the cell's behaviour).
  It is deliberately NOT derived from existing lagging outlines — most of these cells have not been
  traced yet, which is the whole point of the queue.

WHY these cells: in a double/triple-ablation cell there can be MORE THAN ONE polar or lagging
kinetochore at a time, unlike the single-ablation cells on 8811. Use "+ New KT" for each distinct
kinetochore; traces sharing one group are pieces of one (possibly fractured) kinetochore.
"""
import os, sys, json, subprocess

os.chdir("/Volumes/4 MB/ablation_figures_20260625"); sys.path.insert(0, ".")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_lagging_20260803.html")
LIST = "/Volumes/4 MB/_scratch/lagging_two_three_ontarget_20260803.txt"


def _defined(v):
    return bool((v or "").strip())


def batch_set():
    data, _ = lib.load_master()
    return [r for r in data
            if (r.get("Cell Type", "") or "").strip().lower() == "eyfp cdc20"
            and (r.get("On-Target / Off-Target", "") or "").strip().lower() == "on-target"
            and (r.get("# Sisterless KTs", "") or "").strip() in ("2", "3")
            and not lib.plot_excluded(r["Batch Name"])
            and _defined(r.get("Metaphase Start (s)")) and _defined(r.get("Anaphase Onset (s)"))
            and (r.get("Lagging Chromosomes", "") or "").strip().lower() == "yes"]


def main():
    sel = batch_set()
    print(f"{len(sel)} double/triple on-target cdc20 cells with lagging chromosomes")
    specs, missing = [], []
    for r in sel:
        b = r["Batch Name"]
        pkg = os.path.join(PKG_ROOT, b)
        if os.path.isfile(os.path.join(pkg, "index.html")):
            specs.append({"name": b, "pkg_dir": pkg})
        else:
            missing.append(b)
    os.makedirs(os.path.dirname(LIST), exist_ok=True)
    with open(LIST, "w") as f:
        f.write("\n".join(s["name"] for s in specs) + "\n")
    print(f"{len(specs)} packages present, {len(missing)} missing")
    for b in missing:
        print(f"  MISSING PACKAGE: {b}")
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
    print(f"index -> {INDEX}")


if __name__ == "__main__":
    main()
