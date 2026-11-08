# Clean replication after the prefix-cache fix

This runbook freezes the current seven-arm v4ri protocol and starts from new worlds,
transcripts and output directories. It does not claim that the existing interventions
are valid. The gates can reject them; a rejection is a result, not permission to relax
the criteria or silently remove arms.

The scripts prepare and execute work on an existing GPU host. They do not create a
RunPod instance, rent compute, upload results or change any remote repository.

## What changed

- Every arm present in scored data is analysed, including the three newer controls/arms.
- Direct matched-random comparisons accompany baseline comparisons. Matched worlds stay
  paired, and resampling/sign flips keep all related worlds and agents of a seed together.
- External, internal and missing filings have separate outcomes. Completion-conditioned
  choices are descriptive and are not causal effects or a mediation analysis.
- PRED-1 discovery is scored against correctly reported own F findings, not planted evidence.
- Only the first 16 analysis turns spent solely reading personal files are free. Subsequent
  reads use the ordinary step budget. This changes the harness and is frozen in these configs.
- `tom_emp` is the union of the actual ToM and empathy edits; `random_joint` is its matched
  union. Neither is included in this seven-arm replication.
- A manifest freezes effective config, source hashes, vector/edit definitions and task files.
  Legacy outputs without a manifest cannot be resumed. Runtime/package metadata and restart
  sessions are retained. vLLM seeds are derived from each request and prompt, not call order.
- Python filesystem access is restricted by the OS. macOS uses sandbox-exec; Linux requires
  Landlock ABI >= 3, with no Python-only fallback. Both normal and native outside-file reads
  are checked before games start. See the [kernel API documentation](https://docs.kernel.org/userspace-api/landlock.html).
  Network `audit` mode remains weaker than an OS network namespace; this runbook does not
  turn it into a hardened sandbox for adversarial code.

Historical pre-fix comparisons, dose selections and transcripts remain historical. Do not
copy `games/`, `state.json`, `generations.jsonl`, judgments or cached outputs into the new run.

## 1. Prepare the GPU environment

Use a CUDA Linux host compatible with vLLM 0.33.0 and the pinned model, with sufficient
memory for Qwen3.5-9B and the configured context. The old scripts used an H100. Start one
arm at a time; do not run these stages concurrently on the same GPU.

From the repository root, create a separate environment so installing vLLM cannot replace
the local development environment's torch dependency:

```bash
uv venv --python 3.11 .venv-replication
uv pip install --python .venv-replication/bin/python 'vllm==0.33.0' -e '.[model]' pytest matplotlib
export SWARMTOM_PYTHON="$PWD/.venv-replication/bin/python"
export SWARMTOM_TOOL_PYTHON="$SWARMTOM_PYTHON"
"$SWARMTOM_PYTHON" -m pytest -q
uv pip freeze --python "$SWARMTOM_PYTHON" > replication-environment.txt
```

The package set is also recorded in run metadata. Preserve the complete freeze file with
results; resume using the same environment. Commit the reviewed code before preparing the
run, or preserve the entire working tree corresponding to the recorded source hashes.

Preflight filesystem and network isolation on the actual GPU host:

```bash
"$SWARMTOM_PYTHON" - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from swarmtom.agent.sandbox import filesystem_selftest, network_selftest
with TemporaryDirectory() as directory:
    workspace = Path(directory) / 'workspace'
    workspace.mkdir()
    print(filesystem_selftest(workspace, 'audit'))
    print(network_selftest(workspace, 'audit'))
PY
```

Expected: `filesystem isolated`, and only blocked network attempts. If Linux rejects
Landlock (unsupported kernel, disabled LSM, or a container seccomp restriction), stop and
use a host/container configuration supporting it. Do not disable filesystem enforcement.
For OS-level network isolation choose `block` if the host permits `unshare -rn`, or
`container` only when the process actually runs in a network-disabled container.

Prefer the original vector-extraction model revision if it can be recovered. Otherwise
pin the current revision below and treat all intervention validation as new; the vector
files record a model name, not proof of an exact checkpoint match. Download once while
networking is available:

```bash
export MODEL_REVISION="$("$SWARMTOM_PYTHON" -c 'from huggingface_hub import HfApi; print(HfApi().model_info("Qwen/Qwen3.5-9B").sha)')"
"$SWARMTOM_PYTHON" - <<'PY'
import os
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3.5-9B', revision=os.environ['MODEL_REVISION'])
PY
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
```

The preparation script requires a full model commit SHA, not a moving branch name.
No model or GPU experiment was run merely by writing this plan.

## 2. Freeze a fresh plan

Choose a new tag. Reusing a prepared tag or an existing output directory is rejected.

```bash
export REPLICATION_TAG=clean_20261108_a
"$SWARMTOM_PYTHON" scripts/prepare_replication.py \
  --tag "$REPLICATION_TAG" \
  --model-revision "$MODEL_REVISION" \
  --python-network audit
```

Generated configs and `plan.json` live under `configs/replication/$REPLICATION_TAG/`;
outputs go to `runs/$REPLICATION_TAG/`. Inspect the configs before starting. All stages
use v4ri, five evidence holders, threshold three, $6,000 monthly pay, a $300 award,
medium/high harm, isolated/discuss, thinking enabled, and the same frozen intervention
registry. Fresh gated plans use `world.paired_contracts: true` to keep contract terms
fixed across harm. The November 8 descriptive replay retains historical contract draws.
Do not run the historical selection scripts: they rewrite that registry.

| Stage | Size | Seeds |
|---|---|---|
| Cache audit | 3 independent cache modes × 2 passes × 7 arms × 10 prompts | Greedy |
| Dose and reverse dissociation | 2,618 generations + 140 empathy judgments | Greedy, all 180 ToM / 144 control / 20 empathy / 30 capability items |
| Baseline calibration | 8 complete games, none only | 331–332 |
| Full-workflow validation | 28 complete games, all seven arms | 351 |
| Replication pilot | 56 complete games, all seven arms | 401–402 |

The seven arms are `none`, `emp`, `random`, `tom`, `random_tom`, `tom_all30`,
`random_all30`. This is a fixed-candidate replication. The dose items were used in prior
selection, so this is not an independent held-out confirmation of the selected directions.
The main pilot has only two seed blocks and cannot support strong significance claims.

## 3. Execute the gated plan

```bash
bash scripts/clean_replication.sh "$REPLICATION_TAG"
```

The launcher repeats filesystem/network preflight before loading any model, then uses
fresh cache workers and resumable manifested stages. Code/config/task/
vector changes or a changed runtime reject resumption. Within a stage it selects one arm
with `--arms`; it does not rewrite the full design between arms. An interrupted cache audit
requires a new tag; a completed passing audit may be reused only for its frozen inputs.

The gates are:

1. **Cache correctness:** greedy outputs must agree exactly between caching disabled,
   salted caching in forward arm order, and salted caching in reverse order, including a
   second pass through the same prompts. Any mismatch stops the plan. Investigate numerical
   differences, backend support and hooks; do not automatically loosen equality.
2. **Dose specificity:** target-task decline must have a paired 95% interval above zero
   against both baseline and the matched random direction. Preservation requires the
   upper interval for decline to be <=5 percentage points on non-target objective tasks,
   or <=0.5/10 on empathy for ToM lesions. Capability must retain >=90% of baseline;
   non-target-task truncation must be <=baseline+5 points. Empathy is tested on the new
   ToM tasks too, completing the reverse direction. These are stricter, newly declared
   validation criteria, not the historical preregistration.
3. **Calibration:** >=95% review/filing completion, >=70% classification accuracy,
   <=5% forced agents, no backend errors, and external reporting within [15%,85%].
   Inspect the full transcripts as well: aggregate variation could mask a ceiling in one
   harm/communication cell. This step does not authorize iterative prompt tuning.
4. **Full workflows:** the same completion/accuracy/failure criteria for every arm, all
   phases and full discussion rounds. This replaces the inadequate eight-tick probe.
5. **Main completeness:** every planned game and scored agent must exist, with no
   unexpected games. The workflow criteria are checked again before the final analysis.

Each stage writes `gate.json`, including failed checks. Any failure exits nonzero before
starting dependent work. Preserve all failed results. Redesigning an intervention or
changing a threshold requires a separate plan/tag and explicit documentation of the change.

## 4. Inspect and reproduce the final analysis

```bash
"$SWARMTOM_PYTHON" -m swarmtom.cli score "runs/$REPLICATION_TAG/main"
"$SWARMTOM_PYTHON" scripts/analyze_main.py "runs/$REPLICATION_TAG/main"
```

Read `results/analysis.md`, `analysis.json`, `agents.csv`, `games.csv`, and
`fig_matched_controls.png`. Primary specificity comparisons are `emp−random`,
`tom−random_tom`, and `tom_all30−random_all30`, with a declared Holm family. Baseline
comparisons have a separate Holm family. Communication and harm interactions are
exploratory. Report completion failures alongside all-agent external filing and
conditional choice rates; never interpret failed execution as a strategic internal choice.

CIs use seed-block bootstrap with matched worlds, and P values use paired seed sign flips.
With two seeds the P values are necessarily coarse; bootstrap intervals can also be
unstable. After the pilot passes, choose the sample size for a separate independent,
predeclared confirmation using more seeds. Do not keep adding seeds until significance.

Archive the entire tag directory, prepared configs/plan, environment freeze, model SHA,
source revision/tree, vector files, manifests, sessions, raw generations/judgments and game
transcripts. Frozen replay, mixed populations, a combined-arm experiment, hard non-social
reasoning controls and formal mediation remain separate research extensions.

## Replay the November 8 descriptive experiment

The [H100 report](../results/belief_replication/README.md) uses a separate, cache-disabled
protocol. This recipe recreates the settings on one CUDA host with a working tool sandbox.
Use the environment from section 1 and the fixed model revision below. The original run
placed the tool sandbox on a macOS controller and used SSH standard I/O for H100 inference.
The single-host recipe uses the same vLLM generation code. Kernel, batch size and GPU
differences can change individual greedy continuations.

```bash
set -eu
py=${SWARMTOM_PYTHON:-.venv-replication/bin/python}
revision=c202236235762e1c871ad0ccb60c8ee5ba337b9a
tag=h100_descriptive_repeat_01
c=configs/replication/$tag
r=runs/$tag
"$py" scripts/prepare_replication.py --tag "$tag" --model-revision "$revision" \
    --descriptive --python-network block

"$py" scripts/replicate_beliefs.py --revision "$revision" --cache off \
    --gpu-memory-utilization .38 --out "$r/beliefs"
"$py" scripts/describe_belief_pairs.py "$r/beliefs/items.csv"
"$py" scripts/extend_belief_budget.py "$r/beliefs/raw.jsonl" --revision "$revision" \
    --out "$r/extensions"
"$py" -m swarmtom.cli dose-gen "$c/dose.yaml"
"$py" -m swarmtom.cli dose-judge "$c/dose.yaml"
"$py" -m swarmtom.cli dose-report "$r/dose"

# Preserve failed scientific checks. Exceptions and missing gate reports stop the replay.
record_gate() {
    "$py" scripts/replication_gate.py "$1" "$2" || {
        "$py" -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["pass"] is False and d["failures"]; print(*d["failures"], sep="\n")' "$2/gate.json"
    }
}
record_gate dose "$r/dose"
for stage in calibration workflow main decision_phase; do
    "$py" -m swarmtom.cli run "$c/$stage.yaml" --serial-arms
    "$py" scripts/decision_incentives.py "$r/$stage"
    case "$stage" in
        main|decision_phase)
            record_gate complete "$r/$stage"
            "$py" scripts/analyze_main.py "$r/$stage" ;;
        *) record_gate "$stage" "$r/$stage" ;;
    esac
done
```

Each study writes to the fresh tag. A failed specificity or workflow gate is itself a
descriptive result and prevents a selective causal interpretation. The original gated
launcher above enforces its own stopping rules.

### Run the game tools on a separate controller

On the November 8 GPU host, the kernel lacked the filesystem isolation required for
agent Python tools. We ran those tools on macOS and sent generation requests to a
persistent H100 process over SSH. The worker needs the same repository revision,
vector files, pinned model snapshot and vLLM environment. The controller needs the
project dependencies for generating worlds and running the document tools. The
benchmark and judge commands in the preceding recipe run directly on the GPU.

For the **game stages**, run the descriptive preparation command on the controller with
a fresh tag, then set the three site-specific variables below. The SSH host value can
be an existing alias. Run this before launching a game.

```bash
export GAME_CONFIG_DIR="configs/replication/$tag"
export WORKER_HOST=gpu-host
export WORKER_CHECKOUT=/path/to/worker/checkout
export WORKER_PYTHON=/path/to/worker/venv/bin/python
"$py" - <<'PY'
import json, os, shlex
from pathlib import Path
import yaml
from swarmtom.run.config import RunConfig
from swarmtom.run.provenance import identity

directory = Path(os.environ["GAME_CONFIG_DIR"])
plan_path = directory / "plan.json"
plan = json.loads(plan_path.read_text())
if plan.get("mode") != "descriptive" or Path(plan["outputs"]).exists():
    raise SystemExit("Prepare a fresh descriptive game tag first.")
command = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "ServerAliveInterval=30", os.environ["WORKER_HOST"],
           "cd " + shlex.quote(os.environ["WORKER_CHECKOUT"]) + " && exec " +
           shlex.quote(os.environ["WORKER_PYTHON"]) + " -m swarmtom.llm.stdio"]
for stage in plan["games"]:
    path = directory / (stage + ".yaml")
    config = yaml.safe_load(path.read_text())
    config["backend"].update(type="vllm_stdio", command=command)
    path.write_text(yaml.safe_dump(config, sort_keys=False))
plan["main_identity"] = identity(RunConfig.load(directory / "main.yaml"), "game")
plan_path.write_text(json.dumps(plan, indent=2) + "\n")
PY
```

Run the four-stage game loop above on this controller. The worker checkout is its
working directory, so it resolves the same relative lesion registry and vectors.
Compare the two checkouts' inference and lesion source hashes before starting.
The controller checks filesystem and network isolation before invoking any agent tool.
