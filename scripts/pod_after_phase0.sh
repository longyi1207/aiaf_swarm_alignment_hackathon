#!/usr/bin/env bash
# After phase0 (vLLM) finishes: empathy judging + report for the vLLM dose check, then score phase0 and
# run the calibration gate. The lesion decision and the main run are started by hand after review.
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
until grep -qE "DONE|GAVE UP" /workspace/logs/phase0v.log; do sleep 10; done
echo "$(date -u +%FT%TZ) phase0 finished: $(grep -E 'DONE|GAVE UP' /workspace/logs/phase0v.log | tail -1)" >> /workspace/logs/chain.log
bash scripts/pod_supervise.sh dose_vllm_judge2 dose-judge configs/dose_check_vllm.yaml
$SWARMTOM_BIN dose-report runs/dose_check_vllm > /workspace/logs/dose_vllm_report.log 2>&1
echo "$(date -u +%FT%TZ) dose_vllm report exit $?" >> /workspace/logs/chain.log
/root/venv/bin/swarmtom score runs/phase0_lite > /workspace/logs/phase0_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/phase0_lite --samples 8 > /workspace/logs/phase0_gate.log 2>&1
echo "$(date -u +%FT%TZ) phase0 scored + gate exit $?" >> /workspace/logs/chain.log
