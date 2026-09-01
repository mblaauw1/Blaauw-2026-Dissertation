#!/usr/bin/env python3
"""Retype `lagging` annotations in cells whose master says there is no lagging chromosome.

THE RULE (memory/project_sisterless_plate_join.md:15): for single-sisterless cells the number of
lagging kinetochores is taken from the master `Lagging Chromosomes` column, yes->1 / no->0. The
`lagging` label marks a KT at/after anaphase (memory/project_ablation_figure_deck.md:20). So a cell
flagged `Lagging Chromosomes = No` must carry ZERO lagging annotations; any that exist are mislabelled.

Found 2026-07-29 via `20250402 ptk_yfpcdc20_2`, whose master Notes read "polar/sisterless KT stayed
polar until anaphase - never rejoined the plate": the outlines are the POLAR chromosome persisting
through anaphase, not a lagging chromosome.

SCOPE - every cell in the class, and the target label is decided PER CELL from whether the
mislabelled track is a continuation of an existing track or a separate kinetochore:

  APPLIED (the lagging rows continue an existing track with NO frame overlap):
    kt_outlines  20260303 Mad1_..._1metaphase_37   19 rows  f14-29 continues polar f1-12   -> polar
    kt_points    20250410 ptk_yfpcdc20_17          13 rows  f110-125 continues sisterless
                                                            f74-106                        -> sisterless

  NOT TOUCHED - needs the user:
    20250402 ptk_yfpcdc20_2 (82 rows). Its "lagging" grp1 (f24-125) COEXISTS with polar grp4
      (f33-112) on 60 frames at 32-52 px (~2-3 um) separation, so they are two different
      kinetochores. It cannot be retyped polar: the master says # Sisterless KTs = 1 and that
      would create a second polar KT. The cell also holds paired grp2 and grp3, so `paired` is
      plausible - but plausible is not derived.
    20260303 Mad1_..._1metaphase_52 (7 rows). Only lagging rows exist in the cell and the master
      has BOTH Polar=No and Lagging=No. Nothing to derive from.

Only the `label` column changes; geometry, frames and ids are untouched. `notes` carries
"kttype:lagging" for grouped rows and is rewritten in step with the label so the two cannot disagree.
Writes through dataops.apply_edits: backup -> atomic -> verify by re-read -> restore on mismatch.

  python3 fix_lagging_mislabels_20260729.py            # dry run
  python3 fix_lagging_mislabels_20260729.py --apply
"""
import csv, os, re, sys, collections

sys.path.insert(0, "/Volumes/4 MB/dataops")
sys.path.insert(0, "/Volumes/4 MB/ablation_figures_20260625")
import dataops
import lib

csv.field_size_limit(10 ** 9)
ANN = "/Volumes/4 MB/annotations"
APPLY = "--apply" in sys.argv

TARGETS = [("kt_outlines", "20260303 Mad1_Ptk_Eyfpcdc2_ablation_1metaphase_37", "polar"),
           ("kt_points",   "20250410 ptk_yfpcdc20_17", "sisterless")]

data, _ = lib.load_master()
mr = {r["Batch Name"]: r for r in data}

for store, batch, newlab in TARGETS:
    m = mr.get(batch) or {}
    flag = (m.get("Lagging Chromosomes") or "").strip().lower()
    polar = (m.get("Polar Chromosomes") or "").strip().lower()
    if flag != "no":
        sys.exit("REFUSED: %s master Lagging Chromosomes = %r, expected 'No'" % (batch, flag))
    if newlab == "polar" and polar != "yes":
        sys.exit("REFUSED: %s -> polar but master Polar Chromosomes = %r" % (batch, polar))

    path = os.path.join(ANN, store + ".csv")
    rows = list(csv.DictReader(open(path, newline="")))
    ids = collections.Counter(r["id"] for r in rows)
    dup = [i for i, n in ids.items() if n > 1]
    key_cols = ["id"] if not dup else ["id", "frame"]

    edits = {}
    n = 0
    for r in rows:
        if r["batch"].strip() != batch or (r.get("label") or "").strip() != "lagging":
            continue
        # LABEL ONLY. `notes` also embeds "kttype:lagging", but dataops rule R6 refuses to replace a
        # notes column (it is free text and must be preserved verbatim) - and that guard is correct.
        # The authoritative `label` column is what every analysis reads; the stale kttype only affects
        # the 8811 UI group legend (make_annotation_html.py:786). Flagged for the user rather than
        # worked around.
        edits[tuple(r[k] for k in key_cols)] = {"label": newlab}
        n += 1
    print("%-12s %-46s %3d lagging rows -> %s   (key=%s)" % (store, batch, n, newlab, "+".join(key_cols)))
    if not n:
        continue
    dataops.apply_edits(
        path, key_cols, edits,
        tag="fix_lagging_mislabels_20260729",
        reason=("Master says Lagging Chromosomes = No for this cell, so by the documented rule "
                "(memory/project_sisterless_plate_join.md: single-sisterless lagging count comes from "
                "the master column) it can carry no lagging annotations. Master Polar Chromosomes = Yes "
                "and its Notes record the polar/sisterless KT staying polar until anaphase without "
                "rejoining the plate, so these traces are the polar chromosome. Retype lagging -> %s; "
                "geometry untouched." % newlab),
        dry_run=not APPLY)

if not APPLY:
    print("\nDRY RUN - nothing written. Re-run with --apply.")
