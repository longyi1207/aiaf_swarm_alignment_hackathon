#!/usr/bin/env bash
# v4b (2026-11-07, LY: find ToM / empathy lesions that hit the target but not capability or tool use), then the
# v4 main run. Rules: docs/设计.md §8 (written before the data).
#  0. wait for the v4 baseline calibration; pick the award variant (award first if its E rate is in [15%, 85%],
#     else no award, else v4s; else stop)
#  1. dose_check_v4b (thinking on, budget 2048): candidates that bite with cut-off <= unlesioned + 5 points
#  2. probe_v4b: those candidates in every phase, first 8 ticks; agent capability check
#  3. select (both -> 5 arms; ToM only -> none/tom/random; empathy only -> none/emp/random; neither -> stop)
#  4. main_v4 -> score -> analyze -> V4B_DONE
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/v4b_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/V4B_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }
PY=/root/venv/bin/python

say "v4b start; waiting for the v4 calibration"
until [ -f /workspace/logs/V4_CALIB_ONLY_DONE ]; do sleep 20; done
pick_award() {
  /root/venv/bin/swarmtom score "$1" > /dev/null 2>&1
  $PY - "$1" <<'PYEOF'
import csv, statistics as st, sys
rows = list(csv.DictReader(open(sys.argv[1] + "/results/agents.csv")))
by = {}
for r in rows:
    by.setdefault(int(float(r.get("award_usd_level") or 0)), []).append(int(r["filed_e"]))
acc = st.fmean(float(r["classification_accuracy"]) for r in rows)
rates = {k: round(st.fmean(v), 3) for k, v in by.items()}
print("# rates", rates, "accuracy", round(acc, 3), file=sys.stderr)
for k in sorted(rates, reverse=True):
    if acc >= 0.70 and 0.15 <= rates[k] <= 0.85:
        print(k); break
PYEOF
}
award=$(pick_award runs/calib_v4 2>> "$L"); brief=v4
if [ -z "$award" ]; then
  say "calib_v4: no variant in range -> calib_v4s"
  sed -e 's/^run_id: calib_v4/run_id: calib_v4s/' -e 's/^  briefs: \[v4\]/  briefs: [v4s]/' configs/run_calib_v4.yaml > configs/run_calib_v4s.yaml
  $PY scripts/pregen_worlds.py configs/run_calib_v4s.yaml >> "$L" 2>&1
  sup calibv4s run configs/run_calib_v4s.yaml --python-network audit --tool-workers 64 || stop "calib_v4s failed"
  award=$(pick_award runs/calib_v4s 2>> "$L"); brief=v4s
  [ -n "$award" ] || stop "calibration: no v4/v4s variant has a baseline E rate in [15%, 85%]"
fi
say "calibration picked brief=$brief award=$award"

say "1. dose_check_v4b"
sup dose_v4b dose-gen configs/dose_check_v4b.yaml || stop "dose_check_v4b generation failed"
sup dose_v4b_judge dose-judge configs/dose_check_v4b.yaml || stop "dose_check_v4b judging failed"
$SWARMTOM_BIN dose-report runs/dose_check_v4b > /workspace/logs/dose_v4b_report.log 2>&1
cands=$($PY - <<'PYEOF'
import json
rep = json.load(open("runs/dose_check_v4b/report.json"))
rows = {r["condition"]: r for r in rep["table"] if r["thinking"]}
base = rows["none"]["cut_off_rate"]
def bites(r, t):
    d, cap = r.get(t), r.get("capability")
    cap_ok = cap is None or cap.get("base", 0) == 0 or cap["value"] >= 0.9 * cap["base"]
    return bool(d and d["ci"][0] > 0 and cap_ok and r["cut_off_rate"] <= base + 0.05)
c = [k for k in rows if k.startswith("tom") and "emp" not in k and bites(rows[k], "tom")]
c += [k for k in rows if k.startswith("emp") and bites(rows[k], "empathy")]
print(" ".join(c))
PYEOF
)
say "dose_check_v4b: candidates that bite = [$cands]"
[ -n "$cands" ] || stop "dose_check_v4b: no ToM or empathy candidate bites within the cut-off margin"

say "2. probe_v4b"
list=$(echo "none $cands" | sed 's/ /, /g')
sed -e 's/^run_id: probe_v4/run_id: probe_v4b/' -e "s/^  lesion_conditions: \[.*/  lesion_conditions: [$list]/" -e '/^                      emp_sae1, emp_sae5/d' configs/run_probe_v4.yaml > configs/run_probe_v4b.yaml
grep -n "run_id\|lesion_conditions" configs/run_probe_v4b.yaml >> "$L"
$PY scripts/pregen_worlds.py configs/run_probe_v4b.yaml >> "$L" 2>&1
sup probe_v4b run configs/run_probe_v4b.yaml --python-network audit --tool-workers 64 --max-ticks 8 || stop "probe_v4b failed"
$PY scripts/v4_probe_check.py runs/probe_v4b >> "$L" 2>&1

say "3. select"
$PY scripts/select_v4_lesions.py --report runs/dose_check_v4b/report.json --probe runs/probe_v4b/probe_check.json --cutoff-margin 0.05 >> "$L" 2>&1
[ $? -eq 0 ] || stop "v4b selection: no candidate passes both checks"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: $brief, monthly_pay_usd: 6000, award_usd: $award}/" configs/run_main_v4.yaml
grep -n "^world\|lesion_conditions" configs/run_main_v4.yaml >> "$L"

say "4. main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/V4B_DONE
