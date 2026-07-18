"""A registry of policies by table, and the DDL to realize them.

Used by the CLI (``flask rls sql``) and available to applications that want to declare
policies centrally. It is the source for generated DDL; it does not talk to the database
itself.
"""

from __future__ import annotations

from collections.abc import Iterator

from flask_rls import sql
from flask_rls.policies import BasePolicy
from flask_rls.validation import validate_table_name


class _TableEntry:
    __slots__ = ("policies", "force")

    def __init__(self, force: bool) -> None:
        self.policies: list[BasePolicy] = []
        self.force = force


class PolicyRegistry:
    """Maps table names to the policies declared for them."""

    def __init__(self) -> None:
        self._tables: dict[str, _TableEntry] = {}

    def register(self, table: str, *policies: BasePolicy, force: bool = True) -> None:
        """Register one or more policies for ``table``.

        ``force`` (default ``True``) emits ``FORCE ROW LEVEL SECURITY`` so the table owner
        is subject to RLS too — closing the owner-bypass gap.
        """
        validate_table_name(table)
        for policy in policies:
            if not isinstance(policy, BasePolicy):
                raise TypeError(f"Expected a BasePolicy, got {type(policy)!r}")
        entry = self._tables.setdefault(table, _TableEntry(force))
        entry.force = force
        entry.policies.extend(policies)

    def tables(self) -> list[str]:
        """Return the registered table names in insertion order."""
        return list(self._tables)

    def policies_for(self, table: str) -> list[BasePolicy]:
        """Return the policies registered for ``table``."""
        entry = self._tables.get(table)
        return list(entry.policies) if entry else []

    def ddl(self, table: str | None = None) -> Iterator[str]:
        """Yield the DDL statements (enable, force, create policy) for one or all tables."""
        names = [table] if table is not None else self.tables()
        for name in names:
            entry = self._tables.get(name)
            if entry is None:
                continue
            yield sql.enable_rls(name)
            if entry.force:
                yield sql.force_rls(name)
            for policy in entry.policies:
                yield sql.create_policy(name, policy)
