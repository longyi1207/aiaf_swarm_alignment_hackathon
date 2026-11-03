#!/usr/bin/env bash
# 在断网容器里运行一条 swarmtom 命令。模型权重从宿主机的 HF 缓存只读挂载（先在宿主机上下载好）。
# 用法：scripts/run_isolated.sh run configs/run_phase0_baseline.yaml
#      scripts/run_isolated.sh dose-gen configs/dose_check.yaml
# 配置里请设 protocol.python_network: container（容器本身已断网；运行前自检会确认）。
set -euo pipefail
IMAGE="${IMAGE:-swarmtom:latest}"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "building $IMAGE ..." >&2
  docker build -f "$REPO/docker/Dockerfile" -t "$IMAGE" "$REPO"
fi
exec docker run --rm --gpus all --network none --ipc=host \
  -v "$HF_CACHE":/hf:ro -e HF_HOME=/hf \
  -v "$REPO":/work -w /work \
  --user "$(id -u):$(id -g)" \
  "$IMAGE" "$@"
