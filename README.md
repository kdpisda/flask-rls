# flask-rls

[![License](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)

**PostgreSQL Row-Level Security for Flask and SQLAlchemy.**

Security enforced by PostgreSQL, not by application code. Once a table has RLS enabled and
a tenant/user policy attached, the database itself returns only the rows the current
request is authorized to see — even for raw SQL or a forgotten `.filter()`.

flask-rls is the Flask/SQLAlchemy sibling of
[django-rls](https://github.com/kdpisda/django-rls): the same concepts (`TenantPolicy`,
`UserPolicy`, `CustomPolicy`, Pythonic policies, `RLS.user_id()`), adapted to SQLAlchemy
Core and the Flask request lifecycle.

## Features

- 🔒 Database-level Row-Level Security using PostgreSQL RLS
- 🏢 Tenant-based and user-based policies
- 🐍 **Pythonic policies** — compose predicates from SQLAlchemy Core expressions
- ⚡ **Pool-safe** — context is set per transaction via `set_config(..., is_local=true)`,
  so it cannot leak across pooled connections
- 🧩 ORM-agnostic — works with bare SQLAlchemy or Flask-SQLAlchemy
- 🧱 Alembic migration operations (`op.enable_rls`, `op.create_policy`, …)
- 🛠️ `flask rls sql` to dump policy DDL

## Installation

```bash
pip install flask-rls            # core
pip install "flask-rls[alembic]" # + Alembic migration operations
```

Requires Python 3.10+, SQLAlchemy 2.0+, Flask 2.2+, and PostgreSQL 12+.

## Quick start

### 1. Initialize the extension

```python
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_rls import RLS

db = SQLAlchemy()
rls = RLS()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://app@localhost/mydb"
    db.init_app(app)
    with app.app_context():
        rls.init_app(app, engine=db.engine)

    @app.before_request
    def set_tenant():
        g.tenant_id = current_tenant_id()  # however your app resolves it
        g.user_id = current_user_id()

    return app
```

flask-rls reads `g.tenant_id` / `g.user_id` at each transaction begin and issues
`SELECT set_config('rls.tenant_id', ..., true)`. No context set → the GUC is `NULL` →
policies match zero rows (**fail closed**).

### 2. Define and register policies

```python
from flask_rls import TenantPolicy, UserPolicy, ExpressionPolicy, RLS
from sqlalchemy import column, true

rls.register("invoices", TenantPolicy("tenant_isolation", "tenant_id"))

# Pythonic policy: owner OR public
rls.register(
    "projects",
    ExpressionPolicy(
        "project_access",
        expr=(column("owner_id") == RLS.user_id()) | (column("is_public") == true()),
    ),
)
```

`rls.register(...)` feeds the `flask rls sql` dumper. Apply the DDL through Alembic (below)
or by piping `flask rls sql` into a migration.

### 3. Apply via Alembic

```python
# migrations/env.py
from flask_rls.alembic import *  # noqa: F401,F403  registers op.enable_rls, ...

# a migration
from flask_rls import TenantPolicy

def upgrade():
    op.enable_rls("invoices")
    op.force_rls("invoices")
    op.create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id"))

def downgrade():
    op.drop_policy("invoices", "tenant_isolation")
    op.disable_rls("invoices")
```

## Running privileged / background work

Outside a request there is no `g`, so context falls through to fail-closed. Use the scope
managers:

```python
with rls.override(tenant_id=42):   # privileged identity switch (jobs, CLI, tests)
    generate_monthly_report()

with rls.bypass():                 # emit no context — for non-RLS tables
    create_new_tenant()
```

`bypass()` is **not** god-mode: on an RLS table it still sees zero rows. True cross-tenant
access requires a PostgreSQL role with `BYPASSRLS` (see the design doc).

## Important: the owner-bypass gotcha

A table's **owner** (and superusers) bypass RLS entirely unless the table has
`FORCE ROW LEVEL SECURITY`. flask-rls emits `FORCE` for every registered table, and your
application should connect as a **non-owner** role regardless.

## Configuration

| Flask config key | Default | Meaning |
|---|---|---|
| `RLS_GUC_PREFIX` | `rls.` | GUC namespace prefix |
| `RLS_G_TENANT_KEY` | `tenant_id` | `flask.g` attribute read for the tenant |
| `RLS_G_USER_KEY` | `user_id` | `flask.g` attribute read for the user |
| `RLS_REQUIRE_CONTEXT` | `False` | raise `RLSContextRequiredError` when context is missing |
| `RLS_DEBUG` | `False` | debug-log each `set_config` call |

## License

BSD 3-Clause — see [LICENSE](LICENSE).
