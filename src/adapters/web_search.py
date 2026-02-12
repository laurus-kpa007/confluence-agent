"""Web search + scrape adapter. 

Searches the web for a query, then scrapes top results.
Input format: "search:검색어" or "search:AI agent framework"
"""
import re
from typing import List
from .base import BaseAdapter, SourceContent
from .web import WebAdapter


class WebSearchAdapter(BaseAdapter):
    name = "web_search"

    _PREFIX = "search:"

    def __init__(self, provider: str = "google", api_key: str = "", cx_id: str = "", max_results: int = 3, ssl_verify: bool = True):
        self.provider = provider  # google, brave, duckduckgo
        self.api_key = api_key
        self.cx_id = cx_id  # Google Custom Search Engine ID
        self.max_results = max_results
        self.ssl_verify = ssl_verify
        self._scraper = WebAdapter()

    def can_handle(self, source: str) -> bool:
        return source.lower().startswith(self._PREFIX)

    async def extract(self, source: str) -> SourceContent:
        query = source[len(self._PREFIX):].strip()

        # 1. Search
        urls = await self._search(query)

        # 2. Scrape top results
        texts = []
        for url in urls[:self.max_results]:
            try:
                content = await self._scraper.extract(url)
                texts.append(f"[{content.title}]\n{content.source_url}\n{content.text[:3000]}")
            except Exception:
                continue

        if not texts:
            raise ValueError(f"No results found for: {query}")

        return SourceContent(
            text="\n\n---\n\n".join(texts),
            title=f"검색: {query}",
            source_url=f"search:{query}",
            source_type="web_search",
            metadata={"query": query, "results_count": len(texts)},
        )

    async def _search(self, query: str) -> List[str]:
        """Search using configured provider. Priority: google > brave > duckduckgo."""
        if self.provider == "google" and self.api_key:
            return await self._google_search(query)
        elif self.provider == "brave" and self.api_key:
            return await self._brave_search(query)
        return await self._ddg_search(query)

    async def _google_search(self, query: str) -> List[str]:
        """Google Custom Search API (requires API key + CX ID)."""
        import httpx
        async with httpx.AsyncClient(timeout=10.0, verify=self.ssl_verify) as client:
            resp = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": self.api_key,
                    "cx": self.cx_id,
                    "q": query,
                    "num": self.max_results,
                },
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [item["link"] for item in items]

    async def _brave_search(self, query: str) -> List[str]:
        import httpx
        async with httpx.AsyncClient(timeout=10.0, verify=self.ssl_verify) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": self.max_results},
                headers={"X-Subscription-Token": self.api_key},
            )
            resp.raise_for_status()
            results = resp.json().get("web", {}).get("results", [])
            return [r["url"] for r in results]

    async def _ddg_search(self, query: str) -> List[str]:
        """Fallback: DuckDuckGo (no API key needed)."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
                return [r["href"] for r in results]
        except ImportError:
            raise ImportError("pip install duckduckgo-search (or set search API key)")
