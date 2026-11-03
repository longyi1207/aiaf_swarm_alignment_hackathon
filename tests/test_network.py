"""The Python tool's network block, and the self-test that refuses to run when isolation is fake."""

from __future__ import annotations

import sys

import pytest

from swarmtom.agent.sandbox import NetworkIsolationError, network_selftest, run_python

CAN_BLOCK = sys.platform == "darwin"  # Linux depends on whether unprivileged user namespaces are allowed


def _internet(tmp_path) -> bool:
    r = run_python("import socket; socket.create_connection(('1.1.1.1', 53), timeout=3); print('ok')", tmp_path,
                   timeout_s=10, network="allow")
    return r.stdout.strip() == "ok"


@pytest.mark.skipif(not CAN_BLOCK, reason="sandbox-exec block mode is tested on macOS")
def test_block_mode_blocks_and_python_still_works(tmp_path):
    assert "blocked" in network_selftest(tmp_path, "block")
    r = run_python("import pandas, json; print(json.dumps([1]))", tmp_path, timeout_s=60, network="block")
    assert r.returncode == 0 and r.stdout.strip() == "[1]"


def test_container_mode_refuses_when_network_is_reachable(tmp_path):
    if not _internet(tmp_path):
        pytest.skip("no internet here, so 'container' mode is genuinely isolated")
    with pytest.raises(NetworkIsolationError):
        network_selftest(tmp_path, "container")


def test_allow_mode_needs_no_isolation(tmp_path):
    assert network_selftest(tmp_path, "allow").startswith("network allowed")


def test_bad_mode(tmp_path):
    with pytest.raises(ValueError):
        run_python("print(1)", tmp_path, network="maybe")
