#!/usr/bin/env bash
# Install vLLM into the RAM disk: the /workspace network volume reads small files at ~0.3 MB/s,
# too slow to import torch/vLLM from. Same pinned version as tested (0.33.0).
set -uo pipefail
export PATH=$HOME/.local/bin:$PATH UV_CACHE_DIR=/dev/shm/uvcache UV_LINK_MODE=copy
rm -rf /dev/shm/vllm-venv
uv venv -q -p 3.11 /dev/shm/vllm-venv
uv pip install --python /dev/shm/vllm-venv/bin/python "vllm==0.33.0" pyyaml pandas openpyxl python-docx numpy
uv pip install -q --python /dev/shm/vllm-venv/bin/python --no-deps -e /workspace/repo
rm -rf /dev/shm/uvcache
/dev/shm/vllm-venv/bin/python -c "import vllm, torch; print('OK', vllm.__version__, torch.__version__)"
