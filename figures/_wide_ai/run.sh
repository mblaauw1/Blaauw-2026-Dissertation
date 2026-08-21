#!/bin/zsh
SRC="/Volumes/4 MB/ablation_figures_20260625/_wide_ai/place_grid.jsx"
MAN="/Volumes/4 MB/ablation_timestrips_wide_20260710/wide_png_list.txt"
OUT="/Volumes/4 MB/ablation_timestrips_wide_20260710/ablation_timestrips_wide_20260710.ai"
START=$1; COUNT=$2
TMP="/tmp/place_grid_run.jsx"
sed -e "s#__MANIFEST__#$MAN#g" -e "s#__OUTAI__#$OUT#g" -e "s#__START__#$START#g" -e "s#__COUNT__#$COUNT#g" "$SRC" > "$TMP"
osascript -e 'with timeout of 3000 seconds' -e "tell application \"Adobe Illustrator\" to do javascript (POSIX file \"$TMP\")" -e 'end timeout'
