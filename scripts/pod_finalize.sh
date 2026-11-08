#!/usr/bin/env bash
# After main_v4 (ROUND3_DONE): the pre-registered double-dissociation check (configs/dose_check_dissoc.yaml:
# empathy lesion + its random control + none on the ToM v2 test, budget 4096), now with the prefix-cache fix.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
while [ ! -f /workspace/logs/ROUND3_DONE ]; do sleep 20; done
say "finalize: double-dissociation check (empathy lesion on the ToM v2 test)"
bash scripts/pod_supervise.sh dose_dissoc dose-gen configs/dose_check_dissoc.yaml || say "WARNING: dissociation check failed"
$SWARMTOM_BIN dose-report runs/dose_check_dissoc > /workspace/logs/dose_dissoc_report.log 2>&1
say "finalize done"
date -u +%FT%TZ > /workspace/logs/FINAL_DONE
