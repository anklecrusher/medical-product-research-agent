"""Core Pydantic schemas shared across the research workflow."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import AnyUrl, BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class StrictBaseModel(BaseModel):
    """Project-wide base model with explicit JSON-friendly defaults."""

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
        "validate_assignment": True,
    }


class TaskStatus(StrEnum):
    DRAFT = "draft"
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_MORE_SOURCES = "needs_more_sources"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class SourceType(StrEnum):
    PUBLIC_LITERATURE = "public_literature"
    PUBLIC_WEB = "public_web"
    PUBLIC_REGULATORY = "public_regulatory"
    VENDOR_PUBLIC_DOC = "vendor_public_doc"
    USER_UPLOADED_PRIVATE = "user_uploaded_private"
    INTERNAL_PRIVATE = "internal_private"


class DocumentFormat(StrEnum):
    WEB_PAGE = "web_page"
    PDF = "pdf"
    MARKDOWN = "markdown"
    WORD = "word"
    TEXT = "text"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    PRODUCT_PARAMETER = "product_parameter"
    CLINICAL_FINDING = "clinical_finding"
    REGULATORY_FINDING = "regulatory_finding"
    MARKET_FINDING = "market_finding"
    ENGINEERING_NOTE = "engineering_note"
    OTHER = "other"


class EvidenceStatus(StrEnum):
    EXTRACTED = "extracted"
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    NEEDS_REVIEW = "needs_review"


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    NEEDS_REVIEW = "needs_review"


class ArtifactFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    LOG = "log"


class FigureKind(StrEnum):
    SOURCE_IMAGE = "source_image"
    GENERATED_CHART = "generated_chart"
    CONCEPT_DIAGRAM = "concept_diagram"


class FigureStatus(StrEnum):
    CANDIDATE = "candidate"
    SELECTED = "selected"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class TemplateBlockKind(StrEnum):
    CORE_CONCLUSION = "core_conclusion"
    PARAMETER_EVIDENCE = "parameter_evidence"
    CLINICAL_EVIDENCE = "clinical_evidence"
    COMPETITOR_COMPARISON = "competitor_comparison"
    REGULATORY_SUMMARY = "regulatory_summary"
    CONCEPT_EXPLANATION = "concept_explanation"
    ENGINEERING_ANALYSIS = "engineering_analysis"
    TEST_PLAN = "test_plan"
    RISKS_AND_GAPS = "risks_and_gaps"
    REFERENCES = "references"
    CUSTOM = "custom"


class ResearchTask(StrictBaseModel):
    """A user research request and its durable workflow identity."""

    task_id: str = Field(default_factory=lambda: _new_id("task"))
    title: str | None = None
    query: str = Field(min_length=1)
    status: TaskStatus = TaskStatus.DRAFT
    language: str = "zh-CN"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    tags: list[str] = Field(default_factory=list)
    user_notes: str | None = None
    output_dir: str | None = None


class SourceRecord(StrictBaseModel):
    """A normalized external or local source discovered for a task."""

    source_id: str = Field(default_factory=lambda: _new_id("src"))
    task_id: str | None = None
    source_type: SourceType
    title: str
    url: AnyUrl | None = None
    local_path: str | None = None
    publisher: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=_utc_now)
    search_query: str | None = None
    credibility_note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(StrictBaseModel):
    """Parsed text and metadata produced from a source."""

    document_id: str = Field(default_factory=lambda: _new_id("doc"))
    source_id: str
    task_id: str | None = None
    format: DocumentFormat = DocumentFormat.UNKNOWN
    title: str | None = None
    text: str = ""
    summary: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    language: str | None = None
    parser_name: str | None = None
    parsed_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceItem(StrictBaseModel):
    """A structured evidence unit extracted from a parsed document."""

    evidence_id: str = Field(default_factory=lambda: _new_id("ev"))
    task_id: str | None = None
    source_id: str
    document_id: str | None = None
    kind: EvidenceKind = EvidenceKind.OTHER
    statement: str = Field(min_length=1)
    value: str | float | int | None = None
    unit: str | None = None
    product_name: str | None = None
    parameter_name: str | None = None
    quote: str | None = None
    location: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: EvidenceStatus = EvidenceStatus.EXTRACTED
    extracted_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FigureAsset(StrictBaseModel):
    """A figure candidate or selected figure for a report."""

    figure_id: str = Field(default_factory=lambda: _new_id("fig"))
    task_id: str | None = None
    source_id: str | None = None
    document_id: str | None = None
    kind: FigureKind = FigureKind.SOURCE_IMAGE
    title: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    image_path: str | None = None
    image_url: AnyUrl | None = None
    source_url: AnyUrl | None = None
    source_title: str | None = None
    location: str | None = None
    recommended_section: str | None = None
    usage_note: str | None = None
    rights_note: str | None = None
    status: FigureStatus = FigureStatus.CANDIDATE
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("image_url", "source_url")
    @classmethod
    def _stringify_url(cls, value: AnyUrl | None) -> AnyUrl | None:
        return value


class ProductSpec(StrictBaseModel):
    """A product-facing parameter normalized from one or more evidence items."""

    spec_id: str = Field(default_factory=lambda: _new_id("spec"))
    task_id: str | None = None
    product_name: str
    parameter_name: str
    value: str | float | int
    unit: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: EvidenceStatus = EvidenceStatus.EXTRACTED
    notes: str | None = None

    @field_validator("source_ids", "evidence_ids")
    @classmethod
    def _deduplicate_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class Claim(StrictBaseModel):
    """A report claim and its evidence support status."""

    claim_id: str = Field(default_factory=lambda: _new_id("claim"))
    task_id: str | None = None
    text: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.DRAFT
    verification_note: str | None = None

    @field_validator("source_ids", "evidence_ids")
    @classmethod
    def _deduplicate_ids(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class ReportSection(StrictBaseModel):
    """A planned or generated report section."""

    section_id: str = Field(default_factory=lambda: _new_id("section"))
    task_id: str | None = None
    title: str
    level: int = Field(default=2, ge=1, le=6)
    order: int = Field(default=0, ge=0)
    content_markdown: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    figure_ids: list[str] = Field(default_factory=list)
    status: Literal["planned", "draft", "reviewed", "final"] = "planned"


class ReportTemplateBlock(StrictBaseModel):
    """Reusable report section contract for planning and rendering."""

    block_id: str
    kind: TemplateBlockKind = TemplateBlockKind.CUSTOM
    title: str
    required: bool = False
    default_order: int = Field(default=0, ge=0)
    description: str = ""
    evidence_kinds: list[EvidenceKind] = Field(default_factory=list)
    figure_required: bool = False
    figure_optional: bool = True


class ReportTemplate(StrictBaseModel):
    """Versioned report template definition with flexible blocks."""

    template_id: str
    name: str
    version: str
    language: str = "zh-CN"
    required_block_ids: list[str] = Field(default_factory=list)
    blocks: list[ReportTemplateBlock] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportArtifact(StrictBaseModel):
    """A durable report or intermediate output produced by the workflow."""

    artifact_id: str = Field(default_factory=lambda: _new_id("artifact"))
    task_id: str
    format: ArtifactFormat
    path: str
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
