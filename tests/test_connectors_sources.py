from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from medical_research_agent.connectors import (
    ClinicalTrialsConnector,
    ConnectorError,
    CrossrefConnector,
    DuckDuckGoHTMLSearchConnector,
    OpenFDA510kConnector,
    PubMedConnector,
    SearchRequest,
    SemanticScholarConnector,
    URLSourceConnector,
)
from medical_research_agent.io import write_model_json
from medical_research_agent.schemas import DocumentFormat, SourceType


def test_pubmed_connector_returns_source_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "esearch.fcgi" in str(request.url):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["123"]}})
        return httpx.Response(
            200,
            json={
                "result": {
                    "uids": ["123"],
                    "123": {
                        "uid": "123",
                        "title": "DBS electrode impedance study",
                        "source": "J Neural Eng",
                        "pubdate": "2024 Jan 05",
                        "authors": [{"name": "Ada Lovelace"}],
                        "articleids": [{"idtype": "doi", "value": "10.1000/example"}],
                    },
                }
            },
        )

    connector = PubMedConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    records = connector.search(SearchRequest(query="DBS impedance", limit=1, task_id="task_1"))

    assert len(records) == 1
    assert records[0].task_id == "task_1"
    assert records[0].source_type == SourceType.PUBLIC_LITERATURE
    assert str(records[0].url) == "https://pubmed.ncbi.nlm.nih.gov/123/"
    assert records[0].metadata["pmid"] == "123"
    assert records[0].metadata["doi"] == "10.1000/example"


@pytest.mark.parametrize(
    ("date_fields", "expected_published_at"),
    [
        ({"issued": {"date-parts": [[2023, 8]]}}, datetime(2023, 8, 1, tzinfo=timezone.utc)),
        ({"issued": {"date-parts": [[None]]}}, None),
        (
            {
                "published-print": {"date-parts": [[None]]},
                "issued": {"date-parts": [[2023, 8]]},
            },
            datetime(2023, 8, 1, tzinfo=timezone.utc),
        ),
        ({"published-print": "not-a-date-object", "issued": {"date-parts": [[2023, 8]]}}, datetime(2023, 8, 1, tzinfo=timezone.utc)),
        ({"issued": "not-a-date-object"}, None),
    ],
    ids=("valid_issued_date", "nested_null_date", "invalid_preferred_date_falls_back", "scalar_preferred_date_falls_back", "scalar_only_date"),
)
def test_crossref_connector_normalizes_publication_date_candidates(
    date_fields,
    expected_published_at: datetime | None,
) -> None:
    item = {
        "title": ["Spinal cord stimulation parameters"],
        "DOI": "10.1000/scs",
        "URL": "https://doi.org/10.1000/scs",
        "publisher": "Example Publisher",
        "container-title": ["Neuromodulation"],
        "author": [{"given": "Grace", "family": "Hopper"}],
        **date_fields,
    }
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"message": {"items": [item]}},
        )
    )

    records = CrossrefConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="SCS parameters", limit=1)
    )

    assert len(records) == 1
    assert records[0].title == "Spinal cord stimulation parameters"
    assert records[0].authors == ["Grace Hopper"]
    assert records[0].metadata["doi"] == "10.1000/scs"
    assert records[0].published_at == expected_published_at


def test_semantic_scholar_connector_supports_optional_key() -> None:
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers["x-api-key"] = request.headers.get("x-api-key")
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "paperId": "abc",
                        "title": "Closed-loop DBS sensing",
                        "url": "https://www.semanticscholar.org/paper/abc",
                        "venue": "IEEE",
                        "year": 2022,
                        "publicationDate": "2022-02-03",
                        "authors": [{"name": "Test Author"}],
                        "externalIds": {"DOI": "10.1000/dbs", "PubMed": "456"},
                        "citationCount": 12,
                    }
                ]
            },
        )

    connector = SemanticScholarConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        api_key="secret",
    )
    records = connector.search(SearchRequest(query="closed loop DBS", limit=1))

    assert seen_headers["x-api-key"] == "secret"
    assert records[0].metadata["paper_id"] == "abc"
    assert records[0].metadata["pubmed_id"] == "456"


def test_connector_network_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    connector = CrossrefConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(ConnectorError, match="crossref: network request failed"):
        connector.search(SearchRequest(query="DBS", limit=1))


def test_duckduckgo_html_connector_returns_vendor_sources() -> None:
    html = """
    <html><body>
      <a class="result__a" href="/l/?uddg=https%3A%2F%2Fvendor.example%2Fmanual.pdf">Vendor Manual PDF</a>
      <a class="result__a" href="https://vendor.example/specs">Vendor Specs</a>
    </body></html>
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    connector = DuckDuckGoHTMLSearchConnector(
        client=httpx.Client(transport=transport),
        source_type=SourceType.VENDOR_PUBLIC_DOC,
    )

    records = connector.search(SearchRequest(query="DBS product manual", limit=2))

    assert len(records) == 2
    assert records[0].source_type == SourceType.VENDOR_PUBLIC_DOC
    assert records[0].title == "Vendor Manual PDF"
    assert records[0].metadata["document_format_hint"] == DocumentFormat.PDF


def test_openfda_510k_connector_returns_regulatory_sources() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        "k_number": "K123456",
                        "device_name": "Implantable pulse generator",
                        "applicant": "Example Medical",
                        "decision_date": "20240501",
                        "decision_description": "Substantially Equivalent",
                        "product_code": "MHY",
                    }
                ]
            },
        )
    )

    records = OpenFDA510kConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="implantable pulse generator", limit=1)
    )

    assert len(records) == 1
    assert records[0].source_type == SourceType.PUBLIC_REGULATORY
    assert records[0].metadata["k_number"] == "K123456"
    assert records[0].authors == ["Example Medical"]


def test_clinical_trials_connector_returns_regulatory_sources() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "studies": [
                    {
                        "protocolSection": {
                            "identificationModule": {
                                "nctId": "NCT123",
                                "briefTitle": "Study of DBS Device",
                            },
                            "statusModule": {
                                "overallStatus": "RECRUITING",
                                "startDateStruct": {"date": "2024-01"},
                            },
                            "sponsorCollaboratorsModule": {
                                "leadSponsor": {"name": "Example Sponsor"},
                            },
                            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["NA"]},
                            "descriptionModule": {"briefSummary": "A device study."},
                        }
                    }
                ]
            },
        )
    )

    records = ClinicalTrialsConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="DBS device", limit=1)
    )

    assert len(records) == 1
    assert str(records[0].url) == "https://clinicaltrials.gov/study/NCT123"
    assert records[0].metadata["overall_status"] == "RECRUITING"
    assert records[0].metadata["lead_sponsor"] == "Example Sponsor"


def test_url_source_connector_marks_pdf_hint() -> None:
    source = URLSourceConnector().from_url("https://example.com/manual.pdf", title="Manual")

    assert source.title == "Manual"
    assert source.source_type == SourceType.PUBLIC_WEB
    assert source.metadata["document_format_hint"] == DocumentFormat.PDF


def test_write_model_json_saves_source_metadata(tmp_path) -> None:
    source = URLSourceConnector().from_url("https://example.com/manual.pdf", title="Manual")
    output_path = write_model_json(tmp_path / "sources.json", [source])

    assert output_path.exists()
    assert "manual.pdf" in output_path.read_text(encoding="utf-8")
