"""T054 (US7, FR-033/034): a live Ragas evaluation records the provider's real usage on each
evidence entry it writes — each entry its own call's usage — and a re-run against those entries
makes no HTTP call. Faithfulness: two judge calls, no embeddings."""

from __future__ import annotations

from dataclasses import replace

import pytest

from evals.cache import store
from evals.cache.store import CacheEntry
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from tests.per_record_nim import MockNim, install
from tests.per_record_ragas_nim import USAGE, faithfulness
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
RECORD = EvalRecord(input="What colour is the sky?", output="The sky is blue.",
                    contexts=("The sky is blue.",))
LIVE = JudgeConfig("judge/m", "gen/m", mode="live", api_key="nvapi-test")


def _run(config: JudgeConfig = LIVE) -> EvalResult:
    return evaluate("tna.ragas.faithfulness", RECORD, config, cache_dir=store.CACHE_DIR)


def _written() -> list[CacheEntry]:
    files = store.CACHE_DIR.glob("*.json")
    entries = [CacheEntry.model_validate_json(p.read_text()) for p in files]
    return sorted(entries, key=lambda e: e.input_tokens)


def test_each_entry_records_its_own_calls_real_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MockNim(faithfulness)
    install(monkeypatch, mock)
    result = _run()
    assert (result.status, result.score) == ("ok", 1.0)
    assert mock.calls == 2
    written = _written()
    assert [(e.input_tokens, e.output_tokens) for e in written] == sorted(USAGE.values())
    assert all(e.fingerprint for e in written) and len({e.fingerprint for e in written}) == 1
    assert (result.tokens_in, result.tokens_out) == (123 + 200, 45 + 60)
    assert result.fingerprint_provenance == "recorded"


# ids, not bare values: a "live" id is a keyword, and conftest.py skips anything keyed "live".
@pytest.mark.parametrize("mode", ["live", "offline"], ids=["rerun_as_live", "rerun_as_offline"])
def test_a_rerun_against_those_entries_makes_no_http_call(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock = MockNim(faithfulness)
    install(monkeypatch, mock)
    first = _run()
    again = _run(replace(LIVE, mode=mode))  # type: ignore[arg-type]
    assert mock.calls == 2  # both calls were served from evidence the second time
    assert again == first and (again.tokens_in, again.tokens_out) == (323, 105)
