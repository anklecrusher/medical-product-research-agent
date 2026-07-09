"""Source relevance and credibility review before parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Iterable, Sequence, assert_never

from medical_research_agent.research_planning import (
    FACET_SOURCES,
    QueryExpansionPlan,
    ResearchFacetKind,
    SourceQualitySignal,
    SourceReviewDecision,
)
from medical_research_agent.schemas import SourceRecord, SourceType


class SourceQualityStatus(StrEnum):
    HAS_ACCEPTED_SOURCES = "has_accepted_sources"
    NEEDS_MORE_SOURCES = "needs_more_sources"


@dataclass(frozen=True, slots=True)
class SourceQualityReview:
    accepted: tuple[SourceRecord, ...]
    rejected: tuple[SourceRecord, ...]
    status: SourceQualityStatus


@dataclass(frozen=True, slots=True)
class CandidateSignals:
    relevance_score: float
    credibility_score: float
    source_fit_score: float
    reasons: tuple[str, ...]


MEDICAL_DEVICE_TERMS: Final[tuple[str, ...]] = (
    "neurostimulation",
    "stimulation",
    "deep brain stimulation",
    "spinal cord stimulation",
    "dbs",
    "scs",
    "interleaving stimulation",
    "electrode",
    "lead",
    "contact",
    "clinician programmer",
    "patient programmer",
    "programming interface",
    "programmer manual",
    "instructions for use",
    "implantable pulse generator",
    "神经刺激",
    "刺激",
    "交叉刺激",
    "电极",
    "触点",
    "程控",
    "界面",
    "说明书",
)
NOISE_TERM_GROUPS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("math_noise", ("ordinary differential equation", "differential equation", "ode", "mathematical logic", "常微分方程", "微分方程", "数学逻辑")),
    ("laser_plasma_noise", ("laser induced plasma", "plasma hot core", "shock wave", "plasma", "激光诱导等离子体", "冲击波")),
    ("generic_unrelated_noise", ("medieval", "agriculture", "macroeconomic", "astronomy", "crop yield")),
)
METADATA_TEXT_KEYS: Final[tuple[str, ...]] = (
    "title",
    "snippet",
    "abstract",
    "summary",
    "description",
    "journal",
    "container_title",
)
REJECTION_THRESHOLD: Final = 0.18


def review_source_quality(
    sources: Sequence[SourceRecord],
    query_expansion: QueryExpansionPlan,
) -> SourceQualityReview:
    """Split source records into accepted and rejected records with audit metadata."""

    accepted: list[SourceRecord] = []
    rejected: list[SourceRecord] = []
    for source in sources:
        reviewed = _review_single_source(source, query_expansion)
        review = reviewed.metadata["quality_review"]
        if review["decision"] == SourceReviewDecision.REJECTED.value:
            rejected.append(reviewed)
        else:
            accepted.append(reviewed)

    status = SourceQualityStatus.HAS_ACCEPTED_SOURCES
    if not accepted:
        status = SourceQualityStatus.NEEDS_MORE_SOURCES
    return SourceQualityReview(accepted=tuple(accepted), rejected=tuple(rejected), status=status)


def _review_single_source(source: SourceRecord, query_expansion: QueryExpansionPlan) -> SourceRecord:
    facet = _facet_for_source(source)
    signals = _candidate_signals(source, query_expansion, facet)
    decision = _decision_for_source(source, query_expansion, signals)
    signal = SourceQualitySignal(
        facet=facet,
        source_type=source.source_type,
        relevance_score=signals.relevance_score,
        credibility_score=signals.credibility_score,
        source_fit_score=signals.source_fit_score,
        decision=decision,
        reasons=signals.reasons,
    )
    return _with_quality_review(source, signal)


def _candidate_signals(
    source: SourceRecord,
    query_expansion: QueryExpansionPlan,
    facet: ResearchFacetKind,
) -> CandidateSignals:
    candidate_text = _candidate_text(source)
    expansion_matches = _matched_terms(candidate_text, (*query_expansion.chinese_terms, *query_expansion.english_terms))
    facet_matches = _matched_terms(candidate_text, _facet_terms(query_expansion, facet))
    medical_matches = _matched_terms(candidate_text, MEDICAL_DEVICE_TERMS)
    noise_reasons = _noise_reasons(candidate_text)
    relevance_score = min(
        1.0,
        (0.16 * len(expansion_matches)) + (0.18 * len(facet_matches)) + (0.12 * len(medical_matches)),
    )
    reasons = _review_reasons(expansion_matches, facet_matches, medical_matches, noise_reasons)
    return CandidateSignals(
        relevance_score=round(relevance_score, 3),
        credibility_score=_credibility_score(source.source_type),
        source_fit_score=_source_fit_score(source.source_type, facet),
        reasons=reasons,
    )


def _decision_for_source(
    source: SourceRecord,
    query_expansion: QueryExpansionPlan,
    signals: CandidateSignals,
) -> SourceReviewDecision:
    if _has_noise_reason(signals.reasons) and signals.relevance_score < 0.3:
        return SourceReviewDecision.REJECTED
    if source.metadata.get("placeholder"):
        return SourceReviewDecision.REJECTED
    if _is_generic_plan(query_expansion) or source.metadata.get("mock"):
        return SourceReviewDecision.ACCEPTED
    if signals.relevance_score < REJECTION_THRESHOLD:
        return SourceReviewDecision.REJECTED
    return SourceReviewDecision.ACCEPTED


def _with_quality_review(source: SourceRecord, signal: SourceQualitySignal) -> SourceRecord:
    quality_review = {
        "decision": signal.decision.value,
        "reasons": list(signal.reasons),
        "scores": {
            "relevance": signal.relevance_score,
            "credibility": signal.credibility_score,
            "source_fit": signal.source_fit_score,
        },
        "facet": signal.facet.value,
        "source_type": signal.source_type.value,
        "search_query": source.search_query,
    }
    return source.model_copy(update={"metadata": {**source.metadata, "quality_review": quality_review}})


def _candidate_text(source: SourceRecord) -> str:
    parts = [source.title, source.publisher or "", source.credibility_note or ""]
    for key in METADATA_TEXT_KEYS:
        value = source.metadata.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).casefold()


def _facet_for_source(source: SourceRecord) -> ResearchFacetKind:
    facet_value = source.metadata.get("facet")
    if isinstance(facet_value, str):
        for facet in ResearchFacetKind:
            if facet.value == facet_value:
                return facet
    return ResearchFacetKind.GENERIC_BACKGROUND


def _facet_terms(
    query_expansion: QueryExpansionPlan,
    target_facet: ResearchFacetKind,
) -> tuple[str, ...]:
    return tuple(
        term
        for facet in query_expansion.facets
        if facet.kind == target_facet
        for term in (facet.label_zh, facet.label_en, *facet.chinese_terms, *facet.english_terms)
    )


def _matched_terms(text: str, terms: Iterable[str]) -> tuple[str, ...]:
    return tuple(term for term in _unique(term.strip() for term in terms) if term and _contains_term(text, term))


def _contains_term(text: str, term: str) -> bool:
    normalized_term = term.casefold()
    if _has_non_ascii(normalized_term):
        return normalized_term in text
    return re.search(rf"(?<![0-9a-z]){re.escape(normalized_term)}(?![0-9a-z])", text) is not None


def _has_non_ascii(value: str) -> bool:
    return any(ord(character) > 127 for character in value)


def _noise_reasons(text: str) -> tuple[str, ...]:
    return tuple(
        f"{group}: {', '.join(matches)}"
        for group, terms in NOISE_TERM_GROUPS
        for matches in (_matched_terms(text, terms),)
        if matches
    )


def _review_reasons(
    expansion_matches: tuple[str, ...],
    facet_matches: tuple[str, ...],
    medical_matches: tuple[str, ...],
    noise_reasons: tuple[str, ...],
) -> tuple[str, ...]:
    positive_reasons = tuple(
        reason
        for label, matches in (
            ("query_terms", expansion_matches),
            ("facet_terms", facet_matches),
            ("medical_device_terms", medical_matches),
        )
        if matches
        for reason in (f"{label}: {', '.join(matches[:4])}",)
    )
    if noise_reasons:
        return (*positive_reasons, *noise_reasons)
    if positive_reasons:
        return positive_reasons
    return ("low_relevance: no title/snippet overlap with query expansion or medical-device terminology",)


def _credibility_score(source_type: SourceType) -> float:
    match source_type:
        case SourceType.PUBLIC_LITERATURE | SourceType.PUBLIC_REGULATORY | SourceType.VENDOR_PUBLIC_DOC:
            return 0.8
        case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
            return 0.75
        case SourceType.PUBLIC_WEB:
            return 0.55
        case unreachable:
            assert_never(unreachable)


def _source_fit_score(source_type: SourceType, facet: ResearchFacetKind) -> float:
    expected = FACET_SOURCES.get(facet, ())
    if source_type in expected:
        return 1.0
    if facet == ResearchFacetKind.GENERIC_BACKGROUND:
        return 0.6
    return 0.4


def _has_noise_reason(reasons: tuple[str, ...]) -> bool:
    return any("noise" in reason for reason in reasons)


def _is_generic_plan(query_expansion: QueryExpansionPlan) -> bool:
    return query_expansion.facets[0].kind == ResearchFacetKind.GENERIC_BACKGROUND


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
