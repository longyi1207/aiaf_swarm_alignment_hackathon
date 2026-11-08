#!/usr/bin/env python3
"""Filing outcomes of every no-intervention auditor under the final scenario wording, by run and harm (Figure 2a).

    python paper/scripts/baseline_runs.py > paper/data/baseline_runs.json
"""
import csv, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRCS = {"calibration (seeds 101-102)": "runs/calib_v4ri/results/agents.csv",
        "calibration, medium harm (seeds 101-104)": "runs/calib_v4ri_med/results/agents.csv",
        "first run (seeds 201-202)": "results/main_v4/agents.csv",
        "cache-off calibration (seeds 331-332)": "results/swarm_replication/calibration/agents.csv",
        "replication (seed 351)": "results/swarm_replication/workflow/agents.csv"}
out = defaultdict(lambda: {"E": 0, "I": 0, "missing": 0, "agents": 0})
for src, path in SRCS.items():
    for r in csv.DictReader(open(ROOT / path)):
        if r["lesion_tag"] != "none" or r.get("brief", "v4ri") != "v4ri":
            continue
        o = out[(src, r["harm"])]; o["agents"] += 1
        o["E" if r["filing"] == "E" else "I" if r["filing"] == "I" else "missing"] += 1
rows = [{"run": s, "harm": h, **v} for (s, h), v in out.items()]
pooled = defaultdict(lambda: {"E": 0, "I": 0, "missing": 0, "agents": 0})
for r in rows:
    for k in ("E", "I", "missing", "agents"):
        pooled[r["harm"]][k] += r[k]
print(json.dumps({"by_run": rows, "pooled": pooled}, indent=1))
