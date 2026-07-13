from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

import httpx
import pytest

from medical_research_agent.connectors import (
    AccessGUDIDConnector,
    ClinicalTrialsConnector,
    CrossrefConnector,
    DuckDuckGoHTMLSearchConnector,
    EuropePMCConnector,
    OpenFDA510kConnector,
    OpenAlexConnector,
    PatentsViewConnector,
    PMCFullTextConnector,
    PubMedConnector,
    SemanticScholarConnector,
)


class _HTTPClientResource(Protocol):
    _client: httpx.Client

    def close(self) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


type _ResourceFactory = Callable[[httpx.Client | None], _HTTPClientResource]


_RESOURCE_FACTORIES: tuple[_ResourceFactory, ...] = (
    lambda client: AccessGUDIDConnector(client=client),
    lambda client: ClinicalTrialsConnector(client=client),
    lambda client: CrossrefConnector(client=client),
    lambda client: DuckDuckGoHTMLSearchConnector(client=client),
    lambda client: EuropePMCConnector(client=client),
    lambda client: OpenFDA510kConnector(client=client),
    lambda client: OpenAlexConnector(client=client),
    lambda client: PatentsViewConnector(client=client),
    lambda client: PMCFullTextConnector(client=client),
    lambda client: PubMedConnector(client=client),
    lambda client: SemanticScholarConnector(client=client),
)


@pytest.mark.parametrize("factory", _RESOURCE_FACTORIES)
def test_resource_context_closes_internally_created_http_client(factory: _ResourceFactory) -> None:
    # Given: a connector, parser, or verifier that creates its own client.
    resource = factory(None)

    # When: its context exits.
    with resource:
        assert resource._client.is_closed is False

    # Then: the owned client is deterministically closed.
    assert resource._client.is_closed is True


@pytest.mark.parametrize("factory", _RESOURCE_FACTORIES)
def test_resource_context_preserves_injected_http_client(factory: _ResourceFactory) -> None:
    # Given: a caller-owned HTTP client is injected.
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request)))

    # When: the resource context exits.
    with factory(client):
        assert client.is_closed is False

    # Then: ownership remains with the caller.
    assert client.is_closed is False
    client.close()
