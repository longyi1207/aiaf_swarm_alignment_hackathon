#!/usr/bin/env bash
# One-time setup on the RunPod pod (run from /workspace/repo). Logs to /workspace/setup.log.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Fast local disk for the venv and model weights; /workspace (network volume) keeps code and runs.
export UV_CACHE_DIR=/root/uvcache UV_PROJECT_ENVIRONMENT=/root/venv HF_HOME=/root/hf UV_LINK_MODE=copy
apt-get update -qq && apt-get install -y -qq tmux rsync >/dev/null
curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
export PATH="$HOME/.local/bin:$PATH"
cd /workspace/repo
# Model download and environment install run in parallel.
if grep -q DOWNLOAD_OK /workspace/download.log 2>/dev/null; then true & else
( uvx --from huggingface_hub hf download Qwen/Qwen3.5-9B > /workspace/download.log 2>&1 && echo DOWNLOAD_OK >> /workspace/download.log ) &
fi
DL=$!
uv sync --extra model --group dev
uv pip install --python /root/venv/bin/python flash-linear-attention
uv pip install --python /root/venv/bin/python --no-build-isolation causal-conv1d || echo "causal-conv1d unavailable: transformers uses its torch fallback for the short conv"
uv run python -c "import torch, transformers; print('torch', torch.__version__, 'cuda', torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), 'transformers', transformers.__version__)"
uv run python -c "import fla; print('fla', getattr(fla, '__version__', 'ok'))"
uv run pytest -q
wait $DL
tail -2 /workspace/download.log
echo SETUP_DONE
