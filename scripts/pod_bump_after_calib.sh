#!/usr/bin/env bash
# When the v4r calibration finishes, give the running ToM v2 thinking-on screen the whole GPU: raise its vLLM memory
# cap to 0.90 and its chunk to 1024, then restart only the dose-gen process (its supervisor relaunches it; dose-gen
# resumes from generations.jsonl). No effect if the screen already finished. (2026-11-07, speed only.)
set -uo pipefail
cd /workspace/repo
L=/workspace/logs/tom2_pipeline.log
while [ ! -f /workspace/logs/CALIB_V4R_DONE ] && pgrep -f "[p]od_bootstrap_v4r" > /dev/null; do sleep 15; done
if pgrep -f "[b]in/swarmtom dose-gen configs/dose_check_tom2_screen_on" > /dev/null; then
  sed -i -E "s/^(  gpu_memory_utilization: ).*/\10.90/; s/^chunk: .*/chunk: 1024/" configs/dose_check_tom2_screen_on.yaml
  for p in $(pgrep -f "[b]in/swarmtom dose-gen configs/dose_check_tom2_screen_on"); do kill "$p"; done
  echo "$(date -u +%FT%TZ) calibration done: thinking-on screen restarted with the whole GPU (0.90, chunk 1024); resumes" >> "$L"
fi
