#!/usr/bin/env python3
"""Create, inspect, stop and delete the experiment's RunPod GPU pod (REST API v1).

The API key is read from RUNPOD_API_KEY in the ai_notes repo-root .env (or $RUNPOD_ENV_FILE) and is
never printed. Pod details are cached in runs/pod.json (gitignored).

    python scripts/runpod.py create      # H100 80GB, waits until SSH is reachable
    python scripts/runpod.py status      # state, $/hr, uptime, spend so far
    python scripts/runpod.py ssh-cmd     # prints the ssh command
    python scripts/runpod.py stop|start|delete
"""

from __future__ import annotations

import datetime as dt
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path(os.environ.get("RUNPOD_ENV_FILE", ROOT.parents[1] / ".env"))
STATE = Path(os.environ.get("POD_STATE", ROOT / "runs" / "pod.json"))  # POD_STATE selects a second pod
API = "https://rest.runpod.io/v1"
SSH_KEY = Path.home() / ".ssh" / "runpod_swarmtom"
GPU_TYPES = ["NVIDIA H100 80GB HBM3", "NVIDIA H100 NVL", "NVIDIA H100 PCIe"]
IMAGE = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"


def _key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.strip().startswith("RUNPOD_API_KEY="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            if v:
                return v
    sys.exit(f"RUNPOD_API_KEY not found in {ENV_FILE}")


def _req(method: str, path: str, body: dict | None = None) -> dict | list | None:
    data = json.dumps(body).encode() if body is not None else None
    rq = urllib.request.Request(API + path, data=data, method=method,
                                headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json",
                                         # RunPod's edge rejects the default Python-urllib agent (HTTP 403)
                                         "User-Agent": "swarmtom-runpod-client/0.1"})
    try:
        with urllib.request.urlopen(rq, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"RunPod API {method} {path} failed: HTTP {e.code} {e.read()[:500]!r}")


def _save(pod: dict) -> None:
    STATE.parent.mkdir(exist_ok=True)
    keep = {k: pod.get(k) for k in ("id", "name", "desiredStatus", "costPerHr", "adjustedCostPerHr", "publicIp",
                                    "portMappings", "lastStartedAt", "lastStatusChange", "gpu", "machine")}
    old = json.loads(STATE.read_text()) if STATE.exists() else {}
    keep["created_local"] = old.get("created_local") or dt.datetime.now().isoformat(timespec="seconds")
    STATE.write_text(json.dumps(keep, indent=2, default=str))


def _pod_id() -> str:
    if not STATE.exists():
        sys.exit("no pod recorded in runs/pod.json")
    return json.loads(STATE.read_text())["id"]


def _ssh_ready(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=5) as s:
            return s.recv(64).startswith(b"SSH-")
    except OSError:
        return False


def create() -> None:
    if STATE.exists() and json.loads(STATE.read_text()).get("id"):
        sys.exit(f"a pod is already recorded in {STATE}; delete it first")
    pub = (SSH_KEY.with_suffix(".pub")).read_text().strip()
    body = {"name": "swarmtom-h100", "imageName": IMAGE, "gpuTypeIds": GPU_TYPES, "gpuTypePriority": "custom",
            "gpuCount": 1, "cloudType": "SECURE", "containerDiskInGb": 80, "volumeInGb": 120,
            "volumeMountPath": "/workspace", "ports": ["22/tcp"], "env": {"PUBLIC_KEY": pub},
            "minRAMPerGPU": 64, "minVCPUPerGPU": 8}
    pod = _req("POST", "/pods", body)
    _save(pod)
    print(f"created pod {pod['id']} at ${pod.get('costPerHr')}/hr; waiting for SSH...", flush=True)
    for _ in range(120):
        time.sleep(10)
        pod = _req("GET", f"/pods/{pod['id']}")
        _save(pod)
        ip, ports = pod.get("publicIp"), pod.get("portMappings") or {}
        if ip and "22" in ports and _ssh_ready(ip, int(ports["22"])):
            print(json.dumps({"id": pod["id"], "ip": ip, "ssh_port": ports["22"], "costPerHr": pod.get("costPerHr"),
                              "gpu": (pod.get("gpu") or {}).get("displayName")}))
            return
    sys.exit("pod did not become reachable over SSH within 20 minutes")


def status() -> None:
    pod = _req("GET", f"/pods/{_pod_id()}")
    _save(pod)
    st = json.loads(STATE.read_text())
    start = dt.datetime.fromisoformat(st["created_local"])
    hours = (dt.datetime.now() - start).total_seconds() / 3600
    rate = float(pod.get("adjustedCostPerHr") or pod.get("costPerHr") or 0)
    print(json.dumps({"id": pod["id"], "status": pod.get("desiredStatus"), "costPerHr": rate,
                      "hours_since_create": round(hours, 2), "approx_spend_usd": round(hours * rate, 2),
                      "lastStatusChange": pod.get("lastStatusChange")}))


def ssh_cmd() -> None:
    st = json.loads(STATE.read_text())
    print(f"ssh -i {SSH_KEY} -o StrictHostKeyChecking=accept-new -p {st['portMappings']['22']} root@{st['publicIp']}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "create":
        create()
    elif cmd == "status":
        status()
    elif cmd == "ssh-cmd":
        ssh_cmd()
    elif cmd in ("stop", "start"):
        _req("POST", f"/pods/{_pod_id()}/{cmd}")
        status()
    elif cmd == "delete":
        _req("DELETE", f"/pods/{_pod_id()}")
        STATE.rename(STATE.with_suffix(f".deleted-{int(time.time())}.json"))
        print("deleted")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
