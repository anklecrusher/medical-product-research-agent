"""Bounded public connector execution for evidence-gap follow-up."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from medical_research_agent.connectors import ConnectorError, SearchRequest
from medical_research_agent.llm.privacy import PRIVATE_SOURCE_TYPES
from medical_research_agent.resource_context import managed_resource
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.workflow.state import SearchPlanItem

if TYPE_CHECKING:
    from medical_research_agent.workflow.follow_up import FollowUpAdapters


def search_follow_up_sources(
    task_id: str,
    items: list[SearchPlanItem],
    adapters: FollowUpAdapters,
    errors: list[str],
) -> list[SourceRecord]:
    """Execute only bounded public connector routes selected for follow-up items."""

    sources: list[SourceRecord] = []
    for item in items:
        if SourceType(item.source_type) in PRIVATE_SOURCE_TYPES:
            continue
        request = SearchRequest(
            query=item.query,
            limit=item.limit,
            task_id=task_id,
            metadata={
                "expanded_terms": item.expanded_terms,
                "facet": item.facet.value if item.facet else None,
                "source_type": item.source_type.value,
                "preferred_connectors": item.preferred_connectors,
                "follow_up_round": item.metadata["follow_up_round"],
                "gap_facet": item.metadata["gap_facet"].value,
                "gap_description": item.rationale,
                "bounded": True,
            },
        )
        selector = adapters.connector_selector
        connectors = selector(item) if selector is not None else (adapters.vendor_connector,)
        remaining = item.limit
        for connector in connectors:
            if remaining < 1:
                break
            bounded_request = replace(request, limit=remaining)
            try:
                with managed_resource(connector) as active_connector:
                    records = active_connector.search(bounded_request)
            except ConnectorError as exc:
                errors.append(f"{exc} [follow_up_round=1; gap_facet={request.metadata['gap_facet']}]")
                continue
            bounded_records = records[:remaining]
            _mark_records(bounded_records, item)
            sources.extend(bounded_records)
            remaining -= len(bounded_records)
    return sources


def _mark_records(records: list[SourceRecord], item: SearchPlanItem) -> None:
    for record in records:
        record.metadata.setdefault("rationale", item.rationale)
        record.metadata.setdefault("facet", item.facet.value if item.facet else None)
        record.metadata.setdefault("preferred_connectors", item.preferred_connectors)
        record.metadata.setdefault("route_priority", item.route_priority)
        record.metadata["follow_up_round"] = item.metadata["follow_up_round"]
        record.metadata["gap_facet"] = item.metadata["gap_facet"].value
        record.metadata["gap_description"] = item.rationale
        record.metadata["bounded"] = True
