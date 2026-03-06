"""Web UI for preview, edit, and publish to Confluence."""
import asyncio
import json
from pathlib import Path
from typing import Optional

from aiohttp import web
import httpx

from .router import SourceRouter
from .processor import LLMProcessor
from .publisher import ConfluencePublisher, ConfluenceAuthError
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
        conf_url = conf_cfg.get("url", "").strip()
        conf_username = conf_cfg.get("username", "").strip()
        conf_token = conf_cfg.get("api_token", "").strip()
        conf_auth_type = conf_cfg.get("auth_type", "basic").strip()
        if conf_url:
            if conf_auth_type != "bearer" and (not conf_username or not conf_token):
                import logging
                logging.getLogger(__name__).warning(
                    "Confluence URL is set but username or api_token is empty. "
                    "Check .env file (CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)."
                )
            self.publisher = ConfluencePublisher(
                url=conf_url,
                username=conf_username,
                api_token=conf_token,
                ssl_verify=get_ssl_verify(config),
                auth_type=conf_auth_type,
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
        self.app.router.add_post("/api/analyze_sources", self._analyze_sources)
        self.app.router.add_post("/api/process", self._process)
        self.app.router.add_post("/api/process_stream", self._process_stream)
        self.app.router.add_post("/api/refine_stream", self._refine_stream)
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

    async def _analyze_sources(self, request):
        """Analyze source materials and recommend template + extraction profile."""
        try:
            data = await request.json()
            sources = data.get("sources", [])
            if not sources:
                return web.json_response({"template": "summary", "extraction_profile": "general", "use_langextract": False})

            contents = await self.router.extract_many(sources)
            combined = "\n".join(c.text[:3000] for c in contents)[:6000]
            combined_lower = combined.lower()

            # Collect source type hints
            source_types = [c.source_type for c in contents]
            source_titles = " ".join(c.title for c in contents).lower()

            # --- Template selection heuristics ---
            template = "summary"  # default
            extraction_profile = "general"
            use_langextract = False

            # Meeting keywords
            meeting_kw = ["회의", "미팅", "meeting", "minutes", "참석자", "안건", "논의", "결정사항",
                          "액션아이템", "action item", "agenda", "attendee", "발언", "회의록"]
            meeting_score = sum(1 for kw in meeting_kw if kw in combined_lower or kw in source_titles)

            # Tech doc keywords
            tech_kw = ["api", "sdk", "아키텍처", "architecture", "코드", "code", "함수", "function",
                       "설치", "install", "배포", "deploy", "서버", "server", "데이터베이스", "database",
                       "프레임워크", "framework", "라이브러리", "library", "깃", "git", "도커", "docker",
                       "class", "import", "def ", "return", "config", "설정"]
            tech_score = sum(1 for kw in tech_kw if kw in combined_lower or kw in source_titles)

            # Research keywords
            research_kw = ["연구", "research", "논문", "paper", "분석", "analysis", "비교", "comparison",
                           "결론", "conclusion", "조사", "survey", "트렌드", "trend", "인사이트",
                           "insight", "데이터", "data", "통계", "statistics", "리서치", "보고서"]
            research_score = sum(1 for kw in research_kw if kw in combined_lower or kw in source_titles)

            # Weekly report keywords
            weekly_kw = ["주간", "weekly", "실적", "이슈", "차주", "금주", "보고", "report",
                         "진행", "progress", "완료", "계획", "plan", "리스크", "risk"]
            weekly_score = sum(1 for kw in weekly_kw if kw in combined_lower or kw in source_titles)

            # UX Research keywords
            ux_kw = ["ux", "사용자 경험", "user experience", "사용성", "usability", "인터뷰",
                     "interview", "페르소나", "persona", "저니맵", "journey map", "와이어프레임",
                     "wireframe", "프로토타입", "prototype", "사용자 테스트", "user test",
                     "usability test", "태스크", "task flow", "페인포인트", "pain point",
                     "사용자 니즈", "user need", "heuristic", "휴리스틱", "sus ", "nps ",
                     "완료율", "이탈률", "피드백", "feedback", "설문", "survey result"]
            ux_score = sum(1 for kw in ux_kw if kw in combined_lower or kw in source_titles)

            scores = {
                "meeting_notes": meeting_score,
                "tech_doc": tech_score,
                "research": research_score,
                "weekly_report": weekly_score,
                "ux_research": ux_score,
                "summary": 1,  # baseline
            }
            template = max(scores, key=scores.get)

            # Map template → extraction profile
            profile_map = {
                "meeting_notes": "meeting",
                "tech_doc": "tech_review",
                "research": "research",
                "weekly_report": "general",
                "ux_research": "ux_research",
                "summary": "general",
            }
            extraction_profile = profile_map.get(template, "general")

            # Enable LangExtract if strong signal found
            max_score = scores[template]
            use_langextract = max_score >= 3

            return web.json_response({
                "template": template,
                "extraction_profile": extraction_profile,
                "use_langextract": use_langextract,
                "scores": scores,
            })
        except Exception as e:
            return web.json_response({
                "template": "summary",
                "extraction_profile": "general",
                "use_langextract": False,
                "error": str(e),
            })

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
            output_language = data.get("output_language", "ko")

            # Process
            body = await self.processor.process(
                contents,
                template=template,
                output_format=output_format,
                use_langextract=use_langextract,
                extraction_profile=extraction_profile,
                output_length=output_length,
                output_language=output_language,
            )

            # Clean up wiki-style macros that cause "Unknown macro" errors
            if output_format == "confluence":
                body = self._clean_confluence_macros(body)

            return web.json_response({
                "body": body,
                "format": output_format,
                "template": template,
                "sources_count": len(contents),
            })
        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: (no message)"
            tb = traceback.format_exc()
            print(f"❌ Process error: {error_msg}")
            print(tb)
            return web.json_response({
                "error": error_msg,
                "error_type": type(e).__name__,
                "traceback": tb,
            }, status=500)

    async def _process_stream(self, request):
        """Process extracted content with LLM, streaming the response via SSE."""
        response = None
        try:
            data = await request.json()
            sources = data.get("sources", [])
            template = data.get("template", "summary")
            output_format = data.get("format", "confluence")
            use_langextract = data.get("use_langextract", False)
            extraction_profile = data.get("extraction_profile", "general")
            output_length = data.get("output_length", "normal")
            output_language = data.get("output_language", "ko")
            auto_select = data.get("auto_select", False)

            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                },
            )
            await response.prepare(request)

            # Step 1: Send extraction start event
            total_sources = len(sources)
            total_steps = 4  # extract, langextract, llm, done
            await response.write(f"data: {json.dumps({'type': 'status', 'step': 'extract', 'message': f'소스에서 텍스트 추출 중... (0/{total_sources})', 'progress': 0, 'total_sources': total_sources})}\n\n".encode())

            contents = await self.router.extract_many(sources)

            await response.write(f"data: {json.dumps({'type': 'status', 'step': 'extract', 'message': f'소스 추출 완료 ({len(contents)}/{total_sources})', 'progress': 25})}\n\n".encode())

            # Auto-select template and extraction profile if requested
            if auto_select and contents:
                combined_preview = "\n".join(c.text[:3000] for c in contents)[:6000]
                combined_lower = combined_preview.lower()
                source_titles = " ".join(c.title for c in contents).lower()

                meeting_kw = ["회의", "미팅", "meeting", "minutes", "참석자", "안건", "논의", "결정사항",
                              "액션아이템", "action item", "agenda", "attendee", "발언", "회의록"]
                tech_kw = ["api", "sdk", "아키텍처", "architecture", "코드", "code", "함수", "function",
                           "설치", "install", "배포", "deploy", "서버", "server", "데이터베이스", "database",
                           "프레임워크", "framework", "라이브러리", "library", "class", "import", "def ", "config"]
                research_kw = ["연구", "research", "논문", "paper", "분석", "analysis", "비교", "comparison",
                               "결론", "conclusion", "조사", "survey", "트렌드", "trend", "리서치", "보고서"]
                weekly_kw = ["주간", "weekly", "실적", "이슈", "차주", "금주", "보고", "report",
                             "진행", "progress", "완료", "계획", "plan", "리스크", "risk"]
                ux_kw = ["ux", "사용자 경험", "user experience", "사용성", "usability", "인터뷰",
                         "interview", "페르소나", "persona", "저니맵", "journey map", "와이어프레임",
                         "wireframe", "프로토타입", "prototype", "사용자 테스트", "user test",
                         "usability test", "태스크", "task flow", "페인포인트", "pain point",
                         "사용자 니즈", "user need", "heuristic", "휴리스틱", "sus ", "nps ",
                         "완료율", "이탈률", "피드백", "feedback", "설문", "survey result"]

                scores = {
                    "meeting_notes": sum(1 for kw in meeting_kw if kw in combined_lower or kw in source_titles),
                    "tech_doc": sum(1 for kw in tech_kw if kw in combined_lower or kw in source_titles),
                    "research": sum(1 for kw in research_kw if kw in combined_lower or kw in source_titles),
                    "weekly_report": sum(1 for kw in weekly_kw if kw in combined_lower or kw in source_titles),
                    "ux_research": sum(1 for kw in ux_kw if kw in combined_lower or kw in source_titles),
                    "summary": 1,
                }
                template = max(scores, key=scores.get)
                profile_map = {"meeting_notes": "meeting", "tech_doc": "tech_review", "research": "research",
                               "weekly_report": "general", "ux_research": "ux_research", "summary": "general"}
                extraction_profile = profile_map.get(template, "general")
                use_langextract = scores[template] >= 3

                await response.write(f"data: {json.dumps({'type': 'auto_selected', 'template': template, 'extraction_profile': extraction_profile, 'use_langextract': use_langextract, 'scores': scores})}\n\n".encode())

            # Step 2: Optional LangExtract
            combined = self.processor._combine_contents(contents)

            extraction_context = ""
            if use_langextract:
                n = len(contents)
                extractor = self.processor._get_extractor()
                await response.write(f"data: {json.dumps({'type': 'status', 'step': 'langextract', 'message': f'구조화 추출 중... (0/{n})', 'progress': 25})}\n\n".encode())
                try:
                    extraction_results = []
                    for idx, c in enumerate(contents, 1):
                        pct = 25 + round(idx / n * 25)  # 25% ~ 50%
                        try:
                            await response.write(f"data: {json.dumps({'type': 'status', 'step': 'langextract', 'message': f'구조화 추출 중... ({idx}/{n}) {c.title} ({len(c.text):,}자)', 'progress': pct, 'sub_current': idx, 'sub_total': n})}\n\n".encode())
                            result = await extractor.extract(c.text, profile=extraction_profile)
                            result.source_title = c.title
                            extraction_results.append(result)
                        except Exception as e:
                            await response.write(f"data: {json.dumps({'type': 'status', 'step': 'langextract', 'message': f'⚠️ 소스 {idx} 추출 실패: {str(e)[:100]}', 'progress': pct})}\n\n".encode())
                    extraction_context = extractor.format_multi_results_as_context(extraction_results)
                    if extraction_context:
                        combined = f"{extraction_context}\n\n---\n\n## 원본 자료\n{combined}"
                    await response.write(f"data: {json.dumps({'type': 'status', 'step': 'langextract', 'message': f'구조화 추출 완료 ({n}/{n})', 'progress': 50})}\n\n".encode())
                except Exception as e:
                    extraction_context = f"\n[LangExtract 추출 실패: {e}]\n"

            # Step 3: Render template
            prompt = self.processor.templates.render(template, combined, output_format, output_length, output_language)

            await response.write(f"data: {json.dumps({'type': 'status', 'step': 'llm', 'message': 'LLM 생성 중...', 'progress': 50})}\n\n".encode())

            # Step 4: Stream LLM response
            full_body = ""
            async for chunk in self.processor.stream_llm(prompt):
                full_body += chunk
                await response.write(f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n".encode())

            # Clean wiki macros if confluence format
            if output_format == "confluence":
                cleaned = self._clean_confluence_macros(full_body)
                if cleaned != full_body:
                    full_body = cleaned
                    # Send the cleaned full body
                    await response.write(f"data: {json.dumps({'type': 'replace', 'text': full_body})}\n\n".encode())

            # Step 5: Done
            await response.write(f"data: {json.dumps({'type': 'done', 'sources_count': len(contents), 'format': output_format, 'template': template, 'progress': 100})}\n\n".encode())
            await response.write_eof()
            return response

        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: (no message)"
            tb = traceback.format_exc()
            print(f"Stream error: {error_msg}")
            print(tb)
            # If we haven't started streaming yet, return JSON error
            if response is None or not response.prepared:
                return web.json_response({
                    "error": error_msg,
                    "error_type": type(e).__name__,
                }, status=500)
            # Otherwise try to send error event
            try:
                await response.write(f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n".encode())
                await response.write_eof()
            except Exception:
                pass
            return response

    async def _refine_stream(self, request):
        """Refine existing content based on user instruction, streaming via SSE."""
        response = None
        try:
            data = await request.json()
            current_body = data.get("body", "")
            instruction = data.get("instruction", "")
            output_format = data.get("format", "markdown")
            output_language = data.get("output_language", "ko")

            if not current_body or not instruction:
                return web.json_response({"error": "body and instruction are required"}, status=400)

            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                },
            )
            await response.prepare(request)

            await response.write(f"data: {json.dumps({'type': 'status', 'message': '수정 중...'})}\n\n".encode())

            # Build refinement prompt
            fmt = "Confluence Storage Format XHTML" if output_format == "confluence" else "마크다운"
            lang_map = {"ko": "한국어", "en": "English", "ja": "日本語", "zh": "中文"}
            lang = lang_map.get(output_language, "한국어")

            prompt = f"""아래 문서를 사용자의 지시에 따라 수정해주세요.

**출력 형식**: {fmt}
**출력 언어**: {lang}
**중요**: 수정된 전체 문서를 출력하세요. 변경된 부분만이 아니라 전체 내용을 반환해야 합니다.

## 사용자 수정 지시
{instruction}

## 현재 문서
{current_body}"""

            full_body = ""
            async for chunk in self.processor.stream_llm(prompt):
                full_body += chunk
                await response.write(f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n".encode())

            # Clean wiki macros if confluence format
            if output_format == "confluence":
                cleaned = self._clean_confluence_macros(full_body)
                if cleaned != full_body:
                    full_body = cleaned
                    await response.write(f"data: {json.dumps({'type': 'replace', 'text': full_body})}\n\n".encode())

            await response.write(f"data: {json.dumps({'type': 'done'})}\n\n".encode())
            await response.write_eof()
            return response

        except Exception as e:
            import traceback
            error_msg = str(e) if str(e) else f"{type(e).__name__}: (no message)"
            print(f"Refine error: {error_msg}")
            print(traceback.format_exc())
            if response is None or not response.prepared:
                return web.json_response({"error": error_msg}, status=500)
            try:
                await response.write(f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n".encode())
                await response.write_eof()
            except Exception:
                pass
            return response

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

        # Convert markdown to Confluence storage XHTML if requested
        if use_markdown:
            body = self._markdown_to_confluence_storage(body)

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
            combined = "\n\n".join(c.text for c in contents)

            # Run LangExtract with visualization
            from .extractor import StructuredExtractor
            import tempfile

            # Use config model for consistency
            llm_config = self.config.get("llm", {})
            model = llm_config.get("model", "gemma3:4b")
            base_url = llm_config.get("base_url")
            api_key = llm_config.get("api_key")

            extractor = StructuredExtractor(
                model_id=model,
                model_url=base_url,
                api_key=api_key,
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
            # Use config model for consistency
            llm_config = self.config.get("llm", {})
            model = llm_config.get("model", "gemma3:4b")
            base_url = llm_config.get("base_url")
            api_key = llm_config.get("api_key")

            extractor = StructuredExtractor(
                model_id=model,
                model_url=base_url,
                api_key=api_key,
            )
            result = await extractor.extract(combined, profile=profile)

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
        except httpx.ConnectError as e:
            return web.json_response({"error": f"Confluence 연결 실패 - URL을 확인하세요: {e}"}, status=500)
        except httpx.ConnectTimeout as e:
            return web.json_response({"error": f"Confluence 연결 시간 초과 - URL/네트워크를 확인하세요: {e}"}, status=500)
        except ConfluenceAuthError as e:
            return web.json_response({"error": str(e)}, status=500)
        except httpx.HTTPStatusError as e:
            auth_type = self.config.get("confluence", {}).get("auth_type", "basic")
            body_preview = e.response.text[:300] if e.response.text else ""
            import logging
            logging.getLogger(__name__).error(
                "Confluence API error: status=%d, auth_type=%s, body=%s",
                e.response.status_code, auth_type, body_preview
            )
            if e.response.status_code == 401:
                if auth_type == "bearer":
                    msg = "인증 실패 - 개인 액세스 토큰(PAT)이 유효한지 확인하세요"
                else:
                    msg = "인증 실패 - username/api_token을 확인하세요"
                return web.json_response({"error": msg}, status=500)
            elif e.response.status_code == 403:
                if auth_type != "bearer":
                    msg = ("권한 없음 (403) - 현재 auth_type=basic 입니다. "
                           "사내 Confluence Server/DC에서 개인 토큰(PAT)을 사용하시면 "
                           ".env에 CONFLUENCE_AUTH_TYPE=bearer 를 추가하세요. "
                           "또는 관리자가 Basic Auth를 비활성화했을 수 있습니다.")
                else:
                    msg = ("권한 없음 (403) - PAT 토큰에 해당 스페이스 접근 권한이 있는지 확인하세요. "
                           "Confluence 관리자 > 개인 액세스 토큰에서 권한 범위를 확인하세요.")
                return web.json_response({"error": msg}, status=500)
            return web.json_response({"error": f"Confluence API 오류 (HTTP {e.response.status_code}): {body_preview}"}, status=500)
        except Exception as e:
            import logging, traceback
            logging.getLogger(__name__).error("Confluence error: %s\n%s", e, traceback.format_exc())
            return web.json_response({"error": f"Confluence 오류: {e}"}, status=500)

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

    def _clean_confluence_macros(self, body: str) -> str:
        """Remove wiki-style macros that cause 'Unknown macro' errors in Confluence.

        LLMs sometimes generate {code}, {panel}, {note} etc. instead of
        proper Confluence Storage Format XHTML.
        """
        import re

        # Replace {code:lang}...{code} with ac:structured-macro
        def replace_code_macro(m):
            lang = m.group(1) or ""
            code = m.group(2)
            macro = '<ac:structured-macro ac:name="code">'
            if lang:
                macro += f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
            macro += f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
            macro += '</ac:structured-macro>'
            return macro

        body = re.sub(
            r'\{code(?::([a-zA-Z0-9+#]+))?\}(.*?)\{code\}',
            replace_code_macro,
            body,
            flags=re.DOTALL,
        )

        # Remove simple wiki macros: {panel}, {note}, {info}, {warning}, {tip}, {expand}, {toc}, {excerpt}
        simple_macros = ['panel', 'note', 'info', 'warning', 'tip', 'expand', 'toc', 'excerpt',
                         'noformat', 'quote', 'section', 'column', 'color']
        for macro in simple_macros:
            # Remove opening tags: {macro}, {macro:title=...}
            body = re.sub(r'\{' + macro + r'(?::[^}]*)?\}', '', body)
            # Remove closing tags: {macro}
            body = re.sub(r'\{' + macro + r'\}', '', body)

        # Clean double-curly braces wiki links: {{monospace}} -> <code>monospace</code>
        body = re.sub(r'\{\{(.+?)\}\}', r'<code>\1</code>', body)

        # Clean wiki-style headings: h1. Title -> <h1>Title</h1>
        body = re.sub(r'^h([1-6])\.\s*(.+)$', r'<h\1>\2</h\1>', body, flags=re.MULTILINE)

        return body

    def _markdown_to_confluence_storage(self, md_text: str) -> str:
        """Convert markdown to Confluence storage format (XHTML).

        Converts directly to XHTML instead of relying on the Confluence
        Markdown macro plugin which may not be installed on Server/DC.
        """
        import re

        def inline(text: str) -> str:
            """Convert inline markdown formatting to HTML."""
            # Bold
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            # Italic (avoid matching ** already converted)
            text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
            # Inline code
            text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
            # Links
            text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
            return text

        lines = md_text.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Fenced code block
            if stripped.startswith('```'):
                lang = stripped[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1  # skip closing ```
                code = '\n'.join(code_lines)
                macro = '<ac:structured-macro ac:name="code">'
                if lang:
                    macro += f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
                macro += f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                macro += '</ac:structured-macro>'
                result.append(macro)
                continue

            # Heading
            m = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            if m:
                level = len(m.group(1))
                result.append(f'<h{level}>{inline(m.group(2))}</h{level}>')
                i += 1
                continue

            # Horizontal rule
            if re.match(r'^[-*_]{3,}$', stripped):
                result.append('<hr />')
                i += 1
                continue

            # Table
            if '|' in stripped and i + 1 < len(lines):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if re.match(r'^\|[\s\-:|]+\|$', next_line):
                    headers = [c.strip() for c in stripped.strip('|').split('|')]
                    i += 2  # skip header + separator
                    rows = []
                    while i < len(lines) and '|' in lines[i].strip():
                        cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                        rows.append(cells)
                        i += 1
                    tbl = '<table><tbody><tr>'
                    tbl += ''.join(f'<th>{inline(h)}</th>' for h in headers)
                    tbl += '</tr>'
                    for row in rows:
                        tbl += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>'
                    tbl += '</tbody></table>'
                    result.append(tbl)
                    continue

            # Unordered list
            if re.match(r'^[-*+]\s', stripped):
                items = []
                while i < len(lines) and re.match(r'^\s*[-*+]\s', lines[i]):
                    item_text = re.sub(r'^\s*[-*+]\s+', '', lines[i])
                    items.append(f'<li>{inline(item_text)}</li>')
                    i += 1
                result.append('<ul>' + ''.join(items) + '</ul>')
                continue

            # Ordered list
            if re.match(r'^\d+\.\s', stripped):
                items = []
                while i < len(lines) and re.match(r'^\s*\d+\.\s', lines[i]):
                    item_text = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                    items.append(f'<li>{inline(item_text)}</li>')
                    i += 1
                result.append('<ol>' + ''.join(items) + '</ol>')
                continue

            # Empty line
            if not stripped:
                i += 1
                continue

            # Paragraph: collect consecutive non-special lines
            para = []
            while i < len(lines):
                ln = lines[i].strip()
                if (not ln or ln.startswith('#') or ln.startswith('```')
                        or re.match(r'^[-*_]{3,}$', ln)
                        or re.match(r'^[-*+]\s', ln)
                        or re.match(r'^\d+\.\s', ln)):
                    break
                # Check table start
                if '|' in ln and i + 1 < len(lines) and re.match(r'^\|[\s\-:|]+\|$', lines[i + 1].strip()):
                    break
                para.append(ln)
                i += 1
            if para:
                result.append(f'<p>{inline(" ".join(para))}</p>')

        return '\n'.join(result)

    def run(self, host: str = "127.0.0.1", port: int = 8501):
        import sys
        print(f"🌐 Web UI: http://{host}:{port}", flush=True)
        web.run_app(self.app, host=host, port=port, print=lambda msg: print(msg, flush=True))
