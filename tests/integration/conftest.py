"""Fixtures for integration tests that require a live PostgreSQL (via Docker)."""

from __future__ import annotations

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url

APP_USER = "app_user"
APP_PW = "app_pw"
OWNER_ROLE = "owner_role"
OWNER_PW = "owner_pw"


@pytest.fixture(scope="session")
def admin_url() -> str:
    """Start a PostgreSQL container and return the superuser connection URL."""
    pytest.importorskip("testcontainers.postgres")
    from testcontainers.postgres import PostgresContainer

    try:
        container = PostgresContainer("postgres:16-alpine", driver="psycopg")
        container.start()
    except Exception as exc:  # pragma: no cover - environment without Docker
        pytest.skip(f"Docker/PostgreSQL not available: {exc}")

    url = container.get_connection_url()
    yield url
    container.stop()


@pytest.fixture(scope="session")
def admin_engine(admin_url: str) -> Engine:
    engine = create_engine(admin_url, future=True)
    yield engine
    engine.dispose()


def _app_url(admin_url: str, user: str, pw: str) -> str:
    return make_url(admin_url).set(username=user, password=pw).render_as_string(
        hide_password=False
    )


@pytest.fixture(scope="session")
def app_engine_factory(admin_url: str):
    """Return a factory that builds an engine for a given role."""
    engines: list[Engine] = []

    def factory(user: str, pw: str) -> Engine:
        engine = create_engine(_app_url(admin_url, user, pw), future=True)
        engines.append(engine)
        return engine

    yield factory
    for engine in engines:
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _roles(admin_engine: Engine) -> None:
    """Create the login roles used by integration tests."""
    with admin_engine.begin() as conn:
        for role, pw in ((APP_USER, APP_PW), (OWNER_ROLE, OWNER_PW)):
            conn.execute(text(f"DROP ROLE IF EXISTS {role}"))
            conn.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{pw}'"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
