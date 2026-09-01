#!/usr/bin/env python3
"""POLE-ANNOTATION slides for the 1-sisterless and 3-sisterless groups of the main metaphase-duration violin.

USER 2026-08-08: "open a set of slides for the one sisterless group plotted on the main metaphase duration
violin plot and another set of slides for the three sisterless group on that plot."

COHORT SOURCE = the violin's OWN plotted data CSV, `ablation_plots/data/G1_violin2_sisterless_1234.csv`,
not a re-derived filter. That file IS what was drawn, so the slides cannot drift from the figure. Checked
2026-08-08: the 1-Sister (36) and 3-Sister (28) batch sets are BYTE-IDENTICAL across all three violin
variants (`_sisterless_1234`, `_mitotic_duration`, `_no_dc_offtarget`), so "the main one" is unambiguous
here -- whichever is meant, the cohort is the same.

TWO SEPARATE INDEXES ON TWO SEPARATE PORTS, one per group, because she asked for two sets and because a
single index would let a mis-click file a 1-sisterless pole under a 3-sisterless cell.

INDEX-ONLY: all 64 packages already exist (verified before writing this), so nothing is re-rendered --
one `--multi-batch` call per group. Each group happens to live entirely inside ONE package root, which is
what makes a single-root server per group possible:
    1-Sister -> _annotation_packages/kt_outline_annot_pkgs_20260722                          (36/36)
    3-Sister -> _annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725 (28/28)

`--phases mon`: all 24 existing pole marks are on the monitoring movie (phase=mon), so the pole tracks
stay on one clock.

NEW PORTS 8818/8819, deliberately NOT the 8816/8817 these roots normally use. Those two were stopped for
this session; a stale browser tab still pointing at them now fails to connect instead of autosaving a
stale annotation list over fresh pole marks -- which is exactly how 225 outlines and 134 Mad1 rows were
clobbered earlier today.
"""
import os, sys, csv, json, subprocess

VIOLIN = "/Volumes/4 MB/ablation_plots/data/G1_violin2_sisterless_1234.csv"
TOOL   = os.path.expanduser("~/ablation-pipeline/make_annotation_html.py")
SERVER = os.path.expanduser("~/ablation-pipeline/serve_annotation.py")

GROUPS = [
    {"cohort": "1-Sister",
     "root":   "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_20260722",
     "index":  "index_pole_1sisterless_20260808.html",
     "port":   8818},
    {"cohort": "3-Sister",
     "root":   "/Volumes/4 MB/_working/_annotation_packages/kt_outline_annot_pkgs_cdc20_two_three_ontarget_20260725",
     "index":  "index_pole_3sisterless_20260808.html",
     "port":   8819},
]

rows = list(csv.DictReader(open(VIOLIN, newline="", encoding="utf-8", errors="replace")))
by_cohort = {}
for r in rows:
    by_cohort.setdefault(r["cohort"], []).append(r)

for g in GROUPS:
    recs = sorted(by_cohort.get(g["cohort"], []), key=lambda r: r["batch"])
    print(f"\n=== {g['cohort']}: {len(recs)} batches plotted on the violin ===")
    specs, missing = [], []
    for r in recs:
        b = r["batch"]
        pkg = os.path.join(g["root"], b)
        if not os.path.isdir(pkg):
            print(f"  NO PACKAGE: {b}"); missing.append(b); continue
        try:    md = f"{float(r['metaphase_duration_min']):6.1f} min"
        except Exception: md = "     ? min"
        print(f"  {b[:54]:54s} meta {md}")
        specs.append({"name": b, "pkg_dir": pkg})    # `name` = the saved batch identity; NEVER decorate it
    if missing:
        for b in missing: print(f"  MISSING PACKAGE: {b}")
    g["_specs"], g["_index_path"] = specs, os.path.join(g["root"], g["index"])

    if specs:
        subprocess.run([sys.executable, "-u", TOOL, "--multi-batch", json.dumps(specs),
                        "--index-out", g["_index_path"], "--pkg-root", g["root"],
                        "--phases", "mon"], check=False)
    print(f"  -> {len(specs)} slides -> {g['_index_path']}")

print("\n=== launching one server per group ===")
for g in GROUPS:
    if not g["_specs"]:
        print(f"  {g['cohort']}: no slides, not serving"); continue
    log = f"/Volumes/4 MB/_claude_tmp/pole_slides_{g['port']}.log"
    with open(log, "w") as lf:
        subprocess.Popen([sys.executable, "-u", SERVER, g["root"], "--port", str(g["port"])],
                         stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
    print(f"  {g['cohort']:9s} port {g['port']}  log {log}")
    print(f"      http://localhost:{g['port']}/{g['index']}")
