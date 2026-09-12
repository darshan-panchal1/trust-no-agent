"""T3.1/T3.2 acceptance: the GEval factory rejects `criteria`; `CachedJudge` is a pure
cache reader offline, even with a real key exported."""

from __future__ import annotations

import pytest

from evals.cache import store
from evals.cache.keys import hash_prompt, make_key
from evals.cache.store import CacheEntry, CacheMiss
from evals.judge import CachedJudge, build_geval_metric
from evals.models import judge_model

pytestmark = pytest.mark.usefixtures("isolated_cache")


def test_build_geval_metric_succeeds_with_evaluation_steps() -> None:
    metric = build_geval_metric("X", evaluation_steps=["a"])
    assert metric.evaluation_steps == ["a"]
    assert metric.criteria is None


def test_build_geval_metric_rejects_criteria() -> None:
    with pytest.raises(TypeError):
        build_geval_metric("X", evaluation_steps=["a"], criteria="y")  # type: ignore[call-arg]


@pytest.mark.usefixtures("socket_disabled")
def test_offline_judge_hit_returns_without_calling_the_model() -> None:
    judge = CachedJudge("deepeval:refusalcorrectness")
    cache_key = make_key("deepeval:refusalcorrectness", judge_model(), hash_prompt("hi"))
    store.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    entry = CacheEntry(
        call_kind="deepeval:refusalcorrectness",
        response="cached",
        input_tokens=1,
        output_tokens=1,
        usd=0.0,
    )
    (store.CACHE_DIR / f"{cache_key}.json").write_text(entry.model_dump_json())
    assert judge.generate("hi") == "cached"


@pytest.mark.usefixtures("socket_disabled")
def test_offline_judge_miss_raises_even_with_key_exported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-fake-but-present")
    judge = CachedJudge("deepeval:refusalcorrectness")
    with pytest.raises(CacheMiss, match="cache miss"):
        judge.generate("unseen prompt")
