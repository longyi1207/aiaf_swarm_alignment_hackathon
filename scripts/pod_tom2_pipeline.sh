#!/usr/bin/env bash
# ToM v2 lesion search, then the v4 main run (2026-11-07, LY approved 13:59 PST). Rules: docs/设计.md §8.
#  0. wait for the v4r calibration (scripts/pod_bootstrap_v4r.sh) to free the GPU
#  1. extract τ2 (scripts/extract_tom_v2.py) and register the screening conditions (scripts/register_tom_v2.py)
#  2. screen, thinking off (configs/dose_check_tom2_screen.yaml) -> top 3 (scripts/select_tom2.py --stage screen)
#  3. confirm, thinking on (configs/dose_check_tom2_confirm.yaml) -> passers (--stage confirm)
#  4. agent probe (configs/run_probe_tom2.yaml, brief v4r) -> scripts/v4_probe_check.py
#  5. final lesions (--stage final): ToM v2 + matched empathy, or empathy-only if no ToM v2 lesion passes
#  6. calibration gate (runs/calib_v4r: accuracy >= 70%, E rate in [15%, 85%], >= 50% open personal/) -> main_v4
# A ToM stage with no passers skips to step 5 (empathy-only main), as pre-registered.
# TOM2_NO_WAIT=1 (LY 14:27: start ToM early): run steps 1–5 alongside the calibration, sharing the GPU (the
# calibration's vLLM is capped at 0.60; ToM's vLLM stages use 0.30 / the probe 0.35 while it still runs).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/TOM2_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }
PY=/root/venv/bin/python

calib_running() { [ ! -f /workspace/logs/CALIB_V4R_DONE ] && pgrep -f "[p]od_bootstrap_v4r" > /dev/null; }
wait_calib() {
  while calib_running; do sleep 20; done
  [ -f /workspace/logs/CALIB_V4R_DONE ] || say "WARNING: bootstrap ended without CALIB_V4R_DONE (calibration failed)"
}
gpu_mem() {  # set gpu_memory_utilization in a pipeline-owned config: shared GPU while the calibration runs
  local cfg=$1 shared=$2 alone=$3
  if calib_running; then sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$shared/" "$cfg"; else sed -i -E "s/^(  gpu_memory_utilization: ).*/\1$alone/" "$cfg"; fi
  grep -n "gpu_memory_utilization" "$cfg" | sed "s|^|$cfg: |" >> "$L"
}
if [ "${TOM2_NO_WAIT:-0}" = "1" ]; then
  say "tom2 pipeline start (alongside the v4r calibration)"
else
  say "tom2 pipeline start; waiting for the v4r calibration to finish"; wait_calib
fi

tom_ok=1
if [ ! -f assets/vectors/axes_tom_v2.pt ]; then
  say "1. extract tau2"
  $PY scripts/extract_tom_v2.py > /workspace/logs/tom2_extract.log 2>&1 || stop "extraction failed"
fi
$PY scripts/register_tom_v2.py >> "$L" 2>&1 || stop "registering the ToM v2 conditions failed"
grep -E "best_layer|sha256" runs/tom_v2_extract/stats.json >> "$L"

say "2. screen (thinking off)"
gpu_mem configs/dose_check_tom2_screen.yaml 0.30 0.90
sup dose_tom2_screen dose-gen configs/dose_check_tom2_screen.yaml || stop "screen generation failed"
$SWARMTOM_BIN dose-report runs/dose_check_tom2_screen > /workspace/logs/dose_tom2_screen_report.log 2>&1
$PY scripts/select_tom2.py --stage screen >> "$L" 2>&1; rc=$?
[ $rc -eq 0 ] || { [ $rc -eq 2 ] && { say "screen: no ToM v2 candidate passes"; tom_ok=0; } || stop "screen selection crashed"; }

if [ $tom_ok -eq 1 ]; then
  say "3. confirm (thinking on)"
  grep -n "^conditions" configs/dose_check_tom2_confirm.yaml >> "$L"
  gpu_mem configs/dose_check_tom2_confirm.yaml 0.30 0.90
  sup dose_tom2_confirm dose-gen configs/dose_check_tom2_confirm.yaml || stop "confirm generation failed"
  sup dose_tom2_confirm_judge dose-judge configs/dose_check_tom2_confirm.yaml || stop "confirm judging failed"
  $SWARMTOM_BIN dose-report runs/dose_check_tom2_confirm > /workspace/logs/dose_tom2_confirm_report.log 2>&1
  $PY scripts/select_tom2.py --stage confirm >> "$L" 2>&1; rc=$?
  [ $rc -eq 0 ] || { [ $rc -eq 2 ] && { say "confirm: no ToM v2 candidate passes"; tom_ok=0; } || stop "confirm selection crashed"; }
fi

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

say "6. calibration gate (runs/calib_v4r): waiting for it to finish"
wait_calib
[ -f runs/calib_v4r/results/phase0_gate.json ] || stop "lesions chosen; no calibration result (runs/calib_v4r)"
pick=$($PY - <<'PYEOF' 2>> "$L"
import json, sys
g = json.load(open("runs/calib_v4r/results/phase0_gate.json"))
v = (g.get("per_brief") or {}).get("v4r+r300")
print(f"# v4r+r300: {v}", file=sys.stderr)
if v and v["accuracy"] >= 0.70 and 0.15 <= v["filed_E_rate"] <= 0.85 and v.get("opened_personal", 0) >= 0.5:
    print("ok")
PYEOF
)
[ "$pick" = "ok" ] || stop "lesions chosen (runs/dose_check_tom2_confirm/decision.json); v4r calibration did not pass"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: v4r, monthly_pay_usd: 6000, award_usd: 300}/" configs/run_main_v4.yaml
grep -n "^world\|lesion_conditions" configs/run_main_v4.yaml >> "$L"

say "7. main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/TOM2_DONE
