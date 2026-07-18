---
sidebar_position: 2
---

# Installation

## Requirements

- Python 3.10+
- SQLAlchemy 2.0+
- Flask 2.2+
- PostgreSQL 12+ (tested against PostgreSQL 16)

## Install

```bash
pip install flask-rls
```

To use the [Alembic migration operations](/docs/guides/alembic), install the extra:

```bash
pip install "flask-rls[alembic]"
```

## Verify

```python
import flask_rls
print(flask_rls.__version__)
```

## A note on database roles

RLS is only meaningful when your application connects as a role that is **subject** to the
policies. A table's **owner** (and superusers) bypass RLS unless the table is set to
`FORCE ROW LEVEL SECURITY`.

Flask RLS emits `FORCE` for every table you register, but you should still connect your
application as a dedicated **non-owner** role. See [Policies](/docs/guides/policies#the-owner-bypass-gotcha)
for details.
