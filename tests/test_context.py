"""Unit tests for context resolution, override, and bypass."""

from __future__ import annotations

from flask_rls.context import (
    bypass_scope,
    is_bypass,
    override_scope,
    resolve_context,
)


def provider(**values):
    return lambda: dict(values)


class TestResolution:
    def test_providers_merge_in_order(self) -> None:
        providers = [provider(tenant_id=1), provider(user_id=2, tenant_id=9)]
        values, is_bp = resolve_context(providers)
        assert is_bp is False
        # later provider wins for tenant_id
        assert values == {"tenant_id": "9", "user_id": "2"}

    def test_empty_and_none_values_dropped(self) -> None:
        values, _ = resolve_context([provider(tenant_id=None, user_id="", ip="1.2.3.4")])
        assert values == {"ip": "1.2.3.4"}

    def test_values_are_stringified(self) -> None:
        values, _ = resolve_context([provider(tenant_id=42)])
        assert values["tenant_id"] == "42"


class TestOverride:
    def test_override_beats_providers(self) -> None:
        providers = [provider(tenant_id=1)]
        with override_scope(tenant_id=99):
            values, _ = resolve_context(providers)
            assert values["tenant_id"] == "99"

    def test_override_restored_on_exit(self) -> None:
        providers = [provider(tenant_id=1)]
        with override_scope(tenant_id=99):
            pass
        values, _ = resolve_context(providers)
        assert values["tenant_id"] == "1"

    def test_nested_override_accumulates(self) -> None:
        with override_scope(tenant_id=1):
            with override_scope(user_id=2):
                values, _ = resolve_context([])
                assert values == {"tenant_id": "1", "user_id": "2"}


class TestBypass:
    def test_bypass_emits_nothing(self) -> None:
        providers = [provider(tenant_id=1)]
        with bypass_scope():
            assert is_bypass() is True
            values, is_bp = resolve_context(providers)
            assert is_bp is True
            assert values == {}

    def test_bypass_restored_on_exit(self) -> None:
        with bypass_scope():
            pass
        assert is_bypass() is False
