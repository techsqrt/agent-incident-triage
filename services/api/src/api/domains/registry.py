"""Domain module registry.

Central registry for all domain modules. The core pipeline uses this
to get the appropriate module for a given domain key.
"""

from typing import TYPE_CHECKING

from services.api.src.api.core.feature_flags import is_domain_active

if TYPE_CHECKING:
    from services.api.src.api.domains.base import DomainModule


class DomainNotFoundError(Exception):
    """Raised when a domain key is not found in the registry."""

    pass


class DomainInactiveError(Exception):
    """Raised when trying to use an inactive domain."""

    pass


class DomainRegistry:
    """Registry of all available domain modules.

    Usage:
        module = DomainRegistry.get("medical")
        module = DomainRegistry.get("sre", allow_inactive=True)
    """

    _modules: dict[str, "DomainModule"] = {}

    @classmethod
    def register(cls, module: "DomainModule") -> None:
        """Register a domain module."""
        cls._modules[module.domain_key] = module

    @classmethod
    def get(cls, domain_key: str, allow_inactive: bool = False) -> "DomainModule":
        """Get a domain module by key.

        Args:
            domain_key: The domain identifier (e.g., 'medical')
            allow_inactive: If True, return module even if domain is inactive

        Returns:
            The domain module

        Raises:
            DomainNotFoundError: If domain key is not registered
            DomainInactiveError: If domain is inactive and allow_inactive=False
        """
        if domain_key not in cls._modules:
            raise DomainNotFoundError(f"Domain '{domain_key}' not found in registry")

        if not allow_inactive and not is_domain_active(domain_key):
            raise DomainInactiveError(f"Domain '{domain_key}' is not active")

        return cls._modules[domain_key]

    @classmethod
    def get_all(cls, include_inactive: bool = False) -> list["DomainModule"]:
        """Get all registered domain modules.

        Args:
            include_inactive: If True, include inactive domains

        Returns:
            List of domain modules
        """
        if include_inactive:
            return list(cls._modules.values())

        return [m for m in cls._modules.values() if is_domain_active(m.domain_key)]

    @classmethod
    def list_keys(cls, include_inactive: bool = False) -> list[str]:
        """Get all registered domain keys.

        Args:
            include_inactive: If True, include inactive domains

        Returns:
            List of domain keys
        """
        if include_inactive:
            return list(cls._modules.keys())

        return [k for k in cls._modules.keys() if is_domain_active(k)]

    @classmethod
    def is_registered(cls, domain_key: str) -> bool:
        """Check if a domain is registered."""
        return domain_key in cls._modules

    @classmethod
    def clear(cls) -> None:
        """Clear all registered modules. Mainly for testing."""
        cls._modules.clear()
