"""Evidence extraction workflow integration with deterministic fallback."""

from __future__ import annotations

from typing import Any

from medical_research_agent.config import get_settings
from medical_research_agent.evidence import EvidenceExtractionResult, extract_evidence_from_documents
from medical_research_agent.llm.client import get_llm_client
from medical_research_agent.llm_evidence import LLMEvidenceExtractionResult, extract_public_evidence_with_llm
from medical_research_agent.schemas import Claim, EvidenceItem, ProductSpec
from medical_research_agent.workflow.state import NodeLog, WorkflowState


def extract_evidence_node(state: WorkflowState) -> dict[str, Any]:
    """Extract deterministic evidence and optionally augment it with configured LLM output."""

    task = state["task"]
    sources = state.get("sources", [])
    documents = state.get("documents", [])
    deterministic = extract_evidence_from_documents(task.task_id, sources, documents)
    settings = get_settings()
    if settings.llm_provider == "mock":
        return _node_result(deterministic, None)

    llm_result = extract_public_evidence_with_llm(
        task.task_id,
        sources,
        documents,
        llm_client=get_llm_client(settings),
    )
    return _node_result(deterministic, llm_result)


def _node_result(
    deterministic: EvidenceExtractionResult,
    llm_result: LLMEvidenceExtractionResult | None,
) -> dict[str, Any]:
    evidence: list[EvidenceItem] = list(deterministic.evidence)
    product_specs: list[ProductSpec] = list(deterministic.product_specs)
    claims: list[Claim] = []
    llm_errors: tuple[str, ...] = ()
    llm_used = False
    needs_review = False
    skipped_private: tuple[str, ...] = ()

    if llm_result is not None:
        evidence.extend(llm_result.evidence)
        product_specs.extend(llm_result.product_specs)
        claims.extend(llm_result.claims)
        llm_errors = llm_result.errors
        llm_used = bool(llm_result.evidence or llm_result.product_specs or llm_result.claims)
        needs_review = llm_result.needs_review
        skipped_private = llm_result.skipped_private_source_ids

    result: dict[str, Any] = {
        "evidence": evidence,
        "product_specs": product_specs,
        "current_step": "extract_evidence",
        "intermediate": {
            "evidence_count": len(evidence),
            "product_spec_count": len(product_specs),
            "deterministic_evidence_count": len(deterministic.evidence),
            "llm_evidence_count": 0 if llm_result is None else len(llm_result.evidence),
            "llm_evidence_used": llm_used,
            "llm_evidence_needs_review": needs_review,
            "llm_evidence_errors": list(llm_errors),
            "llm_evidence_skipped_private_source_ids": list(skipped_private),
        },
        "errors": [f"llm_evidence:{error}" for error in llm_errors],
        "node_logs": [
            NodeLog(
                node="extract_evidence",
                message="Extracted deterministic evidence with optional schema-bound LLM augmentation.",
                metadata={
                    "evidence_count": len(evidence),
                    "product_spec_count": len(product_specs),
                    "llm_evidence_used": llm_used,
                    "llm_evidence_needs_review": needs_review,
                },
            )
        ],
    }
    if claims:
        result["claims"] = claims
    return result
