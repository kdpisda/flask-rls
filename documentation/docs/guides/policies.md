---
sidebar_position: 3
---

# Policies

A policy renders the `USING` / `WITH CHECK` predicate of a `CREATE POLICY` statement. All
policies share these keyword arguments:

| Argument | Default | Meaning |
|---|---|---|
| `operation` | `"ALL"` | `ALL`, `SELECT`, `INSERT`, `UPDATE`, or `DELETE` |
| `permissive` | `True` | permissive (`OR`-combined) vs restrictive (`AND`-combined) |
| `roles` | `"public"` | the policy's `TO` clause — `PUBLIC` or a comma-separated list |

`USING` and `WITH CHECK` are emitted only for the operations PostgreSQL allows: `USING` for
`SELECT`/`UPDATE`/`DELETE`/`ALL`, `WITH CHECK` for `INSERT`/`UPDATE`/`ALL`.

## TenantPolicy

Isolate rows by a tenant column:

```python
from flask_rls import TenantPolicy

TenantPolicy("tenant_isolation", "tenant_id")
TenantPolicy("tenant_isolation", "tenant_id", cast="uuid")   # cast the GUC
```

Generates `tenant_id = (SELECT NULLIF(current_setting('rls.tenant_id', true), '')::text)`.
The `cast` is configurable and defaults to `text`.

## UserPolicy

Isolate rows by an owning-user column, reading `rls.user_id`:

```python
from flask_rls import UserPolicy

UserPolicy("owner_only", "user_id")
```

## ExpressionPolicy

The Pythonic policy — compose a predicate from SQLAlchemy Core expressions, using
`RLS.tenant_id()` / `RLS.user_id()` as the context references:

```python
from flask_rls import ExpressionPolicy, RLS
from sqlalchemy import column, true

ExpressionPolicy(
    "project_access",
    expr=(column("owner_id") == RLS.user_id()) | (column("is_public") == true()),
)
```

The expression is compiled to SQL by SQLAlchemy's own PostgreSQL compiler, so identifiers
are quoted and literals rendered by the dialect — safer than hand-writing SQL.

## CustomPolicy

An escape hatch for a raw predicate. The expression is checked against obvious injection and
DDL payloads, but prefer `ExpressionPolicy` where possible:

```python
from flask_rls import CustomPolicy

CustomPolicy("recent_only", "created_at > now() - interval '30 days'")
```

## Performance: the InitPlan pattern

The `current_setting` read is wrapped in a scalar subquery
(`(SELECT NULLIF(current_setting(...), '')::type)`) so PostgreSQL evaluates it once per
statement (an InitPlan) rather than once per candidate row — the documented RLS performance
pattern, predicate-equivalent to the bare call.

## The owner-bypass gotcha

A table's **owner** and any **superuser** bypass RLS entirely unless the table has
`FORCE ROW LEVEL SECURITY`. Flask RLS emits `FORCE` for every registered table, and you
should connect your application as a **non-owner** role. Otherwise your policies exist but do
nothing.

## Validation

Every identifier that reaches generated DDL — table, field, role, GUC, cast — is validated
against a strict pattern before interpolation, and a malformed value raises `PolicyError`.
