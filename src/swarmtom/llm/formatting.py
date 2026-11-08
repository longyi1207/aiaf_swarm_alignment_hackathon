"""Chat formatting and stop-token helpers shared by backends (no model dependencies)."""

STOP_TOKENS = ("<|im_end|>", "<|endoftext|>", "<|im_start|>", "<|eot_id|>", "</s>")


def stop_token_ids(tokenizer, model_eos) -> list[int]:
    """Every id that ends an assistant turn.

    Qwen3.5-9B ships no generation_config.json and its model config lists only <|endoftext|> as EOS,
    while chat turns end with <|im_end|> (the tokenizer's EOS). Without this, generation runs past the
    end of the turn and invents further turns until max_new_tokens.
    """
    ids: set[int] = set()
    for x in ([model_eos] if isinstance(model_eos, int) else list(model_eos or [])) + [tokenizer.eos_token_id]:
        if isinstance(x, int):
            ids.add(x)
    unk = getattr(tokenizer, "unk_token_id", None)
    for tok in STOP_TOKENS:
        tid = tokenizer.convert_tokens_to_ids(tok)
        if isinstance(tid, int) and tid >= 0 and tid != unk:
            ids.add(tid)
    return sorted(ids)


def cut_at_stop(ids: list[int], stop_ids: set[int]) -> list[int]:
    for i, t in enumerate(ids):
        if t in stop_ids:
            return ids[:i]
    return ids


def _for_template(messages: list[dict]) -> list[dict]:
    """Chat templates expect tool-call arguments as dicts and no extra keys."""
    out = []
    for m in messages:
        m2 = {"role": m["role"], "content": m.get("content") or ""}
        if m.get("tool_calls"):
            m2["tool_calls"] = [{"type": "function", "function": {"name": tc["function"]["name"],
                                                                  "arguments": tc["function"]["arguments"]}}
                                for tc in m["tool_calls"]]
        if m["role"] == "tool":
            m2["name"] = m.get("name", "")
        out.append(m2)
    return out
