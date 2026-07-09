"""Evidence-driven report section and claim assembly."""

from __future__ import annotations

from dataclasses import dataclass

from medical_research_agent.report_models import ReportIndexes, ReportInputs
from medical_research_agent.report_outline import ReportSectionKind, section_kind_from_section
from medical_research_agent.report_sections import parameter_section, review_section, source_boundary_section
from medical_research_agent.report_semantic_sections import (
    executive_summary_section,
    literature_section,
    missing_ui_manual_section,
    product_programming_section,
    regulatory_section,
    terminology_method_section,
    ui_interface_section,
    vendor_comparison_section,
)
from medical_research_agent.schemas import (
    Claim,
    ClaimStatus,
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ReportSection,
    ResearchTask,
)


@dataclass(frozen=True, slots=True)
class ReportDraft:
    sections: list[ReportSection]
    claims: list[Claim]


def draft_evidence_report(inputs: ReportInputs) -> ReportDraft:
    """Fill planned sections and claims from source-linked evidence."""

    indexes = _indexes(inputs)
    claims = _claims(inputs)
    sections = [_draft_section(section, inputs, indexes, claims) for section in inputs.planned_sections]
    return ReportDraft(sections=sections, claims=claims)


def _indexes(inputs: ReportInputs) -> ReportIndexes:
    return ReportIndexes(
        source_by_id={source.source_id: source for source in inputs.sources},
        evidence_by_id={item.evidence_id: item for item in inputs.evidence},
    )


def _draft_section(
    section: ReportSection,
    inputs: ReportInputs,
    indexes: ReportIndexes,
    claims: list[Claim],
) -> ReportSection:
    kind = section_kind_from_section(section)
    if kind is not None:
        return _draft_section_with_content(section, _content_for_kind(kind, inputs, indexes), claims)
    return _draft_legacy_section(section, inputs, indexes, claims)


def _content_for_kind(kind: ReportSectionKind, inputs: ReportInputs, indexes: ReportIndexes) -> str:
    match kind:
        case ReportSectionKind.EXECUTIVE_SUMMARY:
            return executive_summary_section(inputs)
        case ReportSectionKind.TERMINOLOGY_METHOD:
            return terminology_method_section(inputs)
        case ReportSectionKind.PRODUCT_PROGRAMMING:
            return product_programming_section(inputs, indexes)
        case ReportSectionKind.UI_INTERFACE:
            return ui_interface_section(inputs, indexes)
        case ReportSectionKind.MISSING_UI_MANUAL:
            return missing_ui_manual_section(inputs)
        case ReportSectionKind.PARAMETERS:
            return parameter_section(inputs, indexes)
        case ReportSectionKind.VENDOR_COMPARISON:
            return vendor_comparison_section(inputs, indexes)
        case ReportSectionKind.LITERATURE_EVIDENCE:
            return literature_section(inputs, indexes)
        case ReportSectionKind.REGULATORY_EVIDENCE:
            return regulatory_section(inputs, indexes)
        case ReportSectionKind.GAPS_RISKS:
            return review_section(inputs, indexes)
        case unreachable:
            assert_never(unreachable)


def _draft_legacy_section(
    section: ReportSection,
    inputs: ReportInputs,
    indexes: ReportIndexes,
    claims: list[Claim],
) -> ReportSection:
    if section.order == 1:
        return _draft_section_with_content(section, parameter_section(inputs, indexes), claims)
    if section.order == 2:
        return _draft_section_with_content(section, source_boundary_section(inputs), claims)
    return _draft_section_with_content(section, review_section(inputs, indexes), claims)


def _draft_section_with_content(
    section: ReportSection,
    content: str,
    claims: list[Claim],
) -> ReportSection:
    return section.model_copy(
        update={
            "content_markdown": content,
            "claim_ids": [claim.claim_id for claim in claims],
            "status": "draft",
        },
    )


def _claims(inputs: ReportInputs) -> list[Claim]:
    parameter_evidence = [item for item in inputs.evidence if EvidenceKind(item.kind) == EvidenceKind.PRODUCT_PARAMETER]
    review_evidence = [
        item
        for item in inputs.evidence
        if EvidenceStatus(item.status) in {EvidenceStatus.NEEDS_REVIEW, EvidenceStatus.CONFLICTING}
    ]

    claims: list[Claim] = []
    if parameter_evidence:
        claims.append(
            _claim(
                inputs.task,
                "已从来源证据中抽取产品参数；这些数值按原始来源整理，不能直接外推为临床或注册结论。",
                parameter_evidence,
                ClaimStatus.DRAFT,
            )
        )
    if inputs.sources:
        claims.append(
            Claim(
                task_id=inputs.task.task_id,
                text="报告按来源类型区分公开论文、厂商资料、监管资料、公开网页和本地资料的使用边界。",
                evidence_ids=[item.evidence_id for item in inputs.evidence],
                source_ids=[source.source_id for source in inputs.sources],
                status=ClaimStatus.DRAFT,
            )
        )
    if review_evidence:
        claims.append(
            _claim(
                inputs.task,
                "存在 needs_review 或 conflicting 证据，相关结论需要人工复核后才能用于产品决策。",
                review_evidence,
                ClaimStatus.NEEDS_REVIEW,
            )
        )
    if not claims:
        claims.append(_insufficient_evidence_claim(inputs.task))
    return claims


def _claim(
    task: ResearchTask,
    text: str,
    evidence: list[EvidenceItem],
    status: ClaimStatus,
) -> Claim:
    return Claim(
        task_id=task.task_id,
        text=text,
        evidence_ids=[item.evidence_id for item in evidence],
        source_ids=[item.source_id for item in evidence],
        status=status,
    )


def _insufficient_evidence_claim(task: ResearchTask) -> Claim:
    return Claim(
        task_id=task.task_id,
        text="当前没有可用来源或证据，报告只能作为 needs_review 占位草稿。",
        status=ClaimStatus.NEEDS_REVIEW,
        verification_note="缺少 evidence_ids 和 source_ids。",
    )
