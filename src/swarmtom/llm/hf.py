"""Local transformers backend with per-row ToM / empathy lesions.

One copy of the weights serves every agent. Each batch row carries its own lesion condition,
applied by LesionController at the configured layers during the forward pass.

Loading follows LY's August setup (tom-empathy-dissociation vendor/common.py): bf16 on CUDA,
whole model pinned to the first visible GPU, sdpa attention.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import torch

from swarmtom.lesion.conditions import load_conditions
from swarmtom.lesion.hooks import LesionController
from swarmtom.llm.base import Backend, GenRequest, GenResult
from swarmtom.llm.parse import parse_output

log = logging.getLogger(__name__)


def _device(pref: str) -> torch.device:
    if pref == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(pref)


STOP_TOKENS = ("<|im_end|>", "<|endoftext|>", "<|im_start|>", "<|eot_id|>", "</s>")


def stop_token_ids(tokenizer, model_eos) -> list[int]:
    """Every id that ends an assistant turn.

    Qwen3.5-9B ships no generation_config.json and its model config lists only <|endoftext|> as EOS,
    while chat turns end with <|im_end|> (the tokenizer's EOS). Without this, generation runs past the
    end of the turn and invents further turns until max_new_tokens.
    """
    ids: set[int] = set()
    for x in ([model_eos] if isinstance(model_eos, int) else list(model_eos or [])) + [tokenizer.eos_token_id]:
        if isinstance(x, int):
            ids.add(x)
    unk = getattr(tokenizer, "unk_token_id", None)
    for tok in STOP_TOKENS:
        tid = tokenizer.convert_tokens_to_ids(tok)
        if isinstance(tid, int) and tid >= 0 and tid != unk:
            ids.add(tid)
    return sorted(ids)


def cut_at_stop(ids: list[int], stop_ids: set[int]) -> list[int]:
    for i, t in enumerate(ids):
        if t in stop_ids:
            return ids[:i]
    return ids


def plan_batches(lengths: list[int], max_rows: int, max_new_tokens: int, token_budget: int | None) -> list[list[int]]:
    """Group request indices into generate() calls: sorted by prompt length so each batch pads to a
    similar length, at most max_rows per batch, and (if token_budget is set) at most token_budget
    padded tokens (rows x (longest prompt + max_new_tokens)) per batch. Every index appears once."""
    order = sorted(range(len(lengths)), key=lambda i: lengths[i])
    batches: list[list[int]] = []
    cur: list[int] = []
    for i in order:
        cand = cur + [i]
        too_many = len(cand) > max_rows
        too_big = token_budget is not None and len(cand) * (lengths[i] + max_new_tokens) > token_budget
        if cur and (too_many or too_big):
            batches.append(cur)
            cand = [i]
        cur = cand
    if cur:
        batches.append(cur)
    return batches


def _for_template(messages: list[dict]) -> list[dict]:
    """Chat templates expect tool-call arguments as dicts and no extra keys."""
    out = []
    for m in messages:
        m2 = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            m2["tool_calls"] = [{"type": "function", "function": {"name": tc["function"]["name"],
                                                                  "arguments": tc["function"]["arguments"]}}
                                for tc in m["tool_calls"]]
        if m["role"] == "tool":
            m2["name"] = m.get("name", "")
        out.append(m2)
    return out


class HFBackend(Backend):
    name = "hf"
    supports_lesions = True

    def __init__(self, model_name: str, *, lesions_config: Path | None, repo_root: Path, dtype: str = "bfloat16",
                 device: str = "auto", enable_thinking: bool = True, max_new_tokens: int = 2048,
                 temperature: float = 0.6, top_p: float = 0.95, batch_size: int = 8, seed: int = 0,
                 max_prompt_tokens: int = 32768, token_budget: int | None = None):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_name = model_name
        self.device = _device(device)
        self.enable_thinking = enable_thinking
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.batch_size = batch_size
        self.seed = seed
        self.max_prompt_tokens = max_prompt_tokens
        self.token_budget = token_budget
        self._len_cache: dict[str, int] = {}
        self._calls = 0
        torch_dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[dtype]
        if self.device.type == "cpu":
            torch_dtype = torch.float32
        t0 = time.monotonic()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.tokenizer.padding_side = "left"
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        kw: dict = {"trust_remote_code": True, "torch_dtype": torch_dtype}
        if self.device.type == "cuda":
            kw.update(device_map={"": 0}, attn_implementation="sdpa")
            # The cuDNN SDPA kernel failed with an unrecoverable CUDA error (err 999) under memory pressure
            # on the H100 pod (2026-11-06); flash / memory-efficient SDPA kernels are used instead.
            torch.backends.cuda.enable_cudnn_sdp(False)
            # When several jobs share one GPU, cap this process so it hits a catchable OutOfMemoryError
            # (handled by batch splitting) instead of starving the other job.
            frac = os.environ.get("SWARMTOM_GPU_MEM_FRACTION")
            if frac:
                torch.cuda.set_per_process_memory_fraction(float(frac), 0)
                log.info("GPU memory fraction capped at %s", frac)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kw)
        if self.device.type != "cuda":
            self.model = self.model.to(self.device)
        self.model.eval()
        log.info("loaded %s on %s (%s) in %.0fs", model_name, self.device, torch_dtype, time.monotonic() - t0)

        self.provenance: dict = {}
        conditions = {}
        if lesions_config:
            conditions, self.provenance = load_conditions(lesions_config, repo_root)
            hidden = self.model.config.get_text_config().hidden_size if hasattr(self.model.config, "get_text_config") \
                else self.model.config.hidden_size
            for name, edits in conditions.items():
                for e in edits:
                    if e.vector.numel() != hidden:
                        raise ValueError(f"lesion {name}: vector dim {e.vector.numel()} != model hidden {hidden}")
        self.lesions = LesionController(conditions=conditions)
        self.lesions.register(self.model)
        self.stop_ids = stop_token_ids(self.tokenizer, getattr(self.model.generation_config, "eos_token_id", None))
        log.info("stop token ids: %s", self.stop_ids)

    def describe(self) -> dict:
        return {"name": self.name, "model": self.model_name, "device": str(self.device),
                "enable_thinking": self.enable_thinking, "max_new_tokens": self.max_new_tokens,
                "temperature": self.temperature, "top_p": self.top_p, "batch_size": self.batch_size,
                "token_budget": self.token_budget, "lesion_vectors": self.provenance}

    def render(self, req: GenRequest) -> str:
        kw = dict(tools=req.tools or None, tokenize=False, add_generation_prompt=True)
        thinking = req.meta.get("enable_thinking", self.enable_thinking)
        try:
            return self.tokenizer.apply_chat_template(_for_template(req.messages), enable_thinking=thinking, **kw)
        except TypeError:
            return self.tokenizer.apply_chat_template(_for_template(req.messages), **kw)

    def generate(self, requests: list[GenRequest], max_new_tokens: int | None = None) -> list[GenResult]:
        """max_new_tokens overrides the configured budget for this call (used by the dose check)."""
        budget = max_new_tokens or self.max_new_tokens
        texts = [self.render(r) for r in requests]
        lengths = [len(self.tokenizer(t, add_special_tokens=False)["input_ids"]) for t in texts]
        self._len_cache = {r.key: n for r, n in zip(requests, lengths)}
        out: list[GenResult | None] = [None] * len(requests)
        for idx in plan_batches(lengths, self.batch_size, budget, self.token_budget):
            for i, res in zip(idx, self._generate_split([requests[i] for i in idx], budget)):
                out[i] = res
        return out  # type: ignore[return-value]

    def _generate_split(self, reqs: list[GenRequest], max_new_tokens: int) -> list[GenResult]:
        try:
            return self._generate_batch(reqs, max_new_tokens)
        except torch.OutOfMemoryError:
            pass
        # Retry only after leaving the except block: while it is active, the exception's traceback keeps the
        # failed forward pass's activations alive, so every smaller retry OOMs too (seen 2026-11-06: batches
        # cascaded down to "out of memory on a single row").
        import gc

        gc.collect()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        # Learn from the failure: later batches are planned under a smaller padded-token budget, so the
        # same OOM is not retried every tick.
        padded = len(reqs) * (max(self._len_cache.get(r.key, 0) for r in reqs) + max_new_tokens)
        if padded > 0 and (self.token_budget is None or padded * 0.8 < self.token_budget):
            self.token_budget = int(padded * 0.8)
            log.warning("token_budget lowered to %d after OOM", self.token_budget)
        if len(reqs) == 1:
            return [GenResult(key=reqs[0].key, error="out of memory on a single row")]
        half = len(reqs) // 2
        log.warning("OOM at batch %d; splitting", len(reqs))
        return self._generate_split(reqs[:half], max_new_tokens) + self._generate_split(reqs[half:], max_new_tokens)

    @torch.no_grad()
    def _generate_batch(self, reqs: list[GenRequest], max_new_tokens: int) -> list[GenResult]:
        texts = [self.render(r) for r in reqs]
        enc = self.tokenizer(texts, return_tensors="pt", padding=True, add_special_tokens=False)
        if enc["input_ids"].shape[1] > self.max_prompt_tokens:
            # Rows over the limit fail individually; the rest still run.
            lens = enc["attention_mask"].sum(1).tolist()
            ok = [i for i, n in enumerate(lens) if n <= self.max_prompt_tokens]
            res = {i: GenResult(key=reqs[i].key, error=f"prompt too long ({lens[i]} tokens)")
                   for i in range(len(reqs)) if i not in ok}
            if ok:
                for i, r in zip(ok, self._generate_batch([reqs[i] for i in ok], max_new_tokens)):
                    res[i] = r
            return [res[i] for i in range(len(reqs))]
        enc_dev = {k: v.to(self.device) for k, v in enc.items()}
        self._calls += 1
        torch.manual_seed(self.seed + self._calls)
        self.lesions.set_rows([r.lesion for r in reqs])
        try:
            gen = self.model.generate(
                **enc_dev, max_new_tokens=max_new_tokens, do_sample=self.temperature > 0,
                temperature=self.temperature if self.temperature > 0 else None,
                top_p=self.top_p if self.temperature > 0 else None,
                pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.stop_ids,
            )
        finally:
            self.lesions.set_rows(None)
        gen = gen.cpu()
        del enc_dev
        if self.device.type == "cuda":
            torch.cuda.empty_cache()  # hand cached blocks back so a co-located job can use them
        prompt_len = enc["input_ids"].shape[1]
        results = []
        stops = set(self.stop_ids)
        for i, r in enumerate(reqs):
            new = cut_at_stop(gen[i, prompt_len:].tolist(), stops)
            raw = self.tokenizer.decode(new, skip_special_tokens=False)
            reasoning, content, calls, errors = parse_output(raw)
            n_new = len(new)
            results.append(GenResult(key=r.key, content=content, reasoning=reasoning, tool_calls=calls, raw=raw,
                                     prompt_tokens=int(enc["attention_mask"][i].sum()), completion_tokens=n_new,
                                     parse_errors=errors))
        return results

    def close(self) -> None:
        self.lesions.remove()
