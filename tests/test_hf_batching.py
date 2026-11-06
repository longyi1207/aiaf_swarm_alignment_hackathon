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
