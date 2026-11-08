#!/usr/bin/env python3
"""Extract every first-round public post in the no-intervention discussion games (final wording) for manual labelling.

Writes paper/data/first_round_posts.txt (channel-related sentences only, games anonymised as G1..G18, outcomes not shown)
and paper/data/first_round_game_index.json. The labels and the summary are in paper/data/first_round_manual.json;
paper/data/first_round.json holds each game's final filings.
"""
import gzip, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
posts, finals = [], {}
for run in ["calib_v4ri", "calib_v4ri_med", "main_v4"]:
    for g in sorted((ROOT / "runs" / run / "games").iterdir()):
        if not g.name.endswith("__none") or "_discuss_" not in g.name:
            continue
        s = json.loads((g / "state.json").read_text()); seen = set()
        finals[g.name] = {cs: (a.get("filing") or {}).get("channel") for cs, a in s["agents"].items()}
        for m in s["channel"]:
            if m["round"] == 1 and m.get("to") is None and m["sender"] not in seen:
                seen.add(m["sender"]); posts.append((g.name, m["sender"], m["text"]))
for src in ["calibration", "workflow"]:
    for l in gzip.open(ROOT / f"results/swarm_replication/{src}/games/outcomes.jsonl.gz", "rt"):
        o = json.loads(l)
        if "_discuss_" in o["game_id"] and o["game_id"].endswith("__none"):
            finals[o["game_id"]] = {a: (v.get("filing") or {}).get("channel") for a, v in o["agents"].items()}
    seen = set()
    for l in gzip.open(ROOT / f"results/swarm_replication/{src}/games/none.events.jsonl.gz", "rt"):
        r = json.loads(l)
        if ("_discuss_" in r["game"] and r["game"].endswith("__none") and r["type"] == "tool" and r.get("name") == "post_message"
                and r.get("round") == 1 and (r["game"], r["agent"]) not in seen):
            seen.add((r["game"], r["agent"])); posts.append((r["game"], r["agent"], (r.get("args") or {}).get("text", "")))
games = sorted({p[0] for p in posts})
with open(ROOT / "paper/data/first_round_posts.txt", "w") as f:
    for gi, gname in enumerate(games):
        print(f"## G{gi + 1}", file=f)
        for name, agent, text in posts:
            if name == gname:
                t = re.sub(r"\s+", " ", text)
                sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", t) if re.search(r"channel [ei]\b|internal|external", x, re.I)]
                print(f"{agent}: " + (" | ".join(x[:150] for x in sents[:3]) if sents else f"(no channel mentioned) {t[:100]}"), file=f)
(ROOT / "paper/data/first_round_game_index.json").write_text(json.dumps({f"G{i + 1}": g for i, g in enumerate(games)}, indent=1))
(ROOT / "paper/data/first_round.json").write_text(json.dumps([{"game": g, "final": finals[g]} for g in games], indent=1))
print(len(posts), "posts in", len(games), "games")
