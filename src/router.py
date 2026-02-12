"""Source router - detects source type and dispatches to appropriate adapter."""
import logging
from typing import List, Optional, Dict
from .adapters.base import BaseAdapter, SourceContent
from .adapters import BUILTIN_ADAPTERS
from .adapters.web import WebAdapter
from .adapters.web_search import WebSearchAdapter

logger = logging.getLogger(__name__)


class SourceRouter:
    """Routes input sources to the correct adapter."""

    def __init__(
        self,
        extra_adapters: Optional[List[BaseAdapter]] = None,
        search_config: Optional[Dict] = None,
    ):
        self._adapters: List[BaseAdapter] = []
        ssl_verify = search_config.get("ssl_verify", True) if search_config else True
        logger.debug("SourceRouter init: ssl_verify=%s, search_config=%s", ssl_verify, search_config)

        # Register built-in adapters with config
        for cls in BUILTIN_ADAPTERS:
            if cls == WebSearchAdapter and search_config:
                # Inject search config into WebSearchAdapter
                logger.debug("Registering %s with config: %s", cls.__name__, search_config)
                adapter = cls(**search_config)
            elif cls == WebAdapter:
                proxy = search_config.get("proxy", "") if search_config else ""
                adapter = cls(ssl_verify=ssl_verify, proxy=proxy)
            else:
                adapter = cls()
            self._adapters.append(adapter)
            logger.debug("Registered adapter: %s", adapter.name)

        # Register extra adapters (MCP-based, etc.)
        if extra_adapters:
            for adapter in extra_adapters:
                self._adapters.append(adapter)

    def register(self, adapter: BaseAdapter):
        """Dynamically register a new adapter."""
        self._adapters.append(adapter)

    async def extract(self, source: str) -> SourceContent:
        """Auto-detect source type and extract content."""
        logger.debug("Routing source: %s", source)
        for adapter in self._adapters:
            if adapter.can_handle(source):
                logger.debug("Matched adapter: %s for source: %s", adapter.name, source)
                return await adapter.extract(source)

        # Fallback: treat plain text as search query
        # If no adapter matches, assume it's a search query
        if not source.startswith(("http://", "https://", "search:", "/", "C:\\", "D:\\")):
            # Plain text -> convert to search query
            search_source = f"search:{source}"
            for adapter in self._adapters:
                if adapter.can_handle(search_source):
                    return await adapter.extract(search_source)

        raise ValueError(
            f"No adapter found for source: {source}\n"
            f"Available adapters: {[a.name for a in self._adapters]}\n"
            f"Tip: Use 'search:검색어' for web search, or provide a URL/file path"
        )

    async def extract_many(self, sources: List[str]) -> List[SourceContent]:
        """Extract from multiple sources."""
        results = []
        for source in sources:
            content = await self.extract(source)
            results.append(content)
        return results
