"""vLLM backend: same prompts, stop tokens, sampling settings and output parsing as the HF backend,
but with continuous batching (a batch no longer waits for its slowest row), prefix caching (the
conversation re-read every step is cached) and, without lesions, CUDA graphs.

Lesions. vLLM flattens every request of a step into one [tokens, hidden] tensor, so a per-row mask
is not available. Instead, requests are grouped by lesion condition and each group is generated with
that condition active (games are uniform within a condition in the lite designs, so this does not
change who is lesioned). The edit maths is the HF backend's (swarmtom.lesion.hooks): each direction
is projected out, edits at one layer applied in order. vLLM's decoder layers return the residual
stream split as (hidden_states, residual) with the sum added inside the next layer's fused norm;
projection is linear, so projecting both parts equals projecting the stream itself.
Hooks are registered after model load, so lesioned runs use enforce_eager=True (no torch.compile /
CUDA graphs that would bypass them); the backend refuses lesions otherwise.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

from swarmtom.llm.base import Backend, GenRequest, GenResult
from swarmtom.llm.parse import parse_output

log = logging.getLogger(__name__)


class _LesionState:
    """Directions per layer for the active condition, applied by forward hooks inside the model."""

    def __init__(self, conditions: dict):
        self.conditions = conditions  # name -> [Edit]
        self.active: str = "none"
        self._dirs: dict = {}

    def dirs(self, layer: int, device, dtype):
        key = (self.active, layer, str(device), dtype)
        if key not in self._dirs:
            out = []
            for e in self.conditions.get(self.active, []):
                if e.layer != layer:
                    continue
                if e.type != "ablate":
                    raise ValueError("vLLM backend implements ablate edits only")
                d = e.vector.to(device, dtype=dtype)
                out.append((d / (d.norm() + 1e-8), float(e.alpha)))  # same expression as hooks.ablate_direction
            self._dirs[key] = out
        return self._dirs[key]


def _project(x, dirs):
    for d, alpha in dirs:
        c = (x * d).sum(dim=-1, keepdim=True)
        x = x - c * d if alpha == 1.0 else x - alpha * c * d
    return x


def _decoder_layers(model):
    """The text decoder's layer list. vLLM's Qwen3.5 is a multimodal wrapper:
    Qwen3_5ForConditionalGeneration.language_model.model.layers; plain CausalLMs use .model.layers."""
    for path in ("language_model.model.layers", "model.layers", "model.language_model.layers"):
        m = model
        try:
            for part in path.split("."):
                m = getattr(m, part)
        except AttributeError:
            continue
        return m
    raise ValueError(f"cannot find decoder layers in {type(model).__name__}")


def _install_hooks(model, state: _LesionState, layers: set[int]) -> int:
    blocks = _decoder_layers(model)
    if max(layers) >= len(blocks):
        raise ValueError(f"lesion layer {max(layers)} but the model has {len(blocks)} decoder layers")
    n = 0
    for idx in sorted(layers):
        def hook(_m, _inp, out, idx=idx):
            if state.active == "none":
                return out
            if isinstance(out, tuple):
                hs = out[0]
                dirs = state.dirs(idx, hs.device, hs.dtype)
                if not dirs:
                    return out
                rest = list(out[1:])
                if rest and rest[0] is not None:
                    rest[0] = _project(rest[0], dirs)  # residual part of the stream
                return (_project(hs, dirs), *rest)
            dirs = state.dirs(idx, out.device, out.dtype)
            return _project(out, dirs) if dirs else out
        blocks[idx].register_forward_hook(hook)
        n += 1
    return n


class VLLMBackend(Backend):
    name = "vllm"
    supports_lesions = True

    def __init__(self, model_name: str, *, lesions_config: Path | None, repo_root: Path, dtype: str = "bfloat16",
                 enable_thinking: bool = True, max_new_tokens: int = 2048, temperature: float = 0.6,
                 top_p: float = 0.95, seed: int = 0, max_prompt_tokens: int = 32768,
                 gpu_memory_utilization: float = 0.88, enforce_eager: bool | None = None, max_num_seqs: int = 256,
                 **_ignored):
        import os

        os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")  # model in-process, so hooks can be added
        # FlashInfer's sampler and GDN-prefill kernels are JIT-compiled (needs nvcc + ninja matching torch's
        # CUDA); the pod has neither, so use vLLM's PyTorch sampler and the Triton GDN kernels.
        os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")
        from transformers import AutoTokenizer
        from vllm import LLM

        from swarmtom.lesion.conditions import load_conditions
        from swarmtom.llm.hf import stop_token_ids

        self.model_name, self.enable_thinking = model_name, enable_thinking
        self.max_new_tokens, self.temperature, self.top_p, self.seed = max_new_tokens, temperature, top_p, seed
        self.max_prompt_tokens = max_prompt_tokens
        self._calls = 0
        self.provenance: dict = {}
        conditions: dict = {}
        if lesions_config:
            conditions, self.provenance = load_conditions(lesions_config, repo_root)
        # Hooks (and therefore lesions) only in eager mode; a lesion-free run (e.g. the phase-0 baseline)
        # can use CUDA graphs. generate() refuses a lesioned request when hooks are not installed.
        if enforce_eager is None:
            enforce_eager = bool(conditions)
        self.enforce_eager = enforce_eager
        self.uses_lesions = bool(conditions) and enforce_eager
        t0 = time.monotonic()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.llm = LLM(model=model_name, dtype=dtype, seed=seed, gpu_memory_utilization=gpu_memory_utilization,
                       max_model_len=max_prompt_tokens + max_new_tokens, enable_prefix_caching=True,
                       enforce_eager=enforce_eager, max_num_seqs=max_num_seqs, gdn_prefill_backend="triton")
        log.info("vLLM loaded %s in %.0fs (eager=%s)", model_name, time.monotonic() - t0, enforce_eager)
        self.lesions = _LesionState(conditions)
        if self.uses_lesions:
            layers = {e.layer for edits in conditions.values() for e in edits}
            n = self.llm.apply_model(lambda m: _install_hooks(m, self.lesions, layers))
            log.info("lesion hooks installed on %s layer(s)", n)
        self.stop_ids = stop_token_ids(self.tokenizer, None)
        log.info("stop token ids: %s", self.stop_ids)

    def describe(self) -> dict:
        import vllm

        return {"name": self.name, "vllm": vllm.__version__, "model": self.model_name,
                "enable_thinking": self.enable_thinking, "max_new_tokens": self.max_new_tokens,
                "temperature": self.temperature, "top_p": self.top_p, "enforce_eager": self.enforce_eager,
                "prefix_caching": True, "lesion_vectors": self.provenance}

    def render(self, req: GenRequest) -> str:
        from swarmtom.llm.hf import _for_template

        kw = dict(tools=req.tools or None, tokenize=False, add_generation_prompt=True)
        thinking = req.meta.get("enable_thinking", self.enable_thinking)
        try:
            return self.tokenizer.apply_chat_template(_for_template(req.messages), enable_thinking=thinking, **kw)
        except TypeError:
            return self.tokenizer.apply_chat_template(_for_template(req.messages), **kw)

    def _seed_for(self, key: str) -> int:
        h = hashlib.sha256(f"{self.seed}|{self._calls}|{key}".encode()).digest()
        return int.from_bytes(h[:4], "little")

    def generate(self, requests: list[GenRequest], max_new_tokens: int | None = None) -> list[GenResult]:
        from vllm import SamplingParams
        from vllm.inputs import TokensPrompt

        from swarmtom.llm.hf import cut_at_stop

        budget = max_new_tokens or self.max_new_tokens
        self._calls += 1
        out: list[GenResult | None] = [None] * len(requests)
        groups: dict[str, list[int]] = {}
        for i, r in enumerate(requests):
            groups.setdefault(r.lesion or "none", []).append(i)
        stops = set(self.stop_ids)
        # Alternate the group order every call: the group generated last is generated first next time, so its
        # conversation prefixes are still in the prefix cache (performance only; groups are independent).
        order = sorted(groups)
        if self._calls % 2 == 0:
            order.reverse()
        for cond in order:
            if cond != "none" and (cond not in self.lesions.conditions or not self.uses_lesions):
                raise KeyError(f"lesion condition {cond} not available (unknown, or enforce_eager is off)")
            idx = groups[cond]
            prompts, keep = [], []
            for i in idx:
                ids = self.tokenizer(self.render(requests[i]), add_special_tokens=False)["input_ids"]
                if len(ids) > self.max_prompt_tokens:
                    out[i] = GenResult(key=requests[i].key, error=f"prompt too long ({len(ids)} tokens)")
                    continue
                prompts.append(TokensPrompt(prompt_token_ids=ids))
                keep.append(i)
            if not keep:
                continue
            params = [SamplingParams(temperature=self.temperature, top_p=self.top_p if self.temperature > 0 else 1.0,
                                     max_tokens=budget, stop_token_ids=self.stop_ids,
                                     seed=self._seed_for(requests[i].key), skip_special_tokens=False)
                      for i in keep]
            self.lesions.active = cond
            try:
                res = self.llm.generate(prompts, params, use_tqdm=False)
            finally:
                self.lesions.active = "none"
            for i, p, o in zip(keep, prompts, res):
                new = cut_at_stop(list(o.outputs[0].token_ids), stops)
                raw = self.tokenizer.decode(new, skip_special_tokens=False)
                reasoning, content, calls, errors = parse_output(raw)
                out[i] = GenResult(key=requests[i].key, content=content, reasoning=reasoning, tool_calls=calls,
                                   raw=raw, prompt_tokens=len(p["prompt_token_ids"]), completion_tokens=len(new),
                                   parse_errors=errors)
        return out  # type: ignore[return-value]

    def close(self) -> None:
        pass
