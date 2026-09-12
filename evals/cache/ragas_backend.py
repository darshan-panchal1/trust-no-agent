"""RagasCacheBackend — Trap 19 fix (docs/api-notes.md, Round 4 / CONSTITUTION.md Article III).

Ragas' `cacher()` wraps the *bound* `InstructorLLM.generate`, so `self` never reaches its
cache key; this re-keys through T1.4's `make_key` so a judge change moves the key (Article III).

Trap 29: `json.dumps(model, default=str)` silently stringified pydantic models instead of
raising — every cached result was corrupted from write, since Groq era. Fixed by model_json.py.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from ragas.cache import CacheInterface

from evals.cache.keys import make_key
from evals.cache.model_json import MODEL_JSON_KEY, ModelJson
from evals.cache.store import CacheEntry, CacheMiss, read_or_call, read_or_raise


class RagasCacheBackend(CacheInterface):
    """One instance per judge object; `call_kind` names the metric, e.g. `ragas:faithfulness`."""

    def __init__(
        self, call_kind: str, model_identity: str, mode: Literal["offline", "live"] = "offline"
    ) -> None:
        self._call_kind = call_kind
        self._model_identity = model_identity
        self._mode = mode

    def _real_key(self, ragas_key: str) -> str:
        return make_key(self._call_kind, self._model_identity, ragas_key)

    def has_key(self, key: str) -> bool:
        """Offline: a miss raises here, before ragas' wrapper ever calls the live function."""
        try:
            read_or_raise(self._real_key(key))
            return True
        except CacheMiss:
            if self._mode == "offline":
                raise
            return False

    def get(self, key: str) -> Any:
        parsed = json.loads(read_or_raise(self._real_key(key)).response)
        if isinstance(parsed, dict) and MODEL_JSON_KEY in parsed:
            return ModelJson(parsed[MODEL_JSON_KEY])
        return parsed

    def set(self, key: str, value: Any) -> None:
        if hasattr(value, "model_dump_json"):
            payload = json.dumps({MODEL_JSON_KEY: value.model_dump_json()})
        else:
            payload = json.dumps(value, default=str, sort_keys=True)
        # usage 0: Article VIII sources ragas spend from evaluate(), not per-call here.
        entry = CacheEntry(
            call_kind=self._call_kind, response=payload, input_tokens=0, output_tokens=0, usd=0.0
        )
        read_or_call(self._real_key(key), lambda: entry)
