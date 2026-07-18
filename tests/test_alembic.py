"""Unit tests for the Alembic operation directives (registration + reversibility)."""

from __future__ import annotations

import pytest

pytest.importorskip("alembic")

from alembic.operations import Operations  # noqa: E402

from flask_rls import TenantPolicy  # noqa: E402
from flask_rls.alembic import (  # noqa: E402
    AlterPolicyOp,
    CreatePolicyOp,
    DisableRLSOp,
    DropPolicyOp,
    EnableRLSOp,
    ForceRLSOp,
    NoForceRLSOp,
    _alter_policy,
    _create_policy,
    _enable_rls,
)


class FakeOps:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, statement: str) -> None:
        self.executed.append(statement)


class TestRegistration:
    @pytest.mark.parametrize(
        "name",
        ["enable_rls", "disable_rls", "force_rls", "no_force_rls",
         "create_policy", "drop_policy", "alter_policy"],
    )
    def test_operation_registered(self, name: str) -> None:
        assert hasattr(Operations, name)


class TestReverse:
    def test_enable_reverses_to_disable(self) -> None:
        rev = EnableRLSOp("invoices").reverse()
        assert isinstance(rev, DisableRLSOp)
        assert rev.table == "invoices"

    def test_disable_reverses_to_enable(self) -> None:
        assert isinstance(DisableRLSOp("invoices").reverse(), EnableRLSOp)

    def test_force_reverses_to_no_force(self) -> None:
        assert isinstance(ForceRLSOp("invoices").reverse(), NoForceRLSOp)

    def test_create_reverses_to_drop_with_policy(self) -> None:
        policy = TenantPolicy("t", "tenant_id")
        rev = CreatePolicyOp("invoices", policy).reverse()
        assert isinstance(rev, DropPolicyOp)
        assert rev.policy is policy

    def test_drop_without_policy_not_reversible(self) -> None:
        with pytest.raises(NotImplementedError):
            DropPolicyOp("invoices", "t").reverse()

    def test_drop_with_policy_reverses_to_create(self) -> None:
        policy = TenantPolicy("t", "tenant_id")
        rev = DropPolicyOp("invoices", "t", policy=policy).reverse()
        assert isinstance(rev, CreatePolicyOp)


class TestImplementations:
    def test_enable_emits_ddl(self) -> None:
        ops = FakeOps()
        _enable_rls(ops, EnableRLSOp("invoices"))
        assert ops.executed == ['ALTER TABLE "invoices" ENABLE ROW LEVEL SECURITY;']

    def test_create_emits_ddl(self) -> None:
        ops = FakeOps()
        _create_policy(ops, CreatePolicyOp("invoices", TenantPolicy("t", "tenant_id")))
        assert ops.executed[0].startswith('CREATE POLICY "t" ON "invoices"')

    def test_alter_drops_then_creates(self) -> None:
        ops = FakeOps()
        _alter_policy(ops, AlterPolicyOp("invoices", TenantPolicy("t", "tenant_id")))
        assert len(ops.executed) == 2
        assert ops.executed[0].startswith("DROP POLICY")
        assert ops.executed[1].startswith("CREATE POLICY")
