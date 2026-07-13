"""Shared connector contracts for public research source discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

import httpx

from medical_research_agent.schemas import SourceRecord
from medical_research_agent.http_client import HTTPClientOwner


class ConnectorErrorKind(StrEnum):
    """Connector failure classes that workflow state can audit."""

    RETRYABLE = "retryable"
    BLOCKED = "blocked"
    BAD_QUERY = "bad_query"
    NO_RESULTS = "no_results"
    PARSER_BLOCKED_OR_WAF = "parser_blocked_or_waf"


class ConnectorError(RuntimeError):
    """Raised when a source connector cannot complete a request cleanly."""

    def __init__(
        self,
        connector_name: str,
        message: str,
        *,
        kind: ConnectorErrorKind = ConnectorErrorKind.RETRYABLE,
    ) -> None:
        super().__init__(f"{connector_name}: {message}")
        self.connector_name = connector_name
        self.message = message
        self.kind = kind


class SearchRequestError(ValueError):
    """Raised when connector search input is structurally invalid."""


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Normalized connector search input."""

    query: str
    limit: int = 10
    task_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise SearchRequestError("SearchRequest.query must not be empty.")
        if self.limit < 1:
            raise SearchRequestError("SearchRequest.limit must be at least 1.")


class SourceConnector(HTTPClientOwner, ABC):
    """A source discovery adapter that returns schema-aligned records."""

    name: str

    @abstractmethod
    def search(self, request: SearchRequest) -> list[SourceRecord]:
        """Search a public source and return normalized source records."""


def json_object_response(response: httpx.Response, connector_name: str) -> dict[str, Any]:
    """Parse a connector response whose JSON root must be an object."""

    payload = response.json()
    if not isinstance(payload, dict):
        raise ConnectorError(
            connector_name,
            "invalid response: JSON root must be an object",
            kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF,
        )
    return payload


def object_value(value: Any) -> dict[str, Any]:
    """Normalize an untrusted nested JSON value to an object."""

    return value if isinstance(value, dict) else {}


def object_items(value: Any) -> list[dict[str, Any]]:
    """Keep only object entries from an untrusted JSON collection."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


_ERROR_BODY_LIMIT: Final = 160


def connector_error_from_http_status(connector_name: str, exc: httpx.HTTPStatusError) -> ConnectorError:
    """Classify non-success HTTP responses without treating them as progress."""

    response = exc.response
    status_code = response.status_code
    match status_code:  # noqa: MATCH_OK - HTTP status codes are an open integer set.
        case 400:
            kind = ConnectorErrorKind.BAD_QUERY
        case 403:
            kind = ConnectorErrorKind.BLOCKED
        case 429:
            kind = ConnectorErrorKind.RETRYABLE
        case 404:
            kind = ConnectorErrorKind.NO_RESULTS
        case 401 | 407 | 451:
            kind = ConnectorErrorKind.BLOCKED
        case status if 500 <= status <= 599:
            kind = ConnectorErrorKind.RETRYABLE
        case _:
            kind = ConnectorErrorKind.RETRYABLE
    return ConnectorError(
        connector_name,
        f"HTTP {status_code}: {_clean_error_body(response.text)}",
        kind=kind,
    )


def _clean_error_body(raw_text: str) -> str:
    cleaned = " ".join(raw_text.split())
    if not cleaned:
        return "empty response body"
    return cleaned[:_ERROR_BODY_LIMIT]
