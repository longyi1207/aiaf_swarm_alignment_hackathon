#!/usr/bin/env bash
# Run a prepared plan. Stops on failed gates; never provisions a GPU or changes intervention selection.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${1:?Usage: bash scripts/clean_replication.sh TAG}"
TAG=$1
[[ "$TAG" =~ ^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$ ]] || { echo "Invalid tag" >&2; exit 2; }
PYTHON=${SWARMTOM_PYTHON:-.venv/bin/python}
C="configs/replication/$TAG"
R="runs/$TAG"
[ -f "$C/plan.json" ] || { echo "Prepare the plan first" >&2; exit 2; }
"$PYTHON" - "$C/plan.json" "$C/main.yaml" <<'PYCODE'
import json,sys
from pathlib import Path
from swarmtom.run.config import RunConfig
from swarmtom.run.provenance import identity
plan=json.loads(Path(sys.argv[1]).read_text())
config=RunConfig.load(Path(sys.argv[2]))
if plan['main_identity'] != identity(config, 'game'):
    raise SystemExit('Prepared inputs changed; choose a fresh tag')
from tempfile import TemporaryDirectory
from swarmtom.agent.sandbox import filesystem_selftest, network_selftest
with TemporaryDirectory(prefix='swarmtom-preflight-') as directory:
    workspace=Path(directory)/'workspace'
    workspace.mkdir()
    print(filesystem_selftest(workspace, config.protocol.python_network))
    print(network_selftest(workspace, config.protocol.python_network))
PYCODE
# A completed audit is reusable only under its original config and current code; the stage manifests
# subsequently prevent changed code/config from resuming. Failed/partial audits require a fresh tag.
if [ ! -e "$R/cache/gate.json" ]; then
  "$PYTHON" scripts/check_prefix_cache.py --config "$C/main.yaml" --out "$R/cache"
fi
"$PYTHON" - "$R/cache/gate.json" "$C/main.yaml" <<'PY'
import hashlib,json,sys
from pathlib import Path
from swarmtom.run.provenance import runtime_versions
r=json.loads(Path(sys.argv[1]).read_text())
if not r['pass']:
    raise SystemExit('Cache audit failed; stop and investigate')
if r['packages'] != runtime_versions():
    raise SystemExit('Runtime changed after cache validation; use a fresh tag')
if r['config_sha256'] != hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest():
    raise SystemExit('Cache audit config changed')
PY
"$PYTHON" -m swarmtom.cli dose-gen "$C/dose.yaml"
"$PYTHON" -m swarmtom.cli dose-judge "$C/dose.yaml"
"$PYTHON" -m swarmtom.cli dose-report "$R/dose"
"$PYTHON" scripts/replication_gate.py dose "$R/dose"
"$PYTHON" -m swarmtom.cli run "$C/calibration.yaml"
"$PYTHON" scripts/replication_gate.py calibration "$R/calibration"
for arm in none emp random tom random_tom tom_all30 random_all30; do
  "$PYTHON" -m swarmtom.cli run "$C/workflow.yaml" --arms "$arm"
done
"$PYTHON" scripts/replication_gate.py workflow "$R/workflow"
for arm in none emp random tom random_tom tom_all30 random_all30; do
  "$PYTHON" -m swarmtom.cli run "$C/main.yaml" --arms "$arm"
done
"$PYTHON" scripts/replication_gate.py complete "$R/main"
"$PYTHON" scripts/analyze_main.py "$R/main"
echo "Replication complete: $R/main/results/analysis.md"
