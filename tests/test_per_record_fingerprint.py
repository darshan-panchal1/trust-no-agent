"""T051 (US6, FR-027/030): a new-path write stores its judging fingerprint beside the key; the
same configuration reads it back as `recorded`; a stored fingerprint that disagrees is refused
with an `error` naming both — keeping the stored reply, the key and the result's fingerprint."""

from __future__ import annotations

from dataclasses import replace

import pytest

from evals.cache import store
from evals.cache.store import CacheEntry
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from tests.per_record_nim import MockNim, chat, install
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
ID = "tna.deepeval.refusal_correctness"
RECORD = EvalRecord(input="Can I expense a gym?", output="No.", expected="No: out of scope")
LIVE = JudgeConfig("judge/m", "gen/m", mode="live", api_key="nvapi-test")
REPLY = '{"reason": "correctly refused", "score": 10}'


def _live(monkeypatch: pytest.MonkeyPatch, config: JudgeConfig = LIVE) -> EvalResult:
    install(monkeypatch, MockNim(chat(REPLY)))
    return evaluate(ID, RECORD, config, cache_dir=store.CACHE_DIR)


def test_a_live_write_stores_the_fingerprint_and_reads_back_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _live(monkeypatch)
    [written] = store.CACHE_DIR.glob("*.json")
    assert '"fingerprint"' in written.read_text()
    again = evaluate(ID, RECORD, replace(LIVE, mode="offline"), cache_dir=store.CACHE_DIR)
    assert again == first and again.fingerprint_provenance == "recorded"


def test_a_tampered_fingerprint_is_refused_naming_both(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _live(monkeypatch)
    [path] = store.CACHE_DIR.glob("*.json")
    honest = CacheEntry.model_validate_json(path.read_text())
    path.write_text(honest.model_copy(update={"fingerprint": "0" * 64}).model_dump_json())
    result = evaluate(ID, RECORD, replace(LIVE, mode="offline"), cache_dir=store.CACHE_DIR)
    assert (result.status, result.score, result.label) == ("error", None, None)
    assert "0" * 64 in (result.error or "") and str(honest.fingerprint) in (result.error or "")
    assert result.raw["responses"] == [REPLY] and result.raw["cache_keys"] == [path.stem]
    assert (result.judge_model, result.judge_fingerprint) == ("judge/m", first.judge_fingerprint)


def test_another_judge_model_is_another_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    ours = _live(monkeypatch)
    theirs = _live(monkeypatch, replace(LIVE, judge_model="judge/other"))
    assert ours.status == theirs.status == "ok"
    assert ours.judge_fingerprint != theirs.judge_fingerprint
