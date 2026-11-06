#!/usr/bin/env bash
# Run one swarmtom command; if it crashes, restart it (it resumes from its own checkpoints:
# state.json for games, generations.jsonl for the dose check). Gives up after MAX_RESTARTS.
#   bash scripts/pod_supervise.sh <name> <swarmtom args...>     (normally via pod_run.sh)
set -uo pipefail
name=$1; shift
log=/workspace/logs/$name.log
max=${MAX_RESTARTS:-5}
for attempt in $(seq 0 "$max"); do
  echo "=== $(date -u +%FT%TZ) attempt $attempt: swarmtom $*" >> "$log"
  /root/venv/bin/swarmtom "$@" >> "$log" 2>&1 < /dev/null
  code=$?
  if [ $code -eq 0 ]; then
    echo "=== $(date -u +%FT%TZ) DONE (exit 0)" >> "$log"
    exit 0
  fi
  echo "=== $(date -u +%FT%TZ) CRASH exit $code; restarting from checkpoint in 20s" >> "$log"
  echo "$(date -u +%FT%TZ) $name exit $code (attempt $attempt)" >> /workspace/logs/restarts.log
  sleep 20
done
echo "=== $(date -u +%FT%TZ) GAVE UP after $max restarts" >> "$log"
exit 1
