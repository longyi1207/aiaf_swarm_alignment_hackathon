"""Exercise real request grouping/cache salts without installing vLLM or loading weights."""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from swarmtom.llm.base import GenRequest
from swarmtom.llm.vllm_backend import VLLMBackend, _LesionState


class Tokenizer:
    def __call__(self, text, **kwargs):
        return {'input_ids': [11, 12, 13]}

    def decode(self, ids, **kwargs):
        return str(ids[0]) if ids else ''


class FakeEngine:
    def __init__(self, state):
        self.state = state
        self.cache = {}
        self.seeds = []
        self.fail = False

    def generate(self, prompts, params, **kwargs):
        if self.fail:
            raise RuntimeError('engine failed')
        self.seeds += [p.seed for p in params]
        result = []
        for p in prompts:
            # Without a condition salt this intentionally reproduces the historical contamination.
            key = (tuple(p['prompt_token_ids']), p.get('cache_salt'))
            token = self.cache.setdefault(key, {'none': 1, 'tom': 2, 'emp': 3}[self.state.active])
            result.append(SimpleNamespace(outputs=[SimpleNamespace(token_ids=[token])]))
        return result


@pytest.fixture
def backend(monkeypatch):
    vllm = ModuleType('vllm')
    vllm.SamplingParams = lambda **kwargs: SimpleNamespace(**kwargs)
    inputs = ModuleType('vllm.inputs')
    inputs.TokensPrompt = dict
    monkeypatch.setitem(sys.modules, 'vllm', vllm)
    monkeypatch.setitem(sys.modules, 'vllm.inputs', inputs)
    b = VLLMBackend.__new__(VLLMBackend)
    b.enable_prefix_caching = True
    b.seed, b._calls, b.temperature, b.top_p = 7, 0, 0.6, .95
    b.max_new_tokens, b.max_prompt_tokens = 10, 100
    b.stop_ids, b.uses_lesions = [], True
    b.lesions = _LesionState({'tom': [], 'emp': []})
    b.tokenizer = Tokenizer()
    b.render = lambda request: 'identical shared prefix'
    b.llm = FakeEngine(b.lesions)
    return b


def req(condition):
    return GenRequest(key=f'game/{condition}', messages=[], tools=[], lesion=condition)


def test_only_length_capped_unclosed_thought_is_hidden(backend):
    backend.render = lambda _: 'assistant\n<think>\n'
    raw = 'Thinking of <tool_call>{"name":"end_turn","arguments":{}}</tool_call>'
    backend.tokenizer.decode = lambda ids, **kwargs: raw
    [capped] = backend.generate([req('none')], max_new_tokens=1)
    assert capped.reasoning == capped.raw == raw and capped.content == '' and capped.tool_calls == []
    [natural_stop] = backend.generate([req('none')], max_new_tokens=2)
    assert [call.name for call in natural_stop.tool_calls] == ['end_turn']
    backend.render = lambda _: 'assistant\n<think>\n\n</think>\n\n'
    [plain] = backend.generate([req('none')], max_new_tokens=1)
    assert [call.name for call in plain.tool_calls] == ['end_turn']


def test_identical_prompts_never_share_states_between_conditions(backend):
    for conditions in (['none', 'tom', 'emp'], ['emp', 'tom', 'none'], ['tom', 'none']):
        results = backend.generate([req(c) for c in conditions])
        assert [r.raw for r in results] == [str({'none': 1, 'tom': 2, 'emp': 3}[c]) for c in conditions]
    assert {salt for _, salt in backend.llm.cache} == {'lesion:none', 'lesion:tom', 'lesion:emp'}


def test_request_seed_is_independent_of_restart_batch_and_group_order(backend):
    first = backend.generate([req('tom')])[0]
    seed = backend.llm.seeds[-1]
    backend.generate([req('emp'), req('none')])
    backend._calls = 0  # what a resumed process does
    assert backend.generate([req('tom')])[0].raw == first.raw
    assert backend.llm.seeds[-1] == seed
    assert backend._seed_for('game/tom', [11, 12, 14]) != seed


def test_active_condition_is_reset_after_engine_failure(backend):
    backend.llm.fail = True
    with pytest.raises(RuntimeError, match='engine failed'):
        backend.generate([req('tom')])
    assert backend.lesions.active == 'none'


def test_unknown_condition_is_rejected(backend):
    with pytest.raises(KeyError):
        backend.generate([req('unknown')])
