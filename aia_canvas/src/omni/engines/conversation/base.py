"""
Abstract Base LLM Provider Interface
"""

import abc
from dataclasses import asdict, dataclass
from typing import Any, AsyncIterator, Dict


@dataclass
class ProviderMetadata:
    id: str = "gemini_flash"
    display_name: str = "3.7 Flash"
    accent_color: str = "#38BDF8"
    icon_glyph: str = "✦"
    icon_path: str = "aia_canvas/assets/icons/providers/gemini.svg"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class BaseLLMProvider(abc.ABC):
    """Abstract base class defining the contract for LLM streaming providers."""

    @property
    def metadata(self) -> ProviderMetadata:
        """Return provider metadata configuration."""
        return ProviderMetadata()

    @abc.abstractmethod
    async def stream_chat(
        self, prompt: str, context: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Asynchronously stream chat response tokens/chunks.

        Args:
            prompt: Cleaned prompt query string.
            context: Context dictionary containing session history, node focus, etc.

        Yields:
            str: Token chunks from the provider response stream.
        """
        pass

    @abc.abstractmethod
    def validate_credentials(self) -> bool:
        """Validate if required API keys or credentials are available.

        Returns:
            bool: True if credentials are valid and present, False otherwise.
        """
        pass
