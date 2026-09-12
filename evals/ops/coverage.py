"""What the evidence store holds against what a full run needs. Read-only, always.

Reports **coverage, not key identity** — a judge key hashes the prompt ragas/deepeval builds
at scoring time, unreproducible without scoring. FR-032's one-entry-per-case makes it countable.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from evals.behavior.live_pass import RELEVANT_CATEGORIES
from evals.cache.store import CACHE_DIR
from evals.component.matrix import METRIC_NAMES
from evals.golden.load import load_golden

VARIANTS = ("v1_naive", "v2_fixed")


class Coverage(BaseModel):
    call_kind: str
    present: int
    expected: int

    @property
    def missing(self) -> int:
        return max(0, self.expected - self.present)


def _present_counts() -> dict[str, int]:
    # Committed entries, bucketed by the call_kind each one names about itself.
    counts: dict[str, int] = {}
    if not CACHE_DIR.exists():
        return counts
    for path in sorted(CACHE_DIR.glob("*.json")):
        call_kind = json.loads(path.read_text())["call_kind"]
        counts[call_kind] = counts.get(call_kind, 0) + 1
    return counts


def expected_counts() -> dict[str, int]:
    """Derived from the golden dataset, never hardcoded — a case added here is counted."""
    cases = load_golden()
    refusal_cases = [case for case in cases if case.category in RELEVANT_CATEGORIES]
    expected = {f"generate:{variant}": len(cases) for variant in VARIANTS}
    for metric in METRIC_NAMES:
        expected[f"ragas:{metric}"] = len(cases) * len(VARIANTS)
    expected["deepeval:refusalcorrectness"] = len(refusal_cases) * len(VARIANTS)
    return expected


def coverage() -> list[Coverage]:
    present = _present_counts()
    counts = sorted(expected_counts().items())
    return [Coverage(call_kind=k, present=present.get(k, 0), expected=n) for k, n in counts]


def total_missing() -> int:
    return sum(row.missing for row in coverage())
