#!/bin/zsh
# wait for BOTH the illustrator fix and the trackmate iteration
until [ -s "/private/tmp/claude-501/-Users-mblaauw/8ed28217-56c6-4aa9-99d7-50d9b69b6813/tasks/bhn4ef4m4.output" ] && grep -q "RECALL" "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log" 2>/dev/null; do sleep 25; done
echo "=== illustrator fix ==="; cat "/private/tmp/claude-501/-Users-mblaauw/8ed28217-56c6-4aa9-99d7-50d9b69b6813/tasks/bhn4ef4m4.output"
echo "=== trackmate v3 ==="; grep -E "RECALL|worst" "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log" | tail -2
