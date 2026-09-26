"""Article II.c (Eleventh amendment): exactly one routing facade reaches both eval layers,
named rather than matched — Article I.a's discipline. The cross-layer set binds now; the
no-framework rule binds each named module from the moment it exists."""

from __future__ import annotations

from tests.repo_files import python_files, relative
from tests.source_ast import imports_any

FACADE = "trustnoagent/evaluators.py"
# Operator orchestration that imported both layers before any article named the permission.
PRE_EXISTING = {"evals/ops/coverage.py", "evals/ops/record.py"}
CONTRACT_MODULES = {
    "evals/contract.py",
    "evals/evaluator.py",
    "evals/failures.py",
    "evals/judge_config.py",
    "evals/fingerprint.py",
    "evals/outcomes.py",
    "evals/rubric.py",
    "evals/rubric_verdict.py",
}
FRAMEWORKS = ("ragas", "deepeval")


def test_only_named_modules_import_both_eval_layers() -> None:
    """Checked over every first-party module, tests included: a test needing both layers
    goes through the facade, never around it."""
    both = {
        relative(path)
        for path in python_files()
        if imports_any(path, ("evals.component",)) and imports_any(path, ("evals.behavior",))
    }
    assert both - PRE_EXISTING - {FACADE} == set()


def test_the_facade_and_contract_modules_import_no_framework() -> None:
    """The facade routes and the contract types are plain values — no framework type ever
    crosses from one layer to the other through either."""
    watched = CONTRACT_MODULES | {FACADE}
    offenders = [
        relative(path)
        for path in python_files()
        if relative(path) in watched and imports_any(path, FRAMEWORKS)
    ]
    assert offenders == []
