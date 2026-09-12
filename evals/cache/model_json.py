"""Trap 29 (docs/api-notes.md): a pydantic model round-tripped through `RagasCacheBackend`
can't be reconstructed as its original class — that class is unknown at read time. This
stands in for it on a cache hit, exposing only `.model_dump_json()`, the one method
`ragas/prompt/pydantic_prompt.py` ever calls on an `InstructorLLM.generate()` result.
"""

from __future__ import annotations

MODEL_JSON_KEY = "__model_dump_json__"


class ModelJson:
    def __init__(self, text: str) -> None:
        self._text = text

    def model_dump_json(self) -> str:
        return self._text
