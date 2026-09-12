"""GoldenCase — the one canonical evaluation-case model (FR-010, FR-011, FR-012)."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

Category = Literal["answerable", "multi-hop", "out-of-scope", "contradiction-bait"]


class GoldenCase(BaseModel):
    """One hand-authored evaluation case, one JSONL line (FR-010)."""

    model_config = ConfigDict(frozen=True)

    question: str
    ground_truth: str
    reference_contexts: list[str]
    category: Category
    expected_tools: list[str] | None = None

    @model_validator(mode="after")
    def _expected_tools_matches_category(self) -> Self:
        is_multi_hop = self.category == "multi-hop"
        has_tools = self.expected_tools is not None
        if is_multi_hop and not has_tools:
            raise ValueError("multi-hop cases must set expected_tools")
        if not is_multi_hop and has_tools:
            raise ValueError("expected_tools must be null unless category is multi-hop")
        return self
