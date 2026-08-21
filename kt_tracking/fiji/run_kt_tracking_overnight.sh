#!/bin/bash
# run_kt_tracking_overnight.sh — unattended kinetochore tracking.
# Click-go: builds stitched stacks, tracks each batch with TrackMate, finalizes
# real-time velocities, renders a QC overlay movie, writes a QC summary.
# ALL output goes to the 5 MB drive (/Volumes/5 MB/kt_tracking).
#
# Usage:
#   bash run_kt_tracking_overnight.sh 20260420   # one date
#   bash run_kt_tracking_overnight.sh all         # ALL trackable batches, newest cells first
#
# Tunables (validated on 0420 Cdc20-eYFP data — see logs/probe_*.log):
#   DIAMETER 0.5 um   kinetochore-sized LoG blob (diffraction-limited GFP)
#   QUALITY  -1       ADAPTIVE per-movie threshold = quality p99.9 (noise ceiling).
#                     Auto-adapts to each date's brightness (0420~2.0, 0901~3.6).
#                     Set a value >=0 to force a fixed threshold instead.
#   LINKDIST 0.8 um / GAPDIST 1.0 um / MAXGAP 2   link KTs, bridge brief dropouts
#   MINTRACK 3        keep tracks seen in >=3 frames (KTs/frame are sparse: 3-15)
set -u

ARG="${1:-20260420}"
CODE="$(cd "$(dirname "$0")" && pwd)"
OUT="/Volumes/5 MB/kt_tracking"
FIJI=/Users/mblaauw/Downloads/Fiji/fiji
[ "$ARG" = "all" ] && MANIFEST="$OUT/stacks/manifest_all_bottomup.json" || MANIFEST="$OUT/stacks/manifest_${ARG}.json"

DIAMETER=0.5; QUALITY=-1; LINKDIST=0.8; GAPDIST=1.0; MAXGAP=2; MINTRACK=3
# latest (2026-07-20): per-frame de-dup MERGEDIST (um) + density-adaptive TARGETSPF (keep top N spots/frame by
# quality) — reduces cytosol fragmentation on Cdc20 cells. Override via env: MERGEDIST=.. TARGETSPF=..
MERGEDIST=${MERGEDIST:-0.5}; TARGETSPF=${TARGETSPF:-5}

mkdir -p "$OUT"/{stacks,results,logs,overlays}
RUNLOG="$OUT/logs/overnight_${ARG}.log"
echo "=== KT tracking run '$ARG'  ($(date)) ===" | tee "$RUNLOG"

# (Re)build stacks for this scope.
echo "building stacks..." | tee -a "$RUNLOG"
python3 "$CODE/kt_track_prep.py" "$ARG" 2>&1 | tee -a "$RUNLOG"

# bash 3.2 (macOS) has no mapfile; read into the array portably.
TIFS=()
while IFS= read -r line; do [ -n "$line" ] && TIFS+=("$line"); done < <(python3 -c "import json; [print(e['tif']) for e in json.load(open('$MANIFEST'))]")
N=${#TIFS[@]}
echo "tracking $N batches: diam=$DIAMETER q=$QUALITY link=$LINKDIST gap=$GAPDIST/$MAXGAP minTrack=$MINTRACK merge=$MERGEDIST targetspf=$TARGETSPF" | tee -a "$RUNLOG"

i=0; ok=0; fail=0
for STK in "${TIFS[@]}"; do
  i=$((i+1)); base="$(basename "$STK" .tif)"
  [ -f "$STK" ] || { echo "[$i/$N] MISSING $base" | tee -a "$RUNLOG"; fail=$((fail+1)); continue; }
  echo "[$i/$N] $(date +%H:%M:%S) $base" | tee -a "$RUNLOG"
  blog="$OUT/logs/track_${base}.log"
  "$FIJI" --headless --run "$CODE/kt_trackmate.groovy" \
    "imgPath='$STK',outDir='$OUT/results',diameter=$DIAMETER,quality=$QUALITY,linkdist=$LINKDIST,gapdist=$GAPDIST,maxgap=$MAXGAP,minTrackSpots=$MINTRACK,mergedist=$MERGEDIST,targetspf=$TARGETSPF" \
    > "$blog" 2>&1
  if grep -qE "spots, [0-9]+ tracks" "$blog"; then
    echo "      $(grep -E 'spots, [0-9]+ tracks' "$blog" | tail -1 | sed 's/.*: //')" | tee -a "$RUNLOG"
    ok=$((ok+1))
  else
    echo "      FAILED (see $blog)"; tail -3 "$blog" | sed 's/^/         /' | tee -a "$RUNLOG"
    fail=$((fail+1))
  fi
done

echo "=== tracking done: $ok ok, $fail failed. finalizing timing... ===" | tee -a "$RUNLOG"
python3 "$CODE/kt_finalize.py" 2>&1 | tee -a "$RUNLOG"

# Overlays AFTER finalize (they need spots_timed.csv). One per tracked batch.
echo "=== rendering QC overlays... ===" | tee -a "$RUNLOG"
for STK in "${TIFS[@]}"; do
  b="$(basename "$STK" .tif)"; bb="${b%_KTmon}"
  [ -f "$OUT/results/${bb}.spots_timed.csv" ] && python3 "$CODE/kt_overlay.py" "$bb" >> "$RUNLOG" 2>&1
done
echo "=== ALL DONE $(date) ===" | tee -a "$RUNLOG"
echo "Output on 5 MB drive:" | tee -a "$RUNLOG"
echo "  $OUT/results/   spots_timed.csv, tracks_timed.csv, KT_tracking_summary.csv" | tee -a "$RUNLOG"
echo "  $OUT/overlays/  per-batch QC movies" | tee -a "$RUNLOG"
