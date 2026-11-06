#!/usr/bin/env bash
# When the vLLM dose chain finishes, start phase0_lite on vLLM (it needs no lesion decision).
cd /workspace/repo
until grep -q "dose_vllm chain exit" /workspace/logs/chain.log; do sleep 10; done
echo "$(date -u +%FT%TZ) starting phase0 (vLLM)" >> /workspace/logs/chain.log
bash scripts/pod_vrun.sh phase0v run configs/run_phase0_lite.yaml --python-network audit >> /workspace/logs/chain.log 2>&1
