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
    assert {e.layer for e in conds["tom"]} == {8} and len(conds["tom"]) == 10
    assert {e.layer for e in conds["emp"]} == {17} and len(conds["emp"]) == 1
    assert {e.layer for e in conds["tom_coarse"]} == {8} and {e.layer for e in conds["emp_coarse"]} == {17}
    assert len(conds["tom_emp"]) == 11 and conds["none"] == []
    assert all(p["model_name"] == "Qwen/Qwen3.5-9B" for p in prov.values())
