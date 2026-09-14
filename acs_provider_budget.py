"""Optional request budget, enabled only inside a dedicated proposal worker."""
from contextlib import contextmanager
from contextvars import ContextVar

_budget = ContextVar("acs_provider_request_budget", default=None)


def active():
    return _budget.get() is not None


def consume():
    budget = _budget.get()
    if budget is None:
        return
    if budget["used"] >= budget["limit"]:
        import acs_api_errors as E
        raise E.AcsApiError(E.ACS_PROVIDER_BUDGET_EXHAUSTED, retryable=False)
    budget["used"] += 1


@contextmanager
def limited(limit):
    if type(limit) is not int or not 1 <= limit <= 12:
        raise ValueError("Invalid proposal request budget")
    budget = {"limit": limit, "used": 0}
    token = _budget.set(budget)
    try:
        yield budget
    finally:
        _budget.reset(token)
