"""Evidence-driven report outline planning."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, assert_never

from medical_research_agent.report_models import ReportInputs
from medical_research_agent.schemas import EvidenceKind, EvidenceStatus, ReportSection, SourceType


SECTION_ID_PREFIX: Final = "outline:"
UI_FACETS: Final = ("programmer_ui", "vendor_manual")
REGULATORY_FACETS: Final = ("regulatory",)
UI_INTENT_TERMS: Final = ("程控", "界面", "ui", "programmer", "interface", "说明书", "手册", "manual", "ifu")
REGULATORY_INTENT_TERMS: Final = ("监管", "注册", "fda", "nmpa", "510(k)", "regulatory")


class ReportSectionKind(StrEnum):
    EXECUTIVE_SUMMARY = "executive_summary"
    TERMINOLOGY_METHOD = "terminology_method"
    PRODUCT_PROGRAMMING = "product_programming"
    UI_INTERFACE = "ui_interface"
    MISSING_UI_MANUAL = "missing_ui_manual"
    PARAMETERS = "parameters"
    VENDOR_COMPARISON = "vendor_comparison"
    LITERATURE_EVIDENCE = "literature_evidence"
    REGULATORY_EVIDENCE = "regulatory_evidence"
    GAPS_RISKS = "gaps_risks"


SECTION_TITLES: Final[dict[ReportSectionKind, str]] = {
    ReportSectionKind.EXECUTIVE_SUMMARY: "执行摘要与证据状态",
    ReportSectionKind.TERMINOLOGY_METHOD: "术语、方法与来源边界",
    ReportSectionKind.PRODUCT_PROGRAMMING: "产品/程控逻辑证据",
    ReportSectionKind.UI_INTERFACE: "程控 UI / 界面资料",
    ReportSectionKind.MISSING_UI_MANUAL: "程控/UI资料缺口与需补充资料",
    ReportSectionKind.PARAMETERS: "参数与产品资料证据",
    ReportSectionKind.VENDOR_COMPARISON: "竞品/厂商资料对照",
    ReportSectionKind.LITERATURE_EVIDENCE: "论文与临床证据",
    ReportSectionKind.REGULATORY_EVIDENCE: "监管资料证据",
    ReportSectionKind.GAPS_RISKS: "风险、缺口与未确认项",
}
_KIND_BY_SECTION_ID: Final = {f"{SECTION_ID_PREFIX}{kind.value}": kind for kind in ReportSectionKind}


def plan_report_outline(inputs: ReportInputs) -> list[ReportSection]:
    """Plan report sections from intent, accepted evidence, source types, and gaps."""

    kinds: list[ReportSectionKind] = [
        ReportSectionKind.EXECUTIVE_SUMMARY,
        ReportSectionKind.TERMINOLOGY_METHOD,
    ]
    if _has_product_programming_support(inputs):
        kinds.append(ReportSectionKind.PRODUCT_PROGRAMMING)
    if _has_ui_manual_support(inputs):
        kinds.append(ReportSectionKind.UI_INTERFACE)
    elif _has_ui_intent_or_gap(inputs):
        kinds.append(ReportSectionKind.MISSING_UI_MANUAL)
    if _has_parameter_support(inputs):
        kinds.append(ReportSectionKind.PARAMETERS)
    if _has_vendor_sources(inputs):
        kinds.append(ReportSectionKind.VENDOR_COMPARISON)
    if _has_literature_evidence(inputs):
        kinds.append(ReportSectionKind.LITERATURE_EVIDENCE)
    if _has_regulatory_support(inputs) or _has_regulatory_intent_or_gap(inputs):
        kinds.append(ReportSectionKind.REGULATORY_EVIDENCE)
    if _has_review_or_gap(inputs):
        kinds.append(ReportSectionKind.GAPS_RISKS)

    return [_section(inputs, kind, order) for order, kind in enumerate(kinds, start=1)]


def report_section_id(kind: ReportSectionKind) -> str:
    """Return the stable semantic section ID used by the report writer."""

    return f"{SECTION_ID_PREFIX}{kind.value}"


def section_kind_from_section(section: ReportSection) -> ReportSectionKind | None:
    """Read the semantic outline kind from a planned report section."""

    return _KIND_BY_SECTION_ID.get(section.section_id)


def _section(inputs: ReportInputs, kind: ReportSectionKind, order: int) -> ReportSection:
    return ReportSection(
        section_id=report_section_id(kind),
        task_id=inputs.task.task_id,
        title=SECTION_TITLES[kind],
        order=order,
        evidence_ids=_evidence_ids_for_kind(inputs, kind),
        status="planned",
    )


def _evidence_ids_for_kind(inputs: ReportInputs, kind: ReportSectionKind) -> list[str]:
    match kind:
        case ReportSectionKind.EXECUTIVE_SUMMARY | ReportSectionKind.TERMINOLOGY_METHOD | ReportSectionKind.GAPS_RISKS:
            return [item.evidence_id for item in inputs.evidence]
        case ReportSectionKind.PRODUCT_PROGRAMMING | ReportSectionKind.PARAMETERS:
            return [item.evidence_id for item in inputs.evidence if _is_product_programming_evidence(inputs, item)]
        case ReportSectionKind.UI_INTERFACE:
            return [item.evidence_id for item in inputs.evidence if _is_ui_manual_evidence(inputs, item)]
        case ReportSectionKind.MISSING_UI_MANUAL:
            return []
        case ReportSectionKind.VENDOR_COMPARISON:
            source_ids = {source.source_id for source in inputs.sources if SourceType(source.source_type) == SourceType.VENDOR_PUBLIC_DOC}
            return [item.evidence_id for item in inputs.evidence if item.source_id in source_ids]
        case ReportSectionKind.LITERATURE_EVIDENCE:
            source_ids = {source.source_id for source in inputs.sources if SourceType(source.source_type) == SourceType.PUBLIC_LITERATURE}
            return [item.evidence_id for item in inputs.evidence if item.source_id in source_ids]
        case ReportSectionKind.REGULATORY_EVIDENCE:
            source_ids = {source.source_id for source in inputs.sources if SourceType(source.source_type) == SourceType.PUBLIC_REGULATORY}
            return [item.evidence_id for item in inputs.evidence if item.source_id in source_ids]
        case unreachable:
            assert_never(unreachable)


def _has_product_programming_support(inputs: ReportInputs) -> bool:
    return any(_is_product_programming_evidence(inputs, item) for item in inputs.evidence)


def _has_ui_manual_support(inputs: ReportInputs) -> bool:
    return any(_is_ui_manual_evidence(inputs, item) for item in inputs.evidence)


def _has_parameter_support(inputs: ReportInputs) -> bool:
    return bool(inputs.product_specs) or any(EvidenceKind(item.kind) == EvidenceKind.PRODUCT_PARAMETER for item in inputs.evidence)


def _has_vendor_sources(inputs: ReportInputs) -> bool:
    return any(SourceType(source.source_type) == SourceType.VENDOR_PUBLIC_DOC for source in inputs.sources)


def _has_literature_evidence(inputs: ReportInputs) -> bool:
    source_ids = {source.source_id for source in inputs.sources if SourceType(source.source_type) == SourceType.PUBLIC_LITERATURE}
    return any(item.source_id in source_ids for item in inputs.evidence)


def _has_regulatory_support(inputs: ReportInputs) -> bool:
    return any(
        EvidenceKind(item.kind) == EvidenceKind.REGULATORY_FINDING or _source_type_for_evidence(inputs, item) == SourceType.PUBLIC_REGULATORY
        for item in inputs.evidence
    )


def _has_ui_intent_or_gap(inputs: ReportInputs) -> bool:
    return _query_contains(inputs, UI_INTENT_TERMS) or any(gap.facet in UI_FACETS for gap in inputs.evidence_gaps)


def _has_regulatory_intent_or_gap(inputs: ReportInputs) -> bool:
    return _query_contains(inputs, REGULATORY_INTENT_TERMS) or any(gap.facet in REGULATORY_FACETS for gap in inputs.evidence_gaps)


def _has_review_or_gap(inputs: ReportInputs) -> bool:
    return bool(inputs.evidence_gaps) or any(
        EvidenceStatus(item.status) in {EvidenceStatus.NEEDS_REVIEW, EvidenceStatus.CONFLICTING}
        for item in inputs.evidence
    )


def _is_product_programming_evidence(inputs: ReportInputs, item) -> bool:
    source_type = _source_type_for_evidence(inputs, item)
    return EvidenceKind(item.kind) == EvidenceKind.PRODUCT_PARAMETER and source_type != SourceType.PUBLIC_LITERATURE


def _is_ui_manual_evidence(inputs: ReportInputs, item) -> bool:
    source_type = _source_type_for_evidence(inputs, item)
    return source_type in {SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_WEB, SourceType.USER_UPLOADED_PRIVATE, SourceType.INTERNAL_PRIVATE} and (
        _metadata_facet(item.metadata) in UI_FACETS or _text_contains(item.statement, UI_INTENT_TERMS)
    )


def _source_type_for_evidence(inputs: ReportInputs, item) -> SourceType | None:
    source = next((source for source in inputs.sources if source.source_id == item.source_id), None)
    if source is None:
        return None
    return SourceType(source.source_type)


def _metadata_facet(metadata) -> str:
    return str(metadata.get("facet", ""))


def _query_contains(inputs: ReportInputs, terms: tuple[str, ...]) -> bool:
    return _text_contains(inputs.task.query, terms)


def _text_contains(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)
