#!/usr/bin/env bash
# vLLM speed test on a copy of the phase-0 run (does not touch runs/phase0_lite).
set -uo pipefail
# expects /workspace/vtest/phase0_lite to hold a copy of the run (cp -a runs/phase0_lite /workspace/vtest/)
cd /workspace/repo
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
export SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
exec /root/vllm-venv/bin/swarmtom run configs/run_phase0_lite_vllm_test.yaml --python-network audit --max-ticks "${1:-2}"
