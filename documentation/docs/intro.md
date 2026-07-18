---
sidebar_position: 1
slug: /intro
---

# Introduction

**Flask RLS** brings PostgreSQL Row-Level Security (RLS) to Flask applications backed by
SQLAlchemy. Security is enforced by the database, not by application-layer query filtering —
so even raw SQL or a forgotten `.filter()` cannot leak another tenant's rows.

> Flask RLS is the Flask/SQLAlchemy sibling of
> [django-rls](https://django-rls.com), created by [Kuldeep Pisda](https://kdpisda.in).
> The concepts and naming mirror django-rls, adapted to SQLAlchemy Core and the Flask
> request lifecycle.

## What is Row-Level Security?

Row-Level Security is a PostgreSQL feature that filters rows automatically based on policies
you define on a table. When a query runs, PostgreSQL evaluates each policy's predicate and
returns only the rows the current session is authorized to see. The application cannot
bypass it by "forgetting" a filter — the rule lives in the database.

## Why Flask RLS?

- 🔒 **Database-level security** — enforced by PostgreSQL with `FORCE ROW LEVEL SECURITY`.
- 🏢 **Tenant & user policies** — `TenantPolicy`, `UserPolicy`, `CustomPolicy`, and the
  Pythonic `ExpressionPolicy`.
- ⚡ **Pool-safe context** — set per transaction via `set_config('rls.*', …, true)`, so it
  cannot leak across pooled connections.
- 🧩 **ORM-agnostic** — binds at the SQLAlchemy engine layer; works with bare SQLAlchemy or
  Flask-SQLAlchemy.
- 🧱 **Alembic operations** — manage policies as first-class migration steps.
- 🧪 **Proven against PostgreSQL** — isolation and fail-closed behavior are verified against
  a live database.

## How it works

1. **Define policies** with `TenantPolicy` / `UserPolicy` / `ExpressionPolicy`.
2. **Apply them** to your tables (via Alembic operations or generated SQL).
3. **Initialize the extension** and set `g.tenant_id` / `g.user_id` per request.

On every transaction, Flask RLS reads the current context and issues
`set_config('rls.tenant_id', …, true)` so your policies filter automatically.

```python
from flask_rls import RLS, TenantPolicy

rls = RLS(app, engine=db.engine)
rls.register("invoices", TenantPolicy("tenant_isolation", "tenant_id"))
```

Ready to try it? Head to the [Quick Start](/docs/quick-start).
