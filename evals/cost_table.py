"""Article VIII's cost table, rendered as text — printed after every run, no flag needed.

The zero-call case prints the header and a zero total rather than nothing: "this run made
no calls" and "this run was never instrumented" must not look alike. A row with no dated
price for its model reads `UNVERIFIED` — never a fabricated number (Eighth amendment).
"""

from __future__ import annotations

from evals.cost import CostRow

_HEADER = f"{'call_kind':<28}{'calls':>7}{'cached':>8}{'tok_in':>10}{'tok_out':>10}{'USD':>12}"


def _usd_str(usd: float | None) -> str:
    return "UNVERIFIED" if usd is None else f"${usd:.2f}"


def _format_row(row: CostRow) -> str:
    return (
        f"{row.call_kind:<28}{row.calls:>7}{row.cached:>8}"
        f"{row.input_tokens:>10,}{row.output_tokens:>10,}{_usd_str(row.usd):>12}"
    )


def format_cost_table(rows: list[CostRow]) -> str:
    """The whole table, including its TOTAL line, as one printable string."""
    calls = sum(row.calls for row in rows)
    cached = sum(row.cached for row in rows)
    any_unverified = any(row.usd is None for row in rows)
    total = CostRow(
        call_kind="TOTAL",
        calls=calls,
        cached=cached,
        input_tokens=sum(row.input_tokens for row in rows),
        output_tokens=sum(row.output_tokens for row in rows),
        usd=None if any_unverified else sum(row.usd for row in rows if row.usd is not None),
    )
    hit_rate = 100.0 if calls == 0 else 100.0 * cached / calls
    lines = [_HEADER, "-" * len(_HEADER)]
    lines.extend(_format_row(row) for row in rows)
    lines.append("-" * len(_HEADER))
    lines.append(_format_row(total))
    lines.append(f"cache hit rate: {hit_rate:.0f}%   spend this run: {_usd_str(total.usd)}")
    return "\n".join(lines)
