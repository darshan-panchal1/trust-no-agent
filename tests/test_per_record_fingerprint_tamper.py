"""US6 (FR-030), every path: a copy of the committed store, with a wrong fingerprint stamped onto
exactly the entries a record is served from, is refused by every built-in and by the rubric
judge — never served. Works on a copy; the committed store itself is never written."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from evals.cache.store import CACHE_DIR, CacheEntry
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from tests.per_record_nim import MockNim, chat, install
from tests.per_record_support import golden_record
from trustnoagent import evaluate, list_evaluators

RECORD = golden_record("v2_fixed", 1)[1]
WRONG = "0" * 64


def _tamper(store: Path, keys: object) -> None:
    assert isinstance(keys, list) and keys
    for key in keys:
        path = store / f"{key}.json"
        entry = CacheEntry.model_validate_json(path.read_text())
        path.write_text(entry.model_copy(update={"fingerprint": WRONG}).model_dump_json())


def _refused(result: EvalResult) -> None:
    assert (result.status, result.score, result.label) == ("error", None, None)
    assert WRONG in (result.error or "") and result.raw["responses"]


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("ident", [info.id for info in list_evaluators()])
def test_every_built_in_refuses_a_tampered_entry(ident: str, tmp_path: Path) -> None:
    store = tmp_path / "store"
    shutil.copytree(CACHE_DIR, store)
    served = evaluate(ident, RECORD, cache_dir=store)
    assert served.status == "ok"
    _tamper(store, served.raw["cache_keys"])
    _refused(evaluate(ident, RECORD, cache_dir=store))


@pytest.mark.usefixtures("socket_disabled")
def test_the_rubric_path_refuses_a_tampered_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    polite = RubricJudge("polite", "Is it polite?", frozenset({"output"}), labels=("pass", "fail"))
    install(monkeypatch, MockNim(chat('{"label": "pass", "reason": "courteous"}')))
    live = JudgeConfig("judge/m", "gen/m", mode="live", api_key="nvapi-test")
    record = EvalRecord(output="Happy to help.")
    written = evaluate(polite, record, live, cache_dir=tmp_path)
    assert written.status == "ok"
    _tamper(tmp_path, written.raw["cache_keys"])
    _refused(evaluate(polite, record, JudgeConfig("judge/m", "gen/m"), cache_dir=tmp_path))
