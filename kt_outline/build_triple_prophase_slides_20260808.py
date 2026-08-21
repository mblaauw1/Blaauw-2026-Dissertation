#!/usr/bin/env python3
"""KT-outline slides for the THREE triple-ablation PROPHASE cells.

COHORT (user 2026-08-08, "the three triple ablation prophase cells"):
    # Sisterless KTs == 3  AND  On-target  AND  Phase of Ablations == prophase
    AND not Exclude=Yes, not is_drug, not is_mad1, not REVIEW_EXCLUDE
The naive reading (name contains "triple" OR 3-sisterless, prophase) gives 25 -- the filters are what make
it 3. Four ZM cells are dropped by is_drug, the rest by Exclude=Yes.

INDEX ONLY -- all three packages already exist under the 8816 root; re-running make_annotation_html per
batch would re-extract the movie for nothing (standing rule). Phase = mon, which is the KT-outline format
(outlines are traced on monitoring frames).
"""
import os, sys, json, subprocess, csv
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib
csv.field_size_limit(10 ** 9)

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"   # served on 8816
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_triple_prophase_20260808.html")

rows, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in rows}
def g(b, k): return (mr.get(b, {}).get(k, "") or "").strip()
COH = sorted(b for b in mr
             if g(b,"# Sisterless KTs") == "3"
             and g(b,"On-Target / Off-Target") == "On-target"
             and g(b,"Phase of Ablations").lower().startswith("proph")
             and g(b,"Exclude").lower() not in ("yes","true","1")
             and not lib.is_drug(b) and not lib.is_mad1(b) and not lib.excluded(b))
print(f"cohort = {len(COH)}")

# what KT-outline work already exists on each, so the slide label says where to pick up
have = {}
for r in csv.DictReader(open("/Volumes/4 MB/annotations/kt_outlines.csv",
                             newline="", encoding="utf-8", errors="replace")):
    b = (r.get("batch") or "").strip()
    if b in COH: have.setdefault(b, []).append((r.get("label") or "").strip().lower())

specs, missing = [], []
for b in COH:
    pkg = os.path.join(PKG_ROOT, b)
    if not os.path.isdir(pkg):
        print(f"  NO PACKAGE: {b}"); missing.append(b); continue
    lab = have.get(b, [])
    types = sorted(set(lab))
    tag = f"[{len(lab)} kt_outlines: {', '.join(types)}]" if lab else "[NO kt_outlines yet]"
    specs.append({"name": b, "pkg_dir": pkg})   # NEVER decorate: `name` is the saved batch identity
    print(f"  {b[:50]:50s} {tag}")

if specs:
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
print(f"\n{len(specs)} slides -> {INDEX}")
for b in missing: print(f"  MISSING PACKAGE: {b}")
