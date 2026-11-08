#!/usr/bin/env bash
# Last two batches (2026-11-07 23:13): the one unfinished random_tom game runs together with the 8 tom_all30 games
# (9 games, 45 agents: fits the KV cache, and the straggler overlaps), then random_all30.
# Replaces scripts/pod_main_rest.sh (stopped) and stops the random_tom run (its finished games are kept).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
for p in $(pgrep -f "[b]ash scripts/pod_main_rest.sh"); do kill "$p"; done; bash scripts/pod_stop.sh mainv4_random_tom run_main_v4_arms_random_tom >> "$L" 2>&1
say "main_v4: random_tom has 7/8 games done; its last game joins the tom_all30 batch"

say "main_v4: last batches: [random_tom (1 game), tom_all30], [random_all30]"
for pair in "random_tom, tom_all30" "random_all30"; do
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
