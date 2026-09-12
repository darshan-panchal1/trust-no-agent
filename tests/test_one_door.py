"""T4.6: the single-door rules — Article VI.a's metric factory, Article III's write path,
and Article XI's `run_async` discipline, each asserted over the source rather than trusted.
"""

from __future__ import annotations

from tests.repo_files import python_files, relative
from tests.source_ast import calls_named, calls_with_keyword, imports_any

JUDGE_PACKAGE = "evals/judge/"
METRIC_CLASSES = {"GEval", "ToolCorrectnessMetric", "AnthropicModel"}

# Article III's write path, by name. `==` not `<=`: this fails both when an unsanctioned
# writer appears and when a sanctioned one quietly stops being one.
SANCTIONED_WRITERS = {
    "app/generate.py",  # the generator's live branch (T1.7)
    "evals/cache/ragas_backend.py",  # RagasCacheBackend live mode (T2.1)
    "evals/judge/cached.py",  # CachedJudge live mode (T3.1/T3.2)
    "tests/test_cache_store.py",  # T1.4's acceptance test, against an isolated tmp cache
}

RUN_ASYNC_CALLERS = {"conftest.py", "tests/test_harness_integrity.py"}


def test_no_deepeval_metric_is_constructed_outside_the_judge_package() -> None:
    """Article VI.a: one door. A bare `SomeMetric()` anywhere else is a violation."""
    offenders = [
        f"{relative(path)}:{name}"
        for path in python_files()
        if not relative(path).startswith(JUDGE_PACKAGE)
        for name in calls_named(path, METRIC_CLASSES)
    ]
    assert offenders == []


def test_read_or_call_is_reachable_only_from_sanctioned_writers() -> None:
    """Article III / FR-048: `evals/ops/record.py` is deliberately absent — it orchestrates
    the live passes rather than writing entries itself, so it never touches this path."""
    callers = {relative(path) for path in python_files() if calls_named(path, {"read_or_call"})}
    assert callers == SANCTIONED_WRITERS


def test_run_async_is_passed_in_exactly_two_places() -> None:
    """Article XI: disabled in one place (conftest), reproduced in one (the integrity test).
    Asked as "which files *pass* run_async=", not "which mention it": `evals/ragas_llm.py`
    explains the defence in prose and must not count as practising it."""
    passers = {relative(p) for p in python_files() if calls_with_keyword(p, "run_async")}
    assert passers == RUN_ASYNC_CALLERS


def test_behaviour_tests_reach_assert_test_through_the_conftest_wrapper() -> None:
    """Anything calling deepeval's own `assert_test` bypasses the run_async=False defence."""
    offenders = [
        relative(path)
        for path in python_files()
        if relative(path).startswith("evals/behavior/")
        and imports_any(path, ("deepeval.evaluate",))
    ]
    assert offenders == []
