"""Identifier validation and SQL fragment builders.

RLS policy DDL (``CREATE POLICY``) cannot be parameterized — the whole predicate must be
literal SQL. Every identifier that reaches generated DDL (table, field, role, GUC name,
cast type) is therefore validated here against a strict pattern before interpolation, even
though it comes from trusted config. A malformed value fails loudly rather than reaching
the database.
"""

from __future__ import annotations

import re

from flask_rls.exceptions import PolicyError

#: Default GUC (PostgreSQL custom setting) names read by generated policies.
DEFAULT_GUC_PREFIX = "rls."
DEFAULT_TENANT_GUC = "rls.tenant_id"
DEFAULT_USER_GUC = "rls.user_id"

#: Valid SQL operations for a policy's ``FOR`` clause.
OPERATIONS = frozenset({"ALL", "SELECT", "INSERT", "UPDATE", "DELETE"})

# A bare PostgreSQL identifier: letter/underscore start, then letters/digits/underscores.
_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# A GUC name: two dot-separated identifiers, e.g. ``rls.tenant_id``.
_GUC = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$")

# A cast target type: identifier chars plus spaces, parens, brackets and digits
# (covers ``uuid``, ``bigint``, ``double precision``, ``varchar(50)``, ``int[]``).
# Deliberately excludes quotes, semicolons and comment markers.
_CAST = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_ ()\[\]]*$")


def validate_identifier(name: str, *, kind: str = "identifier") -> str:
    """Validate a bare SQL identifier and return it unchanged."""
    if not isinstance(name, str) or not name:
        raise PolicyError(f"{kind} is required and must be a non-empty string")
    if not _IDENTIFIER.match(name):
        raise PolicyError(
            f"Invalid {kind} {name!r}. Must contain only letters, digits and "
            "underscores, and must not start with a digit."
        )
    return name


def validate_field_name(name: str) -> str:
    """Validate a column/field name used in a policy predicate."""
    return validate_identifier(name, kind="field name")


def validate_table_name(table: str) -> str:
    """Validate a (optionally schema-qualified) table name and return it unchanged."""
    if not isinstance(table, str) or not table:
        raise PolicyError("table name is required and must be a non-empty string")
    parts = table.split(".")
    if len(parts) > 2:
        raise PolicyError(
            f"Invalid table name {table!r}. Use 'table' or 'schema.table'."
        )
    for part in parts:
        validate_identifier(part, kind="table name")
    return table


def quote_identifier(name: str) -> str:
    """Double-quote a validated (optionally schema-qualified) identifier for DDL."""
    validate_table_name(name)
    return ".".join(f'"{part}"' for part in name.split("."))


def validate_operation(operation: str) -> str:
    """Validate a policy operation (``FOR`` clause) and return it uppercased."""
    if not isinstance(operation, str):
        raise PolicyError("operation must be a string")
    upper = operation.upper()
    if upper not in OPERATIONS:
        raise PolicyError(
            f"Invalid operation {operation!r}. Must be one of {sorted(OPERATIONS)}."
        )
    return upper


def validate_roles(roles: str) -> str:
    """Validate the ``TO`` clause target roles.

    ``roles`` is interpolated into an identifier position that cannot be parameterized, so
    it must be ``PUBLIC`` or a comma-separated list of PostgreSQL identifiers.
    """
    if not isinstance(roles, str) or not roles.strip():
        raise PolicyError("roles must be a non-empty string")
    for token in roles.split(","):
        name = token.strip()
        if name.upper() == "PUBLIC":
            continue
        if not _IDENTIFIER.match(name):
            raise PolicyError(
                f"Invalid role name {name!r} in roles={roles!r}. Roles must be 'PUBLIC' "
                "or a comma-separated list of PostgreSQL identifiers."
            )
    return roles


def roles_to_sql(roles: str) -> str:
    """Render a validated ``roles`` string for the ``TO`` clause."""
    validate_roles(roles)
    rendered = []
    for token in roles.split(","):
        name = token.strip()
        rendered.append("PUBLIC" if name.upper() == "PUBLIC" else name)
    return ", ".join(rendered)


def validate_guc(guc: str) -> str:
    """Validate a GUC (custom setting) name such as ``rls.tenant_id``."""
    if not isinstance(guc, str) or not _GUC.match(guc):
        raise PolicyError(
            f"Invalid GUC name {guc!r}. Expected 'namespace.name' (e.g. 'rls.tenant_id')."
        )
    return guc


def validate_cast(cast: str) -> str:
    """Validate a cast target type name such as ``uuid`` or ``bigint``."""
    if not isinstance(cast, str) or not cast.strip() or not _CAST.match(cast.strip()):
        raise PolicyError(
            f"Invalid cast type {cast!r}. Use a plain PostgreSQL type name "
            "(e.g. 'text', 'uuid', 'bigint')."
        )
    return cast.strip()


def current_setting_sql(guc: str, cast: str) -> str:
    """Return the scalar-subquery SQL that reads a GUC as a typed value.

    Wrapping ``current_setting`` in a scalar subquery makes the planner evaluate it once
    per statement (an InitPlan) instead of once per candidate row — the documented
    PostgreSQL RLS performance pattern. ``NULLIF(..., '')`` maps an unset/empty GUC to
    ``NULL`` so the enclosing equality matches no rows (fail-closed).
    """
    validate_guc(guc)
    validate_cast(cast)
    return f"(SELECT NULLIF(current_setting('{guc}', true), '')::{cast})"
