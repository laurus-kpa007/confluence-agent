"""Configuration loader - reads all settings from .env and environment variables."""
import os
from pathlib import Path
from typing import Any, Dict


def _strip_quotes(value: str) -> str:
    """Strip surrounding quotes from a value (single or double)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def load_env_file(env_path: Path = Path(".env")) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = _strip_quotes(value.strip())
    return env_vars


def _env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = True) -> bool:
    """Get boolean environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("false", "0", "no"):
        return False
    if val in ("true", "1", "yes"):
        return True
    return default


def _env_int(key: str, default: int = 0) -> int:
    """Get integer environment variable."""
    val = os.environ.get(key, "")
    if val.isdigit():
        return int(val)
    return default


def load_config(env_path: Path = Path(".env")) -> dict:
    """Build config dict from .env file and environment variables.

    1. Load .env file (if exists)
    2. Build config dict from environment variables
    """
    # Load .env into os.environ
    env_vars = load_env_file(env_path)
    for key, value in env_vars.items():
        if key not in os.environ:  # Don't override existing env vars
            os.environ[key] = value

    # Build config dict from environment variables
    config = {
        "ssl_verify": _env_bool("SSL_VERIFY", True),
        "llm": {
            "provider": _env("LLM_PROVIDER", "ollama"),
            "model": _env("LLM_MODEL", "gemma3:4b"),
            "base_url": _env("LLM_BASE_URL", "http://localhost:11434"),
            "api_key": _env("ANTHROPIC_API_KEY"),
        },
        "confluence": {
            "url": _env("CONFLUENCE_URL"),
            "username": _env("CONFLUENCE_USERNAME"),
            "api_token": _env("CONFLUENCE_API_TOKEN"),
            "auth_type": _env("CONFLUENCE_AUTH_TYPE", "basic"),
            "default_space": _env("CONFLUENCE_DEFAULT_SPACE", "TEAM"),
        },
        "search": {
            "provider": _env("SEARCH_PROVIDER", "duckduckgo"),
            "api_key": _env("GOOGLE_SEARCH_API_KEY") or _env("BRAVE_API_KEY"),
            "cx_id": _env("GOOGLE_SEARCH_CX_ID"),
            "max_results": _env_int("SEARCH_MAX_RESULTS", 3),
            "proxy": _env("SEARCH_PROXY") or _env("HTTPS_PROXY"),
        },
        "mcp_servers": {
            "gdrive": {
                "enabled": _env_bool("MCP_GDRIVE_ENABLED", False),
                "command": "npx",
                "args": ["-y", "google-drive-mcp"],
                "env": {
                    "GOOGLE_APPLICATION_CREDENTIALS": _env("GOOGLE_APPLICATION_CREDENTIALS"),
                },
            },
            "sharepoint": {
                "enabled": _env_bool("MCP_SHAREPOINT_ENABLED", False),
                "command": "npx",
                "args": ["-y", "mcp-onedrive-sharepoint"],
                "env": {
                    "MICROSOFT_CLIENT_ID": _env("MICROSOFT_CLIENT_ID"),
                    "MICROSOFT_CLIENT_SECRET": _env("MICROSOFT_CLIENT_SECRET"),
                    "MICROSOFT_TENANT_ID": _env("MICROSOFT_TENANT_ID"),
                },
            },
            "notion": {
                "enabled": _env_bool("MCP_NOTION_ENABLED", False),
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "NOTION_API_KEY": _env("NOTION_API_KEY"),
                },
            },
            "slack": {
                "enabled": _env_bool("MCP_SLACK_ENABLED", False),
                "command": "npx",
                "args": ["-y", "@anthropic/mcp-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": _env("SLACK_BOT_TOKEN"),
                },
            },
        },
        "templates": {
            "default": _env("DEFAULT_TEMPLATE", "summary"),
        },
    }

    return config


def get_ssl_verify(config: dict) -> bool:
    """Get SSL verification setting from config."""
    return config.get("ssl_verify", True)


def get_search_config(config: dict) -> dict:
    """Extract and validate search configuration."""
    search = config.get("search", {})
    return {
        "provider": search.get("provider", "duckduckgo"),
        "api_key": search.get("api_key", ""),
        "cx_id": search.get("cx_id", ""),
        "max_results": search.get("max_results", 3),
        "proxy": search.get("proxy", ""),
    }
