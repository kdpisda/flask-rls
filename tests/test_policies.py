"""Unit tests for policy classes and their generated predicates."""

from __future__ import annotations

import pytest
from sqlalchemy import column, true

from flask_rls import (
    RLS,
    CustomPolicy,
    ExpressionPolicy,
    TenantPolicy,
    UserPolicy,
)
from flask_rls.exceptions import PolicyError


class TestTenantPolicy:
    def test_default_cast_is_text(self) -> None:
        p = TenantPolicy("t", "tenant_id")
        assert p.get_sql_expression() == (
            "tenant_id = (SELECT NULLIF(current_setting('rls.tenant_id', true), '')::text)"
        )

    def test_configurable_cast(self) -> None:
        p = TenantPolicy("t", "tenant_id", cast="uuid")
        assert "::uuid)" in p.get_sql_expression()

    def test_invalid_field_rejected(self) -> None:
        with pytest.raises(PolicyError):
            TenantPolicy("t", "tenant_id; DROP TABLE x")


class TestUserPolicy:
    def test_default_field_and_guc(self) -> None:
        p = UserPolicy("u")
        assert p.get_sql_expression() == (
            "user_id = (SELECT NULLIF(current_setting('rls.user_id', true), '')::text)"
        )


class TestOperationClauses:
    """USING/WITH CHECK must only appear for the operations PostgreSQL allows."""

    def test_all_has_both(self) -> None:
        p = TenantPolicy("t", "tenant_id", operation="ALL")
        assert p.get_using_expression() is not None
        assert p.get_check_expression() is not None

    def test_select_has_using_only(self) -> None:
        p = TenantPolicy("t", "tenant_id", operation="SELECT")
        assert p.get_using_expression() is not None
        assert p.get_check_expression() is None

    def test_insert_has_check_only(self) -> None:
        p = TenantPolicy("t", "tenant_id", operation="INSERT")
        assert p.get_using_expression() is None
        assert p.get_check_expression() is not None

    def test_delete_has_using_only(self) -> None:
        p = TenantPolicy("t", "tenant_id", operation="DELETE")
        assert p.get_using_expression() is not None
        assert p.get_check_expression() is None


class TestCustomPolicy:
    def test_plain_expression(self) -> None:
        p = CustomPolicy("c", "owner_id = 1")
        assert p.get_sql_expression() == "owner_id = 1"

    @pytest.mark.parametrize(
        "expr",
        ["1=1; DROP TABLE users", "x = 1 -- comment", "DELETE FROM t", "a /* c */ = 1"],
    )
    def test_forbidden_sql_rejected(self, expr: str) -> None:
        with pytest.raises(PolicyError):
            CustomPolicy("c", expr)

    def test_empty_rejected(self) -> None:
        with pytest.raises(PolicyError):
            CustomPolicy("c", "   ")


class TestExpressionPolicy:
    def test_owner_or_public(self) -> None:
        p = ExpressionPolicy(
            "p",
            (column("owner_id") == RLS.user_id()) | (column("is_public") == true()),
        )
        sql = p.get_sql_expression()
        assert "owner_id = (SELECT NULLIF(current_setting('rls.user_id', true), '')::text)" in sql
        assert "is_public = true" in sql
        assert " OR " in sql

    def test_tenant_ref_with_cast(self) -> None:
        p = ExpressionPolicy("p", column("tenant_id") == RLS.tenant_id(cast="uuid"))
        assert "::uuid)" in p.get_sql_expression()

    def test_requires_sqlalchemy_expression(self) -> None:
        with pytest.raises(PolicyError):
            ExpressionPolicy("p", "owner_id = 1")  # type: ignore[arg-type]


class TestPolicyValidation:
    def test_bad_name(self) -> None:
        with pytest.raises(PolicyError):
            TenantPolicy("bad name", "tenant_id")

    def test_bad_roles(self) -> None:
        with pytest.raises(PolicyError):
            TenantPolicy("t", "tenant_id", roles="app-user")

    def test_permissive_flag(self) -> None:
        assert TenantPolicy("t", "tenant_id").permissive is True
        assert TenantPolicy("t", "tenant_id", permissive=False).permissive is False
