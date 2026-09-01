#!/bin/bash
# Self-contained kinetochore tracking — runs entirely off the 4 MB drive.
# Only requirements: 4 MB plugged in + Fiji installed (path below).
#
# Usage:
#   bash run_kt.sh 20260420    # one date
#   bash run_kt.sh all         # all trackable batches (Meta+Anaphase, not Excluded, has render), newest first
#
# Params validated on Cdc20-eYFP data: LoG 0.5um, adaptive quality (p99.9), link 0.8um, gap 1.0um/2fr, minTrack 3.
set -u
ARG="${1:-all}"
CODE="$(cd "$(dirname "$0")" && pwd)"          # .../4 MB/kt_tracking/code
OUT="/Volumes/4 MB/kt_tracking"                # all output stays on 4 MB
FIJI="${FIJI:-/Users/mblaauw/Downloads/Fiji/fiji}"   # override with FIJI=... if elsewhere
[ "$ARG" = "all" ] && MANIFEST="$OUT/stacks/manifest_all_bottomup.json" || MANIFEST="$OUT/stacks/manifest_${ARG}.json"
DIAMETER=0.5; QUALITY=-1; LINKDIST=0.8; GAPDIST=1.0; MAXGAP=2; MINTRACK=3
[ -x "$FIJI" ] || { echo "Fiji not found at $FIJI — set FIJI=/path/to/fiji"; exit 1; }
mkdir -p "$OUT"/{stacks,results,logs,overlays}
RUNLOG="$OUT/logs/run_${ARG}.log"
echo "=== KT tracking '$ARG' ($(date)) — output -> $OUT ===" | tee "$RUNLOG"
echo "building stacks..." | tee -a "$RUNLOG"
python3 "$CODE/kt_track_prep.py" "$ARG" 2>&1 | tee -a "$RUNLOG"
TIFS=()
while IFS= read -r line; do [ -n "$line" ] && TIFS+=("$line"); done < <(python3 -c "import json;[print(e['tif']) for e in json.load(open('$MANIFEST'))]")
N=${#TIFS[@]}
echo "tracking $N batches..." | tee -a "$RUNLOG"
ok=0; fail=0; i=0
for STK in "${TIFS[@]}"; do
  i=$((i+1)); base="$(basename "$STK" .tif)"
  [ -f "$STK" ] || { echo "[$i/$N] MISSING $base" | tee -a "$RUNLOG"; fail=$((fail+1)); continue; }
  echo "[$i/$N] $(date +%H:%M:%S) $base" | tee -a "$RUNLOG"
  "$FIJI" --headless --run "$CODE/kt_trackmate.groovy" \
    "imgPath='$STK',outDir='$OUT/results',diameter=$DIAMETER,quality=$QUALITY,linkdist=$LINKDIST,gapdist=$GAPDIST,maxgap=$MAXGAP,minTrackSpots=$MINTRACK" \
    > "$OUT/logs/track_${base}.log" 2>&1
  if grep -qE "spots, [0-9]+ tracks" "$OUT/logs/track_${base}.log"; then ok=$((ok+1)); else fail=$((fail+1)); fi
done
echo "=== tracked: $ok ok, $fail failed. finalizing + overlays + recording... ===" | tee -a "$RUNLOG"
python3 "$CODE/kt_finalize.py" 2>&1 | tee -a "$RUNLOG"
for STK in "${TIFS[@]}"; do bb="$(basename "$STK" .tif)"; bb="${bb%_KTmon}"
  [ -f "$OUT/results/${bb}.spots_timed.csv" ] && python3 "$CODE/kt_overlay.py" "$bb" >> "$RUNLOG" 2>&1; done
LABEL="$ARG"; [ "$ARG" = "all" ] && LABEL="all_bottomup"
python3 "$CODE/kt_record.py" "$LABEL" 2>&1 | tee -a "$RUNLOG"
echo "=== DONE $(date) — everything on $OUT ===" | tee -a "$RUNLOG"
