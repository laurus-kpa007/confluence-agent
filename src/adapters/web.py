"""Web URL scraper adapter."""
import logging
import re
from .base import BaseAdapter, SourceContent

logger = logging.getLogger(__name__)


class WebAdapter(BaseAdapter):
    name = "web"

    # Exclude youtube, drive, sharepoint URLs
    _EXCLUDE = re.compile(r"(youtube\.com|youtu\.be|drive\.google|sharepoint|onedrive)")

    def __init__(self, ssl_verify: bool = True):
        self.ssl_verify = ssl_verify

    def can_handle(self, source: str) -> bool:
        if not source.startswith(("http://", "https://")):
            return False
        return not self._EXCLUDE.search(source)

    async def extract(self, source: str) -> SourceContent:
        try:
            from trafilatura import fetch_url, extract
        except ImportError:
            raise ImportError("pip install trafilatura")

        logger.debug("Fetching URL: %s (ssl_verify=%s)", source, self.ssl_verify)
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
