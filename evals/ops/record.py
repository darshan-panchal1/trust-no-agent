"""FR-048: the one place an evidence entry is created or refreshed. Everything else reads.
Decides *whether* to spend, not *how* — each layer's own live pass does that, through
`read_or_call`, so refreshed evidence arrives as a reviewable diff."""

from __future__ import annotations

from evals import cost
from evals.behavior.live_pass import main as record_behavior
from evals.component.live_pass import main as record_component
from evals.models import judge_model
from evals.ops.coverage import total_missing
from evals.pricing import price_usd

# Deliberately rough: refuses to *start* a run that would overshoot the ceiling (Article VIII).
ESTIMATED_INPUT_TOKENS_PER_CALL = 2_000
ESTIMATED_OUTPUT_TOKENS_PER_CALL = 200


def estimated_usd(missing_entries: int) -> float | None:
    """`None` if the judge model has no dated price — an unpriced spend can't be capped."""
    per_call = price_usd(
        judge_model(), ESTIMATED_INPUT_TOKENS_PER_CALL, ESTIMATED_OUTPUT_TOKENS_PER_CALL
    )
    return None if per_call is None else missing_entries * per_call


def _abort_if_over(usd_ceiling: float, allow_unpriced: bool) -> None:
    spent = cost.total_usd()
    if spent is None:
        if not allow_unpriced:
            raise RuntimeError("stopping: an unpriced call can't be checked against a ceiling")
        return
    if spent > usd_ceiling:
        raise RuntimeError(
            f"stopping after ${spent:.2f} spent, past the ${usd_ceiling:.2f} ceiling."
        )


def record(usd_ceiling: float, dry_run: bool = False, allow_unpriced: bool = False) -> int:
    """`dry_run=True` cannot spend. `allow_unpriced=True` is an explicit opt-in (never a
    silent default) to spend with no price to bound it against — costs stay UNVERIFIED."""
    missing = total_missing()
    if dry_run:
        return missing
    estimate = estimated_usd(missing)
    if estimate is None and not allow_unpriced:
        raise RuntimeError(
            f"refusing to start: no dated price for {judge_model()!r} in pricing.yaml. "
            "Pass --allow-unpriced to proceed anyway."
        )
    if estimate is not None and estimate > usd_ceiling:
        raise RuntimeError(
            f"refusing to start: ~${estimate:.2f} estimated for {missing} entries "
            f"exceeds the ${usd_ceiling:.2f} ceiling (Article VIII)."
        )
    record_component()
    _abort_if_over(usd_ceiling, allow_unpriced)
    record_behavior()
    _abort_if_over(usd_ceiling, allow_unpriced)
    return total_missing()
