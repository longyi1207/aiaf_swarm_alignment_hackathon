"""A deterministic backend for tests and dry runs.

`OraclePolicy` plays the game like a careful reviewer would: it classifies its batches with the
reference SOP solver, posts in #val-review, and files according to a simple rule. It exercises
every tool and phase without a GPU.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from swarmtom.llm.base import Backend, GenRequest, GenResult, ToolCall
from swarmtom.world.sop import check_workspace

Policy = Callable[[GenRequest], GenResult]


class ScriptedBackend(Backend):
    name = "scripted"
    supports_lesions = True  # lesions are recorded but have no effect

    def __init__(self, policy: Policy):
        self.policy = policy

    def generate(self, requests: list[GenRequest]) -> list[GenResult]:
        return [self.policy(r) for r in requests]


def _call(key: str, name: str, args: dict, text: str = "") -> GenResult:
    raw = f"{text}<tool_call>{json.dumps({'name': name, 'arguments': args})}</tool_call>"
    return GenResult(key=key, content=text, tool_calls=[ToolCall(name, args)], raw=raw,
                     prompt_tokens=0, completion_tokens=len(raw) // 4)


class OraclePolicy:
    """file_rule: 'evidence' = file E iff own batches have Category F; 'never'; 'always'."""

    def __init__(self, file_rule: str = "evidence", read_first: bool = True):
        self.file_rule = file_rule
        self.read_first = read_first
        self._cache: dict[str, dict] = {}

    def _verdicts(self, ws: Path) -> dict:
        key = str(ws)
        if key not in self._cache:
            self._cache[key] = check_workspace(ws / "shared", ws)
        return self._cache[key]

    def __call__(self, req: GenRequest) -> GenResult:
        m = req.meta
        phase, cs, ws = m["phase"], m["callsign"], Path(m["workspace"])
        tool_msgs = [x for x in req.messages if x["role"] == "tool"]
        verdicts = self._verdicts(ws)
        has_f = any(v.category == "F" for v in verdicts.values())
        if phase == "analysis":
            if self.read_first and not tool_msgs:
                return _call(req.key, "run_python", {"code": "import pandas as pd\nprint(pd.read_excel("
                                                     "'shared/lot_master.xlsx').shape)"})
            log = [{"batch_id": b, "classification": v.category,
                    "record_ids": sorted(v.violating_records | set(v.r3_block))} for b, v in verdicts.items()]
            return _call(req.key, "submit_review_log", {"batches": log})
        if phase in ("pred_a", "pred_b"):
            est = [{"review_agent": o, "p_found_category_f": 0.5, "p_files_channel_e": 0.5} for o in m["others"]]
            return _call(req.key, "submit_pred1", {"estimates": est})
        if phase == "discussion":
            if m.get("posted_this_round"):
                return _call(req.key, "end_turn", {})
            msg = f"{cs}: {'I found Category F records' if has_f else 'my batches look clean or clerical'}."
            return _call(req.key, "post_message", {"text": msg})
        if phase == "filing":
            file_e = self.file_rule == "always" or (self.file_rule == "evidence" and has_f)
            ids = sorted({r for v in verdicts.values() if v.category == "F" for r in v.violating_records}) or \
                [f"{next(iter(verdicts))}-001"]
            return _call(req.key, "submit_filing",
                         {"channel": "E" if file_e else "I", "record_ids": ids, "summary": "scripted"})
        raise ValueError(f"unknown phase {phase}")
