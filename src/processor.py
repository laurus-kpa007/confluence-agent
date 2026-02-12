"""LLM processor - takes extracted content and generates Confluence-formatted output."""
from typing import List, Optional
import httpx

from .adapters.base import SourceContent
from .templates import TemplateManager
from .extractor import StructuredExtractor


class LLMProcessor:
    """Process extracted content through LLM to generate Confluence pages."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen3:14b-128k",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        ssl_verify: bool = True,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.ssl_verify = ssl_verify
        self.templates = TemplateManager()
        self.extractor = None  # Lazy init

    def _get_extractor(self) -> StructuredExtractor:
        if not self.extractor:
            # Use smaller model for extraction (faster)
            self.extractor = StructuredExtractor(
                model_id="gemma2:2b",
                model_url=self.base_url if self.provider == "ollama" else None,
                api_key=self.api_key if self.provider != "ollama" else None,
            )
        return self.extractor

    async def process(
        self,
        contents: List[SourceContent],
        template: str = "summary",
        output_format: str = "markdown",
        use_langextract: bool = False,
        extraction_profile: str = "general",
        output_length: str = "normal",
    ) -> str:
        """Generate formatted content from extracted sources.

        Args:
            use_langextract: If True, run LangExtract for structured extraction first
            extraction_profile: LangExtract profile (meeting, tech_review, research, general)
            output_length: Output length - "compact", "normal", "detailed", "comprehensive"
        """

        # Combine all source contents
        combined = self._combine_contents(contents)

        # Optional: structured extraction with LangExtract
        extraction_context = ""
        if use_langextract:
            try:
                extractor = self._get_extractor()
                # Extract from combined text (truncated for speed)
                result = await extractor.extract(
                    combined[:20000],
                    profile=extraction_profile,
                )
                extraction_context = extractor.format_entities_as_context(result)
                if extraction_context:
                    combined = f"{extraction_context}\n\n---\n\n## 원본 자료\n{combined}"
            except Exception as e:
                # Fallback: continue without extraction
                extraction_context = f"\n[LangExtract 추출 실패: {e}]\n"

        # Render template with content and format instructions
        prompt = self.templates.render(template, combined, output_format, output_length)

        # Call LLM
        response = await self._call_llm(prompt)
        return response

    def _combine_contents(self, contents: List[SourceContent]) -> str:
        parts = []
        for i, c in enumerate(contents, 1):
            header = f"--- 소스 {i}: [{c.source_type}] {c.title} ---"
            if c.source_url:
                header += f"\nURL: {c.source_url}"
            parts.append(f"{header}\n{c.text[:10000]}")  # Limit per source
        return "\n\n".join(parts)

    async def _call_llm(self, prompt: str) -> str:
        if self.provider == "ollama":
            return await self._call_ollama(prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _call_ollama(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0, verify=self.ssl_verify) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def _call_anthropic(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0, verify=self.ssl_verify) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
