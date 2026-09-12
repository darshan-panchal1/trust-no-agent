"""T1.11 acceptance: deterministic plausibility checks (FR-028's non-judged half).
The judged half (SoundsAuthoritative) is added in Slice 3's T3.9.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.cache.store import CacheMiss
from tests.vibes_checks import assert_deterministic_vibes

QUESTIONS = [
    # contradiction-bait: original case; v1's real answer is a terse 16-char fact.
    "What is the current per diem rate for business travel meals?",
    # multi-hop: original case.
    "Can a Senior Manager approve their own $2,500 international trip?",
    # answerable: shortest real cached answer (5 chars, "$500.").
    "What is the one-time home office stipend amount for eligible remote employees?",
    # answerable: v2's real answer ends in a bare citation with no terminal punctuation —
    # genuinely fails today; kept in so it stays visible instead of going unexercised.
    "What is the minimum password length required if using a password manager?",
    # out-of-scope: longest real cached answer (3131 chars) — MAX_LENGTH's real ceiling test.
    "What is the process for internal transfers between departments?",
    # out-of-scope: v1's real answer ends "...material.)" — trailing-closer case.
    "How many paid holidays does Meridian observe each year?",
    # out-of-scope: v1's real answer contains "...at least none is described..." —
    # the substring-match false positive `has_no_error_strings` used to trip on.
    "Does Meridian offer a company car program?",
]


@pytest.mark.parametrize("variant_answer", [v1_answer, v2_answer])
@pytest.mark.parametrize("question", QUESTIONS)
def test_deterministic_vibes_gate_on_cached_answers(
    variant_answer: Callable[[str], AgentResult], question: str
) -> None:
    """Requires T1.9's live pass to have populated the cache first."""
    try:
        result = variant_answer(question)
    except CacheMiss:
        pytest.skip("cache not yet populated — run app.smoke_check with a real API key first")
    assert_deterministic_vibes(result.answer)
