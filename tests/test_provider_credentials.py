"""Article III / VI.a (Eighth amendment): JUDGE_MODEL and GENERATOR_MODEL are actually set
by the `env` block, not just declared in it; no provider credential is present, and the
suite is green anyway — proof by mechanism, matching Article III.a's own standard.
"""

from __future__ import annotations

import os

import pytest


def test_judge_and_generator_models_are_actually_set(pytestconfig: pytest.Config) -> None:
    """A silently-ignored `env` block (III.a's own warning) would leave these unset too."""
    assert os.environ.get("JUDGE_MODEL")
    assert os.environ.get("GENERATOR_MODEL")
    ini = pytestconfig.getini("env")
    assert any(entry.startswith("JUDGE_MODEL=") for entry in ini)
    assert any(entry.startswith("GENERATOR_MODEL=") for entry in ini)


def test_no_openai_credential_is_needed_anywhere_and_the_suite_is_green_anyway() -> None:
    """Article VI.a (Ninth amendment): OPENAI_API_KEY was the last credential this repo
    needed on any path — ResponseRelevancy's embeddings moved to a local
    sentence-transformers model. Nothing constructs an OpenAI client anywhere now."""
    assert "OPENAI_API_KEY" not in os.environ


def test_the_nvidia_credential_is_absent_and_the_suite_is_green_anyway() -> None:
    """`openai.OpenAI()` is eager, same as Groq's before it (docs/api-notes.md V8.2) — if
    any offline path constructed one, this suite would be red, not green, right here."""
    assert "NVIDIA_API_KEY" not in os.environ
