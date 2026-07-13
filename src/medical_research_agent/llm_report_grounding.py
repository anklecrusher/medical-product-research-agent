"""Prompt construction and source/evidence grounding for LLM report responses."""

from __future__ import annotations

from dataclasses import asdict
import json

from medical_research_agent.llm.models import LLMMessage, LLMRequest
from medical_research_agent.llm_report_models import LLMReportClaim, LLMReportResponse, LLMReportSection
from medical_research_agent.report_models import ReportInputs
from medical_research_agent.schemas import EvidenceItem, EvidenceKind, EvidenceStatus, SourceRecord, SourceType


def build_report_request(
    inputs: ReportInputs,
    sources: list[SourceRecord],
    evidence: list[EvidenceItem],
    system_prompt: str,
) -> LLMRequest:
    """Build a provider-neutral JSON report request from eligible public evidence only."""

    payload = {
        "task": {"title": inputs.task.title, "query": inputs.task.query},
        "planned_sections": [
            {"section_id": section.section_id, "title": section.title}
            for section in inputs.planned_sections
        ],
        "eligible_sources": [
            {
                "source_id": source.source_id,
                "source_type": SourceType(source.source_type).value,
                "title": source.title,
                "url": str(source.url),
            }
            for source in sources
        ],
        "evidence": [
            {
                "evidence_id": item.evidence_id,
                "source_id": item.source_id,
                "kind": EvidenceKind(item.kind).value,
                "statement": item.statement,
                "quote": item.quote,
                "location": item.location,
                "status": EvidenceStatus(item.status).value,
            }
            for item in evidence
        ],
        "product_specs": [spec.model_dump(mode="json") for spec in inputs.product_specs],
        "evidence_gaps": [asdict(gap) for gap in inputs.evidence_gaps],
        "required_output": {
            "sections": "section_id, content_markdown, evidence_ids, source_ids, claim_indices",
            "claims": "text, evidence_ids, source_ids, needs_review",
        },
    }
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
        ],
        temperature=0.1,
        max_tokens=4000,
        response_format={"type": "json_object"},
        source_types=list(_unique_source_types(sources)),
        metadata={"purpose": "llm_report_writer"},
    )


def validate_report_response(
    parsed: LLMReportResponse,
    inputs: ReportInputs,
    eligible_source_ids: set[str],
    eligible_evidence: list[EvidenceItem],
) -> tuple[str, ...]:
    """Reject unknown, ineligible, mismatched, or structurally stale response links."""

    planned_ids = {section.section_id for section in inputs.planned_sections}
    evidence_by_id = {item.evidence_id: item for item in eligible_evidence}
    errors: list[str] = []
    seen_sections: set[str] = set()
    for section in parsed.sections:
        if section.section_id not in planned_ids:
            errors.append(f"unknown_section_id:{section.section_id}")
        if section.section_id in seen_sections:
            errors.append(f"duplicate_section_id:{section.section_id}")
        seen_sections.add(section.section_id)
        if not (section.evidence_ids or section.source_ids or section.claim_indices):
            errors.append(f"unsupported_section_without_grounding:{section.section_id}")
        errors.extend(_validate_links(section.evidence_ids, section.source_ids, evidence_by_id, eligible_source_ids))
        errors.extend(_validate_claim_indices(section, len(parsed.claims)))
        errors.extend(_validate_section_claim_links(section, parsed.claims))
    for claim in parsed.claims:
        errors.extend(_validate_links(claim.evidence_ids, claim.source_ids, evidence_by_id, eligible_source_ids))
    return tuple(dict.fromkeys(errors))


def _validate_links(
    evidence_ids: tuple[str, ...],
    source_ids: tuple[str, ...],
    evidence_by_id: dict[str, EvidenceItem],
    eligible_source_ids: set[str],
) -> tuple[str, ...]:
    errors: list[str] = []
    for source_id in source_ids:
        if source_id not in eligible_source_ids:
            errors.append(f"ineligible_or_unknown_source_id:{source_id}")
    for evidence_id in evidence_ids:
        item = evidence_by_id.get(evidence_id)
        if item is None:
            errors.append(f"unknown_evidence_id:{evidence_id}")
            continue
        if item.source_id not in source_ids:
            errors.append(f"evidence_source_mismatch:{evidence_id}:{item.source_id}")
    return tuple(errors)


def _validate_claim_indices(section: LLMReportSection, claim_count: int) -> tuple[str, ...]:
    return tuple(
        f"invalid_claim_index:{section.section_id}:{index}"
        for index in section.claim_indices
        if index < 0 or index >= claim_count
    )


def _validate_section_claim_links(
    section: LLMReportSection,
    claims: tuple[LLMReportClaim, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if not section.evidence_ids:
        errors.append(f"section_without_evidence:{section.section_id}")
    if not section.source_ids:
        errors.append(f"section_without_source:{section.section_id}")
    for index in section.claim_indices:
        if index < 0 or index >= len(claims):
            continue
        claim = claims[index]
        if not set(claim.evidence_ids).intersection(section.evidence_ids):
            errors.append(f"section_claim_evidence_unlinked:{section.section_id}:{index}")
        if not set(claim.source_ids).intersection(section.source_ids):
            errors.append(f"section_claim_source_unlinked:{section.section_id}:{index}")
    return tuple(errors)


def _unique_source_types(sources: list[SourceRecord]) -> tuple[SourceType, ...]:
    result: list[SourceType] = []
    for source in sources:
        source_type = SourceType(source.source_type)
        if source_type not in result:
            result.append(source_type)
    return tuple(result)
