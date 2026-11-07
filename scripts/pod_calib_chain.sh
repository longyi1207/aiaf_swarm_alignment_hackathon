#!/usr/bin/env bash
# calib_v3 -> score -> gate (per-brief selection rule) -> if a brief is selected: set it in run_main_lite.yaml and
# start the main run. If none is selected, stop (iterate on the wording; the main run never starts on a failed gate).
cd /workspace/repo
until grep -qE "DONE|GAVE UP" /workspace/logs/calibv3.log 2>/dev/null; do sleep 10; done
echo "$(date -u +%FT%TZ) calib_v3 finished: $(grep -E 'DONE|GAVE UP' /workspace/logs/calibv3.log | tail -1)" >> /workspace/logs/chain.log
/root/venv/bin/swarmtom score runs/calib_v3 > /workspace/logs/calib_v3_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/calib_v3 --samples 12 > /workspace/logs/calib_v3_gate.log 2>&1
pick=$(/root/venv/bin/python -c "import json;print(json.load(open('runs/calib_v3/results/phase0_gate.json')).get('selected_brief'))")
echo "$(date -u +%FT%TZ) calib_v3 selected brief: $pick" >> /workspace/logs/chain.log
if [ "$pick" != "None" ] && [ -n "$pick" ]; then
  sed -i -E "s/^world: \{n_agents: 5, threshold: 3, brief: [a-z0-9]+\}/world: {n_agents: 5, threshold: 3, brief: $pick}/" configs/run_main_lite.yaml
  grep -n "^world:" configs/run_main_lite.yaml >> /workspace/logs/chain.log
  bash scripts/pod_vrun.sh main run configs/run_main_lite.yaml --python-network audit --tool-workers 64 >> /workspace/logs/chain.log 2>&1
  echo "$(date -u +%FT%TZ) main_lite started with brief $pick" >> /workspace/logs/chain.log
fi
