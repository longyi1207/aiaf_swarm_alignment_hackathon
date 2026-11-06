#!/usr/bin/env bash
# After phase0_v2 finishes: score it and run the calibration gate.
cd /workspace/repo
until grep -qE "DONE|GAVE UP" /workspace/logs/phase0v2.log 2>/dev/null; do sleep 10; done
echo "$(date -u +%FT%TZ) phase0_v2 finished: $(grep -E 'DONE|GAVE UP' /workspace/logs/phase0v2.log | tail -1)" >> /workspace/logs/chain.log
/root/venv/bin/swarmtom score runs/phase0_v2 > /workspace/logs/phase0_v2_score.log 2>&1
/root/venv/bin/python scripts/phase0_gate.py runs/phase0_v2 --samples 10 > /workspace/logs/phase0_v2_gate.log 2>&1
echo "$(date -u +%FT%TZ) phase0_v2 scored + gate exit $?" >> /workspace/logs/chain.log
