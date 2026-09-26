"""T047, rubric path (US5): the rubric judge keys its evidence on the passed-in config's model.
Seeded under `other/model`, it is served to a config naming `other/model` and never to one
naming the environment's model — the gap Phase 6 left open."""

from __future__ import annotations

import pytest

from evals.cache import store
from evals.cache.keys import hash_prompt, make_key
from evals.contract import EvalRecord
from evals.judge_config import JudgeConfig
from evals.models import judge_model
from evals.rubric import RubricJudge
from evals.rubric_verdict import render_prompt
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
POLITE = RubricJudge(
    "polite", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)
RECORD = EvalRecord(output="Happy to help.")
OTHER = JudgeConfig(judge_model="other/model", generator_model="other/gen")


def _seed_under(model: str, reply: str) -> str:
    kind = "deepeval:judge.polite"
    key = make_key(kind, model, hash_prompt(render_prompt(POLITE, RECORD)))
    entry = store.CacheEntry(
        call_kind=kind, response=reply, input_tokens=1, output_tokens=1, usd=0.0
    )
    store.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (store.CACHE_DIR / f"{key}.json").write_text(entry.model_dump_json())
    return key


def test_the_rubric_is_keyed_on_the_config_model_not_the_environment() -> None:
    assert judge_model() != OTHER.judge_model  # the environment names a different model
    key = _seed_under(OTHER.judge_model, '{"label": "pass", "reason": "courteous"}')
    served = evaluate(POLITE, RECORD, OTHER, cache_dir=store.CACHE_DIR)
    assert (served.status, served.label, served.raw["cache_keys"]) == ("ok", "pass", [key])
    under_env = evaluate(POLITE, RECORD, cache_dir=store.CACHE_DIR)
    assert under_env.status == "error" and under_env.label is None  # never served other's verdict


def test_two_configs_two_models_two_verdicts_one_store() -> None:
    _seed_under(OTHER.judge_model, '{"label": "pass", "reason": "a"}')
    _seed_under(judge_model(), '{"label": "fail", "reason": "b"}')
    other = evaluate(POLITE, RECORD, OTHER, cache_dir=store.CACHE_DIR)
    env = evaluate(POLITE, RECORD, cache_dir=store.CACHE_DIR)
    assert (other.label, env.label) == ("pass", "fail")
    assert other.judge_fingerprint != env.judge_fingerprint
