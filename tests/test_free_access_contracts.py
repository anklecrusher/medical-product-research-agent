import pytest
from pydantic import ValidationError

from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import (
    AccessCheck,
    CitationEligibility,
    FreeAccessStatus,
    LLMResearchDecision,
    ReportQualityMetric,
    ReportQualityMetrics,
    SourceRoute,
    SourceStrategy,
)


def test_source_strategy_and_report_metrics_serialize_when_instantiated() -> None:
    # Given
    route = SourceRoute(
        route_id="literature-open-full-text",
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_types=(SourceType.PUBLIC_LITERATURE,),
        connectors=("pubmed", "pmc"),
        queries=("DBS electrode contact open access",),
        budget=3,
        rationale="Need open literature evidence for device parameters.",
    )
    strategy = SourceStrategy(
        task_id="task_contracts",
        objective="Map free public evidence for a medical device topic.",
        routes=(route,),
        max_follow_up_rounds=1,
    )
    metrics = ReportQualityMetrics(
        metrics=(
            ReportQualityMetric(name="eligible_reference_rate", score=1.0, required=True),
            ReportQualityMetric(name="supported_claim_rate", score=0.8, required=True),
        ),
        summary="Report has free references and source-backed claims.",
    )
    decision = LLMResearchDecision(
        decision_id="decision_1",
        selected_routes=(route.route_id,),
        accepted_source_ids=("src_pdf",),
        rejected_source_ids=("src_metadata",),
        rationale="Prefer free PDF and open full-text sources.",
    )

    # When
    dumped = {
        "strategy": strategy.model_dump(mode="json"),
        "metrics": metrics.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
    }

    # Then
    assert dumped["strategy"]["routes"][0]["connectors"] == ["pubmed", "pmc"]
    assert dumped["metrics"]["passed"] is True
    assert dumped["decision"]["selected_routes"] == ["literature-open-full-text"]


def test_free_pdf_and_html_sources_are_final_citation_eligible() -> None:
    # Given
    pdf_source = SourceRecord(
        source_id="src_pdf",
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Public clinician manual PDF",
        url="https://example.com/manual.pdf",
    )
    html_source = SourceRecord(
        source_id="src_html",
        source_type=SourceType.PUBLIC_WEB,
        title="Open product page",
        url="https://example.com/product",
    )

    # When
    pdf_eligibility = CitationEligibility.from_access_check(
        AccessCheck(source_id=pdf_source.source_id, url=pdf_source.url, status=FreeAccessStatus.PDF_ACCESSIBLE),
    )
    html_eligibility = CitationEligibility.from_access_check(
        AccessCheck(source_id=html_source.source_id, url=html_source.url, status=FreeAccessStatus.FREE_LANDING_PAGE),
    )

    # Then
    assert pdf_eligibility.eligible is True
    assert html_eligibility.eligible is True


def test_paywalled_metadata_only_and_missing_url_sources_are_final_citation_ineligible() -> None:
    # Given
    paywalled_check = AccessCheck(
        source_id="src_paywalled",
        url="https://example.com/paywalled",
        status=FreeAccessStatus.PAYWALLED,
    )
    metadata_only_check = AccessCheck(
        source_id="src_metadata",
        url="https://doi.org/10.1000/metadata",
        status=FreeAccessStatus.METADATA_ONLY,
    )
    missing_url_check = AccessCheck(source_id="src_missing_url", status=FreeAccessStatus.PDF_ACCESSIBLE)

    # When
    eligibilities = (
        CitationEligibility.from_access_check(paywalled_check),
        CitationEligibility.from_access_check(metadata_only_check),
        CitationEligibility.from_access_check(missing_url_check),
    )

    # Then
    assert [item.eligible for item in eligibilities] == [False, False, False]
    assert eligibilities[2].reason == "source_url_required_for_final_citation"


def test_malformed_access_status_is_rejected_at_parse_boundary() -> None:
    # Given
    payload = {
        "source_id": "src_bad",
        "url": "https://example.com/item",
        "status": "freeish",
    }

    # When / Then
    with pytest.raises(ValidationError):
        AccessCheck.model_validate(payload)
