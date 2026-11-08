"""Phase 0b dose check: scoring, generation bookkeeping, judging and the matching report (no GPU)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from swarmtom.dose.report import build_report
from swarmtom.dose.run import DoseConfig, generate, judge
from swarmtom.dose.tasks import extract_letter, final_answer, load_items, parse_judge, score_objective
from swarmtom.llm.base import Backend, GenResult

ROOT = Path(__file__).resolve().parents[1]


def test_items_present():
    assert len(load_items("tom")) == 216 and len(load_items("empathy")) == 20 and len(load_items("capability")) == 30


def test_scoring():
    it = load_items("tom")[0]
    assert score_objective("tom", it, it["correct_letter"])["correct"]
    assert extract_letter("The answer is (B).") == "B" and extract_letter("B") == "B"
    assert final_answer("<think>hmm A?</think>\nB") == "B"
    assert score_objective("capability", {"answer": "Paris"}, "It is Paris.")["correct"]
    assert parse_judge('```json\n{"score": 7, "rationale": "x"}\n```') == 7
    assert parse_judge('<think>ok</think>{"score": 12}') is None and parse_judge("nope") is None


def test_capability_accepts_equivalent_counts_and_rejects_partial_tokens():
    def correct(expected, text):
        return score_objective("capability", {"answer": expected}, text)["correct"]

    assert correct("six", "A hexagon has **6** sides.")
    assert correct("eight", "A spider has 8 legs.")
    assert correct("2", "It is two.") and correct("100", "100.0 °C")
    assert not correct("O", "The chemical symbol is Co.")
    assert not correct("Au", "The Latin name is aurum.")
    assert not correct("eight", "18 legs.")
    assert not correct("0", "10.5°C") and not correct("9", "-9.") and not correct("2", "2.5.")


class FakeBackend(Backend):
    """'tom*' lesions answer ToM items wrong, 'emp*' lesions give flat replies; capability always right."""

    name = "fake"
    supports_lesions = True

    def __init__(self, emp_on_thinking: bool = True):
        self.lesions = SimpleNamespace(conditions={c: [] for c in (
            "tom_sae10", "emp_sae10", "random", "tom_sae1", "emp_sae1")})
        self.emp_on_thinking = emp_on_thinking
        self.items = {i["id"]: i for i in load_items("tom")} | {i["id"]: i for i in load_items("capability")}

    def generate(self, requests, max_new_tokens=None):
        out = []
        for r in requests:
            cond, thinking, task, item_id = r.key.split("|")
            if r.messages[0]["role"] == "system":  # judge call
                flat = "Here is what to do" in r.messages[1]["content"]
                out.append(GenResult(key=r.key, content=json.dumps({"score": 2 if flat else 9}),
                                     raw=json.dumps({"score": 2 if flat else 9})))
                continue
            if task == "tom":
                it = self.items[item_id]
                wrong = "A" if it["correct_letter"] == "B" else "B"
                ans = wrong if cond == "tom_sae10" and int(item_id[-1:] or 0) % 2 == 0 else it["correct_letter"]
                if cond == "tom_sae1":
                    ans = it["correct_letter"]
            elif task == "capability":
                ans = self.items[item_id]["answer"]
            else:
                bites = cond.startswith("emp") and (thinking == "0" or self.emp_on_thinking)
                ans = "Here is what to do: call someone." if bites else "I'm so sorry, that sounds painful."
            raw = f"reasoning...</think>\n\n{ans}" if thinking == "1" else ans  # real outputs close the think block
            out.append(GenResult(key=r.key, content=ans, raw=raw, completion_tokens=3))
        return out

    def describe(self):
        return {"name": "fake"}


def _cfg(tmp_path: Path) -> DoseConfig:
    raw = {"run_id": "d", "out_dir": str(tmp_path), "repo_root": str(ROOT), "backend": {"type": "hf", "model": "x"},
           "lesions_config": "configs/lesions.yaml",
           "conditions": ["none", "tom_sae1", "tom_sae10", "emp_sae10", "random"], "thinking": [False, True],
           "limit": {"tom": 40}}
    p = tmp_path / "dose.yaml"
    p.write_text(yaml.safe_dump(raw))
    return DoseConfig.load(p)


def test_generate_is_resumable(tmp_path):
    cfg = _cfg(tmp_path)
    be = FakeBackend()
    n = generate(cfg, be)
    assert n == 5 * 2 * (40 + 20 + 30)
    assert generate(cfg, be) == 0  # nothing left to do


def test_report_matches_and_verdicts(tmp_path):
    cfg = _cfg(tmp_path)
    be = FakeBackend(emp_on_thinking=True)
    generate(cfg, be)
    assert judge(cfg, be) == 5 * 2 * 20
    rep = build_report(cfg.run_dir)
    for t in ("False", "True"):
        assert rep["proposed_pairs"][t] == {"tom": "tom_sae10", "emp": "emp_sae10",
                                            "std_gap": rep["proposed_pairs"][t]["std_gap"]}
    assert rep["thinking_verdict"].startswith("thinking ON is acceptable")
    assert (cfg.run_dir / "report.md").read_text().startswith("# 剂量检查结果")


def test_report_says_thinking_off_when_lesion_stops_biting(tmp_path):
    cfg = _cfg(tmp_path)
    be = FakeBackend(emp_on_thinking=False)
    generate(cfg, be)
    judge(cfg, be)
    rep = build_report(cfg.run_dir)
    assert rep["proposed_pairs"]["True"] is None
    assert rep["thinking_verdict"].startswith("thinking OFF")


def test_cut_off_is_unclosed_thinking():
    from swarmtom.dose.run import cut_off

    assert cut_off(True, "reasoning that never ends")
    assert not cut_off(True, "reasoning</think>\n\nB")
    assert not cut_off(False, "B")


def test_unparseable_judgment_retries_and_preserves_valid_zero(tmp_path):
    from swarmtom.dose.run import judgment_scores

    cfg = _cfg(tmp_path)
    cfg.tasks, cfg.conditions, cfg.thinking, cfg.limit = ["empathy"], ["none"], [True], {"empathy": 2}
    backend = FakeBackend()
    generate(cfg, backend)
    keys = [json.loads(line)["key"] for line in (cfg.run_dir / "generations.jsonl").read_text().splitlines()]
    judgments = cfg.run_dir / "judgments.jsonl"
    old = [{"key": keys[0], "score": 0}, {"key": keys[0], "score": None},
           {"key": keys[1], "score": None, "error": None}]
    judgments.write_text("".join(json.dumps(row) + "\n" for row in old))
    assert parse_judge('{"score": true}') is None
    assert judge(cfg, backend) == 1
    assert judgment_scores(judgments) == {keys[0]: 0, keys[1]: 9}
    assert judge(cfg, backend) == 0
    assert build_report(cfg.run_dir)["table"][0]["empathy"]["value"] == 4.5


def test_tom2_tasks_load_and_score():
    """ToM v2 (2026-11-07): held-out belief items and reality / memory controls, letter-scored."""
    from swarmtom.dose.tasks import load_items, score_objective

    tom, ctl = load_items("tom2"), load_items("tom2ctl")
    assert len(tom) == 180 and len(ctl) == 144
    assert {r["qtype"] for r in tom} == {"fb1", "tb1", "secret1", "fb2", "tb2"}
    assert {r["qtype"] for r in ctl} == {"reality", "memory"}
    r = tom[0]
    assert score_objective("tom2", r, r["correct_letter"])["correct"]
    assert not score_objective("tom2ctl", ctl[0], "AB".replace(ctl[0]["correct_letter"], ""))["correct"]


def test_unfinished_reasoning_is_not_scored_as_an_answer_letter(tmp_path):
    cfg = _cfg(tmp_path)
    cfg.thinking, cfg.tasks, cfg.conditions = [True], ['tom'], ['none']
    cfg.limit = {'tom': 1}
    be = FakeBackend()
    correct = load_items('tom')[0]['correct_letter']
    be.generate = lambda requests, max_new_tokens=None: [GenResult(key=r.key, content=correct + ' while thinking',
        raw=correct + ' while thinking') for r in requests]
    generate(cfg, be)
    row = json.loads((cfg.run_dir / 'generations.jsonl').read_text())
    assert row['cut_off_thinking'] and row['answer'] == '' and not row['correct']
