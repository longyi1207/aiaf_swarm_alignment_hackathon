"""Agents see only their own workspace; the Python tool is isolated and bounded."""

from __future__ import annotations

import pytest

from swarmtom.agent.sandbox import preferred_network, run_python, truncate

NET = preferred_network()  # OS-level block where the host allows it (macOS, most Linux), else 'audit'
from swarmtom.agent.tools import run_read_tool
from swarmtom.agent.workspace import Workspace, WorkspaceError
from swarmtom.world import WorldSpec, generate_world


@pytest.fixture(scope="module")
def ws(tmp_path_factory):
    root = tmp_path_factory.mktemp("w")
    spec = WorldSpec(seed=4, k_evidence=3)
    world = root / spec.world_id
    gt = generate_world(spec, world)
    cs = gt["agents"][0]["callsign"]
    return Workspace.create(world, cs, root / "game" / cs), gt, cs


def test_workspace_has_no_ground_truth(ws):
    w, _, _ = ws
    listing = w.list_files()
    assert "ground_truth.json" not in listing and "TASK_BRIEF.md" in listing and "shared/lot_master.xlsx" in listing


@pytest.mark.parametrize("bad", ["../ground_truth.json", "/etc/passwd", "shared/../../x"])
def test_path_escape_rejected(ws, bad):
    w, _, _ = ws
    with pytest.raises(WorkspaceError):
        w.resolve(bad)


def test_only_own_batches(ws):
    w, gt, cs = ws
    mine = next(a for a in gt["agents"] if a["callsign"] == cs)["batches"]
    files = {p.stem for p in (w.root / "batches").glob("*.xlsx")}
    assert files == set(mine)


def test_read_document_docx_includes_tables(ws):
    w, _, _ = ws
    text = w.read_document("shared/SOP-VAL-014_Data_Integrity_Review.docx")
    assert "R1 (chronology)" in text and "Category F (integrity failure)" in text


def test_read_table_pages(ws):
    w, _, _ = ws
    out = w.read_table("shared/reference_archive_2025.xlsx", start_row=10, n_rows=5)
    assert "rows 10–14 of 720" in out and out.count("\n") == 7  # header line + csv header + 5 rows


def test_read_tool_errors_are_text(ws):
    w, _, _ = ws
    out = run_read_tool(w, "read_table", {"path": "nope.xlsx"}, max_chars=1000, python_timeout_s=5, python_network=NET)
    assert out.startswith("Error:")
    out = run_read_tool(w, "read_document", {}, max_chars=1000, python_timeout_s=5, python_network=NET)
    assert "missing argument" in out


def test_python_runs_in_workspace_and_persists_files(ws):
    w, _, _ = ws
    r = run_python("import pandas as pd\nprint(len(pd.read_excel('shared/lot_master.xlsx')))\n"
                   "open('note.txt','w').write('x')", w.root, timeout_s=60, network=NET)
    assert r.returncode == 0 and r.stdout.strip() == "24"
    assert (w.root / "note.txt").exists()


def test_python_env_has_no_secrets(ws, monkeypatch):
    w, _, _ = ws
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret-value")
    r = run_python("import os; print(sorted(os.environ))", w.root, timeout_s=30, network=NET)
    assert "AZURE_OPENAI_API_KEY" not in r.stdout


def test_python_cwd_not_importable(ws):
    w, _, _ = ws
    (w.root / "json.py").write_text("raise SystemExit('shadowed')")
    r = run_python("import json; print(json.dumps([1]))", w.root, timeout_s=30, network=NET)
    assert r.stdout.strip() == "[1]"
    (w.root / "json.py").unlink()


def test_python_timeout(ws):
    w, _, _ = ws
    r = run_python("while True: pass", w.root, timeout_s=2, network=NET)
    assert r.timed_out and "timed out" in r.render(500)


def test_truncate_keeps_head_and_tail():
    s = "a" * 100 + "b" * 100
    t = truncate(s, 60)
    assert t.startswith("a") and t.endswith("b") and "omitted" in t
