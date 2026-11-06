#!/usr/bin/env bash
# Like pod_run.sh, but with the vLLM venv on the local disk (/root/vllm-venv). The agents' run_python
# tool keeps the original environment's interpreter (/root/venv) so pandas / openpyxl versions match.
#   bash scripts/pod_vrun.sh <name> <swarmtom args...>
set -euo pipefail
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python
export VLLM_CACHE_ROOT=/root/.cache/vllm
exec bash "$(dirname "$0")/pod_run.sh" "$@"
