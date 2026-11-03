"""Inference-time lesions: remove ToM / empathy directions from the residual stream.

Ported from LY's tom-empathy-dissociation (src/hooks.py, MIT). The maths is unchanged:
`ablate_direction` projects one unit direction out of the hidden state at a given layer,
and several edits at one layer are applied in order (the August "sequential" behaviour).

What is new here is a per-row mask. In a swarm every agent shares one copy of the weights,
and agents in the same batch may sit in different lesion conditions. `LesionController`
applies each condition only to the batch rows that belong to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch


def _unwrap_model(model):
    """PeftModel wraps the base LM; hooks need the inner transformer."""
    m = model
    for _ in range(8):
        if hasattr(m, "model") and hasattr(m.model, "layers"):
            return m
        if hasattr(m, "transformer") and hasattr(m.transformer, "h"):
            return m
        if hasattr(m, "base_model"):
            inner = getattr(m.base_model, "model", m.base_model)
            if inner is m:
                break
            m = inner
            continue
        if hasattr(m, "get_base_model"):
            m = m.get_base_model()
            continue
        break
    return m


def get_layers(model):
    m = _unwrap_model(model)
    if hasattr(m, "model") and hasattr(m.model, "layers"):
        return m.model.layers
    if hasattr(m, "transformer") and hasattr(m.transformer, "h"):
        return m.transformer.h
    raise ValueError(f"Unsupported model: {type(model).__name__}")


def _hs(output):
    return output[0] if isinstance(output, tuple) else output


def _wrap(output, hs):
    return (hs,) + output[1:] if isinstance(output, tuple) else hs


def ablate_direction(hs: torch.Tensor, direction: torch.Tensor) -> torch.Tensor:
    """Remove the component along a unit direction (all positions)."""
    d = direction.to(hs.device, dtype=hs.dtype)
    d = d / (d.norm() + 1e-8)
    coeff = (hs * d).sum(dim=-1, keepdim=True)
    return hs - coeff * d


def steer_direction(hs: torch.Tensor, direction: torch.Tensor, alpha: float) -> torch.Tensor:
    d = direction.to(hs.device, dtype=hs.dtype)
    return hs + alpha * d


@dataclass(frozen=True)
class Edit:
    """One edit at one layer. type: ablate | steer+ | steer-."""

    type: str
    layer: int
    vector: torch.Tensor
    alpha: float = 1.0

    def apply(self, hs: torch.Tensor) -> torch.Tensor:
        if self.type == "ablate":
            return ablate_direction(hs, self.vector)
        if self.type == "steer+":
            return steer_direction(hs, self.vector, self.alpha)
        if self.type == "steer-":
            return steer_direction(hs, self.vector, -self.alpha)
        raise ValueError(f"Unknown edit type: {self.type}")


@dataclass
class LesionController:
    """Holds the edits of every lesion condition and which batch rows each applies to.

    Usage:
        ctl = LesionController(conditions={"tom": [Edit(...), ...], "emp": [...]})
        handles = ctl.register(model)
        ctl.set_rows(["none", "tom", "tom", "emp"])   # one entry per batch row
        model.generate(...)
        ctl.remove()
    """

    conditions: dict[str, list[Edit]]
    _rows: list[str] | None = field(default=None, init=False, repr=False)
    _handles: list = field(default_factory=list, init=False, repr=False)

    def set_rows(self, row_conditions: list[str] | None) -> None:
        """Condition name per batch row; None or 'none' rows are left untouched."""
        if row_conditions is not None:
            unknown = {c for c in row_conditions if c not in self.conditions and c != "none"}
            if unknown:
                raise KeyError(f"Unknown lesion condition(s): {sorted(unknown)}")
        self._rows = row_conditions

    def layers(self) -> set[int]:
        return {e.layer for edits in self.conditions.values() for e in edits}

    def _hook_for(self, layer_idx: int):
        def hook(_module, _input, output):
            if not self._rows:
                return output
            hs = _hs(output)
            if hs.shape[0] != len(self._rows):
                raise RuntimeError(
                    f"Batch has {hs.shape[0]} rows but set_rows() was given {len(self._rows)} conditions"
                )
            new_hs = None
            for cond in set(self._rows):
                if cond == "none":
                    continue
                edits = [e for e in self.conditions[cond] if e.layer == layer_idx]
                if not edits:
                    continue
                idx = torch.tensor([i for i, c in enumerate(self._rows) if c == cond], device=hs.device)
                sub = hs.index_select(0, idx)
                for e in edits:
                    sub = e.apply(sub)
                if new_hs is None:
                    new_hs = hs.clone()
                new_hs.index_copy_(0, idx, sub)
            return output if new_hs is None else _wrap(output, new_hs)

        return hook

    def register(self, model) -> list:
        layers = get_layers(model)
        self.remove()
        for idx in sorted(self.layers()):
            self._handles.append(layers[idx].register_forward_hook(self._hook_for(idx)))
        return self._handles

    def remove(self) -> None:
        for h in self._handles:
            h.remove()
        self._handles = []
