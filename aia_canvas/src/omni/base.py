"""
OmniEngine Base Classes and OmniResult Data Schema
"""

import abc
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Union

from .context import OmniContext


@dataclass
class OmniResult:
    id: str
    title: str
    category: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""


class OmniEngine(abc.ABC):
    @abc.abstractmethod
    def can_handle(self, query: str, context: OmniContext) -> float:
        """Evaluate affinity score (0.0 to 1.0) for query and context."""
        pass

    @abc.abstractmethod
    async def execute(
        self, query: str, context: OmniContext
    ) -> Union[AsyncIterator[OmniResult], List[OmniResult]]:
        """Asynchronously yield or return OmniResult items."""
        pass

    @abc.abstractmethod
    def get_mode_metadata(self) -> Dict[str, Any]:
        """Return visual mode config dictionary (e.g. glow_color, icon, placeholder)."""
        pass
