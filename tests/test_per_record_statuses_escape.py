"""US3's headline guarantee: NOTHING an evaluator raises escapes `evaluate()`, no failed result
carries a verdict, and a failure leaves no state behind — a leaked session breaks the next call."""

from __future__ import annotations

import pytest

from evals.cache import location, session
from evals.cache.session import FingerprintMismatch
from evals.cache.store import CacheMiss
from evals.contract import EvalRecord
from tests.per_record_support import golden_record
from trustnoagent import evaluate, evaluators

ID = "tna.ragas.faithfulness"
EXCEPTIONS: list[Exception] = [
    RuntimeError("r"), KeyError("k"), ValueError("v"), TypeError("t"), OSError("o"),
    ImportError("i"), AssertionError("a"), ZeroDivisionError("z"), AttributeError("x"),
    CacheMiss("cache miss for key 'abc' — no path"), FingerprintMismatch("k", "s", "e", "raw"),
]


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("exc", EXCEPTIONS, ids=lambda e: type(e).__name__)
def test_no_exception_escapes_and_no_state_leaks(
    exc: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_args: object) -> None:
        with session.begin("F", "ragas:x"):
            raise exc

    monkeypatch.setitem(evaluators.REGISTRY, ID, explode)
    result = evaluate(ID, EvalRecord(input="q", output="a", contexts=("c",)))
    assert result.status == "error" and result.error
    assert (result.score, result.label) == (None, None)
    assert type(exc).__name__ in result.error or isinstance(exc, (CacheMiss, FingerprintMismatch))
    assert location.current() is None
    monkeypatch.undo()  # a session that leaked would make this healthy call raise "nest"
    assert evaluate(ID, golden_record("v2_fixed", 0)[1]).status == "ok"


def test_a_message_is_capped_so_a_huge_provider_error_stays_readable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*_args: object) -> None:
        raise RuntimeError("x" * 5000)

    monkeypatch.setitem(evaluators.REGISTRY, ID, explode)
    result = evaluate(ID, EvalRecord(input="q", output="a", contexts=("c",)))
    assert result.error is not None and len(result.error) <= 500


def test_a_keyboard_interrupt_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The safety net catches `Exception`, never `BaseException`: Ctrl-C must still stop it."""
    def interrupt(*_args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setitem(evaluators.REGISTRY, ID, interrupt)
    with pytest.raises(KeyboardInterrupt):
        evaluate(ID, EvalRecord(input="q", output="a", contexts=("c",)))
