"""Web UI for preview, edit, and publish to Confluence."""
import asyncio
import json
from pathlib import Path
from typing import Optional

from aiohttp import web

from .router import SourceRouter
from .processor import LLMProcessor
from .publisher import ConfluencePublisher
from .templates import TemplateManager

STATIC_DIR = Path(__file__).parent.parent / "static"


class WebUI:
    def __init__(self, config: dict, router: SourceRouter, processor: LLMProcessor):
        self.config = config
        self.router = router
        self.processor = processor
        self.templates = TemplateManager()

        conf_cfg = config.get("confluence", {})
        self.publisher = None
        if conf_cfg.get("url"):
            self.publisher = ConfluencePublisher(
                url=conf_cfg["url"],
                username=conf_cfg["username"],
                api_token=conf_cfg["api_token"],
            )

        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._index)
        self.app.router.add_get("/api/templates", self._get_templates)
        self.app.router.add_get("/api/templates/{name}", self._get_template)
        self.app.router.add_put("/api/templates/{name}", self._save_template)
        self.app.router.add_post("/api/templates", self._create_template)
        self.app.router.add_post("/api/extract", self._extract)
        self.app.router.add_post("/api/process", self._process)
        self.app.router.add_post("/api/publish", self._publish)
        if STATIC_DIR.exists():
            self.app.router.add_static("/static", STATIC_DIR)

    async def _index(self, request):
        return web.FileResponse(STATIC_DIR / "index.html")

    async def _get_templates(self, request):
        templates = self.templates.list_templates()
        return web.json_response(templates)

    async def _get_template(self, request):
        name = request.match_info["name"]
        content = self.templates.get_template(name)
        return web.json_response({"name": name, "content": content})

    async def _save_template(self, request):
        name = request.match_info["name"]
        data = await request.json()
        self.templates.save_template(name, data["content"])
        return web.json_response({"ok": True})

    async def _create_template(self, request):
        data = await request.json()
        self.templates.save_template(data["name"], data["content"])
        return web.json_response({"ok": True})

    async def _extract(self, request):
        """Extract content from sources."""
        data = await request.json()
        sources = data.get("sources", [])

        results = []
        for source in sources:
            try:
                content = await self.router.extract(source)
                results.append({
                    "source": source,
                    "title": content.title,
                    "type": content.source_type,
                    "text": content.text[:5000],  # Preview limit
                    "chars": len(content.text),
                    "ok": True,
                })
            except Exception as e:
                results.append({"source": source, "ok": False, "error": str(e)})

        return web.json_response(results)

    async def _process(self, request):
        """Process extracted content with LLM."""
        data = await request.json()
        sources = data.get("sources", [])
        template = data.get("template", "summary")
        output_format = data.get("format", "confluence")  # confluence or markdown

        # Extract
        contents = await self.router.extract_many(sources)

        # Process
        body = await self.processor.process(
            contents,
            template=template,
            output_format=output_format,
        )

        return web.json_response({
            "body": body,
            "format": output_format,
            "template": template,
            "sources_count": len(contents),
        })

    async def _publish(self, request):
        """Publish to Confluence."""
        if not self.publisher:
            return web.json_response(
                {"ok": False, "error": "Confluence not configured"}, status=400
            )

        data = await request.json()
        title = data["title"]
        body = data["body"]
        space = data.get("space", self.config.get("confluence", {}).get("default_space", "TEAM"))
        parent_id = data.get("parent_id")
        use_markdown = data.get("use_markdown", False)

        # Wrap in markdown macro if requested
        if use_markdown:
            body = self._wrap_markdown_macro(body)

        try:
            result = await self.publisher.create_page(
                title=title,
                body=body,
                space_key=space,
                parent_id=parent_id,
            )
            return web.json_response({"ok": True, **result})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    def _wrap_markdown_macro(self, markdown_text: str) -> str:
        """Wrap markdown in Confluence markdown macro."""
        import html
        escaped = html.escape(markdown_text)
        return (
            '<ac:structured-macro ac:name="markdown">'
            '<ac:plain-text-body>'
            f'<![CDATA[{markdown_text}]]>'
            '</ac:plain-text-body>'
            '</ac:structured-macro>'
        )

    def run(self, host: str = "127.0.0.1", port: int = 8501):
        import sys
        print(f"🌐 Web UI: http://{host}:{port}", flush=True)
        web.run_app(self.app, host=host, port=port, print=lambda msg: print(msg, flush=True))
