"""System prompts per variant (FR-003, FR-004) and the shared user-prompt template."""

from __future__ import annotations

from app.models import RetrievedChunk

V1_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about Meridian Logistics company policy. "
    "You may use outside general knowledge if the provided context does not fully answer the "
    "question. Answer confidently and directly."
)

V2_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about Meridian Logistics company policy. "
    "Answer using ONLY the provided context below — never use outside knowledge, and never "
    "guess. If the context does not contain the answer, say so explicitly rather than "
    "fabricating one. Cite the source document filename for every claim you make."
)


def build_user_prompt(question: str, contexts: list[RetrievedChunk]) -> str:
    """Combine the question with retrieved context, in the format both variants share."""
    if not contexts:
        context_block = "(no matching context retrieved)"
    else:
        context_block = "\n\n".join(f"[Source: {c.source_document}]\n{c.text}" for c in contexts)
    return f"Context:\n{context_block}\n\nQuestion: {question}"
