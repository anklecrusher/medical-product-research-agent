from __future__ import annotations

from email.message import Message
from http.client import HTTPException, HTTPResponse, IncompleteRead
from io import BytesIO

import pytest

from medical_research_agent import public_http_transport


StreamFailure = OSError | HTTPException


class ScriptedHTTPResponse:
    status = 200
    version = 11

    def __init__(
        self,
        failure: StreamFailure | None,
        *,
        declared_length: int | None = None,
    ) -> None:
        self.headers = Message()
        self.headers["content-type"] = "text/html"
        if declared_length is not None:
            self.headers["content-length"] = str(declared_length)
        self._failure = failure
        self._read_count = 0
        self.length = declared_length
        self.chunked = False
        self.closed = False

    def read(self, _size: int) -> bytes:
        self._read_count += 1
        if self._read_count == 1:
            chunk = b"<html><main>partial"
            if self.length is not None:
                self.length -= len(chunk)
            return chunk
        if self._failure is not None:
            raise self._failure
        return b""

    def close(self) -> None:
        self.closed = True


TestHTTPResponse = ScriptedHTTPResponse | HTTPResponse


class ScriptedConnection:
    def __init__(self, response: TestHTTPResponse) -> None:
        self._response = response
        self.closed = False

    def request(self, *_args, **_kwargs) -> None:
        return None

    def getresponse(self) -> TestHTTPResponse:
        return self._response

    def close(self) -> None:
        self.closed = True


def _install_stream(
    monkeypatch: pytest.MonkeyPatch,
    failure: StreamFailure | None,
    *,
    declared_length: int | None = None,
) -> tuple[list[ScriptedHTTPResponse], list[ScriptedConnection]]:
    responses: list[ScriptedHTTPResponse] = []
    connections: list[ScriptedConnection] = []

    def connection_factory(_origin) -> ScriptedConnection:
        response = ScriptedHTTPResponse(failure, declared_length=declared_length)
        connection = ScriptedConnection(response)
        responses.append(response)
        connections.append(connection)
        return connection

    monkeypatch.setattr(public_http_transport, "_PinnedHTTPConnection", connection_factory)
    monkeypatch.setattr(
        "medical_research_agent.url_security.getaddrinfo",
        lambda *_args: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    return responses, connections


def install_stream_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure: StreamFailure,
) -> tuple[list[ScriptedHTTPResponse], list[ScriptedConnection]]:
    return _install_stream(monkeypatch, failure)


def install_premature_eof(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[HTTPResponse], list[ScriptedConnection]]:
    responses: list[HTTPResponse] = []
    connections: list[ScriptedConnection] = []

    class ResponseSocket:
        def makefile(self, _mode: str) -> BytesIO:
            return BytesIO(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html\r\n"
                b"Content-Length: 100\r\n\r\n"
                b"<html><main>partial"
            )

    def connection_factory(_origin) -> ScriptedConnection:
        response = HTTPResponse(ResponseSocket())
        response.begin()
        connection = ScriptedConnection(response)
        responses.append(response)
        connections.append(connection)
        return connection

    monkeypatch.setattr(public_http_transport, "_PinnedHTTPConnection", connection_factory)
    monkeypatch.setattr(
        "medical_research_agent.url_security.getaddrinfo",
        lambda *_args: [(2, 1, 6, "", ("93.184.216.34", 80))],
    )
    return responses, connections


def incomplete_read() -> IncompleteRead:
    return IncompleteRead(partial=b"truncated", expected=100)
