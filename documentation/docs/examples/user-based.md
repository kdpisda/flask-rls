---
sidebar_position: 2
---

# User-based ownership

Restrict rows to the user who owns them, reading `rls.user_id`.

## Model

```python
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String)
```

## Policy

```python
from flask_rls import RLS, UserPolicy

rls = RLS()
rls.register("document", UserPolicy("owner_only", "user_id", cast="bigint"))
```

This generates:

```sql
user_id = (SELECT NULLIF(current_setting('rls.user_id', true), '')::bigint)
```

## Request wiring

```python
@app.before_request
def set_user():
    if current_user.is_authenticated:
        g.user_id = current_user.id
```

## Read-only vs write policies

By default a policy applies to `ALL` operations. To allow everyone to read but only the owner
to modify, combine two policies:

```python
from flask_rls import UserPolicy, CustomPolicy

rls.register(
    "document",
    CustomPolicy("read_all", "true", operation="SELECT"),
    UserPolicy("owner_writes", "user_id", operation="UPDATE"),
    UserPolicy("owner_deletes", "user_id", operation="DELETE"),
    UserPolicy("owner_inserts", "user_id", operation="INSERT"),
)
```
