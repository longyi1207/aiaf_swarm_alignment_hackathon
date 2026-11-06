import pytest

torch = pytest.importorskip("torch")

from swarmtom.llm.hf import plan_batches  # noqa: E402


def test_every_index_once_sorted_and_capped():
    lengths = [500, 20000, 1200, 800, 15000, 3000, 900]
    b = plan_batches(lengths, max_rows=3, max_new_tokens=100, token_budget=None)
    flat = [i for x in b for i in x]
    assert sorted(flat) == list(range(len(lengths)))
    assert all(len(x) <= 3 for x in b)
    assert [lengths[i] for i in flat] == sorted(lengths)


def test_token_budget_limits_padded_tokens():
    lengths = [1000] * 10 + [20000] * 4
    b = plan_batches(lengths, max_rows=64, max_new_tokens=2048, token_budget=100_000)
    for x in b:
        assert len(x) == 1 or len(x) * (max(lengths[i] for i in x) + 2048) <= 100_000
    assert sorted(i for x in b for i in x) == list(range(14))


def test_single_row_over_budget_still_scheduled():
    b = plan_batches([50000], max_rows=8, max_new_tokens=2048, token_budget=10_000)
    assert b == [[0]]


def test_oom_retry_splits_and_recovers():
    from swarmtom.llm.base import GenRequest, GenResult
    from swarmtom.llm.hf import HFBackend

    b = HFBackend.__new__(HFBackend)
    b.device = torch.device("cpu")
    b.token_budget = None
    b._len_cache = {str(i): 100 for i in range(8)}
    calls = []

    def fake_batch(reqs, max_new_tokens):
        calls.append(len(reqs))
        if len(reqs) > 2:
            raise torch.OutOfMemoryError("fake")
        return [GenResult(key=r.key, content="ok") for r in reqs]

    b._generate_batch = fake_batch
    reqs = [GenRequest(key=str(i), messages=[], tools=[]) for i in range(8)]
    out = b._generate_split(reqs, 16)
    assert [r.key for r in out] == [str(i) for i in range(8)] and all(r.content == "ok" for r in out)
    assert calls[0] == 8 and max(calls[1:]) <= 4
    assert b.token_budget is not None and b.token_budget < 8 * (100 + 16)  # budget learned from the OOM
