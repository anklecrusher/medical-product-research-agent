from __future__ import annotations

import httpx
import pytest

from medical_research_agent.connectors import ConnectorError, ConnectorErrorKind, CrossrefConnector, SearchRequest


def test_crossref_connector_skips_scalar_items_in_response_envelope() -> None:
    # Given: Crossref returns a malformed scalar in its otherwise JSON-shaped items list.
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"message": {"items": ["not-a-mapping"]}})
    )
    connector = CrossrefConnector(client=httpx.Client(transport=transport))

    # When: the connector normalizes the response.
    records = connector.search(SearchRequest(query="DBS literature", limit=1))

    # Then: the malformed record is auditable through normal zero-result behavior, not an AttributeError crash.
    assert records == []


def test_crossref_connector_rejects_non_mapping_json_root_as_parser_error() -> None:
    # Given: Crossref returns valid JSON whose root cannot contain its response envelope.
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    connector = CrossrefConnector(client=httpx.Client(transport=transport))

    # When: the connector normalizes the response.
    with pytest.raises(ConnectorError) as exc_info:
        connector.search(SearchRequest(query="DBS literature", limit=1))

    # Then: the workflow receives a recoverable parser-classified connector failure instead of an AttributeError.
    assert exc_info.value.kind is ConnectorErrorKind.PARSER_BLOCKED_OR_WAF


def test_crossref_connector_skips_scalar_author_payload() -> None:
    # Given: Crossref returns an otherwise useful item whose author field is malformed.
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "title": ["DBS electrode impedance literature"],
                            "DOI": "10.1000/dbs-author",
                            "author": "not-a-list",
                        }
                    ]
                }
            },
        )
    )
    connector = CrossrefConnector(client=httpx.Client(transport=transport))

    # When: the connector normalizes the item.
    records = connector.search(SearchRequest(query="DBS literature", limit=1))

    # Then: the record survives without inventing authors or raising an AttributeError.
    assert len(records) == 1
    assert records[0].authors == []


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("DOI", {"unexpected": "mapping"}),
        ("URL", ["https://example.test/not-a-url-scalar"]),
        ("publisher", {"unexpected": "mapping"}),
    ],
)
def test_crossref_connector_skips_mapping_rows_with_invalid_identity_fields(
    field_name: str,
    invalid_value: dict[str, str] | list[str],
) -> None:
    # Given: a mapping-shaped Crossref row has one invalid identity field.
    item = {
        "title": ["DBS electrode impedance literature"],
        "DOI": "10.1000/dbs-boundary",
        "URL": "https://doi.org/10.1000/dbs-boundary",
        "publisher": "Example Publisher",
        "author": [{"given": "Ada", "family": "Lovelace"}],
    }
    item[field_name] = invalid_value
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"message": {"items": [item]}}))
    connector = CrossrefConnector(client=httpx.Client(transport=transport))

    # When: the connector normalizes the malformed mapping row.
    records = connector.search(SearchRequest(query="DBS literature", limit=1))

    # Then: it is safely skipped instead of leaking a Pydantic validation error into the workflow.
    assert records == []
