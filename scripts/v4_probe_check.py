#!/usr/bin/env python3
"""Agent-capability check for v4 lesion candidates (run_probe_v4.yaml: lesions in every phase, first ticks of the
analysis phase, thinking on). Per arm vs the unlesioned arm:
  tool-error rate (tool results starting with "Error"/"Not executed") <= none + 0.10
  unknown-tool calls (names not offered by the platform)               <= 2% of tool calls
  frame-break turns ("fictional", "unable to complete", ...)           <= 2% of model turns
  replies cut off at the token cap (completion_tokens >= max_new_tokens) <= 10% of model turns
  (fixed 2026-11-07: "no </think>" is wrong for multi-turn agent output, where later turns often do not think)
Writes runs/probe_v4/probe_check.json.   python scripts/v4_probe_check.py runs/probe_v4
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

FRAME = re.compile(r"fictional|unable to complete|cannot complete|can't complete|not able to complete|role-?play", re.I)
CAP = 4096  # run_probe_v4.yaml max_new_tokens
KNOWN = {"list_files", "read_document", "read_table", "run_python", "submit_review_log", "submit_pred1",
         "post_message", "send_dm", "end_turn", "submit_filing"}


def main() -> int:
    run = Path(sys.argv[1])
    m = defaultdict(lambda: defaultdict(int))
    for gdir in sorted((run / "games").iterdir()):
        arm = gdir.name.split("__")[1]
        for line in open(gdir / "events.jsonl"):
            e = json.loads(line)
            if e["type"] == "model":
                m[arm]["turns"] += 1
                text = (e.get("content") or "") + (e.get("reasoning") or "")
                m[arm]["frame"] += bool(FRAME.search(text))
                m[arm]["cutoff"] += int(e.get("completion_tokens", 0) >= CAP)
                m[arm]["no_think_close"] += "</think>" not in (e.get("raw") or "")
                for c in e.get("tool_calls", []):
                    m[arm]["calls"] += 1
                    m[arm]["unknown"] += c["name"] not in KNOWN
            elif e["type"] == "tool":
                m[arm]["results"] += 1
                m[arm]["errors"] += str(e.get("result", "")).startswith(("Error", "Not executed"))
            elif e["type"] == "backend_error":
                m[arm]["backend_errors"] += 1
    rates = {}
    for arm, d in m.items():
        rates[arm] = {"turns": d["turns"], "calls": d["calls"],
                      "tool_error_rate": d["errors"] / max(1, d["results"]),
                      "unknown_tool_rate": d["unknown"] / max(1, d["calls"]),
                      "frame_break_rate": d["frame"] / max(1, d["turns"]),
                      "cutoff_rate": d["cutoff"] / max(1, d["turns"]),
                      "no_think_close_rate": d["no_think_close"] / max(1, d["turns"]),
                      "backend_errors": d["backend_errors"]}
    base = rates["none"]["tool_error_rate"]
    for arm, r in rates.items():
        r["pass"] = (r["tool_error_rate"] <= base + 0.10 and r["unknown_tool_rate"] <= 0.02
                     and r["frame_break_rate"] <= 0.02 and r["cutoff_rate"] <= 0.10)
    (run / "probe_check.json").write_text(json.dumps(rates, indent=2))
    for arm, r in sorted(rates.items()):
        print(f"{arm:15s} pass={r['pass']!s:5s} err={r['tool_error_rate']:.2f} unknown={r['unknown_tool_rate']:.2f} "
              f"frame={r['frame_break_rate']:.2f} cutoff={r['cutoff_rate']:.2f} turns={r['turns']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
