"""AccessGUDID public device identifier connector."""

from __future__ import annotations

import re
from typing import Any, Final, Iterable

import httpx

from medical_research_agent.connectors.base import (
    ConnectorError,
    ConnectorErrorKind,
    SearchRequest,
    SourceConnector,
    connector_error_from_http_status,
    json_object_response,
    object_items,
    object_value,
)
from medical_research_agent.public_sources import PublicSourceCategory
from medical_research_agent.schemas import SourceRecord, SourceType

_DI_RE: Final = re.compile(r"\b\d{8,18}\b")


class AccessGUDIDConnector(SourceConnector):
    """Look up public AccessGUDID records by device identifier."""

    name = "accessgudid"
    lookup_url = "https://accessgudid.nlm.nih.gov/api/v3/devices/lookup.json"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for device_identifier in _device_identifiers(request):
            try:
                response = self._client.get(self.lookup_url, params={"di": device_identifier})
                response.raise_for_status()
                payload = json_object_response(response, self.name)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    continue
                raise connector_error_from_http_status(self.name, exc) from exc
            except httpx.HTTPError as exc:
                raise ConnectorError(self.name, f"network request failed: {exc}") from exc
            except ValueError as exc:
                raise ConnectorError(
                    self.name,
                    f"invalid response: {exc}",
                    kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF,
                ) from exc

            records.append(self._payload_to_source(payload, device_identifier, request))
            if len(records) >= request.limit:
                break
        return records

    def _payload_to_source(
        self,
        payload: dict[str, Any],
        device_identifier: str,
        request: SearchRequest,
    ) -> SourceRecord:
        device = object_value(object_value(payload.get("gudid")).get("device"))
        brand_name = _text(device.get("brandName")) or "AccessGUDID device record"
        company_name = _text(device.get("companyName"))
        product_codes = tuple(
            code
            for item in object_items(payload.get("productCodes"))
            for code in (_text(item.get("productCode")),)
            if code
        )

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_REGULATORY,
            title=brand_name,
            url=f"https://accessgudid.nlm.nih.gov/devices/{device_identifier}",
            publisher="AccessGUDID",
            authors=[company_name] if company_name else [],
            search_query=request.query,
            credibility_note="Public FDA/NLM AccessGUDID device identifier record.",
            metadata={
                "connector": self.name,
                "public_source_category": PublicSourceCategory.DEVICE_IDENTIFIER,
                "device_identifier": device_identifier,
                "company_name": company_name,
                "device_description": device.get("deviceDescription"),
                "public_device_record_key": device.get("publicDeviceRecordKey"),
                "product_codes": list(product_codes),
            },
        )


def _device_identifiers(request: SearchRequest) -> tuple[str, ...]:
    metadata_values = ()
    if request.metadata is not None:
        raw_value = request.metadata.get("device_identifiers")
        if isinstance(raw_value, list | tuple):
            metadata_values = tuple(str(value) for value in raw_value)
    return _unique((*metadata_values, *_DI_RE.findall(request.query)))


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
