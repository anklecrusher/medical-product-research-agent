from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from medical_research_agent.schemas import EvidenceKind
from mvp_flow_fixtures import EXPECTED_SOURCE_IDS, run_fixture_workflow


def test_fixture_flow_extracts_source_traced_evidence_and_product_specs_without_external_llm(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: five deterministic in-memory source/document fixtures, including a private upload.
    state = run_fixture_workflow(monkeypatch, tmp_path)

    # When: the current workflow back half extracts evidence and product specs.
    evidence = state["evidence"]
    product_specs = state["product_specs"]
    evidence_source_ids = {item.source_id for item in evidence}
    spec_keys = {(item.product_name, item.parameter_name, str(item.value), item.unit) for item in product_specs}

    # Then: every fixture source is traced by non-mock evidence and unit-bearing sources create specs.
    assert {source.source_id for source in state["sources"]} == EXPECTED_SOURCE_IDS
    assert EXPECTED_SOURCE_IDS <= evidence_source_ids
    assert all(item.evidence_id and item.source_id in EXPECTED_SOURCE_IDS for item in evidence)
    assert all(item.document_id is not None for item in evidence)
    assert all(item.metadata.get("mock") is not True for item in evidence)
    assert any(item.kind == EvidenceKind.CLINICAL_FINDING and item.source_id == "src_literature" for item in evidence)
    assert any(item.kind == EvidenceKind.REGULATORY_FINDING and item.source_id == "src_regulatory" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_vendor" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_public_web" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_private_upload" for item in evidence)
    assert ("Fixture NeuroStim", "stimulation_frequency", "2-130", "Hz") in spec_keys
    assert any(item.source_ids and item.evidence_ids for item in product_specs)
