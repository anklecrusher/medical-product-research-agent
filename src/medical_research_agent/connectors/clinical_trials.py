"""ClinicalTrials.gov regulatory and clinical study source connector."""

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
from medical_research_agent.connectors.query_sanitizer import sanitized_api_query
from medical_research_agent.schemas import SourceRecord, SourceType


class ClinicalTrialsConnector(SourceConnector):
    """Search ClinicalTrials.gov v2 studies API."""

    name = "clinicaltrials_gov"
    endpoint = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params = {
            "query.term": sanitized_api_query(request),
            "pageSize": str(request.limit),
            "format": "json",
        }
        try:
            response = self._client.get(self.endpoint, params=params)
            response.raise_for_status()
            studies = response.json().get("studies", [])
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc

        return [self._study_to_source(study, request) for study in studies]

    def _study_to_source(self, study: dict[str, Any], request: SearchRequest) -> SourceRecord:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        design = protocol.get("designModule", {})
        nct_id = identification.get("nctId")
        title = identification.get("briefTitle") or identification.get("officialTitle") or "ClinicalTrials.gov study"
        lead_sponsor = (sponsor.get("leadSponsor") or {}).get("name")

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_REGULATORY,
            title=title,
            url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "https://clinicaltrials.gov/",
            publisher="ClinicalTrials.gov",
            authors=[lead_sponsor] if lead_sponsor else [],
            published_at=_parse_iso_date(status.get("startDateStruct", {}).get("date")),
            search_query=request.query,
            credibility_note="Clinical study registry metadata from ClinicalTrials.gov.",
            metadata={
                "connector": self.name,
                "nct_id": nct_id,
                "overall_status": status.get("overallStatus"),
                "brief_summary": (protocol.get("descriptionModule") or {}).get("briefSummary"),
                "study_type": design.get("studyType"),
                "phases": design.get("phases"),
                "lead_sponsor": lead_sponsor,
            },
        )


def _parse_iso_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parts = value.split("-")
        return datetime(
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 1,
            int(parts[2]) if len(parts) > 2 else 1,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
