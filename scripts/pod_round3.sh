#!/usr/bin/env bash
# Round 3 (2026-11-07 16:30, docs/设计.md §8): ToM v2 re-test at a 4096 thinking budget, medium-harm calibration
# alongside it, then the main experiment (v4ri; ToM arms only if a ToM v2 lesion passes; harm medium+high if the
# medium calibration passes, else low+high).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
export TOM2_CONFIRM_RUN=dose_check_tom2_b4096
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/ROUND3_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }
PY=/root/venv/bin/python
MARK=/workspace/logs/CALIB_V4RI_MED_DONE
calib_running() { [ ! -f "$MARK" ] && pgrep -f "[p]od_calib.sh configs/run_calib_v4ri_med" > /dev/null; }
gpu_mem() { local cfg=$1 shared=$2 alone=$3
  if calib_running; then sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$shared/" "$cfg"; else sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$alone/" "$cfg"; fi
  grep -n "gpu_memory_utilization" "$cfg" | sed "s|^|$cfg: |" >> "$L"; }

say "round 3 start: medium-harm calibration + ToM v2 re-test at budget 4096"
[ -d runs/main_v4 ] && mv runs/main_v4 "runs/main_v4_aborted_$(date -u +%H%M)"
(nohup setsid bash scripts/pod_calib.sh configs/run_calib_v4ri_med.yaml calibv4rimed CALIB_V4RI_MED_DONE > /dev/null 2>&1 < /dev/null &)
sleep 60
gpu_mem configs/dose_check_tom2_b4096.yaml 0.40 0.90
sup dose_tom2_b4096 dose-gen configs/dose_check_tom2_b4096.yaml || stop "ToM re-test generation failed"
gpu_mem configs/dose_check_tom2_b4096.yaml 0.40 0.90
sup dose_tom2_b4096_judge dose-judge configs/dose_check_tom2_b4096.yaml || stop "ToM re-test judging failed"
$SWARMTOM_BIN dose-report runs/dose_check_tom2_b4096 > /workspace/logs/dose_tom2_b4096_report.log 2>&1
tom_ok=1
$PY scripts/select_tom2.py --stage confirm >> "$L" 2>&1; rc=$?
[ $rc -eq 0 ] || { [ $rc -eq 2 ] && { say "budget 4096: no ToM v2 candidate passes"; tom_ok=0; } || stop "selection crashed"; }
rm -f runs/probe_tom2/probe_check.json
if [ $tom_ok -eq 1 ]; then
  say "agent probe"
  sed -i -E "s/brief: v4r,/brief: v4ri,/" configs/run_probe_tom2.yaml
  grep -n "run_id\|brief\|lesion_conditions" configs/run_probe_tom2.yaml >> "$L"
  gpu_mem configs/run_probe_tom2.yaml 0.35 0.94
  $PY scripts/pregen_worlds.py configs/run_probe_tom2.yaml >> "$L" 2>&1
  sup probe_tom2 run configs/run_probe_tom2.yaml --python-network audit --tool-workers 64 --max-ticks 8 || stop "probe failed"
  $PY scripts/v4_probe_check.py runs/probe_tom2 >> "$L" 2>&1
fi
say "final lesions"
$PY scripts/select_tom2.py --stage final >> "$L" 2>&1 || stop "final selection crashed"
date -u +%FT%TZ > /workspace/logs/ROUND3_LESIONS_DONE

say "waiting for the medium-harm calibration"
while calib_running; do sleep 20; done
harm="[low, high]"
if [ -f runs/calib_v4ri_med/results/phase0_gate.json ]; then
  ok=$($PY - <<'PYEOF' 2>> "$L"
import json, sys
g = json.load(open("runs/calib_v4ri_med/results/phase0_gate.json"))
e, acc = g["filed_E_rate"], g["analysis_accuracy_mean"]
pb = next(iter((g.get("per_brief") or {}).values()), {})
op = pb.get("opened_personal", 0)
print(f"# medium harm: E {e} acc {acc} opened_personal {op}", file=sys.stderr)
print("ok" if 0.25 <= e <= 0.70 and acc >= 0.70 and op >= 0.5 else "")
PYEOF
)
  [ "$ok" = "ok" ] && harm="[medium, high]"
fi
say "main harm levels: $harm"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: v4ri, monthly_pay_usd: 6000, award_usd: 300}/" configs/run_main_v4.yaml
sed -i -E "s/^(  gpu_memory_utilization: ).*/\10.94/" configs/run_main_v4.yaml
sed -i -E "s/^  harm: \[[a-z, ]+\]/  harm: $harm/" configs/run_main_v4.yaml
grep -n "^world\|harm:\|lesion_conditions\|seeds\|gpu_memory" configs/run_main_v4.yaml >> "$L"

say "main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/ROUND3_DONE
