"""US6 (FR-029): a pre-1.1 evidence entry — no stored fingerprint — is served as before and
marked `not_recorded`, never refused. Checked on the real committed store for every built-in,
with the served files themselves confirmed fingerprint-free on disk."""

from __future__ import annotations

import pytest

from evals.cache import store
from evals.cache.store import CACHE_DIR
from evals.contract import EvalRecord
from tests.per_record_nim import MockNim, chat, install
from tests.per_record_support import golden_record
from trustnoagent import evaluate, list_evaluators

RECORD = golden_record("v2_fixed", 1)[1]


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("ident", [info.id for info in list_evaluators()])
def test_committed_pre_1_1_evidence_is_served_and_marked_not_recorded(ident: str) -> None:
    result = evaluate(ident, RECORD)
    assert result.status == "ok", result.error
    assert result.fingerprint_provenance == "not_recorded"
    assert result.judge_fingerprint is not None  # the result still names how it was judged
    keys = result.raw["cache_keys"]
    assert isinstance(keys, list) and keys
    for key in keys:
        assert '"fingerprint"' not in (CACHE_DIR / f"{key}.json").read_text(), key


@pytest.mark.usefixtures("socket_disabled")
def test_an_error_after_the_config_is_known_still_names_its_judge_and_fingerprint() -> None:
    """Data model: `judge_fingerprint` is None only when no configuration was reached."""
    result = evaluate("tna.ragas.response_relevancy", EvalRecord(input="unrecorded?", output="a"))
    assert result.status == "error" and "cache miss" in (result.error or "")
    assert result.judge_model is not None and result.judge_fingerprint is not None


@pytest.mark.usefixtures("isolated_cache", "socket_disabled")
def test_an_old_path_write_carries_no_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """No judging session, no stamp: v1.0.0's `CachedJudge` writes exactly its v1 bytes."""
    from evals.judge import CachedJudge

    install(monkeypatch, MockNim(chat('{"reason": "r", "score": 10}')))
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")  # the v1 path reads the environment
    CachedJudge("deepeval:refusalcorrectness", mode="live").generate("a v1-path prompt")
    [written] = store.CACHE_DIR.glob("*.json")
    assert '"fingerprint"' not in written.read_text()
