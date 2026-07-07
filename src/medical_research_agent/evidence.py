"""Deterministic evidence and product-spec extraction for MVP workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha1
from typing import Final, assert_never

from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ParsedDocument,
    ProductSpec,
    SourceRecord,
    SourceType,
)


MIN_USEFUL_TEXT_CHARS: Final = 120
SNIPPET_LIMIT: Final = 220
UNIT_PATTERN: Final = r"uC/cm2|μC/cm²|µs|μs|ohm|Hz|mA|mm|cm|us|Ω|V"
VALUE_PATTERN: Final = r"\d+(?:\.\d+)?(?:\s*(?:-|–|—|~|to|至|到)\s*\d+(?:\.\d+)?)?"
UNIT_RE: Final = re.compile(
    rf"(?P<value>{VALUE_PATTERN})\s*(?P<unit>{UNIT_PATTERN})\b",
    re.IGNORECASE,
)
BOUNDARY_RE: Final = re.compile(r"[\n.;。；]")


@dataclass(frozen=True, slots=True)
class EvidenceExtractionResult:
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    task_id: str | None
    source: SourceRecord
    document: ParsedDocument


@dataclass(frozen=True, slots=True)
class UnitSnippet:
    value: str
    unit: str
    quote: str
    location: str
    parameter_name: str


def extract_evidence_from_documents(
    task_id: str | None,
    sources: list[SourceRecord],
    documents: list[ParsedDocument],
) -> EvidenceExtractionResult:
    """Extract deterministic evidence items and product specs from documents."""

    source_by_id = {source.source_id: source for source in sources}
    evidence: list[EvidenceItem] = []
    product_specs: list[ProductSpec] = []

    for document in documents:
        source = source_by_id.get(document.source_id)
        if source is None:
            continue

        context = ExtractionContext(task_id=task_id, source=source, document=document)
        document_evidence = _extract_document_evidence(context)
        evidence.extend(document_evidence)
        product_specs.extend(_product_spec_from_evidence(item) for item in document_evidence if _is_spec_evidence(item))

    return EvidenceExtractionResult(evidence=evidence, product_specs=product_specs)


def _extract_document_evidence(context: ExtractionContext) -> list[EvidenceItem]:
    text = context.document.text.strip()
    unit_snippets = _unit_snippets(context.document)

    if unit_snippets:
        return [_unit_evidence(context, snippet, index) for index, snippet in enumerate(unit_snippets, start=1)]

    if len(text) >= MIN_USEFUL_TEXT_CHARS:
        return [_gap_evidence(context, "parsed text contains no deterministic unit-bearing parameter")]

    if _has_source_gap_seed(context.source):
        return [_gap_evidence(context, "parsed text is too short for deterministic extraction")]

    return []


def _unit_evidence(context: ExtractionContext, snippet: UnitSnippet, index: int) -> EvidenceItem:
    source_type = SourceType(context.source.source_type)
    kind = _evidence_kind(source_type, has_unit=True, text=snippet.quote)
    product_name = _product_name(context.source, context.document)
    statement = (
        f"{product_name} {snippet.parameter_name} is {snippet.value} {snippet.unit} "
        f"according to {context.source.title}."
    )
    return EvidenceItem(
        evidence_id=_stable_id("ev", context.document.document_id, str(index), statement),
        task_id=context.task_id,
        source_id=context.source.source_id,
        document_id=context.document.document_id,
        kind=kind,
        statement=statement,
        value=snippet.value,
        unit=snippet.unit,
        product_name=product_name,
        parameter_name=snippet.parameter_name,
        quote=snippet.quote,
        location=snippet.location,
        confidence=0.74,
        status=EvidenceStatus.EXTRACTED,
        metadata=_evidence_metadata(context, source_type, "unit_snippet"),
    )


def _gap_evidence(context: ExtractionContext, reason: str) -> EvidenceItem:
    source_type = SourceType(context.source.source_type)
    kind = _evidence_kind(source_type, has_unit=False, text=context.document.text)
    quote = _gap_quote(context)
    statement = f"{context.source.title}: {reason}; manual review is required before using it as a conclusion."
    return EvidenceItem(
        evidence_id=_stable_id("ev", context.document.document_id, "gap", statement),
        task_id=context.task_id,
        source_id=context.source.source_id,
        document_id=context.document.document_id,
        kind=kind,
        statement=statement,
        quote=quote,
        location=_document_location(context.document, 1),
        confidence=0.42,
        status=EvidenceStatus.NEEDS_REVIEW,
        metadata=_evidence_metadata(context, source_type, "gap"),
    )


def _product_spec_from_evidence(item: EvidenceItem) -> ProductSpec:
    product_name = item.product_name or "Unknown product"
    parameter_name = item.parameter_name or "measurement"
    value = item.value or "needs_review"
    unit_part = item.unit or ""
    return ProductSpec(
        spec_id=_stable_id("spec", product_name, parameter_name, str(value), unit_part, item.source_id),
        task_id=item.task_id,
        product_name=product_name,
        parameter_name=parameter_name,
        value=value,
        unit=item.unit,
        source_ids=[item.source_id],
        evidence_ids=[item.evidence_id],
        status=item.status,
        notes="Extracted from deterministic unit-bearing snippet.",
    )


def _is_spec_evidence(item: EvidenceItem) -> bool:
    return item.kind == EvidenceKind.PRODUCT_PARAMETER and item.value is not None


def _evidence_kind(source_type: SourceType, has_unit: bool, text: str) -> EvidenceKind:
    match source_type:
        case SourceType.VENDOR_PUBLIC_DOC:
            return EvidenceKind.PRODUCT_PARAMETER if has_unit else EvidenceKind.MARKET_FINDING
        case SourceType.PUBLIC_REGULATORY:
            return EvidenceKind.REGULATORY_FINDING
        case SourceType.PUBLIC_LITERATURE:
            return EvidenceKind.CLINICAL_FINDING if _has_clinical_keywords(text) else EvidenceKind.ENGINEERING_NOTE
        case SourceType.PUBLIC_WEB:
            return EvidenceKind.PRODUCT_PARAMETER if has_unit else EvidenceKind.MARKET_FINDING
        case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
            return EvidenceKind.PRODUCT_PARAMETER if has_unit else EvidenceKind.OTHER
        case unreachable:
            assert_never(unreachable)


def _unit_snippets(document: ParsedDocument) -> list[UnitSnippet]:
    snippets: list[UnitSnippet] = []
    text = document.text
    for match in UNIT_RE.finditer(text):
        value = _clean_value(match.group("value"))
        unit = _normalize_unit(match.group("unit"))
        quote = _shortest_surrounding_snippet(text, match.start(), match.end())
        snippets.append(
            UnitSnippet(
                value=value,
                unit=unit,
                quote=quote,
                location=_document_location(document, _line_number(text, match.start())),
                parameter_name=_parameter_name(unit, quote),
            )
        )
    return snippets


def _parameter_name(unit: str, quote: str) -> str:
    text = quote.lower()
    if "frequency" in text or "频率" in text:
        return "stimulation_frequency"
    if "pulse width" in text or "pulse-width" in text or "脉宽" in text:
        return "pulse_width"
    if "impedance" in text or "resistance" in text or "阻抗" in text:
        return "impedance"
    if "spacing" in text or "distance" in text or "间距" in text:
        return "electrode_spacing"
    if "amplitude" in text or "current" in text or "电流" in text:
        return "stimulation_amplitude"
    if "voltage" in text or "电压" in text:
        return "voltage"
    if unit in {"uC/cm2", "μC/cm²"}:
        return "charge_density"
    return f"measurement_{unit.lower().replace('/', '_').replace('²', '2')}"


def _product_name(source: SourceRecord, document: ParsedDocument) -> str:
    title = (document.title or source.title).strip()
    lower_title = title.lower()
    for marker in [
        " product manual",
        " manual",
        " 产品手册",
        " public product comparison page",
        " comparison page",
        " 510(k) summary",
    ]:
        marker_index = lower_title.find(marker)
        if marker_index >= 0:
            title = title[:marker_index]
            break
    return title.strip(" :-") or source.title


def _shortest_surrounding_snippet(text: str, start: int, end: int) -> str:
    left = max((match.end() for match in BOUNDARY_RE.finditer(text, 0, start)), default=0)
    right_match = BOUNDARY_RE.search(text, end)
    right = right_match.start() if right_match else len(text)
    snippet = " ".join(text[left:right].split())
    if len(snippet) <= SNIPPET_LIMIT:
        return snippet

    window_start = max(start - (SNIPPET_LIMIT // 2), 0)
    window_end = min(end + (SNIPPET_LIMIT // 2), len(text))
    return " ".join(text[window_start:window_end].split())


def _document_location(document: ParsedDocument, line_number: int) -> str:
    page = document.metadata.get("page") or document.metadata.get("page_number")
    if page:
        return f"page {page}"
    return f"text line {line_number}"


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _gap_quote(context: ExtractionContext) -> str:
    text = context.document.text.strip()
    if text:
        return _shortest_surrounding_snippet(text, 0, min(len(text), SNIPPET_LIMIT))
    return context.document.title or context.source.title


def _evidence_metadata(context: ExtractionContext, source_type: SourceType, rule: str) -> dict[str, str | bool]:
    metadata = {
        "extractor": "deterministic_mvp",
        "rule": rule,
        "source_type": source_type.value,
    }
    privacy = context.source.metadata.get("privacy") or context.document.metadata.get("privacy")
    if privacy:
        metadata["privacy"] = privacy
    if source_type in {SourceType.USER_UPLOADED_PRIVATE, SourceType.INTERNAL_PRIVATE}:
        metadata["privacy"] = metadata.get("privacy", "local_only")
        metadata["local_only"] = True
    return metadata


def _has_source_gap_seed(source: SourceRecord) -> bool:
    return bool(source.title.strip() or source.publisher or source.url or source.local_path or source.metadata)


def _has_clinical_keywords(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ["clinical", "trial", "outcome", "follow-up", "患者", "临床"])


def _clean_value(value: str) -> str:
    return re.sub(r"\s*(?:–|—|~|to|至|到|-)\s*", "-", value.strip())


def _normalize_unit(unit: str) -> str:
    lower_unit = unit.lower()
    if lower_unit == "hz":
        return "Hz"
    if lower_unit == "ma":
        return "mA"
    if lower_unit == "uc/cm2":
        return "uC/cm2"
    if unit == "µs":
        return "μs"
    return unit


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"
