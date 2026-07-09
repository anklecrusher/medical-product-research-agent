"""openFDA regulatory source connectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from medical_research_agent.connectors.base import (
    ConnectorError,
    ConnectorErrorKind,
    SearchRequest,
    SourceConnector,
    connector_error_from_http_status,
)
from medical_research_agent.connectors.query_sanitizer import product_codes_from_request, sanitized_api_query
from medical_research_agent.schemas import SourceRecord, SourceType


class OpenFDA510kConnector(SourceConnector):
    """Search FDA device 510(k) clearances through openFDA."""

    name = "openfda_510k"
    endpoint = "https://api.fda.gov/device/510k.json"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params = {
            "search": _openfda_search_query(request),
            "limit": str(request.limit),
        }
        try:
            response = self._client.get(self.endpoint, params=params)
            response.raise_for_status()
            results = response.json().get("results", [])
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc

        return [self._record_to_source(item, request) for item in results]

    def _record_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        k_number = item.get("k_number")
        applicant = item.get("applicant")
        device_name = item.get("device_name") or "FDA 510(k) device clearance"
        title = f"{device_name} ({k_number})" if k_number else device_name
        url = (
            f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k_number}"
            if k_number
            else "https://open.fda.gov/apis/device/510k/"
        )

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_REGULATORY,
            title=title,
            url=url,
            publisher="FDA openFDA",
            authors=[applicant] if applicant else [],
            published_at=_parse_fda_date(item.get("decision_date")),
            search_query=request.query,
            credibility_note="FDA 510(k) clearance metadata from openFDA.",
            metadata={
                "connector": self.name,
                "k_number": k_number,
                "applicant": applicant,
                "decision_date": item.get("decision_date"),
                "decision_description": item.get("decision_description"),
                "product_code": item.get("product_code"),
                "advisory_committee": item.get("advisory_committee"),
                "raw": item,
            },
        )


def _openfda_search_query(request: SearchRequest) -> str:
    terms = _escape_openfda_value(sanitized_api_query(request, max_terms=4))
    query_parts = [f'device_name:"{terms}"', f'applicant:"{terms}"']
    query_parts.extend(f'product_code:"{code}"' for code in product_codes_from_request(request))
    return "+".join(query_parts)


def _escape_openfda_value(value: str) -> str:
    return value.replace('"', " ").strip()


def _parse_fda_date(value: str | None) -> datetime | None:
    if not value or len(value) != 8:
        return None
    try:
        return datetime(int(value[:4]), int(value[4:6]), int(value[6:8]), tzinfo=timezone.utc)
    except ValueError:
        return None
