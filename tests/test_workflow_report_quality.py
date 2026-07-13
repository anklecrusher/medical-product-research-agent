from __future__ import annotations

from medical_research_agent.schemas import (
    Claim,
    ClaimStatus,
    EvidenceItem,
    EvidenceKind,
    ReportSection,
    SourceRecord,
    SourceType,
    TaskStatus,
)
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus
from medical_research_agent.workflow.graph import create_initial_state
from medical_research_agent.workflow.nodes import render_outputs


def test_render_outputs_marks_weak_report_needs_review_with_quality_diagnostics(tmp_path) -> None:
    # Given: source/evidence counts exist but the rendered report is too weak for the quality rubric.
    state = create_initial_state("Research a product", output_dir=tmp_path)
    source = _source("src_weak", SourceType.VENDOR_PUBLIC_DOC)
    state["sources"] = [source]
    state["evidence"] = [_evidence("ev_weak", source.source_id)]
    state["claims"] = [_claim("claim_weak", "ev_weak", source.source_id)]
    state["report_sections"] = [
        ReportSection(
            section_id="weak",
            task_id=state["task"].task_id,
            title="简短说明",
            content_markdown="证据不足。",
            status="draft",
        )
    ]

    # When: the renderer evaluates the completed Markdown/PDF artifacts.
    result = render_outputs(state)

    # Then: quality reasons are persisted and task completion is blocked.
    assert result["task"].status == TaskStatus.NEEDS_REVIEW
    assert result["intermediate"]["report_quality"]["passed"] is False
    assert result["intermediate"]["report_quality"]["reasons"]


def test_render_outputs_marks_good_deep_free_cited_report_completed(tmp_path) -> None:
    # Given: a broad source set, linked supported claim, deep sections, tables, free links, and gap boundaries.
    state = create_initial_state("Research public medical product evidence", output_dir=tmp_path)
    sources = [
        _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC),
        _source("src_literature", SourceType.PUBLIC_LITERATURE),
        _source("src_regulatory", SourceType.PUBLIC_REGULATORY),
    ]
    evidence = [_evidence(f"ev_{index}", source.source_id) for index, source in enumerate(sources, start=1)]
    state["sources"] = sources
    state["evidence"] = evidence
    state["intermediate"] = {"source_quality_status": "has_accepted_sources"}
    state["claims"] = [
        Claim(
            claim_id="claim_supported",
            task_id=state["task"].task_id,
            text="The report has source-linked evidence.",
            evidence_ids=[item.evidence_id for item in evidence],
            source_ids=[source.source_id for source in sources],
            status=ClaimStatus.SUPPORTED,
        )
    ]
    urls = [str(source.url) for source in sources]
    state["report_sections"] = [
        ReportSection(
            section_id="core",
            task_id=state["task"].task_id,
            title="核心结论",
            content_markdown=f"- 产品参数有公开来源支持：{urls[0]}\n- 临床与监管线索需分开解读：{urls[1]}",
            evidence_ids=[evidence[0].evidence_id, evidence[1].evidence_id],
            status="draft",
        ),
        ReportSection(
            section_id="background",
            task_id=state["task"].task_id,
            title="背景与方法",
            content_markdown="本报告按公开来源、证据类型和产品边界整理调研方法。",
            status="draft",
        ),
        ReportSection(
            section_id="product",
            task_id=state["task"].task_id,
            title="产品与技术分析",
            content_markdown="| 参数 | 公开来源 |\n|---|---|\n| 能力 | 已核查 |",
            evidence_ids=[evidence[0].evidence_id],
            status="draft",
        ),
        ReportSection(
            section_id="evidence",
            task_id=state["task"].task_id,
            title="论文与监管证据",
            content_markdown="| 证据类型 | 结论边界 |\n|---|---|\n| 论文 | 非行业共识 |",
            evidence_ids=[evidence[1].evidence_id, evidence[2].evidence_id],
            status="draft",
        ),
        ReportSection(
            section_id="risks",
            task_id=state["task"].task_id,
            title="风险、缺口与未确认项",
            content_markdown="存在未确认信息和证据缺口，结论仍受来源边界约束。",
            status="draft",
        ),
    ]

    # When: the render node evaluates the artifacts through the real quality adapter.
    result = render_outputs(state)

    # Then: all quality dimensions pass and the workflow can complete.
    assert result["task"].status == TaskStatus.COMPLETED, result["intermediate"]["report_quality"]
    assert result["intermediate"]["report_quality"]["passed"] is True
    assert result["intermediate"]["report_quality"]["score"] >= 0.8


def test_render_outputs_preserves_prior_needs_more_sources_when_quality_fails(tmp_path) -> None:
    # Given: an earlier source stage marked the task under-sourced before a weak report was rendered.
    state = create_initial_state("Research a product", output_dir=tmp_path)
    state["task"] = state["task"].model_copy(update={"status": TaskStatus.NEEDS_MORE_SOURCES})
    source = _source("src_weak", SourceType.VENDOR_PUBLIC_DOC)
    state["sources"] = [source]
    state["evidence"] = [_evidence("ev_weak", source.source_id)]
    state["claims"] = [_claim("claim_weak", "ev_weak", source.source_id)]
    state["report_sections"] = [
        ReportSection(
            section_id="weak",
            task_id=state["task"].task_id,
            title="简短说明",
            content_markdown="证据不足。",
            status="draft",
        )
    ]

    # When: the renderer records a quality failure.
    result = render_outputs(state)

    # Then: the earlier under-sourced outcome remains actionable.
    assert result["intermediate"]["report_quality"]["passed"] is False
    assert result["task"].status == TaskStatus.NEEDS_MORE_SOURCES


def test_render_outputs_preserves_prior_failed_status_when_quality_fails(tmp_path) -> None:
    # Given: a fatal upstream failure was already recorded before a weak report was rendered.
    state = create_initial_state("Research a product", output_dir=tmp_path)
    state["task"] = state["task"].model_copy(update={"status": TaskStatus.FAILED})
    source = _source("src_weak", SourceType.VENDOR_PUBLIC_DOC)
    state["sources"] = [source]
    state["evidence"] = [_evidence("ev_weak", source.source_id)]
    state["claims"] = [_claim("claim_weak", "ev_weak", source.source_id)]
    state["report_sections"] = [
        ReportSection(
            section_id="weak",
            task_id=state["task"].task_id,
            title="简短说明",
            content_markdown="证据不足。",
            status="draft",
        )
    ]

    # When: the renderer records a quality failure.
    result = render_outputs(state)

    # Then: quality diagnostics do not downgrade a fatal outcome to a review state.
    assert result["intermediate"]["report_quality"]["passed"] is False
    assert result["task"].status == TaskStatus.FAILED


def _source(source_id: str, source_type: SourceType) -> SourceRecord:
    url = f"https://example.test/{source_id}"
    access = AccessCheck(source_id=source_id, url=url, status=FreeAccessStatus.FREE_LANDING_PAGE)
    return SourceRecord(
        source_id=source_id,
        source_type=source_type,
        title=f"Public {source_type.value} source",
        url=url,
        metadata={
            "access_check": access.model_dump(mode="json"),
            "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
        },
    )


def _evidence(evidence_id: str, source_id: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_id=source_id,
        kind=EvidenceKind.ENGINEERING_NOTE,
        statement="Public source-bound evidence.",
        quote="Public source-bound evidence.",
        location="fixture",
    )


def _claim(claim_id: str, evidence_id: str, source_id: str) -> Claim:
    return Claim(
        claim_id=claim_id,
        text="Weak linked claim.",
        evidence_ids=[evidence_id],
        source_ids=[source_id],
        status=ClaimStatus.SUPPORTED,
    )
