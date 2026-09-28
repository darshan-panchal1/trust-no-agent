"""T054 edges (US7, FR-037): usage from a retried attempt is billed to the entry that attempt
produced, not the next call's; the v1 path, run live with no session, still writes 0/0. (A
record served from 0/0 evidence reporting unknown tokens is T019's test.)"""

from __future__ import annotations

import httpx
import pytest

from evals.cache import store
from evals.cache.store import CacheEntry
from evals.component.matrix import build_metric
from evals.contract import EvalRecord
from evals.judge_config import JudgeConfig
from tests.per_record_nim import MockNim, install
from tests.per_record_ragas_nim import REPLIES, USAGE, faithfulness, requested_tool, tool_reply
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
RECORD = EvalRecord(input="What colour is the sky?", output="The sky is blue.",
                    contexts=("The sky is blue.",))
LIVE = JudgeConfig("judge/m", "gen/m", mode="live", api_key="nvapi-test")


def _usages() -> list[tuple[int, int]]:
    files = store.CACHE_DIR.glob("*.json")
    entries = [CacheEntry.model_validate_json(p.read_text()) for p in files]
    return sorted((e.input_tokens, e.output_tokens) for e in entries)


def test_a_retried_attempt_is_billed_to_the_entry_it_produced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[str] = []

    def first_reply_malformed(request: httpx.Request) -> httpx.Response:
        tool = requested_tool(request)
        attempts.append(tool)
        if tool == "StatementGeneratorOutput" and attempts.count(tool) == 1:
            return tool_reply(tool, {"wrong": "shape"}, (7, 3))  # fails validation: retried
        return tool_reply(tool, REPLIES[tool], USAGE[tool])

    install(monkeypatch, MockNim(first_reply_malformed))
    result = evaluate("tna.ragas.faithfulness", RECORD, LIVE, cache_dir=store.CACHE_DIR)
    assert result.status == "ok" and len(attempts) == 3
    assert _usages() == [(123 + 7, 45 + 3), (200, 60)]  # the retry's tokens stay with their call
    assert (result.tokens_in, result.tokens_out) == (330, 108)


def test_the_v1_path_run_live_still_writes_zero_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, MockNim(faithfulness))
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")  # the v1 path reads the environment
    from evals.adapters.ragas_adapter import record_to_sample

    build_metric("faithfulness", "live").single_turn_score(record_to_sample(RECORD))
    assert _usages() == [(0, 0), (0, 0)]  # FR-037: the old path's recording is untouched
