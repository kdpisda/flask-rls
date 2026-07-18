---
sidebar_position: 5
---

# Testing

RLS cannot be enforced on SQLite, so behavior tests need **real PostgreSQL**. The two things
worth testing are that your policies isolate data and that they fail closed.

## Use a non-owner role

RLS only applies to roles that are subject to it. Run your isolation tests as a **non-owner**
login role (the table owner bypasses RLS unless the table is `FORCE`d — and Flask RLS does
emit `FORCE`, which you should also verify).

## Driving context in tests

Use `override()` to set context without a Flask request:

```python
def test_tenant_isolation(app_engine, rls):
    with rls.override(tenant_id="a"):
        with app_engine.connect() as conn:
            rows = conn.execute(text("SELECT body FROM notes")).all()
    assert all(r.tenant_id == "a" for r in rows)  # only tenant a
```

## What to assert

- **Isolation** — tenant A cannot see tenant B's rows.
- **Fail-closed** — with no context set, queries return zero rows.
- **No leak** — after a committed `override()`, the next transaction on the same pooled
  connection has no context (proves `is_local=true`).
- **WITH CHECK** — inserting a row for another tenant is rejected.
- **FORCE** — a non-superuser table owner is still subject to RLS.

## Testcontainers

The Flask RLS test suite spins up PostgreSQL with
[Testcontainers](https://testcontainers.com/), which requires Docker. A minimal fixture:

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()
```

See the project's `tests/integration/` for the full isolation suite.
