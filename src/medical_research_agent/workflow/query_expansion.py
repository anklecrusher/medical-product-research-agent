"""Workflow adapter for deterministic query-expansion plans."""

from __future__ import annotations

from typing import Final, Iterable, Mapping, TypeVar, assert_never

from medical_research_agent.research_planning import (
    QueryExpansionPlan,
    ResearchFacetKind,
    SearchRoute,
    TerminologyCategory,
)
from medical_research_agent.schemas import SourceType
from medical_research_agent.workflow.state import SearchPlanItem

T = TypeVar("T")

PROGRAMMER_SEARCH_TERMS: Final[tuple[str, ...]] = (
    "clinician programmer",
    "programming interface",
    "SCS programmer",
    "DBS programmer",
)
DBS_TERMS: Final[tuple[str, ...]] = ("deep brain stimulation", "DBS programmer")
SCS_TERMS: Final[tuple[str, ...]] = ("spinal cord stimulation", "SCS programmer")
INTERLEAVING_TERMS: Final[tuple[str, ...]] = ("interleaving stimulation",)
DBS_HINTS: Final[tuple[str, ...]] = ("dbs", "deep brain stimulation", "脑深部")
SCS_HINTS: Final[tuple[str, ...]] = ("scs", "spinal cord stimulation", "脊髓")
INTERLEAVING_HINTS: Final[tuple[str, ...]] = ("interleaving", "交叉刺激")
LITERATURE_HINTS: Final[tuple[str, ...]] = ("literature evidence", "clinical study")
VENDOR_HINTS: Final[tuple[str, ...]] = ("programmer manual", "instructions for use", "technical manual")
REGULATORY_HINTS: Final[tuple[str, ...]] = ("FDA 510(k)", "regulatory clearance", "product code")
CONNECTORS_BY_SOURCE_TYPE: Final[Mapping[SourceType, tuple[str, ...]]] = {
    SourceType.PUBLIC_LITERATURE: ("pubmed", "crossref", "semantic_scholar"),
    SourceType.PUBLIC_WEB: ("duckduckgo_html",),
    SourceType.PUBLIC_REGULATORY: ("openfda_510k", "clinicaltrials_gov", "duckduckgo_html"),
    SourceType.VENDOR_PUBLIC_DOC: ("duckduckgo_html",),
    SourceType.USER_UPLOADED_PRIVATE: ("local_upload",),
    SourceType.INTERNAL_PRIVATE: ("local_private_index",),
}
SUPPLEMENTAL_MEDICAL_ROUTES: Final[tuple[tuple[ResearchFacetKind, SourceType, int, str], ...]] = (
    (ResearchFacetKind.CLINICAL_STUDY, SourceType.PUBLIC_LITERATURE, 35, "补充论文、临床研究和参数范围证据。"),
    (ResearchFacetKind.REGULATORY, SourceType.PUBLIC_REGULATORY, 40, "补充监管、注册和产品代码资料线索。"),
)


def focus_terms_from_expansion(plan: QueryExpansionPlan) -> list[str]:
    """Return concise terms for the intent snapshot without inventing domains."""

    if _is_generic(plan):
        return ["通用背景"]
    return list(_unique((*plan.chinese_terms, *plan.english_terms[:4])))


def source_types_from_expansion(plan: QueryExpansionPlan) -> list[SourceType]:
    """Return connector source types requested by the expansion plan."""

    return list(_unique(item.source_type for item in build_search_items_from_expansion(plan)))


def build_search_items_from_expansion(plan: QueryExpansionPlan) -> list[SearchPlanItem]:
    """Expand facet routes into connector-ready search items without losing intent."""

    if _is_generic(plan):
        return [
            SearchPlanItem(
                query=plan.original_query,
                source_type=SourceType.PUBLIC_WEB,
                rationale="通用背景题目，先使用公开网页来源并等待人工确认研究分面。",
                facet=ResearchFacetKind.GENERIC_BACKGROUND,
                preferred_connectors=list(CONNECTORS_BY_SOURCE_TYPE[SourceType.PUBLIC_WEB]),
                route_priority=90,
                limit=2,
            )
        ]

    search_items = [
        item
        for route in sorted(plan.search_routes, key=lambda item: item.priority)
        for item in _items_for_route(plan, route)
    ]
    return _with_supplemental_routes(plan, search_items)


def _is_generic(plan: QueryExpansionPlan) -> bool:
    return plan.facets[0].kind == ResearchFacetKind.GENERIC_BACKGROUND


def _terms_for_query(plan: QueryExpansionPlan, hints: tuple[str, ...]) -> tuple[str, ...]:
    recognized_hints = _programmer_terms(plan, hints)
    return _unique((*recognized_hints, *_domain_terms(plan, plan.english_terms)))


def _items_for_route(plan: QueryExpansionPlan, route: SearchRoute) -> tuple[SearchPlanItem, ...]:
    return tuple(
        SearchPlanItem(
            query=_compose_query(plan.original_query, terms),
            source_type=source_type,
            rationale=route.rationale,
            facet=route.facet,
            expanded_terms=list(terms),
            preferred_connectors=list(CONNECTORS_BY_SOURCE_TYPE[source_type]),
            route_priority=route.priority,
            limit=_limit_for_source_type(source_type),
        )
        for source_type in route.source_types
        for terms in (_terms_for_facet_source(plan, route.facet, source_type),)
    )


def _with_supplemental_routes(
    plan: QueryExpansionPlan,
    search_items: list[SearchPlanItem],
) -> list[SearchPlanItem]:
    requested_pairs = {(item.facet, item.source_type) for item in search_items}
    supplemental_items = [
        SearchPlanItem(
            query=_compose_query(plan.original_query, _terms_for_facet_source(plan, facet, source_type)),
            source_type=source_type,
            rationale=rationale,
            facet=facet,
            expanded_terms=list(_terms_for_facet_source(plan, facet, source_type)),
            preferred_connectors=list(CONNECTORS_BY_SOURCE_TYPE[source_type]),
            route_priority=priority,
            limit=_limit_for_source_type(source_type),
        )
        for facet, source_type, priority, rationale in SUPPLEMENTAL_MEDICAL_ROUTES
        if (facet, source_type) not in requested_pairs
    ]
    return [*search_items, *supplemental_items]


def _terms_for_facet_source(
    plan: QueryExpansionPlan,
    facet: ResearchFacetKind,
    source_type: SourceType,
) -> tuple[str, ...]:
    facet_terms = tuple(term for item in plan.facets if item.kind == facet for term in item.english_terms)
    source_hints = _source_hints(facet, source_type)
    return _unique((*facet_terms, *_terms_for_query(plan, source_hints)))


def _source_hints(facet: ResearchFacetKind, source_type: SourceType) -> tuple[str, ...]:
    match source_type:
        case SourceType.PUBLIC_LITERATURE:
            return LITERATURE_HINTS
        case SourceType.PUBLIC_REGULATORY:
            return REGULATORY_HINTS
        case SourceType.VENDOR_PUBLIC_DOC | SourceType.PUBLIC_WEB:
            return _manual_or_web_hints(facet)
        case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
            return VENDOR_HINTS
        case unreachable:
            assert_never(unreachable)


def _manual_or_web_hints(facet: ResearchFacetKind) -> tuple[str, ...]:
    match facet:
        case ResearchFacetKind.PROGRAMMER_UI | ResearchFacetKind.VENDOR_MANUAL:
            return (*VENDOR_HINTS, *PROGRAMMER_SEARCH_TERMS)
        case ResearchFacetKind.STIMULATION | ResearchFacetKind.ELECTRODE_CONTACTS:
            return (*VENDOR_HINTS, *PROGRAMMER_SEARCH_TERMS)
        case ResearchFacetKind.REGULATORY:
            return REGULATORY_HINTS
        case (
            ResearchFacetKind.CLINICAL_STUDY
            | ResearchFacetKind.PRIVATE_LOCAL_DOCS
            | ResearchFacetKind.GENERIC_BACKGROUND
        ):
            return VENDOR_HINTS
        case unreachable:
            assert_never(unreachable)


def _limit_for_source_type(source_type: SourceType) -> int:
    match source_type:
        case SourceType.PUBLIC_REGULATORY:
            return 1
        case SourceType.PUBLIC_LITERATURE | SourceType.PUBLIC_WEB | SourceType.VENDOR_PUBLIC_DOC:
            return 2
        case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
            return 1
        case unreachable:
            assert_never(unreachable)


def _programmer_terms(plan: QueryExpansionPlan, hints: tuple[str, ...]) -> tuple[str, ...]:
    categories = set(plan.recognized_categories)
    has_programmer = TerminologyCategory.PROGRAMMER_UI in categories
    has_stimulation = TerminologyCategory.STIMULATION in categories
    if has_programmer and has_stimulation:
        return _domain_terms(plan, hints)
    return tuple(term for term in hints if term not in PROGRAMMER_SEARCH_TERMS)


def _domain_terms(plan: QueryExpansionPlan, terms: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term for term in terms if _keeps_domain_term(plan, term))


def _keeps_domain_term(plan: QueryExpansionPlan, term: str) -> bool:
    lowered = term.casefold()
    if lowered in (value.casefold() for value in DBS_TERMS):
        return _allows_dbs(plan)
    if lowered in (value.casefold() for value in SCS_TERMS):
        return _allows_scs(plan)
    if lowered in (value.casefold() for value in INTERLEAVING_TERMS):
        return _query_has(plan, INTERLEAVING_HINTS)
    return True


def _allows_dbs(plan: QueryExpansionPlan) -> bool:
    return _query_has(plan, DBS_HINTS) or _is_generic_neurostimulation(plan)


def _allows_scs(plan: QueryExpansionPlan) -> bool:
    return _query_has(plan, SCS_HINTS) or _is_generic_neurostimulation(plan)


def _is_generic_neurostimulation(plan: QueryExpansionPlan) -> bool:
    return (
        TerminologyCategory.STIMULATION in set(plan.recognized_categories)
        and not _query_has(plan, DBS_HINTS)
        and not _query_has(plan, SCS_HINTS)
    )


def _query_has(plan: QueryExpansionPlan, hints: tuple[str, ...]) -> bool:
    lowered = plan.original_query.casefold()
    return any(hint.casefold() in lowered for hint in hints)


def _compose_query(original_query: str, terms: tuple[str, ...]) -> str:
    suffix = " ".join(terms)
    if suffix:
        return f"{original_query} {suffix}"
    return original_query


def _unique(values: Iterable[T]) -> tuple[T, ...]:
    result: list[T] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
