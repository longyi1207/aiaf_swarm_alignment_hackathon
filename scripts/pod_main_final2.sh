#!/usr/bin/env bash
# Final batches (2026-11-08 00:47): random_all30 alone, then the unfinished tom_all30 games alone. Merged, every
# tick waited for the looping tom_all30 agents (~3 min per tick). Then score + analyze -> ROUND3_DONE.
# Replaces scripts/pod_main_final.sh (stopped) and stops its merged run (progress kept).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
for p in $(pgrep -f "[b]ash scripts/pod_main_final.sh"); do kill "$p"; done; bash scripts/pod_stop.sh mainv4_tom_all30_random_all30 run_main_v4_arms_tom_all30_random_all30 >> "$L" 2>&1
say "main_v4: merged batch split (looping tom_all30 agents slowed every tick)"

say "main_v4: final batches: [random_all30], [tom_all30 (unfinished)]"
for pair in "random_all30" "tom_all30"; do
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
