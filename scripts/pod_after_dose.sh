#!/usr/bin/env bash
# Pod-side chain: when dose-gen exits, start the smoke game and the empathy judge side by side,
# then build the dose report once the judge is done.
set -uo pipefail
cd /workspace/repo
while pgrep -f "swarmtom dose-gen" >/dev/null; do sleep 10; done
echo "$(date -u +%FT%TZ) dose-gen exited" >> /workspace/logs/chain.log
SWARMTOM_GPU_MEM_FRACTION=0.5 bash scripts/pod_run.sh smoke run configs/run_qwen_smoke.yaml --python-network audit >> /workspace/logs/chain.log
SWARMTOM_GPU_MEM_FRACTION=0.4 bash scripts/pod_run.sh dose_judge dose-judge configs/dose_check.yaml --batch-size 64 >> /workspace/logs/chain.log
sleep 30
while pgrep -f "swarmtom dose-judge" >/dev/null; do sleep 10; done
echo "$(date -u +%FT%TZ) dose-judge exited" >> /workspace/logs/chain.log
/root/venv/bin/swarmtom dose-report runs/dose_check >> /workspace/logs/dose_report.log 2>&1
echo "$(date -u +%FT%TZ) dose-report exit $?" >> /workspace/logs/chain.log
