"""Pytest configuration and shared fixtures."""

import os
from unittest.mock import patch

import pytest


def pytest_configure(config):
    """Configure test environment before collection."""
    # Patch env vars before any test modules are imported
    os.environ.setdefault("RUN_MIGRATIONS", "false")
    os.environ.setdefault("RECAPTCHA_SECRET_KEY", "")


@pytest.fixture(scope="session", autouse=True)
def disable_recaptcha_for_tests():
    """Disable reCAPTCHA verification for all tests."""
    with patch.dict(os.environ, {"RECAPTCHA_SECRET_KEY": ""}):
        # Also patch the settings object if already loaded
        try:
            from services.api.src.api.config import settings
            original = settings.recaptcha_secret_key
            settings.recaptcha_secret_key = ""
            yield
            settings.recaptcha_secret_key = original
        except ImportError:
            yield
