#!/usr/bin/env bash
# Takes over from scripts/pod_tom2b_pipeline.sh (2026-11-07 15:15, LY chose baseline v4ri): after the thinking-on
# screen generation, start the v4ri calibration alongside the rest of the ToM v2 search, then run the main
# experiment with brief v4ri if the calibration passes. Rules: docs/设计.md §8.
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
export TOM2_CONFIRM_RUN=dose_check_tom2_screen_on
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/TOM2_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }
PY=/root/venv/bin/python
calib_running() { [ ! -f /workspace/logs/CALIB_V4RI_DONE ] && pgrep -f "[p]od_calib_v4ri" > /dev/null; }
wait_calib() { while calib_running; do sleep 20; done
  [ -f /workspace/logs/CALIB_V4RI_DONE ] || say "WARNING: v4ri calibration ended without CALIB_V4RI_DONE"; }
gpu_mem() { local cfg=$1 shared=$2 alone=$3
  if calib_running; then sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$shared/" "$cfg"; else sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$alone/" "$cfg"; fi
  grep -n "gpu_memory_utilization" "$cfg" | sed "s|^|$cfg: |" >> "$L"; }

say "tom2c: waiting for the thinking-on screen generation to finish"
while pgrep -f "[p]od_supervise.sh dose_tom2_screen_on " > /dev/null; do sleep 15; done
tail -n 1 /workspace/logs/dose_tom2_screen_on.log | grep -q "DONE (exit 0)" || stop "thinking-on screen generation failed"
(nohup setsid bash scripts/pod_calib_v4ri.sh > /dev/null 2>&1 < /dev/null &)
sleep 90   # let the calibration's vLLM claim its share first

gpu_mem configs/dose_check_tom2_screen_on.yaml 0.30 0.90
sup dose_tom2_screen_on_judge dose-judge configs/dose_check_tom2_screen_on.yaml || stop "thinking-on screen judging failed"
$SWARMTOM_BIN dose-report runs/dose_check_tom2_screen_on > /workspace/logs/dose_tom2_screen_on_report.log 2>&1
tom_ok=1
$PY scripts/select_tom2.py --stage confirm >> "$L" 2>&1; rc=$?
[ $rc -eq 0 ] || { [ $rc -eq 2 ] && { say "thinking-on screen: no ToM v2 candidate passes"; tom_ok=0; } || stop "selection crashed"; }

rm -f runs/probe_tom2/probe_check.json
if [ $tom_ok -eq 1 ]; then
  say "4. agent probe"
  grep -n "run_id\|brief\|lesion_conditions" configs/run_probe_tom2.yaml >> "$L"
  gpu_mem configs/run_probe_tom2.yaml 0.35 0.94
  $PY scripts/pregen_worlds.py configs/run_probe_tom2.yaml >> "$L" 2>&1
  sup probe_tom2 run configs/run_probe_tom2.yaml --python-network audit --tool-workers 64 --max-ticks 8 || stop "probe failed"
  $PY scripts/v4_probe_check.py runs/probe_tom2 >> "$L" 2>&1
fi

say "5. final lesions"
$PY scripts/select_tom2.py --stage final >> "$L" 2>&1 || stop "final selection crashed"
grep -n "lesion_conditions" configs/run_main_v4.yaml >> "$L"
date -u +%FT%TZ > /workspace/logs/TOM2_LESIONS_DONE

say "6. calibration gate (runs/calib_v4ri): waiting for it to finish"
wait_calib
[ -f runs/calib_v4ri/results/phase0_gate.json ] || stop "lesions chosen; no calibration result (runs/calib_v4ri)"
pick=$($PY - <<'PYEOF' 2>> "$L"
import json, sys
g = json.load(open("runs/calib_v4ri/results/phase0_gate.json"))
v = (g.get("per_brief") or {}).get("v4ri+r300")
print(f"# v4ri+r300: {v}", file=sys.stderr)
if v and v["accuracy"] >= 0.70 and 0.15 <= v["filed_E_rate"] <= 0.85 and v.get("opened_personal", 0) >= 0.5:
    print("ok")
PYEOF
)
[ "$pick" = "ok" ] || stop "lesions chosen (runs/$TOM2_CONFIRM_RUN/decision.json); v4ri calibration did not pass"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: v4ri, monthly_pay_usd: 6000, award_usd: 300}/" configs/run_main_v4.yaml
sed -i -E "s/^(  gpu_memory_utilization: ).*/\10.94/" configs/run_main_v4.yaml
grep -n "^world\|lesion_conditions\|gpu_memory" configs/run_main_v4.yaml >> "$L"

say "7. main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/TOM2_DONE
