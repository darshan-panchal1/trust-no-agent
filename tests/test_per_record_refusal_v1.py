"""T020 (US1, SC-002, Article XI): `tna.deepeval.refusal_correctness` reproduces every v1
per-case score from committed evidence, carries GEval's reason, reports the real tokens
DeepEval entries recorded — and shows `v1_naive` failing at least once."""

from __future__ import annotations

import pytest

from tests.per_record_v1 import VARIANTS, answers, record_for, refusal_triples
from trustnoagent import evaluate

ID = "tna.deepeval.refusal_correctness"


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("variant", VARIANTS)
def test_reproduces_every_v1_refusal_score(variant: str) -> None:
    assert answers()  # answers are shared with the ragas tests; built once per session
    for case, answer, expected in refusal_triples()[variant]:
        result = evaluate(ID, record_for(case, answer))
        assert result.status == "ok", (case.question, result.error)
        assert result.score == pytest.approx(expected, abs=1e-9), case.question
        assert result.explanation
        assert result.tokens_in and result.tokens_out  # deepeval entries hold real usage


@pytest.mark.usefixtures("socket_disabled")
def test_a_v1_answer_fails_refusal_correctness() -> None:
    worst = min(refusal_triples()["v1_naive"], key=lambda triple: triple[2])
    result = evaluate(ID, record_for(worst[0], worst[1]))
    assert result.score is not None and result.score < 0.5
