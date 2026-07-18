"""Unit tests for the DDL generators."""

from __future__ import annotations

from flask_rls import TenantPolicy
from flask_rls.sql import (
    create_policy,
    disable_rls,
    drop_policy,
    enable_rls,
    force_rls,
    no_force_rls,
)


class TestAlterTable:
    def test_enable(self) -> None:
        assert enable_rls("invoices") == 'ALTER TABLE "invoices" ENABLE ROW LEVEL SECURITY;'

    def test_disable(self) -> None:
        assert disable_rls("invoices") == 'ALTER TABLE "invoices" DISABLE ROW LEVEL SECURITY;'

    def test_force(self) -> None:
        assert force_rls("invoices") == 'ALTER TABLE "invoices" FORCE ROW LEVEL SECURITY;'

    def test_no_force(self) -> None:
        assert no_force_rls("invoices") == 'ALTER TABLE "invoices" NO FORCE ROW LEVEL SECURITY;'

    def test_schema_qualified(self) -> None:
        assert enable_rls("app.invoices") == (
            'ALTER TABLE "app"."invoices" ENABLE ROW LEVEL SECURITY;'
        )


class TestCreatePolicy:
    def test_all_operation_has_using_and_check(self) -> None:
        ddl = create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id"))
        assert ddl.startswith('CREATE POLICY "tenant_isolation" ON "invoices"')
        assert "AS PERMISSIVE" in ddl
        assert "FOR ALL" in ddl
        assert "TO PUBLIC" in ddl
        assert "USING (" in ddl
        assert "WITH CHECK (" in ddl
        assert ddl.endswith(";")

    def test_select_omits_check(self) -> None:
        ddl = create_policy("invoices", TenantPolicy("t", "tenant_id", operation="SELECT"))
        assert "USING (" in ddl
        assert "WITH CHECK" not in ddl

    def test_insert_omits_using(self) -> None:
        ddl = create_policy("invoices", TenantPolicy("t", "tenant_id", operation="INSERT"))
        assert "WITH CHECK (" in ddl
        assert "USING (" not in ddl

    def test_restrictive(self) -> None:
        ddl = create_policy("invoices", TenantPolicy("t", "tenant_id", permissive=False))
        assert "AS RESTRICTIVE" in ddl

    def test_custom_roles(self) -> None:
        ddl = create_policy("invoices", TenantPolicy("t", "tenant_id", roles="app_user"))
        assert "TO app_user" in ddl


class TestDropPolicy:
    def test_drop(self) -> None:
        assert drop_policy("invoices", "tenant_isolation") == (
            'DROP POLICY IF EXISTS "tenant_isolation" ON "invoices";'
        )
