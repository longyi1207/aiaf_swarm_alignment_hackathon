#!/usr/bin/env python3
"""External-reporting rate of each no-intervention calibration version with reasoning enabled (for the baseline figure).

    python paper/scripts/baseline_calibration.py > paper/data/baseline_calibration.json
"""
import csv, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = defaultdict(lambda: [0, 0])
for run in ["calib_v4", "calib_v4p", "calib_v4u", "calib_v4r", "calib_v4ri", "calib_v4ri_med"]:
    for r in csv.DictReader(open(ROOT / "runs" / run / "results/agents.csv")):
        key = (r["brief"], r["award_usd_level"], r["harm"] if r["brief"] == "v4ri" else "all")
        rows[key][0] += int(r["filed_e"]); rows[key][1] += 1
out = [{"brief": b, "award_usd": a, "harm": h, "external": e, "agents": n, "rate": e / n} for (b, a, h), (e, n) in sorted(rows.items())]
print(json.dumps(out, indent=1))
