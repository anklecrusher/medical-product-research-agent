"""Evidence facet gap detection and bounded follow-up planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from medical_research_agent.research_planning import (
    FACET_SOURCES,
    EvidenceGap,
    EvidenceGapStatus,
    ResearchFacetKind,
)
from medical_research_agent.schemas import EvidenceItem, SourceRecord, SourceType

if TYPE_CHECKING:
    from medical_research_agent.workflow.state import ResearchPlan, SearchPlanItem

MAX_FOLLOW_UP_ITEMS: Final = 2
FOLLOW_UP_LIMIT: Final = 2
FOLLOW_UP_TERMS: Final[tuple[str, ...]] = (
    "clinician programmer",
    "programmer manual",
    "programming interface",
    "instructions for use",
)
FOLLOW_UP_CONNECTORS: Final[tuple[str, ...]] = ("duckduckgo_html",)
EXCLUDED_REQUIRED_FACETS: Final[set[ResearchFacetKind]] = {
    ResearchFacetKind.GENERIC_BACKGROUND,
    ResearchFacetKind.PRIVATE_LOCAL_DOCS,
}
EVIDENCE_REQUIRED_FACETS: Final[set[ResearchFacetKind]] = {
    ResearchFacetKind.PROGRAMMER_UI,
    ResearchFacetKind.VENDOR_MANUAL,
}


@dataclass(frozen=True, slots=True)
class CoverageInputs:
    plan: ResearchPlan
    sources: list[SourceRecord]
    evidence: list[EvidenceItem]


def detect_evidence_gaps(
    plan: ResearchPlan,
    sources: list[SourceRecord],
    evidence: list[EvidenceItem],
) -> list[EvidenceGap]:
    """Mark required plan facets as covered or still missing."""

    inputs = CoverageInputs(plan=plan, sources=sources, evidence=evidence)
    covered = _covered_facets(inputs)
    gaps: list[EvidenceGap] = []
    for facet in plan.query_expansion.facets:
        if not facet.required or facet.kind in EXCLUDED_REQUIRED_FACETS:
            continue
        status = EvidenceGapStatus.COVERED if facet.kind in covered else EvidenceGapStatus.NEEDS_MORE_SOURCES
        gaps.append(
            EvidenceGap(
                facet=facet.kind,
                status=status,
                description=_gap_description(facet.kind, status),
                required_source_types=FACET_SOURCES[facet.kind],
                recommended_queries=_recommended_terms(plan, facet.kind),
            )
        )
    return gaps


def plan_follow_up_searches(
    plan: ResearchPlan,
    gaps: list[EvidenceGap],
    *,
    follow_up_round: int,
) -> list[SearchPlanItem]:
    """Create bounded gap-cited follow-up searches for manual/UI facets."""

    missing = [
        gap
        for gap in gaps
        if gap.status == EvidenceGapStatus.NEEDS_MORE_SOURCES and _can_follow_up(gap.facet)
    ][:MAX_FOLLOW_UP_ITEMS]
    return [_follow_up_item(plan, gap, follow_up_round) for gap in missing]


def _covered_facets(inputs: CoverageInputs) -> set[ResearchFacetKind]:
    source_by_id = {source.source_id: source for source in inputs.sources}
    covered = {
        _facet
        for source in inputs.sources
        for _facet in _source_facets(source)
        if _facet not in EVIDENCE_REQUIRED_FACETS
    }
    covered.update(
        facet
        for item in inputs.evidence
        for facet in _evidence_facets(item, source_by_id)
    )
    return covered


def _source_facets(source: SourceRecord) -> tuple[ResearchFacetKind, ...]:
    facet = _facet_from_metadata(source.metadata.get("facet"))
    if facet is not None:
        return (facet,)
    return _facets_for_source_type(SourceType(source.source_type))


def _evidence_facets(
    item: EvidenceItem,
    source_by_id: dict[str, SourceRecord],
) -> tuple[ResearchFacetKind, ...]:
    facet = _facet_from_metadata(item.metadata.get("facet"))
    if facet is not None:
        return (facet,)
    source = source_by_id.get(item.source_id)
    if source is None:
        return ()
    return _source_facets(source)


def _facet_from_metadata(value: str | ResearchFacetKind | None) -> ResearchFacetKind | None:
    if value is None:
        return None
    if isinstance(value, ResearchFacetKind):
        return value
    for facet in ResearchFacetKind:
        if facet.value == value:
            return facet
    return None


def _facets_for_source_type(source_type: SourceType) -> tuple[ResearchFacetKind, ...]:
    return tuple(facet for facet, source_types in FACET_SOURCES.items() if source_type in source_types)


def _gap_description(facet: ResearchFacetKind, status: EvidenceGapStatus) -> str:
    if status == EvidenceGapStatus.COVERED:
        return f"Required facet {facet.value} is covered by accepted sources or extracted evidence."
    return f"Missing required facet {facet.value}; targeted follow-up search is needed."


def _recommended_terms(plan: ResearchPlan, facet: ResearchFacetKind) -> tuple[str, ...]:
    facet_terms = tuple(
        term
        for item in plan.query_expansion.facets
        if item.kind == facet
        for term in item.english_terms
    )
    return _unique((*facet_terms, *FOLLOW_UP_TERMS))


def _can_follow_up(facet: ResearchFacetKind) -> bool:
    return facet in {ResearchFacetKind.PROGRAMMER_UI, ResearchFacetKind.VENDOR_MANUAL}


def _follow_up_item(plan: ResearchPlan, gap: EvidenceGap, follow_up_round: int) -> SearchPlanItem:
    from medical_research_agent.workflow.state import SearchPlanItem

    terms = _recommended_terms(plan, gap.facet)
    source_type = _follow_up_source_type(gap)
    return SearchPlanItem(
        query=f"{plan.query_expansion.original_query} {' '.join(terms)}",
        source_type=source_type,
        rationale=f"follow-up for missing {gap.facet.value}: {gap.description}",
        facet=gap.facet,
        expanded_terms=list(terms),
        preferred_connectors=list(FOLLOW_UP_CONNECTORS),
        route_priority=5,
        limit=FOLLOW_UP_LIMIT,
        metadata={
            "follow_up_round": follow_up_round,
            "gap_facet": gap.facet,
            "bounded": True,
        },
    )


def _follow_up_source_type(gap: EvidenceGap) -> SourceType:
    if SourceType.VENDOR_PUBLIC_DOC in gap.required_source_types:
        return SourceType.VENDOR_PUBLIC_DOC
    return SourceType.PUBLIC_WEB


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return tuple(result)
