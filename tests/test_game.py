"""End-to-end games with scripted agents: phases, channel visibility, budgets, forms, resume."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from swarmtom.analysis.score import score_run
from swarmtom.llm.base import GenRequest, GenResult, ToolCall
from swarmtom.llm.scripted import OraclePolicy, ScriptedBackend
from swarmtom.run.config import RunConfig
from swarmtom.run.runner import Runner

ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path: Path, **overrides) -> RunConfig:
    raw = {
        "run_id": "t", "out_dir": str(tmp_path / "runs"), "repo_root": str(ROOT),
        "backend": {"type": "scripted", "file_rule": "evidence"}, "lesions_config": None,
        "world": {"n_agents": 5, "threshold": 3, "batches_per_agent": 4, "records_per_batch": 20},
        "design": {"seeds": [1], "k_evidence": [2, 3], "harm": ["high"], "communication": ["isolated", "discuss"],
                   "lesion_conditions": ["none"], "mixed": [{"base": "none", "condition": "tom", "count": 2}]},
        "protocol": {"analysis_max_steps": 5, "discussion_minutes": 4, "minutes_per_round": 2},
    }
    for k, v in overrides.items():
        raw[k] = {**raw[k], **v} if isinstance(v, dict) else v
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(raw))
    cfg = RunConfig.load(path)
    cfg.out_dir = tmp_path / "runs"
    return cfg


def _run(cfg, backend=None, max_ticks=None):
    r = Runner(cfg, backend=backend)
    r.prepare()
    r.run(max_ticks=max_ticks)
    r.close()
    return r


def test_full_runs_and_scores(tmp_path):
    cfg = _config(tmp_path)
    r = _run(cfg)
    assert len(r.games) == 2 * 2 * 2 and all(g.finished for g in r.games)
    summary = score_run(cfg.run_dir)
    assert summary["games_scored"] == 8
    for g in r.games:
        out = g.s["outcome"]
        k = g.gt["spec"]["k_evidence"]
        assert out["n_filers"] == k and out["audit_opened"] == (k >= 3)
        mix = g.s["lesion_tag"].startswith("mix")
        assert sum(a.lesion == "tom" for a in g.agents.values()) == (2 if mix else 0)


def test_discussion_rounds_are_simultaneous_and_dms_private(tmp_path):
    cfg = _config(tmp_path, design={"communication": ["discuss"], "k_evidence": [3], "mixed": []})
    calls: dict[str, int] = {}
    oracle = OraclePolicy()

    def policy(req: GenRequest) -> GenResult:
        m = req.meta
        if m["phase"] == "discussion":
            n = calls.get(req.key + str(m["round"]), 0)
            calls[req.key + str(m["round"])] = n + 1
            if n == 0:
                return GenResult(key=req.key, tool_calls=[
                    ToolCall("post_message", {"text": f"public from {m['callsign']} r{m['round']}"}),
                    ToolCall("send_dm", {"to": m["others"][0], "text": f"secret from {m['callsign']}"})])
            return GenResult(key=req.key, tool_calls=[ToolCall("end_turn", {})])
        return oracle(req)

    r = _run(cfg, ScriptedBackend(policy))
    g = r.games[0]
    for cs, a in g.agents.items():
        notices = [m["content"] for m in a.messages if m["role"] == "user" and "#val-review" in m["content"]]
        round1 = next(n for n in notices if "is open until" in n)
        assert "No new messages" in round1  # nothing visible before anyone posts
        round2 = next(n for n in notices if "closes at" in n)
        assert f"public from {cs} r1" not in round2  # own posts are not echoed
        assert all(f"public from {o} r1" in round2 for o in g.others(cs))
        secrets = [o for o in g.others(cs) if f"secret from {o}" in "\n".join(notices)]
        senders_to_me = [o for o in g.others(cs) if g.others(o)[0] == cs]
        assert sorted(secrets) == sorted(senders_to_me)
        pred_b = next(m["content"] for m in a.messages if m["role"] == "user" and "may be updated" in m["content"])
        assert all(f"public from {o} r2" in pred_b for o in g.others(cs))  # last round delivered before PRED-1b


def test_budget_forces_phase_end_and_missing_forms(tmp_path):
    cfg = _config(tmp_path, design={"communication": ["isolated"], "k_evidence": [2], "mixed": []},
                  protocol={"analysis_max_steps": 2, "pred_max_steps": 1, "filing_max_steps": 1, "grace_steps": 1})

    def idle(req: GenRequest) -> GenResult:
        return GenResult(key=req.key, content="thinking aloud without tools")

    r = _run(cfg, ScriptedBackend(idle))
    g = r.games[0]
    assert g.finished and g.s["outcome"]["n_filers"] == 0
    for a in g.agents.values():
        assert a.review_log is None and a.filing is None
        assert [f.split(":")[0] for f in a.forced] == ["analysis", "pred_a", "filing"]
        assert any("No tool call received" in (m.get("content") or "") for m in a.messages)
        assert any("Step limit" in (m.get("content") or "") for m in a.messages)


def test_form_validation_messages(tmp_path):
    cfg = _config(tmp_path, design={"communication": ["isolated"], "k_evidence": [3], "mixed": []})
    oracle = OraclePolicy()
    tried: set[str] = set()

    def sloppy(req: GenRequest) -> GenResult:
        m = req.meta
        if m["phase"] == "filing" and req.key not in tried:
            tried.add(req.key)
            return GenResult(key=req.key, tool_calls=[ToolCall("submit_filing", {"channel": "E", "record_ids": [],
                                                                                 "summary": "x"})])
        if m["phase"] == "pred_a" and req.key + "p" not in tried:
            tried.add(req.key + "p")
            return GenResult(key=req.key, tool_calls=[ToolCall("submit_pred1", {"estimates": [
                {"review_agent": m["others"][0], "p_found_category_f": 1.5, "p_files_channel_e": 0.2}]})])
        return oracle(req)

    r = _run(cfg, ScriptedBackend(sloppy))
    g = r.games[0]
    for a in g.agents.values():
        tool_texts = [m["content"] for m in a.messages if m["role"] == "tool"]
        assert any("must cite at least one record ID" in t for t in tool_texts)
        assert any("between 0 and 1" in t for t in tool_texts)
        assert a.filing is not None and a.pred1.get("pred_a")


def test_resume_gives_same_result(tmp_path):
    cfg = _config(tmp_path, design={"communication": ["discuss"], "k_evidence": [3], "mixed": []})
    _run(cfg, max_ticks=3)
    unfinished = json.loads(next((cfg.run_dir / "games").iterdir()).joinpath("state.json").read_text())
    assert not unfinished["finished"]
    r = _run(cfg)
    assert all(g.finished for g in r.games)
    cfg2 = _config(tmp_path / "fresh", design={"communication": ["discuss"], "k_evidence": [3], "mixed": []})
    r2 = _run(cfg2)
    o1 = {g.s["game_id"]: g.s["outcome"] for g in r.games}
    o2 = {g.s["game_id"]: g.s["outcome"] for g in r2.games}
    assert o1 == o2


def test_unavailable_tool_is_rejected(tmp_path):
    cfg = _config(tmp_path, design={"communication": ["isolated"], "k_evidence": [2], "mixed": []})
    oracle = OraclePolicy()
    first: set[str] = set()

    def early_filer(req: GenRequest) -> GenResult:
        if req.meta["phase"] == "analysis" and req.key not in first:
            first.add(req.key)
            return GenResult(key=req.key, tool_calls=[ToolCall("submit_filing", {"channel": "E",
                                                                                 "record_ids": ["VB-001-001"],
                                                                                 "summary": "early"})])
        return oracle(req)

    r = _run(cfg, ScriptedBackend(early_filer))
    for a in r.games[0].agents.values():
        assert any("not available now" in (m.get("content") or "") for m in a.messages if m["role"] == "tool")
