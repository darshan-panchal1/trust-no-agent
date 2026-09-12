"""T4.8: the CI configuration is under test too — Article XI's spirit, applied to YAML.

"No API key in the offline job" decays silently: someone adds one `env:` line to debug a
flake and nothing objects. These assertions object."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from tests.repo_files import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CREDENTIAL_NAMES = ("NVIDIA_API_KEY",)  # sole credential since the tenth amendment
# The only file allowed to hold a provider secret — enumerated by directory listing, not a
# fixed pair, so a NEW workflow (example.yml, or any future one) is covered automatically
# instead of silently unpoliced until someone remembers to add it here.
CREDENTIALED_WORKFLOWS = {"live.yml"}
WORKFLOW_NAMES = sorted(p.name for p in WORKFLOWS.glob("*.yml"))


def _load(name: str) -> dict[Any, Any]:
    # dict[Any, Any], not dict[str, Any]: YAML 1.1 parses a bare `on:` key as the boolean
    # True, so a workflow's trigger block is genuinely not reachable by a string key.
    loaded: dict[Any, Any] = yaml.safe_load((WORKFLOWS / name).read_text())
    return loaded

@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_every_workflow_parses(name: str) -> None:
    assert _load(name)["jobs"]

@pytest.mark.parametrize("name", WORKFLOW_NAMES)
def test_only_the_allow_listed_workflows_hold_a_credential(name: str) -> None:
    """Article VI / FR-046: covers every workflow file, not just the ones that existed
    when this was first written."""
    text = (WORKFLOWS / name).read_text()
    has_credential = any(f"{c}:" in text or f"secrets.{c}" in text for c in CREDENTIAL_NAMES)
    if name in CREDENTIALED_WORKFLOWS:
        assert has_credential, f"{name} is allow-listed to hold a credential but does not"
    else:
        assert not has_credential, name

def test_the_live_workflow_is_manually_dispatched_only() -> None:
    """Article VI: it never gates a merge, so it cannot run on push or pull_request."""
    triggers = _load("live.yml")[True]
    assert set(triggers) == {"workflow_dispatch"}

def test_ci_installs_from_the_lockfile() -> None:
    """Article IX: exact pins. `--frozen` fails on drift instead of resolving around it."""
    for name in ("offline.yml", "live.yml"):
        assert "uv sync --frozen" in (WORKFLOWS / name).read_text(), name

def test_the_readmes_first_code_block_is_the_plain_test_invocation() -> None:
    """Article 0: the first thing shown is the Prime Contract's exact command, verbatim."""
    body = (REPO_ROOT / "README.md").read_text()
    first_block = body.split("```")[1].strip()
    assert first_block == "git clone <repo> && cd trust-no-agent && uv sync && uv run pytest"
    assert body.index("```") < body.index("## Maintaining this repo")
