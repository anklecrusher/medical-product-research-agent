from __future__ import annotations

import httpx

from medical_research_agent.connectors import (
    CrossrefConnector,
    EuropePMCConnector,
    OpenAlexConnector,
    PMCFullTextConnector,
    PubMedConnector,
    SearchRequest,
)
from medical_research_agent.schemas import SourceRecord
from medical_research_agent.source_contracts import CitationEligibility, FreeAccessStatus


def _access_status(record_index: int, records: list[SourceRecord]) -> str:
    return records[record_index].metadata["access_check"]["status"]


def _is_eligible(record_index: int, records: list[SourceRecord]) -> bool:
    return bool(records[record_index].metadata["citation_eligibility"]["eligible"])


def test_pubmed_connector_marks_abstract_url_final_eligible() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "esearch.fcgi" in str(request.url):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["12345"]}})
        return httpx.Response(
            200,
            json={
                "result": {
                    "uids": ["12345"],
                    "12345": {
                        "uid": "12345",
                        "title": "DBS electrode impedance study",
                        "source": "J Neural Eng",
                        "pubdate": "2024 Jan 05",
                        "articleids": [{"idtype": "doi", "value": "10.1000/dbs"}],
                    },
                }
            },
        )

    records = PubMedConnector(client=httpx.Client(transport=httpx.MockTransport(handler))).search(
        SearchRequest(query="DBS impedance", limit=1)
    )

    assert str(records[0].url) == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    assert _access_status(0, records) == FreeAccessStatus.ABSTRACT_ACCESSIBLE
    assert _is_eligible(0, records)


def test_europe_pmc_prefers_free_full_text_url() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "resultList": {
                    "result": [
                        {
                            "id": "38300001",
                            "pmid": "38300001",
                            "pmcid": "PMC1234567",
                            "title": "Closed-loop stimulation sensing",
                            "journalTitle": "Open Journal",
                            "authorString": "Ada Lovelace, Grace Hopper",
                            "doi": "10.1000/open",
                            "isOpenAccess": "Y",
                            "fullTextUrlList": {
                                "fullTextUrl": [
                                    {
                                        "url": "https://europepmc.org/articles/PMC1234567",
                                        "documentStyle": "html",
                                    }
                                ]
                            },
                        }
                    ]
                }
            },
        )
    )

    records = EuropePMCConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="closed loop DBS", limit=1, task_id="task_open")
    )

    assert records[0].task_id == "task_open"
    assert str(records[0].url) == "https://europepmc.org/articles/PMC1234567"
    assert _access_status(0, records) == FreeAccessStatus.OPEN_FULL_TEXT
    assert _is_eligible(0, records)


def test_openalex_uses_oa_pdf_then_rejects_metadata_only_doi() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "doi": "https://doi.org/10.1000/free",
                        "display_name": "OA stimulation parameters",
                        "publication_year": 2023,
                        "authorships": [{"author": {"display_name": "Test Author"}}],
                        "open_access": {"is_oa": True, "oa_url": "notaurl"},
                        "primary_location": {"pdf_url": "https://publisher.example/free.pdf"},
                    },
                    {
                        "id": "https://openalex.org/W2",
                        "doi": "https://doi.org/10.1000/closed",
                        "display_name": "Metadata-only DOI",
                        "publication_year": 2022,
                        "authorships": [],
                        "open_access": {"is_oa": False, "oa_url": None},
                        "primary_location": {"landing_page_url": None, "pdf_url": None},
                    },
                    {
                        "id": "https://openalex.org/W3",
                        "doi": "https://doi.org/10.1000/landing",
                        "display_name": "Open publisher landing page",
                        "publication_year": 2021,
                        "authorships": [],
                        "open_access": {"is_oa": True, "oa_url": None},
                        "primary_location": {
                            "landing_page_url": "https://publisher.example/open-article",
                            "pdf_url": None,
                        },
                    },
                ]
            },
        )
    )

    records = OpenAlexConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="stimulation parameters", limit=3)
    )

    assert str(records[0].url) == "https://publisher.example/free.pdf"
    assert _access_status(0, records) == FreeAccessStatus.PDF_ACCESSIBLE
    assert _is_eligible(0, records)
    assert str(records[1].url) == "https://doi.org/10.1000/closed"
    assert _access_status(1, records) == FreeAccessStatus.METADATA_ONLY
    assert not _is_eligible(1, records)
    assert str(records[2].url) == "https://publisher.example/open-article"
    assert _access_status(2, records) == FreeAccessStatus.FREE_LANDING_PAGE
    assert _is_eligible(2, records)


def test_pmc_full_text_connector_returns_ncbi_open_full_text_link() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "esearch.fcgi" in str(request.url):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["7654321"]}})
        return httpx.Response(
            200,
            json={
                "result": {
                    "uids": ["7654321"],
                    "7654321": {
                        "uid": "7654321",
                        "title": "Open PMC neuromodulation article",
                        "fulljournalname": "PMC Journal",
                        "pubdate": "2024 Mar",
                        "articleids": [{"idtype": "pmcid", "value": "PMC7654321"}],
                    },
                }
            },
        )

    records = PMCFullTextConnector(client=httpx.Client(transport=httpx.MockTransport(handler))).search(
        SearchRequest(query="neuromodulation", limit=1)
    )

    assert str(records[0].url) == "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7654321/"
    assert _access_status(0, records) == FreeAccessStatus.OPEN_FULL_TEXT
    assert _is_eligible(0, records)


def test_crossref_remains_metadata_only_final_ineligible() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "title": ["Paywalled DOI metadata"],
                            "DOI": "10.1000/paywalled",
                            "URL": "https://doi.org/10.1000/paywalled",
                            "publisher": "Example Publisher",
                        }
                    ]
                }
            },
        )
    )

    records = CrossrefConnector(client=httpx.Client(transport=transport)).search(
        SearchRequest(query="paywalled DOI", limit=1)
    )
    access = records[0].metadata["access_check"]

    assert access["status"] == FreeAccessStatus.METADATA_ONLY
    assert not CitationEligibility.model_validate(records[0].metadata["citation_eligibility"]).eligible
