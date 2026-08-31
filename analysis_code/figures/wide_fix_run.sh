#!/bin/zsh
cd "/Volumes/4 MB/ablation_figures_20260625"
LOG="/Volumes/4 MB/ablation_timestrips_wide_20260710/fix_run.log"; : > "$LOG"
echo "=== FIX START $(date +%H:%M:%S) ===" >> "$LOG"
# 1) delete 127 non-cdc20 timelapse PNGs to force re-render with the correct eYFP-Mad1 label
python3 -c "
import json,os
d='/Volumes/4 MB/ablation_timestrips_wide_20260710/png'
n=0
for b in json.load(open('/tmp/wide_noncdc20_timelapse.json')):
    s=b.replace('/','_').replace(' ','_')
    for suf in ('.png','_notext.png'):
        p=f'{d}/{s}{suf}'
        if os.path.exists(p): os.remove(p); n+=1
print(f'deleted {n} non-cdc20 timelapse files')
" >> "$LOG" 2>&1
echo "=== relabel: re-render non-cdc20 timelapses $(date +%H:%M:%S) ===" >> "$LOG"
python3 wide_timestrips.py >> "$LOG" 2>&1
echo "=== zscan: redo 256 z-stacks (MIP+slices, correct label) $(date +%H:%M:%S) ===" >> "$LOG"
python3 zscan_timestrips.py >> "$LOG" 2>&1
echo "=== assemble: rebuild PDF $(date +%H:%M:%S) ===" >> "$LOG"
python3 assemble_wide.py >> "$LOG" 2>&1
echo "=== FIX DONE $(date +%H:%M:%S) ===" >> "$LOG"
