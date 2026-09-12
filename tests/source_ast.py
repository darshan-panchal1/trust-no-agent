"""AST queries for the constitution tests — never substring matching. Not collected.
Text search flags this repo's own prose, and `evals/cli_helpers.py` would pass for
`evals/cli`: Article I.a's carve-out is by name, not by pattern."""

from __future__ import annotations

import ast
from pathlib import Path


def imported_modules(path: Path) -> set[str]:
    """Dotted module names this file imports, from the parse tree rather than the text."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def imports_any(path: Path, prefixes: tuple[str, ...]) -> bool:
    """True when any import is one of `prefixes` or a submodule of one."""
    return any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in imported_modules(path)
        for prefix in prefixes
    )


def calls_named(path: Path, names: set[str]) -> list[str]:
    """Which of `names` this file actually calls — `ast.Call` nodes, not mentions."""
    called: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name in names:
                called.append(name)
    return called


def has_main_block(path: Path) -> bool:
    """A real `if __name__ == "__main__":` statement, not a mention of one in prose."""
    return any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        for node in ast.walk(ast.parse(path.read_text()))
    )


def calls_with_keyword(path: Path, keyword: str) -> bool:
    """True when a call in this file passes `keyword=`. Prose mentioning it does not count."""
    return any(
        isinstance(node, ast.Call) and any(kw.arg == keyword for kw in node.keywords)
        for node in ast.walk(ast.parse(path.read_text()))
    )
