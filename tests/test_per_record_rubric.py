"""T041 (US4, FR-020–023): a rubric judge scores through the same `evaluate()` as the built-ins.
Evidence is seeded as files, as `tests/test_judge.py` does — never through `read_or_call`."""

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
POLITE = RubricJudge(
    "polite", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)
DEPTH = RubricJudge("depth", "Rate the depth.", frozenset({"input", "output"}), score_range=(1, 5))
GOOD = EvalRecord(input="Where is my badge?", output="Happy to help: badges are at reception.")
BAD = EvalRecord(input="Where is my badge?", output="Figure it out yourself.")  # known-bad


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


def test_a_good_record_passes_and_a_known_bad_record_fails_through_the_same_path() -> None:
    _seed(POLITE, GOOD, '{"label": "pass", "reason": "courteous"}')
    _seed(POLITE, BAD, '{"label": "fail", "reason": "dismissive"}')
    good, bad = _score(POLITE, GOOD), _score(POLITE, BAD)
    assert (good.status, good.label, good.score) == ("ok", "pass", None)
    assert (bad.status, bad.label, bad.score) == ("ok", "fail", None)  # a verdict, not an error
    assert (bad.evaluator_id, bad.explanation) == ("tna.judge.polite", "dismissive")
    assert (bad.tokens_in, bad.tokens_out) == (40, 12)


def test_same_name_different_instructions_is_a_different_judge() -> None:
    rude = RubricJudge("polite", "Is the answer rude?", POLITE.requires, labels=("pass", "fail"))
    _seed(POLITE, GOOD, '{"label": "pass", "reason": "courteous"}')
    unseeded = _score(rude, GOOD)
    assert unseeded.status == "error" and unseeded.label is None  # never served POLITE's verdict
    _seed(rude, GOOD, '{"label": "fail", "reason": "not rude"}')
    assert _score(rude, GOOD).judge_fingerprint != _score(POLITE, GOOD).judge_fingerprint


def test_a_record_missing_a_rubric_field_is_skipped() -> None:
    result = _score(DEPTH, EvalRecord(output="only an answer"))
    assert (result.status, result.score) == ("skipped", None) and "input" in (result.error or "")
