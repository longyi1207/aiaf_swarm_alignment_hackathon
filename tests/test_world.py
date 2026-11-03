"""World generation: the files alone must determine the ground truth, deterministically."""

from __future__ import annotations

import json

import pandas as pd
import pytest
from docx import Document

from swarmtom.world import WorldSpec, generate_world
from swarmtom.world.sop import check_workspace


def _gen(tmp_path, **kw):
    spec = WorldSpec(**kw)
    out = tmp_path / spec.world_id
    return spec, out, generate_world(spec, out)


@pytest.mark.parametrize("seed,k", [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (7, 3)])
def test_files_reproduce_ground_truth(tmp_path, seed, k):
    spec, out, gt = _gen(tmp_path, seed=seed, k_evidence=k)
    assert len(gt["evidence_agents"]) == k
    for a in gt["agents"]:
        verdicts = check_workspace(out / "shared", out / "agents" / a["callsign"])
        assert {b: v.category for b, v in verdicts.items()} == a["batches"]
        assert any(v.category == "F" for v in verdicts.values()) == a["has_category_f"]
        assert a["has_category_f"] == (a["callsign"] in gt["evidence_agents"])


def test_fabrication_only_in_w_cell(tmp_path):
    _, out, gt = _gen(tmp_path, seed=11, k_evidence=4)
    for a in gt["agents"]:
        f_batches = {b for b, c in a["batches"].items() if c == "F"}
        assert f_batches <= set(a["w_batches"])


def test_deterministic(tmp_path):
    _, out1, gt1 = _gen(tmp_path / "a", seed=42, k_evidence=3, harm="low", communication="isolated")
    _, out2, gt2 = _gen(tmp_path / "b", seed=42, k_evidence=3, harm="low", communication="isolated")
    assert json.dumps(gt1, sort_keys=True) == json.dumps(gt2, sort_keys=True)
    for f in sorted((out1 / "agents").rglob("*.xlsx")):
        rel = f.relative_to(out1)
        pd.testing.assert_frame_equal(pd.read_excel(f), pd.read_excel(out2 / rel))
    for f in (out1 / "shared").glob("*.docx"):
        t1 = [p.text for p in Document(f).paragraphs]
        t2 = [p.text for p in Document(out2 / "shared" / f.name).paragraphs]
        assert t1 == t2


def test_agents_see_only_their_batches(tmp_path):
    _, out, gt = _gen(tmp_path, seed=3, k_evidence=2)
    asg = pd.read_excel(out / "shared" / "review_assignment.xlsx")
    for a in gt["agents"]:
        files = {p.stem for p in (out / "agents" / a["callsign"] / "batches").glob("*.xlsx")}
        assert files == set(asg[asg["reviewer"] == a["callsign"]]["batch_id"])


def test_communication_condition_changes_only_the_channel_text(tmp_path):
    _, o1, _ = _gen(tmp_path / "d", seed=9, communication="discuss")
    _, o2, _ = _gen(tmp_path / "i", seed=9, communication="isolated")
    pol1 = [p.text for p in Document(o1 / "shared" / "POL-ESC-007_External_Escalation_Policy.docx").paragraphs]
    pol2 = [p.text for p in Document(o2 / "shared" / "POL-ESC-007_External_Escalation_Policy.docx").paragraphs]
    diff = [(a, b) for a, b in zip(pol1, pol2) if a != b]
    assert len(diff) == 1 and "#val-review" in diff[0][0] and "may not communicate" in diff[0][1]


def test_harm_levels(tmp_path):
    _, _, lo = _gen(tmp_path / "l", seed=5, harm="low")
    _, _, hi = _gen(tmp_path / "h", seed=5, harm="high")
    assert hi["harm"]["expected_severe_events"] > 0 == lo["harm"]["expected_severe_events"]
    assert hi["harm"]["expected_affected_users"] > lo["harm"]["expected_affected_users"]


def test_spec_validation():
    with pytest.raises(ValueError):
        WorldSpec(seed=1, n_agents=5, threshold=6).validate()
    with pytest.raises(ValueError):
        WorldSpec(seed=1, k_evidence=7).validate()
