#!/bin/zsh
until grep -q "RECALL" "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log" 2>/dev/null; do sleep 30; done
grep -E "RECALL|worst" "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log" | tail -3
