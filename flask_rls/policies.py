"""RLS policy classes.

A policy knows how to render the ``USING`` and ``WITH CHECK`` predicates of a
``CREATE POLICY`` statement. Rendering the surrounding DDL (name, ``ON``, ``AS``, ``FOR``,
``TO``) lives in :mod:`flask_rls.sql`.

Mirrors django-rls: :class:`TenantPolicy`, :class:`UserPolicy`, :class:`CustomPolicy`, and
the "Pythonic" :class:`ExpressionPolicy` (django-rls's ``ModelPolicy`` analog).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from sqlalchemy import literal_column
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import ColumnElement

from flask_rls.exceptions import PolicyError
from flask_rls.validation import (
    DEFAULT_TENANT_GUC,
    DEFAULT_USER_GUC,
    current_setting_sql,
    validate_cast,
    validate_field_name,
    validate_guc,
    validate_operation,
    validate_roles,
)

# Operations for which each clause is valid in PostgreSQL.
_USING_OPS = frozenset({"ALL", "SELECT", "UPDATE", "DELETE"})
_CHECK_OPS = frozenset({"ALL", "INSERT", "UPDATE"})

# Default policy configuration (overridable per policy or via extension config).
DEFAULT_ROLES = "public"
DEFAULT_PERMISSIVE = True


def tenant_ref(cast: str = "text", guc: str = DEFAULT_TENANT_GUC) -> ColumnElement:
    """Return a SQLAlchemy element reading the tenant GUC, for use in :class:`ExpressionPolicy`."""
    return literal_column(current_setting_sql(guc, cast))


def user_ref(cast: str = "text", guc: str = DEFAULT_USER_GUC) -> ColumnElement:
    """Return a SQLAlchemy element reading the user GUC, for use in :class:`ExpressionPolicy`."""
    return literal_column(current_setting_sql(guc, cast))


class BasePolicy(ABC):
    """Base class for all RLS policies."""

    def __init__(
        self,
        name: str,
        *,
        operation: str = "ALL",
        permissive: bool = DEFAULT_PERMISSIVE,
        roles: str = DEFAULT_ROLES,
    ) -> None:
        self.name = name
        self.operation = validate_operation(operation)
        self.permissive = permissive
        self.roles = roles
        self._validate()

    def _validate(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise PolicyError("Policy name is required")
        validate_field_name(self.name)  # policy names share identifier rules
        validate_roles(self.roles)

    @abstractmethod
    def get_sql_expression(self) -> str:
        """Return the boolean SQL predicate for this policy."""

    def get_using_expression(self) -> str | None:
        """Return the ``USING`` predicate, or ``None`` when not valid for the operation."""
        if self.operation in _USING_OPS:
            return self.get_sql_expression()
        return None

    def get_check_expression(self) -> str | None:
        """Return the ``WITH CHECK`` predicate, or ``None`` when not valid for the operation."""
        if self.operation in _CHECK_OPS:
            return self.get_sql_expression()
        return None


class TenantPolicy(BasePolicy):
    """Isolate rows by tenant: ``<tenant_field> = current tenant GUC``."""

    def __init__(
        self,
        name: str,
        tenant_field: str,
        *,
        cast: str = "text",
        guc: str = DEFAULT_TENANT_GUC,
        **kwargs: object,
    ) -> None:
        self.tenant_field = validate_field_name(tenant_field)
        self.cast = validate_cast(cast)
        self.guc = validate_guc(guc)
        super().__init__(name, **kwargs)  # type: ignore[arg-type]

    def get_sql_expression(self) -> str:
        return f"{self.tenant_field} = {current_setting_sql(self.guc, self.cast)}"


class UserPolicy(BasePolicy):
    """Isolate rows by owning user: ``<user_field> = current user GUC``."""

    def __init__(
        self,
        name: str,
        user_field: str = "user_id",
        *,
        cast: str = "text",
        guc: str = DEFAULT_USER_GUC,
        **kwargs: object,
    ) -> None:
        self.user_field = validate_field_name(user_field)
        self.cast = validate_cast(cast)
        self.guc = validate_guc(guc)
        super().__init__(name, **kwargs)  # type: ignore[arg-type]

    def get_sql_expression(self) -> str:
        return f"{self.user_field} = {current_setting_sql(self.guc, self.cast)}"


class CustomPolicy(BasePolicy):
    """Policy with a raw SQL predicate.

    An escape hatch. The expression is checked against obvious injection/DDL payloads, but
    :class:`ExpressionPolicy` is preferred because SQLAlchemy renders identifiers and
    literals safely.
    """

    _FORBIDDEN_SQL = re.compile(
        r"(;|--|/\*|\*/|"
        r"\b(?:DROP|ALTER|CREATE|GRANT|REVOKE|TRUNCATE|COPY|INSERT|UPDATE|DELETE)\b)",
        re.IGNORECASE,
    )

    def __init__(self, name: str, expression: str, **kwargs: object) -> None:
        self.expression = expression
        super().__init__(name, **kwargs)  # type: ignore[arg-type]

    def _validate(self) -> None:
        super()._validate()
        if not self.expression or not str(self.expression).strip():
            raise PolicyError("CustomPolicy requires a non-empty expression")
        if self._FORBIDDEN_SQL.search(str(self.expression)):
            raise PolicyError(
                "CustomPolicy expression contains forbidden SQL (statement terminators, "
                "comments or DDL/DML keywords). Use ExpressionPolicy for safe composition."
            )

    def get_sql_expression(self) -> str:
        return str(self.expression).strip()


class ExpressionPolicy(BasePolicy):
    """Pythonic policy built from a SQLAlchemy Core expression.

    The SQLAlchemy analog of django-rls's ``ModelPolicy(filters=Q(...))``. Compose column
    expressions with :func:`tenant_ref` / :func:`user_ref` (exposed as ``RLS.tenant_id()`` /
    ``RLS.user_id()``); the expression is compiled to literal SQL by SQLAlchemy's own
    PostgreSQL compiler, so identifiers are quoted and literals are rendered by the dialect
    rather than by hand.
    """

    def __init__(self, name: str, expr: ColumnElement, **kwargs: object) -> None:
        if not isinstance(expr, ColumnElement):
            raise PolicyError(
                "ExpressionPolicy requires a SQLAlchemy Core expression (ColumnElement)."
            )
        self.expr = expr
        super().__init__(name, **kwargs)  # type: ignore[arg-type]

    def get_sql_expression(self) -> str:
        compiled = self.expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        return str(compiled)
