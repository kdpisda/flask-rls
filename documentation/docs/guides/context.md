---
sidebar_position: 2
---

# Context

RLS policies read the current identity from PostgreSQL session variables (GUCs). Flask RLS
sets those variables **per transaction** so your policies can filter rows.

## The mechanism

On each transaction begin, Flask RLS resolves the active context and, for every key, runs:

```sql
SELECT set_config('rls.tenant_id', :value, true)
```

The third argument (`is_local`) is `true`, so the setting is **transaction-scoped**:
PostgreSQL discards it automatically on `COMMIT`/`ROLLBACK`. It therefore **cannot leak
across pooled connections** — there is nothing to reset.

:::note Why not `SET LOCAL`?
`SET LOCAL rls.tenant_id = :value` is invalid — `SET` cannot take a bind parameter.
`set_config()` is an ordinary function call, so both the GUC name and value are bound,
eliminating string interpolation.
:::

## Where context comes from

Flask RLS resolves context from **providers** — callables returning `{key: value}`. The
built-in provider reads Flask `g`:

```python
@app.before_request
def set_rls_context():
    g.tenant_id = current_tenant_id()
    g.user_id = current_user_id()
```

Register additional providers for custom keys:

```python
from flask import request, has_request_context

@rls.context_provider
def request_ip():
    if has_request_context():
        return {"ip": request.remote_addr}
    return {}
```

A key named `ip` becomes the GUC `rls.ip`, which a policy can read with
`current_setting('rls.ip', true)`.

## Resolution order

From highest precedence to lowest:

1. **`bypass()`** active → emit nothing.
2. **`override()`** values → win over providers for the keys given.
3. **Registered providers** → merged in registration order.
4. Nothing resolvable → GUCs unset → **fail closed** (zero rows).

## Scopes for non-request code

Outside a request there is no `g`. Use the scope managers:

```python
# privileged identity switch — jobs, CLI commands, tests
with rls.override(tenant_id="acme", user_id=42):
    generate_report()

# emit no context (fail-closed on RLS tables) — for work on non-RLS tables
with rls.bypass():
    create_new_tenant()
```

Both are implemented with `contextvars`, so they are correct under threads, greenlets, and
asyncio without leaking across requests.

:::warning `bypass()` is not god-mode
On an RLS-protected table, `bypass()` emits no context, so it still sees **zero** rows.
True cross-tenant access requires a PostgreSQL role with the `BYPASSRLS` attribute — run
such work through a separate engine bound to that role.
:::
