"""Which files the constitution tests inspect. Not collected (no `test_` prefix)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("app", "evals", "tests", "trustnoagent")
MAX_MODULE_LINES = 60


def python_files() -> list[Path]:
    """Every first-party module, including the root conftest, excluding caches."""
    found: list[Path] = [REPO_ROOT / "conftest.py"]
    for directory in SOURCE_DIRS:
        found.extend(sorted((REPO_ROOT / directory).rglob("*.py")))
    return [path for path in found if "__pycache__" not in path.parts]


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))
