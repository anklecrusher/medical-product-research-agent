from __future__ import annotations

from medical_research_agent.evidence import extract_evidence_from_documents
from medical_research_agent.schemas import (
    DocumentFormat,
    EvidenceKind,
    EvidenceStatus,
    ParsedDocument,
    SourceRecord,
    SourceType,
)


def test_extract_evidence_detects_unit_snippets_and_product_specs() -> None:
    # Given: a useful vendor document with every MVP unit class in local text.
    source = SourceRecord(
        source_id="src_vendor_units",
        task_id="task_units",
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Acme Stim product manual",
    )
    document = ParsedDocument(
        document_id="doc_vendor_units",
        task_id="task_units",
        source_id=source.source_id,
        format=DocumentFormat.TEXT,
        title="Acme Stim product manual",
        text=(
            "Acme Stim manual line: stimulation frequency 130 Hz, pulse width 60 us, "
            "pulse width 90 μs, pulse width 100 µs, amplitude 2.5 mA, voltage 3 V, "
            "impedance 500 ohm, impedance 300 Ω, charge density 30 uC/cm2, "
            "charge density 20 μC/cm², spacing 1.5 mm, and lead distance 2 cm. "
            "These values are deterministic fixture parameters, not clinical conclusions."
        ),
    )

    # When: deterministic evidence extraction runs without any model call.
    result = extract_evidence_from_documents("task_units", [source], [document])
    quotes = " ".join(item.quote or "" for item in result.evidence)
    units = {item.unit for item in result.evidence}

    # Then: every unit-bearing snippet is traced as product-parameter evidence and specs.
    assert {
        "Hz",
        "us",
        "μs",
        "mA",
        "V",
        "ohm",
        "Ω",
        "uC/cm2",
        "μC/cm²",
        "mm",
        "cm",
    } <= units
    assert "100 µs" in quotes
    assert all(item.kind == EvidenceKind.PRODUCT_PARAMETER for item in result.evidence)
    assert all(item.source_id == source.source_id and item.document_id == document.document_id for item in result.evidence)
    assert len(result.product_specs) == len(result.evidence)


def test_extract_evidence_marks_short_documents_as_gap_without_fake_specs() -> None:
    # Given: a source-bound parsed document too short to support parameter extraction.
    source = SourceRecord(
        source_id="src_short",
        task_id="task_short",
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Short vendor brochure",
        metadata={"fixture": "short_doc"},
    )
    document = ParsedDocument(
        document_id="doc_short",
        task_id="task_short",
        source_id=source.source_id,
        format=DocumentFormat.TEXT,
        title="Short vendor brochure",
        text="Too short.",
    )

    # When: deterministic evidence extraction sees no useful unit-bearing text.
    result = extract_evidence_from_documents("task_short", [source], [document])

    # Then: it records a review gap but does not invent a product parameter.
    assert len(result.evidence) == 1
    assert result.evidence[0].kind == EvidenceKind.MARKET_FINDING
    assert result.evidence[0].status == EvidenceStatus.NEEDS_REVIEW
    assert result.evidence[0].value is None
    assert result.product_specs == []
