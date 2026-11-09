#!/usr/bin/env bash
# Re-run a resumable `swarmtom run` (all remaining games of every arm in one batch) until it exits cleanly. Before each retry, stop any inference worker left on the
# pod by a dropped SSH session (it would otherwise hold the GPU memory). Progress is checkpointed every tick.
# usage: tools/run_with_retry2.sh <config> <log> <pod-state-json>
cfg=$1; log=$2; pod=$3
for attempt in 1 2 3 4 5 6 7 8; do
  POD_STATE=$pod timeout 60 scripts/pod.sh 'pkill -f "llm[.]stdio"; sleep 5; nvidia-smi --query-gpu=memory.used --format=csv,noheader' >> "$log" 2>&1
  echo "=== $(date -u +%FT%TZ) attempt $attempt: swarmtom run $cfg" >> "$log"
  PYTHONUNBUFFERED=1 .venv/bin/swarmtom run "$cfg" >> "$log" 2>&1 && { echo "=== $(date -u +%FT%TZ) DONE" >> "$log"; exit 0; }
  echo "=== $(date -u +%FT%TZ) exited with $?; retrying in 20 s" >> "$log"
  sleep 20
done
exit 1
