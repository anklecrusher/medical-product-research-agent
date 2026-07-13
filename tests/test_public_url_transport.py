from __future__ import annotations

import gzip
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from pinned_transport_stream_fixtures import (
    StreamFailure,
    incomplete_read,
    install_premature_eof,
    install_stream_failure,
)
from medical_research_agent.url_security import PublicURLFetcher, PublicURLPolicyError, ResponseSizeLimit


class ClosingByteStream(httpx.SyncByteStream):
    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self._chunks = chunks
        self.closed = False
        self.iterated = False

    def __iter__(self):
        self.iterated = True
        yield from self._chunks

    def close(self) -> None:
        self.closed = True


def test_public_fetcher_pins_validated_address_at_socket_boundary(monkeypatch) -> None:
    # Given: DNS would rebind if the hostname reached the socket layer.
    answers = iter(
        (
            [(2, 1, 6, "", ("93.184.216.34", 443))],
            [(2, 1, 6, "", ("169.254.169.254", 443))],
        )
    )
    connected: list[tuple[str, int]] = []
    monkeypatch.setattr("medical_research_agent.url_security.getaddrinfo", lambda *_args: next(answers))

    def stop_connection(address: tuple[str, int], *_args, **_kwargs):
        connected.append(address)
        raise OSError("deterministic connection stop")

    monkeypatch.setattr("medical_research_agent.public_http_transport.create_connection", stop_connection)

    # When: the owned transport reaches its connection boundary.
    with PublicURLFetcher() as fetcher, pytest.raises(httpx.ConnectError):
        fetcher.request("GET", "https://rebinding.example/resource")

    # Then: only the once-validated address reaches the socket API.
    assert connected == [("93.184.216.34", 443)]


def test_public_fetcher_preserves_tls_hostname_when_connecting_to_pinned_ip(monkeypatch) -> None:
    # Given: a public address and a TLS wrapper that records the verification hostname.
    monkeypatch.setattr(
        "medical_research_agent.url_security.getaddrinfo",
        lambda *_args: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    server_names: list[str] = []

    class SocketStub:
        def close(self) -> None:
            return None

    def wrap_socket(_socket, *, server_hostname: str):
        server_names.append(server_hostname)
        raise OSError("deterministic TLS stop")

    monkeypatch.setattr(
        "medical_research_agent.public_http_transport.create_connection",
        lambda *_args, **_kwargs: SocketStub(),
    )
    monkeypatch.setattr("medical_research_agent.public_http_transport.wrap_tls_socket", wrap_socket)

    # When: HTTPS connects to the pinned IP.
    with PublicURLFetcher() as fetcher, pytest.raises(httpx.ConnectError):
        fetcher.request("GET", "https://tls-name.example/resource")

    # Then: certificate verification still targets the original hostname.
    assert server_names == ["tls-name.example"]


def test_public_fetcher_tries_each_validated_address(monkeypatch) -> None:
    # Given: DNS returns two public addresses and the first cannot connect.
    monkeypatch.setattr(
        "medical_research_agent.url_security.getaddrinfo",
        lambda *_args: [
            (2, 1, 6, "", ("93.184.216.34", 80)),
            (2, 1, 6, "", ("1.1.1.1", 80)),
        ],
    )
    connected: list[tuple[str, int]] = []

    def stop_connection(address: tuple[str, int], *_args, **_kwargs):
        connected.append(address)
        raise OSError("deterministic connection stop")

    monkeypatch.setattr("medical_research_agent.public_http_transport.create_connection", stop_connection)

    # When: all validated connection candidates fail.
    with PublicURLFetcher() as fetcher, pytest.raises(httpx.ConnectError):
        fetcher.request("GET", "http://multi-address.example/resource")

    # Then: the transport attempts every validated address without re-resolving.
    assert connected == [("93.184.216.34", 80), ("1.1.1.1", 80)]


def test_public_fetcher_keeps_mock_transport_deterministic_and_thread_safe() -> None:
    # Given: an explicit deterministic transport used by offline tests.
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=str(request.url), request=request))

    # When: independent requests share the fetcher's owned client concurrently.
    with PublicURLFetcher(transport=transport) as fetcher, ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda suffix: fetcher.request("GET", f"https://public.example/{suffix}"), ("a", "b")))

    # Then: both complete without transport mutation or caller-pool closure.
    assert sorted(response.text for response in responses) == ["https://public.example/a", "https://public.example/b"]
    assert fetcher._client.is_closed is True


def test_public_fetcher_rejects_proxy_transport_override() -> None:
    # Given: an explicit proxy transport whose DNS/connect destination cannot be proven locally.
    transport = httpx.HTTPTransport(proxy="http://proxy.example:8080")

    # When/Then: only MockTransport is accepted as an override.
    with pytest.raises(PublicURLPolicyError, match="only MockTransport"):
        PublicURLFetcher(transport=transport)
    transport.close()


def test_public_fetcher_rejects_oversized_declared_length_before_reading() -> None:
    # Given: a response declares a body larger than the configured public limit.
    stream = ClosingByteStream((b"unused",))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-length": "65"}, stream=stream, request=request)
    )

    # When/Then: the fetcher rejects before consuming and closes the stream.
    with PublicURLFetcher(transport=transport, max_response_bytes=ResponseSizeLimit(64)) as fetcher:
        with pytest.raises(PublicURLPolicyError, match="response body exceeds"):
            fetcher.request("GET", "https://public.example/declared")
    assert stream.iterated is False
    assert stream.closed is True


def test_public_fetcher_preserves_head_content_length_without_reading_body() -> None:
    # Given: HEAD reports a resource larger than the GET response limit.
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-length": "100000000"}, request=request)
    )

    # When: the fetcher performs the metadata-only request.
    with PublicURLFetcher(transport=transport, max_response_bytes=ResponseSizeLimit(64)) as fetcher:
        response = fetcher.request("HEAD", "https://public.example/large-resource")

    # Then: no body is read and the origin's metadata remains intact.
    assert response.content == b""
    assert response.headers["content-length"] == "100000000"


def test_public_fetcher_rejects_oversized_body_without_declared_length() -> None:
    # Given: a chunked/no-length response crosses the configured limit while streaming.
    stream = ClosingByteStream((b"a" * 40, b"b" * 25))
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=stream, request=request))

    # When/Then: decoded-byte counting rejects and closes the stream.
    with PublicURLFetcher(transport=transport, max_response_bytes=ResponseSizeLimit(64)) as fetcher:
        with pytest.raises(PublicURLPolicyError, match="response body exceeds"):
            fetcher.request("GET", "https://public.example/chunked")
    assert stream.closed is True


def test_public_fetcher_rejects_compressed_decoded_expansion() -> None:
    # Given: a small gzip payload expands beyond the configured public limit.
    compressed = gzip.compress(b"a" * 65)
    assert len(compressed) < 64
    stream = ClosingByteStream((compressed,))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-encoding": "gzip", "content-length": str(len(compressed))},
            stream=stream,
            request=request,
        )
    )

    # When/Then: the limit applies after decoding and the stream is closed.
    with PublicURLFetcher(transport=transport, max_response_bytes=ResponseSizeLimit(64)) as fetcher:
        with pytest.raises(PublicURLPolicyError, match="response body exceeds"):
            fetcher.request("GET", "https://public.example/compressed")
    assert stream.closed is True


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        (incomplete_read(), httpx.RemoteProtocolError),
        (OSError("socket read failed"), httpx.ReadError),
    ],
)
def test_pinned_transport_translates_stream_failure_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
    failure: StreamFailure,
    expected_error: type[httpx.HTTPError],
) -> None:
    # Given: the validated origin starts a response, then fails while its body is read.
    responses, connections = install_stream_failure(monkeypatch, failure)

    # When: the production pinned transport is consumed by its owning fetcher.
    with PublicURLFetcher() as fetcher, pytest.raises(expected_error) as caught:
        fetcher.request("GET", "http://stream-failure.example/document")

    # Then: callers receive an HTTPX error bound to the request and all resources close.
    assert str(caught.value.request.url) == "http://stream-failure.example/document"
    assert responses and all(response.closed for response in responses)
    assert connections and all(connection.closed for connection in connections)


def test_pinned_transport_rejects_silent_eof_before_declared_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the origin declares 100 raw bytes but silently ends after a partial chunk.
    responses, connections = install_premature_eof(monkeypatch)

    # When: the production pinned stream reaches an empty read without an exception.
    with PublicURLFetcher() as fetcher, pytest.raises(httpx.RemoteProtocolError, match="incomplete response body") as caught:
        fetcher.request("GET", "http://silent-eof.example/document")

    # Then: truncation is a request-bound protocol failure and resources are closed.
    assert str(caught.value.request.url) == "http://silent-eof.example/document"
    assert responses and all(response.closed for response in responses)
    assert connections and all(connection.closed for connection in connections)
