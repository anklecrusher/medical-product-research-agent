"""LLM-assisted source triage with deterministic safety gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence

from pydantic import ValidationError

from medical_research_agent.llm.client import (
    LLMClient,
    LLMRequestFailedError,
    MissingLLMAPIKeyError,
    UnsupportedLLMProviderError,
    get_llm_client,
)
from medical_research_agent.llm.models import LLMMessage, LLMRequest
from medical_research_agent.research_planning import QueryExpansionPlan, SourceReviewDecision
from medical_research_agent.schemas import SourceRecord
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility
from medical_research_agent.source_quality import SourceQualityReview, review_source_quality
from medical_research_agent.source_triage_models import (
    MAX_FOLLOW_UP_QUERIES,
    TRIAGE_SYSTEM_PROMPT,
    LLMSourceTriageItem,
    LLMSourceTriageResponse,
    SourceTriageReview,
    SourceTriageStatus,
    access_checks_by_source_id,
    build_triage_payload,
    contains_private_source,
    is_generic_only_source,
    status_for,
    unique_source_types,
    with_access_metadata,
    with_llm_triage,
)


def review_sources_with_configured_llm_triage(
    sources: Sequence[SourceRecord],
    query_expansion: QueryExpansionPlan,
    *,
    access_checks: Sequence[AccessCheck] = (),
    require_access_check: bool = False,
) -> SourceTriageReview:
    """Run source triage with the configured LLM client and deterministic fallback."""

    try:
        llm_client = get_llm_client()
    except UnsupportedLLMProviderError:
        llm_client = None
    return review_sources_with_llm_triage(
        sources,
        query_expansion,
        llm_client=llm_client,
        access_checks=access_checks,
        require_access_check=require_access_check,
    )


def review_sources_with_llm_triage(
    sources: Sequence[SourceRecord],
    query_expansion: QueryExpansionPlan,
    *,
    llm_client: LLMClient | None = None,
    access_checks: Sequence[AccessCheck] = (),
    require_access_check: bool = False,
) -> SourceTriageReview:
    """Combine deterministic relevance, free-access checks, and LLM JSON triage."""

    deterministic = review_source_quality(sources, query_expansion)
    access_by_source_id = access_checks_by_source_id(access_checks, deterministic.accepted)
    prelim = _apply_access_gate(deterministic.accepted, access_by_source_id, require_access_check)
    if llm_client is None or contains_private_source(prelim.accepted):
        return _review_without_llm(deterministic, prelim)

    llm_result = _request_llm_triage(llm_client, query_expansion, prelim.accepted)
    return _merge_llm_triage(deterministic, prelim, llm_result)


@dataclass(frozen=True, slots=True)
class _AccessGateResult:
    accepted: tuple[SourceRecord, ...]
    rejected: tuple[SourceRecord, ...]
    pending_review: tuple[SourceRecord, ...]


@dataclass(frozen=True, slots=True)
class _LLMTriageResult:
    response: LLMSourceTriageResponse | None
    audit_reason: str | None


def _review_without_llm(deterministic: SourceQualityReview, prelim: _AccessGateResult) -> SourceTriageReview:
    accepted = tuple(with_llm_triage(source, SourceReviewDecision.ACCEPTED, ("llm_not_used",)) for source in prelim.accepted)
    rejected = (*deterministic.rejected, *prelim.rejected)
    status = status_for(accepted)
    return SourceTriageReview(
        accepted=accepted,
        rejected=rejected,
        pending_review=prelim.pending_review,
        status=status,
        follow_up_queries=(),
        follow_up_searches=(),
        llm_used=False,
    )


def _merge_llm_triage(
    deterministic: SourceQualityReview,
    prelim: _AccessGateResult,
    llm_result: _LLMTriageResult,
) -> SourceTriageReview:
    if llm_result.response is None:
        audit_reason = llm_result.audit_reason or "llm_output_invalid"
        accepted = tuple(
            with_llm_triage(source, SourceReviewDecision.ACCEPTED, (audit_reason,))
            for source in prelim.accepted
        )
        return SourceTriageReview(
            accepted=accepted,
            rejected=(*deterministic.rejected, *prelim.rejected),
            pending_review=prelim.pending_review,
            status=status_for(accepted),
            follow_up_queries=(),
            follow_up_searches=(),
            llm_used=False,
        )

    items_by_source_id = {item.source_id: item for item in llm_result.response.items}
    accepted: list[SourceRecord] = []
    rejected: list[SourceRecord] = [*deterministic.rejected, *prelim.rejected]
    pending = [*prelim.pending_review]
    for source in prelim.accepted:
        item = items_by_source_id.get(source.source_id)
        if item is None:
            pending.append(with_llm_triage(source, SourceReviewDecision.PENDING_REVIEW, ("llm_no_decision_for_source",)))
            continue
        routed = _source_from_llm_item(source, item)
        match item.decision:
            case SourceReviewDecision.ACCEPTED:
                accepted.append(routed)
            case SourceReviewDecision.REJECTED:
                rejected.append(routed)
            case SourceReviewDecision.PENDING_REVIEW:
                pending.append(routed)
            case unreachable:
                from typing import assert_never

                assert_never(unreachable)

    follow_up_searches = tuple(llm_result.response.follow_up_queries[:MAX_FOLLOW_UP_QUERIES])
    return SourceTriageReview(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        pending_review=tuple(pending),
        status=status_for(tuple(accepted)),
        follow_up_queries=tuple(item.query for item in follow_up_searches),
        follow_up_searches=follow_up_searches,
        llm_used=True,
    )


def _apply_access_gate(
    sources: tuple[SourceRecord, ...],
    access_by_source_id: dict[str, AccessCheck],
    require_access_check: bool,
) -> _AccessGateResult:
    accepted: list[SourceRecord] = []
    rejected: list[SourceRecord] = []
    pending: list[SourceRecord] = []
    for source in sources:
        access_check = access_by_source_id.get(source.source_id)
        if access_check is None:
            if require_access_check:
                pending.append(with_llm_triage(source, SourceReviewDecision.PENDING_REVIEW, ("missing_access_check",)))
                continue
            accepted.append(source)
            continue
        if is_generic_only_source(source):
            rejected.append(
                with_llm_triage(
                    with_access_metadata(source, access_check, CitationEligibility.from_access_check(access_check)),
                    SourceReviewDecision.REJECTED,
                    ("generic_stimulation_or_contact_only",),
                )
            )
            continue
        eligibility = CitationEligibility.from_access_check(access_check)
        if eligibility.eligible:
            accepted.append(with_access_metadata(source, access_check, eligibility))
            continue
        rejected.append(
            with_llm_triage(
                with_access_metadata(source, access_check, eligibility),
                SourceReviewDecision.REJECTED,
                (eligibility.reason,),
            )
        )
    return _AccessGateResult(accepted=tuple(accepted), rejected=tuple(rejected), pending_review=tuple(pending))


def _request_llm_triage(
    llm_client: LLMClient,
    query_expansion: QueryExpansionPlan,
    sources: tuple[SourceRecord, ...],
) -> _LLMTriageResult:
    if not sources:
        return _LLMTriageResult(response=LLMSourceTriageResponse(rationale="no candidate sources"), audit_reason=None)
    try:
        response = llm_client.complete(
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=TRIAGE_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=build_triage_payload(query_expansion, sources)),
                ],
                temperature=0.0,
                max_tokens=1200,
                response_format={"type": "json_object"},
                source_types=list(unique_source_types(sources)),
                metadata={"purpose": "source_triage"},
            )
        )
        parsed = LLMSourceTriageResponse.model_validate(json.loads(response.content))
    except json.JSONDecodeError:
        return _LLMTriageResult(response=None, audit_reason="llm_output_invalid")
    except ValidationError:
        return _LLMTriageResult(response=None, audit_reason="llm_output_invalid")
    except PermissionError:
        return _LLMTriageResult(response=None, audit_reason="llm_privacy_blocked")
    except MissingLLMAPIKeyError:
        return _LLMTriageResult(response=None, audit_reason="llm_missing_api_key")
    except UnsupportedLLMProviderError:
        return _LLMTriageResult(response=None, audit_reason="llm_provider_unsupported")
    except LLMRequestFailedError:
        return _LLMTriageResult(response=None, audit_reason="llm_request_failed")
    return _LLMTriageResult(response=parsed, audit_reason=None)


def _source_from_llm_item(source: SourceRecord, item: LLMSourceTriageItem) -> SourceRecord:
    return with_llm_triage(
        source,
        item.decision,
        (item.rationale,),
        scores={
            "topic_fit": item.topic_fit_score,
            "facet_fit": item.facet_fit_score,
            "source_type_fit": item.source_type_fit_score,
            "citation_usability": item.citation_usability_score,
        },
    )
