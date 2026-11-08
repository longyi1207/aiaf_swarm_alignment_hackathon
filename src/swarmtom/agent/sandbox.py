"""The run_python tool: run agent code in a fresh, isolated interpreter inside its workspace.

Isolation (proportionate to a local open-weight model analysing spreadsheets):
- filesystem access: workspace read/write, interpreter/runtime read-only. macOS uses
  sandbox-exec; Linux requires Landlock ABI >= 3. Unsupported hosts fail closed;
- `python -I`: no PYTHONPATH, no user site, and the working directory is NOT on sys.path,
  so files the agent writes cannot shadow imports;
- a minimal environment (no credentials are inherited);
- wall-clock timeout, CPU-time limit, and on Linux an address-space limit;
- its own process group, killed as a whole on timeout;
- output truncated (head and tail kept);
- network blocked (`network="block"`): `sandbox-exec` deny-network profile on macOS, `unshare -rn`
  (a fresh network namespace with no interfaces) on Linux. Where neither works (e.g. Ubuntu with
  unprivileged user namespaces restricted), run the whole job in a container started with
  `--network none` and set `network="container"`. `network_selftest` proves the block before a run;
- `network="audit"`: for hosts that are themselves unprivileged containers (e.g. RunPod), where
  neither OS-level option is available. A Python audit hook installed before the agent code runs
  refuses socket creation/connection/DNS and process spawning. This is weaker than an OS-level
  block: code that reaches libc directly (e.g. through ctypes, which cannot be blocked because
  numpy/pandas load shared libraries with it on Linux) could bypass it. It stops the ordinary ways
  Python code reaches the network, and the self-test verifies it.
"""

from __future__ import annotations

import os
import json
from functools import lru_cache
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


# Filesystem restrictions are enforced by the OS, including native libc file access.
_LANDLOCK = Path(__file__).with_name("_landlock.py").read_text()

# Limits are set inside the child by this wrapper rather than with preexec_fn, which is not
# safe when tools run from a thread pool.
_WRAPPER = (
    "import resource, sys, json\n"
    "if sys.platform.startswith('linux'):\n"
    "    exec(sys.argv[5], globals())\n"
    "    restrict_filesystem(sys.argv[4], json.loads(sys.argv[6]))\n"
    "cpu, mem, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]\n"
    "if mode == 'audit':\n"
    "    _BLOCK = ('socket.__new__', 'socket.connect', 'socket.bind', 'socket.getaddrinfo', 'socket.gethostbyname',\n"
    "              'socket.gethostbyaddr', 'socket.sendto', 'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn',\n"
    "              'os.spawn', 'os.fork', 'os.forkpty', 'pty.spawn')\n"
    "    def _hook(event, args):\n"
    "        if event in _BLOCK:\n"
    "            raise PermissionError(f'{event} is not allowed in this sandbox')\n"
    "    sys.addaudithook(_hook)\n"
    "resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 2))\n"
    "if mem > 0 and sys.platform.startswith('linux'):\n"
    "    resource.setrlimit(resource.RLIMIT_AS, (mem * 1048576, mem * 1048576))\n"
    "src = sys.stdin.read()\n"
    "sys.argv = ['agent_code']\n"
    "exec(compile(src, '<agent_code>', 'exec'), {'__name__': '__main__'})\n"
)


MAC_NO_NETWORK = "(version 1)(allow default)(deny network*)"

def _tool_python() -> str:
    """Interpreter for the agents' run_python tool. SWARMTOM_TOOL_PYTHON pins it (e.g. the vLLM venv
    runs games but the tool keeps the original environment's pandas / openpyxl versions)."""
    return os.environ.get("SWARMTOM_TOOL_PYTHON") or sys.executable

NETWORK_MODES = ("block", "audit", "container", "allow")


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



@lru_cache(maxsize=4)
def _runtime_paths(interpreter: str) -> list[str]:
    probe = subprocess.run([interpreter, "-I", "-c",
        "import json,sys,mimetypes; print(json.dumps([sys.prefix,sys.base_prefix,*sys.path,*mimetypes.knownfiles]))"],
        check=True, capture_output=True, text=True, timeout=20)
    paths = json.loads(probe.stdout)
    paths += ["/System", "/Library/Apple", "/usr", "/private/var/db/dyld", "/usr/lib", "/usr/local/lib", "/lib", "/lib64",
              "/usr/share/zoneinfo", "/dev/null", "/dev/urandom", "/dev/random",
              "/etc/ld.so.cache", "/etc/localtime", "/etc/hosts", "/etc/resolv.conf", "/etc/nsswitch.conf"]
    return sorted({str(Path(p).resolve()) for p in paths if p and Path(p).exists()})


def _sandbox_prefix(network: str, cwd: Path, read_paths: list[str]) -> list[str]:
    if sys.platform == "darwin":
        if not shutil.which("sandbox-exec"):
            raise NetworkIsolationError("sandbox-exec is required for filesystem isolation on macOS")
        # Metadata is needed for import/path traversal; file contents and directory listings
        # outside the allowlist remain denied. JSON quoting also escapes spaces/quotes in paths.
        reads = " ".join(f"(subpath {json.dumps(p)})" for p in [*read_paths, str(cwd)])
        parents = {str(parent) for p in [*read_paths, str(cwd)] for parent in Path(p).parents}
        reads += " " + " ".join(f"(literal {json.dumps(p)})" for p in sorted(parents))
        profile = ("(version 1)(allow default)"
                   f"(deny file-read-data (require-not (require-any {reads})))"
                   f"(deny file-write* (require-not (subpath {json.dumps(str(cwd))})))")
        if network == "block":
            profile += "(deny network*)"
        return ["sandbox-exec", "-p", profile]
    if sys.platform.startswith("linux"):
        return _prefix(network)  # Landlock is installed by the child before agent code.
    raise NetworkIsolationError("OS filesystem isolation is supported only on macOS and Linux")

def preferred_network() -> str:
    """The strongest isolation this host supports: an OS-level block if it works here, else 'audit'."""
    try:
        prefix = _prefix("block")
        r = subprocess.run(prefix + [_tool_python(), "-c", "pass"], capture_output=True, timeout=20)
        return "block" if r.returncode == 0 else "audit"
    except (NetworkIsolationError, OSError, subprocess.TimeoutExpired):
        return "audit"


def run_python(code: str, cwd: Path, timeout_s: float = 30.0, mem_limit_mb: int | None = 4096,
               network: str = "block") -> PythonResult:
    if network not in NETWORK_MODES:
        raise ValueError(f"network must be one of {NETWORK_MODES}")
    cwd = cwd.resolve()
    read_paths = _runtime_paths(_tool_python())
    scratch = cwd / ".tmp"
    scratch.mkdir(exist_ok=True)
    if cwd not in scratch.resolve().parents:
        raise ValueError("workspace scratch directory may not escape the workspace")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(cwd),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "MPLBACKEND": "Agg",
        "TMPDIR": str(scratch),
        "MPLCONFIGDIR": str(scratch / "matplotlib"),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    start = time.monotonic()
    proc = subprocess.Popen(
        _sandbox_prefix(network, cwd, read_paths) + [_tool_python(), "-I", "-c", _WRAPPER,
                            str(int(timeout_s) + 5), str(mem_limit_mb or 0), network, str(cwd),
                            _LANDLOCK, json.dumps(read_paths)],
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


def filesystem_selftest(cwd: Path, network: str) -> str:
    """Prove both Python and native reads cannot reach a sibling answer-key sentinel."""
    import tempfile
    cwd.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cwd.parent, prefix=".fsprobe-") as td:
        outside = Path(td) / "answer_key.txt"
        outside.write_text("outside-workspace-sentinel")
        link = cwd / ".fsprobe-link"
        link.symlink_to(outside)
        try:
            code = f"""
import ctypes, os
for path in ({str(outside)!r}, '.fsprobe-link'):
    try:
        open(path).read()
        raise RuntimeError('outside read succeeded')
    except PermissionError:
        pass
libc = ctypes.CDLL(None)
fd = libc.open({str(outside).encode()!r}, 0)
if fd >= 0:
    os.close(fd)
    raise RuntimeError('native outside read succeeded')
open('.fsprobe-inside', 'w').write('ok')
print('filesystem isolated')
"""
            result = run_python(code, cwd, network=network)
            if result.returncode != 0 or result.stdout.strip() != "filesystem isolated":
                raise NetworkIsolationError("filesystem self-test failed: " + (result.stderr + result.stdout)[:1000])
            return result.stdout.strip()
        finally:
            link.unlink(missing_ok=True)
            (cwd / ".fsprobe-inside").unlink(missing_ok=True)


def tool_environment() -> dict:
    """Record the separately configured tool interpreter and spreadsheet-library versions."""
    code = """
import importlib.metadata as m,json,sys
versions={}
for name in ('numpy','pandas','openpyxl','python-docx'):
    try: versions[name]=m.version(name)
    except m.PackageNotFoundError: versions[name]=None
print(json.dumps({'executable':sys.executable,'python':sys.version,'packages':versions}))
"""
    result = subprocess.run([_tool_python(), '-I', '-c', code], capture_output=True, text=True, check=True, timeout=20)
    return json.loads(result.stdout)
