#!/usr/bin/env bash
# Kill processes whose command line matches a pattern, never this script or the shell that ran it
# (an ssh "bash -c ..." whose own command line contains the pattern).
#   bash scripts/pod_kill.sh <pattern> [signal]
pat=$1; sig=${2:-TERM}
for pid in $(pgrep -f -- "$pat"); do
  [ "$pid" = "$$" ] || [ "$pid" = "$PPID" ] && continue
  kill -s "$sig" "$pid" 2>/dev/null && echo "killed $pid"
done
