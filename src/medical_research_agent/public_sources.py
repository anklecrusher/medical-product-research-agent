"""Public non-literature source routing and citation filtering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Iterable, assert_never

from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, SourceRoute, SourceStrategy


class PublicSourceCategory(StrEnum):
    REGULATORY_DEVICE = "regulatory_device"
    CLINICAL_TRIAL = "clinical_trial"
    DEVICE_IDENTIFIER = "device_identifier"
    PATENT = "patent"
    COMPANY_OFFICIAL = "company_official"
    PUBLIC_MANUAL = "public_manual"
    DOMESTIC_NEWS = "domestic_news"
    INTERNATIONAL_NEWS = "international_news"
    INDUSTRY_MEDIA = "industry_media"
    PUBLIC_ANNOUNCEMENT = "public_announcement"


@dataclass(frozen=True, slots=True)
class PublicSourceSelectionResult:
    accepted: tuple[SourceRecord, ...]
    rejected: tuple[SourceRecord, ...]
    gaps: tuple[str, ...]


_REGULATORY_HINTS: Final = ("fda", "510(k)", "udi", "注册", "监管", "批准", "器械唯一标识")
_CLINICAL_HINTS: Final = ("clinicaltrials", "clinical trial", "临床试验", "nct")
_PATENT_HINTS: Final = ("patent", "专利", "发明")
_COMPANY_HINTS: Final = ("公司", "企业", "厂商", "产品线", "company", "vendor")
_MANUAL_HINTS: Final = ("说明书", "手册", "ifu", "manual", "datasheet", "白皮书")
_NEWS_HINTS: Final = ("新闻", "动态", "融资", "上市", "获批", "news")
_ANNOUNCEMENT_HINTS: Final = ("招采", "招标", "中标", "公告", "采购", "tender", "bid")


def build_public_non_literature_strategy(query: str, *, task_id: str | None = None) -> SourceStrategy:
    """Build bounded free public source routes for non-literature discovery."""

    normalized = " ".join(query.strip().split())
    categories = _categories_for_query(normalized)
    routes = tuple(_route_for_category(category, normalized) for category in categories)
    return SourceStrategy(
        task_id=task_id,
        objective=normalized,
        routes=routes,
        max_follow_up_rounds=1,
        privacy_note="Public non-literature routes only; no paid API key or private source required.",
    )


def filter_citable_public_sources(
    sources: Iterable[SourceRecord],
    access_checks: Iterable[AccessCheck],
) -> PublicSourceSelectionResult:
    """Keep only final-citable public sources and audit inaccessible gaps."""

    checks_by_source_id = {check.source_id: check for check in access_checks}
    accepted: list[SourceRecord] = []
    rejected: list[SourceRecord] = []
    gaps: list[str] = []

    for source in sources:
        check = checks_by_source_id.get(source.source_id)
        if check is None:
            rejected.append(source)
            gaps.append(f"{source.source_id}:missing_access_check")
            continue
        eligibility = CitationEligibility.from_access_check(check)
        if eligibility.eligible:
            accepted.append(source)
            continue
        rejected.append(source)
        gaps.append(f"{source.source_id}:{eligibility.reason}")

    return PublicSourceSelectionResult(accepted=tuple(accepted), rejected=tuple(rejected), gaps=tuple(gaps))


def _categories_for_query(query: str) -> tuple[PublicSourceCategory, ...]:
    categories: list[PublicSourceCategory] = []
    if _has_any(query, _REGULATORY_HINTS):
        categories.extend(
            [
                PublicSourceCategory.REGULATORY_DEVICE,
                PublicSourceCategory.DEVICE_IDENTIFIER,
            ]
        )
    if _has_any(query, _CLINICAL_HINTS):
        categories.append(PublicSourceCategory.CLINICAL_TRIAL)
    if _has_any(query, _PATENT_HINTS):
        categories.append(PublicSourceCategory.PATENT)
    if _has_any(query, _COMPANY_HINTS):
        categories.append(PublicSourceCategory.COMPANY_OFFICIAL)
    if _has_any(query, _MANUAL_HINTS) or _has_any(query, _COMPANY_HINTS):
        categories.append(PublicSourceCategory.PUBLIC_MANUAL)
    if _has_any(query, _NEWS_HINTS) or _has_any(query, _COMPANY_HINTS):
        categories.extend(
            [
                PublicSourceCategory.DOMESTIC_NEWS,
                PublicSourceCategory.INTERNATIONAL_NEWS,
                PublicSourceCategory.INDUSTRY_MEDIA,
            ]
        )
    if _has_any(query, _ANNOUNCEMENT_HINTS):
        categories.append(PublicSourceCategory.PUBLIC_ANNOUNCEMENT)
    if not categories:
        categories.extend(
            [
                PublicSourceCategory.PUBLIC_MANUAL,
                PublicSourceCategory.PATENT,
            ]
        )
    return _unique(categories)


def _route_for_category(category: PublicSourceCategory, query: str) -> SourceRoute:
    match category:
        case PublicSourceCategory.REGULATORY_DEVICE:
            return SourceRoute(
                route_id=category.value,
                facet=ResearchFacetKind.REGULATORY,
                source_types=(SourceType.PUBLIC_REGULATORY,),
                connectors=("openfda_510k",),
                queries=(f"{query} FDA 510(k) device database",),
                budget=2,
                rationale="Search free public device regulatory records.",
            )
        case PublicSourceCategory.CLINICAL_TRIAL:
            return SourceRoute(
                route_id=category.value,
                facet=ResearchFacetKind.CLINICAL_STUDY,
                source_types=(SourceType.PUBLIC_REGULATORY,),
                connectors=("clinicaltrials_gov",),
                queries=(f"{query} ClinicalTrials.gov",),
                budget=2,
                rationale="Search public clinical-trial registry records.",
            )
        case PublicSourceCategory.DEVICE_IDENTIFIER:
            return SourceRoute(
                route_id=category.value,
                facet=ResearchFacetKind.REGULATORY,
                source_types=(SourceType.PUBLIC_REGULATORY,),
                connectors=("accessgudid",),
                queries=(f"{query} UDI AccessGUDID",),
                budget=2,
                rationale="Search public device identifier records.",
            )
        case PublicSourceCategory.PATENT:
            return SourceRoute(
                route_id=category.value,
                facet=ResearchFacetKind.STIMULATION,
                source_types=(SourceType.PUBLIC_WEB,),
                connectors=("patentsview",),
                queries=(f"{query} medical device patent",),
                budget=2,
                rationale="Search free public patent records for product and engineering clues.",
            )
        case PublicSourceCategory.COMPANY_OFFICIAL:
            return _web_route(category, query, "official company product page site:com OR site:cn")
        case PublicSourceCategory.PUBLIC_MANUAL:
            return SourceRoute(
                route_id=category.value,
                facet=ResearchFacetKind.VENDOR_MANUAL,
                source_types=(SourceType.VENDOR_PUBLIC_DOC,),
                connectors=("duckduckgo_html",),
                queries=(f"{query} manual IFU PDF instructions for use",),
                budget=3,
                rationale="Search public manuals, IFU pages, datasheets, and white papers.",
            )
        case PublicSourceCategory.DOMESTIC_NEWS:
            return _web_route(category, query, "国内 新闻 医疗器械")
        case PublicSourceCategory.INTERNATIONAL_NEWS:
            return _web_route(category, query, "international medical device news")
        case PublicSourceCategory.INDUSTRY_MEDIA:
            return _web_route(category, query, "industry media 医疗器械")
        case PublicSourceCategory.PUBLIC_ANNOUNCEMENT:
            return _web_route(category, query, "招标 中标 公告 采购")
        case unreachable:
            assert_never(unreachable)


def _web_route(category: PublicSourceCategory, query: str, suffix: str) -> SourceRoute:
    return SourceRoute(
        route_id=category.value,
        facet=ResearchFacetKind.GENERIC_BACKGROUND,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("duckduckgo_html",),
        queries=(f"{query} {suffix}",),
        budget=2,
        rationale=f"Search free public {category.value.replace('_', ' ')} pages.",
    )


def _has_any(query: str, hints: tuple[str, ...]) -> bool:
    lowered = query.casefold()
    return any(hint.casefold() in lowered for hint in hints)


def _unique(values: Iterable[PublicSourceCategory]) -> tuple[PublicSourceCategory, ...]:
    result: list[PublicSourceCategory] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
