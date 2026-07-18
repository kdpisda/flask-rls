"""The Flask extension.

``RLS`` plays two roles:

* **instance** — the Flask extension: ``rls = RLS(app, engine=...)`` binds a per-transaction
  handler that sets the tenant/user GUCs, and exposes ``override()`` / ``bypass()`` /
  ``context_provider`` / ``register``.
* **classmethods** — ``RLS.tenant_id()`` / ``RLS.user_id()`` return SQLAlchemy elements for
  use inside :class:`~flask_rls.policies.ExpressionPolicy`, mirroring django-rls's
  ``RLS.user_id()`` API.
"""

from __future__ import annotations

import logging
from contextlib import AbstractContextManager
from typing import Any

from flask import Flask, g, has_app_context
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.elements import ColumnElement

from flask_rls.context import (
    Provider,
    bypass_scope,
    override_scope,
    resolve_context,
)
from flask_rls.exceptions import RLSContextRequiredError
from flask_rls.policies import BasePolicy, tenant_ref, user_ref
from flask_rls.registry import PolicyRegistry

logger = logging.getLogger("flask_rls")

_SET_CONFIG = text("SELECT set_config(:name, :value, true)")


class RLS:
    """PostgreSQL Row-Level Security extension for Flask + SQLAlchemy."""

    def __init__(self, app: Flask | None = None, engine: Engine | None = None) -> None:
        self.registry = PolicyRegistry()
        self._providers: list[Provider] = [self._g_provider]
        self._bound_engines: list[Engine] = []
        # Config (populated by init_app); defaults chosen for the common case.
        self.guc_prefix: str = "rls."
        self.g_tenant_key: str = "tenant_id"
        self.g_user_key: str = "user_id"
        self.require_context: bool = False
        self.debug: bool = False
        if app is not None:
            self.init_app(app, engine=engine)

    # -- context references (for ExpressionPolicy) --------------------------------------

    @staticmethod
    def tenant_id(cast: str = "text", guc: str = "rls.tenant_id") -> ColumnElement:
        """SQLAlchemy element reading the tenant GUC (use inside ``ExpressionPolicy``)."""
        return tenant_ref(cast=cast, guc=guc)

    @staticmethod
    def user_id(cast: str = "text", guc: str = "rls.user_id") -> ColumnElement:
        """SQLAlchemy element reading the user GUC (use inside ``ExpressionPolicy``)."""
        return user_ref(cast=cast, guc=guc)

    # -- setup --------------------------------------------------------------------------

    def init_app(self, app: Flask, engine: Engine | None = None) -> None:
        """Configure the extension for ``app`` and, if given, bind ``engine``."""
        self.guc_prefix = app.config.setdefault("RLS_GUC_PREFIX", "rls.")
        self.g_tenant_key = app.config.setdefault("RLS_G_TENANT_KEY", "tenant_id")
        self.g_user_key = app.config.setdefault("RLS_G_USER_KEY", "user_id")
        self.require_context = app.config.setdefault("RLS_REQUIRE_CONTEXT", False)
        self.debug = app.config.setdefault("RLS_DEBUG", False)

        app.extensions["rls"] = self

        from flask_rls.cli import rls_cli

        app.cli.add_command(rls_cli)

        if engine is not None:
            self.bind_engine(engine)

    def bind_engine(self, engine: Engine) -> None:
        """Register the per-transaction context handler on ``engine``."""
        if engine in self._bound_engines:
            return
        event.listen(engine, "begin", self._on_begin)
        self._bound_engines.append(engine)

    # -- context providers & scopes -----------------------------------------------------

    def context_provider(self, func: Provider) -> Provider:
        """Register a context provider ``() -> {key: value}``. Usable as a decorator."""
        self._providers.append(func)
        return func

    def override(self, **keys: Any) -> AbstractContextManager:
        """Force context keys for the block (privileged identity switch, e.g. jobs/tests)."""
        return override_scope(**keys)

    def bypass(self) -> AbstractContextManager:
        """Emit no RLS context for the block (fail-closed on RLS tables)."""
        return bypass_scope()

    def register(self, table: str, *policies: BasePolicy, force: bool = True) -> None:
        """Register policies for ``table`` on this extension's registry (for the CLI)."""
        self.registry.register(table, *policies, force=force)

    # -- internals ----------------------------------------------------------------------

    def _g_provider(self) -> dict[str, Any]:
        """Built-in provider that reads tenant/user identity from Flask ``g``."""
        if not has_app_context():
            return {}
        out: dict[str, Any] = {}
        tenant = getattr(g, self.g_tenant_key, None)
        if tenant is not None:
            out["tenant_id"] = tenant
        user = getattr(g, self.g_user_key, None)
        if user is not None:
            out["user_id"] = user
        return out

    def _on_begin(self, conn: Any) -> None:
        """SQLAlchemy ``begin`` handler: set the resolved context on the new transaction."""
        values, is_bypass = resolve_context(self._providers)
        if not values and not is_bypass and self.require_context:
            raise RLSContextRequiredError(
                "RLS identity context is required but none is set. Set g.tenant_id/"
                "g.user_id in a before_request, use rls.override(...), or disable "
                "RLS_REQUIRE_CONTEXT for this environment."
            )
        for key, value in values.items():
            guc = f"{self.guc_prefix}{key}"
            conn.execute(_SET_CONFIG, {"name": guc, "value": value})
            if self.debug:
                logger.debug("flask-rls set %s = %s", guc, value)
