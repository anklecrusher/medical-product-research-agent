"""Item-level free-access verification for final citation links."""

from __future__ import annotations

from typing import Final
from urllib.parse import urlparse

import httpx

from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.schemas import DocumentFormat, SourceRecord
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus
from medical_research_agent.url_security import (
    PublicURLFetcherOwner,
    PublicURLPolicyError,
    request_public_url,
    validate_public_http_url,
)


_HTML_TYPES: Final = ("text/html", "application/xhtml+xml")
_PDF_TYPES: Final = ("application/pdf", "application/x-pdf")
_LOGIN_MARKERS: Final = (
    "log in",
    "login",
    "sign in",
    "sign-in",
    "password",
    "authentication required",
)
_PAYWALL_MARKERS: Final = (
    "subscribe to access",
    "purchase access",
    "rent this article",
    "institutional access",
    "access through your institution",
    "paywall",
)
_MIN_HTML_TEXT_LENGTH: Final = 20


class SourceAccessVerifier(PublicURLFetcherOwner):
    """Verify whether a source URL is free enough to cite in final reports."""

    def __init__(self, *, transport: httpx.MockTransport | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(transport=transport, timeout_seconds=timeout_seconds)

    def verify(self, source: SourceRecord) -> AccessCheck:
        """Check status, redirects, markers, and parseability for one source."""

        if source.url is None:
            return _needs_review(source, "missing_url")

        url = str(source.url)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return _needs_review(source, "unsupported_scheme")
        try:
            validate_public_http_url(url)
        except PublicURLPolicyError as exc:
            return _needs_review(source, str(exc))

        try:
            head_response = request_public_url(self._fetcher, "HEAD", url)
        except PublicURLPolicyError as exc:
            return _needs_review(source, str(exc))
        except httpx.HTTPError as exc:
            return _needs_review(source, f"head_failed: {exc}")

        head_check = _check_http_failure(source, url, head_response)
        if head_check is not None:
            return head_check

        try:
            response = request_public_url(self._fetcher, "GET", url)
        except PublicURLPolicyError as exc:
            return _needs_review(source, str(exc), head_response)
        except httpx.HTTPError as exc:
            return _needs_review(source, f"get_failed: {exc}", head_response)

        failure_check = _check_http_failure(source, url, response)
        if failure_check is not None:
            return failure_check

        content_type = _content_type(response)
        if _is_pdf_response(source, response, content_type):
            return _verify_pdf(source, response, url)
        if _is_html_response(content_type):
            return _verify_html(source, response, url)
        return _needs_review(source, "unsupported_content_type", response)


def _verify_pdf(source: SourceRecord, response: httpx.Response, original_url: str) -> AccessCheck:
    try:
        with PDFParser() as parser:
            parser.parse_bytes(
                response.content,
                source=source,
                final_url=str(response.url),
                content_type=_content_type(response),
                status_code=response.status_code,
            )
    except DocumentParseError as exc:
        return AccessCheck(
            source_id=source.source_id,
            url=original_url,
            final_url=str(response.url),
            status=FreeAccessStatus.PARSER_FAILED,
            status_code=response.status_code,
            content_type=_content_type(response),
            redirected=_was_redirected(original_url, response),
            failure_reason=str(exc),
            checked_by="source_access_verifier",
        )
    return AccessCheck(
        source_id=source.source_id,
        url=original_url,
        final_url=str(response.url),
        status=FreeAccessStatus.PDF_ACCESSIBLE,
        status_code=response.status_code,
        content_type=_content_type(response),
        redirected=_was_redirected(original_url, response),
        checked_by="source_access_verifier",
    )


def _verify_html(source: SourceRecord, response: httpx.Response, original_url: str) -> AccessCheck:
    with WebPageParser() as parser:
        document = parser.parse_html(
            response.text,
            source=source,
            final_url=str(response.url),
            content_type=_content_type(response),
            status_code=response.status_code,
        )
    marker_status = _marker_status(document.text)
    if marker_status is not None:
        return AccessCheck(
            source_id=source.source_id,
            url=original_url,
            final_url=str(response.url),
            status=marker_status,
            status_code=response.status_code,
            content_type=_content_type(response),
            redirected=_was_redirected(original_url, response),
            failure_reason=marker_status.value,
            checked_by="source_access_verifier",
        )
    if len(document.text.strip()) < _MIN_HTML_TEXT_LENGTH:
        return AccessCheck(
            source_id=source.source_id,
            url=original_url,
            final_url=str(response.url),
            status=FreeAccessStatus.PARSER_FAILED,
            status_code=response.status_code,
            content_type=_content_type(response),
            redirected=_was_redirected(original_url, response),
            failure_reason="html_parser: extracted text too short",
            checked_by="source_access_verifier",
        )

    status = _html_access_status(str(response.url))
    return AccessCheck(
        source_id=source.source_id,
        url=original_url,
        final_url=str(response.url),
        status=status,
        status_code=response.status_code,
        content_type=_content_type(response),
        redirected=_was_redirected(original_url, response),
        failure_reason=None if status is not FreeAccessStatus.METADATA_ONLY else "doi_metadata_only",
        checked_by="source_access_verifier",
    )


def _check_http_failure(source: SourceRecord, original_url: str, response: httpx.Response) -> AccessCheck | None:
    status_code = response.status_code
    match status_code:  # noqa: MATCH_OK - HTTP status codes are an open integer set.
        case 401 | 407:
            status = FreeAccessStatus.LOGIN_REQUIRED
        case 403 | 451:
            status = FreeAccessStatus.BLOCKED
        case 404:
            status = FreeAccessStatus.NOT_FOUND
        case status if 400 <= status <= 599 and status != 405:
            status = FreeAccessStatus.NEEDS_REVIEW
        case _:
            return None
    return AccessCheck(
        source_id=source.source_id,
        url=original_url,
        final_url=str(response.url),
        status=status,
        status_code=status_code,
        content_type=_content_type(response),
        redirected=_was_redirected(original_url, response),
        failure_reason=f"http_{status_code}",
        checked_by="source_access_verifier",
    )


def _html_access_status(final_url: str) -> FreeAccessStatus:
    host = urlparse(final_url).netloc.casefold()
    path = urlparse(final_url).path.casefold()
    if host == "pubmed.ncbi.nlm.nih.gov":
        return FreeAccessStatus.ABSTRACT_ACCESSIBLE
    if host.endswith("ncbi.nlm.nih.gov") and "/articles/pmc" in path:
        return FreeAccessStatus.OPEN_FULL_TEXT
    if host.endswith("europepmc.org"):
        return FreeAccessStatus.OPEN_FULL_TEXT
    if host == "doi.org" or host.endswith(".doi.org"):
        return FreeAccessStatus.METADATA_ONLY
    return FreeAccessStatus.FREE_LANDING_PAGE


def _marker_status(text: str) -> FreeAccessStatus | None:
    normalized = text.casefold()
    if any(marker in normalized for marker in _LOGIN_MARKERS):
        return FreeAccessStatus.LOGIN_REQUIRED
    if any(marker in normalized for marker in _PAYWALL_MARKERS):
        return FreeAccessStatus.PAYWALLED
    return None


def _is_pdf_response(source: SourceRecord, response: httpx.Response, content_type: str | None) -> bool:
    final_path = urlparse(str(response.url)).path.casefold()
    return _content_type_matches(content_type, _PDF_TYPES) or final_path.endswith(".pdf") or source.metadata.get("document_format_hint") == DocumentFormat.PDF


def _is_html_response(content_type: str | None) -> bool:
    return content_type is None or _content_type_matches(content_type, _HTML_TYPES)


def _content_type(response: httpx.Response) -> str | None:
    value = response.headers.get("content-type")
    return value.split(";", 1)[0].strip().casefold() if value else None


def _content_type_matches(content_type: str | None, expected_types: tuple[str, ...]) -> bool:
    return content_type in expected_types


def _was_redirected(original_url: str, response: httpx.Response) -> bool:
    return str(response.url).rstrip("/") != original_url.rstrip("/")


def _needs_review(
    source: SourceRecord,
    reason: str,
    response: httpx.Response | None = None,
) -> AccessCheck:
    url = str(source.url) if source.url is not None else None
    return AccessCheck(
        source_id=source.source_id,
        url=url,
        final_url=str(response.url) if response else url,
        status=FreeAccessStatus.NEEDS_REVIEW,
        status_code=response.status_code if response else None,
        content_type=_content_type(response) if response else None,
        redirected=_was_redirected(url, response) if url and response else False,
        failure_reason=reason,
        checked_by="source_access_verifier",
    )
