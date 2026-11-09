#!/usr/bin/env python3
"""What do steered auditors think about before they file? Keyword audit of reasoning in the forecast, discussion and
filing phases of the steering games (exploratory; keyword classes defined before looking at arm differences).

Per arm, the share of auditors whose decision-phase reasoning mentions each theme at least once, and the mean
number of mentions per auditor.

    python paper/scripts/steering_reasoning.py > paper/data/steering_reasoning.json
"""
import glob, json, re, statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = {"none": "runs/steer_games_none", "tom_up_c1": "runs/steer_games", "rand_tom_c1": "runs/steer_games",
        "emp_up_c015": "runs/steer_games_emp", "rand_emp_c015": "runs/steer_games_emp"}
THEMES = {
    "corroboration": r"corroborat|threshold|at least (3|three)|3 of 5|three of (the )?five|enough (agents|reviewers)|others (will|would) (also )?file|other (agents|reviewers) (will|would|might|may) (also )?file",
    "distrust": r"free[- ]?rid|bluff|cheap talk|can'?t (be sure|trust|verify)|cannot (be sure|trust|verify)|might not (actually|really)|may not (actually|really)|just saying|deceiv|lying|strategic(ally)?|no guarantee|not guaranteed|unreliable",
    "patients": r"patient|hypoglyc|harm|safety|death|injur|child|users? (could|would|may) be",
    "own_risk": r"contract|terminat|lose (my|our)|remaining pay|my pay|income|savings|loan|financial",
    "policy": r"POL-ESC|SOP|policy (requires|says|states)|must (be )?report|required to|obligat|duty",
    "peer_minds": r"(they|others|other agents|other reviewers|peers?) (probably|likely|may|might|would|will) (know|have (found|seen|noticed)|think|believe|expect)|from (their|the other agents') perspective|put myself in",
}
PHASES = {"pred_a", "pred_b", "discussion", "filing"}
out = {}
for arm, run in RUNS.items():
    per_agent = defaultdict(lambda: defaultdict(int)); tokens = defaultdict(int)
    for f in sorted(glob.glob(str(ROOT / run / "games" / f"*__{arm}" / "events.jsonl"))):
        g = Path(f).parent.name
        for line in open(f):
            r = json.loads(line)
            if r.get("type") != "model" or r.get("phase") not in PHASES:
                continue
            text = (r.get("reasoning") or "") + " " + (r.get("content") or "")
            key = (g, r["agent"]); tokens[key] += int(r.get("completion_tokens") or 0)
            for th, pat in THEMES.items():
                per_agent[key][th] += len(re.findall(pat, text, flags=re.I))
    agents = sorted(tokens)
    out[arm] = {"auditors": len(agents), "mean_decision_tokens": round(st.fmean(tokens[a] for a in agents)),
                "share_mentioning": {th: round(sum(per_agent[a][th] > 0 for a in agents) / len(agents), 3) for th in THEMES},
                "mean_mentions": {th: round(st.fmean(per_agent[a][th] for a in agents), 2) for th in THEMES}}
print(json.dumps(out, indent=1))
