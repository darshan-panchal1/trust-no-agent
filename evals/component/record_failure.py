"""When is a Ragas failure the judge's fault? (spec 001, US3, FR-016). Ragas only (Article II).
Probed on instructor 1.16.0 with a mocked NIM: a reply that fails to parse raises
`InstructorRetryException` with `last_completion` set; an HTTP failure raises the same class with
it unset. Truncation is `IncompleteOutputException`. `last_completion` is what tells them apart."""

from __future__ import annotations

from instructor.exceptions import IncompleteOutputException, InstructorRetryException
from pydantic import ValidationError
from ragas.exceptions import RagasOutputParserException


def _reply_text(completion: object) -> str:
    """The judge's own text from a chat completion: tool-call arguments, else content."""
    choices = getattr(completion, "choices", None) or [None]
    message = getattr(choices[0], "message", None)
    calls = getattr(message, "tool_calls", None) or []
    return str(calls[0].function.arguments if calls else getattr(message, "content", "") or "")


def unusable_reply(exc: BaseException) -> str | None:
    """The judge's reply text if `exc` means it replied and the reply was unusable, else None
    (a failure before any reply is an `error`, not `invalid_output`)."""
    if isinstance(exc, (InstructorRetryException, IncompleteOutputException)):
        completion = exc.last_completion
        return None if completion is None else _reply_text(completion)
    if isinstance(exc, (ValidationError, RagasOutputParserException)):
        return str(exc)
    return None
