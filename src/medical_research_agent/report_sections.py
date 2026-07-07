"""Evidence-driven report section table rendering."""

from __future__ import annotations

from typing import Final, assert_never

from medical_research_agent.report_models import ReportIndexes, ReportInputs
from medical_research_agent.schemas import EvidenceItem, EvidenceKind, EvidenceStatus, ProductSpec, SourceType


MAX_TABLE_TEXT: Final = 96


def parameter_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render the product parameter/evidence table."""

    if not inputs.product_specs:
        return "证据不足：当前来源未抽取到可用产品参数表，needs_review。"

    rows = [
        "| 参数/主题 | 证据摘要 | 数值 | 来源类型 | 证据状态 | 证据ID |",
        "|---|---|---:|---|---|---|",
    ]
    for spec in inputs.product_specs:
        evidence = _first_evidence(spec.evidence_ids, indexes)
        rows.append(_parameter_row(spec, evidence, indexes))
    return "\n".join(rows)


def source_boundary_section(inputs: ReportInputs) -> str:
    """Render source type counts and allowed-use boundaries."""

    if not inputs.sources:
        return "证据不足：未检索到来源，所有工程解释均应保持 needs_review。"

    rows = [
        "不同来源只能支持不同强度的产品判断；厂商资料不等同于临床结论，单篇论文不等同于行业共识。",
        "",
        "| 来源类型 | 来源数 | 证据数 | 使用边界 |",
        "|---|---:|---:|---|",
    ]
    for source_type in _source_type_order():
        rows.extend(_source_type_row(source_type, inputs))

    if _has_private_source(inputs):
        rows.append("")
        rows.append("- 私有或内部资料仅用于本地整理；报告中保留 local_only 边界，不作为外部 LLM 处理依据。")
    return "\n".join(rows)


def review_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render regulatory, conflicting, and needs-review evidence."""

    review_items = [
        item
        for item in inputs.evidence
        if EvidenceStatus(item.status) in {EvidenceStatus.NEEDS_REVIEW, EvidenceStatus.CONFLICTING}
        or EvidenceKind(item.kind) == EvidenceKind.REGULATORY_FINDING
    ]
    if not review_items:
        return "暂未发现监管资料或显式冲突；仍需人工复核来源完整性，needs_review。"

    rows = [
        "| 未确认/监管项 | 来源类型 | 状态 | 证据ID |",
        "|---|---|---|---|",
    ]
    for item in review_items:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(item.statement),
                    _cell(_source_type_for_evidence(item, indexes)),
                    _cell(str(item.status)),
                    item.evidence_id,
                ]
            )
            + " |"
        )
    rows.append("")
    rows.append("以上条目不得直接写成临床、注册或工程定论；needs_review 项必须补充来源或人工判断。")
    return "\n".join(rows)


def _parameter_row(spec: ProductSpec, evidence: EvidenceItem | None, indexes: ReportIndexes) -> str:
    return (
        "| "
        + " | ".join(
            [
                _cell(f"{spec.product_name} / {spec.parameter_name}"),
                _cell(evidence.statement if evidence else spec.notes or "needs_review"),
                _cell(_value_with_unit(spec)),
                _cell(_source_types(spec.source_ids, indexes)),
                _cell(str(spec.status)),
                _cell(", ".join(spec.evidence_ids)),
            ]
        )
        + " |"
    )


def _source_type_row(source_type: SourceType, inputs: ReportInputs) -> list[str]:
    sources = [source for source in inputs.sources if SourceType(source.source_type) == source_type]
    if not sources:
        return []

    source_ids = {source.source_id for source in sources}
    evidence_count = sum(1 for item in inputs.evidence if item.source_id in source_ids)
    return [
        "| "
        + " | ".join(
            [
                source_type.value,
                str(len(sources)),
                str(evidence_count),
                _source_boundary_note(source_type),
            ]
        )
        + " |"
    ]


def _source_type_order() -> list[SourceType]:
    return [
        SourceType.PUBLIC_LITERATURE,
        SourceType.VENDOR_PUBLIC_DOC,
        SourceType.PUBLIC_REGULATORY,
        SourceType.PUBLIC_WEB,
        SourceType.USER_UPLOADED_PRIVATE,
        SourceType.INTERNAL_PRIVATE,
    ]


def _source_boundary_note(source_type: SourceType) -> str:
    match source_type:
        case SourceType.PUBLIC_LITERATURE:
            return "支持论文或临床研究背景，单篇不能代表共识"
        case SourceType.VENDOR_PUBLIC_DOC:
            return "支持产品参数和厂商口径，不支持临床有效性结论"
        case SourceType.PUBLIC_REGULATORY:
            return "支持注册或监管语境，不等同于性能优越性"
        case SourceType.PUBLIC_WEB:
            return "支持市场线索，需二次核查"
        case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
            return "本地资料，仅在授权边界内使用"
        case unreachable:
            assert_never(unreachable)


def _first_evidence(evidence_ids: list[str], indexes: ReportIndexes) -> EvidenceItem | None:
    for evidence_id in evidence_ids:
        item = indexes.evidence_by_id.get(evidence_id)
        if item is not None:
            return item
    return None


def _source_types(source_ids: list[str], indexes: ReportIndexes) -> str:
    values = []
    for source_id in source_ids:
        source = indexes.source_by_id.get(source_id)
        if source is not None:
            values.append(SourceType(source.source_type).value)
    return ", ".join(dict.fromkeys(values)) or "needs_review"


def _source_type_for_evidence(item: EvidenceItem, indexes: ReportIndexes) -> str:
    source = indexes.source_by_id.get(item.source_id)
    if source is None:
        return "needs_review"
    return SourceType(source.source_type).value


def _value_with_unit(spec: ProductSpec) -> str:
    if spec.unit:
        return f"{spec.value} {spec.unit}"
    return str(spec.value)


def _cell(value: str) -> str:
    text = " ".join(value.split()).replace("|", "/")
    if len(text) <= MAX_TABLE_TEXT:
        return text
    return f"{text[: MAX_TABLE_TEXT - 3]}..."


def _has_private_source(inputs: ReportInputs) -> bool:
    return any(
        SourceType(source.source_type) in {SourceType.USER_UPLOADED_PRIVATE, SourceType.INTERNAL_PRIVATE}
        for source in inputs.sources
    )
