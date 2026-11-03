"""The run_python tool: run agent code in a fresh, isolated interpreter inside its workspace.

Isolation (proportionate to a local open-weight model analysing spreadsheets):
- `python -I`: no PYTHONPATH, no user site, and the working directory is NOT on sys.path,
  so files the agent writes cannot shadow imports;
- a minimal environment (no credentials are inherited);
- wall-clock timeout, CPU-time limit, and on Linux an address-space limit;
- its own process group, killed as a whole on timeout;
- output truncated (head and tail kept);
- network blocked (`network="block"`): `sandbox-exec` deny-network profile on macOS, `unshare -rn`
  (a fresh network namespace with no interfaces) on Linux. Where neither works (e.g. Ubuntu with
  unprivileged user namespaces restricted), run the whole job in a container started with
  `--network none` and set `network="container"`. `network_selftest` proves the block before a run.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PythonResult:
    stdout: str
    stderr: str
    returncode: int | None
    timed_out: bool
    duration_s: float

    def render(self, max_chars: int) -> str:
        parts = []
        if self.timed_out:
            parts.append(f"[timed out after {self.duration_s:.0f}s]")
        if self.stdout:
            parts.append(truncate(self.stdout, max_chars))
        if self.stderr:
            parts.append("[stderr]\n" + truncate(self.stderr, max_chars // 2))
        if not parts:
            parts.append("[no output — use print() to see results]")
        if self.returncode not in (0, None):
            parts.append(f"[exit code {self.returncode}]")
        return "\n".join(parts)


def truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = max_chars * 2 // 3
    tail = max_chars - head
    return f"{text[:head]}\n[... {len(text) - max_chars:,} characters omitted ...]\n{text[-tail:]}"


# Limits are set inside the child by this wrapper rather than with preexec_fn, which is not
# safe when tools run from a thread pool.
_WRAPPER = (
    "import resource, sys\n"
    "cpu, mem = int(sys.argv[1]), int(sys.argv[2])\n"
    "resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 2))\n"
    "if mem > 0 and sys.platform.startswith('linux'):\n"
    "    resource.setrlimit(resource.RLIMIT_AS, (mem * 1048576, mem * 1048576))\n"
    "src = sys.stdin.read()\n"
    "sys.argv = ['agent_code']\n"
    "exec(compile(src, '<agent_code>', 'exec'), {'__name__': '__main__'})\n"
)


MAC_NO_NETWORK = "(version 1)(allow default)(deny network*)"
NETWORK_MODES = ("block", "container", "allow")


class NetworkIsolationError(RuntimeError):
    pass


def _prefix(network: str) -> list[str]:
    if network not in NETWORK_MODES:
        raise ValueError(f"network must be one of {NETWORK_MODES}")
    if network != "block":
        return []
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return ["sandbox-exec", "-p", MAC_NO_NETWORK]
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        return ["unshare", "-rn", "--"]
    raise NetworkIsolationError("no way to block the network for the Python tool on this machine; run inside a "
                                "container with --network none and set protocol.python_network: container")


def run_python(code: str, cwd: Path, timeout_s: float = 30.0, mem_limit_mb: int | None = 4096,
               network: str = "block") -> PythonResult:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(cwd),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MPLBACKEND": "Agg",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    start = time.monotonic()
    proc = subprocess.Popen(
        _prefix(network) + [sys.executable, "-I", "-c", _WRAPPER, str(int(timeout_s) + 5), str(mem_limit_mb or 0)],
        cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(code, timeout=timeout_s)
        return PythonResult(out, err, proc.returncode, False, time.monotonic() - start)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return PythonResult(out or "", err or "", None, True, time.monotonic() - start)


_PROBE = """
import socket
results = []
for host, port in (("1.1.1.1", 53), ("8.8.8.8", 443)):
    try:
        socket.create_connection((host, port), timeout=3).close()
        results.append(f"connected {host}:{port}")
    except OSError as e:
        results.append(f"blocked {host}:{port} ({type(e).__name__})")
try:
    socket.getaddrinfo("example.com", 443)
    results.append("dns resolved")
except OSError as e:
    results.append(f"dns blocked ({type(e).__name__})")
print("; ".join(results))
"""


def network_selftest(cwd: Path, network: str) -> str:
    """Run a probe through the sandbox; raise if the network is reachable in block/container mode."""
    if network == "allow":
        return "network allowed (no isolation requested)"
    try:
        res = run_python(_PROBE, cwd, timeout_s=20, network=network)
    except (FileNotFoundError, PermissionError) as e:
        raise NetworkIsolationError(f"cannot start the network-blocked sandbox: {e}") from e
    out = (res.stdout + res.stderr).strip()
    if res.returncode != 0 and "blocked" not in out:
        raise NetworkIsolationError(f"network-blocked sandbox failed to run Python: {out[:500]}")
    if "connected" in out or "dns resolved" in out:
        raise NetworkIsolationError(f"network is reachable from the Python tool ({network}): {out}")
    return out
