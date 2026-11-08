"""Run inference in a long-lived child (e.g. ssh + docker exec), keeping tools on the controller."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from swarmtom.llm.base import Backend, GenRequest, GenResult, ToolCall


class StdioBackend(Backend):
    name = "vllm_stdio"
    supports_lesions = True

    def __init__(self, command: list[str], *, model_config: dict, lesions_file: str):
        if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
            raise ValueError("stdio command must be a nonempty argv list")
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        encoding="utf-8", bufsize=1)
        try:
            info = self._exchange({"backend": model_config, "lesions_file": lesions_file})
            self.description = info["description"]
            self.lesions = SimpleNamespace(conditions=dict.fromkeys(info["conditions"]))
        except BaseException:
            self.close()
            raise

    def _exchange(self, payload):
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"Inference worker disconnected (exit {self.process.poll()})")
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(f"Inference worker: {response['error']}")
        return response["value"]

    def describe(self):
        return {"name": self.name, "worker": self.description}

    def generate(self, requests, max_new_tokens=None):
        batch = []
        for request in requests:
            batch.append({"key": request.key, "messages": request.messages, "tools": request.tools,
                          "lesion": request.lesion,
                          "meta": {k:v for k,v in request.meta.items() if k == "enable_thinking"}})
        values = self._exchange({"requests": batch, "max_new_tokens": max_new_tokens})
        if [r["key"] for r in values] != [r.key for r in requests]:
            raise RuntimeError("Inference worker returned different request keys")
        return [GenResult(**{**r, "tool_calls": [ToolCall(**c) for c in r["tool_calls"]]}) for r in values]

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdout.close()


def serve():
    # Native engine output goes to stderr too. Reserve a separate FD for protocol responses.
    wire = os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    from swarmtom.llm.vllm_backend import VLLMBackend
    from swarmtom.run.provenance import runtime_versions
    engine = None
    try:
        spec = json.loads(sys.stdin.readline())
        root = Path.cwd().resolve()
        config = spec["backend"]
        lesions = (root / spec["lesions_file"]).resolve()
        if not lesions.is_relative_to(root):
            raise ValueError("lesions_file must be inside the worker checkout")
        engine = VLLMBackend(config.pop("model"), repo_root=root, lesions_config=lesions, **config)
        info = {"description": {**engine.describe(), "packages": runtime_versions()},
                "conditions": list(engine.lesions.conditions)}
        wire.write(json.dumps({"value":info}) + "\n")
        for line in sys.stdin:
            msg = json.loads(line)
            results = engine.generate([GenRequest(**r) for r in msg["requests"]], msg["max_new_tokens"])
            wire.write(json.dumps({"value":[asdict(r) for r in results]}, separators=(",", ":")) + "\n")
    except Exception as error:
        wire.write(json.dumps({"error":str(error)}) + "\n")
        raise
    finally:
        if engine is not None:
            engine.close()
        wire.close()


if __name__ == "__main__":
    serve()
