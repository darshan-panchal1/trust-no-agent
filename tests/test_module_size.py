"""Article VII's 60-line cap, machine-enforced rather than remembered.

Its own module because it is the one constitutional rule that fails on the very file that
would otherwise be growing to hold it.
"""

from __future__ import annotations

from tests.repo_files import MAX_MODULE_LINES, python_files, relative


def test_every_module_fits_on_a_screen() -> None:
    sizes = {relative(path): len(path.read_text().splitlines()) for path in python_files()}
    assert {name: count for name, count in sizes.items() if count > MAX_MODULE_LINES} == {}
