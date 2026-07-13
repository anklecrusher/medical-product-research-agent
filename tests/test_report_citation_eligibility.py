from __future__ import annotations

import json
from pathlib import Path

from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus
from medical_research_agent.workflow import report_nodes
from medical_research_agent.workflow.graph import create_initial_state


INELIGIBLE_STATUSES = (
    FreeAccessStatus.METADATA_ONLY,
    FreeAccessStatus.PAYWALLED,
    FreeAccessStatus.BLOCKED,
    FreeAccessStatus.LOGIN_REQUIRED,
    FreeAccessStatus.NOT_FOUND,
    FreeAccessStatus.PARSER_FAILED,
    FreeAccessStatus.NEEDS_REVIEW,
)


def test_rendered_references_only_include_final_citable_sources_and_preserve_audit(tmp_path: Path) -> None:
    # Given: eligible, abstract-only, ineligible, and pending sources are retained in workflow state.
    state = create_initial_state("Citation eligibility fixture", output_dir=tmp_path)
    eligible_source = _source_with_access("src_pdf", FreeAccessStatus.PDF_ACCESSIBLE)
    abstract_source = _source_with_access("src_pubmed_abstract", FreeAccessStatus.ABSTRACT_ACCESSIBLE)
    ineligible_sources = [_source_with_access(f"src_{status.value}", status) for status in INELIGIBLE_STATUSES]
    pending_source = SourceRecord(
        source_id="src_missing_access_check",
        task_id=state["task"].task_id,
        source_type=SourceType.PUBLIC_WEB,
        title="Pending access verification",
        url="https://example.test/pending",
    )
    state["sources"] = [eligible_source, abstract_source, *ineligible_sources, pending_source]

    # When: durable report artifacts are rendered.
    result = report_nodes.render_outputs(state)
    rendered = result["report_markdown"]
    sources_json = json.loads((tmp_path / "sources.json").read_text(encoding="utf-8"))

    # Then: final references contain only final-citable items and label abstract evidence accurately.
    references, audit = _references_and_audit(rendered)
    assert eligible_source.source_id in references
    assert abstract_source.source_id in references
    assert "仅摘要证据，非全文" in references
    for source in ineligible_sources:
        assert source.source_id not in references
        assert source.source_id in audit
        assert source.metadata["access_check"]["status"] in audit
    assert pending_source.source_id not in references
    assert pending_source.source_id in audit
    assert "missing_or_invalid_access_check" in audit
    assert {item["source_id"] for item in sources_json} == {
        source.source_id for source in state["sources"]
    }


def test_access_check_cannot_be_overridden_by_incorrect_eligibility_metadata(tmp_path: Path) -> None:
    # Given: stale eligibility metadata incorrectly says a paywalled source is citable.
    state = create_initial_state("Access metadata consistency fixture", output_dir=tmp_path)
    source = _source_with_access("src_inconsistent_paywall", FreeAccessStatus.PAYWALLED)
    metadata = {
        **source.metadata,
        "citation_eligibility": CitationEligibility(
            source_id=source.source_id,
            eligible=True,
            status=FreeAccessStatus.PAYWALLED,
            url=str(source.url),
            reason="stale_eligibility_metadata",
        ).model_dump(mode="json"),
    }
    state["sources"] = [source.model_copy(update={"metadata": metadata})]

    # When: the report renderer applies citation eligibility.
    rendered = report_nodes.render_outputs(state)["report_markdown"]
    references, audit = _references_and_audit(rendered)

    # Then: access status remains the final safety gate and the mismatch is auditable.
    assert source.source_id not in references
    assert source.source_id in audit
    assert "access_status_not_final_citable:paywalled" in audit


def _source_with_access(source_id: str, status: FreeAccessStatus) -> SourceRecord:
    source = SourceRecord(
        source_id=source_id,
        source_type=SourceType.PUBLIC_LITERATURE,
        title=f"Source for {status.value}",
        url=f"https://example.test/{source_id}",
    )
    access_check = AccessCheck(source_id=source.source_id, url=str(source.url), status=status)
    return source.model_copy(
        update={
            "metadata": {
                "access_check": access_check.model_dump(mode="json"),
                "citation_eligibility": CitationEligibility.from_access_check(access_check).model_dump(mode="json"),
            }
        }
    )


def _references_and_audit(rendered: str) -> tuple[str, str]:
    references_heading = "## 参考文献与来源链接"
    audit_heading = "## 来源审计与证据缺口"
    references = rendered.split(references_heading, maxsplit=1)[1].split(audit_heading, maxsplit=1)[0]
    audit = rendered.split(audit_heading, maxsplit=1)[1]
    return references, audit
