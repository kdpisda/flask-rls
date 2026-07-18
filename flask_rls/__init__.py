"""flask-rls: PostgreSQL Row-Level Security for Flask and SQLAlchemy.

The Alembic operations live in :mod:`flask_rls.alembic` and are imported separately so
Alembic stays an optional dependency.
"""

from __future__ import annotations

from flask_rls.__version__ import __version__
from flask_rls.exceptions import (
    ConfigurationError,
    PolicyError,
    RLSContextImmutableError,
    RLSContextRequiredError,
    RLSError,
    TenantAccessDeniedError,
)
from flask_rls.extension import RLS
from flask_rls.policies import (
    BasePolicy,
    CustomPolicy,
    ExpressionPolicy,
    TenantPolicy,
    UserPolicy,
)
from flask_rls.registry import PolicyRegistry

__all__ = [
    "__version__",
    "RLS",
    "BasePolicy",
    "TenantPolicy",
    "UserPolicy",
    "CustomPolicy",
    "ExpressionPolicy",
    "PolicyRegistry",
    "RLSError",
    "PolicyError",
    "ConfigurationError",
    "RLSContextRequiredError",
    "RLSContextImmutableError",
    "TenantAccessDeniedError",
]
