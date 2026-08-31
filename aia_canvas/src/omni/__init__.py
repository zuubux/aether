"""
Aether Canvas Omni Package
Provides OmniContext, SpatialContext, OmniResult, OmniEngine, OmniRouter and built-in engines.
"""

from .models import SpatialContext
from .context import (
    AetherContextBuilder,
    OmniContext,
    assemble_spatial_context,
    format_spatial_envelope,
)
from .base import OmniResult, OmniEngine
from .router import OmniRouter
from .engines import (
    FuzzySearchEngine,
    ShellEngine,
    LLMEngine,
    ConversationEngine,
    BaseLLMProvider,
    ProviderMetadata,
    GeminiProvider,
)

__all__ = [
    "AetherContextBuilder",
    "SpatialContext",
    "OmniContext",
    "assemble_spatial_context",
    "format_spatial_envelope",
    "OmniResult",
    "OmniEngine",
    "OmniRouter",
    "FuzzySearchEngine",
    "ShellEngine",
    "LLMEngine",
    "ConversationEngine",
    "BaseLLMProvider",
    "ProviderMetadata",
    "GeminiProvider",
]

