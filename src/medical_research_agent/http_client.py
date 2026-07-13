"""Deterministic ownership for synchronous HTTP clients."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx


class HTTPClientOwner:
    """Close internally created clients while preserving injected clients."""

    def __init__(self, *, client: httpx.Client | None, timeout_seconds: float) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    def close(self) -> None:
        """Release an internally created client."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
