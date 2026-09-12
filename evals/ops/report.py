"""FR-042: one `RunSummary`, two renderings, generated from the same object so the
Markdown and the HTML cannot disagree about a number.

Autoescaping is on for HTML because the report embeds model output verbatim — the answer
text is the point of the report, and it is not trusted markup.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evals.ops.run_summary import RunSummary

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
MARKDOWN_TEMPLATE = "report.md.j2"
HTML_TEMPLATE = "report.html.j2"


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(default_for_string=False, enabled_extensions=("html",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(summary: RunSummary, template_name: str) -> str:
    """One rendering of one summary. Both formats come through here."""
    return _environment().get_template(template_name).render(summary=summary)


def write_reports(summary: RunSummary, out_dir: Path) -> tuple[Path, Path]:
    """Write both renderings, timestamped (FR-042), and return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = summary.generated_at.strftime("%Y%m%dT%H%M%S")
    markdown_path = out_dir / f"report-{stamp}.md"
    html_path = out_dir / f"report-{stamp}.html"
    markdown_path.write_text(render(summary, MARKDOWN_TEMPLATE))
    html_path.write_text(render(summary, HTML_TEMPLATE))
    return markdown_path, html_path
