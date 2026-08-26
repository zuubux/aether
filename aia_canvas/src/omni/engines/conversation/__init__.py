"""
Conversation Engine Package
Modular LLM Provider Interface and Gemini Streaming Adapter
"""

from .base import BaseLLMProvider, ProviderMetadata
from .engine import ConversationEngine
from .gemini import GeminiProvider
from .persona import AETHER_SYSTEM_INSTRUCTION

__all__ = [
    "BaseLLMProvider",
    "ProviderMetadata",
    "GeminiProvider",
    "ConversationEngine",
    "AETHER_SYSTEM_INSTRUCTION",
]

