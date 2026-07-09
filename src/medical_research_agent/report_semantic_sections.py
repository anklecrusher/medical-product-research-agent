"""Semantic report sections selected by the outline planner."""

from __future__ import annotations

from typing import Final

from medical_research_agent.report_models import EvidenceGapReportItem, ReportIndexes, ReportInputs
from medical_research_agent.schemas import EvidenceItem, EvidenceKind, SourceType


MAX_TABLE_TEXT: Final = 96
UI_FACETS: Final = {"programmer_ui", "vendor_manual"}


def executive_summary_section(inputs: ReportInputs) -> str:
    """Render evidence counts and high-level completion status."""

    rows = [
        f"- 已接受来源：{len(inputs.sources)} 个；结构化证据：{len(inputs.evidence)} 条；产品参数：{len(inputs.product_specs)} 条。",
        "- 报告只按已接受来源和显式缺口组织内容；未覆盖分面保留 needs_review。",
    ]
    if inputs.evidence_gaps:
        unresolved = [gap for gap in inputs.evidence_gaps if gap.status == "needs_more_sources"]
        rows.append(f"- 未解决证据缺口：{len(unresolved)} 个。")
    if not inputs.evidence:
        rows.append("- 证据不足：当前没有可用 evidence_id，不能形成完整产品结论。")
    return "\n".join(rows)


def terminology_method_section(inputs: ReportInputs) -> str:
    """Render query intent and source-method boundaries."""

    source_types = ", ".join(dict.fromkeys(SourceType(source.source_type).value for source in inputs.sources))
    if not source_types:
        source_types = "未形成接受来源"
    return "\n".join(
        [
            f"- 原始需求：{inputs.task.query}",
            f"- 接受来源类型：{source_types}",
            "- 章节按来源类型、证据类型和 evidence gap 生成；厂商手册、论文、监管资料不互相替代。",
        ]
    )


def product_programming_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render vendor/manual product or programming logic evidence only."""

    product_items = _product_programming_items(inputs, indexes)
    if not product_items:
        return "未确认：当前没有厂商/手册/公开产品资料支持的程控或产品逻辑证据，需补充资料。"
    return _evidence_table(product_items, indexes, "产品/程控证据")


def ui_interface_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render UI/interface evidence from manual-like accepted sources."""

    ui_items = _ui_manual_items(inputs, indexes)
    if not ui_items:
        return missing_ui_manual_section(inputs)
    rows = [
        "以下只列出来自厂商手册、公开产品资料或本地授权资料的 UI/程控界面线索；论文证据不在本节充当产品界面证据。",
        "",
        _evidence_table(ui_items, indexes, "UI/程控资料"),
    ]
    return "\n".join(rows)


def missing_ui_manual_section(inputs: ReportInputs) -> str:
    """Render explicit missing evidence text for UI/programmer/manual facets."""

    gaps = [gap for gap in inputs.evidence_gaps if gap.facet in UI_FACETS and gap.status == "needs_more_sources"]
    if not gaps:
        return "未确认：题目涉及程控/UI/说明书，但当前未抽取到可用手册或界面证据，需补充资料。"
    return "\n".join(_gap_lines(gaps))


def vendor_comparison_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render vendor evidence as product/vendor material, not literature."""

    vendor_items = [
        item for item in inputs.evidence if _source_type_for_evidence(item, indexes) == SourceType.VENDOR_PUBLIC_DOC.value
    ]
    if not vendor_items:
        return "未确认：当前没有 accepted 厂商公开资料，无法形成竞品/厂商表。"
    return _evidence_table(vendor_items, indexes, "厂商资料")


def literature_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render literature evidence without promoting it into product/manual evidence."""

    literature_items = [
        item for item in inputs.evidence if _source_type_for_evidence(item, indexes) == SourceType.PUBLIC_LITERATURE.value
    ]
    if not literature_items:
        return "未确认：当前没有 accepted 论文证据。"
    return _evidence_table(literature_items, indexes, "论文/临床证据")


def regulatory_section(inputs: ReportInputs, indexes: ReportIndexes) -> str:
    """Render regulatory evidence or explicit regulatory gaps."""

    regulatory_items = [
        item
        for item in inputs.evidence
        if EvidenceKind(item.kind) == EvidenceKind.REGULATORY_FINDING
        or _source_type_for_evidence(item, indexes) == SourceType.PUBLIC_REGULATORY.value
    ]
    if regulatory_items:
        return _evidence_table(regulatory_items, indexes, "监管资料")
    regulatory_gaps = [gap for gap in inputs.evidence_gaps if gap.facet == "regulatory"]
    if regulatory_gaps:
        return "\n".join(_gap_lines(regulatory_gaps))
    return "未确认：当前没有监管资料证据，不能写成注册或合规结论。"


def _evidence_table(items: list[EvidenceItem], indexes: ReportIndexes, label: str) -> str:
    rows = [
        f"| {label} | 来源类型 | 状态 | 证据ID |",
        "|---|---|---|---|",
    ]
    for item in items:
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
    return "\n".join(rows)


def _gap_lines(gaps: list[EvidenceGapReportItem]) -> list[str]:
    lines = ["未确认/需补充资料：以下分面缺少 accepted 手册、UI 或监管证据，不能写成完整结论。"]
    for gap in gaps:
        lines.append(
            f"- {gap.description} status={gap.status}; facet={gap.facet}; "
            f"required_source_types={', '.join(gap.required_source_types)}"
        )
    return lines


def _product_programming_items(inputs: ReportInputs, indexes: ReportIndexes) -> list[EvidenceItem]:
    return [
        item
        for item in inputs.evidence
        if EvidenceKind(item.kind) == EvidenceKind.PRODUCT_PARAMETER
        and _source_type_for_evidence(item, indexes) != SourceType.PUBLIC_LITERATURE.value
    ]


def _ui_manual_items(inputs: ReportInputs, indexes: ReportIndexes) -> list[EvidenceItem]:
    allowed_source_types = {
        SourceType.VENDOR_PUBLIC_DOC.value,
        SourceType.PUBLIC_WEB.value,
        SourceType.USER_UPLOADED_PRIVATE.value,
        SourceType.INTERNAL_PRIVATE.value,
    }
    return [
        item
        for item in inputs.evidence
        if _source_type_for_evidence(item, indexes) in allowed_source_types
        and (_metadata_facet(item) in UI_FACETS or _has_ui_text(item.statement))
    ]


def _source_type_for_evidence(item: EvidenceItem, indexes: ReportIndexes) -> str:
    source = indexes.source_by_id.get(item.source_id)
    if source is None:
        return "needs_review"
    return SourceType(source.source_type).value


def _metadata_facet(item: EvidenceItem) -> str:
    return str(item.metadata.get("facet", ""))


def _has_ui_text(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in ("programmer", "interface", "ui", "程控", "界面", "manual", "说明书"))


def _cell(value: str) -> str:
    text = " ".join(value.split()).replace("|", "/")
    if len(text) <= MAX_TABLE_TEXT:
        return text
    return f"{text[: MAX_TABLE_TEXT - 3]}..."
