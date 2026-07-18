---
sidebar_position: 3
---

# Pythonic policies (ExpressionPolicy)

`ExpressionPolicy` composes a predicate from SQLAlchemy Core expressions — the analog of
django-rls's `ModelPolicy(filters=Q(...))`.

## Owner or public

```python
from flask_rls import ExpressionPolicy, RLS
from sqlalchemy import column, true

rls.register(
    "project",
    ExpressionPolicy(
        "project_access",
        expr=(column("owner_id") == RLS.user_id()) | (column("is_public") == true()),
    ),
)
```

Compiles to:

```sql
owner_id = (SELECT NULLIF(current_setting('rls.user_id', true), '')::text)
  OR is_public = true
```

## Combining tenant and status

```python
from sqlalchemy import column, and_

ExpressionPolicy(
    "active_tenant_rows",
    expr=and_(
        column("tenant_id") == RLS.tenant_id(),
        column("status") != "archived",
    ),
)
```

## Context references

`RLS.tenant_id()` and `RLS.user_id()` return SQLAlchemy elements that read the corresponding
GUC. Both accept a `cast`:

```python
column("tenant_id") == RLS.tenant_id(cast="uuid")
```

## Why it's safer than raw SQL

The expression is compiled by SQLAlchemy's own PostgreSQL dialect, so column identifiers are
quoted and literal values are rendered by the dialect rather than by string concatenation.
Prefer `ExpressionPolicy` over `CustomPolicy` whenever your predicate can be expressed with
SQLAlchemy Core.
