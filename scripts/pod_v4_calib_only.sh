#!/usr/bin/env bash
# If the v4 pipeline stops at lesion selection (no candidate passes the pre-registered criteria), still run the v4
# baseline calibration (unlesioned; independent of the lesions) so the v4 baseline is measured, then stop.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/v4_pipeline.log
until [ -f /workspace/logs/V4_PIPELINE_STOPPED ] || [ -f /workspace/logs/V4_PIPELINE_DONE ]; do sleep 20; done
[ -f /workspace/logs/V4_PIPELINE_DONE ] && exit 0
grep -q "lesion selection" /workspace/logs/V4_PIPELINE_STOPPED || exit 0
echo "$(date -u +%FT%TZ) calib-only: lesion selection stopped the pipeline; running the v4 baseline calibration" >> "$L"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_calib_v4.yaml >> "$L" 2>&1
bash scripts/pod_supervise.sh calibv4 run configs/run_calib_v4.yaml --python-network audit --tool-workers 64
/root/venv/bin/swarmtom score runs/calib_v4 > /workspace/logs/calib_v4_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/calib_v4 --samples 12 > /workspace/logs/calib_v4_gate.log 2>&1
echo "$(date -u +%FT%TZ) calib-only: v4 baseline calibration done" >> "$L"
date -u +%FT%TZ > /workspace/logs/V4_CALIB_ONLY_DONE
