"""CLI entrypoint for Confluence Knowledge Agent."""
import asyncio
import argparse
import yaml
from pathlib import Path

from .router import SourceRouter
from .processor import LLMProcessor
from .publisher import ConfluencePublisher

# Optional MCP adapters
from .adapters.gdrive import GDriveAdapter
from .adapters.sharepoint import SharePointAdapter

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


def build_router(config: dict) -> SourceRouter:
    """Build router with configured adapters."""
    extra = []
    mcp = config.get("mcp_servers", {})

    if mcp.get("gdrive", {}).get("enabled"):
        extra.append(GDriveAdapter())
    if mcp.get("sharepoint", {}).get("enabled"):
        extra.append(SharePointAdapter())

    return SourceRouter(extra_adapters=extra if extra else None)


async def run(args):
    config = load_config()

    # Build components
    router = build_router(config)

    llm_cfg = config.get("llm", {})
    processor = LLMProcessor(
        provider=llm_cfg.get("provider", "ollama"),
        model=llm_cfg.get("model", "qwen3:14b-128k"),
        base_url=llm_cfg.get("base_url", "http://localhost:11434"),
        api_key=llm_cfg.get("api_key"),
    )

    # 1. Extract from all sources
    print(f"📥 Extracting from {len(args.sources)} source(s)...")
    contents = await router.extract_many(args.sources)
    for c in contents:
        print(f"  ✅ [{c.source_type}] {c.title} ({len(c.text)} chars)")

    # 2. Process with LLM
    template = args.template or config.get("templates", {}).get("default", "summary")
    print(f"🤖 Processing with {processor.model} (template: {template})...")
    body = await processor.process(contents, template=template)
    print(f"  ✅ Generated {len(body)} chars")

    # 3. Publish to Confluence (if configured)
    conf_cfg = config.get("confluence", {})
    if conf_cfg.get("url") and not args.dry_run:
        publisher = ConfluencePublisher(
            url=conf_cfg["url"],
            username=conf_cfg["username"],
            api_token=conf_cfg["api_token"],
        )
        space = args.space or conf_cfg.get("default_space", "TEAM")
        title = args.title or contents[0].title

        print(f"📤 Publishing to Confluence [{space}]...")
        result = await publisher.create_page(
            title=title,
            body=body,
            space_key=space,
            parent_id=args.parent_id,
        )
        print(f"  ✅ Created: {result['url']}")
    else:
        # Dry run - just print output
        print("\n" + "=" * 60)
        print("📄 Generated Content (dry-run):")
        print("=" * 60)
        print(body)


def main():
    parser = argparse.ArgumentParser(
        description="Confluence Knowledge Agent - Multi-source → LLM → Confluence"
    )
    subparsers = parser.add_subparsers(dest="command")

    # CLI mode
    cli = subparsers.add_parser("run", help="CLI mode - process and publish")
    cli.add_argument("sources", nargs="+", help="Source URLs, file paths, or gdrive:// URIs")
    cli.add_argument("--space", "-s", help="Confluence space key")
    cli.add_argument("--title", "-t", help="Page title")
    cli.add_argument("--template", choices=["summary", "meeting_notes", "tech_doc", "research"])
    cli.add_argument("--format", choices=["markdown", "confluence"], default="markdown")
    cli.add_argument("--parent-id", help="Parent page ID")
    cli.add_argument("--dry-run", action="store_true", help="Don't publish, just print")
    cli.add_argument("--config", "-c", help="Config file path")

    # Web UI mode
    ui = subparsers.add_parser("ui", help="Start web UI")
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8501)
    ui.add_argument("--config", "-c", help="Config file path")

    args = parser.parse_args()

    if args.command == "ui":
        if getattr(args, 'config', None):
            global CONFIG_PATH
            CONFIG_PATH = Path(args.config)
        config = load_config()
        router = build_router(config)
        llm_cfg = config.get("llm", {})
        processor = LLMProcessor(
            provider=llm_cfg.get("provider", "ollama"),
            model=llm_cfg.get("model", "qwen3:14b-128k"),
            base_url=llm_cfg.get("base_url", "http://localhost:11434"),
            api_key=llm_cfg.get("api_key"),
        )
        from .web_ui import WebUI
        web_ui = WebUI(config, router, processor)
        web_ui.run(host=args.host, port=args.port)
    elif args.command == "run":
        if getattr(args, 'config', None):
            CONFIG_PATH = Path(args.config)
        asyncio.run(run(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
