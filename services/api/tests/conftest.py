"""Pytest configuration and shared fixtures using PostgreSQL via Docker."""

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from testcontainers.postgres import PostgresContainer

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


# Session-scoped PostgreSQL container (reused across all tests)
@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="function")
def engine(postgres_container) -> Engine:
    """Create a fresh database engine for each test.

    Tables are created fresh for each test to ensure isolation.
    """
    url = postgres_container.get_connection_url()
    eng = create_engine(url)

    # Create all tables
    metadata.create_all(eng)

    yield eng

    # Clean up: drop all tables after test
    metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db_url(postgres_container) -> str:
    """Get the PostgreSQL connection URL."""
    return postgres_container.get_connection_url()
