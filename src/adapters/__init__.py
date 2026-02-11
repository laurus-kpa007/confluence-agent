from .base import BaseAdapter, SourceContent
from .web import WebAdapter
from .web_search import WebSearchAdapter
from .youtube import YouTubeAdapter
from .local_file import LocalFileAdapter

# MCP-based adapters (optional, loaded if configured)
BUILTIN_ADAPTERS = [WebSearchAdapter, WebAdapter, YouTubeAdapter, LocalFileAdapter]

__all__ = [
    "BaseAdapter",
    "SourceContent",
    "WebAdapter",
    "YouTubeAdapter",
    "LocalFileAdapter",
    "BUILTIN_ADAPTERS",
]
