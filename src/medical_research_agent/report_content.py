"""Template-facing report content assembly."""

from __future__ import annotations

from dataclasses import dataclass

from medical_research_agent.report_models import EvidenceGapReportItem, ReportInputs
from medical_research_agent.schemas import EvidenceStatus, ReportSection, SourceRecord, SourceType


@dataclass(frozen=True, slots=True)
class RenderReport:
    title: str
    subtitle: str
    core_conclusions: list[str]
    sections: list[ReportSection]
    risks_and_gaps: list[str]
    references: list[str]


def build_render_report(inputs: ReportInputs) -> RenderReport:
    """Build the template-facing report object from evidence-backed sections."""

    return RenderReport(
        title=inputs.task.title or inputs.task.query[:36] or "医疗产品调研报告",
        subtitle=f"任务 ID：{inputs.task.task_id}",
        core_conclusions=_core_conclusions(inputs),
        sections=inputs.planned_sections,
        risks_and_gaps=_risks_and_gaps(inputs),
        references=_references(inputs.sources),
    )


def _core_conclusions(inputs: ReportInputs) -> list[str]:
    missing_gaps = _unresolved_gap_messages(inputs.evidence_gaps)
    if not inputs.evidence:
        conclusions = ["证据不足：当前 workflow 未获得可用来源证据，全部结论保持 needs_review。"]
        conclusions.extend(missing_gaps)
        return conclusions

    conclusions = [
        f"本次草稿整理了 {len(inputs.evidence)} 条证据和 {len(inputs.product_specs)} 条产品参数，所有关键表述需回到 evidence_id/source_id 核查。",
        "厂商参数、论文发现、监管资料和本地资料已分开呈现；不同来源类型不能互相替代。",
    ]
    conclusions.extend(missing_gaps)
    review_count = sum(
        1
        for item in inputs.evidence
        if EvidenceStatus(item.status) in {EvidenceStatus.NEEDS_REVIEW, EvidenceStatus.CONFLICTING}
    )
    if review_count:
        conclusions.append(f"仍有 {review_count} 条证据为 needs_review 或 conflicting，不能写成确定结论。")
    return conclusions


def _risks_and_gaps(inputs: ReportInputs) -> list[str]:
    missing_gaps = _unresolved_gap_messages(inputs.evidence_gaps)
    if not inputs.evidence:
        return ["证据不足：未形成可核查来源链路，needs_review。", *missing_gaps]

    risks = [
        "参数表只表达来源原文中的数值或范围，不自动等同于产品规格上限、临床处方或注册承诺。",
        "厂商公开资料、公开网页和论文证据必须分开解释；宣传材料不能当作临床结论。",
    ]
    if any(EvidenceStatus(item.status) == EvidenceStatus.CONFLICTING for item in inputs.evidence):
        risks.append("存在 conflicting 参数证据，需保留冲突并回看原始来源。")
    if any(EvidenceStatus(item.status) == EvidenceStatus.NEEDS_REVIEW for item in inputs.evidence):
        risks.append("存在 needs_review 条目，需补充资料或人工确认后再用于决策。")
    risks.extend(missing_gaps)
    return risks


def _unresolved_gap_messages(gaps: list[EvidenceGapReportItem]) -> list[str]:
    return [
        f"{gap.description} status={gap.status}; facet={gap.facet}; required_source_types={', '.join(gap.required_source_types)}"
        for gap in gaps
        if gap.status == "needs_more_sources"
    ]


def _references(sources: list[SourceRecord]) -> list[str]:
    refs: list[str] = []
    for source in sources:
        ref = f"{source.source_id} [{SourceType(source.source_type).value}] {source.title}"
        if source.url:
            ref = f"{ref}: {source.url}"
        elif source.local_path:
            ref = f"{ref}: {source.local_path}"
        refs.append(ref)
    return refs
