#!/usr/bin/env bash
# Steering dose check on a fresh pod (2026-11-08): env setup -> vLLM -> tests (torch present here) -> vector norms
# -> dose-gen / judge / report for configs/dose_check_steer.yaml -> STEER_DOSE_DONE.
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/steer.log; mkdir -p /workspace/logs
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
say "setup"
bash scripts/pod_setup.sh > /workspace/setup.log 2>&1 || { say "SETUP FAILED"; tail -20 /workspace/setup.log >> "$L"; exit 1; }
bash scripts/pod_vllm_install_local.sh > /workspace/logs/vllm_install.log 2>&1
grep -q "^OK " /workspace/logs/vllm_install.log || { say "VLLM INSTALL FAILED"; tail -20 /workspace/logs/vllm_install.log >> "$L"; exit 1; }
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
/root/venv/bin/python -m pytest -q tests/test_steer.py tests/test_lesion.py >> "$L" 2>&1 || { say "STEER TESTS FAILED"; exit 1; }
/root/venv/bin/python - >> "$L" 2>&1 <<'PY'
import torch
t = torch.load("assets/vectors/axes_tom_v2.pt", weights_only=False)["vectors"]["tau2"]
e = torch.load("assets/vectors/axes_vectors.pt", weights_only=False)["vectors"]["epsilon"]
print("tau2 norms L12-20:", [round(float(t[l].norm()), 3) for l in range(12, 21)])
print("epsilon norms L13-21:", [round(float(e[l].norm()), 3) for l in range(13, 22)])
PY
date -u +%FT%TZ > /workspace/logs/ENV_READY
say "dose-gen"
bash scripts/pod_supervise.sh steer_dose dose-gen configs/dose_check_steer.yaml || { say "dose-gen failed"; exit 1; }
bash scripts/pod_supervise.sh steer_judge dose-judge configs/dose_check_steer.yaml || { say "judge failed"; exit 1; }
$SWARMTOM_BIN dose-report runs/dose_check_steer > /workspace/logs/steer_report.log 2>&1
say "done"
date -u +%FT%TZ > /workspace/logs/STEER_DOSE_DONE
