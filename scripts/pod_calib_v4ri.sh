#!/usr/bin/env bash
# v4ri baseline calibration (LY 15:15, option B): 8 games, shares the GPU with the ToM v2 pipeline (0.55).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
# idempotent: the ToM pipeline also launches this script; a second launch exits if one is running or done
[ -f /workspace/logs/CALIB_V4RI_DONE ] && exit 0
exec 9> /workspace/logs/calib_v4ri.lock
flock -n 9 || exit 0   # (a pgrep guard matched the launching ssh command itself)
echo "$(date -u +%FT%TZ) calibration v4ri start" >> "$L"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_calib_v4ri.yaml >> /workspace/logs/calib_v4ri_pregen.log 2>&1
bash scripts/pod_supervise.sh calibv4ri run configs/run_calib_v4ri.yaml --python-network audit --tool-workers 64 \
  || { echo "$(date -u +%FT%TZ) calibration v4ri FAILED" >> "$L"; exit 1; }
/root/venv/bin/swarmtom score runs/calib_v4ri > /workspace/logs/calib_v4ri_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/calib_v4ri --samples 12 > /workspace/logs/calib_v4ri_gate.log 2>&1
echo "$(date -u +%FT%TZ) calibration v4ri done" >> "$L"
date -u +%FT%TZ > /workspace/logs/CALIB_V4RI_DONE
