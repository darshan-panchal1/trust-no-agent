"""Unit tests for the deterministic vibes checks themselves (T1.11)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.vibes_checks import (
    assert_deterministic_vibes,
    ends_in_complete_sentence,
    has_no_error_strings,
    has_reasonable_length,
    is_non_empty,
)


@pytest.mark.parametrize(
    "text",
    [
        "The current per diem rate for business travel meals is $65 USD per day.",
        (
            "A Senior Manager cannot approve this trip alone, since Director-level "
            "approval is required for international travel."
        ),
    ],
)
def test_deterministic_checks_pass_on_plausible_text(text: str) -> None:
    assert_deterministic_vibes(text)


@pytest.mark.parametrize(
    ("text", "failing_check"),
    [
        ("", is_non_empty),
        ("Hi", has_reasonable_length),
        ("Traceback: NoneType has no attribute", has_no_error_strings),
        ("This answer is incomplete and trails off without", ends_in_complete_sentence),
    ],
)
def test_deterministic_checks_catch_bad_text(
    text: str, failing_check: Callable[[str], bool]
) -> None:
    assert failing_check(text) is False
