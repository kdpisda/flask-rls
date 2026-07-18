# flask-rls — Design Spec

**Date:** 2026-07-18
**Status:** Approved for planning
**Author:** Kuldeep Pisda (with Claude)

## 1. Purpose

`flask-rls` is an open-source library that brings PostgreSQL Row-Level Security (RLS)
to Flask applications backed by SQLAlchemy. It is the Flask sibling of
[`django-rls`](https://github.com/kdpisda/django-rls) — same concepts and naming,
adapted to SQLAlchemy Core and the Flask request lifecycle.

Security is enforced by PostgreSQL, not by application-layer query filtering. Once a
table has RLS enabled and a tenant/user policy attached, the database itself returns
only the rows the current context is authorized to see — even for raw SQL, admin
tooling, or a forgotten `.filter()`.

The library has three responsibilities:

1. **Context setting** — set per-transaction Postgres session variables (GUCs) so RLS
   policies can read the current tenant/user via `current_setting()`.
2. **Policy authoring** — Python classes that generate the `CREATE POLICY` /
   `ALTER TABLE ... ENABLE/FORCE ROW LEVEL SECURITY` SQL.
3. **Migrations** — Alembic operation directives that apply that SQL as first-class
   migration steps.

## 2. Scope

### In scope (v1)
- SQLAlchemy Core integration at the `Engine` level (ORM-agnostic — works with bare
  SQLAlchemy or Flask-SQLAlchemy).
- Per-transaction context via `SET LOCAL` on the engine `begin` event.
- Pluggable context providers (default: Flask `g`), plus `override()` and `bypass()`
  context managers for non-request code.
- Policy classes: `TenantPolicy`, `UserPolicy`, `CustomPolicy`, `ExpressionPolicy`.
- `RLS.tenant_id()` / `RLS.user_id()` context references (SQLAlchemy elements).
- SQL generators: enable RLS, force RLS, create policy, drop policy.
- Alembic operations wrapping the generators.
- Flask CLI: `flask rls sql` to print policy DDL.
- Tests against real PostgreSQL.

### Out of scope (v1) — candidates for later
- Alembic **autogenerate** integration (detect policy drift automatically).
- Hierarchical RLS via recursive CTEs / nested organizations (django-rls has this).
- `TENANT_MEMBERSHIP_VALIDATOR` enforcement in the request path.
- A declarative-model auto-enable signal equivalent to django's `post_migrate`.

## 3. Core mechanism

### 3.1 Why `SET LOCAL`
Postgres RLS policies read the current context through a custom GUC, e.g.
`current_setting('rls.tenant_id', true)`. The value must be set on the connection that
runs the query. Two strategies exist:

- **`SET LOCAL` on transaction begin (chosen).** Transaction-scoped; Postgres
  automatically resets it on `COMMIT`/`ROLLBACK`. It therefore *cannot* leak across
  pooled connections. This is the safe default for multi-tenant isolation.
- `SET SESSION` on pool checkout + `RESET` on checkin (rejected). Works outside
  explicit transactions but a missed reset leaks one tenant's context into the next
  request served by that pooled connection.

This is a deliberate improvement over django-rls, which sets the GUC per request on the
connection and clears it on teardown/`reset_connection_rls_context`.

### 3.2 Binding
`RLS.init_app(app, engine=...)` registers a listener on the SQLAlchemy `Engine`'s
`"begin"` event. On each transaction begin the handler:

1. Resolves the active context (see §4).
2. For each `(key, value)` emits `SET LOCAL rls.<key> = :value` via
   `conn.exec_driver_sql` with the value passed as a bound parameter (never string
   interpolation).

Because SQLAlchemy 2.0 autobegins a transaction for every statement, the `begin` event
fires for both explicit and implicit transactions, so `SET LOCAL` always lands inside
the transaction it applies to. This hook is ORM-agnostic: Flask-SQLAlchemy sessions and
bare Core connections share the same engine and fire the same event.

> **Constraint:** `SET LOCAL` has no effect outside a transaction block. Code running in
> driver-level autocommit (no transaction) will not carry context. This is documented; the
> normal SQLAlchemy/Flask-SQLAlchemy usage is always transactional.

## 4. Context resolution

### 4.1 Multi-key context
Context is not tenant-only. Mirroring django-rls's context processors, the extension
resolves a `dict[str, value]` each transaction and emits one `SET LOCAL rls.<key>` per
entry. Default keys: `tenant_id`, `user_id`.

### 4.2 Providers
A **context provider** is a callable returning `dict[str, value]` (or `{}`). The built-in
provider reads Flask `g` (keys configurable, default `g.tenant_id` and `g.user_id`) and
is safe outside a request context (returns `{}` rather than raising when there is no app
context). Apps register additional providers for custom keys (e.g. `ip`, `org_id`):

```python
@rls.context_provider
def request_ip():
    return {"ip": request.remote_addr} if has_request_context() else {}
```

### 4.3 Resolution order (highest precedence first)
1. **`bypass()` active** → emit nothing (privileged/system work). See §4.5.
2. **`override(**kwargs)` active** → use the overridden keys/values (merged over
   provider output for the keys given).
3. **Registered providers** (built-in `g` provider + app providers), merged in
   registration order.
4. Nothing resolvable → emit nothing → GUCs unset → fail closed (§4.4).

`bypass()` and `override()` are implemented with `contextvars`, so they are correct
under threads, `gevent`, and `asyncio` without leaking across requests.

### 4.4 Fail-closed semantics
Generated policies read the GUC with the missing-ok form
`current_setting('rls.tenant_id', true)`. When unset this is `NULL`, so
`tenant_id = NULL` matches no rows — "no context" yields zero rows by construction.

`RLS_REQUIRE_CONTEXT` (default `False`, mirrors django's `REQUIRE_CONTEXT`) upgrades this
to a loud failure: if a transaction begins with no resolvable context and no active
`bypass()`, raise `RLSContextError`. This turns silent empty-result bugs into errors in
development.

### 4.5 Bypass and the owner-bypass gotcha
`with rls.bypass():` runs a transaction with no tenant/user GUC — for login, tenant
creation, and admin/system jobs.

**Critical Postgres behavior:** a table's owner (and superusers) bypass RLS *unless* the
table is set to `FORCE ROW LEVEL SECURITY`. So `bypass()` only means something if the
app's normal DB role is a non-owner, **or** policies use `FORCE`. The policy helpers
always emit `ALTER TABLE ... FORCE ROW LEVEL SECURITY` to close this gap, and this
requirement is documented prominently.

## 5. Policy classes

All policies subclass `BasePolicy` and mirror django-rls semantics:

- Constructor: `name`, `operation` (`ALL`/`SELECT`/`INSERT`/`UPDATE`/`DELETE`, default
  `ALL`), `permissive` (default from `RLS_DEFAULT_PERMISSIVE`, itself default `True`),
  `roles` (default from `RLS_DEFAULT_ROLES`, default `"public"`).
- Validation on construction: `name` required; `operation` in the valid set; `roles`
  is `PUBLIC` or a comma-separated list of valid PG identifiers (regex-checked, since it
  is interpolated into the un-parameterizable `TO` clause); field names regex-checked.
- `get_using_expression()` (USING clause, for SELECT/DELETE) and
  `get_check_expression()` (WITH CHECK, for INSERT/UPDATE; defaults to the USING
  expression for `ALL`/`INSERT`/`UPDATE`).
- The `current_setting` read is wrapped in a scalar subquery
  `(SELECT NULLIF(current_setting('rls.tenant_id', true), '')::<cast>)` so the planner
  evaluates it once per statement (InitPlan) rather than per row — the documented
  Postgres RLS performance pattern, predicate-equivalent to the bare call.

### 5.1 `TenantPolicy(name, tenant_field, cast="text", ...)`
Generates `<tenant_field> = (SELECT NULLIF(current_setting('rls.tenant_id', true), '')::<cast>)`.
`cast` is configurable per policy; default `"text"` (django-rls hardcodes integer —
flask-rls generalizes it).

### 5.2 `UserPolicy(name, user_field="user_id", cast="text", ...)`
Same shape against `rls.user_id`.

### 5.3 `CustomPolicy(name, expression, ...)`
Raw SQL expression. Validated against a forbidden-SQL regex (rejects `;`, comments, and
DDL/DML keywords) to blunt injection when the expression comes from config. Documented as
an escape hatch; `ExpressionPolicy` is preferred.

### 5.4 `ExpressionPolicy(name, expr, ...)` — the Pythonic policy
The SQLAlchemy analog of django-rls's `ModelPolicy(filters=Q(...))`. Accepts a
SQLAlchemy Core `ColumnElement` built from real column expressions and the context
references:

```python
from sqlalchemy import column, true
from flask_rls import ExpressionPolicy, RLS

ExpressionPolicy(
    "project_access",
    expr=(column("owner_id") == RLS.user_id()) | (column("is_public") == true()),
)
```

`RLS.tenant_id(cast="text")` and `RLS.user_id(cast="text")` return SQLAlchemy elements
that compile to the scalar-subquery `current_setting` form. The policy compiles `expr`
to SQL via SQLAlchemy's compiler with `literal_binds` where safe; column identifiers come
from SQLAlchemy (already quoted/escaped), so this is safer than `CustomPolicy`.

## 6. SQL generation & registry

`policies.py` (or `sql.py`) exposes pure SQL generators, usable with or without Alembic:

- `enable_rls(table) -> str`  → `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY`
- `force_rls(table) -> str`   → `ALTER TABLE <table> FORCE ROW LEVEL SECURITY`
- `create_policy(table, policy) -> str` → `CREATE POLICY ...` from a policy object
- `drop_policy(table, name) -> str` → `DROP POLICY IF EXISTS ...`

A lightweight `PolicyRegistry` maps `table_name -> [policies]` so policies can be
declared centrally and emitted together (used by the CLI and, optionally, a declarative
mixin). Table and policy names are identifier-validated before interpolation.

## 7. Alembic integration (`alembic.py`, optional extra)

Custom operation directives registered via `@Operations.register_operation`, each
wrapping the §6 generators and emitting SQL through `op.execute`:

```python
op.enable_rls("invoices")
op.force_rls("invoices")
op.create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id", cast="uuid"))
op.drop_policy("invoices", "tenant_isolation")
```

Each has a reverse for `downgrade()` where meaningful (`create_policy` ↔ `drop_policy`,
`enable_rls` ↔ `disable_rls`). Shipped under the `flask-rls[alembic]` extra so Alembic
is not a hard dependency.

## 8. Flask extension API

```python
from flask_rls import RLS

rls = RLS()

def create_app():
    app = Flask(__name__)
    db = SQLAlchemy(app)           # or a bare SQLAlchemy engine
    rls.init_app(app, engine=db.engine)
    return app

# per request: app sets g.tenant_id / g.user_id in its own before_request
# (Flask g convention) — flask-rls reads them at transaction begin.

# background job / CLI / test:
with rls.override(tenant_id=42):
    run_report()

with rls.bypass():                 # privileged/system work
    create_new_tenant()
```

`RLS` supports both the direct (`RLS(app, engine=...)`) and factory
(`RLS()` + `init_app`) patterns.

## 9. Configuration (Flask config keys)

Mirrors django-rls's `DJANGO_RLS` dict as flat Flask config keys:

| Key | Default | Meaning |
|---|---|---|
| `RLS_TENANT_GUC` | `rls.tenant_id` | GUC name for tenant context |
| `RLS_USER_GUC` | `rls.user_id` | GUC name for user context |
| `RLS_G_TENANT_KEY` | `tenant_id` | `flask.g` attribute for tenant |
| `RLS_G_USER_KEY` | `user_id` | `flask.g` attribute for user |
| `RLS_DEFAULT_ROLES` | `public` | default `TO` roles for policies |
| `RLS_DEFAULT_PERMISSIVE` | `True` | permissive vs restrictive policies |
| `RLS_REQUIRE_CONTEXT` | `False` | raise `RLSContextError` when context missing |
| `RLS_DEBUG` | `False` | debug logging of emitted `SET LOCAL` |

## 10. CLI

A Flask CLI group registered on `init_app`:

- `flask rls sql [--table NAME]` — print the DDL (`ENABLE`/`FORCE`/`CREATE POLICY`) for
  registered policies, for review or piping into a migration. Mirrors django-rls's
  management commands.

## 11. Exceptions (`exceptions.py`)

- `RLSError` — base.
- `PolicyError(RLSError)` — invalid policy configuration (bad name/operation/role/field).
- `RLSContextError(RLSError)` — required context missing (`RLS_REQUIRE_CONTEXT`).
- `TenantAccessDeniedError(RLSError)` — reserved for membership validation (mirrors
  django-rls; enforcement is a later milestone).

## 12. Testing strategy

RLS is unenforceable on SQLite, so behavior tests require **real PostgreSQL**
(via `testcontainers` or a CI Postgres service).

- **Unit (no DB):** policy classes produce exact SQL strings; validation rejects bad
  identifiers/roles/operations and injection payloads; context resolution order and
  `override`/`bypass` precedence; provider merging.
- **Integration (Postgres):** two DB roles —
  1. a **non-owner app role** where RLS applies: cross-tenant isolation (tenant A cannot
     see tenant B's rows), `SELECT`/`INSERT`/`UPDATE`/`DELETE` policies, fail-closed when
     context unset, `override`/`bypass` behavior, and `SET LOCAL` not leaking across
     transactions on a pooled connection;
  2. the **table owner** with `FORCE ROW LEVEL SECURITY` to prove owner-bypass is closed.
- **Pytest fixtures** (not class-based `setUp`), Postgres session fixture + per-test
  transaction rollback.

## 13. Packaging & tooling

- `pyproject.toml` with hatchling.
- Python 3.9+ (align with django-rls's floor where reasonable), `SQLAlchemy>=2.0`,
  `Flask>=2.2`. Alembic is an optional extra: `flask-rls[alembic]`.
- Ruff (lint + format), mypy (typed public API), pytest + coverage.
- GitHub Actions: lint/type job + test matrix across Python versions with a Postgres
  service; codecov; build/publish workflow. BSD 3-Clause license (match django-rls).
- Repo docs: `README.md` (quick start mirroring the django-rls readme), `SECURITY.md`,
  `CONTRIBUTING.md`.

## 14. Module layout

```
flask_rls/
  __init__.py     # public exports: RLS, policy classes, RLS refs, exceptions
  extension.py    # RLS extension: init_app, config, engine begin-event binding, CLI reg
  context.py      # contextvars, providers, override()/bypass(), resolution order
  policies.py     # BasePolicy + Tenant/User/Custom/ExpressionPolicy, RLS refs
  sql.py          # pure SQL generators (enable/force/create/drop) + identifier validation
  registry.py     # PolicyRegistry (table -> policies)
  alembic.py      # Alembic operation directives (optional extra)
  cli.py          # `flask rls` CLI group
  exceptions.py   # RLSError hierarchy
```

## 15. Open questions / future work
- Alembic autogenerate support for policy drift detection.
- Hierarchical / recursive-CTE policies (django-rls parity).
- Optional declarative SQLAlchemy mixin (`__rls_policies__`) as sugar over the registry.
- `TENANT_MEMBERSHIP_VALIDATOR` enforcement in the request path.

## References
- django-rls: https://github.com/kdpisda/django-rls · https://django-rls.com/
- PostgreSQL RLS: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
