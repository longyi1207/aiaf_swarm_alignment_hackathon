"""Phase 0b dose check: how much does each lesion strength hurt ToM, empathy and general capability,
with thinking off and on?

Three steps, so generation (GPU) and judging (any machine) can run in different places:
    swarmtom dose-gen    <config>   generations.jsonl  (GPU; resumable)
    swarmtom dose-judge  <config>   judgments.jsonl    (empathy replies scored 0–10; local model or API)
    swarmtom dose-report <run_dir>  report.md / report.json (drops vs no lesion, matched doses, thinking verdict)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from swarmtom.dose.tasks import (EMPATHY_JUDGE_SYSTEM, EMPATHY_JUDGE_TEMPLATE, MAX_TOKENS, final_answer,
                                 load_items, parse_judge, prompt_of, score_objective)
from swarmtom.llm.base import GenRequest
from swarmtom.run.provenance import ensure_manifest, ensure_runtime, record_session

log = logging.getLogger(__name__)


@dataclass
class DoseConfig:
    run_id: str
    out_dir: Path
    repo_root: Path
    backend: dict
    lesions_config: Path
    conditions: list[str]
    thinking: list[bool] = field(default_factory=lambda: [False, True])
    tasks: list[str] = field(default_factory=lambda: ["tom", "empathy", "capability"])
    limit: dict = field(default_factory=dict)  # task -> max items (e.g. subsample BigToM with thinking on)
    chunk: int = 128  # requests handed to the backend per call (it batches internally)
    judge: dict = field(default_factory=lambda: {"type": "hf_self"})
    # Optional per-task token budgets for thinking-on answers (2026-11-07: the default 1024 for BigToM cut off 9% of
    # the unlesioned model's answers, so "cut off" measured the budget rather than lesion damage).
    max_tokens_thinking: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "DoseConfig":
        raw = yaml.safe_load(path.read_text())
        root = Path(raw.get("repo_root", path.resolve().parents[1]))
        return cls(run_id=raw["run_id"], out_dir=(root / raw.get("out_dir", "runs")).resolve(), repo_root=root,
                   backend=raw["backend"], lesions_config=(root / raw["lesions_config"]).resolve(),
                   conditions=raw["conditions"], thinking=raw.get("thinking", [False, True]),
                   tasks=raw.get("tasks", ["tom", "empathy", "capability"]), limit=raw.get("limit", {}),
                   chunk=raw.get("chunk", 128), judge=raw.get("judge", {"type": "hf_self"}),
                   max_tokens_thinking=raw.get("max_tokens_thinking", {}))

    @property
    def run_dir(self) -> Path:
        return self.out_dir / self.run_id


def cut_off(thinking: bool, raw: str | None) -> bool:
    """Thinking was on but the reasoning never closed within the token budget. (The chat template opens
    <think> in the prompt, so an unclosed block parses as plain content; checking the parsed fields missed
    these until 2026-11-06.)"""
    return bool(thinking) and "</think>" not in (raw or "")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def judgment_scores(path: Path) -> dict[str, int]:
    """Keep the latest successful score per answer, including zero, across attempts."""
    return {row["key"]: row["score"] for row in _read_jsonl(path)
            if not row.get("error") and type(row.get("score")) is int and 0 <= row["score"] <= 10}


def _hf(cfg: DoseConfig):
    b = dict(cfg.backend)
    kind = b.pop("type")
    b.setdefault("temperature", 0.0)  # August used greedy decoding
    if kind == "vllm":
        from swarmtom.llm.vllm_backend import VLLMBackend

        b.pop("batch_size", None)
        b.pop("token_budget", None)
        b.setdefault("enforce_eager", True)
        return VLLMBackend(b.pop("model"), lesions_config=cfg.lesions_config, repo_root=cfg.repo_root, **b)
    assert kind == "hf", "the dose check needs a backend that can apply lesions (hf or vllm)"
    from swarmtom.llm.hf import HFBackend

    return HFBackend(b.pop("model"), lesions_config=cfg.lesions_config, repo_root=cfg.repo_root, **b)


def generate(cfg: DoseConfig, backend=None) -> int:
    ensure_manifest(cfg, "dose")
    out = cfg.run_dir / "generations.jsonl"
    done = {r["key"] for r in _read_jsonl(out)}
    backend = backend or _hf(cfg)
    missing = set(cfg.conditions) - {"none"} - set(getattr(backend, "lesions").conditions)
    if missing:
        raise ValueError(f"conditions not in {cfg.lesions_config}: {sorted(missing)}")
    ensure_runtime(cfg.run_dir, backend.describe())
    meta = {"backend": backend.describe(), "conditions": cfg.conditions}
    record_session(cfg.run_dir, meta)
    if not (cfg.run_dir / "dose_meta.json").exists():
        (cfg.run_dir / "dose_meta.json").write_text(json.dumps(meta, indent=2, default=str))
    written = 0
    with open(out, "a", buffering=1) as f:
        for thinking in cfg.thinking:
            for task in cfg.tasks:
                items = load_items(task, cfg.repo_root)[: cfg.limit.get(task) or None]
                reqs = []
                for cond in cfg.conditions:
                    for it in items:
                        key = f"{cond}|{int(thinking)}|{task}|{it['id']}"
                        if key not in done:
                            reqs.append((GenRequest(key=key, messages=[{"role": "user", "content": prompt_of(task, it)}],
                                                    tools=[], lesion=cond, meta={"enable_thinking": thinking}), it))
                for i in range(0, len(reqs), cfg.chunk):
                    part = reqs[i: i + cfg.chunk]
                    t0 = time.monotonic()
                    budget = (cfg.max_tokens_thinking.get(task) if thinking else None) or MAX_TOKENS[thinking][task]
                    results = backend.generate([r for r, _ in part], max_new_tokens=budget)
                    for (req, it), res in zip(part, results):
                        truncated = cut_off(thinking, res.raw)
                        # Never score a letter mentioned in unfinished reasoning as the final answer.
                        answer = "" if truncated else (res.content if res.content or not res.raw else final_answer(res.raw))
                        rec = {"key": req.key, "condition": req.lesion, "thinking": thinking, "task": task,
                               "item_id": it["id"], "item_condition": it.get("condition"), "answer": answer,
                               "reasoning": res.reasoning, "raw": res.raw, "error": res.error,
                               "completion_tokens": res.completion_tokens,
                               "cut_off_thinking": truncated,
                               **score_objective(task, it, answer)}
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        written += 1
                    log.info("dose-gen thinking=%s task=%s %d/%d (%.1fs)", thinking, task, min(i + cfg.chunk, len(reqs)),
                             len(reqs), time.monotonic() - t0)
    return written


def judge(cfg: DoseConfig, backend=None) -> int:
    ensure_manifest(cfg, "dose")
    gens = [g for g in _read_jsonl(cfg.run_dir / "generations.jsonl") if g["task"] == "empathy"]
    out = cfg.run_dir / "judgments.jsonl"
    done = judgment_scores(out)
    todo = [g for g in gens if g["key"] not in done]
    if not todo:
        return 0
    prompts = {it["id"]: it["prompt"] for it in load_items("empathy", cfg.repo_root)}
    kind = cfg.judge.get("type", "hf_self")
    if backend is None:
        if kind == "hf_self":
            backend = _hf(cfg)
        elif kind == "openai_compat":
            from swarmtom.llm.openai_compat import OpenAICompatBackend

            j = {k: v for k, v in cfg.judge.items() if k != "type"}
            backend = OpenAICompatBackend(j.pop("base_url"), j.pop("model"), **j)
        else:
            raise ValueError(f"unknown judge type {kind}")
    reqs = [GenRequest(key=g["key"], tools=[], lesion="none", meta={"enable_thinking": False}, messages=[
        {"role": "system", "content": EMPATHY_JUDGE_SYSTEM},
        {"role": "user", "content": EMPATHY_JUDGE_TEMPLATE.format(confide=prompts[g["item_id"]], reply=g["answer"])}])
            for g in todo]
    n = 0
    with open(out, "a", buffering=1) as f:
        for i in range(0, len(reqs), cfg.chunk):
            part = reqs[i: i + cfg.chunk]
            results = backend.generate(part, max_new_tokens=200) if kind == "hf_self" else backend.generate(part)
            for req, res in zip(part, results, strict=True):
                score = parse_judge(res.raw or res.content)
                error = res.error or ("Judge returned no valid score" if score is None else None)
                f.write(json.dumps({"key": req.key, "score": score, "raw": res.raw,
                                    "judge": kind, "error": error}) + "\n")
                n += 1
    return n
