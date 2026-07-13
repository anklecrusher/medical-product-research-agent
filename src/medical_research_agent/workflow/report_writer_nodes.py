"""Configured LLM report-writer workflow adapter."""

from __future__ import annotations

from medical_research_agent.config import get_settings
from medical_research_agent.llm.client import get_llm_client
from medical_research_agent.llm_report_writer import LLMReportDraft, draft_llm_report
from medical_research_agent.report_models import ReportInputs
from medical_research_agent.report_writer import draft_evidence_report


def draft_configured_report(inputs: ReportInputs) -> LLMReportDraft:
    """Use the external LLM only when configured, otherwise preserve deterministic writing."""

    settings = get_settings()
    if settings.llm_provider == "mock":
        deterministic = draft_evidence_report(inputs)
        return LLMReportDraft(
            sections=deterministic.sections,
            claims=deterministic.claims,
            needs_review=False,
            errors=(),
            external_llm_used=False,
        )
    return draft_llm_report(inputs, llm_client=get_llm_client(settings))
