"""Alembic migration operations for RLS.

Import this module in your Alembic ``env.py`` to register the operations, then use them in
migrations::

    from flask_rls.alembic import *  # noqa: F401,F403  (registers op.enable_rls, ...)

    def upgrade():
        op.enable_rls("invoices")
        op.force_rls("invoices")
        op.create_policy("invoices", TenantPolicy("tenant_isolation", "tenant_id"))

Requires the ``flask-rls[alembic]`` extra.
"""

from __future__ import annotations

from typing import Any

try:
    from alembic.operations import MigrateOperation, Operations
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "flask_rls.alembic requires Alembic. Install with: pip install 'flask-rls[alembic]'"
    ) from exc

from flask_rls import sql
from flask_rls.policies import BasePolicy

__all__ = [
    "EnableRLSOp",
    "DisableRLSOp",
    "ForceRLSOp",
    "NoForceRLSOp",
    "CreatePolicyOp",
    "DropPolicyOp",
    "AlterPolicyOp",
]


@Operations.register_operation("enable_rls")
class EnableRLSOp(MigrateOperation):
    """Enable RLS on a table."""

    def __init__(self, table: str) -> None:
        self.table = table

    @classmethod
    def enable_rls(cls, operations: Operations, table: str) -> Any:
        return operations.invoke(cls(table))

    def reverse(self) -> DisableRLSOp:
        return DisableRLSOp(self.table)


@Operations.register_operation("disable_rls")
class DisableRLSOp(MigrateOperation):
    """Disable RLS on a table."""

    def __init__(self, table: str) -> None:
        self.table = table

    @classmethod
    def disable_rls(cls, operations: Operations, table: str) -> Any:
        return operations.invoke(cls(table))

    def reverse(self) -> EnableRLSOp:
        return EnableRLSOp(self.table)


@Operations.register_operation("force_rls")
class ForceRLSOp(MigrateOperation):
    """Force RLS so the table owner is also subject to policies."""

    def __init__(self, table: str) -> None:
        self.table = table

    @classmethod
    def force_rls(cls, operations: Operations, table: str) -> Any:
        return operations.invoke(cls(table))

    def reverse(self) -> NoForceRLSOp:
        return NoForceRLSOp(self.table)


@Operations.register_operation("no_force_rls")
class NoForceRLSOp(MigrateOperation):
    """Stop forcing RLS on the table owner (reverse of :class:`ForceRLSOp`)."""

    def __init__(self, table: str) -> None:
        self.table = table

    @classmethod
    def no_force_rls(cls, operations: Operations, table: str) -> Any:
        return operations.invoke(cls(table))

    def reverse(self) -> ForceRLSOp:
        return ForceRLSOp(self.table)


@Operations.register_operation("create_policy")
class CreatePolicyOp(MigrateOperation):
    """Create an RLS policy on a table."""

    def __init__(self, table: str, policy: BasePolicy) -> None:
        self.table = table
        self.policy = policy

    @classmethod
    def create_policy(cls, operations: Operations, table: str, policy: BasePolicy) -> Any:
        return operations.invoke(cls(table, policy))

    def reverse(self) -> DropPolicyOp:
        return DropPolicyOp(self.table, self.policy.name, policy=self.policy)


@Operations.register_operation("drop_policy")
class DropPolicyOp(MigrateOperation):
    """Drop an RLS policy from a table.

    ``policy`` may be supplied to make the operation reversible (recreate on downgrade).
    """

    def __init__(
        self, table: str, policy_name: str, policy: BasePolicy | None = None
    ) -> None:
        self.table = table
        self.policy_name = policy_name
        self.policy = policy

    @classmethod
    def drop_policy(
        cls,
        operations: Operations,
        table: str,
        policy_name: str,
        policy: BasePolicy | None = None,
    ) -> Any:
        return operations.invoke(cls(table, policy_name, policy=policy))

    def reverse(self) -> CreatePolicyOp:
        if self.policy is None:
            raise NotImplementedError(
                "drop_policy is only reversible when the original policy is supplied via "
                "policy=."
            )
        return CreatePolicyOp(self.table, self.policy)


@Operations.register_operation("alter_policy")
class AlterPolicyOp(MigrateOperation):
    """Alter a policy by dropping and recreating it (portable across PG versions)."""

    def __init__(self, table: str, policy: BasePolicy) -> None:
        self.table = table
        self.policy = policy

    @classmethod
    def alter_policy(cls, operations: Operations, table: str, policy: BasePolicy) -> Any:
        return operations.invoke(cls(table, policy))

    def reverse(self) -> AlterPolicyOp:
        raise NotImplementedError(
            "alter_policy reversal requires the prior policy definition; write an explicit "
            "downgrade."
        )


@Operations.implementation_for(EnableRLSOp)
def _enable_rls(operations: Operations, operation: EnableRLSOp) -> None:
    operations.execute(sql.enable_rls(operation.table))


@Operations.implementation_for(DisableRLSOp)
def _disable_rls(operations: Operations, operation: DisableRLSOp) -> None:
    operations.execute(sql.disable_rls(operation.table))


@Operations.implementation_for(ForceRLSOp)
def _force_rls(operations: Operations, operation: ForceRLSOp) -> None:
    operations.execute(sql.force_rls(operation.table))


@Operations.implementation_for(NoForceRLSOp)
def _no_force_rls(operations: Operations, operation: NoForceRLSOp) -> None:
    operations.execute(sql.no_force_rls(operation.table))


@Operations.implementation_for(CreatePolicyOp)
def _create_policy(operations: Operations, operation: CreatePolicyOp) -> None:
    operations.execute(sql.create_policy(operation.table, operation.policy))


@Operations.implementation_for(DropPolicyOp)
def _drop_policy(operations: Operations, operation: DropPolicyOp) -> None:
    operations.execute(sql.drop_policy(operation.table, operation.policy_name))


@Operations.implementation_for(AlterPolicyOp)
def _alter_policy(operations: Operations, operation: AlterPolicyOp) -> None:
    operations.execute(sql.drop_policy(operation.table, operation.policy.name))
    operations.execute(sql.create_policy(operation.table, operation.policy))
