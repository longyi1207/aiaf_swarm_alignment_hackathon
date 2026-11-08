#!/usr/bin/env bash
# Run main_v4 one lesion arm at a time (2026-11-07 18:05). With all 7 arms at once (280 agents) the KV cache could
# not hold the conversations, so every tick re-read them (tick time 3 -> 8 min and rising). One arm = 8 games /
# 40 agents fits, so ticks reuse the cache. Games resume from their checkpoints; the design is unchanged.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
for p in $(pgrep -f "[b]ash scripts/pod_round3c.sh"); do kill "$p"; done
bash scripts/pod_stop.sh mainv4 run_main_v4.yaml >> "$L" 2>&1
say "main_v4: switching to one arm at a time (order: none, emp, tom, tom_all30, random, random_tom, random_all30)"
for arm in none emp tom tom_all30 random random_tom random_all30; do
  cfg=configs/run_main_v4_arm_${arm}.yaml
  sed -E "s/^  lesion_conditions: \[.*\]/  lesion_conditions: [$arm]/" configs/run_main_v4.yaml > "$cfg"
  say "main_v4 arm $arm start"
  bash scripts/pod_supervise.sh "mainv4_$arm" run "$cfg" --python-network audit --tool-workers 64 || say "WARNING: arm $arm failed"
  say "main_v4 arm $arm done"
  date -u +%FT%TZ > "/workspace/logs/MAIN_ARM_${arm}_DONE"
done
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
/root/venv/bin/python scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done (all arms)"
date -u +%FT%TZ > /workspace/logs/ROUND3_DONE
