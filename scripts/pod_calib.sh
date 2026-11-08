#!/usr/bin/env bash
# Generic baseline calibration on a shared GPU:  bash scripts/pod_calib.sh <config> <supervise-name> <done-marker>
set -uo pipefail
cd /workspace/repo
CFG=$1 NAME=$2 MARK=/workspace/logs/$3
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
[ -f "$MARK" ] && exit 0
exec 9> "/workspace/logs/$NAME.lock"; flock -n 9 || exit 0
RID=$(/root/venv/bin/python -c "import yaml; print(yaml.safe_load(open('$CFG'))['run_id'])")
echo "$(date -u +%FT%TZ) calibration $RID start" >> "$L"
/root/venv/bin/python scripts/pregen_worlds.py "$CFG" >> "/workspace/logs/${RID}_pregen.log" 2>&1
bash scripts/pod_supervise.sh "$NAME" run "$CFG" --python-network audit --tool-workers 64 \
  || { echo "$(date -u +%FT%TZ) calibration $RID FAILED" >> "$L"; exit 1; }
/root/venv/bin/swarmtom score "runs/$RID" > "/workspace/logs/${RID}_score.log" 2>&1
/root/venv/bin/python scripts/phase0_gate.py "runs/$RID" --samples 12 > "/workspace/logs/${RID}_gate.log" 2>&1
echo "$(date -u +%FT%TZ) calibration $RID done" >> "$L"
date -u +%FT%TZ > "$MARK"
