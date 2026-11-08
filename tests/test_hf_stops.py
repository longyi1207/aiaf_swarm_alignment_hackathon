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


def test_hf_capped_thinking_prefill_does_not_reenter_history():
    from types import SimpleNamespace
    from swarmtom.llm.base import GenRequest
    from swarmtom.llm.hf import HFBackend

    raw = 'Consider a possible call: <tool_call>{"name":"end_turn","arguments":{}}</tool_call>'

    class Tokens:
        pad_token_id = 0

        def __call__(self, texts, **kwargs):
            return {'input_ids': torch.tensor([[3]]), 'attention_mask': torch.tensor([[1]])}

        def decode(self, ids, **kwargs):
            return raw

    b = HFBackend.__new__(HFBackend)
    b.device = torch.device('cpu')
    b.seed, b._calls, b.max_prompt_tokens, b.temperature, b.stop_ids = 0, 0, 10, 0, [1]
    b.render = lambda req: 'assistant\n<think>\n'
    b.tokenizer = Tokens()
    b.model = SimpleNamespace(generate=lambda **kwargs: torch.tensor([[3, 4, 5]]))
    b.lesions = SimpleNamespace(set_rows=lambda rows: None)
    [result] = b._generate_batch([GenRequest('sample', [], [])], max_new_tokens=2)
    assert result.raw == result.reasoning == raw
    assert result.content == '' and result.tool_calls == [] and result.completion_tokens == 2
