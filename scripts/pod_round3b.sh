#!/usr/bin/env bash
# Round 3, option B (LY 17:13): main = none / emp / random / tom (tom2_L6, exploratory) / random_tom (rand2_L6),
# if tom2_L6 passes the agent probe; else empathy-only. Harm medium+high if the medium calibration passes, else
# low+high. Rules: docs/设计.md §8 (2026-11-07 17:15).
set -uo pipefail
cd /workspace/repo
export SWARMTOM_BIN=/root/vllm-venv/bin/swarmtom SWARMTOM_TOOL_PYTHON=/root/venv/bin/python VLLM_CACHE_ROOT=/root/.cache/vllm
export HF_HOME=/root/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
L=/workspace/logs/tom2_pipeline.log
say() { echo "$(date -u +%FT%TZ) $*" >> "$L"; }
stop() { say "STOP: $*"; echo "$*" > /workspace/logs/ROUND3_STOPPED; exit 1; }
PY=/root/venv/bin/python
MARK=/workspace/logs/CALIB_V4RI_MED_DONE

say "round 3b: waiting for the tom2_L6 agent probe and the medium-harm calibration"
while pgrep -f "[p]od_supervise.sh probe_tom2_L6 " > /dev/null; do sleep 15; done
sleep 5
[ -f runs/probe_tom2_L6/probe_check.json ] || $PY scripts/v4_probe_check.py runs/probe_tom2_L6 >> "$L" 2>&1
cat runs/probe_tom2_L6/probe_check.json >> "$L" 2>/dev/null
l6=$($PY -c "import json; p=json.load(open('runs/probe_tom2_L6/probe_check.json')); print('ok' if p.get('tom2_L6',{}).get('pass') else '')" 2>> "$L")
while [ ! -f "$MARK" ] && pgrep -f "[p]od_calib.sh configs/run_calib_v4ri_med" > /dev/null; do sleep 20; done

harm="[low, high]"
if [ -f runs/calib_v4ri_med/results/phase0_gate.json ]; then
  ok=$($PY - <<'PYEOF' 2>> "$L"
import json, sys
g = json.load(open("runs/calib_v4ri_med/results/phase0_gate.json"))
e, acc = g["filed_E_rate"], g["analysis_accuracy_mean"]
pb = next(iter((g.get("per_brief") or {}).values()), {})
op = pb.get("opened_personal", 0)
print(f"# medium harm: E {e} acc {acc} opened_personal {op} by cell {g.get('filed_E_by_harm_comm')}", file=sys.stderr)
print("ok" if 0.25 <= e <= 0.70 and acc >= 0.70 and op >= 0.5 else "")
PYEOF
)
  [ "$ok" = "ok" ] && harm="[medium, high]"
fi

if [ "$l6" = "ok" ]; then
  arms="none, emp, random, tom, random_tom"
  $PY - <<'PYEOF' >> "$L" 2>&1
import re, sys
from pathlib import Path
sys.path.insert(0, "src")
p = Path("configs/lesions.yaml"); t = p.read_text()
old = "  tom:\n    edits: []\n"
assert old in t, "tom block not found"
t = t.replace(old, "  # 方案 B（LY 2026-11-07）：探索性 ToM 组 = tom2_L6（没通过预设的截断标准）\n"
                   "  tom:\n    edits:\n      - file: tom_v2\n        axes: [tau2]\n        layer: 6\n", 1)
anchor = "  # --- Phase 0b 剂量阶梯"
add = ("  # 方案 B：ToM 组的随机对照（同层同强度）\n  random_tom:\n    edits:\n      - file: rand_dirs\n"
       "        axes: [rand_dir]\n        layer: 6\n\n")
assert anchor in t and "  random_tom:" not in t
t = t.replace(anchor, add + anchor, 1)
p.write_text(t)
from swarmtom.lesion.conditions import load_conditions
c, _ = load_conditions(p, Path("."))
print("lesions OK:", {k: [(e.layer, e.alpha) for e in c[k]][:3] for k in ("tom", "random_tom", "emp")})
PYEOF
  [ $? -eq 0 ] || stop "could not add the exploratory ToM arm to configs/lesions.yaml"
else
  arms="none, emp, random"
  say "tom2_L6 did not pass the agent probe: empathy-only main"
fi
say "main arms: [$arms]; harm: $harm"
sed -i -E "s/^  lesion_conditions: \[.*\]/  lesion_conditions: [$arms]/" configs/run_main_v4.yaml
sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+, monthly_pay_usd: 6000, award_usd: [0-9]+\}/world: {n_agents: 5, threshold: 3, brief: v4ri, monthly_pay_usd: 6000, award_usd: 300}/" configs/run_main_v4.yaml
sed -i -E "s/^(  gpu_memory_utilization: ).*/\10.94/" configs/run_main_v4.yaml
sed -i -E "s/^  harm: \[[a-z, ]+\]/  harm: $harm/" configs/run_main_v4.yaml
grep -n "^world\|harm:\|lesion_conditions\|seeds\|gpu_memory" configs/run_main_v4.yaml >> "$L"
[ -d runs/main_v4 ] && mv runs/main_v4 "runs/main_v4_aborted_$(date -u +%H%M)"
date -u +%FT%TZ > /workspace/logs/ROUND3_LESIONS_DONE

say "main_v4"
$PY scripts/pregen_worlds.py configs/run_main_v4.yaml >> "$L" 2>&1
bash scripts/pod_supervise.sh mainv4 run configs/run_main_v4.yaml --python-network audit --tool-workers 64 || stop "main_v4 failed"
/root/venv/bin/swarmtom score runs/main_v4 > /workspace/logs/main_v4_score.log 2>&1
$PY scripts/analyze_main.py runs/main_v4 > /workspace/logs/main_v4_analysis.log 2>&1
say "main_v4 done"
date -u +%FT%TZ > /workspace/logs/ROUND3_DONE
