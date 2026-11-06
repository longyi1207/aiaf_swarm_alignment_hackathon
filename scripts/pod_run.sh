#!/usr/bin/env bash
# Launch a swarmtom command on the pod in the background under the crash supervisor,
# logging to /workspace/logs/<name>.log.
#   bash scripts/pod_run.sh <name> <swarmtom args...>
#   SWARMTOM_GPU_MEM_FRACTION=0.4 bash scripts/pod_run.sh ...   # when sharing the GPU with another job
# Calls the venv's swarmtom directly: `uv run` would re-sync the env to the lockfile and could
# remove packages installed outside it (flash-linear-attention).
set -euo pipefail
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
# Several jobs share the GPU; expandable segments reduce fragmentation-driven OOMs.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p /workspace/logs
cd /workspace/repo
name=$1; shift
nohup setsid bash scripts/pod_supervise.sh "$name" "$@" > /dev/null 2>&1 < /dev/null &
echo "started $name (supervisor pid $!)"
