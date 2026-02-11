"""Google Drive MCP adapter."""
import re
from .base import BaseAdapter, SourceContent


class GDriveAdapter(BaseAdapter):
    """Access files via Google Drive MCP server.
    
    Requires: google-drive-mcp server configured in config.yaml
    Uses MCP protocol to communicate with the server.
    """
    name = "gdrive"

    _GDRIVE_PATTERN = re.compile(
        r"(drive\.google\.com|gdrive://|docs\.google\.com)"
    )

    def can_handle(self, source: str) -> bool:
        return bool(self._GDRIVE_PATTERN.search(source)) or source.startswith("gdrive://")

    async def extract(self, source: str) -> SourceContent:
        from ..mcp_client import call_mcp_tool

        # Extract file ID from URL or gdrive:// scheme
        file_id = self._parse_file_id(source)

        # Call MCP server to get file content
        result = await call_mcp_tool(
            server="gdrive",
            tool="read_file",
            arguments={"file_id": file_id},
        )

        return SourceContent(
            text=result.get("content", ""),
            title=result.get("name", source),
            source_url=source,
            source_type="gdrive",
            metadata=result.get("metadata", {}),
        )

    def _parse_file_id(self, source: str) -> str:
        if source.startswith("gdrive://"):
            return source.replace("gdrive://", "")
        # Extract from Google Drive URL patterns
        patterns = [
            r"/d/([a-zA-Z0-9_-]+)",
            r"id=([a-zA-Z0-9_-]+)",
        ]
        for p in patterns:
            m = re.search(p, source)
            if m:
                return m.group(1)
        return source
