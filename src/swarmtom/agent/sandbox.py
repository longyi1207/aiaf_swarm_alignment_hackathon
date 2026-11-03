"""The run_python tool: run agent code in a fresh, isolated interpreter inside its workspace.

Isolation (proportionate to a local open-weight model analysing spreadsheets):
- `python -I`: no PYTHONPATH, no user site, and the working directory is NOT on sys.path,
  so files the agent writes cannot shadow imports;
- a minimal environment (no credentials are inherited);
- wall-clock timeout, CPU-time limit, and on Linux an address-space limit;
- its own process group, killed as a whole on timeout;
- output truncated (head and tail kept).
Network access is not blocked at this layer; run games inside a container without network
(see docs/运行指南.md) when that matters.
"""

from __future__ import annotations

import os
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


def run_python(code: str, cwd: Path, timeout_s: float = 30.0, mem_limit_mb: int | None = 4096) -> PythonResult:
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
        [sys.executable, "-I", "-c", _WRAPPER, str(int(timeout_s) + 5), str(mem_limit_mb or 0)],
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
