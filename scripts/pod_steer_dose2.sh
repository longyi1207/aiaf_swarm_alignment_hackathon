#!/usr/bin/env bash
# Second steering grid (2026-11-08 13:12 amendment): dose-gen / judge / report for configs/dose_check_steer2.yaml.
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/steer.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
say "dose2-gen"
bash scripts/pod_supervise.sh steer_dose2 dose-gen configs/dose_check_steer2.yaml || { say "dose2-gen failed"; exit 1; }
bash scripts/pod_supervise.sh steer_judge2 dose-judge configs/dose_check_steer2.yaml || { say "judge2 failed"; exit 1; }
$SWARMTOM_BIN dose-report runs/dose_check_steer2 > /workspace/logs/steer2_report.log 2>&1
/root/venv/bin/python scripts/select_steer.py runs/dose_check_steer2 > /workspace/logs/steer2_selection.log 2>&1
say "dose2 done"
date -u +%FT%TZ > /workspace/logs/STEER_DOSE2_DONE
