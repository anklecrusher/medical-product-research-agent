from __future__ import annotations

from dataclasses import replace

from medical_research_agent.report_models import EvidenceGapReportItem, ReportInputs
from medical_research_agent.report_outline import plan_report_outline
from medical_research_agent.report_writer import draft_evidence_report
from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ProductSpec,
    ResearchTask,
    SourceRecord,
    SourceType,
)


def test_plan_report_outline_includes_ui_programming_sections_when_manual_evidence_exists() -> None:
    # Given: accepted vendor/manual evidence and separate literature evidence for a UI/programming topic.
    task = ResearchTask(query="调研 DBS 程控界面和 clinician programmer manual")
    vendor_source = SourceRecord(
        source_id="src_vendor_manual",
        task_id=task.task_id,
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="DBS clinician programmer manual",
        metadata={"facet": "programmer_ui"},
    )
    literature_source = SourceRecord(
        source_id="src_literature",
        task_id=task.task_id,
        source_type=SourceType.PUBLIC_LITERATURE,
        title="DBS programming clinical literature",
        metadata={"facet": "clinical_study"},
    )
    manual_evidence = EvidenceItem(
        evidence_id="ev_manual_ui",
        task_id=task.task_id,
        source_id=vendor_source.source_id,
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement="Manual shows clinician programmer screen with frequency 130 Hz.",
        value="130",
        unit="Hz",
        product_name="DBS clinician programmer",
        parameter_name="stimulation_frequency",
        metadata={"facet": "programmer_ui"},
    )
    literature_evidence = EvidenceItem(
        evidence_id="ev_literature",
        task_id=task.task_id,
        source_id=literature_source.source_id,
        kind=EvidenceKind.CLINICAL_FINDING,
        statement="Clinical paper discusses DBS programming follow-up.",
        metadata={"facet": "clinical_study"},
    )
    inputs = ReportInputs(
        task=task,
        planned_sections=[],
        sources=[vendor_source, literature_source],
        documents=[],
        evidence=[manual_evidence, literature_evidence],
        product_specs=[
            ProductSpec(
                task_id=task.task_id,
                product_name="DBS clinician programmer",
                parameter_name="stimulation_frequency",
                value="130",
                unit="Hz",
                source_ids=[vendor_source.source_id],
                evidence_ids=[manual_evidence.evidence_id],
            )
        ],
    )

    # When: the outline is planned and the report writer fills the sections.
    planned = plan_report_outline(inputs)
    draft = draft_evidence_report(replace(inputs, planned_sections=planned))

    # Then: product/UI sections are present and vendor/manual evidence is not buried as literature.
    section_titles = [section.title for section in planned]
    rendered_by_title = {section.title: section.content_markdown for section in draft.sections}
    literature_content = "\n".join(
        content for title, content in rendered_by_title.items() if "论文" in title or "文献" in title
    )

    assert any("程控" in title or "UI" in title or "界面" in title for title in section_titles)
    assert any("产品/程控逻辑" in title for title in section_titles)
    assert "Manual shows clinician programmer screen" in "\n".join(rendered_by_title.values())
    assert "src_vendor_manual" not in literature_content
    assert "vendor_public_doc" in "\n".join(rendered_by_title.values())


def test_plan_report_outline_marks_missing_ui_manual_gaps_without_complete_ui_claim() -> None:
    # Given: a UI/programming topic with literature evidence but unresolved programmer/manual gaps.
    task = ResearchTask(query="调研 DBS 程控界面和说明书")
    literature_source = SourceRecord(
        source_id="src_literature",
        task_id=task.task_id,
        source_type=SourceType.PUBLIC_LITERATURE,
        title="DBS programming clinical literature",
        metadata={"facet": "clinical_study"},
    )
    literature_evidence = EvidenceItem(
        evidence_id="ev_literature",
        task_id=task.task_id,
        source_id=literature_source.source_id,
        kind=EvidenceKind.CLINICAL_FINDING,
        statement="Clinical paper discusses DBS programming follow-up.",
        status=EvidenceStatus.EXTRACTED,
        metadata={"facet": "clinical_study"},
    )
    inputs = ReportInputs(
        task=task,
        planned_sections=[],
        sources=[literature_source],
        documents=[],
        evidence=[literature_evidence],
        product_specs=[],
        evidence_gaps=[
            EvidenceGapReportItem(
                facet="programmer_ui",
                status="needs_more_sources",
                description="Missing required facet programmer_ui; targeted follow-up search is needed.",
                required_source_types=("vendor_public_doc", "public_web"),
                recommended_queries=("clinician programmer", "programming interface"),
            ),
            EvidenceGapReportItem(
                facet="vendor_manual",
                status="needs_more_sources",
                description="Missing required facet vendor_manual; targeted follow-up search is needed.",
                required_source_types=("vendor_public_doc", "public_web"),
                recommended_queries=("programmer manual", "instructions for use"),
            ),
        ],
    )

    # When: the outline is planned and drafted.
    planned = plan_report_outline(inputs)
    draft = draft_evidence_report(replace(inputs, planned_sections=planned))
    rendered = "\n".join(section.content_markdown for section in draft.sections)

    # Then: the report has explicit missing-evidence language and no completed UI claim.
    assert any("缺口" in section.title or "未确认" in section.title for section in planned)
    assert "Missing required facet programmer_ui" in rendered
    assert "Missing required facet vendor_manual" in rendered
    assert "需补充资料" in rendered or "未确认" in rendered
    assert "程控/UI证据已覆盖" not in rendered
