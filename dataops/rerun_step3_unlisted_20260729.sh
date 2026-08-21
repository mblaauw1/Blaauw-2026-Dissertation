#!/bin/bash
# STEP 3 of the frame off-by-one re-run - the 8 FluorTif users that handoff-7 §7 omitted.
#
# WHY THEY WERE OMITTED (established 2026-07-29): the §7 list was built from figure
# provenance. All 8 lack a `code/<fig>__<script>.py` provenance link.
#   * group4_lagging_examples is a GENUINE MISS. It writes G4_lagging_examples.png and
#     G4_lagging_examples_outlined.png, both registered in PLOT_SETTINGS and linked into
#     the deck via _ai_relink/pdf/ - but their `code` field is the retroactive placeholder
#     "deck.py" (handoff-4 §6), so a provenance lookup finds nothing. This is exactly the
#     failure handoff-7 §3.2 warns about: scope must be the UNION of provenance and
#     filename patterns. The v7 SNAPSHOT used the union and does contain both PNGs; the
#     re-run list did not.
#   * The other 7 write a single _UPPERCASE.png QC image each. Not deck content, but they
#     were the EVIDENCE for the centering work and currently show pre-fix numbers.
cd "/Volumes/4 MB/ablation_figures_20260625" || exit 1
LOG="/Volumes/4 MB/_logs/rerun_frameoffbyone_20260728"
mkdir -p "$LOG"

# group4_lagging_examples is DELIBERATELY NOT HERE (her call, 2026-07-29).
# It reads kt_points circle marks labelled 'lagging' and derives a shape (length um,
# aspect) by auto-segmenting around the click point - with a fallback that MANUFACTURES
# an outline at percentile 62 of a central disk. Every panel is timed t+N min from
# ANAPHASE onset. The circle-marking technique is not sufficient for characterizing
# lagging kinetochores in anaphase (it is in metaphase); kt_outlines now carries 602
# manual lagging polygons vs 339 circle marks. Re-running would fix the frame the crop
# is taken from while simultaneously refreshing a superseded measurement, making it look
# newly validated. Both figures are live in the deck (AB13, AB27) - decide retire vs
# rebuild-from-kt_outlines vs re-run-without-the-derived-numbers before running it.
STEP3="diag_filmstrip diag_placement diag_temporal snap_proof \
verify_annotation_placement verify_kt_size verify_snap_demo"

echo "STEP 3" >> "$LOG/_progress.txt"
for s in $STEP3; do
  echo "=== START $s $(date '+%H:%M:%S') ===" >> "$LOG/_progress.txt"
  t0=$(date +%s)
  python3 -u "$s.py" > "$LOG/$s.log" 2>&1
  rc=$?
  t1=$(date +%s)
  echo "=== END   $s rc=$rc $((t1-t0))s ===" >> "$LOG/_progress.txt"
  printf '%s\trc=%s\t%ss\n' "$s" "$rc" "$((t1-t0))" >> "$LOG/_summary.tsv"
done
echo "STEP3 DONE $(date '+%H:%M:%S')" >> "$LOG/_progress.txt"
