---
sidebar_position: 4
---

# API Reference

## `RLS`

The Flask extension. Also exposes classmethods used inside `ExpressionPolicy`.

```python
RLS(app=None, engine=None)
```

| Member | Description |
|---|---|
| `init_app(app, engine=None)` | Configure for `app`; bind `engine` if given. |
| `bind_engine(engine)` | Register the per-transaction handler on a SQLAlchemy `Engine`. |
| `register(table, *policies, force=True)` | Register policies for the `flask rls sql` dumper. |
| `context_provider(func)` | Register a `() -> {key: value}` provider. Usable as a decorator. |
| `override(**keys)` | Context manager: force context keys (privileged switch). |
| `bypass()` | Context manager: emit no context (fail-closed on RLS tables). |
| `RLS.tenant_id(cast="text", guc="rls.tenant_id")` | *classmethod* — element reading the tenant GUC. |
| `RLS.user_id(cast="text", guc="rls.user_id")` | *classmethod* — element reading the user GUC. |

## Policies

All accept `operation="ALL"`, `permissive=True`, `roles="public"`.

```python
TenantPolicy(name, tenant_field, *, cast="text", guc="rls.tenant_id")
UserPolicy(name, user_field="user_id", *, cast="text", guc="rls.user_id")
CustomPolicy(name, expression)
ExpressionPolicy(name, expr)      # expr is a SQLAlchemy ColumnElement
```

Each exposes `get_using_expression()` and `get_check_expression()` (returning the predicate
or `None` when not valid for the operation).

## SQL generators — `flask_rls.sql`

Pure functions returning DDL strings.

```python
enable_rls(table) -> str
disable_rls(table) -> str
force_rls(table) -> str
no_force_rls(table) -> str
create_policy(table, policy) -> str
drop_policy(table, policy_name) -> str
```

## Registry — `flask_rls.PolicyRegistry`

```python
registry.register(table, *policies, force=True)
registry.tables() -> list[str]
registry.policies_for(table) -> list[BasePolicy]
registry.ddl(table=None) -> Iterator[str]
```

## Alembic operations — `flask_rls.alembic`

Import to register: `op.enable_rls`, `op.disable_rls`, `op.force_rls`, `op.no_force_rls`,
`op.create_policy`, `op.drop_policy`, `op.alter_policy`. See [Alembic](/docs/guides/alembic).

## CLI

```bash
flask rls sql [--table NAME]
```

Prints the RLS DDL (`ENABLE` / `FORCE` / `CREATE POLICY`) for registered policies.

## Exceptions — `flask_rls.exceptions`

| Exception | Raised when |
|---|---|
| `RLSError` | base class |
| `PolicyError` | invalid policy configuration (name, operation, role, field) |
| `ConfigurationError` | invalid or missing extension configuration |
| `RLSContextRequiredError` | context required (`RLS_REQUIRE_CONTEXT`) but missing |
| `RLSContextImmutableError` | an established identity key changed without `override()` |
| `TenantAccessDeniedError` | reserved for tenant-membership validation |
