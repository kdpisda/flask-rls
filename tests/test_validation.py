"""Unit tests for identifier validation and SQL fragment builders."""

from __future__ import annotations

import pytest

from flask_rls.exceptions import PolicyError
from flask_rls.validation import (
    current_setting_sql,
    quote_identifier,
    roles_to_sql,
    validate_cast,
    validate_field_name,
    validate_guc,
    validate_operation,
    validate_roles,
    validate_table_name,
)


class TestIdentifiers:
    def test_valid_field(self) -> None:
        assert validate_field_name("tenant_id") == "tenant_id"

    @pytest.mark.parametrize("bad", ["1col", "col-name", "col;drop", "", "a b", "a'b"])
    def test_invalid_field(self, bad: str) -> None:
        with pytest.raises(PolicyError):
            validate_field_name(bad)

    def test_table_schema_qualified(self) -> None:
        assert validate_table_name("public.invoices") == "public.invoices"

    def test_table_too_many_parts(self) -> None:
        with pytest.raises(PolicyError):
            validate_table_name("db.public.invoices")

    def test_quote_identifier(self) -> None:
        assert quote_identifier("invoices") == '"invoices"'
        assert quote_identifier("public.invoices") == '"public"."invoices"'

    def test_quote_rejects_injection(self) -> None:
        with pytest.raises(PolicyError):
            quote_identifier('invoices"; DROP TABLE users; --')


class TestOperation:
    @pytest.mark.parametrize("op", ["all", "SELECT", "insert", "Update", "DELETE"])
    def test_valid_normalized_to_upper(self, op: str) -> None:
        assert validate_operation(op) == op.upper()

    def test_invalid(self) -> None:
        with pytest.raises(PolicyError):
            validate_operation("TRUNCATE")


class TestRoles:
    def test_public(self) -> None:
        assert roles_to_sql("public") == "PUBLIC"
        assert roles_to_sql("PUBLIC") == "PUBLIC"

    def test_list(self) -> None:
        assert roles_to_sql("app_user, reporting") == "app_user, reporting"

    @pytest.mark.parametrize("bad", ["", "app-user", "app_user; DROP", "1role"])
    def test_invalid(self, bad: str) -> None:
        with pytest.raises(PolicyError):
            validate_roles(bad)


class TestGucAndCast:
    def test_valid_guc(self) -> None:
        assert validate_guc("rls.tenant_id") == "rls.tenant_id"

    @pytest.mark.parametrize("bad", ["tenant_id", "rls.", "a.b.c", "rls.x;y"])
    def test_invalid_guc(self, bad: str) -> None:
        with pytest.raises(PolicyError):
            validate_guc(bad)

    @pytest.mark.parametrize(
        "good", ["text", "uuid", "bigint", "double precision", "varchar(50)", "int[]"]
    )
    def test_valid_cast(self, good: str) -> None:
        assert validate_cast(good) == good

    @pytest.mark.parametrize("bad", ["text;drop", "uuid'", "", "1type"])
    def test_invalid_cast(self, bad: str) -> None:
        with pytest.raises(PolicyError):
            validate_cast(bad)


class TestCurrentSetting:
    def test_shape(self) -> None:
        assert current_setting_sql("rls.tenant_id", "uuid") == (
            "(SELECT NULLIF(current_setting('rls.tenant_id', true), '')::uuid)"
        )
