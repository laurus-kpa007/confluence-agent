"""Configuration loader with environment variable support."""
import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict


def load_env_file(env_path: Path = Path(".env")) -> Dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
    return env_vars


def expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in config values.

    Supports formats:
    - ${VAR_NAME}
    - ${VAR_NAME:default_value}
    """
    if isinstance(value, str):
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replacer, value)

    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]

    return value


def load_config(config_path: Path, env_path: Path = Path(".env")) -> dict:
    """Load config.yaml with environment variable expansion.

    1. Load .env file (if exists)
    2. Load config.yaml
    3. Expand ${VAR} references
    """
    # Load .env into os.environ
    env_vars = load_env_file(env_path)
    for key, value in env_vars.items():
        if key not in os.environ:  # Don't override existing env vars
            os.environ[key] = value

    # Load YAML config
    if not config_path.exists():
        return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Expand environment variables
    return expand_env_vars(config)


def get_search_config(config: dict) -> dict:
    """Extract and validate search configuration."""
    search = config.get("search", {})
    provider = search.get("provider", "duckduckgo")

    return {
        "provider": provider,
        "api_key": search.get("api_key", ""),
        "cx_id": search.get("cx_id", ""),
        "max_results": search.get("max_results", 3),
    }
