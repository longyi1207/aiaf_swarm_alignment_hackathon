"""Backend interface: turn a batch of conversations into assistant turns (with tool calls).

Internal message format is the OpenAI chat format, with tool-call arguments kept as dicts:
    {"role": "assistant", "content": str, "tool_calls": [{"id", "type": "function",
                                                         "function": {"name", "arguments": dict}}]}
    {"role": "tool", "tool_call_id": str, "name": str, "content": str}
Backends convert as their API or chat template needs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    arguments: dict
    id: str = ""


@dataclass
class GenRequest:
    key: str  # "<game_id>/<callsign>"
    messages: list[dict]
    tools: list[dict]
    lesion: str = "none"
    meta: dict = field(default_factory=dict)  # phase, workspace path...; used by scripted backends and logs


@dataclass
class GenResult:
    key: str
    content: str = ""
    reasoning: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    parse_errors: list[str] = field(default_factory=list)
    error: str | None = None  # backend failure for this row; the game retries the step
    cached_prompt_tokens: int | None = None


class Backend(ABC):
    name: str = "backend"
    supports_lesions: bool = False

    @abstractmethod
    def generate(self, requests: list[GenRequest]) -> list[GenResult]:
        """Return one result per request, in order. Must not raise for a single bad row."""

    def describe(self) -> dict:
        return {"name": self.name, "supports_lesions": self.supports_lesions}

    def close(self) -> None:
        pass
