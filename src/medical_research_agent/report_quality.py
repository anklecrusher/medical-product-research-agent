"""Deterministic quality checks for generated research reports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from medical_research_agent.schemas import Claim, ClaimStatus, SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility


MIN_SCORE_TO_PASS: Final = 0.8
URL_PATTERN: Final = re.compile(r"https?://[^\s)\]>]+")
TABLE_ROW_PATTERN: Final = re.compile(r"^\|.*\|$", re.MULTILINE)
SECTION_PATTERN: Final = re.compile(r"^#{2,}\s+(.+)$", re.MULTILINE)
CITATION_PATTERN: Final = re.compile(r"(?:\[[^\]]+\]\(https?://[^)]+\)|<sup>\[[^\]]+\]</sup>)")
SOURCE_TYPE_VALUES: Final = tuple(item.value for item in SourceType)


@dataclass(frozen=True, slots=True)
class ReportQualityArtifacts:
    report_markdown: str
    access_checks: tuple[AccessCheck, ...] = ()
    claims: tuple[Claim, ...] = ()
    sources: tuple[SourceRecord, ...] = ()
    pdf_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ReportQualityCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ReportQualityResult:
    passed: bool
    score: float
    checks: tuple[ReportQualityCheck, ...]
    reasons: tuple[str, ...] = field(default=())


def evaluate_report_quality(artifacts: ReportQualityArtifacts) -> ReportQualityResult:
    """Evaluate broad report depth without relying on benchmark wording."""

    text = artifacts.report_markdown.strip()
    checks = (
        _core_conclusions(text),
        _tables(text),
        _source_diversity(artifacts),
        _evidence_breadth(artifacts),
        _supported_claims(artifacts),
        _free_citations(text, artifacts.access_checks),
        _topic_sections(text),
        _missing_evidence(text),
        _citation_density(text),
        _pdf_readability(artifacts.pdf_path),
    )
    score = sum(1 for check in checks if check.passed) / len(checks)
    reasons = tuple(f"{check.name}: {check.detail}" for check in checks if not check.passed)
    return ReportQualityResult(
        passed=score >= MIN_SCORE_TO_PASS and not reasons,
        score=score,
        checks=checks,
        reasons=reasons,
    )


def _core_conclusions(text: str) -> ReportQualityCheck:
    conclusion_text = _section_body(text, "核心结论")
    bullet_count = conclusion_text.count("\n- ") + int(conclusion_text.startswith("- "))
    passed = bullet_count >= 2 and _has_url(conclusion_text)
    return ReportQualityCheck("core conclusions", passed, f"found {bullet_count} source-linked conclusion bullets")


def _tables(text: str) -> ReportQualityCheck:
    table_count = sum(1 for line in TABLE_ROW_PATTERN.findall(text) if "---" in line)
    return ReportQualityCheck("tables", table_count >= 2, f"found {table_count} markdown tables")


def _source_diversity(artifacts: ReportQualityArtifacts) -> ReportQualityCheck:
    source_types = _source_types(artifacts)
    citable_count = sum(1 for check in artifacts.access_checks if CitationEligibility.from_access_check(check).eligible)
    passed = len(source_types) >= 3 and citable_count >= 3
    return ReportQualityCheck(
        "source diversity",
        passed,
        f"found {len(source_types)} source types and {citable_count} final-citable free sources",
    )


def _evidence_breadth(artifacts: ReportQualityArtifacts) -> ReportQualityCheck:
    final_citable_source_ids = {
        check.source_id for check in artifacts.access_checks if CitationEligibility.from_access_check(check).eligible
    }
    supported_source_ids = {
        source_id
        for claim in artifacts.claims
        if ClaimStatus(claim.status) == ClaimStatus.SUPPORTED and claim.evidence_ids
        for source_id in claim.source_ids
        if source_id in final_citable_source_ids
    }
    return ReportQualityCheck(
        "evidence breadth",
        len(supported_source_ids) >= 3,
        f"found supported evidence links across {len(supported_source_ids)} final-citable sources",
    )


def _supported_claims(artifacts: ReportQualityArtifacts) -> ReportQualityCheck:
    supported = [
        claim
        for claim in artifacts.claims
        if ClaimStatus(claim.status) == ClaimStatus.SUPPORTED and claim.evidence_ids and claim.source_ids
    ]
    return ReportQualityCheck("supported claims", bool(supported), f"found {len(supported)} supported linked claims")


def _free_citations(text: str, access_checks: tuple[AccessCheck, ...]) -> ReportQualityCheck:
    report_urls = set(URL_PATTERN.findall(text))
    free_urls = {str(check.url).rstrip("/") for check in access_checks if CitationEligibility.from_access_check(check).eligible}
    cited_free_urls = {url.rstrip("/") for url in report_urls if url.rstrip("/") in free_urls}
    passed = len(cited_free_urls) >= 3 and cited_free_urls == {url.rstrip("/") for url in report_urls}
    return ReportQualityCheck(
        "free citations",
        passed,
        f"found {len(cited_free_urls)} free cited links among {len(report_urls)} report links",
    )


def _topic_sections(text: str) -> ReportQualityCheck:
    titles = tuple(title.casefold() for title in SECTION_PATTERN.findall(text))
    categories = (
        ("background", ("背景", "术语", "方法")),
        ("analysis", ("技术", "产品", "参数", "公司", "市场", "竞品")),
        ("evidence", ("论文", "监管", "注册", "证据")),
        ("gaps", ("风险", "边界", "未确认", "缺口")),
    )
    matched = [name for name, keywords in categories if any(keyword in title for title in titles for keyword in keywords)]
    return ReportQualityCheck(
        "topic-appropriate sections",
        len(matched) >= 4,
        f"matched {len(matched)} broad section categories",
    )


def _missing_evidence(text: str) -> ReportQualityCheck:
    lower_text = text.casefold()
    markers = ("未确认", "needs_review", "缺少", "缺口", "边界")
    matched = sum(1 for marker in markers if marker in lower_text)
    return ReportQualityCheck("missing evidence quality", matched >= 2, f"found {matched} gap/boundary markers")


def _citation_density(text: str) -> ReportQualityCheck:
    word_units = max(len(re.findall(r"[\w\u4e00-\u9fff]+", text)), 1)
    citations = len(CITATION_PATTERN.findall(text)) + len(URL_PATTERN.findall(_section_body(text, "参考")))
    density = citations / word_units
    return ReportQualityCheck("citation density", citations >= 3 and density >= 0.01, f"found {citations} citations")


def _pdf_readability(pdf_path: Path | None) -> ReportQualityCheck:
    readable = pdf_path is not None and pdf_path.exists() and pdf_path.stat().st_size > 12
    if readable:
        with pdf_path.open("rb") as handle:
            readable = handle.read(5) == b"%PDF-"
    return ReportQualityCheck("PDF readability", readable, "PDF exists and starts with %PDF-" if readable else "PDF missing or unreadable")


def _section_body(text: str, heading_fragment: str) -> str:
    match = re.search(rf"^##\s+.*{re.escape(heading_fragment)}.*$", text, re.MULTILINE)
    if match is None:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = len(text) if next_heading is None else match.end() + next_heading.start()
    return text[match.end() : end].strip()


def _has_url(text: str) -> bool:
    return URL_PATTERN.search(text) is not None


def _source_types(artifacts: ReportQualityArtifacts) -> set[SourceType]:
    source_types = {SourceType(source.source_type) for source in artifacts.sources}
    for access_check in artifacts.access_checks:
        note = access_check.evidence_note
        if note in SOURCE_TYPE_VALUES:
            source_types.add(SourceType(note))
    return source_types
