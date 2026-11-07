"""Lesion maths and the per-row mask (skipped without torch)."""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from swarmtom.lesion.conditions import load_conditions  # noqa: E402
from swarmtom.lesion.hooks import Edit, LesionController, ablate_direction  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class _Layer(torch.nn.Module):
    def forward(self, x):
        return (x,)


class _Inner(torch.nn.Module):
    def __init__(self, n):
        super().__init__()
        self.layers = torch.nn.ModuleList([_Layer() for _ in range(n)])


class _Model(torch.nn.Module):
    def __init__(self, n=4):
        super().__init__()
        self.model = _Inner(n)

    def forward(self, x):
        for layer in self.model.layers:
            x = layer(x)[0]
        return x


def test_ablate_removes_component():
    d = torch.randn(16)
    hs = torch.randn(2, 3, 16)
    out = ablate_direction(hs, d)
    assert torch.allclose((out * (d / d.norm())).sum(-1), torch.zeros(2, 3), atol=1e-5)


def test_per_row_mask_only_touches_selected_rows():
    d = torch.randn(16)
    ctl = LesionController(conditions={"tom": [Edit("ablate", 1, d)]})
    model = _Model()
    ctl.register(model)
    x = torch.randn(3, 5, 16)
    ctl.set_rows(["none", "tom", "none"])
    y = model(x)
    assert torch.equal(y[0], x[0]) and torch.equal(y[2], x[2])
    assert torch.allclose(y[1], ablate_direction(x[1:2], d)[0])
    ctl.remove()
    assert torch.equal(model(x), x)


def test_rows_must_match_batch():
    ctl = LesionController(conditions={"tom": [Edit("ablate", 0, torch.randn(8))]})
    model = _Model()
    ctl.register(model)
    ctl.set_rows(["tom"])
    with pytest.raises(RuntimeError):
        model(torch.randn(2, 1, 8))


def test_unknown_condition():
    ctl = LesionController(conditions={})
    with pytest.raises(KeyError):
        ctl.set_rows(["tom"])


def test_config_loads_with_checksums_and_august_layers():
    conds, prov = load_conditions(ROOT / "configs" / "lesions.yaml", ROOT)
    # the dose ladder is fixed; tom / emp / tom_emp / random are set by scripts/apply_dose_decision.py
    assert {e.layer for e in conds["tom_sae10"]} == {8} and len(conds["tom_sae10"]) == 10
    assert {e.layer for e in conds["emp_sae1"]} == {17} and len(conds["emp_sae1"]) == 1
    assert {e.layer for e in conds["tom_coarse"]} == {8} and {e.layer for e in conds["emp_coarse"]} == {17}
    assert len(conds["tom_emp"]) == len(conds["tom"]) + len(conds["emp"]) and conds["none"] == []
    assert all(p["model_name"] == "Qwen/Qwen3.5-9B" for p in prov.values())
    # dose ladder (Phase 0b)
    for fam, layer in (("tom", 8), ("emp", 17)):
        for k in (1, 3, 5, 10):
            edits = conds[f"{fam}_sae{k}"]
            assert len(edits) == k and {e.layer for e in edits} == {layer}
    assert {e.layer for e in conds["random_L17"]} == {17} and len(conds["random_L17"]) == 10
    # the ε top-1 rebuilt from the downloaded SAE equals the August vector
    assert torch.allclose(conds["emp_sae1"][0].vector, conds["emp_sae10"][0].vector, atol=1e-5)
    # ladders are nested: top-3 starts with top-1
    assert torch.allclose(conds["emp_sae3"][0].vector, conds["emp_sae1"][0].vector, atol=1e-5)


def test_cached_ablation_is_bit_identical_to_original():
    import torch

    from swarmtom.lesion.hooks import Edit, LesionController

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    g = torch.Generator().manual_seed(0)
    edits = [Edit(type="ablate", layer=3, vector=torch.randn(64, generator=g)) for _ in range(3)]
    ctl = LesionController(conditions={"a": edits})
    for dtype in (torch.float32, torch.bfloat16):
        hs = torch.randn(5, 7, 64, generator=g).to(dev, dtype)
        ref, got = hs, hs
        for e in edits:
            ref = e.apply(ref)
            got = ctl._apply_cached(e, got)
        assert torch.equal(ref, got)


def test_partial_ablation_removes_that_fraction():
    import torch

    from swarmtom.lesion.hooks import Edit, LesionController, ablate_direction

    g = torch.Generator().manual_seed(1)
    d = torch.randn(32, generator=g)
    h = torch.randn(4, 3, 32, generator=g)
    u = d / d.norm()
    before = (h * u).sum(-1)
    half = ablate_direction(h, d, 0.5)
    assert torch.allclose((half * u).sum(-1), 0.5 * before, atol=1e-5)
    full_new, full_old = ablate_direction(h, d, 1.0), h - (h * u).sum(-1, keepdim=True) * u
    assert torch.equal(full_new, full_old)
    e = Edit(type="ablate", layer=0, vector=d, alpha=0.5)
    ctl = LesionController(conditions={"x": [e]})
    assert torch.equal(ctl._apply_cached(e, h), e.apply(h))
