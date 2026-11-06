#!/usr/bin/env bash
# Launch a swarmtom command on the pod in the background, logging to /workspace/logs/<name>.log.
#   bash scripts/pod_run.sh <name> <swarmtom args...>
# Calls the venv's swarmtom directly: `uv run` would re-sync the env to the lockfile and could
# remove packages installed outside it (flash-linear-attention, causal-conv1d).
set -euo pipefail
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
# Several jobs share the GPU; expandable segments reduce fragmentation-driven OOMs.
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p /workspace/logs
cd /workspace/repo
name=$1; shift
nohup setsid /root/venv/bin/swarmtom "$@" > "/workspace/logs/$name.log" 2>&1 < /dev/null &
echo "started $name (pid $!)"
