"""FR-033 (spec 001, T057's finding): `outcomes.invalid()` surfaces real tokens a completed
call already recorded, and stays unknown when the reply was unusable before any call completed."""

from __future__ import annotations

from evals import outcomes
from evals.cache.store import CacheEntry
from evals.evaluator import EvaluatorInfo

INFO = EvaluatorInfo(id="tna.x", version="1.1.0+x@1", requires=frozenset(), output_type="score")


def _entry(tokens: int) -> CacheEntry:
    return CacheEntry(call_kind="k", response="r", input_tokens=tokens, output_tokens=tokens,
                      usd=0.0, fingerprint="F")


def test_invalid_surfaces_tokens_a_completed_call_already_recorded() -> None:
    """The reply that broke validation was still a real, billed call — not a free one."""
    served = {"a": _entry(7)}
    invalid = outcomes.invalid(INFO, "bad", "{}", "j", "R", served=served)
    assert (invalid.tokens_in, invalid.tokens_out) == (7, 7)


def test_invalid_stays_unknown_when_nothing_was_served() -> None:
    """A reply unusable before any call completed (no JSON at all) has nothing to report."""
    assert outcomes.invalid(INFO, "bad", "junk", "j", "R").tokens_in is None
    assert outcomes.invalid(INFO, "bad", "junk", "j", "R", served={}).tokens_in is None


def test_invalid_stays_unknown_for_an_unusable_zero_zero_entry() -> None:
    """A 0/0 entry (the old Ragas path) is not real usage; it must not read as real here either."""
    served = {"a": _entry(0)}
    assert outcomes.invalid(INFO, "bad", "{}", "j", "R", served=served).tokens_in is None
