#!/usr/bin/env python3
"""Do auditors with more contract pay at stake report externally less often? Correlational check on the 180
no-intervention auditors under the final wording. Remaining contract value differs across auditors by world design.

    python paper/scripts/contract_value.py > paper/data/contract_value.json
"""
import gzip, json, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
agents = []  # (game, harm, communication, value, filing)
for run in ["calib_v4ri", "calib_v4ri_med", "main_v4"]:
    for g in sorted((ROOT / "runs" / run / "games").iterdir()):
        if not g.name.endswith("__none"):
            continue
        s = json.loads((g / "state.json").read_text())
        gt = json.loads((ROOT / "runs" / run / "worlds" / Path(s["world_dir"]).name / "ground_truth.json").read_text())
        val = {a["callsign"]: a["remaining_value_usd"] for a in gt["agents"]}
        spec = gt["spec"]
        for cs, a in s["agents"].items():
            agents.append((g.name, spec["harm"], spec["communication"], val[cs], (a.get("filing") or {}).get("channel")))
for src in ["calibration", "workflow"]:
    for l in gzip.open(ROOT / f"results/swarm_replication/{src}/games/outcomes.jsonl.gz", "rt"):
        o = json.loads(l)
        if not o["game_id"].endswith("__none"):
            continue
        harm = "high" if "_high_" in o["game_id"] else "medium" if "_medium_" in o["game_id"] else "low"
        comm = "discuss" if "_discuss_" in o["game_id"] else "isolated"
        for cs, a in o["agents"].items():
            v = o["outcome"]["per_agent"][cs]["contract_value_usd"]
            agents.append((o["game_id"], harm, comm, v, (a.get("filing") or {}).get("channel")))
E = [v for *_, v, f in agents if f == "E"]; I = [v for *_, v, f in agents if f == "I"]
# within mixed games: do external filers have less at stake than internal filers in the same game?
games = {}
for gname, h, c, v, f in agents:
    games.setdefault(gname, []).append((v, f))
less = more = tie = 0
for rows in games.values():
    e = [v for v, f in rows if f == "E"]; i = [v for v, f in rows if f == "I"]
    if e and i:
        d = st.fmean(e) - st.fmean(i)
        less += d < 0; more += d > 0; tie += d == 0
out = {"auditors": len(agents), "external": len(E), "internal": len(I),
       "mean_value_external": st.fmean(E), "mean_value_internal": st.fmean(I),
       "value_range": [min(v for *_, v, _ in agents), max(v for *_, v, _ in agents)],
       "mixed_games": less + more + tie, "external_filers_had_less_at_stake": less, "had_more": more, "tie": tie}
print(json.dumps(out, indent=1))
