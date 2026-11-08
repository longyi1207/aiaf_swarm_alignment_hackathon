"""Parse raw model text into reasoning, visible content and tool calls.

Supports the two Qwen tool-call formats:
    <tool_call>{"name": "...", "arguments": {...}}</tool_call>                  (Qwen2.5 / Qwen3)
    <tool_call><function=NAME><parameter=KEY>VALUE</parameter>...</function></tool_call>  (Qwen3-Coder style)
and a <think>...</think> reasoning block (the opening tag may live in the prompt).
"""

from __future__ import annotations

import json
import re

from swarmtom.llm.base import ToolCall

_TOOL_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", re.S)
_XML_FN = re.compile(r"<function=([^>\s]+)>\s*(.*?)\s*</function>", re.S)
_XML_PARAM = re.compile(r"<parameter=([^>\s]+)>\s*(.*?)\s*</parameter>", re.S)
_SPECIAL = ("<|im_end|>", "<|endoftext|>", "<|im_start|>", "</s>", "<eos>")
REASONING_HISTORY_POLICY = "hide_capped_unclosed_prefill_v1"


def _xml_value(v: str):
    v = v.strip()
    try:
        return json.loads(v)
    except (json.JSONDecodeError, ValueError):
        return v


def split_reasoning(text: str) -> tuple[str, str]:
    if "</think>" in text:
        head, tail = text.split("</think>", 1)
        return head.replace("<think>", "").strip(), tail
    if "<think>" in text:  # cut off while still thinking
        return text.split("<think>", 1)[1].strip(), ""
    return "", text


def parse_output(raw: str, *, capped_think_prefill: bool = False) -> tuple[str, str, list[ToolCall], list[str]]:
    """Return (reasoning, content, tool_calls, parse_errors)."""
    text = raw
    for tok in _SPECIAL:
        text = text.replace(tok, "")
    # Some chat templates put the opening tag in the prompt. At a length stop,
    # an unclosed thought must stay out of the next prompt and tool dispatcher.
    if capped_think_prefill and "</think>" not in text:
        return text.removeprefix("<think>").strip(), "", [], []
    reasoning, rest = split_reasoning(text)
    calls: list[ToolCall] = []
    errors: list[str] = []
    for block in _TOOL_BLOCK.findall(rest):
        block = block.strip()
        if not block:
            continue
        fn = _XML_FN.search(block)
        if fn:
            calls.append(ToolCall(fn.group(1), {k: _xml_value(v) for k, v in _XML_PARAM.findall(fn.group(2))}))
            continue
        try:
            obj = json.loads(block)
        except json.JSONDecodeError as e:
            errors.append(f"tool call is not valid JSON ({e.msg})")
            continue
        args = obj.get("arguments", obj.get("parameters", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                errors.append(f"arguments of {obj.get('name')} are not valid JSON")
                continue
        if not isinstance(obj.get("name"), str) or not isinstance(args, dict):
            errors.append("tool call needs a 'name' and an 'arguments' object")
            continue
        calls.append(ToolCall(obj["name"], args))
    content = _TOOL_BLOCK.sub("", rest).strip()
    return reasoning, content, calls, errors
