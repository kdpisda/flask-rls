"""Pure SQL generators for RLS DDL.

Each function returns a SQL string and performs no I/O, so it is usable directly, from the
:mod:`flask_rls.cli` dumper, or from the Alembic operations in :mod:`flask_rls.alembic`.
Every identifier is validated and quoted before interpolation.
"""

from __future__ import annotations

from flask_rls.policies import BasePolicy
from flask_rls.validation import quote_identifier, roles_to_sql, validate_field_name


def enable_rls(table: str) -> str:
    """``ALTER TABLE ... ENABLE ROW LEVEL SECURITY``."""
    return f"ALTER TABLE {quote_identifier(table)} ENABLE ROW LEVEL SECURITY;"


def disable_rls(table: str) -> str:
    """``ALTER TABLE ... DISABLE ROW LEVEL SECURITY``."""
    return f"ALTER TABLE {quote_identifier(table)} DISABLE ROW LEVEL SECURITY;"


def force_rls(table: str) -> str:
    """``ALTER TABLE ... FORCE ROW LEVEL SECURITY`` (also applies RLS to the table owner)."""
    return f"ALTER TABLE {quote_identifier(table)} FORCE ROW LEVEL SECURITY;"


def no_force_rls(table: str) -> str:
    """``ALTER TABLE ... NO FORCE ROW LEVEL SECURITY`` (reverse of :func:`force_rls`)."""
    return f"ALTER TABLE {quote_identifier(table)} NO FORCE ROW LEVEL SECURITY;"


def create_policy(table: str, policy: BasePolicy) -> str:
    """Render a ``CREATE POLICY`` statement for ``policy`` on ``table``.

    ``USING`` and ``WITH CHECK`` clauses are emitted only for the operations where
    PostgreSQL accepts them (see :class:`~flask_rls.policies.BasePolicy`).
    """
    name = quote_identifier(policy.name)
    parts = [
        f"CREATE POLICY {name} ON {quote_identifier(table)}",
        "AS PERMISSIVE" if policy.permissive else "AS RESTRICTIVE",
        f"FOR {policy.operation}",
        f"TO {roles_to_sql(policy.roles)}",
    ]
    using = policy.get_using_expression()
    if using is not None:
        parts.append(f"USING ({using})")
    check = policy.get_check_expression()
    if check is not None:
        parts.append(f"WITH CHECK ({check})")
    return " ".join(parts) + ";"


def drop_policy(table: str, policy_name: str) -> str:
    """``DROP POLICY IF EXISTS ...``."""
    validate_field_name(policy_name)
    return f'DROP POLICY IF EXISTS "{policy_name}" ON {quote_identifier(table)};'
