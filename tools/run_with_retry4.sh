#!/usr/bin/env bash
# Keep a resumable `swarmtom run` going until it exits cleanly or a deadline passes. Waits with backoff (30 s up to
# 5 min) so a local network outage does not exhaust the retries; before each attempt, stops any inference worker left
# on the pod by a dropped SSH session. Progress is checkpointed every tick.
# usage: tools/run_with_retry4.sh <config> <log> <pod-state-json> [--serial-arms]
cfg=$1; log=$2; pod=$3; extra=${4:-}
deadline=$(( $(date +%s) + 8 * 3600 )); wait=30; attempt=0
while [ "$(date +%s)" -lt "$deadline" ]; do
  attempt=$((attempt + 1))
  if ! POD_STATE=$pod timeout 60 scripts/pod.sh 'pkill -f "llm[.]stdio"; sleep 5; nvidia-smi --query-gpu=memory.used --format=csv,noheader' >> "$log" 2>&1; then
    echo "=== $(date -u +%FT%TZ) pod unreachable; waiting ${wait}s" >> "$log"; sleep $wait; wait=$(( wait * 2 > 300 ? 300 : wait * 2 )); continue
  fi
  echo "=== $(date -u +%FT%TZ) attempt $attempt: swarmtom run $cfg $extra" >> "$log"
  start=$(date +%s)
  PYTHONUNBUFFERED=1 .venv/bin/swarmtom run "$cfg" $extra >> "$log" 2>&1 && { echo "=== $(date -u +%FT%TZ) DONE" >> "$log"; exit 0; }
  [ $(( $(date +%s) - start )) -gt 600 ] && wait=30
  echo "=== $(date -u +%FT%TZ) run exited; retrying in ${wait}s" >> "$log"; sleep $wait; wait=$(( wait * 2 > 300 ? 300 : wait * 2 ))
done
exit 1
