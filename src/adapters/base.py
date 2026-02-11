"""Base adapter interface for source plugins."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceContent:
    """Extracted content from any source."""
    text: str
    title: str = ""
    source_url: str = ""
    source_type: str = ""  # web, youtube, gdrive, sharepoint, local, notion
    metadata: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """All source adapters implement this interface."""

    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Return True if this adapter can handle the given source string."""
        ...

    @abstractmethod
    async def extract(self, source: str) -> SourceContent:
        """Extract text content from the source."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name for logging/config."""
        ...
