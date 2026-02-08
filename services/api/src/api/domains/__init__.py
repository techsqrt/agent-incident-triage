"""Domain modules package.

Registers all available domain modules with the central registry.
"""

from services.api.src.api.domains.crypto.module import crypto_module
from services.api.src.api.domains.medical.module import medical_module
from services.api.src.api.domains.registry import DomainRegistry
from services.api.src.api.domains.sre.module import sre_module

# Register all domain modules
DomainRegistry.register(medical_module)
DomainRegistry.register(sre_module)
DomainRegistry.register(crypto_module)

__all__ = ["DomainRegistry"]
