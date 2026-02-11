"""Lightweight MCP client for calling MCP server tools.

This module handles communication with MCP servers configured in config.yaml.
Each MCP server runs as a subprocess and communicates via stdio JSON-RPC.
"""
import asyncio
import json
import subprocess
from typing import Any, Dict, Optional
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

# Cache running MCP server processes
_servers: Dict[str, subprocess.Popen] = {}


def _load_mcp_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        return cfg.get("mcp_servers", {})
    return {}


async def call_mcp_tool(
    server: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> dict:
    """Call a tool on an MCP server.
    
    Args:
        server: MCP server name (e.g., "gdrive", "sharepoint")
        tool: Tool name to call
        arguments: Tool arguments
        
    Returns:
        Tool result as dict
    """
    config = _load_mcp_config()
    server_cfg = config.get(server)
    if not server_cfg:
        raise ValueError(f"MCP server '{server}' not configured in config.yaml")
    if not server_cfg.get("enabled"):
        raise ValueError(f"MCP server '{server}' is disabled")

    # Start server if not running
    if server not in _servers or _servers[server].poll() is not None:
        cmd = [server_cfg["command"]] + server_cfg.get("args", [])
        env_vars = server_cfg.get("env", {})

        import os
        env = {**os.environ, **env_vars}

        _servers[server] = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    proc = _servers[server]

    # JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": arguments or {},
        },
    }

    # Send request
    request_bytes = json.dumps(request).encode() + b"\n"
    proc.stdin.write(request_bytes)
    proc.stdin.flush()

    # Read response (with timeout)
    loop = asyncio.get_event_loop()
    line = await asyncio.wait_for(
        loop.run_in_executor(None, proc.stdout.readline),
        timeout=30.0,
    )

    response = json.loads(line)
    if "error" in response:
        raise RuntimeError(f"MCP error: {response['error']}")

    result = response.get("result", {})

    # Parse content from MCP response
    if isinstance(result, dict) and "content" in result:
        contents = result["content"]
        if isinstance(contents, list) and contents:
            return {"content": contents[0].get("text", ""), **result}

    return result


def cleanup():
    """Shutdown all running MCP servers."""
    for name, proc in _servers.items():
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    _servers.clear()
