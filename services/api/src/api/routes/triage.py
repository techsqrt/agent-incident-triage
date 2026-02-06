"""Triage API endpoints — stub for M1, implemented in M4."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/domains")
def list_domains() -> dict:
    """List all domains and their active status."""
    from services.api.src.api.core.feature_flags import ALL_DOMAINS, is_domain_active

    domains = []
    for domain in ALL_DOMAINS:
        domains.append({
            "name": domain,
            "active": is_domain_active(domain),
        })
    return {"domains": domains}
