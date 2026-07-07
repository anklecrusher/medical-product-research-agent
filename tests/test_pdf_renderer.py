from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

import medical_research_agent.renderers.pdf as pdf_renderer


def test_render_markdown_pdf_writes_real_pdf_when_windows_fonts_are_missing(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: no configured Windows CJK font candidate exists.
    missing_font = tmp_path / "missing-font.ttf"
    monkeypatch.setattr(pdf_renderer, "WINDOWS_FONT_CANDIDATES", (("MissingFont", missing_font),))

    # When: a Markdown report is rendered to PDF.
    output_path = tmp_path / "report.pdf"
    result = pdf_renderer.render_markdown_pdf("# 标题\n\n正文 130 Hz 60 us", output_path, title="字体回退测试")

    # Then: rendering still produces a real PDF and records a non-blocking font warning.
    assert output_path.read_bytes().startswith(b"%PDF")
    assert result.path == output_path
    assert result.warnings
    assert any("Font not found" in warning for warning in result.warnings)
