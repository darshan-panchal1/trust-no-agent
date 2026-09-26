"""When is a GEval failure the judge's fault? (spec 001, US3, FR-016). DeepEval only (Article II).
GEval never validates what the judge sends back, so malformed output escapes it as one of three
exceptions, probed on deepeval 4.2.0 with a mocked NIM: `json.JSONDecodeError` (the text is not
JSON), a bare `KeyError` (JSON of the wrong shape) or a `ValueError` (a score that is not a
number, or GEval's own "invalid JSON"). A bare `KeyError` could also be an ordinary bug, so it
counts only once a judge reply was actually obtained — the served evidence entry is that proof."""

from __future__ import annotations

import json
from collections.abc import Mapping

from evals.cache.store import CacheEntry


def unusable_reply(exc: BaseException, served: Mapping[str, CacheEntry]) -> str | None:
    """The judge's reply text if `exc` means it replied and the reply was unusable, else None
    (a failure before any reply — an HTTP error, a cache miss — is an `error`)."""
    if isinstance(exc, json.JSONDecodeError):
        return exc.doc
    if isinstance(exc, (KeyError, ValueError)) and (served or "invalid JSON" in str(exc)):
        return "\n".join(entry.response for entry in served.values()) or str(exc)
    return None
