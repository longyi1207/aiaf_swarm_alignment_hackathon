#!/usr/bin/env bash
# Prepare a pod as an inference worker for controller-side games (2026-11-08): env setup -> vLLM -> WORKER_READY.
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/worker.log; mkdir -p /workspace/logs
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
say "setup"
bash scripts/pod_setup.sh > /workspace/setup.log 2>&1 || { say "SETUP FAILED"; tail -20 /workspace/setup.log >> "$L"; exit 1; }
bash scripts/pod_vllm_install_local.sh > /workspace/logs/vllm_install.log 2>&1
grep -q "^OK " /workspace/logs/vllm_install.log || { say "VLLM INSTALL FAILED"; tail -20 /workspace/logs/vllm_install.log >> "$L"; exit 1; }
HF_HOME=/root/hf HF_HUB_OFFLINE=1 /root/vllm-venv/bin/python -c "import swarmtom.llm.stdio, vllm; print('worker imports ok', vllm.__version__)" >> "$L" 2>&1
say "WORKER_READY"
date -u +%FT%TZ > /workspace/logs/WORKER_READY
