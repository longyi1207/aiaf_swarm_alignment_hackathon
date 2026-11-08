#!/usr/bin/env bash
# Weaker empathy steering (2026-11-08 14:50 amendment): dose-gen / judge / report for configs/dose_check_steer3.yaml.
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/steer.log; mkdir -p /workspace/logs
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
say "dose3-gen"
bash scripts/pod_supervise.sh steer_dose3 dose-gen configs/dose_check_steer3.yaml || { say "dose3-gen failed"; exit 1; }
bash scripts/pod_supervise.sh steer_judge3 dose-judge configs/dose_check_steer3.yaml || { say "judge3 failed"; exit 1; }
$SWARMTOM_BIN dose-report runs/dose_check_steer3 > /workspace/logs/steer3_report.log 2>&1
/root/venv/bin/python scripts/select_steer.py runs/dose_check_steer3 > /workspace/logs/steer3_selection.log 2>&1
say "dose3 done"
date -u +%FT%TZ > /workspace/logs/STEER_DOSE3_DONE
