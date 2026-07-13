from __future__ import annotations

import httpx
import pytest

from medical_research_agent.connectors import ConnectorError, URLSourceConnector
from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_access import SourceAccessVerifier
from medical_research_agent.source_contracts import FreeAccessStatus
from medical_research_agent.url_security import PublicURLPolicyError, validate_public_http_url


def _source(url: str) -> SourceRecord:
    return SourceRecord(source_id="src_security", source_type=SourceType.PUBLIC_WEB, title="Public source", url=url)


@pytest.mark.parametrize(
    "url",
    (
        "http://127.0.0.1/admin",
        "http://10.0.0.1/admin",
        "http://100.64.0.1/shared-address-space",
        "http://169.254.169.254/latest/meta-data",
        "http://240.0.0.1/reserved",
        "http://[::1]/admin",
        "http://[fec0::1]/deprecated-site-local",
    ),
)
def test_url_connector_rejects_non_public_ip_destinations(url: str) -> None:
    with pytest.raises(ConnectorError, match="blocked host"):
        URLSourceConnector().from_url(url)


@pytest.mark.parametrize("parser_type", (WebPageParser, PDFParser))
def test_document_parser_rejects_private_destination_before_network_fetch(parser_type: type[WebPageParser] | type[PDFParser]) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text="unexpected fetch", request=request)

    parser = parser_type(transport=httpx.MockTransport(handler))

    with pytest.raises(DocumentParseError, match="blocked host"):
        parser.parse_url(_source("http://127.0.0.1/private"))

    assert requested == []


def test_web_parser_rejects_redirect_to_private_destination_before_following() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == "https://public.example/start":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"}, request=request)
        return httpx.Response(200, text="unexpected private response", request=request)

    parser = WebPageParser(transport=httpx.MockTransport(handler))

    with pytest.raises(DocumentParseError, match="blocked host"):
        parser.parse_url(_source("https://public.example/start"))

    assert requested == ["https://public.example/start"]


def test_access_verifier_rejects_redirect_to_private_destination_before_following() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == "https://public.example/start":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private"}, request=request)
        return httpx.Response(
            200,
            text="<html><main><p>unexpected private response</p></main></html>",
            headers={"content-type": "text/html"},
            request=request,
        )

    verifier = SourceAccessVerifier(transport=httpx.MockTransport(handler))

    check = verifier.verify(_source("https://public.example/start"))

    assert check.status == FreeAccessStatus.NEEDS_REVIEW
    assert check.failure_reason == "blocked host: loopback"
    assert requested == ["https://public.example/start"]


def test_url_policy_rejects_hostname_resolving_to_private_address(monkeypatch) -> None:
    def resolve_private(*_args):
        return [(2, 1, 6, "", ("169.254.169.254", 443))]

    monkeypatch.setattr("medical_research_agent.url_security.getaddrinfo", resolve_private)

    with pytest.raises(PublicURLPolicyError, match="resolved_link_local"):
        validate_public_http_url("https://metadata.attacker.example/path", resolve_dns=True)


@pytest.mark.parametrize("address", ("100.64.0.1", "fec0::1"))
def test_url_policy_rejects_hostname_resolving_to_non_global_address(monkeypatch, address: str) -> None:
    # Given: DNS returns a special-purpose address that is neither private nor loopback.
    monkeypatch.setattr(
        "medical_research_agent.url_security.getaddrinfo",
        lambda *_args: [(2, 1, 6, "", (address, 443))],
    )

    # When/Then: public URL validation rejects the non-global destination.
    with pytest.raises(PublicURLPolicyError, match="resolved_non_global"):
        validate_public_http_url("https://special-purpose.attacker.example/path", resolve_dns=True)


def test_url_policy_accepts_hostname_when_all_resolved_addresses_are_public(monkeypatch) -> None:
    def resolve_public(*_args):
        return [(2, 1, 6, "", ("93.184.216.34", 443))]

    monkeypatch.setattr("medical_research_agent.url_security.getaddrinfo", resolve_public)

    validate_public_http_url("https://public.example/path", resolve_dns=True)

