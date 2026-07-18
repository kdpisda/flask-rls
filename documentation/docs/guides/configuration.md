---
sidebar_position: 1
---

# Configuration

Flask RLS reads configuration from standard Flask config keys.

| Key | Default | Meaning |
|---|---|---|
| `RLS_GUC_PREFIX` | `rls.` | GUC namespace prefix; the full GUC is `<prefix><key>` |
| `RLS_G_TENANT_KEY` | `tenant_id` | `flask.g` attribute read for the tenant |
| `RLS_G_USER_KEY` | `user_id` | `flask.g` attribute read for the user |
| `RLS_REQUIRE_CONTEXT` | `False` | raise `RLSContextRequiredError` when context is missing |
| `RLS_DEBUG` | `False` | debug-log each `set_config` call |

```python
app.config["RLS_REQUIRE_CONTEXT"] = True
app.config["RLS_G_TENANT_KEY"] = "org_id"   # read g.org_id instead of g.tenant_id
rls.init_app(app, engine=db.engine)
```

## GUC names

The full PostgreSQL setting is `<RLS_GUC_PREFIX><key>`. With the defaults, the tenant is
stored in `rls.tenant_id` and the user in `rls.user_id` — the same names your policies read
via `current_setting('rls.tenant_id', true)`.

If you change `RLS_GUC_PREFIX`, pass a matching `guc=` to your policies so the two agree:

```python
TenantPolicy("tenant_isolation", "tenant_id", guc="app.tenant_id")
```

## Requiring context

By default, a missing context fails closed (zero rows). Setting `RLS_REQUIRE_CONTEXT = True`
turns a missing context into a loud `RLSContextRequiredError` at transaction begin, which is
useful in development to catch views that forgot to set `g.tenant_id`. A `bypass()` scope is
exempt from this check.

## Policy defaults

`roles` (default `"public"`) and `permissive` (default `True`) are arguments on the policy
classes themselves, not Flask config — policies are typically defined at migration time,
outside any Flask app context. See [Policies](/docs/guides/policies).
