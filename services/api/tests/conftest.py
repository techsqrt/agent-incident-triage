"""Pytest configuration and shared fixtures.

Unit tests use mocks (fast).
Integration tests use real PostgreSQL via testcontainers (slow, marked).
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from services.api.src.api.db.models import metadata


def pytest_configure(config):
    """Configure test environment before collection."""
    os.environ.setdefault("RUN_MIGRATIONS", "false")
    os.environ.setdefault("RECAPTCHA_SECRET_KEY", "")

    # Register integration marker
    config.addinivalue_line(
        "markers", "integration: tests that require real PostgreSQL (slow)"
    )


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


# =============================================================================
# UNIT TEST FIXTURES (fast, use mocks)
# =============================================================================

@pytest.fixture
def mock_engine():
    """Mock database engine for unit tests."""
    return MagicMock()


@pytest.fixture
def mock_incident_repo():
    """Mock incident repository for unit tests."""
    from unittest.mock import MagicMock
    repo = MagicMock()
    repo.create.return_value = {
        "id": "test-incident-id",
        "domain": "medical",
        "status": "OPEN",
        "mode": "chat",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "ts_escalated": None,
        "diagnostic": {},
        "history": {"interactions": []},
    }
    repo.get.return_value = repo.create.return_value
    return repo


# =============================================================================
# INTEGRATION TEST FIXTURES (slow, real PostgreSQL)
# =============================================================================

@pytest.fixture(scope="session")
def postgres_container():
    """Create a PostgreSQL container for integration tests.

    Only created if integration tests are being run.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture
def pg_engine(postgres_container):
    """Create a fresh PostgreSQL engine for each integration test."""
    from sqlalchemy import create_engine

    url = postgres_container.get_connection_url()
    eng = create_engine(url)

    # Create all tables
    metadata.create_all(eng)

    yield eng

    # Clean up
    metadata.drop_all(eng)
    eng.dispose()
