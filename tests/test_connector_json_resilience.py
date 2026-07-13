from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import httpx
import pytest

from medical_research_agent.connectors import (
    AccessGUDIDConnector,
    EuropePMCConnector,
    OpenAlexConnector,
    PatentsViewConnector,
    PMCFullTextConnector,
    PubMedConnector,
)
from medical_research_agent.connectors.base import ConnectorError, SearchRequest, SourceConnector


class _ConnectorFactory(Protocol):
    def __call__(self, *, client: httpx.Client) -> SourceConnector: ...


def _single_response_client(payload: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, headers={"content-type": "application/json"}, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "factory",
    [
        AccessGUDIDConnector,
        EuropePMCConnector,
        OpenAlexConnector,
        PatentsViewConnector,
        PMCFullTextConnector,
        PubMedConnector,
    ],
)
@pytest.mark.parametrize("payload", ["[]", '"scalar"', "1"])
def test_connector_raises_typed_error_when_json_root_is_not_an_object(
    factory: _ConnectorFactory,
    payload: str,
) -> None:
    # Given: a successful API response whose JSON root violates the connector contract.
    connector = factory(client=_single_response_client(payload))
    request = SearchRequest(
        query="00812345678901 DBS",
        limit=1,
        metadata={"device_identifiers": ["00812345678901"]},
    )

    # When / Then: the connector emits a workflow-safe typed error, not AttributeError.
    with pytest.raises(ConnectorError, match="JSON root must be an object"):
        connector.search(request)


@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (EuropePMCConnector, '{"resultList":{"result":[1,"bad",null]}}'),
        (OpenAlexConnector, '{"results":[1,"bad",null]}'),
        (PatentsViewConnector, '{"patents":[1,"bad",null]}'),
    ],
)
def test_connector_skips_non_object_collection_items(
    factory: _ConnectorFactory,
    payload: str,
) -> None:
    # Given: an otherwise valid response containing only malformed collection items.
    connector = factory(client=_single_response_client(payload))

    # When: the connector normalizes the response.
    records = connector.search(SearchRequest(query="DBS", limit=3))

    # Then: malformed items are skipped without aborting the workflow.
    assert records == []


@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (EuropePMCConnector, '{"resultList":"bad"}'),
        (OpenAlexConnector, '{"results":"bad"}'),
        (PatentsViewConnector, '{"patents":"bad"}'),
    ],
)
def test_connector_normalizes_scalar_collection_to_empty(
    factory: _ConnectorFactory,
    payload: str,
) -> None:
    # Given: a response whose result collection is a scalar.
    connector = factory(client=_single_response_client(payload))

    # When: the connector parses the collection.
    records = connector.search(SearchRequest(query="DBS", limit=3))

    # Then: no raw attribute or iteration error escapes.
    assert records == []


def test_accessgudid_normalizes_malformed_nested_fields() -> None:
    # Given: an object root with scalar device and product-code fields.
    connector = AccessGUDIDConnector(
        client=_single_response_client('{"gudid":{"device":"bad"},"productCodes":[1,"bad"]}')
    )

    # When: the record is normalized.
    records = connector.search(
        SearchRequest(
            query="00812345678901",
            limit=1,
            metadata={"device_identifiers": ["00812345678901"]},
        )
    )

    # Then: the public record remains auditable with safe fallback metadata.
    assert len(records) == 1
    assert records[0].title == "AccessGUDID device record"
    assert records[0].metadata["product_codes"] == []


def test_ncbi_connectors_skip_malformed_summary_items() -> None:
    # Given: valid search IDs followed by scalar summary records for PubMed and PMC.
    responses = iter(
        [
            '{"esearchresult":{"idlist":["1"]}}',
            '{"result":{"uids":["1"],"1":"bad"}}',
            '{"esearchresult":{"idlist":["2"]}}',
            '{"result":{"uids":["2"],"2":7}}',
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=next(responses), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    # When: both NCBI connector families fetch summaries.
    pubmed_records = PubMedConnector(client=client).search(SearchRequest(query="DBS", limit=1))
    pmc_records = PMCFullTextConnector(client=client).search(SearchRequest(query="DBS", limit=1))

    # Then: malformed summary items are skipped without raw attribute errors.
    assert pubmed_records == []
    assert pmc_records == []


def test_ncbi_connectors_normalize_malformed_nested_summary_fields() -> None:
    # Given: summary objects whose optional fields have unexpected JSON types.
    responses = iter(
        [
            '{"esearchresult":{"idlist":["1"]}}',
            '{"result":{"uids":["1"],"1":{"uid":"1","title":7,"source":3,"authors":[1],"articleids":"bad","pubdate":[]}}}',
            '{"esearchresult":{"idlist":["2"]}}',
            '{"result":{"uids":["2"],"2":{"uid":"2","title":7,"articleids":"bad","pubdate":[]}}}',
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=next(responses), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    # When: both NCBI connector families normalize the summaries.
    pubmed_records = PubMedConnector(client=client).search(SearchRequest(query="DBS", limit=1))
    pmc_records = PMCFullTextConnector(client=client).search(SearchRequest(query="DBS", limit=1))

    # Then: fallback metadata is emitted instead of raw type errors.
    assert pubmed_records[0].title == "PubMed record 1"
    assert pubmed_records[0].published_at is None
    assert pmc_records[0].title == "PMC record 2"
    assert pmc_records[0].published_at is None


def test_ncbi_connectors_normalize_out_of_range_summary_dates() -> None:
    # Given: summary objects whose optional publication dates exceed datetime ranges.
    responses = iter(
        [
            '{"esearchresult":{"idlist":["1"]}}',
            '{"result":{"uids":["1"],"1":{"uid":"1","pubdate":"999999 Jan 99"}}}',
            '{"esearchresult":{"idlist":["2"]}}',
            '{"result":{"uids":["2"],"2":{"uid":"2","pubdate":"999999 Jan"}}}',
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=next(responses), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    # When: both NCBI connector families normalize the summaries.
    pubmed_records = PubMedConnector(client=client).search(SearchRequest(query="DBS", limit=1))
    pmc_records = PMCFullTextConnector(client=client).search(SearchRequest(query="DBS", limit=1))

    # Then: malformed optional dates do not discard otherwise auditable records.
    assert pubmed_records[0].published_at is None
    assert pmc_records[0].published_at is None


@pytest.mark.parametrize(
    ("factory", "payload"),
    [
        (EuropePMCConnector, '{"resultList":{"result":[{"id":"1","title":7,"pubYear":999999}]}}'),
        (OpenAlexConnector, '{"results":[{"id":"1","display_name":7,"publication_year":999999}]}'),
    ],
)
def test_literature_connector_normalizes_invalid_optional_metadata(
    factory: _ConnectorFactory,
    payload: str,
) -> None:
    # Given: an object item with malformed title and out-of-range publication year.
    connector = factory(client=_single_response_client(payload))

    # When: the record is normalized.
    records = connector.search(SearchRequest(query="DBS", limit=1))

    # Then: the item remains auditable with no invalid publication date.
    assert len(records) == 1
    assert records[0].published_at is None
