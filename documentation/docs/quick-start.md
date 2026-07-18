---
sidebar_position: 3
---

# Quick Start

This walks through wiring Flask RLS into a Flask + Flask-SQLAlchemy app for tenant isolation.

## 1. Initialize the extension

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
    def set_rls_context():
        # however your app resolves the current tenant / user:
        g.tenant_id = current_tenant_id()
        g.user_id = current_user_id()

    return app
```

Flask RLS reads `g.tenant_id` / `g.user_id` at each transaction begin and issues
`SELECT set_config('rls.tenant_id', …, true)`. If no context is set, the GUC is `NULL` and
policies match **zero rows** (fail closed).

## 2. Register policies

```python
from flask_rls import TenantPolicy

rls.register("invoices", TenantPolicy("tenant_isolation", "tenant_id"))
```

## 3. Apply the policies to the database

Either generate the DDL:

```bash
flask rls sql
```

```sql
ALTER TABLE "invoices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "invoices" FORCE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON "invoices" AS PERMISSIVE FOR ALL TO PUBLIC
  USING (tenant_id = (SELECT NULLIF(current_setting('rls.tenant_id', true), '')::text))
  WITH CHECK (tenant_id = (SELECT NULLIF(current_setting('rls.tenant_id', true), '')::text));
```

…or apply them through [Alembic](/docs/guides/alembic):

```python
from flask_rls import TenantPolicy

def upgrade():
    op.enable_rls("invoices")
    op.force_rls("invoices")
    op.create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id"))
```

## 4. Query normally

```python
# during a request where g.tenant_id == "acme":
Invoice.query.all()   # returns only Acme's invoices — enforced by PostgreSQL
```

## Working outside a request

There is no `g` outside a request, so context falls through to fail-closed. Use the scope
managers for jobs, CLI commands, and tests:

```python
with rls.override(tenant_id="acme"):
    generate_monthly_report()

with rls.bypass():          # emit no context — for non-RLS tables only
    create_new_tenant()
```

Next: read about [policies](/docs/guides/policies) and [context](/docs/guides/context) in depth.
