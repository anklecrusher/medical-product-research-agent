"""Helpers for loading and rendering report templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from medical_research_agent.report_models import SourceAuditItem
from medical_research_agent.schemas import FigureAsset


TEMPLATE_DIR = Path(__file__).with_name("templates")
DEFAULT_REPORT_TEMPLATE = "report_markdown.j2"


def render_figure_markdown(figure: FigureAsset) -> str:
    """Render a figure asset as Markdown with required source attribution."""

    image_ref = figure.image_path or str(figure.image_url or "")
    source_ref = str(figure.source_url or "")
    location = f"，位置：{figure.location}" if figure.location else ""
    usage = f"\n\n> 使用说明：{figure.usage_note}" if figure.usage_note else ""
    rights = f"\n\n> 版权/使用备注：{figure.rights_note}" if figure.rights_note else ""

    if not image_ref:
        return f"> 图：{figure.title}。未找到可嵌入图片，建议后续人工补图。"

    source_text = figure.source_title or "原始来源"
    if source_ref:
        source_text = f"[{source_text}]({source_ref})"

    return (
        f"![{figure.title}]({image_ref})\n\n"
        f"**图：{figure.title}。** {figure.caption}\n\n"
        f"> 来源：{source_text}{location}{usage}{rights}"
    )


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )
    env.globals["render_figure"] = render_figure_markdown
    return env


def render_report_markdown(
    report: Any,
    *,
    figures: list[FigureAsset] | None = None,
    source_audit: list[SourceAuditItem] | None = None,
    template_name: str = DEFAULT_REPORT_TEMPLATE,
) -> str:
    """Render a Markdown report from a flexible report object."""

    figures_by_section: dict[str, list[FigureAsset]] = {}
    for figure in figures or []:
        if figure.status == "rejected":
            continue
        key = figure.recommended_section or "unassigned"
        figures_by_section.setdefault(key, []).append(figure)

    template = _environment().get_template(template_name)
    return template.render(
        report=report,
        figures_by_section=figures_by_section,
        source_audit=source_audit or [],
    )

