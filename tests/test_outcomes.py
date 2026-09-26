"""T016's tests (added for TDD): result builders never carry a score on failure, never report
a 0/0 entry's tokens as real, and turn NaN into `invalid_output` (spec FR-014, FR-034)."""

from __future__ import annotations

from evals import outcomes
from evals.cache.store import CacheEntry
from evals.evaluator import EvaluatorInfo

INFO = EvaluatorInfo(id="tna.x", version="1.1.0+x@1", requires=frozenset(), output_type="score")


def _entry(tokens: int, fingerprint: str | None = None) -> CacheEntry:
    return CacheEntry(
        call_kind="k", response=f"r{tokens}", input_tokens=tokens, output_tokens=tokens,
        usd=0.0, fingerprint=fingerprint,
    )


def test_skipped_names_the_missing_field_and_has_no_score() -> None:
    result = outcomes.skipped(INFO, "contexts")
    assert (result.status, result.score, result.label) == ("skipped", None, None)
    assert result.error is not None and "contexts" in result.error


def test_ok_sums_real_tokens_and_reports_recorded_provenance() -> None:
    served = {"b": _entry(3, "F"), "a": _entry(2, "F")}
    result = outcomes.ok(INFO, score=0.5, judge_model="j", fingerprint="R", served=served)
    assert (result.status, result.score, result.tokens_in, result.tokens_out) == ("ok", 0.5, 5, 5)
    assert result.fingerprint_provenance == "recorded"
    assert result.raw["cache_keys"] == ["a", "b"]
    assert result.raw["responses"] == ["r2", "r3"]


def test_a_zero_zero_entry_makes_tokens_unknown_not_zero() -> None:
    served = {"a": _entry(2, "F"), "b": _entry(0)}
    result = outcomes.ok(INFO, score=0.5, judge_model="j", fingerprint="R", served=served)
    assert (result.tokens_in, result.tokens_out) == (None, None)
    assert result.fingerprint_provenance == "not_recorded"


def test_nothing_served_means_no_tokens_and_no_provenance() -> None:
    result = outcomes.ok(INFO, score=0.5, judge_model="j", fingerprint="R", served={})
    assert (result.tokens_in, result.fingerprint_provenance) == (None, None)


def test_nan_is_invalid_output_never_a_score() -> None:
    result = outcomes.ok(INFO, score=float("nan"), judge_model="j", fingerprint="R", served={})
    assert (result.status, result.score) == ("invalid_output", None)


def test_error_and_invalid_carry_no_score_and_keep_the_raw_text() -> None:
    assert outcomes.error(INFO, "boom").score is None
    invalid = outcomes.invalid(INFO, "bad", raw_text="{}", judge_model="j", fingerprint="R")
    assert (invalid.status, invalid.score) == ("invalid_output", None)
    assert invalid.raw["responses"] == ["{}"]
