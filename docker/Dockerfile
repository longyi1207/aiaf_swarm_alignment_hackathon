# 在完全断网的容器里跑实验（docs/运行指南.md §1）。
# 基础镜像：NVIDIA NGC PyTorch（多架构，含 arm64/DGX Spark）。请在 https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch
# 选一个支持 GB10 / Blackwell 的较新标签，用 --build-arg NGC_TAG=... 传入。未在 Spark 上实测。
ARG NGC_TAG=25.10-py3
FROM nvcr.io/nvidia/pytorch:${NGC_TAG}

WORKDIR /work
# 镜像里已有 CUDA 版 torch；只装其余依赖，不让 pip 替换 torch。
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps -e . \
 && pip install --no-cache-dir "pandas>=2.2" "openpyxl>=3.1" "python-docx>=1.1" "pyyaml>=6.0" "transformers>=4.46" pytest \
 && python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)"

ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["swarmtom"]
