from types import SimpleNamespace

from medical_research_agent.report_templates import render_report_markdown
from medical_research_agent.schemas import FigureAsset, FigureStatus, ReportSection


def test_source_figure_requires_attribution_fields_and_dumps() -> None:
    figure = FigureAsset(
        title="SCS stimulation waveform",
        caption="Manufacturer waveform diagram used for engineering context.",
        image_url="https://example.com/figure.png",
        source_url="https://example.com/manual.pdf",
        source_title="Example device manual",
        location="p. 12, Figure 3",
        recommended_section="engineering_analysis",
        usage_note="Only use as product documentation evidence.",
        rights_note="Public vendor document; verify redistribution before external sharing.",
        status=FigureStatus.SELECTED,
    )

    dumped = figure.model_dump(mode="json")

    assert dumped["kind"] == "source_image"
    assert dumped["source_url"] == "https://example.com/manual.pdf"
    assert dumped["location"] == "p. 12, Figure 3"


def test_report_template_renders_figures_and_missing_figure_placeholder() -> None:
    report = SimpleNamespace(
        title="SCS 参数调研",
        subtitle=None,
        core_conclusions=["高频刺激参数需要区分论文证据和厂商资料。"],
        sections=[
            ReportSection(
                section_id="engineering_analysis",
                title="工程换算与产品解释",
                content_markdown="阻抗、电压和电流需要联合解释。",
            ),
            ReportSection(
                section_id="test_plan",
                title="推荐测试方案",
                content_markdown="建议补充台架验证。",
                figure_ids=["fig_missing"],
            ),
        ],
        risks_and_gaps=["厂商资料不能直接等同临床结论。"],
        references=["Example device manual: https://example.com/manual.pdf"],
    )
    figure = FigureAsset(
        title="参数换算示意图",
        caption="用于说明电压、电流和阻抗关系。",
        image_url="https://example.com/conversion.png",
        source_url="https://example.com/manual.pdf",
        source_title="Example manual",
        recommended_section="engineering_analysis",
        status=FigureStatus.SELECTED,
    )

    rendered = render_report_markdown(report, figures=[figure])

    assert "![参数换算示意图](https://example.com/conversion.png)" in rendered
    assert "来源：[Example manual](https://example.com/manual.pdf)" in rendered
    assert "未找到适合本节的来源图" in rendered

