#!/usr/bin/env bash
# Re-run a resumable `swarmtom run` until it exits cleanly (SSH worker drops are retried; progress is checkpointed).
# usage: scripts/run_with_retry.sh <config> <log>
cfg=$1; log=$2
for attempt in 1 2 3 4 5 6; do
  echo "=== $(date -u +%FT%TZ) attempt $attempt: swarmtom run $cfg --serial-arms" >> "$log"
  PYTHONUNBUFFERED=1 .venv/bin/swarmtom run "$cfg" --serial-arms >> "$log" 2>&1 && { echo "=== $(date -u +%FT%TZ) DONE" >> "$log"; exit 0; }
  echo "=== $(date -u +%FT%TZ) exited with $?; retrying in 20 s" >> "$log"
  sleep 20
done
exit 1
