#!/bin/zsh
cd "/Volumes/4 MB/ablation_figures_20260625"
LOG="/Volumes/4 MB/ablation_timestrips_wide_20260710/rerender_run.log"; : > "$LOG"
echo "=== RERENDER START $(date +%H:%M:%S) ===" >> "$LOG"
python3 wide_timestrips.py >> "$LOG" 2>&1          # re-renders deleted timelapses with the 5 fixes; skips z-stacks
echo "=== assemble PDF $(date +%H:%M:%S) ===" >> "$LOG"
python3 assemble_wide.py >> "$LOG" 2>&1
echo "=== RERENDER DONE $(date +%H:%M:%S) ===" >> "$LOG"
