"""OpenAI-compatible chat-completions backend (vLLM server, Azure, etc.). No lesions.

Useful for Phase 0 calibration of the no-lesion baseline on a fast server (e.g. vLLM with prefix
caching on the Spark), and for developing prompts against other models.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from swarmtom.llm.base import Backend, GenRequest, GenResult, ToolCall
from swarmtom.llm.parse import parse_output

log = logging.getLogger(__name__)


def _to_api(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        m2 = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            m2["tool_calls"] = [{"id": tc["id"], "type": "function",
                                 "function": {"name": tc["function"]["name"],
                                              "arguments": json.dumps(tc["function"]["arguments"])}}
                                for tc in m["tool_calls"]]
        if m["role"] == "tool":
            m2["tool_call_id"] = m["tool_call_id"]
        out.append(m2)
    return out


class OpenAICompatBackend(Backend):
    name = "openai_compat"
    supports_lesions = False

    def __init__(self, base_url: str, model: str, *, api_key_env: str | None = None, auth_header: str = "Authorization",
                 max_tokens: int = 2048, temperature: float = 0.6, top_p: float = 0.95, concurrency: int = 8,
                 timeout_s: float = 300, max_retries: int = 4, extra_body: dict | None = None):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = os.environ.get(api_key_env, "") if api_key_env else ""
        if api_key_env and not self.api_key:
            raise RuntimeError(f"environment variable {api_key_env} is not set")
        self.auth_header = auth_header
        self.max_tokens, self.temperature, self.top_p = max_tokens, temperature, top_p
        self.concurrency, self.timeout_s, self.max_retries = concurrency, timeout_s, max_retries
        self.extra_body = extra_body or {}

    def describe(self) -> dict:
        return {"name": self.name, "url": self.url, "model": self.model, "max_tokens": self.max_tokens,
                "temperature": self.temperature, "top_p": self.top_p, "extra_body": self.extra_body}

    def generate(self, requests: list[GenRequest]) -> list[GenResult]:
        for r in requests:
            if r.lesion != "none":
                raise ValueError("openai_compat backend cannot apply lesions; use the hf backend")
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            return list(pool.map(self._one, requests))

    def _one(self, req: GenRequest) -> GenResult:
        body = {"model": self.model, "messages": _to_api(req.messages), "max_tokens": self.max_tokens,
                "temperature": self.temperature, "top_p": self.top_p, **self.extra_body}
        if req.tools:
            body["tools"] = req.tools
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers[self.auth_header] = f"Bearer {self.api_key}" if self.auth_header == "Authorization" else self.api_key
        last = ""
        for attempt in range(self.max_retries + 1):
            try:
                rq = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(rq, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read())
                return self._parse(req.key, data)
            except urllib.error.HTTPError as e:
                last = f"HTTP {e.code}: {e.read()[:300]!r}"
                if e.code not in (408, 409, 429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = f"{type(e).__name__}: {e}"
            time.sleep(min(60, 2 ** attempt))
        log.error("request %s failed: %s", req.key, last)
        return GenResult(key=req.key, error=last)

    def _parse(self, key: str, data: dict) -> GenResult:
        msg = data["choices"][0]["message"]
        usage = data.get("usage", {})
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        calls, errors = [], []
        for tc in msg.get("tool_calls") or []:
            try:
                args = tc["function"].get("arguments") or "{}"
                calls.append(ToolCall(tc["function"]["name"], json.loads(args) if isinstance(args, str) else args,
                                      tc.get("id", "")))
            except (json.JSONDecodeError, KeyError) as e:
                errors.append(f"bad tool call from API: {e}")
        if not calls and "<tool_call>" in content:  # server without a tool parser
            r2, content, calls, errors = parse_output(content)
            reasoning = reasoning or r2
        return GenResult(key=key, content=content, reasoning=reasoning, tool_calls=calls,
                         raw=json.dumps(msg, ensure_ascii=False), prompt_tokens=usage.get("prompt_tokens", 0),
                         completion_tokens=usage.get("completion_tokens", 0), parse_errors=errors)
