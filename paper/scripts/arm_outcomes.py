#!/usr/bin/env python3
"""Per-arm filing outcomes and evidence discovery for both seven-arm game runs (for Figure 3).

Discovery = the agent's submitted review classified at least one of its own planted fabricated batches as
fabricated (the current scorer's definition). For the historical run the world paths recorded on the pod are
remapped to the local copy.

    python paper/scripts/arm_outcomes.py > paper/data/arm_outcomes.json
"""
import csv, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def historical():
    out = defaultdict(lambda: {"E": 0, "I": 0, "missing": 0, "discovered": 0, "agents": 0})
    for g in sorted((ROOT / "runs/main_v4/games").iterdir()):
        s = json.loads((g / "state.json").read_text())
        wd = ROOT / "runs/main_v4/worlds" / Path(s["world_dir"]).name
        gt = json.loads((wd / "ground_truth.json").read_text())
        planted = {a["callsign"]: a["batches"] for a in gt["agents"]}
        arm = s["lesion_tag"]
        for cs, a in s["agents"].items():
            o = out[arm]; o["agents"] += 1
            ch = (a.get("filing") or {}).get("channel")
            o["E" if ch == "E" else "I" if ch == "I" else "missing"] += 1
            o["discovered"] += any(e["classification"] == "F" and planted[cs].get(e["batch_id"]) == "F"
                                   for e in (a.get("review_log") or []))
    return out

def replication():
    out = defaultdict(lambda: {"E": 0, "I": 0, "missing": 0, "discovered": 0, "agents": 0})
    for r in csv.DictReader(open(ROOT / "results/swarm_replication/workflow/agents.csv")):
        o = out[r["lesion_tag"]]; o["agents"] += 1
        o["E" if r["filing"] == "E" else "I" if r["filing"] == "I" else "missing"] += 1
        o["discovered"] += int(r["discovered_own_f"])
    return out

print(json.dumps({"historical_seeds_201_202": historical(), "cache_off_seed_351": replication()}, indent=2))
