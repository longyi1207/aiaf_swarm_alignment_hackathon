#!/usr/bin/env bash
# One SSH round-trip that summarises everything on the pod, plus local spend.
# Usage: scripts/experiment_status.sh
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
echo "== spend"
python3 "$HERE/runpod.py" status 2>&1 | tail -1
"$HERE/pod.sh" 'bash -s' <<'REMOTE'
cd /workspace/repo 2>/dev/null || exit 0
echo "== gpu"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader
echo "== processes"
pgrep -fa "swarmtom|pod_setup|hf download" | grep -v pgrep | cut -c1-160 || echo "(none)"
for r in runs/*/; do
  [ -d "$r" ] || continue
  name=$(basename "$r")
  if [ -f "$r/generations.jsonl" ]; then
    echo "== $name (dose): generations $(wc -l < "$r/generations.jsonl"), judgments $(cat "$r/judgments.jsonl" 2>/dev/null | wc -l), report $(test -f "$r/report.md" && echo yes || echo no)"
  fi
  if [ -d "$r/games" ]; then
    total=$(ls "$r/games" | wc -l)
    done=$(ls "$r"/games/*/result.json 2>/dev/null | wc -l)
    echo "== $name (games): finished $done / $total"
    tail -n 2 "$r/progress.log" 2>/dev/null | cut -c1-260
  fi
done
for f in /workspace/logs/*.log; do
  [ -f "$f" ] || continue
  echo "== log $(basename "$f") (last error lines, if any)"
  grep -E "Traceback|Error|error:|CUDA out of memory|Killed" "$f" | tail -3
  tail -n 1 "$f" | cut -c1-200
done
REMOTE
