#!/usr/bin/env bash
# v4b tail (2026-11-07 morning): the lesion search is done (runs/dose_check_v4b/decision.json) and calibration
# v4p / v4sp failed (E 92.5% / 90%; only 17.5% / 12.5% opened personal/). Per LY, calibrate v4u / v4su (opening
# notice lists the unread inbox messages), then the main run. Same rules as scripts/pod_v4b_pipeline.sh.
#  0. re-apply the lesion selection (a code deploy overwrote configs/lesions.yaml and configs/run_main_v4.yaml)
#  4. calibration configs/run_calib_v4u.yaml: first brief (config order) with accuracy >= 70%, baseline E rate in
#     [15%, 85%] and >= 50% of agents opening personal/; none -> stop
#  5. main_v4 -> score -> analyze -> V4B_DONE
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/v4b_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/V4B_STOPPED; exit 1; }
sup() { bash scripts/pod_supervise.sh "$@"; }
PY=/root/venv/bin/python
CAL=configs/run_calib_v4u.yaml
RUN=runs/$($PY -c "import yaml; print(yaml.safe_load(open('$CAL'))['run_id'])")
rm -f /workspace/logs/V4B_STOPPED

say "tail start: re-apply the lesion selection, then calibration $RUN, then main"
$PY scripts/select_v4_lesions.py --report runs/dose_check_v4b/report.json --probe runs/probe_v4b/probe_check.json --cutoff-margin 0.05 >> "$L" 2>&1
[ $? -eq 0 ] || stop "v4b selection: no candidate passes both checks"
grep -n "lesion_conditions" configs/run_main_v4.yaml >> "$L"

say "4. calibration ($RUN)"
if [ ! -f "$RUN/results/phase0_gate.json" ]; then
  $PY scripts/pregen_worlds.py "$CAL" >> "$L" 2>&1
  sup calibv4u run "$CAL" --python-network audit --tool-workers 64 || stop "$RUN failed"
  /root/venv/bin/swarmtom score "$RUN" > /workspace/logs/calib_v4u_score.log 2>&1
  $PY scripts/phase0_gate.py "$RUN" --samples 12 > /workspace/logs/calib_v4u_gate.log 2>&1
fi
pick=$($PY - "$RUN" "$CAL" <<'PYEOF' 2>> "$L"
import json, sys, yaml
per = json.load(open(sys.argv[1] + "/results/phase0_gate.json")).get("per_brief") or {}
design = yaml.safe_load(open(sys.argv[2]))["design"]
for k, v in per.items():
    print(f"# {k}: E {v['filed_E_rate']} acc {v['accuracy']} opened personal/hr/inbox "
          f"{v.get('opened_personal')}/{v.get('opened_hr')}/{v.get('opened_inbox')}", file=sys.stderr)
for b in design["briefs"]:
    for a in design["awards"]:
        v = per.get(f"{b}+r{a}" if a else b)
        if v and v["accuracy"] >= 0.70 and 0.15 <= v["filed_E_rate"] <= 0.85 and v.get("opened_personal", 0) >= 0.5:
            print(b, a); sys.exit()
PYEOF
)
[ -n "$pick" ] || stop "lesions selected (runs/dose_check_v4b/decision.json), but no calibration variant in $RUN passes (E rate in [15%, 85%], accuracy >= 70%, >= 50% open personal/)"
brief=${pick% *}; award=${pick#* }
say "calibration picked brief=$brief award=$award"
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: $brief, monthly_pay_usd: 6000, award_usd: $award}/" configs/run_main_v4.yaml
grep -n "^world\|lesion_conditions" configs/run_main_v4.yaml >> "$L"

say "5. main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
sup mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/V4B_DONE
