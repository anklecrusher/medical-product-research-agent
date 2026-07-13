from __future__ import annotations

from medical_research_agent.report_models import citation_render_projection
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus
from medical_research_agent.workflow.quality_nodes import evaluate_rendered_quality


def test_rendered_quality_counts_only_sources_allowed_by_citation_projection(tmp_path) -> None:
    # Given: one valid public source plus private, URL-mismatched, and citation-mismatched records.
    valid = _source("src_valid", SourceType.PUBLIC_WEB, "https://example.test/valid")
    private = _source("src_private", SourceType.INTERNAL_PRIVATE, "https://example.test/private")
    url_mismatch = _source(
        "src_url_mismatch",
        SourceType.PUBLIC_REGULATORY,
        "https://example.test/regulatory",
        access_url="https://example.test/other",
    )
    citation_mismatch = _source(
        "src_citation_mismatch",
        SourceType.PUBLIC_LITERATURE,
        "https://example.test/literature",
        citation_source_id="src_forged",
    )
    sources = [valid, private, url_mismatch, citation_mismatch]
    report = "\n".join(str(source.url) for source in sources)
    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(b"%PDF-fixture-content")

    # When: final report quality and final citation projection inspect the same records.
    quality = evaluate_rendered_quality(report, sources, [], pdf_path)
    projection = citation_render_projection(sources)

    # Then: both boundaries recognize only the valid public source as final-citable.
    source_diversity = next(check for check in quality.checks if check.name == "source diversity")
    assert [source.source_id for source in projection.references] == [valid.source_id]
    assert "1 final-citable free sources" in source_diversity.detail


def _source(
    source_id: str,
    source_type: SourceType,
    url: str,
    *,
    access_url: str | None = None,
    citation_source_id: str | None = None,
) -> SourceRecord:
    access = AccessCheck(
        source_id=source_id,
        url=access_url or url,
        status=FreeAccessStatus.FREE_LANDING_PAGE,
    )
    citation = CitationEligibility.from_access_check(access).model_copy(
        update={"source_id": citation_source_id or source_id}
    )
    return SourceRecord(
        source_id=source_id,
        source_type=source_type,
        title=source_id,
        url=url,
        metadata={
            "access_check": access.model_dump(mode="json"),
            "citation_eligibility": citation.model_dump(mode="json"),
        },
    )
