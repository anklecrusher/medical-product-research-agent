"""Safety checks for public URL fetches and redirects."""

from __future__ import annotations

from ipaddress import IPv6Address, ip_address
from socket import gaierror, getaddrinfo
from types import TracebackType
from typing import Final, NewType, Self
from urllib.parse import urljoin, urlparse

import httpx

from medical_research_agent.public_http_transport import PinnedPublicTransport


_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
_REDIRECT_STATUSES: Final[frozenset[int]] = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS: Final = 5
ResponseSizeLimit = NewType("ResponseSizeLimit", int)
DEFAULT_MAX_PUBLIC_RESPONSE_BYTES: Final = ResponseSizeLimit(10 * 1024 * 1024)


class PublicURLPolicyError(httpx.HTTPError):
    """Raised when a URL cannot be fetched as a public Internet resource."""


def validate_public_http_url(url: str, *, resolve_dns: bool = False) -> None:
    """Reject a URL whose scheme or literal host is unsafe for public fetching."""

    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or parsed.hostname is None:
        raise PublicURLPolicyError(f"unsupported URL: {url}")

    reason = _blocked_host_reason(parsed.hostname)
    if reason is not None:
        raise PublicURLPolicyError(f"blocked host: {reason}")
    if resolve_dns:
        _validate_resolved_addresses(parsed.hostname, parsed.port)


class PublicURLFetcher:
    """Own the client and transport used for policy-enforced public fetches."""

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 20.0,
        max_response_bytes: ResponseSizeLimit = DEFAULT_MAX_PUBLIC_RESPONSE_BYTES,
    ) -> None:
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise PublicURLPolicyError("only MockTransport may override the public transport")
        owned_transport = transport or PinnedPublicTransport(
            _resolve_public_addresses,
            timeout_seconds=timeout_seconds,
        )
        self._client = httpx.Client(
            transport=owned_transport,
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
        )
        self._max_response_bytes = max_response_bytes

    def request(self, method: str, url: str) -> httpx.Response:
        """Request a public URL while validating every redirect target."""

        current_url = url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            validate_public_http_url(current_url)
            response = self._request_bounded(method, current_url)
            location = response.headers.get("location")
            if response.status_code not in _REDIRECT_STATUSES or location is None:
                return response
            if redirect_count == _MAX_REDIRECTS:
                response.close()
                raise PublicURLPolicyError("redirect limit exceeded")

            next_url = urljoin(str(response.url), location)
            try:
                validate_public_http_url(next_url)
            except PublicURLPolicyError:
                response.close()
                raise
            response.close()
            current_url = next_url

        raise AssertionError("redirect loop must return or raise")

    def _request_bounded(self, method: str, url: str) -> httpx.Response:
        with self._client.stream(method, url, follow_redirects=False) as response:
            headers = response.headers.copy()
            if method.upper() == "HEAD":
                content = b""
            else:
                _reject_oversized_declared_length(response, self._max_response_bytes)
                content = _read_decoded_with_limit(response, self._max_response_bytes)
                headers.pop("content-encoding", None)
                headers["content-length"] = str(len(content))
            return httpx.Response(
                response.status_code,
                headers=headers,
                content=content,
                extensions=response.extensions,
                request=response.request,
            )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PublicURLFetcher:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class PublicURLFetcherOwner:
    """Own a policy-enforced fetcher for deterministic resource cleanup."""

    def __init__(
        self,
        *,
        transport: httpx.MockTransport | None,
        timeout_seconds: float,
    ) -> None:
        self._fetcher = PublicURLFetcher(
            transport=transport,
            timeout_seconds=timeout_seconds,
        )

    def close(self) -> None:
        self._fetcher.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def request_public_url(fetcher: PublicURLFetcher, method: str, url: str) -> httpx.Response:
    """Compatibility helper for policy-enforced public URL requests."""

    return fetcher.request(method, url)


def _reject_oversized_declared_length(
    response: httpx.Response,
    limit: ResponseSizeLimit,
) -> None:
    declared_length = response.headers.get("content-length")
    if declared_length is None:
        return
    try:
        parsed_length = int(declared_length)
    except ValueError:
        return
    if parsed_length > limit:
        raise PublicURLPolicyError("public response body exceeds configured limit")


def _read_decoded_with_limit(response: httpx.Response, limit: ResponseSizeLimit) -> bytes:
    chunks: list[bytes] = []
    total_bytes = 0
    for chunk in response.iter_bytes(chunk_size=64 * 1024):
        total_bytes += len(chunk)
        if total_bytes > limit:
            raise PublicURLPolicyError("public response body exceeds configured limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _blocked_host_reason(hostname: str) -> str | None:
    host = hostname.rstrip(".").casefold()
    if host == "localhost" or host.endswith(".localhost"):
        return "loopback"
    try:
        address = ip_address(host)
    except ValueError:
        return None

    if address.is_loopback:
        return "loopback"
    if address.is_link_local:
        return "link_local"
    if address.is_private:
        return "private"
    if address.is_reserved:
        return "reserved"
    if address.is_unspecified:
        return "unspecified"
    if address.is_multicast:
        return "multicast"
    if isinstance(address, IPv6Address) and address.is_site_local:
        return "non_global"
    if not address.is_global:
        return "non_global"
    return None


def _validate_resolved_addresses(hostname: str, port: int | None) -> None:
    _resolve_public_addresses(hostname, port)


def _resolve_public_addresses(hostname: str, port: int | None) -> tuple[str, ...]:
    try:
        resolved = getaddrinfo(hostname, port or 443)
    except gaierror as exc:
        raise PublicURLPolicyError(f"DNS resolution failed: {hostname}") from exc
    addresses: list[str] = []
    for result in resolved:
        address = result[4][0]
        reason = _blocked_host_reason(address)
        if reason is not None:
            raise PublicURLPolicyError(f"blocked host: resolved_{reason}")
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise PublicURLPolicyError(f"DNS resolution failed: {hostname}")
    return tuple(addresses)
