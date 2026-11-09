"""Steering edits (2026-11-08): added once to vLLM's split stream; natural / reference scaling in the loader."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")


def test_steer_added_once_to_split_stream_and_ablation_to_both():
    from swarmtom.lesion.hooks import Edit
    from swarmtom.llm.vllm_backend import _LesionState, _project, _steer

    g = torch.Generator().manual_seed(0)
    d = torch.randn(16, generator=g)
    state = _LesionState({"up": [Edit("steer+", 3, d / d.norm(), 2.5)], "dn": [Edit("steer-", 3, d / d.norm(), 2.5)],
                          "abl": [Edit("ablate", 3, d, 1.0)]})
    hidden, residual = torch.randn(4, 16, generator=g), torch.randn(4, 16, generator=g)
    u = d / d.norm()
    for cond, sign in (("up", 1.0), ("dn", -1.0)):
        state.active = cond
        dirs = state.dirs(3, hidden.device, hidden.dtype)
        new_res = _steer(_project(residual, dirs), dirs)
        new_hid = _project(hidden, dirs)
        assert torch.allclose(new_hid + new_res, hidden + residual + sign * 2.5 * u, atol=1e-5)
    state.active = "abl"
    dirs = state.dirs(3, hidden.device, hidden.dtype)
    total = _project(hidden, dirs) + _steer(_project(residual, dirs), dirs)
    assert torch.allclose((total * u).sum(-1), torch.zeros(4), atol=1e-4)


def test_natural_and_reference_scaling(tmp_path):
    import yaml

    from swarmtom.lesion.conditions import load_conditions

    v = {0: torch.tensor([3.0, 4.0]), 1: torch.tensor([0.0, 2.0])}
    r = {0: torch.tensor([1.0, 0.0]), 1: torch.tensor([0.0, 1.0])}
    torch.save({"model_name": "m", "vectors": {"tau2": v}, "metadata": {"tau2": {"best_layer": 0}}}, tmp_path / "a.pt")
    torch.save({"model_name": "m", "vectors": {"rand": r}, "metadata": {"rand": {"best_layer": 0}}}, tmp_path / "b.pt")
    cfg = {"vector_files": {"a": {"path": "a.pt"}, "b": {"path": "b.pt"}},
           "conditions": {"nat": {"edits": [{"file": "a", "axes": ["tau2"], "layers": "all", "type": "steer+",
                                             "alpha": 2.0, "scale": "natural"}]},
                          "ref": {"edits": [{"file": "b", "axes": ["rand"], "layers": "all", "type": "steer+",
                                             "alpha": 2.0, "scale_ref": {"file": "a", "axis": "tau2"}}]}}}
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(cfg))
    conds, _ = load_conditions(tmp_path / "c.yaml", tmp_path)
    assert [round(e.alpha, 4) for e in conds["nat"]] == [10.0, 4.0]  # 2 × |v| = 2×5, 2×2
    assert [round(e.alpha, 4) for e in conds["ref"]] == [10.0, 4.0]  # matched magnitudes, random directions
    assert all(abs(float(e.vector.norm()) - 1) < 1e-6 for e in conds["nat"] + conds["ref"])
