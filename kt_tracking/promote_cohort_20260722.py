#!/usr/bin/env python3
"""Promote the winning TrackMate configuration into the LIVE kt_tracking/results.

WINNER (measured, 2026-07-22): kt_trackmate_v3.groovy per-frame threshold + targetspf=20, run on the
anaphase+15 min stacks. Benchmark 87.3% recall @ 9.4 spots/frame; cohort 86.9% over 53 scorable
batches; marks outside the tracked window 473 -> 13; median longest track covers 90% of
metaphase->anaphase, and 50/76 batches have a track spanning all of anaphase->+5 min.

THIS IS A MERGE, NOT A REPLACEMENT.  The live results dir holds 312 batches; the cohort run covers 83.
Copying the directory over would silently delete tracking for 229 batches, so each promoted batch is
copied in individually and every other batch is left exactly as it was.  `results/CONFIG_BY_BATCH.csv`
records which configuration each batch's results came from, so a mixed dir is never ambiguous.

It does NOT touch any manual annotation store: only kt_tracking/results, KT_TRACKING_MASTER.csv, and
the master's kt_tracking_id / kt_n_tracks columns (all backed up first).

Run with --apply.
"""
import csv, glob, os, shutil, subprocess, sys, datetime

BASE = "/Volumes/4 MB/kt_tracking"
SRC = f"{BASE}/results_cohort_v3spf20_long"
RES = f"{BASE}/results"
STK_LONG = f"{BASE}/stacks_long"
APPLY = "--apply" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
CONFIG = "kt_trackmate_v3.groovy targetspf=20 · stacks_long (anaphase+15min)"

bases = sorted(os.path.basename(p)[:-len(".trackmate.xml")]
               for p in glob.glob(f"{SRC}/*.trackmate.xml"))
print(f"cohort batches to promote: {len(bases)}")
live = sorted(os.path.basename(p)[:-len(".trackmate.xml")]
              for p in glob.glob(f"{RES}/*.trackmate.xml"))
print(f"live results currently hold: {len(live)} batches "
      f"({len(set(live) & set(bases))} of them are in the cohort, "
      f"{len(set(live) - set(bases))} are NOT and will be left untouched)")

if not APPLY:
    print("\n(dry run -- pass --apply)")
    sys.exit(0)

bak = f"{BASE}/results_pre_promote_{STAMP}"
shutil.copytree(RES, bak)
print(f"backed up live results -> {bak}")
for f in ("/Volumes/4 MB/annotations/KT_TRACKING_MASTER.csv", "/Volumes/4 MB/ABLATION_MASTER.csv"):
    shutil.copy(f, f"/Volumes/4 MB/_master_backups/{os.path.basename(f)}.bak_pre_promote_{STAMP}")

n = 0
for b in bases:
    for ext in (".trackmate.xml", ".spots.csv", ".tracks.csv"):
        s = f"{SRC}/{b}{ext}"
        if os.path.isfile(s):
            shutil.copy(s, f"{RES}/{b}{ext}")
    for ext in (".spots_timed.csv", ".tracks_timed.csv"):
        p = f"{RES}/{b}{ext}"
        if os.path.isfile(p):
            os.remove(p)
    n += 1
print(f"copied {n} batches into {RES}")

for p in glob.glob(f"{STK_LONG}/*_timing.csv"):
    b = os.path.basename(p)[:-len("_timing.csv")]
    if b in set(bases):
        shutil.copy(p, f"{BASE}/stacks/{os.path.basename(p)}")
print("copied the promoted batches' long-window timing sidecars into stacks/")

r = subprocess.run([sys.executable, "-u", f"{BASE}/code/kt_finalize.py"],
                   capture_output=True, text=True)
tail = (r.stdout or r.stderr).strip().splitlines()
print("kt_finalize:", tail[-1] if tail else "no output")

rows = set()
for b in live:
    rows.add((b, CONFIG if b in set(bases) else "pre-2026-07-22 (global threshold, anaphase+3min stacks)"))
for b in bases:
    rows.add((b, CONFIG))
with open(f"{RES}/CONFIG_BY_BATCH.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["results_base", "trackmate_config"]); w.writerows(sorted(rows))
print(f"wrote {RES}/CONFIG_BY_BATCH.csv")
print(f"\nPROMOTED {len(bases)} batches. Backup: {bak}")
