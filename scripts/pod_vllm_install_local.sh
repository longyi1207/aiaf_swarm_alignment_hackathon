#!/usr/bin/env bash
# Install vLLM on the local container disk (the /workspace network volume is too slow to import from,
# /dev/shm is noexec). The download cache lives in /dev/shm and is deleted afterwards. vLLM 0.33.0.
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH UV_CACHE_DIR=/dev/shm/uvcache UV_LINK_MODE=copy
rm -rf /dev/shm/vllm-venv /root/vllm-venv
uv venv -q -p 3.11 /root/vllm-venv
uv pip install --python /root/vllm-venv/bin/python "vllm==0.33.0" pyyaml pandas openpyxl python-docx numpy
uv pip install -q --python /root/vllm-venv/bin/python --no-deps -e /workspace/repo
rm -rf /dev/shm/uvcache
df -h / | tail -1
/root/vllm-venv/bin/python -c "import vllm, torch; print('OK', vllm.__version__, torch.__version__)"
