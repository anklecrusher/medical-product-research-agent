"""Shared connector contracts for public research source discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from medical_research_agent.schemas import SourceRecord


class ConnectorError(RuntimeError):
    """Raised when a source connector cannot complete a request cleanly."""

    def __init__(self, connector_name: str, message: str) -> None:
        super().__init__(f"{connector_name}: {message}")
        self.connector_name = connector_name
        self.message = message


@dataclass(frozen=True)
class SearchRequest:
    """Normalized connector search input."""

    query: str
    limit: int = 10
    task_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("SearchRequest.query must not be empty.")
        if self.limit < 1:
            raise ValueError("SearchRequest.limit must be at least 1.")


class SourceConnector(ABC):
    """A source discovery adapter that returns schema-aligned records."""

    name: str

    @abstractmethod
    def search(self, request: SearchRequest) -> list[SourceRecord]:
        """Search a public source and return normalized source records."""
