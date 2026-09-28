"""T034 (US3, FR-017): a record with no committed evidence, scored offline, is an `error` naming
the missing key and pointing at live mode — never a raw `CacheMiss`, never a guessed score."""

from __future__ import annotations

import pytest

from evals.contract import EvalRecord
from tests.per_record_support import golden_record
from trustnoagent import evaluate


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("id_", ["tna.ragas.faithfulness", "tna.deepeval.refusal_correctness"])
def test_a_novel_record_offline_names_the_key_and_points_at_live_mode(id_: str) -> None:
    result = evaluate(id_, EvalRecord(input="q?", output="a.", contexts=("c",), expected="e"))
    assert (result.status, result.score, result.label) == ("error", None, None)
    assert result.error is not None
    assert "cache miss for key" in result.error and "live" in result.error
    assert "evals.cli record" not in result.error  # `record` only refreshes the built-in set


@pytest.mark.usefixtures("socket_disabled")
def test_a_golden_record_with_committed_evidence_is_still_ok() -> None:
    """The control: the same call shape succeeds when the evidence exists."""
    assert evaluate("tna.ragas.faithfulness", golden_record("v2_fixed", 0)[1]).status == "ok"
