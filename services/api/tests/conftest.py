"""Pytest configuration and shared fixtures.

All tests use PostgreSQL via testcontainers (Docker-based).
The container is session-scoped for performance.
"""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from services.api.src.api.db.models import metadata


def pytest_configure(config):
    """Configure test environment before collection."""
    os.environ.setdefault("RUN_MIGRATIONS", "false")
    os.environ.setdefault("RECAPTCHA_SECRET_KEY", "")


@pytest.fixture(scope="session", autouse=True)
def disable_recaptcha_for_tests():
    """Disable reCAPTCHA verification for all tests."""
    with patch.dict(os.environ, {"RECAPTCHA_SECRET_KEY": ""}):
        try:
            from services.api.src.api.config import settings
            original = settings.recaptcha_secret_key
            settings.recaptcha_secret_key = ""
            yield
            settings.recaptcha_secret_key = original
        except ImportError:
            yield


# ---------------------------------------------------------------------------
# PostgreSQL fixtures (testcontainers)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container (session-scoped for performance).

    Starts once, reused by all tests. Requires Docker.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def session_engine(postgres_container):
    """Session-scoped engine for table creation."""
    url = postgres_container.get_connection_url()
    eng = create_engine(url)
    metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def engine(session_engine):
    """Function-scoped engine that cleans tables between tests.

    Uses the session-scoped container but truncates tables for isolation.
    """
    # Clean all data before each test
    with session_engine.connect() as conn:
        for table in reversed(metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()

    yield session_engine


# Alias for integration tests
@pytest.fixture
def pg_engine(engine):
    """Alias for integration tests."""
    return engine
