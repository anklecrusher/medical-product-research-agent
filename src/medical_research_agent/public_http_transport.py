"""HTTPX transport that connects to a pre-resolved public address."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection, HTTPResponse
from socket import create_connection, socket
from ssl import SSLSocket, create_default_context
from typing import Final, Iterator

import httpx


AddressResolver = Callable[[str, int | None], tuple[str, ...]]
_TLS_CONTEXT: Final = create_default_context()
_HTTP_VERSION: Final = {10: b"HTTP/1.0", 11: b"HTTP/1.1"}
_READ_CHUNK_BYTES: Final = 16 * 1024


@dataclass(frozen=True, slots=True)
class _PinnedOrigin:
    hostname: str
    address: str
    port: int
    timeout_seconds: float


def wrap_tls_socket(raw_socket: socket, *, server_hostname: str) -> SSLSocket:
    """Wrap a connected socket while verifying the original URL hostname."""

    return _TLS_CONTEXT.wrap_socket(raw_socket, server_hostname=server_hostname)


class PinnedPublicTransport(httpx.BaseTransport):
    """Resolve once and connect each request directly to a validated address."""

    def __init__(self, resolver: AddressResolver, *, timeout_seconds: float) -> None:
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        hostname = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        addresses = self._resolver(hostname, port)
        last_error: OSError | None = None

        for address in addresses:
            origin = _PinnedOrigin(hostname, address, port, self._timeout_seconds)
            connection: HTTPConnection
            if request.url.scheme == "https":
                connection = _PinnedHTTPSConnection(origin)
            else:
                connection = _PinnedHTTPConnection(origin)
            transport_owns_connection = True
            try:
                connection.request(
                    request.method,
                    request.url.raw_path.decode("ascii"),
                    body=request.read(),
                    headers=dict(request.headers),
                )
                response = _to_httpx_response(request, connection.getresponse(), connection)
                transport_owns_connection = False
                return response
            except OSError as exc:
                last_error = exc
            except HTTPException as exc:
                raise httpx.ProtocolError(str(exc), request=request) from exc
            finally:
                if transport_owns_connection:
                    connection.close()

        raise httpx.ConnectError(
            f"connection failed for validated public host: {hostname}",
            request=request,
        ) from last_error


class _PinnedHTTPConnection(HTTPConnection):
    def __init__(self, origin: _PinnedOrigin) -> None:
        super().__init__(origin.hostname, origin.port, timeout=origin.timeout_seconds)
        self._address = origin.address

    def connect(self) -> None:
        self.sock = create_connection(
            (self._address, self.port),
            self.timeout,
            self.source_address,
        )


class _PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, origin: _PinnedOrigin) -> None:
        super().__init__(origin.hostname, origin.port, timeout=origin.timeout_seconds, context=_TLS_CONTEXT)
        self._address = origin.address

    def connect(self) -> None:
        raw_socket = create_connection(
            (self._address, self.port),
            self.timeout,
            self.source_address,
        )
        try:
            self.sock = wrap_tls_socket(raw_socket, server_hostname=self.host)
        except OSError:
            raw_socket.close()
            raise


class _HTTPResponseStream(httpx.SyncByteStream):
    """Stream an HTTP response while retaining ownership of its connection."""

    def __init__(
        self,
        request: httpx.Request,
        response: HTTPResponse,
        connection: HTTPConnection,
    ) -> None:
        self._request = request
        self._response = response
        self._connection = connection
        self._expected_body_bytes = None if response.chunked else response.length

    def __iter__(self) -> Iterator[bytes]:
        received_body_bytes = 0
        try:
            while True:
                chunk = self._response.read(_READ_CHUNK_BYTES)
                if not chunk:
                    if (
                        self._expected_body_bytes is not None
                        and received_body_bytes < self._expected_body_bytes
                    ):
                        self.close()
                        raise httpx.RemoteProtocolError(
                            "incomplete response body: "
                            f"received {received_body_bytes} bytes, "
                            f"expected {self._expected_body_bytes}",
                            request=self._request,
                        )
                    return
                received_body_bytes += len(chunk)
                yield chunk
        except HTTPException as exc:
            self.close()
            raise httpx.RemoteProtocolError(str(exc), request=self._request) from exc
        except OSError as exc:
            self.close()
            raise httpx.ReadError(str(exc), request=self._request) from exc

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self._connection.close()


def _to_httpx_response(
    request: httpx.Request,
    response: HTTPResponse,
    connection: HTTPConnection,
) -> httpx.Response:
    return httpx.Response(
        response.status,
        headers=list(response.headers.raw_items()),
        stream=_HTTPResponseStream(request, response, connection),
        extensions={"http_version": _HTTP_VERSION.get(response.version, b"HTTP/1.1")},
        request=request,
    )
