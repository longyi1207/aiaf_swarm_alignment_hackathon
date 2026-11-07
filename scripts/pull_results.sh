#!/usr/bin/env bash
# Pull every run's data from the pod into local runs/ (agent workspaces excluded: every tool call and result is
# already in events.jsonl, and the worlds are regenerable from their specs). Also pulls the pod's logs.
#   bash scripts/pull_results.sh [run ...]      (default: every run directory on the pod)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
runs=("$@")
if [ ${#runs[@]} -eq 0 ]; then
  while IFS= read -r line; do runs+=("$line"); done < <("$HERE/pod.sh" 'ls -1 /workspace/repo/runs' 2>/dev/null | grep -v '^pod')
fi
mkdir -p "$ROOT/runs" "$ROOT/runs/_pod_logs"
for r in "${runs[@]}"; do
  echo "pulling $r"
  "$HERE/pod.sh" "cd /workspace/repo/runs && tar czf - --exclude='*/workspaces' --exclude='*/worlds/*/batches' $r" \
    | tar xzf - -C "$ROOT/runs" && echo "  ok $(du -sh "$ROOT/runs/$r" | cut -f1)"
done
"$HERE/pod.sh" 'cd /workspace && tar czf - logs' | tar xzf - -C "$ROOT/runs/_pod_logs" && echo "logs ok"
