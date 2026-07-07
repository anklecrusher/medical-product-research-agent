from __future__ import annotations

from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ProductSpec,
)
from medical_research_agent.workflow.nodes import deduplicate_evidence


def _parameter_evidence(
    evidence_id: str,
    source_id: str,
    document_id: str,
    value: str,
    statement: str,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        task_id="task_dedup",
        source_id=source_id,
        document_id=document_id,
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement=statement,
        value=value,
        unit="Hz",
        product_name="NeuroStim",
        parameter_name="stimulation_frequency",
        quote=f"stimulation frequency {value} Hz",
        status=EvidenceStatus.EXTRACTED,
    )


def _product_spec(
    spec_id: str,
    source_ids: list[str],
    evidence_ids: list[str],
    value: str,
) -> ProductSpec:
    return ProductSpec(
        spec_id=spec_id,
        task_id="task_dedup",
        product_name="NeuroStim",
        parameter_name="stimulation_frequency",
        value=value,
        unit="Hz",
        source_ids=source_ids,
        evidence_ids=evidence_ids,
        status=EvidenceStatus.EXTRACTED,
    )


def test_deduplicate_evidence_collapses_exact_same_source_parameter_rows() -> None:
    # Given: two extracted rows describe the same source/document parameter and product spec.
    first = _parameter_evidence(
        "ev_freq_a",
        "src_vendor",
        "doc_vendor",
        "2-130",
        "NeuroStim stimulation_frequency is 2-130 Hz according to vendor manual.",
    )
    duplicate = _parameter_evidence(
        "ev_freq_b",
        "src_vendor",
        "doc_vendor",
        "2-130",
        "NeuroStim stimulation_frequency is 2-130 Hz according to vendor manual.",
    )

    # When: workflow deduplication runs before report planning/writing.
    result = deduplicate_evidence(
        {
            "evidence": [first, duplicate],
            "product_specs": [
                _product_spec("spec_a", ["src_vendor", "src_vendor"], ["ev_freq_a", "ev_freq_a"], "2-130"),
                _product_spec("spec_b", ["src_vendor"], ["ev_freq_b"], "2-130"),
            ],
        }
    )

    # Then: duplicate evidence shrinks and product-spec report rows keep deduplicated links.
    assert [item.evidence_id for item in result["evidence"]] == ["ev_freq_a"]
    assert len(result["product_specs"]) == 1
    assert result["product_specs"][0].source_ids == ["src_vendor"]
    assert result["product_specs"][0].evidence_ids == ["ev_freq_a"]


def test_deduplicate_evidence_preserves_and_marks_cross_source_conflicts() -> None:
    # Given: two sources disagree on the same product parameter range.
    vendor = _parameter_evidence(
        "ev_vendor_freq",
        "src_vendor",
        "doc_vendor",
        "2-130",
        "NeuroStim stimulation_frequency is 2-130 Hz according to vendor manual.",
    )
    public_web = _parameter_evidence(
        "ev_web_freq",
        "src_web",
        "doc_web",
        "5-160",
        "NeuroStim stimulation_frequency is 5-160 Hz according to public comparison page.",
    )

    # When: deduplication encounters conflicting values across different sources.
    result = deduplicate_evidence(
        {
            "evidence": [vendor, public_web],
            "product_specs": [
                _product_spec("spec_vendor", ["src_vendor"], ["ev_vendor_freq"], "2-130"),
                _product_spec("spec_web", ["src_web"], ["ev_web_freq"], "5-160"),
            ],
        }
    )

    # Then: both values remain visible and receive review/conflict status.
    assert [item.evidence_id for item in result["evidence"]] == ["ev_vendor_freq", "ev_web_freq"]
    assert {item.status for item in result["evidence"]} == {EvidenceStatus.CONFLICTING}
    assert {item.status for item in result["product_specs"]} == {EvidenceStatus.CONFLICTING}
    assert {str(item.value) for item in result["product_specs"]} == {"2-130", "5-160"}
