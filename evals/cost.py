"""Article VIII: what this run actually cost, accumulated as the cache is read and written.

`evals/cache/store.py` is the only writer — every cache read or write lands here, so the
table at the end of a run counts real calls rather than intentions. A cached call adds its
token counts but $0.00 spend, unconditionally. A row's `usd` becomes `None` (UNVERIFIED)
the moment an uncached call has no dated price — never a fabricated figure.
"""

from __future__ import annotations

from pydantic import BaseModel


class CostRow(BaseModel):
    """One `call_kind`'s totals: `generate:v1_naive`, `ragas:faithfulness`, …"""

    call_kind: str
    calls: int = 0
    cached: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float | None = 0.0  # None: at least one uncached call here has no dated price


_ROWS: dict[str, CostRow] = {}


def record_call(
    call_kind: str, input_tokens: int, output_tokens: int, usd: float | None, cached: bool
) -> None:
    """Count one served call. `usd` is charged only when it was not served from cache; an
    uncached call with no dated price (`usd is None`) marks the whole row UNVERIFIED."""
    row = _ROWS.setdefault(call_kind, CostRow(call_kind=call_kind))
    row.calls += 1
    row.cached += int(cached)
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens
    if cached:
        return  # $0.00 contribution, unconditionally — no spend happened this run
    if usd is None or row.usd is None:
        row.usd = None
    else:
        row.usd += usd


def rows() -> list[CostRow]:
    """Every row this run touched, in a stable order for the table and for reports."""
    return [_ROWS[key] for key in sorted(_ROWS)]


def total_usd() -> float | None:
    """None if any row is UNVERIFIED — a total cannot be known when one input isn't."""
    if any(row.usd is None for row in _ROWS.values()):
        return None
    return sum(row.usd for row in _ROWS.values() if row.usd is not None)


def reset() -> None:
    """Test-only: drop accumulated rows so one test's calls cannot leak into another's."""
    _ROWS.clear()
