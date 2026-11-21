import pytest
from pdrw_experience._ace_worker import CallBudget


def test_limiter_counts_and_blocks_entry_calls():
    budget = CallBudget(2)
    calls = []
    f = budget.guard(lambda i: calls.append(i) or i)
    assert f(1) == 1
    assert f(2) == 2
    with pytest.raises(RuntimeError, match="ACE_MODEL_CALL_CAP_REACHED"):
        f(3)
    assert calls == [1, 2]
    assert budget.used == 2


@pytest.mark.parametrize("limit", [0, 31, True, "3"])
def test_limiter_rejects_invalid_budget(limit):
    with pytest.raises(ValueError):
        CallBudget(limit)
