"""T4.6: Articles I, I.a, II and II.b, enforced over the real source tree — the assertions
that turn the constitution from a document into a build failure."""

from __future__ import annotations

from tests.repo_files import python_files, relative
from tests.source_ast import has_main_block, imports_any

CLI_MODULE = "evals/cli.py"  # Article I.a's carve-out, named — never matched by pattern
COMMAND_LIBS = ("argparse", "click", "typer")
SUITE = ("evals/component/", "evals/behavior/", "tests/")


def _outside_the_cli_and_app(name: str) -> bool:
    return name != CLI_MODULE and not name.startswith("app/")


def test_only_the_named_cli_module_imports_a_command_line_library() -> None:
    """Article I: one entry point that is not pytest, and it is named, not matched."""
    offenders = [
        relative(path)
        for path in python_files()
        if _outside_the_cli_and_app(relative(path)) and imports_any(path, COMMAND_LIBS)
    ]
    assert offenders == []


def test_no_main_block_outside_app_and_the_cli() -> None:
    watched = [p for p in python_files() if _outside_the_cli_and_app(relative(p))]
    assert [relative(p) for p in watched if has_main_block(p)] == []


def test_the_suite_never_imports_the_operator_cli() -> None:
    """Article I.a / FR-044: pytest never reaches the module that rewrites thresholds."""
    offenders = [
        relative(path)
        for path in python_files()
        if relative(path).startswith(SUITE) and imports_any(path, ("evals.cli",))
    ]
    assert offenders == []


def test_the_two_eval_layers_never_import_each_other_or_the_other_framework() -> None:
    """Article II: two layers, never merged — checked as import edges, not folder names."""
    for path in python_files():
        name = relative(path)
        if name.startswith("evals/component/"):
            assert not imports_any(path, ("evals.behavior", "deepeval")), name
        if name.startswith("evals/behavior/"):
            assert not imports_any(path, ("evals.component", "ragas")), name


def test_no_adapter_module_imports_both_frameworks() -> None:
    """Article II.b: colocation is not spanning — one framework per adapter module."""
    for path in python_files():
        if relative(path).startswith("evals/adapters/"):
            assert not (imports_any(path, ("ragas",)) and imports_any(path, ("deepeval",)))
