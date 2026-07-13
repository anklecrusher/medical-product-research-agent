"""Workflow adapter for deterministic rendered-report quality evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from medical_research_agent.report_models import eligible_citation_access_check
from medical_research_agent.report_quality import ReportQualityArtifacts, evaluate_report_quality
from medical_research_agent.schemas import Claim, SourceRecord
from medical_research_agent.source_contracts import AccessCheck


class QualityCheckSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    detail: str


class RenderQualitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    reasons: tuple[str, ...] = ()
    checks: tuple[QualityCheckSnapshot, ...] = ()


def evaluate_rendered_quality(
    report_markdown: str,
    sources: Sequence[SourceRecord],
    claims: Sequence[Claim],
    pdf_path: Path,
) -> RenderQualitySnapshot:
    """Evaluate final artifacts from source metadata without making network calls."""

    result = evaluate_report_quality(
        ReportQualityArtifacts(
            report_markdown=report_markdown,
            access_checks=_access_checks(sources),
            claims=tuple(claims),
            sources=tuple(sources),
            pdf_path=pdf_path,
        )
    )
    return RenderQualitySnapshot(
        passed=result.passed,
        score=result.score,
        reasons=result.reasons,
        checks=tuple(
            QualityCheckSnapshot(name=check.name, passed=check.passed, detail=check.detail)
            for check in result.checks
        ),
    )


def _access_checks(sources: Sequence[SourceRecord]) -> tuple[AccessCheck, ...]:
    checks: list[AccessCheck] = []
    for source in sources:
        check = eligible_citation_access_check(source)
        if check is not None:
            checks.append(check)
    return tuple(checks)
