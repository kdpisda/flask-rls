"""Per-transaction RLS context: contextvars, scope managers, and resolution.

Context is resolved fresh at each transaction begin. ``bypass`` and ``override`` are held
in :class:`~contextvars.ContextVar` so they are correct under threads, greenlets, and
asyncio without leaking across requests.

Resolution precedence (highest first): ``bypass`` → ``override`` → registered providers.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

# A provider is a zero-argument callable returning a ``{key: value}`` mapping (or ``{}``).
Provider = Callable[[], dict[str, Any]]

_override: ContextVar[dict[str, Any] | None] = ContextVar(
    "flask_rls_override", default=None
)
_bypass: ContextVar[bool] = ContextVar("flask_rls_bypass", default=False)


def is_bypass() -> bool:
    """Return whether a :func:`bypass_scope` is currently active."""
    return _bypass.get()


def get_override() -> dict[str, Any] | None:
    """Return the current override mapping, if any."""
    return _override.get()


@contextmanager
def override_scope(**keys: Any) -> Iterator[None]:
    """Force context keys for the duration of the block (privileged identity switch).

    Nesting accumulates: inner keys are merged over outer ones.
    """
    current = _override.get() or {}
    token = _override.set({**current, **keys})
    try:
        yield
    finally:
        _override.reset(token)


@contextmanager
def bypass_scope() -> Iterator[None]:
    """Emit no RLS context for the duration of the block.

    On RLS-protected tables this is fail-closed (no context → zero rows). It is meant for
    work on non-RLS tables and for isolation tests, not for cross-tenant access.
    """
    token = _bypass.set(True)
    try:
        yield
    finally:
        _bypass.reset(token)


def resolve_context(providers: list[Provider]) -> tuple[dict[str, str], bool]:
    """Resolve the active context to ``(values, is_bypass)``.

    Values are stringified because GUCs are text. Empty/``None`` values are dropped so they
    read as "unset" (fail-closed) rather than as an empty string.
    """
    if _bypass.get():
        return {}, True

    resolved: dict[str, str] = {}
    for provider in providers:
        data = provider() or {}
        for key, value in data.items():
            if value is not None and value != "":
                resolved[key] = str(value)

    override = _override.get()
    if override:
        for key, value in override.items():
            if value is not None and value != "":
                resolved[key] = str(value)

    return resolved, False
