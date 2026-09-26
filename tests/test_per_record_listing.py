"""T031 (US2, FR-006/008/010/012): the evaluator listing needs no environment and no network,
and matches both the published catalogue and the exact pinned library versions."""

from __future__ import annotations

import re
import tomllib

import pytest

import trustnoagent
from tests.repo_files import REPO_ROOT
from trustnoagent.evaluators import list_evaluators

ID_SHAPE = re.compile(r"^tna\.(ragas|deepeval)\.[a-z_]+$")
CATALOGUE = REPO_ROOT / "specs" / "001-per-record-evaluators" / "contracts" / "public-api.md"
ROW = re.compile(r"^\| `(tna\.[a-z_.]+)` \| `[^`]+` \| ([^|]+)\| `?(\w+)`? ", re.MULTILINE)


def _pin(name: str) -> str:
    pins = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    return str(next(p.split("==")[1] for p in pins if p.startswith(f"{name}==")))


@pytest.mark.usefixtures("socket_disabled")
def test_the_listing_needs_no_environment_and_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("JUDGE_MODEL", "GENERATOR_MODEL", "NVIDIA_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    ids = [info.id for info in list_evaluators()]
    assert len(ids) == 5 and ids == sorted(ids)
    assert all(ID_SHAPE.match(i) for i in ids)


def test_the_package_version_is_the_project_version() -> None:
    """The listing stamps `__version__`, so a release that bumps only one of the two files
    would ship evaluator versions that name a release nobody published."""
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    assert trustnoagent.__version__ == project["version"]


def test_versions_name_the_release_and_the_exact_pinned_library() -> None:
    for info in list_evaluators():
        lib = "deepeval" if ".deepeval." in info.id else "ragas"
        assert info.version == f"{trustnoagent.__version__}+{lib}@{_pin(lib)}", info.id


def test_requires_and_output_type_match_the_published_catalogue() -> None:
    published = {
        ident: (frozenset(re.findall(r"`(\w+)`", requires)), output)
        for ident, requires, output in ROW.findall(CATALOGUE.read_text())
    }
    listed = {i.id: (frozenset(i.requires), i.output_type) for i in list_evaluators()}
    assert len(published) == 5
    assert listed == published
