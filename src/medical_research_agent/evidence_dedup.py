"""Evidence deduplication and parameter conflict handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ProductSpec,
)


@dataclass(frozen=True, slots=True)
class EvidenceDeduplicationResult:
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]
    duplicate_count: int
    conflict_count: int


@dataclass(frozen=True, slots=True)
class EvidenceDedupKey:
    source_id: str
    document_id: str
    kind: str
    product_name: str
    parameter_name: str
    value: str
    unit: str
    statement: str


@dataclass(frozen=True, slots=True)
class ParameterConflictKey:
    product_name: str
    parameter_name: str
    unit: str


@dataclass(frozen=True, slots=True)
class ProductSpecDedupKey:
    product_name: str
    parameter_name: str
    value: str
    unit: str


@dataclass(frozen=True, slots=True)
class ParameterGroup:
    values: set[str]
    source_ids: set[str]


def deduplicate_evidence_items(
    evidence: list[EvidenceItem],
    product_specs: list[ProductSpec],
) -> EvidenceDeduplicationResult:
    """Collapse exact duplicate evidence while preserving cross-source conflicts."""

    deduped_evidence: list[EvidenceItem] = []
    seen_evidence: dict[EvidenceDedupKey, EvidenceItem] = {}
    canonical_evidence_ids: dict[str, str] = {}
    duplicate_count = 0

    for item in evidence:
        key = _evidence_dedup_key(item)
        existing = seen_evidence.get(key)
        if existing is None:
            seen_evidence[key] = item
            canonical_evidence_ids[item.evidence_id] = item.evidence_id
            deduped_evidence.append(item)
            continue
        duplicate_count += 1
        canonical_evidence_ids[item.evidence_id] = existing.evidence_id

    conflict_keys = _conflict_keys(deduped_evidence)
    final_evidence = [_mark_conflicting(item) if _has_conflict(item, conflict_keys) else item for item in deduped_evidence]
    final_specs = _deduplicate_product_specs(product_specs, canonical_evidence_ids, conflict_keys)

    return EvidenceDeduplicationResult(
        evidence=final_evidence,
        product_specs=final_specs,
        duplicate_count=duplicate_count,
        conflict_count=len(conflict_keys),
    )


def _evidence_dedup_key(item: EvidenceItem) -> EvidenceDedupKey:
    statement = "" if _is_parameter_evidence(item) else _normalize_text(item.statement)
    return EvidenceDedupKey(
        source_id=item.source_id,
        document_id=item.document_id or "",
        kind=str(item.kind),
        product_name=_normalize_text(item.product_name),
        parameter_name=_normalize_text(item.parameter_name),
        value=_normalize_value(item.value),
        unit=_normalize_text(item.unit),
        statement=statement,
    )


def _conflict_keys(evidence: list[EvidenceItem]) -> set[ParameterConflictKey]:
    groups: dict[ParameterConflictKey, ParameterGroup] = {}
    for item in evidence:
        key = _parameter_conflict_key(item)
        if key is None:
            continue
        group = groups.setdefault(key, ParameterGroup(values=set(), source_ids=set()))
        group.values.add(_normalize_value(item.value))
        group.source_ids.add(item.source_id)

    return {key for key, group in groups.items() if len(group.values) > 1 and len(group.source_ids) > 1}


def _deduplicate_product_specs(
    product_specs: list[ProductSpec],
    canonical_evidence_ids: dict[str, str],
    conflict_keys: set[ParameterConflictKey],
) -> list[ProductSpec]:
    merged_specs: dict[ProductSpecDedupKey, ProductSpec] = {}
    spec_order: list[ProductSpecDedupKey] = []

    for spec in product_specs:
        normalized = _normalize_spec(spec, canonical_evidence_ids, conflict_keys)
        key = ProductSpecDedupKey(
            product_name=_normalize_text(normalized.product_name),
            parameter_name=_normalize_text(normalized.parameter_name),
            value=_normalize_value(normalized.value),
            unit=_normalize_text(normalized.unit),
        )
        existing = merged_specs.get(key)
        if existing is None:
            merged_specs[key] = normalized
            spec_order.append(key)
            continue
        merged_specs[key] = _merge_specs(existing, normalized)

    return [merged_specs[key] for key in spec_order]


def _normalize_spec(
    spec: ProductSpec,
    canonical_evidence_ids: dict[str, str],
    conflict_keys: set[ParameterConflictKey],
) -> ProductSpec:
    evidence_ids = _dedupe_ids([canonical_evidence_ids.get(evidence_id, evidence_id) for evidence_id in spec.evidence_ids])
    status = EvidenceStatus.CONFLICTING if _spec_conflict_key(spec) in conflict_keys else spec.status
    return spec.model_copy(
        update={
            "source_ids": _dedupe_ids(spec.source_ids),
            "evidence_ids": evidence_ids,
            "status": status,
        }
    )


def _merge_specs(existing: ProductSpec, incoming: ProductSpec) -> ProductSpec:
    status = EvidenceStatus.CONFLICTING if _is_conflicting_status(incoming.status) else existing.status
    return existing.model_copy(
        update={
            "source_ids": _dedupe_ids([*existing.source_ids, *incoming.source_ids]),
            "evidence_ids": _dedupe_ids([*existing.evidence_ids, *incoming.evidence_ids]),
            "status": status,
        }
    )


def _parameter_conflict_key(item: EvidenceItem) -> ParameterConflictKey | None:
    if item.parameter_name is None or item.value is None:
        return None
    return ParameterConflictKey(
        product_name=_normalize_text(item.product_name),
        parameter_name=_normalize_text(item.parameter_name),
        unit=_normalize_text(item.unit),
    )


def _spec_conflict_key(spec: ProductSpec) -> ParameterConflictKey:
    return ParameterConflictKey(
        product_name=_normalize_text(spec.product_name),
        parameter_name=_normalize_text(spec.parameter_name),
        unit=_normalize_text(spec.unit),
    )


def _has_conflict(item: EvidenceItem, conflict_keys: set[ParameterConflictKey]) -> bool:
    key = _parameter_conflict_key(item)
    return key in conflict_keys


def _mark_conflicting(item: EvidenceItem) -> EvidenceItem:
    return item.model_copy(update={"status": EvidenceStatus.CONFLICTING})


def _is_parameter_evidence(item: EvidenceItem) -> bool:
    match EvidenceKind(item.kind):
        case EvidenceKind.PRODUCT_PARAMETER:
            return item.parameter_name is not None and item.value is not None
        case (
            EvidenceKind.CLINICAL_FINDING
            | EvidenceKind.REGULATORY_FINDING
            | EvidenceKind.MARKET_FINDING
            | EvidenceKind.ENGINEERING_NOTE
            | EvidenceKind.OTHER
        ):
            return False
        case unreachable:
            assert_never(unreachable)


def _is_conflicting_status(status: EvidenceStatus | str) -> bool:
    match EvidenceStatus(status):
        case EvidenceStatus.CONFLICTING:
            return True
        case EvidenceStatus.EXTRACTED | EvidenceStatus.VERIFIED | EvidenceStatus.NEEDS_REVIEW:
            return False
        case unreachable:
            assert_never(unreachable)


def _normalize_value(value: str | float | int | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def _dedupe_ids(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
