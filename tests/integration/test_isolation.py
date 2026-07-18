"""End-to-end RLS isolation tests against a live PostgreSQL.

These prove the guarantees that unit tests cannot: real cross-tenant isolation, fail-closed
behavior, transaction-scoped (non-leaking) context, WITH CHECK enforcement, and the
FORCE/owner-bypass gotcha.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from flask_rls import RLS, TenantPolicy
from flask_rls.sql import create_policy, enable_rls, force_rls

pytestmark = pytest.mark.integration

# Login roles created by the integration conftest (kept in sync with conftest.py).
APP_USER = "app_user"
APP_PW = "app_pw"
OWNER_ROLE = "owner_role"
OWNER_PW = "owner_pw"


def _bodies(engine: Engine, sql: str = "SELECT body FROM notes") -> list[str]:
    with engine.connect() as conn:
        return sorted(row[0] for row in conn.execute(text(sql)))


@pytest.fixture
def notes(admin_engine: Engine, app_engine_factory):
    """A tenant-isolated ``notes`` table queried by the non-owner ``app_user``."""
    with admin_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS notes"))
        conn.execute(
            text(
                "CREATE TABLE notes (id serial PRIMARY KEY, "
                "tenant_id text NOT NULL, body text)"
            )
        )
        conn.execute(
            text("INSERT INTO notes (tenant_id, body) VALUES "
                 "('a','a1'), ('a','a2'), ('b','b1')")
        )
        conn.execute(text(enable_rls("notes")))
        conn.execute(text(force_rls("notes")))
        conn.execute(text(create_policy("notes", TenantPolicy("tenant_isolation", "tenant_id"))))
        conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON notes TO {APP_USER}"))
        conn.execute(
            text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_USER}")
        )

    engine = app_engine_factory(APP_USER, APP_PW)
    rls = RLS()
    rls.bind_engine(engine)
    yield engine, rls

    with admin_engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS notes"))


class TestIsolation:
    def test_tenant_a_sees_only_a(self, notes) -> None:
        engine, rls = notes
        with rls.override(tenant_id="a"):
            assert _bodies(engine) == ["a1", "a2"]

    def test_tenant_b_sees_only_b(self, notes) -> None:
        engine, rls = notes
        with rls.override(tenant_id="b"):
            assert _bodies(engine) == ["b1"]

    def test_no_context_fails_closed(self, notes) -> None:
        engine, rls = notes
        assert _bodies(engine) == []

    def test_bypass_sees_nothing(self, notes) -> None:
        engine, rls = notes
        with rls.bypass():
            assert _bodies(engine) == []

    def test_nested_override_switches_tenant(self, notes) -> None:
        engine, rls = notes
        with rls.override(tenant_id="a"):
            with rls.override(tenant_id="b"):
                assert _bodies(engine) == ["b1"]


class TestTransactionScope:
    def test_context_does_not_leak_across_transactions(self, notes) -> None:
        """A committed override must not bleed into the next txn on the same connection."""
        engine, rls = notes
        with engine.connect() as conn:
            with rls.override(tenant_id="a"):
                first = conn.execute(text("SELECT count(*) FROM notes")).scalar()
                conn.commit()
            second = conn.execute(text("SELECT count(*) FROM notes")).scalar()
            conn.commit()
        assert first == 2
        assert second == 0  # is_local=true was discarded at commit


class TestWithCheck:
    def test_insert_matching_tenant_ok(self, notes) -> None:
        engine, rls = notes
        with rls.override(tenant_id="a"):
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO notes (tenant_id, body) VALUES ('a','a3')"))
            assert _bodies(engine) == ["a1", "a2", "a3"]

    def test_insert_foreign_tenant_rejected(self, notes) -> None:
        engine, rls = notes
        with rls.override(tenant_id="a"):
            with pytest.raises(DBAPIError):
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO notes (tenant_id, body) VALUES ('b','x')"))


class TestForceOwnerBypass:
    """FORCE ROW LEVEL SECURITY is what subjects the table owner to RLS."""

    @pytest.fixture
    def owner_tables(self, admin_engine: Engine, app_engine_factory):
        with admin_engine.begin() as conn:
            for table in ("forced", "unforced"):
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.execute(
                    text(
                        f"CREATE TABLE {table} (id serial PRIMARY KEY, "
                        "tenant_id text NOT NULL, body text)"
                    )
                )
                conn.execute(
                    text(f"INSERT INTO {table} (tenant_id, body) VALUES ('a','a1'), ('b','b1')")
                )
                conn.execute(text(enable_rls(table)))
                conn.execute(text(create_policy(table, TenantPolicy("iso", "tenant_id"))))
                conn.execute(text(f"ALTER TABLE {table} OWNER TO {OWNER_ROLE}"))
            conn.execute(text(force_rls("forced")))  # only 'forced' is FORCEd

        engine = app_engine_factory(OWNER_ROLE, OWNER_PW)
        rls = RLS()
        rls.bind_engine(engine)
        yield engine, rls

        with admin_engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS forced"))
            conn.execute(text("DROP TABLE IF EXISTS unforced"))

    def test_force_applies_rls_to_owner(self, owner_tables) -> None:
        engine, rls = owner_tables
        with rls.override(tenant_id="a"):
            assert _bodies(engine, "SELECT body FROM forced") == ["a1"]

    def test_without_force_owner_bypasses_rls(self, owner_tables) -> None:
        engine, rls = owner_tables
        with rls.override(tenant_id="a"):
            # owner sees ALL rows — this is exactly why flask-rls emits FORCE
            assert _bodies(engine, "SELECT body FROM unforced") == ["a1", "b1"]
