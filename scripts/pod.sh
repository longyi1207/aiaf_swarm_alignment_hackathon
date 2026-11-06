#!/usr/bin/env bash
# Run a command on the experiment pod: scripts/pod.sh 'nvidia-smi'
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
read -r IP PORT < <(python3 - "$HERE/../runs/pod.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); print(s["publicIp"], s["portMappings"]["22"])
PY
)
exec ssh -i "$HOME/.ssh/runpod_swarmtom" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20 \
  -o ServerAliveInterval=30 -o BatchMode=yes -p "$PORT" "root@$IP" "$@"
