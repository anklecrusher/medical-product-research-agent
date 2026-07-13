"""Fixed source-route catalog for bounded strategy planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceType

MAX_ROUTE_BUDGET: Final = 4
DEFAULT_FOLLOW_UP_ROUNDS: Final = 1


@dataclass(frozen=True, slots=True)
class RouteTemplate:
    route_id: str
    facet: ResearchFacetKind
    source_types: tuple[SourceType, ...]
    connectors: tuple[str, ...]
    query_terms: tuple[str, ...]
    default_budget: int
    rationale: str


ROUTE_TEMPLATES: Final[tuple[RouteTemplate, ...]] = (
    RouteTemplate(
        route_id="public_web_background",
        facet=ResearchFacetKind.GENERIC_BACKGROUND,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("duckduckgo_html",),
        query_terms=("public background",),
        default_budget=2,
        rationale="Use public web background sources until medical-device facets are confirmed.",
    ),
    RouteTemplate(
        route_id="product_technology",
        facet=ResearchFacetKind.STIMULATION,
        source_types=(SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_LITERATURE),
        connectors=("duckduckgo_html", "pubmed"),
        query_terms=("stimulation parameters", "product specifications", "technical manual"),
        default_budget=3,
        rationale="Find product and technical evidence for stimulation parameters.",
    ),
    RouteTemplate(
        route_id="programmer_ui",
        facet=ResearchFacetKind.PROGRAMMER_UI,
        source_types=(SourceType.PUBLIC_WEB, SourceType.VENDOR_PUBLIC_DOC),
        connectors=("duckduckgo_html",),
        query_terms=("clinician programmer", "programming interface", "programming workflow", "UI"),
        default_budget=3,
        rationale="Find public programmer UI, interface, and workflow materials.",
    ),
    RouteTemplate(
        route_id="electrode_contacts",
        facet=ResearchFacetKind.ELECTRODE_CONTACTS,
        source_types=(SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_LITERATURE),
        connectors=("duckduckgo_html", "pubmed"),
        query_terms=("electrode contacts", "lead contacts", "contact configuration"),
        default_budget=3,
        rationale="Find public evidence about lead contacts and contact configurations.",
    ),
    RouteTemplate(
        route_id="literature_pubmed",
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_types=(SourceType.PUBLIC_LITERATURE,),
        connectors=("pubmed", "crossref"),
        query_terms=("PubMed", "clinical study", "peer-reviewed evidence"),
        default_budget=4,
        rationale="Find public literature, abstract-level evidence, and auditable scholarly metadata.",
    ),
    RouteTemplate(
        route_id="open_full_text",
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_types=(SourceType.PUBLIC_LITERATURE,),
        connectors=("pmc", "europe_pmc", "openalex"),
        query_terms=("open access", "full text", "PMC", "Europe PMC"),
        default_budget=3,
        rationale="Prefer open full text and open-access literature records.",
    ),
    RouteTemplate(
        route_id="vendor_company",
        facet=ResearchFacetKind.VENDOR_MANUAL,
        source_types=(SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_WEB),
        connectors=("duckduckgo_html",),
        query_terms=("company", "product page", "manual", "IFU"),
        default_budget=3,
        rationale="Find public vendor, company, product, and manual materials.",
    ),
    RouteTemplate(
        route_id="regulatory_records",
        facet=ResearchFacetKind.REGULATORY,
        source_types=(SourceType.PUBLIC_REGULATORY,),
        connectors=("openfda_510k", "accessgudid", "duckduckgo_html"),
        query_terms=("FDA 510(k)", "regulatory clearance", "device registration"),
        default_budget=3,
        rationale="Find public regulatory and device-registration records.",
    ),
    RouteTemplate(
        route_id="patents",
        facet=ResearchFacetKind.STIMULATION,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("patentsview", "google_patents_public"),
        query_terms=("patent", "inventor", "assignee"),
        default_budget=2,
        rationale="Find public patent and engineering-design signals.",
    ),
    RouteTemplate(
        route_id="clinical_trials",
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_types=(SourceType.PUBLIC_REGULATORY,),
        connectors=("clinicaltrials_gov",),
        query_terms=("clinical trial", "ClinicalTrials.gov"),
        default_budget=2,
        rationale="Find public clinical-trial registry records.",
    ),
    RouteTemplate(
        route_id="domestic_news",
        facet=ResearchFacetKind.VENDOR_MANUAL,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("duckduckgo_html",),
        query_terms=("国内新闻", "行业媒体", "公司动态"),
        default_budget=3,
        rationale="Find domestic public news and industry-media signals.",
    ),
    RouteTemplate(
        route_id="international_news",
        facet=ResearchFacetKind.VENDOR_MANUAL,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("duckduckgo_html",),
        query_terms=("news", "investor relations", "press release"),
        default_budget=2,
        rationale="Find international public news and company announcements.",
    ),
    RouteTemplate(
        route_id="tenders_announcements",
        facet=ResearchFacetKind.VENDOR_MANUAL,
        source_types=(SourceType.PUBLIC_WEB,),
        connectors=("duckduckgo_html",),
        query_terms=("招标", "中标", "公告", "采购"),
        default_budget=2,
        rationale="Find public tenders, procurement notices, and announcements.",
    ),
    RouteTemplate(
        route_id="local_docs",
        facet=ResearchFacetKind.PRIVATE_LOCAL_DOCS,
        source_types=(SourceType.USER_UPLOADED_PRIVATE, SourceType.INTERNAL_PRIVATE),
        connectors=("local_upload", "local_private_index"),
        query_terms=("local document", "uploaded private document"),
        default_budget=1,
        rationale="Use local private documents without external LLM disclosure.",
    ),
)

TEMPLATES_BY_ID: Final = {template.route_id: template for template in ROUTE_TEMPLATES}


def template_for(route_id: str) -> RouteTemplate:
    return TEMPLATES_BY_ID[route_id]
