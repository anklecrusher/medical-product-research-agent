"""Deterministic fallback heuristics for source-strategy planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from medical_research_agent.llm.privacy import PRIVATE_SOURCE_TYPES
from medical_research_agent.research_planning import TerminologyCategory

if TYPE_CHECKING:
    from medical_research_agent.workflow.state import ResearchIntent


def fallback_route_ids(intent: "ResearchIntent") -> tuple[str, ...]:
    categories = set(intent.query_expansion.recognized_categories)
    query = intent.original_query.casefold()
    route_ids: list[str] = []

    if TerminologyCategory.PRIVATE_LOCAL_DOCS in categories:
        route_ids.append("local_docs")
    if TerminologyCategory.VENDOR_MANUAL in categories:
        route_ids.append("vendor_company")
    if TerminologyCategory.PROGRAMMER_UI in categories:
        route_ids.append("programmer_ui")
    if TerminologyCategory.STIMULATION in categories:
        route_ids.append("product_technology")
    if TerminologyCategory.ELECTRODE_CONTACTS in categories:
        route_ids.append("electrode_contacts")
    if _has_literature_signal(query, categories):
        route_ids.append("literature_pubmed")
    if _has_open_full_text_signal(query):
        route_ids.append("open_full_text")
    if _has_company_signal(query, categories):
        route_ids.append("vendor_company")
    if _has_regulatory_signal(query, categories):
        route_ids.append("regulatory_records")
    elif _has_literature_signal(query, categories) and _has_medical_device_signal(categories):
        route_ids.append("regulatory_records")
    elif _requires_product_evidence_backstop(categories):
        route_ids.extend(("literature_pubmed", "regulatory_records"))
    if _has_trial_signal(query, categories):
        route_ids.append("clinical_trials")
    if _has_patent_signal(query):
        route_ids.append("patents")
    if _has_domestic_news_signal(query):
        route_ids.extend(("domestic_news", "tenders_announcements"))
    if _has_international_news_signal(query):
        route_ids.append("international_news")
    if not route_ids:
        route_ids.append("public_web_background")

    return _unique(route_ids)


def requires_private_local_only(intent: "ResearchIntent") -> bool:
    source_types = set(intent.target_source_types)
    has_private_type = bool(source_types.intersection(PRIVATE_SOURCE_TYPES))
    return TerminologyCategory.PRIVATE_LOCAL_DOCS in set(intent.query_expansion.recognized_categories) or has_private_type


def fallback_follow_up_intents(intent: "ResearchIntent") -> tuple[str, ...]:
    return tuple(gap.description for gap in intent.query_expansion.evidence_gaps[:2])


def all_expansion_terms(intent: "ResearchIntent") -> tuple[str, ...]:
    return _unique(
        (
            *intent.query_expansion.english_terms,
            *(term for facet in intent.query_expansion.facets for term in facet.english_terms),
            *_programmer_domain_terms(intent),
        )
    )


def _programmer_domain_terms(intent: "ResearchIntent") -> tuple[str, ...]:
    categories = set(intent.query_expansion.recognized_categories)
    if TerminologyCategory.PROGRAMMER_UI not in categories or TerminologyCategory.STIMULATION not in categories:
        return ()

    query = intent.original_query.casefold()
    if _contains_any(query, ("dbs", "deep brain stimulation", "脑深部", "深脑")):
        return ("DBS programmer",)
    if _contains_any(query, ("scs", "spinal cord stimulation", "脊髓")):
        return ("SCS programmer",)
    return ("SCS programmer", "DBS programmer")


def _has_literature_signal(query: str, categories: set[TerminologyCategory]) -> bool:
    return TerminologyCategory.CLINICAL_STUDY in categories or _contains_any(query, ("论文", "文献", "literature", "pubmed", "open full text", "开放全文"))


def _has_open_full_text_signal(query: str) -> bool:
    return _contains_any(query, ("开放全文", "open full text", "full text", "open access", "pmc", "europe pmc", "oa"))


def _has_company_signal(query: str, categories: set[TerminologyCategory]) -> bool:
    product_categories = {
        TerminologyCategory.PROGRAMMER_UI,
        TerminologyCategory.VENDOR_MANUAL,
    }
    return bool(categories.intersection(product_categories)) or _contains_any(
        query,
        ("公司", "厂商", "产品", "产品线", "竞品", "company", "vendor", "manual", "ifu", "景昱", "品驰", "美敦力", "波士顿科学"),
    )


def _has_regulatory_signal(query: str, categories: set[TerminologyCategory]) -> bool:
    return TerminologyCategory.REGULATOR in categories or _contains_any(query, ("监管", "注册", "fda", "nmpa", "510(k)", "gudid"))


def _has_medical_device_signal(categories: set[TerminologyCategory]) -> bool:
    return bool(
        categories.intersection(
            {
                TerminologyCategory.STIMULATION,
                TerminologyCategory.ELECTRODE_CONTACTS,
                TerminologyCategory.PROGRAMMER_UI,
                TerminologyCategory.VENDOR_MANUAL,
            }
        )
    )


def _requires_product_evidence_backstop(categories: set[TerminologyCategory]) -> bool:
    return bool(
        categories.intersection({TerminologyCategory.STIMULATION, TerminologyCategory.ELECTRODE_CONTACTS})
    ) and TerminologyCategory.PROGRAMMER_UI in categories


def _has_trial_signal(query: str, categories: set[TerminologyCategory]) -> bool:
    return TerminologyCategory.CLINICAL_STUDY in categories and _contains_any(query, ("临床", "试验", "trial", "clinical"))


def _has_patent_signal(query: str) -> bool:
    return _contains_any(query, ("专利", "patent"))


def _has_domestic_news_signal(query: str) -> bool:
    return _contains_any(query, ("国内", "新闻", "融资", "公告", "招标", "中标", "采购", "行业媒体", "公司动态"))


def _has_international_news_signal(query: str) -> bool:
    return _contains_any(query, ("international news", "press release", "investor", "global news"))


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle.casefold() in text for needle in needles)


def _unique[T](values: Iterable[T]) -> tuple[T, ...]:
    result: list[T] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
