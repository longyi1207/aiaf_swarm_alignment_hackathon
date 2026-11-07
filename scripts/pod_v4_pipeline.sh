#!/usr/bin/env bash
# Overnight v4 pipeline (2026-11-06 night). Every decision follows the rule written in docs/设计.md §8 beforehand.
#  0. wait for main_lite (v3) to finish; score it
#  1. dose_check_v4 (thinking on): gen -> judge -> report
#  2. probe_v4: candidate lesions in every phase, first 8 ticks; capability check
#  3. select_v4_lesions.py -> lesions.yaml main block + run_main_v4 arms (exit 2 = no usable empathy lesion -> stop)
#  4. calib_v4 (unlesioned, thinking on, award 0 vs $300): award variant if its E rate is in [15%, 85%], else the
#     no-award variant if in range, else calib_v4s (stronger self-description) with the same rule, else stop
#  5. main_v4 -> score -> analyze;  writes /workspace/logs/V4_PIPELINE_DONE (or ..._STOPPED with the reason)
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/v4_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/V4_PIPELINE_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }

say "pipeline start; waiting for main_lite"
until grep -qE "DONE|GAVE UP" /workspace/logs/main.log 2>/dev/null; do sleep 20; done
say "main_lite: $(grep -E 'DONE|GAVE UP' /workspace/logs/main.log | tail -1)"
/root/venv/bin/swarmtom score runs/main_lite > /workspace/logs/main_lite_score.log 2>&1
/root/venv/bin/python scripts/analyze_main.py runs/main_lite > /workspace/logs/main_lite_analysis.log 2>&1
say "main_lite scored + analyzed"

say "1. dose_check_v4"
sup dose_v4 dose-gen configs/dose_check_v4.yaml || stop "dose_check_v4 generation failed"
sup dose_v4_judge dose-judge configs/dose_check_v4.yaml || stop "dose_check_v4 judging failed"
$SWARMTOM_BIN dose-report runs/dose_check_v4 > /workspace/logs/dose_v4_report.log 2>&1
say "dose_check_v4 report: $(tail -1 /workspace/logs/dose_v4_report.log)"

say "2. probe_v4"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_probe_v4.yaml >> "$L" 2>&1
sup probe_v4 run configs/run_probe_v4.yaml --python-network audit --tool-workers 64 --max-ticks 8 || stop "probe failed"
/root/venv/bin/python scripts/v4_probe_check.py runs/probe_v4 >> "$L" 2>&1

say "3. select lesions"
/root/venv/bin/python scripts/select_v4_lesions.py >> "$L" 2>&1
rc=$?
[ $rc -eq 0 ] || stop "lesion selection: no usable empathy lesion (rc=$rc)"

pick_award() {  # $1 = run dir; prints the chosen variant (award level) or nothing
  /root/venv/bin/swarmtom score "$1" > /dev/null 2>&1
  /root/venv/bin/python - "$1" <<'PY'
import csv, statistics as st, sys
rows = list(csv.DictReader(open(sys.argv[1] + "/results/agents.csv")))
by = {}
for r in rows:
    by.setdefault(int(float(r.get("award_usd_level") or 0)), []).append(int(r["filed_e"]))
acc = st.fmean(float(r["classification_accuracy"]) for r in rows)
rates = {k: st.fmean(v) for k, v in by.items()}
print("# rates", rates, "accuracy", round(acc, 3), file=sys.stderr)
for k in sorted(rates, reverse=True):  # award first (LY's design), then no award
    if acc >= 0.70 and 0.15 <= rates[k] <= 0.85:
        print(k); break
PY
}

say "4. calib_v4"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_calib_v4.yaml >> "$L" 2>&1
sup calibv4 run configs/run_calib_v4.yaml --python-network audit --tool-workers 64 || stop "calib_v4 failed"
award=$(pick_award runs/calib_v4 2>> "$L"); brief=v4
if [ -z "$award" ]; then
  say "calib_v4: no variant in range -> calib_v4s (stronger self-description)"
  sed -e 's/^run_id: calib_v4/run_id: calib_v4s/' -e 's/^  briefs: \[v4\]/  briefs: [v4s]/' configs/run_calib_v4.yaml > configs/run_calib_v4s.yaml
  /root/venv/bin/python scripts/pregen_worlds.py configs/run_calib_v4s.yaml >> "$L" 2>&1
  sup calibv4s run configs/run_calib_v4s.yaml --python-network audit --tool-workers 64 || stop "calib_v4s failed"
  award=$(pick_award runs/calib_v4s 2>> "$L"); brief=v4s
  [ -n "$award" ] || stop "calibration: no v4/v4s variant has a baseline E rate in [15%, 85%]"
fi
say "calibration picked brief=$brief award=$award"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: $brief, monthly_pay_usd: 6000, award_usd: $award}/" configs/run_main_v4.yaml
grep -n "^world\|lesion_conditions" configs/run_main_v4.yaml >> "$L"

say "5. main_v4"
/root/venv/bin/python scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
/root/venv/bin/python scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/V4_PIPELINE_DONE
