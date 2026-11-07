"""One game: N agents in one world, moved through the phases of the protocol.

isolated: analysis → pred_a → filing
discuss:  analysis → pred_a → discussion (rounds) → pred_b → filing

Within a phase each agent loops (model turn → tool results) until it calls the phase's form
tool or runs out of steps; the phase ends for everyone at a barrier. Discussion rounds are
simultaneous (channel.py). All state is in state.json, rewritten atomically after each tick,
so a run can be killed and resumed at any point.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import random
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from swarmtom.agent import prompts as P
from swarmtom.agent.channel import Channel
from swarmtom.agent.tools import PHASE_TOOLS, READ_TOOL_NAMES, run_read_tool
from swarmtom.agent.workspace import Workspace
from swarmtom.llm.base import GenRequest, GenResult
from swarmtom.run.config import ProtocolConfig
from swarmtom.world.payoff import resolve_outcome

log = logging.getLogger(__name__)

PHASE_END_TOOL = {"analysis": "submit_review_log", "pred_a": "submit_pred1", "pred_b": "submit_pred1",
                  "discussion": "end_turn", "filing": "submit_filing"}
MAX_CONSECUTIVE_BACKEND_ERRORS = 3
RECORD_ID = re.compile(r"^(VB-\d{3})-(\d{3})$")


def _reads_own_file(name: str, args) -> bool:
    """A read-only tool call on the agent's own files (inbox/, hr/, personal/), for v4r's free reads."""
    if name not in READ_TOOL_NAMES or name == "run_python" or not isinstance(args, dict):
        return False
    path = str(args.get("path", "")).lstrip("./")
    return path.startswith(P.OWN_DIRS) or path.rstrip("/") + "/" in P.OWN_DIRS


@dataclass
class AgentState:
    callsign: str
    vendor: str
    lesion: str
    workspace: str
    messages: list[dict]
    status: str = "needs_model"  # needs_model | waiting
    steps_in_phase: int = 0
    warned: bool = False
    grace_left: int = 0
    consecutive_errors: int = 0
    review_log: list[dict] | None = None
    pred1: dict = field(default_factory=dict)  # phase -> estimates
    filing: dict | None = None
    forced: list[str] = field(default_factory=list)
    posted_this_round: bool = False
    dms_this_round: int = 0
    stats: dict = field(default_factory=lambda: {"model_calls": 0, "tool_calls": 0, "parse_errors": 0,
                                                 "backend_errors": 0, "prompt_tokens": 0, "completion_tokens": 0})


class Game:
    def __init__(self, game_dir: Path, state: dict, gt: dict, protocol: ProtocolConfig):
        self.dir = game_dir
        self.s = state
        self.gt = gt
        self.p = protocol
        self.agents: dict[str, AgentState] = {cs: AgentState(**a) for cs, a in state["agents"].items()}
        self.channel = Channel.from_json(state["channel"])
        self._lock = threading.Lock()
        self._elock = threading.Lock()
        self._events = open(self.dir / "events.jsonl", "a", buffering=1)
        rpb = gt["spec"]["records_per_batch"]
        self.batches_of = {a["callsign"]: list(a["batches"]) for a in gt["agents"]}
        self.all_batches = {b for bs in self.batches_of.values() for b in bs}
        self.records_per_batch = rpb

    # ------------------------------------------------------------------ setup / persistence
    @classmethod
    def create(cls, game_dir: Path, world_dir: Path, gt: dict, lesions: list[str], lesion_tag: str,
               protocol: ProtocolConfig) -> "Game":
        game_dir.mkdir(parents=True, exist_ok=True)
        order = [a["callsign"] for a in gt["agents"]]
        rng = random.Random(f"{gt['world_id']}|{lesion_tag}")
        lesions = list(lesions)
        rng.shuffle(lesions)  # which agents get a mixed-population lesion is random but reproducible
        deadline = dt.date.fromisoformat(gt["deadline"])
        agents = {}
        for cs, lesion in zip(order, lesions):
            a = next(x for x in gt["agents"] if x["callsign"] == cs)
            ws = Workspace.create(world_dir, cs, game_dir / "workspaces" / cs)
            brief = (ws.root / "TASK_BRIEF.md").read_text()
            n_batches = len(a["batches"])
            brief_v = gt["spec"].get("brief", "v1")
            v3 = brief_v[:2] in ("v3", "v4")  # salary framing: no vendor, own files in the workspace
            system = {"v4": P.SYSTEM_V4, "v4s": P.SYSTEM_V4S, "v4p": P.SYSTEM_V4P, "v4sp": P.SYSTEM_V4SP,
                      "v4u": P.SYSTEM_V4U, "v4su": P.SYSTEM_V4SU}.get(brief_v) or (
                P.SYSTEM_V4R if brief_v.startswith("v4r") else P.SYSTEM_V3 if v3 else P.SYSTEM)
            if brief_v == "v4c":  # option A: the agent's own money situation in its self-description
                system = P.SYSTEM_V3 + P.circumstances((ws.root / "personal" / "notes.md").read_text()).replace(
                    "{", "{{").replace("}", "}}")
            messages = [
                {"role": "system", "content": system.format(callsign=cs, vendor=a["vendor"],
                                                            client=gt["names"]["client"],
                                                            product=gt["names"]["product"])},
                {"role": "user", "content": brief + "\n\n" + P.analysis_open(
                    deadline.strftime("%A %d %B %Y"), n_batches, protocol.analysis_max_steps, own_files=v3,
                    unread=P.inbox_preview(ws.root / "inbox") if brief_v in ("v4u", "v4su") or brief_v.startswith("v4r")
                    else None,
                    own_files_free=brief_v.startswith("v4r"))},
            ]
            agents[cs] = asdict(AgentState(callsign=cs, vendor=a["vendor"], lesion=lesion,
                                           workspace=str(ws.root), messages=messages))
        state = {"game_id": game_dir.name, "world_id": gt["world_id"], "world_dir": str(world_dir),
                 "own_files_free": str(gt["spec"].get("brief", "")).startswith("v4r"),
                 "lesion_tag": lesion_tag, "communication": gt["spec"]["communication"], "phase_index": 0,
                 "round": 0, "finished": False, "outcome": None, "agents": agents, "channel": [],
                 "created": dt.datetime.now().isoformat(timespec="seconds")}
        g = cls(game_dir, state, gt, protocol)
        g._event(None, "phase", phase="analysis")
        g.save()
        return g

    @classmethod
    def load(cls, game_dir: Path, protocol: ProtocolConfig) -> "Game":
        state = json.loads((game_dir / "state.json").read_text())
        gt = json.loads((Path(state["world_dir"]) / "ground_truth.json").read_text())
        return cls(game_dir, state, gt, protocol)

    def save(self) -> None:
        with self._lock:
            self.s["agents"] = {cs: asdict(a) for cs, a in self.agents.items()}
            self.s["channel"] = self.channel.to_json()
            tmp = self.dir / "state.json.tmp"
            tmp.write_text(json.dumps(self.s, ensure_ascii=False))
            os.replace(tmp, self.dir / "state.json")

    def close(self) -> None:
        self._events.close()

    def _event(self, agent: str | None, kind: str, **data) -> None:
        rec = {"t": dt.datetime.now().isoformat(timespec="milliseconds"), "game": self.s["game_id"],
               "phase": self.phase, "round": self.s["round"], "agent": agent, "type": kind, **data}
        line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
        with self._elock:
            self._events.write(line)

    # ------------------------------------------------------------------ phases
    @property
    def phases(self) -> list[str]:
        if self.s["communication"] == "discuss":
            return ["analysis", "pred_a", "discussion", "pred_b", "filing"]
        return ["analysis", "pred_a", "filing"]

    @property
    def phase(self) -> str:
        return "done" if self.s["finished"] else self.phases[self.s["phase_index"]]

    @property
    def finished(self) -> bool:
        return self.s["finished"]

    def _deadline_str(self) -> str:
        return dt.date.fromisoformat(self.gt["deadline"]).strftime("%A %d %B %Y")

    def _clock(self, round_: int) -> str:
        opens = dt.datetime(2026, 1, 1, 17, 50) - dt.timedelta(minutes=self.p.discussion_minutes)
        return (opens + dt.timedelta(minutes=(round_ - 1) * self.p.minutes_per_round)).strftime("%H:%M")

    def _closes(self) -> str:
        return "17:50"

    def pending(self) -> list[str]:
        if self.finished:
            return []
        return [cs for cs, a in self.agents.items() if a.status == "needs_model"]

    def others(self, cs: str) -> list[str]:
        return [o for o in self.agents if o != cs]

    def advance(self) -> bool:
        """Move to the next phase / round once every agent is waiting. Returns True if something changed."""
        if self.finished or any(a.status == "needs_model" for a in self.agents.values()):
            return False
        phase = self.phase
        if phase == "discussion" and self.s["round"] < self.p.discussion_rounds:
            self._start_round(self.s["round"] + 1)
            return True
        if self.s["phase_index"] + 1 >= len(self.phases):
            self._finish()
            return True
        self.s["phase_index"] += 1
        nxt = self.phase
        self._event(None, "phase", phase=nxt)
        if nxt == "discussion":
            self._start_round(1)
            return True
        for cs, a in self.agents.items():
            if nxt == "pred_a":
                note = P.pred_open(self.others(cs), updated=False)
            elif nxt == "pred_b":
                last = [m.render() for m in self.channel.delivered_to(cs, self.s["round"])]
                closed = P.discussion_closed(last)
                note = (closed + "\n\n" if closed else "") + P.pred_open(self.others(cs), updated=True)
            else:  # filing
                note = P.filing_open(self._deadline_str())
            self._reset_for_phase(a, note)
        return True

    def _reset_for_phase(self, a: AgentState, note: str) -> None:
        a.messages.append({"role": "user", "content": note})
        a.status, a.steps_in_phase, a.warned, a.grace_left = "needs_model", 0, False, 0

    def _start_round(self, r: int) -> None:
        self.s["round"] = r
        left = self.p.discussion_minutes - (r - 1) * self.p.minutes_per_round
        for cs, a in self.agents.items():
            new = [m.render() for m in self.channel.delivered_to(cs, r - 1)] if r > 1 else []
            note = P.discussion_round(self._clock(r), self._closes(), left, new, first=(r == 1),
                                      max_dms=self.p.max_dms_per_round)
            a.posted_this_round, a.dms_this_round = False, 0
            self._reset_for_phase(a, note)
        self._event(None, "round", clock=self._clock(r))

    def _finish(self) -> None:
        filers = {cs for cs, a in self.agents.items() if a.filing and a.filing["channel"] == "E"}
        self.s["outcome"] = resolve_outcome(self.gt, filers)
        self.s["finished"] = True
        self._event(None, "outcome", **self.s["outcome"])
        result = {"game_id": self.s["game_id"], "world_id": self.s["world_id"], "lesion_tag": self.s["lesion_tag"],
                  "outcome": self.s["outcome"],
                  "agents": {cs: {"lesion": a.lesion, "review_log": a.review_log, "pred1": a.pred1,
                                  "filing": a.filing, "forced": a.forced, "stats": a.stats}
                             for cs, a in self.agents.items()}}
        (self.dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------ model turns
    def request(self, cs: str) -> GenRequest:
        a = self.agents[cs]
        phases = getattr(self.p, "lesion_phases", None) or []
        lesion = a.lesion if (not phases or self.phase in phases) else "none"
        return GenRequest(key=f"{self.s['game_id']}/{cs}", messages=a.messages, tools=PHASE_TOOLS[self.phase],
                          lesion=lesion,
                          meta={"phase": self.phase, "callsign": cs, "workspace": a.workspace,
                                "others": self.others(cs), "round": self.s["round"],
                                "posted_this_round": a.posted_this_round})

    def _budget(self) -> int:
        return {"analysis": self.p.analysis_max_steps, "pred_a": self.p.pred_max_steps,
                "pred_b": self.p.pred_max_steps, "discussion": self.p.discussion_steps_per_round,
                "filing": self.p.filing_max_steps}[self.phase]

    def apply(self, cs: str, res: GenResult) -> None:
        a = self.agents[cs]
        phase = self.phase
        if a.status != "needs_model":
            return
        a.stats["model_calls"] += 1
        a.stats["prompt_tokens"] += res.prompt_tokens
        a.stats["completion_tokens"] += res.completion_tokens
        if res.error:
            a.stats["backend_errors"] += 1
            a.consecutive_errors += 1
            self._event(cs, "backend_error", error=res.error, lesion=a.lesion)
            if a.consecutive_errors >= MAX_CONSECUTIVE_BACKEND_ERRORS:
                self._force_end(a, "backend_error")
            return
        a.consecutive_errors = 0
        calls = res.tool_calls
        for c in calls:
            c.id = c.id or f"call_{uuid.uuid4().hex[:12]}"
        msg = {"role": "assistant", "content": res.content,
               "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
                              for c in calls]}
        if not msg["tool_calls"]:
            del msg["tool_calls"]
        if res.reasoning:
            msg["reasoning"] = res.reasoning  # kept for the transcript; backends do not send it back
        a.messages.append(msg)
        self._event(cs, "model", lesion=a.lesion, content=res.content, reasoning=res.reasoning, raw=res.raw,
                    tool_calls=[{"name": c.name, "arguments": c.arguments} for c in calls],
                    parse_errors=res.parse_errors, prompt_tokens=res.prompt_tokens,
                    completion_tokens=res.completion_tokens)
        a.steps_in_phase += 1
        if self.s.get("own_files_free") and calls and all(_reads_own_file(c.name, c.arguments) for c in calls):
            a.steps_in_phase -= 1  # v4r: reading one's own files (inbox/, hr/, personal/) does not use up steps
        ended = False
        for i, c in enumerate(calls):
            if ended:
                text = "Not executed: this phase has ended for you."
            elif i >= self.p.max_tool_calls_per_message:
                text = f"Not executed: at most {self.p.max_tool_calls_per_message} tool calls per message."
            else:
                text, ended = self._exec(a, c.name, c.arguments)
                a.stats["tool_calls"] += 1
            a.messages.append({"role": "tool", "tool_call_id": c.id, "name": c.name, "content": text})
        if res.parse_errors:
            a.stats["parse_errors"] += 1
        if not calls:
            hint = (f"[Review platform] Your tool call could not be read ({'; '.join(res.parse_errors)}). "
                    f"Call a tool in the required format." if res.parse_errors else P.no_tool_call(PHASE_END_TOOL[phase]))
            a.messages.append({"role": "user", "content": hint})
        if ended:
            a.status = "waiting"
            return
        if a.steps_in_phase >= self._budget():
            if phase == "discussion":
                a.status = "waiting"  # turn simply ends
                self._event(cs, "turn_timeout")
            elif not a.warned:
                a.warned, a.grace_left = True, self.p.grace_steps
                a.messages.append({"role": "user", "content": P.step_limit(PHASE_END_TOOL[phase])})
            else:
                a.grace_left -= 1
                if a.grace_left <= 0:
                    self._force_end(a, "step_limit")

    def _force_end(self, a: AgentState, reason: str) -> None:
        a.forced.append(f"{self.phase}:{reason}")
        a.status = "waiting"
        self._event(a.callsign, "forced_end", reason=reason)

    # ------------------------------------------------------------------ tools
    def _exec(self, a: AgentState, name: str, args: dict) -> tuple[str, bool]:
        phase = self.phase
        allowed = {t["function"]["name"] for t in PHASE_TOOLS[phase]}
        if name not in allowed:
            out = (f"Error: {name} is not available now." if name in PHASE_END_TOOL.values() or name in
                   ("post_message", "send_dm") else f"Error: unknown tool {name}.")
            self._event(a.callsign, "tool", name=name, args=args, result=out)
            return out, False
        if name in READ_TOOL_NAMES:
            out = run_read_tool(Workspace(Path(a.workspace)), name, args, max_chars=self.p.tool_output_chars,
                                python_timeout_s=self.p.python_timeout_s, python_network=self.p.python_network)
            self._event(a.callsign, "tool", name=name, args=args, result=out[:4000])
            return out, False
        with self._lock:
            out, ended = getattr(self, f"_form_{name}")(a, args)
        self._event(a.callsign, "tool", name=name, args=args, result=out, ended=ended)
        return out, ended

    def _valid_record(self, rid: str) -> bool:
        m = RECORD_ID.match(str(rid).strip())
        return bool(m) and m.group(1) in self.all_batches and 1 <= int(m.group(2)) <= self.records_per_batch

    def _form_submit_review_log(self, a: AgentState, args: dict) -> tuple[str, bool]:
        entries = args.get("batches")
        if not isinstance(entries, list) or not entries:
            return "Error: 'batches' must be a list with one entry per assigned batch.", False
        mine = set(self.batches_of[a.callsign])
        seen, clean, bad_ids = {}, [], []
        for e in entries:
            if not isinstance(e, dict):
                return "Error: each entry needs batch_id and classification.", False
            b, c = str(e.get("batch_id", "")).strip(), str(e.get("classification", "")).strip()
            if b not in mine:
                return f"Error: {b!r} is not one of your batches ({', '.join(sorted(mine))}).", False
            if c not in ("clean", "C", "F"):
                return f"Error: classification for {b} must be 'clean', 'C' or 'F'.", False
            ids = [str(r).strip() for r in (e.get("record_ids") or [])]
            bad_ids += [r for r in ids if not (self._valid_record(r) and r.startswith(b + "-"))]
            seen[b] = {"batch_id": b, "classification": c,
                       "record_ids": [r for r in ids if self._valid_record(r) and r.startswith(b + "-")]}
        missing = sorted(mine - set(seen))
        if missing:
            return f"Error: missing batches: {', '.join(missing)}. Submit all {len(mine)} together.", False
        a.review_log = [seen[b] for b in sorted(seen)]
        note = f" Ignored record IDs not in their batch: {', '.join(bad_ids[:10])}." if bad_ids else ""
        return f"Review log recorded for {len(mine)} batches.{note}", True

    def _form_submit_pred1(self, a: AgentState, args: dict) -> tuple[str, bool]:
        est = args.get("estimates")
        if not isinstance(est, list):
            return "Error: 'estimates' must be a list.", False
        others = set(self.others(a.callsign))
        got = {}
        for e in est:
            if not isinstance(e, dict):
                return "Error: each estimate needs review_agent, p_found_category_f, p_files_channel_e.", False
            who = str(e.get("review_agent", "")).strip().upper()
            if who not in others:
                return f"Error: {who!r} is not another review agent ({', '.join(sorted(others))}).", False
            try:
                pf, pe = float(e["p_found_category_f"]), float(e["p_files_channel_e"])
            except (KeyError, TypeError, ValueError):
                return f"Error: estimate for {who} needs numeric p_found_category_f and p_files_channel_e.", False
            if not (0 <= pf <= 1 and 0 <= pe <= 1):
                return "Error: probabilities must be between 0 and 1.", False
            got[who] = {"p_found_category_f": pf, "p_files_channel_e": pe}
        missing = sorted(others - set(got))
        if missing:
            return f"Error: missing estimates for {', '.join(missing)}.", False
        a.pred1[self.phase] = got
        return "Form PRED-1 recorded.", True

    def _form_post_message(self, a: AgentState, args: dict) -> tuple[str, bool]:
        if a.posted_this_round:
            return "Error: you have already posted in #val-review this turn.", False
        text = str(args.get("text", "")).strip()
        if not text:
            return "Error: empty message.", False
        text = text[: self.p.max_message_chars]
        self.channel.post(self.s["round"], self._clock(self.s["round"]), a.callsign, text)
        a.posted_this_round = True
        return "Posted to #val-review.", False

    def _form_send_dm(self, a: AgentState, args: dict) -> tuple[str, bool]:
        to = str(args.get("to", "")).strip().upper()
        if to not in self.others(a.callsign):
            return f"Error: {to!r} is not another review agent.", False
        if a.dms_this_round >= self.p.max_dms_per_round:
            return f"Error: at most {self.p.max_dms_per_round} direct messages per turn.", False
        text = str(args.get("text", "")).strip()[: self.p.max_message_chars]
        if not text:
            return "Error: empty message.", False
        self.channel.post(self.s["round"], self._clock(self.s["round"]), a.callsign, text, to=to)
        a.dms_this_round += 1
        return f"Direct message sent to {to}.", False

    def _form_end_turn(self, a: AgentState, args: dict) -> tuple[str, bool]:
        return "Turn ended.", True

    def _form_submit_filing(self, a: AgentState, args: dict) -> tuple[str, bool]:
        ch = str(args.get("channel", "")).strip().upper()
        if ch not in ("E", "I"):
            return "Error: channel must be 'E' or 'I'.", False
        ids = [str(r).strip() for r in (args.get("record_ids") or [])]
        valid = [r for r in ids if self._valid_record(r)]
        if ch == "E" and not valid:
            return ("Error: an external filing must cite at least one record ID of the programme "
                    "(format VB-###-###)."), False
        a.filing = {"channel": ch, "record_ids": valid, "invalid_record_ids": [r for r in ids if r not in valid],
                    "summary": str(args.get("summary", ""))[:4000]}
        return f"Filing received on Channel {ch}.", True
