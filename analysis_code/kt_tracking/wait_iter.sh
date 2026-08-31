#!/bin/zsh
until [ -f "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log" ] && grep -q "RECALL" "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log"; do sleep 20; done
tail -4 "/Volumes/4 MB/kt_tracking/logs/iter_v3perframe.log"
