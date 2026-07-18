---
sidebar_position: 4
---

# Alembic migrations

Flask RLS ships Alembic operation directives so you can manage RLS as first-class migration
steps. Install the extra:

```bash
pip install "flask-rls[alembic]"
```

## Register the operations

Import the module once in your Alembic `env.py`; importing it registers the `op.*` methods:

```python
# migrations/env.py
from flask_rls.alembic import *  # noqa: F401,F403  registers op.enable_rls, ...
```

## Use them in migrations

```python
from flask_rls import TenantPolicy

def upgrade():
    op.enable_rls("invoices")
    op.force_rls("invoices")
    op.create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id"))

def downgrade():
    op.drop_policy("invoices", "tenant_isolation")
    op.disable_rls("invoices")
```

## Available operations

| Operation | SQL | Reverse |
|---|---|---|
| `op.enable_rls(table)` | `ENABLE ROW LEVEL SECURITY` | `disable_rls` |
| `op.disable_rls(table)` | `DISABLE ROW LEVEL SECURITY` | `enable_rls` |
| `op.force_rls(table)` | `FORCE ROW LEVEL SECURITY` | `no_force_rls` |
| `op.no_force_rls(table)` | `NO FORCE ROW LEVEL SECURITY` | `force_rls` |
| `op.create_policy(table, policy)` | `CREATE POLICY …` | `drop_policy` |
| `op.drop_policy(table, name)` | `DROP POLICY IF EXISTS …` | needs the policy |
| `op.alter_policy(table, policy)` | drop + recreate | write an explicit downgrade |

## Reversibility

`create_policy` reverses to `drop_policy` automatically. To make a standalone `drop_policy`
reversible (so `downgrade()` recreates it), pass the original policy:

```python
op.drop_policy("invoices", "tenant_isolation", policy=TenantPolicy("tenant_isolation", "tenant_id"))
```

`alter_policy` is implemented as drop-then-create (portable across PostgreSQL versions); its
reversal requires the prior definition, so write an explicit `downgrade()`.

## Previewing the DDL

Prefer to review the SQL first? Register your policies on the extension and dump them:

```bash
flask rls sql --table invoices
```
