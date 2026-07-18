---
sidebar_position: 1
---

# Tenant-based isolation

The most common multi-tenant pattern: every tenant sees only its own rows.

## Model

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.String, nullable=False)
    amount = db.Column(db.Numeric)
```

## Policy

```python
from flask_rls import RLS, TenantPolicy

rls = RLS()
rls.register("invoice", TenantPolicy("tenant_isolation", "tenant_id"))
```

## Migration

```python
from flask_rls import TenantPolicy

def upgrade():
    op.enable_rls("invoice")
    op.force_rls("invoice")
    op.create_policy("invoice", TenantPolicy("tenant_isolation", "tenant_id"))
```

## Request wiring

```python
@app.before_request
def set_tenant():
    g.tenant_id = current_user.tenant_id
```

## Result

```python
# during a request where g.tenant_id == "acme"
Invoice.query.all()          # only Acme's invoices

# a background job
with rls.override(tenant_id="acme"):
    Invoice.query.count()    # only Acme's invoices
```

If `g.tenant_id` is not set, the query returns **zero rows** — never another tenant's data.

## UUID tenant ids

If `tenant_id` is a UUID column, cast the GUC accordingly:

```python
TenantPolicy("tenant_isolation", "tenant_id", cast="uuid")
```
