#!/usr/bin/env python3
"""KT-outline slides for the batches actually PLOTTED in the "Triple+Double (on-target cdc20) Prophase"
group of G2_noc_washout_vs_prophase.

USER 2026-08-08: the earlier slide set used a literal 3-sisterless prophase filter and did NOT match the
plot. Two differences, both real:
  * `20260107 two_sisterless_kinetochores_3` is 3-sisterless prophase and qualifies on every criterion,
    but the violin hard-excludes it as TD_OUTLIER. User confirmed it STAYS excluded.
  * `20260108 two_sisterless_kinetochores_14` IS in the plot and is 2-SISTERLESS — the group pools
    double with triple, so a strict "==3" filter misses it.

The cohort is therefore derived HERE with the violin's own logic rather than re-specified, so the two can
never drift apart again.
"""
import os, sys, json, subprocess
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import lib

PKG_ROOT = "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725"   # served on 8816
TOOL = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
INDEX = os.path.join(PKG_ROOT, "index_violin_prophase_20260808.html")

data, _ = lib.load_master(); mr = {r["Batch Name"]: r for r in data}
coh = lib.assign_cohorts(include_prophase=True)

def phase_v2(b):
    if lib.is_v2_prometaphase(b): return "Prometaphase"
    p = (mr.get(b, {}).get("Phase of Ablations", "") or "").strip().lower()
    return "Prometaphase" if p.startswith("promet") else ("Prophase" if p.startswith("proph") else None)

def ontarget_cdc20(b):
    r = mr.get(b, {}); ct = (r.get("Cell Type", "") or "").lower()
    if "cdc20" not in ct or "hec1" in ct or "mad1" in ct: return False
    return (r.get("On-Target / Off-Target", "") or "").strip().lower() == "on-target"

TD_OUTLIER = {"20260107 two_sisterless_kinetochores_3"}   # user-confirmed 2026-08-08: stays excluded
combined = [(b, v) for b, v in (coh["2-Sister"] + coh["3-Sister"])
            if ontarget_cdc20(b) and b not in TD_OUTLIER]
COH = sorted(b for b, v in combined if phase_v2(b) == "Prophase")
print(f"plotted 'Triple+Double Prophase' cohort = {len(COH)}")

specs, missing = [], []
for b in COH:
    sis = (mr[b].get("# Sisterless KTs", "") or "").strip()
    md = lib.parse_time(mr[b].get("Meta Duration (s)", ""))
    pkg = os.path.join(PKG_ROOT, b)
    if not os.path.isdir(pkg):
        print(f"  NO PACKAGE: {b}"); missing.append(b); continue
    print(f"  {b[:50]:50s} #sis={sis}  meta {md/60.0:.1f} min")
    specs.append({"name": b, "pkg_dir": pkg})     # name = batch identity; never decorate

if specs:
    subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                    "--index-out", INDEX, "--pkg-root", PKG_ROOT, "--phases", "mon"], check=False)
print(f"\n{len(specs)} slides -> {INDEX}")
for b in missing: print(f"  MISSING: {b}")
