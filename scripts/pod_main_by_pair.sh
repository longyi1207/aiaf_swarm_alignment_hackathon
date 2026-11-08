#!/usr/bin/env bash
# Remaining main_v4 arms two at a time (2026-11-07 19:32): one arm at a time leaves the GPU nearly idle at the end of
# each arm while one slow game finishes (~15 min per arm). Two arms (16 games, 80 agents) still mostly fit the KV
# cache and let stragglers overlap. Takes over from scripts/pod_main_by_arm.sh after the emp arm.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
for p in $(pgrep -f "[b]ash scripts/pod_main_by_arm.sh"); do kill "$p"; done
while pgrep -f "[p]od_supervise.sh mainv4_emp " > /dev/null; do sleep 15; done
say "main_v4 arm emp done"; date -u +%FT%TZ > /workspace/logs/MAIN_ARM_emp_DONE
say "main_v4: remaining arms two at a time: [tom, tom_all30], [random, random_tom], [random_all30]"
for pair in "tom, tom_all30" "random, random_tom" "random_all30"; do
  name=$(echo "$pair" | tr -d ' ' | tr ',' '_')
  cfg=configs/run_main_v4_arms_${name}.yaml
  sed -E "s/^  lesion_conditions: \[.*\]/  lesion_conditions: [$pair]/" configs/run_main_v4.yaml > "$cfg"
  say "main_v4 arms [$pair] start"
  bash scripts/pod_supervise.sh "mainv4_$name" run "$cfg" --python-network audit --tool-workers 64 || say "WARNING: arms [$pair] failed"
  say "main_v4 arms [$pair] done"
done
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
/root/venv/bin/python scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done (all arms)"
date -u +%FT%TZ > /workspace/logs/ROUND3_DONE
