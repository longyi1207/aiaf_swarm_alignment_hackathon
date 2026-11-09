#!/usr/bin/env python3
"""Per-arm outcomes of the steering games (Figure 4 bottom rows, section 4.3).

Reads the scored run directories (run `swarmtom score <run>` first) and writes paper/data/steering_games.json with
keys none, tom_up_c1, rand_tom_c1, emp_up, rand_emp: external (E), internal (I) and missing filings, auditors, and
how many identified at least one of their own fabricated batches. Arms that have not finished are omitted.

    .venv/bin/python paper/scripts/steering_games.py
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = {"runs/steer_games_none": {"none": "none"},
        "runs/steer_games": {"tom_up_c1": "tom_up_c1", "rand_tom_c1": "rand_tom_c1"},
        "runs/steer_games_emp": {"emp_up_c015": "emp_up", "rand_emp_c015": "rand_emp"}}

out, per_world = {}, defaultdict(dict)
for run, arms in RUNS.items():
    path = ROOT / run / "results/agents.csv"
    if not path.exists():
        continue
    rows = list(csv.DictReader(open(path)))
    games = {r["game_id"]: r for r in csv.DictReader(open(ROOT / run / "results/games.csv"))}
    for tag, key in arms.items():
        rs = [r for r in rows if r["lesion_tag"] == tag]
        if len(rs) < 40:          # an arm counts only when all 8 games (40 auditors) are scored
            continue
        out[key] = {"E": sum(r["filing"] == "E" for r in rs), "I": sum(r["filing"] == "I" for r in rs),
                    "missing": sum(r["filing"] not in ("E", "I") for r in rs), "agents": len(rs),
                    "discovered": sum(int(r["discovered_own_f"]) for r in rs),
                    "audits": sum(int(g["audit_opened"]) for g in games.values() if g["lesion_tag"] == tag)}
        for r in rs:
            per_world[key].setdefault(r["world_id"], []).append(int(r["filing"] == "E"))
out["external_per_world"] = {k: {w: sum(v) for w, v in sorted(ws.items())} for k, ws in per_world.items()}
(ROOT / "paper/data/steering_games.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: v for k, v in out.items() if k != "external_per_world"}, indent=1))
