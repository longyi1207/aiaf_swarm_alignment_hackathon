#!/usr/bin/env bash
# After phase0_v2 is scored: if the quantitative gate passes (accuracy >= 70%, E rate in [15%, 85%]), start the
# main run so the GPU does not sit idle; the qualitative check (real trade-offs in the reasoning) is done by hand
# right after, and the main run is stopped if it fails.
cd /workspace/repo
until grep -q "phase0_v2 scored + gate" /workspace/logs/chain.log; do sleep 10; done
pass=$(/root/venv/bin/python -c "import json;print(json.load(open('runs/phase0_v2/results/phase0_gate.json'))['gate_pass_quantitative'])" 2>/dev/null)
echo "$(date -u +%FT%TZ) phase0_v2 quantitative gate: $pass" >> /workspace/logs/chain.log
if [ "$pass" = "True" ]; then
  bash scripts/pod_vrun.sh main run configs/run_main_lite.yaml --python-network audit --tool-workers 64 >> /workspace/logs/chain.log 2>&1
  echo "$(date -u +%FT%TZ) main_lite started automatically (quantitative gate passed)" >> /workspace/logs/chain.log
fi
