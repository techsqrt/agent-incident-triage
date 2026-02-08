"""Domain modules package.

Registers all available domain modules with the central registry.
"""

from services.api.src.api.domains.medical.module import medical_module
from services.api.src.api.domains.registry import DomainRegistry

# Register all domain modules
DomainRegistry.register(medical_module)

__all__ = ["DomainRegistry"]
