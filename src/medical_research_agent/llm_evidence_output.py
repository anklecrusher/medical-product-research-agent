"""Conversion from validated LLM extraction data to workflow models."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from medical_research_agent.llm_evidence_models import LLMClaim, LLMEvidenceItem, LLMEvidenceResponse, LLMProductSpec
from medical_research_agent.schemas import Claim, ClaimStatus, EvidenceItem, EvidenceStatus, ProductSpec, SourceRecord, SourceType


@dataclass(frozen=True, slots=True)
class ExtractionOutput:
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]
    claims: list[Claim]


def build_extraction_output(
    task_id: str | None,
    parsed: LLMEvidenceResponse,
    source_by_id: dict[str, SourceRecord],
) -> ExtractionOutput:
    """Convert a response whose source and evidence links have already been validated."""

    evidence = [_to_evidence(task_id, item, source_by_id[item.source_id]) for item in parsed.evidence]
    return ExtractionOutput(
        evidence=evidence,
        product_specs=[_to_product_spec(task_id, spec, evidence) for spec in parsed.product_specs],
        claims=[_to_claim(task_id, claim, evidence) for claim in parsed.claims],
    )


def _to_evidence(task_id: str | None, item: LLMEvidenceItem, source: SourceRecord) -> EvidenceItem:
    metadata: dict[str, str] = {
        "extractor": "llm_structured",
        "source_type": SourceType(source.source_type).value,
        "source_url": str(source.url),
    }
    if item.facet is not None:
        metadata["facet"] = item.facet
    return EvidenceItem(
        evidence_id=_stable_id("ev", item.source_id, item.document_id, item.statement, item.quote),
        task_id=task_id,
        source_id=item.source_id,
        document_id=item.document_id,
        kind=item.kind,
        statement=item.statement,
        value=item.value,
        unit=item.unit,
        product_name=item.product_name,
        parameter_name=item.parameter_name,
        quote=item.quote,
        location=item.location,
        confidence=item.confidence,
        status=EvidenceStatus.EXTRACTED,
        metadata=metadata,
    )


def _to_product_spec(task_id: str | None, spec: LLMProductSpec, evidence: list[EvidenceItem]) -> ProductSpec:
    linked = evidence[spec.evidence_index]
    return ProductSpec(
        spec_id=_stable_id("spec", spec.source_id, spec.parameter_name, str(spec.value), linked.evidence_id),
        task_id=task_id,
        product_name=spec.product_name,
        parameter_name=spec.parameter_name,
        value=spec.value,
        unit=spec.unit,
        source_ids=[spec.source_id],
        evidence_ids=[linked.evidence_id],
        status=EvidenceStatus.EXTRACTED,
        notes=spec.notes,
    )


def _to_claim(task_id: str | None, claim: LLMClaim, evidence: list[EvidenceItem]) -> Claim:
    return Claim(
        claim_id=_stable_id("claim", claim.source_id, claim.text),
        task_id=task_id,
        text=claim.text,
        evidence_ids=[evidence[index].evidence_id for index in claim.evidence_indices],
        source_ids=[claim.source_id],
        status=ClaimStatus.DRAFT,
        verification_note="LLM-extracted claim; downstream verifier must confirm support.",
    )


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"
