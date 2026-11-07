#!/usr/bin/env bash
# New pod (2026-11-07 afternoon): set up both envs, then run the v4r baseline calibration only (8 games, $300 bonus).
# The main run waits for the new ToM lesion search (docs/设计.md §8), so this script stops after calibration.
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/bootstrap.log; mkdir -p /workspace/logs
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
say "setup (uv env + model download)"
bash scripts/pod_setup.sh > /workspace/setup.log 2>&1 || { say "SETUP FAILED"; tail -20 /workspace/setup.log >> "$L"; exit 1; }
say "vLLM install"
bash scripts/pod_vllm_install_local.sh > /workspace/logs/vllm_local_install.log 2>&1
grep -q "^OK " /workspace/logs/vllm_local_install.log || { say "VLLM INSTALL FAILED"; tail -20 /workspace/logs/vllm_local_install.log >> "$L"; exit 1; }
date -u +%FT%TZ > /workspace/logs/ENV_READY
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
say "calibration v4r"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_calib_v4r.yaml >> "$L" 2>&1
bash scripts/pod_supervise.sh calibv4r run configs/run_calib_v4r.yaml --python-network audit --tool-workers 64 || { say "calib_v4r failed"; exit 1; }
/root/venv/bin/swarmtom score runs/calib_v4r > /workspace/logs/calib_v4r_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/calib_v4r --samples 12 > /workspace/logs/calib_v4r_gate.log 2>&1
say "calibration v4r done"
date -u +%FT%TZ > /workspace/logs/CALIB_V4R_DONE
