"""LLM processor - takes extracted content and generates Confluence-formatted output."""
from typing import List, Optional
import httpx

from .adapters.base import SourceContent
from .templates import TemplateManager


class LLMProcessor:
    """Process extracted content through LLM to generate Confluence pages."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "qwen3:14b-128k",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
    ):
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.templates = TemplateManager()

    async def process(
        self,
        contents: List[SourceContent],
        template: str = "summary",
        output_format: str = "markdown",
    ) -> str:
        """Generate formatted content from extracted sources."""

        # Combine all source contents
        combined = self._combine_contents(contents)

        # Render template with content and format instructions
        prompt = self.templates.render(template, combined, output_format)

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
        async with httpx.AsyncClient(timeout=120.0) as client:
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
        async with httpx.AsyncClient(timeout=120.0) as client:
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
