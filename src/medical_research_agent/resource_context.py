"""Context adaptation for production resources and lightweight test doubles."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext


def managed_resource[T](resource: T) -> AbstractContextManager[T]:
    """Use a resource context when available and preserve plain adapters."""

    if isinstance(resource, AbstractContextManager):  # noqa: IF_VARIANT_OK - open adapter protocol.
        return resource
    return nullcontext(resource)
