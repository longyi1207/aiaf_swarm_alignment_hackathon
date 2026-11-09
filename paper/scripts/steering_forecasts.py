#!/usr/bin/env python3
"""Peer forecasts (PRED-1) in the steering games: does steering change what auditors expect their peers to do?

For each arm: mean forecast that a peer found fabrication and that a peer will report externally, before discussion
(pred_a, every game) and after it (pred_b, discussion games); and, in isolated games, the mean forecast of auditors who
then reported externally vs internally.

    python paper/scripts/steering_forecasts.py > paper/data/steering_forecasts.json
"""
import glob, json, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = {"none": "runs/steer_games_none", "tom_up_c1": "runs/steer_games", "rand_tom_c1": "runs/steer_games",
        "emp_up_c015": "runs/steer_games_emp", "rand_emp_c015": "runs/steer_games_emp"}
out = {}
for arm, run in RUNS.items():
    acc = defaultdict(list); per_world = defaultdict(list); by_choice = defaultdict(list)
    for f in sorted(glob.glob(str(ROOT / run / "games" / f"*__{arm}" / "state.json"))):
        s = json.loads(Path(f).read_text())
        world = Path(f).parent.name.split("__")[0]; iso = "_isolated_" in world
        for a in s["agents"].values():
            p = a.get("pred1") or {}
            for phase in ("pred_a", "pred_b"):
                v = p.get(phase)
                if not v:
                    continue
                e = st.fmean(float(x["p_files_channel_e"]) for x in v.values())
                fnd = st.fmean(float(x["p_found_category_f"]) for x in v.values())
                acc[f"{phase}_files_e"].append(e); acc[f"{phase}_found_f"].append(fnd)
                if phase == "pred_a":
                    per_world[world].append(e)
                    if iso:
                        by_choice[(a.get("filing") or {}).get("channel") or "none"].append(e)
    out[arm] = {k: round(st.fmean(v), 3) for k, v in acc.items()} | {"n_pred_a": len(acc["pred_a_files_e"])}
    out[arm]["isolated_pred_a_files_e_by_choice"] = {k: [round(st.fmean(v), 3), len(v)] for k, v in by_choice.items()}
    out[arm]["pred_a_files_e_per_world"] = {w: round(st.fmean(v), 3) for w, v in sorted(per_world.items())}
print(json.dumps(out, indent=1))
