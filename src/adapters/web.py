"""Web URL scraper adapter."""
import logging
import os
import re
from .base import BaseAdapter, SourceContent

logger = logging.getLogger(__name__)


class WebAdapter(BaseAdapter):
    name = "web"

    # Exclude youtube, drive, sharepoint URLs
    _EXCLUDE = re.compile(r"(youtube\.com|youtu\.be|drive\.google|sharepoint|onedrive)")

    def __init__(self, ssl_verify: bool = True, proxy: str = ""):
        self.ssl_verify = ssl_verify
        self.proxy = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None

    def can_handle(self, source: str) -> bool:
        if not source.startswith(("http://", "https://")):
            return False
        return not self._EXCLUDE.search(source)

    async def extract(self, source: str) -> SourceContent:
        try:
            from trafilatura import extract
        except ImportError:
            raise ImportError("pip install trafilatura")

        logger.debug("Fetching URL: %s (ssl_verify=%s, proxy=%s)", source, self.ssl_verify, self.proxy)

        # Use httpx for fetching (supports proxy), then trafilatura for extraction
        if self.proxy:
            downloaded = await self._fetch_with_proxy(source)
        else:
            from trafilatura import fetch_url
            downloaded = fetch_url(source, no_ssl=not self.ssl_verify)

        if not downloaded:
            logger.error("Failed to fetch URL: %s", source)
            raise ValueError(f"Failed to fetch: {source}")

        text = extract(downloaded, include_comments=False, include_tables=True)
        if not text:
            logger.warning("No content extracted from: %s", source)
            raise ValueError(f"No content extracted from: {source}")
        logger.debug("Extracted %d chars from %s", len(text), source)

        # Try to get title
        from trafilatura.metadata import extract_metadata
        meta = extract_metadata(downloaded)
        title = meta.title if meta and meta.title else source

        return SourceContent(
            text=text,
            title=title,
            source_url=source,
            source_type="web",
        )

    async def _fetch_with_proxy(self, url: str) -> str | None:
        """Fetch URL content via proxy using httpx."""
        import httpx
        try:
            async with httpx.AsyncClient(
                timeout=15.0, verify=self.ssl_verify, proxy=self.proxy,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; ConfluenceAgent/1.0)",
                })
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            logger.warning("Failed to fetch %s via proxy: %s", url, e)
            return None
