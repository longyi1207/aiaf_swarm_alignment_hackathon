#!/usr/bin/env bash
# dose-gen -> dose-judge -> dose-report for configs/dose_check_vllm.yaml on the vLLM venv.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
echo "$(date -u +%FT%TZ) dose_vllm start" >> /workspace/logs/chain.log
bash scripts/pod_supervise.sh dose_vllm dose-gen configs/dose_check_vllm.yaml && \
bash scripts/pod_supervise.sh dose_vllm_judge dose-judge configs/dose_check_vllm.yaml && \
$SWARMTOM_BIN dose-report runs/dose_check_vllm > /workspace/logs/dose_vllm_report.log 2>&1
echo "$(date -u +%FT%TZ) dose_vllm chain exit $?" >> /workspace/logs/chain.log
