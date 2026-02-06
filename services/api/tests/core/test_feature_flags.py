"""Tests for feature flags."""

from services.api.src.api.core.feature_flags import (
    ALL_DOMAINS,
    get_active_domains,
    is_domain_active,
)


def test_all_domains_defined():
    assert "medical" in ALL_DOMAINS
    assert "sre" in ALL_DOMAINS
    assert "crypto" in ALL_DOMAINS


def test_default_active_domains():
    domains = get_active_domains()
    assert "medical" in domains


def test_is_domain_active_medical():
    assert is_domain_active("medical") is True


def test_is_domain_active_sre():
    # SRE is not active by default
    assert is_domain_active("sre") is False


def test_is_domain_active_crypto():
    # Crypto is not active by default
    assert is_domain_active("crypto") is False
