"""Feature flags for domain activation."""

from services.api.src.api.config import settings

# Valid domains
ALL_DOMAINS = ("medical", "sre", "crypto")


def get_active_domains() -> list[str]:
    """Return list of currently active domain names."""
    raw = settings.active_domains
    domains = [d.strip().lower() for d in raw.split(",") if d.strip()]
    return [d for d in domains if d in ALL_DOMAINS]


def is_domain_active(domain: str) -> bool:
    """Check if a specific domain is active."""
    return domain.lower() in get_active_domains()
