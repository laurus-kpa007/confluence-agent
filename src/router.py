"""Source router - detects source type and dispatches to appropriate adapter."""
from typing import List, Optional
from .adapters.base import BaseAdapter, SourceContent
from .adapters import BUILTIN_ADAPTERS


class SourceRouter:
    """Routes input sources to the correct adapter."""

    def __init__(self, extra_adapters: Optional[List[BaseAdapter]] = None):
        self._adapters: List[BaseAdapter] = []

        # Register built-in adapters
        for cls in BUILTIN_ADAPTERS:
            self._adapters.append(cls())

        # Register extra adapters (MCP-based, etc.)
        if extra_adapters:
            for adapter in extra_adapters:
                self._adapters.append(adapter)

    def register(self, adapter: BaseAdapter):
        """Dynamically register a new adapter."""
        self._adapters.append(adapter)

    async def extract(self, source: str) -> SourceContent:
        """Auto-detect source type and extract content."""
        for adapter in self._adapters:
            if adapter.can_handle(source):
                return await adapter.extract(source)

        raise ValueError(
            f"No adapter found for source: {source}\n"
            f"Available adapters: {[a.name for a in self._adapters]}"
        )

    async def extract_many(self, sources: List[str]) -> List[SourceContent]:
        """Extract from multiple sources."""
        results = []
        for source in sources:
            content = await self.extract(source)
            results.append(content)
        return results
