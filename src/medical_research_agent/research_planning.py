"""Research planning schemas and deterministic terminology primitives."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final, Iterable, Mapping, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from medical_research_agent.schemas import SourceType

T = TypeVar("T")

DEFAULT_QUERY: Final = "未命名医疗产品调研需求"
CONTACT_COUNT_RE: Final = re.compile(r"(?<!\d)([1-9]\d?)\s*(?:触点|contacts?|电极触点)", re.IGNORECASE)
ASCII_TRIGGER_RE_TEMPLATE: Final = r"(?<![A-Za-z0-9]){trigger}(?![A-Za-z0-9])"


class FrozenPlanningModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class TerminologyCategory(StrEnum):
    STIMULATION = "stimulation"
    ELECTRODE_CONTACTS = "electrode_contacts"
    PROGRAMMER_UI = "programmer_ui"
    VENDOR_MANUAL = "vendor_manual"
    REGULATOR = "regulator"
    CLINICAL_STUDY = "clinical_study"
    PRIVATE_LOCAL_DOCS = "private_local_docs"


class ResearchFacetKind(StrEnum):
    STIMULATION = "stimulation"
    ELECTRODE_CONTACTS = "electrode_contacts"
    PROGRAMMER_UI = "programmer_ui"
    VENDOR_MANUAL = "vendor_manual"
    REGULATORY = "regulatory"
    CLINICAL_STUDY = "clinical_study"
    PRIVATE_LOCAL_DOCS = "private_local_docs"
    GENERIC_BACKGROUND = "generic_background"


class EvidenceGapStatus(StrEnum):
    NEEDS_MORE_SOURCES = "needs_more_sources"
    NEEDS_REVIEW = "needs_review"
    COVERED = "covered"


class SourceReviewDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING_REVIEW = "pending_review"


class TerminologyPrimitive(FrozenPlanningModel):
    category: TerminologyCategory
    triggers: tuple[str, ...] = Field(min_length=1)
    english_terms: tuple[str, ...] = Field(min_length=1)
    facets: tuple[ResearchFacetKind, ...] = Field(min_length=1)


class SearchFacet(FrozenPlanningModel):
    kind: ResearchFacetKind
    label_zh: str = Field(min_length=1)
    label_en: str = Field(min_length=1)
    required: bool = True
    chinese_terms: tuple[str, ...] = Field(default=())
    english_terms: tuple[str, ...] = Field(default=())


class SearchRoute(FrozenPlanningModel):
    facet: ResearchFacetKind
    source_types: tuple[SourceType, ...] = Field(min_length=1)
    queries: tuple[str, ...] = Field(min_length=1)
    priority: int = Field(ge=0)
    rationale: str = Field(min_length=1)


class SourceQualitySignal(FrozenPlanningModel):
    facet: ResearchFacetKind
    source_type: SourceType
    relevance_score: float = Field(ge=0.0, le=1.0)
    credibility_score: float = Field(ge=0.0, le=1.0)
    source_fit_score: float = Field(ge=0.0, le=1.0)
    decision: SourceReviewDecision = SourceReviewDecision.PENDING_REVIEW
    reasons: tuple[str, ...] = Field(default=())


class EvidenceGap(FrozenPlanningModel):
    facet: ResearchFacetKind
    status: EvidenceGapStatus = EvidenceGapStatus.NEEDS_MORE_SOURCES
    description: str = Field(min_length=1)
    required_source_types: tuple[SourceType, ...] = Field(default=())
    recommended_queries: tuple[str, ...] = Field(default=())


class QueryExpansionPlan(FrozenPlanningModel):
    original_query: str = Field(min_length=1)
    normalized_query: str = Field(min_length=1)
    recognized_categories: tuple[TerminologyCategory, ...] = Field(default=())
    chinese_terms: tuple[str, ...] = Field(default=())
    english_terms: tuple[str, ...] = Field(default=())
    facets: tuple[SearchFacet, ...] = Field(min_length=1)
    search_routes: tuple[SearchRoute, ...] = Field(min_length=1)
    evidence_gaps: tuple[EvidenceGap, ...] = Field(default=())
    quality_signals: tuple[SourceQualitySignal, ...] = Field(default=())


TERMINOLOGY: Final[tuple[TerminologyPrimitive, ...]] = (
    TerminologyPrimitive(category=TerminologyCategory.STIMULATION, triggers=("刺激", "神经刺激", "交叉刺激", "DBS", "SCS", "stimulation", "neurostimulation"), english_terms=("stimulation", "neurostimulation", "deep brain stimulation", "spinal cord stimulation", "interleaving stimulation"), facets=(ResearchFacetKind.STIMULATION,)),
    TerminologyPrimitive(category=TerminologyCategory.ELECTRODE_CONTACTS, triggers=("触点", "电极", "导联", "contact", "electrode", "lead"), english_terms=("electrode contact", "lead contact count", "multi-contact lead"), facets=(ResearchFacetKind.ELECTRODE_CONTACTS,)),
    TerminologyPrimitive(category=TerminologyCategory.PROGRAMMER_UI, triggers=("程控", "程序控制", "界面", "UI", "programmer", "interface"), english_terms=("clinician programmer", "patient programmer", "programming interface", "programming workflow"), facets=(ResearchFacetKind.PROGRAMMER_UI,)),
    TerminologyPrimitive(category=TerminologyCategory.VENDOR_MANUAL, triggers=("说明书", "手册", "厂商", "IFU", "manual", "datasheet"), english_terms=("vendor manual", "programmer manual", "instructions for use", "technical manual"), facets=(ResearchFacetKind.VENDOR_MANUAL,)),
    TerminologyPrimitive(category=TerminologyCategory.REGULATOR, triggers=("监管", "注册", "FDA", "NMPA", "510(k)", "regulatory"), english_terms=("regulatory clearance", "FDA 510(k)", "product code", "registration dossier"), facets=(ResearchFacetKind.REGULATORY,)),
    TerminologyPrimitive(category=TerminologyCategory.CLINICAL_STUDY, triggers=("临床", "试验", "论文", "文献", "clinical", "trial", "literature"), english_terms=("clinical study", "clinical trial", "peer-reviewed evidence", "safety and efficacy"), facets=(ResearchFacetKind.CLINICAL_STUDY,)),
    TerminologyPrimitive(category=TerminologyCategory.PRIVATE_LOCAL_DOCS, triggers=("本地", "上传", "内部", "私有", "PDF", "DOCX", "local", "uploaded"), english_terms=("private local document", "uploaded private document", "local PDF", "internal reference"), facets=(ResearchFacetKind.PRIVATE_LOCAL_DOCS,)),
)

DOMAIN_TERM_HINTS: Final[Mapping[str, tuple[str, ...]]] = {
    "deep brain stimulation": ("dbs", "deep brain stimulation", "脑深部", "深脑"),
    "dbs programmer": ("dbs", "deep brain stimulation", "脑深部", "深脑"),
    "spinal cord stimulation": ("scs", "spinal cord stimulation", "脊髓"),
    "scs programmer": ("scs", "spinal cord stimulation", "脊髓"),
    "interleaving stimulation": ("interleaving", "交叉刺激"),
}

PRIMITIVES_BY_CATEGORY: Final[Mapping[TerminologyCategory, TerminologyPrimitive]] = {
    primitive.category: primitive for primitive in TERMINOLOGY
}

RELATED_CATEGORIES: Final[Mapping[TerminologyCategory, tuple[TerminologyCategory, ...]]] = {
    TerminologyCategory.PROGRAMMER_UI: (TerminologyCategory.VENDOR_MANUAL,),
}

FACET_LABELS: Final[Mapping[ResearchFacetKind, tuple[str, str]]] = {
    ResearchFacetKind.STIMULATION: ("刺激模式与参数", "stimulation mode and parameters"),
    ResearchFacetKind.ELECTRODE_CONTACTS: ("电极与触点", "electrode and contact configuration"),
    ResearchFacetKind.PROGRAMMER_UI: ("程控与界面", "programmer and user interface"),
    ResearchFacetKind.VENDOR_MANUAL: ("厂商手册与说明书", "vendor manuals and IFU"),
    ResearchFacetKind.REGULATORY: ("监管与注册", "regulatory and registration evidence"),
    ResearchFacetKind.CLINICAL_STUDY: ("临床与论文证据", "clinical and literature evidence"),
    ResearchFacetKind.PRIVATE_LOCAL_DOCS: ("本地私有资料", "private local documents"),
    ResearchFacetKind.GENERIC_BACKGROUND: ("通用背景调研", "generic background research"),
}

FACET_SOURCES: Final[Mapping[ResearchFacetKind, tuple[SourceType, ...]]] = {
    ResearchFacetKind.STIMULATION: (SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_LITERATURE),
    ResearchFacetKind.ELECTRODE_CONTACTS: (SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_LITERATURE),
    ResearchFacetKind.PROGRAMMER_UI: (SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_WEB),
    ResearchFacetKind.VENDOR_MANUAL: (SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_WEB),
    ResearchFacetKind.REGULATORY: (SourceType.PUBLIC_REGULATORY, SourceType.PUBLIC_WEB),
    ResearchFacetKind.CLINICAL_STUDY: (SourceType.PUBLIC_LITERATURE,),
    ResearchFacetKind.PRIVATE_LOCAL_DOCS: (SourceType.USER_UPLOADED_PRIVATE, SourceType.INTERNAL_PRIVATE),
    ResearchFacetKind.GENERIC_BACKGROUND: (SourceType.PUBLIC_WEB,),
}

FACET_PRIORITY: Final[Mapping[ResearchFacetKind, int]] = {
    ResearchFacetKind.VENDOR_MANUAL: 10,
    ResearchFacetKind.PROGRAMMER_UI: 15,
    ResearchFacetKind.STIMULATION: 20,
    ResearchFacetKind.ELECTRODE_CONTACTS: 25,
    ResearchFacetKind.REGULATORY: 30,
    ResearchFacetKind.CLINICAL_STUDY: 35,
    ResearchFacetKind.PRIVATE_LOCAL_DOCS: 40,
    ResearchFacetKind.GENERIC_BACKGROUND: 90,
}


def build_query_expansion_plan(raw_query: str) -> QueryExpansionPlan:
    """Build a deterministic first-pass planning contract for a research query."""

    query = _clean_query(raw_query)
    categories = _matched_categories(query)
    primitives = tuple(PRIMITIVES_BY_CATEGORY[category] for category in categories)

    if not primitives:
        return _generic_plan(query)

    contact_terms = _contact_count_terms(query)
    english_terms = _unique((*_filtered_english_terms(query, primitives), *contact_terms))
    chinese_terms = _unique(
        trigger
        for primitive in primitives
        for trigger in primitive.triggers
        if _query_contains_trigger(query, trigger)
    )
    facets = _build_facets(query, primitives, contact_terms)
    routes = tuple(_build_route(query, facet) for facet in facets)
    gaps = tuple(_build_gap(facet) for facet in facets)

    return QueryExpansionPlan(
        original_query=query,
        normalized_query=query,
        recognized_categories=categories,
        chinese_terms=chinese_terms,
        english_terms=_unique(english_terms),
        facets=facets,
        search_routes=routes,
        evidence_gaps=gaps,
    )


def _clean_query(raw_query: str) -> str:
    cleaned = " ".join(raw_query.strip().split())
    if cleaned:
        return cleaned
    return DEFAULT_QUERY


def _matched_categories(query: str) -> tuple[TerminologyCategory, ...]:
    matched = tuple(primitive.category for primitive in TERMINOLOGY if _contains_trigger(query, primitive))
    related = tuple(related for category in matched for related in RELATED_CATEGORIES.get(category, ()))
    return _unique((*matched, *related))


def _contains_trigger(query: str, primitive: TerminologyPrimitive) -> bool:
    return any(_query_contains_trigger(query, trigger) for trigger in primitive.triggers)


def _query_contains_trigger(query: str, trigger: str) -> bool:
    if trigger.isascii() and any(char.isalnum() for char in trigger):
        pattern = ASCII_TRIGGER_RE_TEMPLATE.format(trigger=re.escape(trigger))
        return re.search(pattern, query, flags=re.IGNORECASE) is not None
    return trigger.casefold() in query.casefold()


def _contact_count_terms(query: str) -> tuple[str, ...]:
    counts = _unique(CONTACT_COUNT_RE.findall(query))
    return tuple(term for count in counts for term in (f"{count}-contact lead", f"{count}-contact electrode"))


def _filtered_english_terms(query: str, primitives: tuple[TerminologyPrimitive, ...], kind: ResearchFacetKind | None = None) -> tuple[str, ...]:
    return tuple(term for primitive in primitives for term in primitive.english_terms if (kind is None or kind in primitive.facets) and _keeps_domain_term(query, term))


def _keeps_domain_term(query: str, term: str) -> bool:
    hints = DOMAIN_TERM_HINTS.get(term.casefold())
    return hints is None or any(hint.casefold() in query.casefold() for hint in hints)


def _build_facets(
    query: str,
    primitives: tuple[TerminologyPrimitive, ...],
    contact_terms: tuple[str, ...],
) -> tuple[SearchFacet, ...]:
    facet_kinds = _unique(facet for primitive in primitives for facet in primitive.facets)
    return tuple(
        SearchFacet(
            kind=kind,
            label_zh=FACET_LABELS[kind][0],
            label_en=FACET_LABELS[kind][1],
            chinese_terms=_unique(
                trigger
                for primitive in primitives
                for trigger in primitive.triggers
                if _query_contains_trigger(query, trigger)
            ),
            english_terms=_unique(
                (*_filtered_english_terms(query, primitives, kind), *(contact_terms if kind == ResearchFacetKind.ELECTRODE_CONTACTS else ())),
            ),
        )
        for kind in facet_kinds
    )


def _build_route(query: str, facet: SearchFacet) -> SearchRoute:
    focused_terms = " ".join(facet.english_terms[:3])
    queries = _unique((f"{query} {focused_terms}".strip(), f"{facet.label_en} {focused_terms}".strip()))
    return SearchRoute(facet=facet.kind, source_types=FACET_SOURCES[facet.kind], queries=queries, priority=FACET_PRIORITY[facet.kind], rationale=f"Use {facet.label_en} sources for {facet.label_zh}.")


def _build_gap(facet: SearchFacet) -> EvidenceGap:
    return EvidenceGap(facet=facet.kind, description=f"Need source-backed evidence for {facet.label_zh}.", required_source_types=FACET_SOURCES[facet.kind], recommended_queries=facet.english_terms[:2])


def _generic_plan(query: str) -> QueryExpansionPlan:
    label_zh, label_en = FACET_LABELS[ResearchFacetKind.GENERIC_BACKGROUND]
    facet = SearchFacet(
        kind=ResearchFacetKind.GENERIC_BACKGROUND,
        label_zh=label_zh,
        label_en=label_en,
        required=False,
    )
    route = SearchRoute(
        facet=facet.kind,
        source_types=FACET_SOURCES[facet.kind],
        queries=(query,),
        priority=FACET_PRIORITY[facet.kind],
        rationale="Use public web sources until the topic is clarified.",
    )
    gap = EvidenceGap(
        facet=facet.kind,
        status=EvidenceGapStatus.NEEDS_REVIEW,
        description="No medical-device terminology was recognized; human review should confirm research facets.",
        required_source_types=route.source_types,
        recommended_queries=(query,),
    )
    return QueryExpansionPlan(
        original_query=query,
        normalized_query=query,
        facets=(facet,),
        search_routes=(route,),
        evidence_gaps=(gap,),
    )


def _unique(values: Iterable[T]) -> tuple[T, ...]:
    result: list[T] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
