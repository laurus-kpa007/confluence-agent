"""SharePoint/OneDrive MCP adapter."""
import re
from .base import BaseAdapter, SourceContent


class SharePointAdapter(BaseAdapter):
    """Access files via SharePoint/OneDrive MCP server.
    
    Requires: mcp-onedrive-sharepoint server configured in config.yaml
    """
    name = "sharepoint"

    _SP_PATTERN = re.compile(r"(sharepoint\.com|onedrive\.live|onedrive://|sharepoint://)")

    def can_handle(self, source: str) -> bool:
        return bool(self._SP_PATTERN.search(source)) or source.startswith(("onedrive://", "sharepoint://"))

    async def extract(self, source: str) -> SourceContent:
        from ..mcp_client import call_mcp_tool

        result = await call_mcp_tool(
            server="sharepoint",
            tool="get_file_content",
            arguments={"path_or_url": source},
        )

        return SourceContent(
            text=result.get("content", ""),
            title=result.get("name", source),
            source_url=source,
            source_type="sharepoint",
            metadata=result.get("metadata", {}),
        )
