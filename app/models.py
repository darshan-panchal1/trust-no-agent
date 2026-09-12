"""Framework-free data shapes shared by both agent variants (FR-001, FR-050)."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict


class ToolCallRecord(BaseModel):
    """One tool invocation, framework-free — evals/adapters converts this per layer."""

    model_config = ConfigDict(frozen=True)

    name: str
    arguments: Mapping[str, str]


class RetrievedChunk(BaseModel):
    """One retrieved passage, carrying its source filename (FR-050)."""

    model_config = ConfigDict(frozen=True)

    text: str
    source_document: str
    score: float


class AgentResult(BaseModel):
    """One variant's response to one question (FR-001)."""

    model_config = ConfigDict(frozen=True)

    answer: str
    retrieved_contexts: list[RetrievedChunk]
    tool_calls: list[ToolCallRecord]
    latency_ms: float
