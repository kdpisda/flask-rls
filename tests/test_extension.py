"""Unit tests for the RLS extension (no live database)."""

from __future__ import annotations

import pytest
from flask import Flask, g
from sqlalchemy.sql.elements import ColumnElement

from flask_rls import RLS
from flask_rls.exceptions import RLSContextRequiredError


class FakeConn:
    """Records the parameters passed to ``execute`` in place of a real connection."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def execute(self, statement, params) -> None:  # noqa: ANN001
        self.calls.append(params)


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    return app


class TestConfig:
    def test_defaults(self, app: Flask) -> None:
        rls = RLS()
        rls.init_app(app)
        assert rls.guc_prefix == "rls."
        assert rls.g_tenant_key == "tenant_id"
        assert rls.require_context is False
        assert app.extensions["rls"] is rls

    def test_custom_config(self) -> None:
        app = Flask(__name__)
        app.config["RLS_GUC_PREFIX"] = "app."
        app.config["RLS_G_TENANT_KEY"] = "org_id"
        app.config["RLS_REQUIRE_CONTEXT"] = True
        rls = RLS(app)
        assert rls.guc_prefix == "app."
        assert rls.g_tenant_key == "org_id"
        assert rls.require_context is True


class TestContextReferences:
    def test_classmethods_return_elements(self) -> None:
        assert isinstance(RLS.tenant_id(), ColumnElement)
        assert isinstance(RLS.user_id(cast="bigint"), ColumnElement)


class TestGProvider:
    def test_reads_g(self, app: Flask) -> None:
        rls = RLS(app)
        with app.test_request_context():
            g.tenant_id = 7
            g.user_id = 3
            assert rls._g_provider() == {"tenant_id": 7, "user_id": 3}

    def test_missing_g_keys(self, app: Flask) -> None:
        rls = RLS(app)
        with app.test_request_context():
            assert rls._g_provider() == {}

    def test_outside_app_context(self, app: Flask) -> None:
        rls = RLS(app)
        assert rls._g_provider() == {}


class TestOnBegin:
    def test_sets_config_from_g(self, app: Flask) -> None:
        rls = RLS(app)
        conn = FakeConn()
        with app.test_request_context():
            g.tenant_id = 42
            rls._on_begin(conn)
        assert {"name": "rls.tenant_id", "value": "42"} in conn.calls

    def test_custom_prefix(self) -> None:
        app = Flask(__name__)
        app.config["RLS_GUC_PREFIX"] = "app."
        rls = RLS(app)
        conn = FakeConn()
        with app.test_request_context():
            g.tenant_id = 42
            rls._on_begin(conn)
        assert conn.calls[0]["name"] == "app.tenant_id"

    def test_no_context_no_calls(self, app: Flask) -> None:
        rls = RLS(app)
        conn = FakeConn()
        with app.test_request_context():
            rls._on_begin(conn)
        assert conn.calls == []

    def test_require_context_raises(self) -> None:
        app = Flask(__name__)
        app.config["RLS_REQUIRE_CONTEXT"] = True
        rls = RLS(app)
        conn = FakeConn()
        with app.test_request_context():
            with pytest.raises(RLSContextRequiredError):
                rls._on_begin(conn)

    def test_bypass_skips_require_context(self) -> None:
        app = Flask(__name__)
        app.config["RLS_REQUIRE_CONTEXT"] = True
        rls = RLS(app)
        conn = FakeConn()
        with app.test_request_context():
            with rls.bypass():
                rls._on_begin(conn)  # must not raise
        assert conn.calls == []

    def test_override_supplies_context(self, app: Flask) -> None:
        rls = RLS(app)
        conn = FakeConn()
        with rls.override(tenant_id=100):
            rls._on_begin(conn)
        assert {"name": "rls.tenant_id", "value": "100"} in conn.calls


class TestCustomProvider:
    def test_registered_provider_emitted(self, app: Flask) -> None:
        rls = RLS(app)
        conn = FakeConn()

        @rls.context_provider
        def ip_provider() -> dict:
            return {"ip": "10.0.0.1"}

        with app.test_request_context():
            g.tenant_id = 1
            rls._on_begin(conn)
        names = {c["name"] for c in conn.calls}
        assert "rls.ip" in names
        assert "rls.tenant_id" in names
