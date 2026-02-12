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
from .config_loader import get_ssl_verify

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
                ssl_verify=get_ssl_verify(config),
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
        self.app.router.add_post("/api/extract_viz", self._extract_visualize)
        self.app.router.add_post("/api/extract_entities", self._extract_entities)
        self.app.router.add_get("/viz", self._viz_page)
        self.app.router.add_get("/entities", self._entities_page)
        self.app.router.add_get("/api/confluence/spaces", self._list_spaces)
        self.app.router.add_get("/api/confluence/pages", self._list_pages)
        self.app.router.add_get("/api/confluence/search", self._search_pages)
        self.app.router.add_get("/api/confluence/tree", self._page_tree)
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
        try:
            data = await request.json()
            sources = data.get("sources", [])
            template = data.get("template", "summary")
            output_format = data.get("format", "confluence")  # confluence or markdown

            # Extract
            contents = await self.router.extract_many(sources)

            use_langextract = data.get("use_langextract", False)
            extraction_profile = data.get("extraction_profile", "general")
            output_length = data.get("output_length", "normal")

            # Process
            body = await self.processor.process(
                contents,
                template=template,
                output_format=output_format,
                use_langextract=use_langextract,
                extraction_profile=extraction_profile,
                output_length=output_length,
            )

            return web.json_response({
                "body": body,
                "format": output_format,
                "template": template,
                "sources_count": len(contents),
            })
        except Exception as e:
            import traceback
            return web.json_response({
                "error": str(e),
                "traceback": traceback.format_exc(),
            }, status=500)

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

    async def _extract_visualize(self, request):
        """Run LangExtract and return interactive HTML visualization."""
        data = await request.json()
        sources = data.get("sources", [])
        profile = data.get("profile", "general")

        try:
            # Extract text from sources
            contents = await self.router.extract_many(sources)
            combined = "\n\n".join(c.text[:10000] for c in contents)

            # Run LangExtract with visualization
            from .extractor import StructuredExtractor
            import tempfile
            extractor = StructuredExtractor(
                model_id="gemma2:2b",
                model_url="http://localhost:11434",
            )
            with tempfile.TemporaryDirectory() as tmpdir:
                result, html_str = await extractor.extract_with_visualization(
                    combined, profile=profile, output_dir=tmpdir,
                )

            entities_summary = extractor.format_entities_as_context(result)

            return web.json_response({
                "ok": True,
                "html": html_str,
                "entities_count": len(result.entities),
                "entities_summary": entities_summary,
            })
        except Exception as e:
            import traceback
            return web.json_response({
                "ok": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }, status=500)

    async def _viz_page(self, request):
        """Serve the last generated visualization as a standalone page."""
        return web.Response(
            text=getattr(self, '_last_viz_html', '<h1>No visualization yet</h1>'),
            content_type='text/html',
        )

    async def _extract_entities(self, request):
        """Extract structured entities and return JSON data."""
        try:
            data = await request.json()
            sources = data.get("sources", [])
            profile = data.get("profile", "general")

            # Validate sources
            if not sources or len(sources) == 0:
                return web.json_response({
                    "ok": False,
                    "error": "소스가 비어있습니다. 최소 1개의 소스를 추가하세요.",
                }, status=400)

            # Extract content from sources
            try:
                contents = await self.router.extract_many(sources)
            except FileNotFoundError as e:
                return web.json_response({
                    "ok": False,
                    "error": f"파일을 찾을 수 없습니다: {str(e)}",
                }, status=404)
            except ValueError as e:
                return web.json_response({
                    "ok": False,
                    "error": f"소스 처리 오류: {str(e)}",
                }, status=400)

            combined = "\n\n".join([c.text for c in contents])

            # Check if combined text is too short
            if len(combined.strip()) < 10:
                return web.json_response({
                    "ok": False,
                    "error": "추출된 텍스트가 너무 짧습니다 (최소 10자 필요).",
                }, status=400)

            # Run LangExtract
            from .extractor import StructuredExtractor
            extractor = StructuredExtractor(
                model_id="gemma2:2b",
                model_url="http://localhost:11434",
            )
            result = await extractor.extract(combined[:20000], profile=profile)

            # Convert entities to JSON-serializable format
            entities_data = []
            for entity in result.entities:
                entity_dict = {
                    "type": entity.get("class", "unknown"),
                    "content": entity.get("text", ""),
                    "fields": entity.get("attributes", {}),
                    "confidence": 0.9,  # LangExtract doesn't provide confidence scores
                    "position": None,  # Position info not available from current extraction
                }
                entities_data.append(entity_dict)

            return web.json_response({
                "ok": True,
                "profile": profile,
                "entities": entities_data,
                "total_count": len(entities_data),
                "source_text": combined[:5000],  # First 5000 chars for preview
            })
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            print(f"❌ Entity extraction error: {error_msg}")
            print(tb)
            return web.json_response({
                "ok": False,
                "error": error_msg if error_msg else f"{type(e).__name__} (no message)",
                "traceback": tb,
            }, status=500)

    async def _entities_page(self, request):
        """Serve the entities viewer page."""
        entities_html_path = STATIC_DIR / "entities.html"
        if entities_html_path.exists():
            return web.FileResponse(entities_html_path)
        return web.Response(text="<h1>Entities viewer not found</h1>", content_type="text/html")

    async def _list_spaces(self, request):
        if not self.publisher:
            return web.json_response({"error": "Confluence not configured"}, status=400)
        try:
            spaces = await self.publisher.list_spaces()
            return web.json_response(spaces)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _list_pages(self, request):
        if not self.publisher:
            return web.json_response({"error": "Confluence not configured"}, status=400)
        space = request.query.get("space", "")
        parent_id = request.query.get("parent_id")
        try:
            pages = await self.publisher.list_pages(space, parent_id=parent_id)
            return web.json_response(pages)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _search_pages(self, request):
        if not self.publisher:
            return web.json_response({"error": "Confluence not configured"}, status=400)
        query = request.query.get("q", "")
        space = request.query.get("space")
        try:
            results = await self.publisher.search_pages(query, space_key=space)
            return web.json_response(results)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def _page_tree(self, request):
        if not self.publisher:
            return web.json_response({"error": "Confluence not configured"}, status=400)
        space = request.query.get("space", "")
        try:
            tree = await self.publisher.get_page_tree(space)
            return web.json_response(tree)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

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
