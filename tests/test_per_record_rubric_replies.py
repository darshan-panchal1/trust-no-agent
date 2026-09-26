"""T041, reply half (US4, FR-016): a score rubric in range is `ok`; a reply that breaks the
rubric's schema is `invalid_output` with the judge's own text kept, never a coerced verdict."""

from __future__ import annotations

import pytest

from evals.cache import store
from evals.cache.keys import hash_prompt, make_key
from evals.contract import EvalRecord, EvalResult
from evals.models import judge_model
from evals.rubric import RubricJudge
from evals.rubric_verdict import render_prompt
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
DEPTH = RubricJudge("depth", "Rate the depth.", frozenset({"input", "output"}), score_range=(1, 5))
GOOD = EvalRecord(input="Where is my badge?", output="Happy to help: badges are at reception.")


def _seed(rubric: RubricJudge, record: EvalRecord, reply: str) -> None:
    kind = f"deepeval:judge.{rubric.name}"
    key = make_key(kind, judge_model(), hash_prompt(render_prompt(rubric, record)))
    entry = store.CacheEntry(
        call_kind=kind, response=reply, input_tokens=40, output_tokens=12, usd=None
    )
    store.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (store.CACHE_DIR / f"{key}.json").write_text(entry.model_dump_json())


def _score(rubric: RubricJudge, record: EvalRecord) -> EvalResult:
    return evaluate(rubric, record, cache_dir=store.CACHE_DIR)


@pytest.mark.parametrize(
    "reply", ['{"score": 7, "reason": "x"}', '{"verdict": "x"}', '{"score": "high", "reason": "x"}']
)
def test_a_reply_that_breaks_the_rubric_is_invalid_output_with_the_text_kept(reply: str) -> None:
    _seed(DEPTH, GOOD, reply)
    result = _score(DEPTH, GOOD)
    assert (result.status, result.score, result.label) == ("invalid_output", None, None)
    assert result.raw["responses"] == [reply]


def test_a_score_rubric_in_range_is_ok() -> None:
    _seed(DEPTH, GOOD, '{"score": 4, "reason": "thorough"}')
    assert (_score(DEPTH, GOOD).status, _score(DEPTH, GOOD).score) == ("ok", 4.0)
