#!/bin/zsh
until grep -q "RECALL" "/Volumes/4 MB/kt_tracking/logs/iter_v4spf20.log" 2>/dev/null; do sleep 40; done
grep -E "RECALL|worst" "/Volumes/4 MB/kt_tracking/logs/iter_v4spf20.log" | tail -2
