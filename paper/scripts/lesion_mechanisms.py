#!/usr/bin/env python3
"""Same reasoning-theme audit and peer forecasts for the lesion runs (first run, seeds 201-202; local transcripts).

    python paper/scripts/lesion_mechanisms.py > paper/data/lesion_mechanisms.json
"""
import glob, json, re, statistics as st, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper/scripts"))
src = (ROOT / "paper/scripts/steering_reasoning.py").read_text()
THEMES = eval(src.split("THEMES = ", 1)[1].split("\nPHASES")[0])
PHASES = {"pred_a", "pred_b", "discussion", "filing"}
out = {}
for arm in ["none", "emp", "random", "tom", "random_tom"]:
    per_agent = defaultdict(lambda: defaultdict(int)); tokens = defaultdict(int); fc = []
    for gdir in sorted(glob.glob(str(ROOT / "runs/main_v4/games" / f"*__{arm}"))):
        g = Path(gdir).name
        s = json.loads((Path(gdir) / "state.json").read_text())
        for a in s["agents"].values():
            v = (a.get("pred1") or {}).get("pred_a")
            if v:
                fc.append(st.fmean(float(x["p_files_channel_e"]) for x in v.values()))
        ev = Path(gdir) / "events.jsonl"
        if not ev.exists():
            continue
        for line in open(ev):
            r = json.loads(line)
            if r.get("type") != "model" or r.get("phase") not in PHASES:
                continue
            text = (r.get("reasoning") or "") + " " + (r.get("content") or "")
            key = (g, r["agent"]); tokens[key] += int(r.get("completion_tokens") or 0)
            for th, pat in THEMES.items():
                per_agent[key][th] += len(re.findall(pat, text, flags=re.I))
    agents = sorted(tokens)
    out[arm] = {"auditors_with_decision_text": len(agents), "pred_a_peer_files_e": round(st.fmean(fc), 3) if fc else None, "n_forecasts": len(fc),
                "mean_decision_tokens": round(st.fmean(tokens[a] for a in agents)) if agents else None,
                "per_1k_tokens": {th: round(1000 * sum(per_agent[a][th] for a in agents) / max(1, sum(tokens.values())), 2) for th in THEMES}}
print(json.dumps(out, indent=1))
