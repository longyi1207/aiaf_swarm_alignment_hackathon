"""Turn-ending tokens (no torch needed: the helpers take plain ids)."""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from swarmtom.llm.hf import cut_at_stop, stop_token_ids  # noqa: E402


class _Tok:
    """Qwen3.5-9B's actual ids: model config EOS = <|endoftext|>, tokenizer EOS = <|im_end|>."""

    vocab = {"<|im_end|>": 248046, "<|endoftext|>": 248044, "<|im_start|>": 248045}
    eos_token_id = 248046
    unk_token_id = None

    def convert_tokens_to_ids(self, tok):
        return self.vocab.get(tok)


def test_qwen35_turn_end_is_a_stop_even_though_model_eos_is_endoftext():
    ids = stop_token_ids(_Tok(), 248044)
    assert {248046, 248044, 248045} <= set(ids)


def test_cut_at_first_stop():
    assert cut_at_stop([5, 6, 248046, 248045, 9], {248046, 248045}) == [5, 6]
    assert cut_at_stop([5, 6], {1}) == [5, 6]
