"""Unit tests for the ``flask rls`` CLI."""

from __future__ import annotations

import pytest
from flask import Flask

from flask_rls import RLS, TenantPolicy


@pytest.fixture
def app() -> Flask:
    return Flask(__name__)


def test_sql_lists_registered_ddl(app: Flask) -> None:
    rls = RLS(app)
    rls.register("invoices", TenantPolicy("tenant_isolation", "tenant_id"))
    result = app.test_cli_runner().invoke(args=["rls", "sql"])
    assert result.exit_code == 0
    assert "ENABLE ROW LEVEL SECURITY" in result.output
    assert "FORCE ROW LEVEL SECURITY" in result.output
    assert 'CREATE POLICY "tenant_isolation"' in result.output


def test_sql_filter_by_table(app: Flask) -> None:
    rls = RLS(app)
    rls.register("invoices", TenantPolicy("t1", "tenant_id"))
    rls.register("orders", TenantPolicy("t2", "tenant_id"))
    result = app.test_cli_runner().invoke(args=["rls", "sql", "--table", "orders"])
    assert '"orders"' in result.output
    assert '"invoices"' not in result.output


def test_sql_empty_registry(app: Flask) -> None:
    RLS(app)
    result = app.test_cli_runner().invoke(args=["rls", "sql"])
    assert "No RLS policies registered" in result.output
