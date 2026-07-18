"""Exception hierarchy for flask-rls.

Names mirror django-rls for sibling consistency. django-rls's ``BackendError`` is
intentionally omitted — it is specific to Django's DB backend and has no flask-rls analog.
"""

from __future__ import annotations


class RLSError(Exception):
    """Base exception for all flask-rls errors."""


class PolicyError(RLSError):
    """Raised for invalid policy configuration (bad name, operation, role, or field)."""


class ConfigurationError(RLSError):
    """Raised for invalid or missing extension configuration."""


class RLSContextRequiredError(RLSError):
    """Raised when identity context is required (``RLS_REQUIRE_CONTEXT``) but missing."""


class RLSContextImmutableError(RLSError):
    """Raised when an already-established identity key is changed without ``override()``."""


class TenantAccessDeniedError(RLSError):
    """Raised when tenant context fails membership validation (reserved for a later milestone)."""
