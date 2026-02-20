"""LLM processor - takes extracted content and generates Confluence-formatted output."""
import json
import logging
from typing import AsyncIterator, List, Optional
import httpx

from .adapters.base import SourceContent
from .templates import TemplateManager
from .extractor import StructuredExtractor

logger = logging.getLogger(__name__)


class LLMProcessor:
    """Process extracted content through LLM to generate Confluence pages."""

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "gemma3:4b",
        base_url: str = "",
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
        logger.debug("LLMProcessor init: provider=%s, model=%s, base_url=%s, ssl_verify=%s", provider, model, base_url, ssl_verify)

    def _get_extractor(self) -> StructuredExtractor:
        if not self.extractor:
            # Use same model as main LLM for consistency and speed
            self.extractor = StructuredExtractor(
                model_id=self.model,  # Use main model (e.g., gemma3:4b)
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
        output_language: str = "ko",
    ) -> str:
        """Generate formatted content from extracted sources.

        Args:
            use_langextract: If True, run LangExtract for structured extraction first
            extraction_profile: LangExtract profile (meeting, tech_review, research, general)
            output_length: Output length - "compact", "normal", "detailed", "comprehensive"
            output_language: Output language code - "ko", "en", "ja", "zh"
        """

        logger.info("Processing %d source(s), template=%s, length=%s, language=%s", len(contents), template, output_length, output_language)

        # Combine all source contents
        combined = self._combine_contents(contents)
        logger.debug("Combined content length: %d chars", len(combined))

        # Optional: structured extraction with LangExtract
        extraction_context = ""
        if use_langextract:
            try:
                extractor = self._get_extractor()
                # Extract from combined text (truncated for stability and speed)
                # Limit to 5000 chars to avoid JSON parsing issues
                result = await extractor.extract(
                    combined[:5000],
                    profile=extraction_profile,
                )
                extraction_context = extractor.format_entities_as_context(result)
                if extraction_context:
                    combined = f"{extraction_context}\n\n---\n\n## 원본 자료\n{combined}"
            except Exception as e:
                # Fallback: continue without extraction
                extraction_context = f"\n[LangExtract 추출 실패: {e}]\n"

        # Render template with content and format instructions
        prompt = self.templates.render(template, combined, output_format, output_length, output_language)

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
        url = f"{self.base_url}/v1/chat/completions"
        logger.debug("Calling Ollama: %s model=%s prompt_len=%d", url, self.model, len(prompt))
        # Increased timeout to 300s (5 min) for LangExtract processing
        async with httpx.AsyncClient(timeout=300.0, verify=self.ssl_verify) as client:
            resp = await client.post(
                url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "temperature": 0.3,
                },
            )
            logger.debug("Ollama response: status=%d", resp.status_code)
            resp.raise_for_status()
            result = resp.json()["choices"][0]["message"]["content"]
            logger.debug("Ollama result length: %d chars", len(result))
            return result

    async def _call_anthropic(self, prompt: str) -> str:
        logger.debug("Calling Anthropic: model=%s prompt_len=%d", self.model, len(prompt))
        # Increased timeout to 300s (5 min) for complex processing
        async with httpx.AsyncClient(timeout=300.0, verify=self.ssl_verify) as client:
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
            logger.debug("Anthropic response: status=%d", resp.status_code)
            resp.raise_for_status()
            result = resp.json()["content"][0]["text"]
            logger.debug("Anthropic result length: %d chars", len(result))
            return result

    # --- Streaming methods ---

    async def stream_llm(self, prompt: str) -> AsyncIterator[str]:
        """Stream LLM response chunk by chunk."""
        if self.provider == "ollama":
            async for chunk in self._stream_ollama(prompt):
                yield chunk
        elif self.provider == "anthropic":
            async for chunk in self._stream_anthropic(prompt):
                yield chunk
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _stream_ollama(self, prompt: str) -> AsyncIterator[str]:
        """Stream from Ollama using /v1/chat/completions with stream=True."""
        url = f"{self.base_url}/v1/chat/completions"
        logger.debug("Streaming Ollama: %s model=%s", url, self.model)
        async with httpx.AsyncClient(timeout=300.0, verify=self.ssl_verify) as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                    "temperature": 0.3,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue

    async def _stream_anthropic(self, prompt: str) -> AsyncIterator[str]:
        """Stream from Anthropic using /v1/messages with stream=True."""
        logger.debug("Streaming Anthropic: model=%s", self.model)
        async with httpx.AsyncClient(timeout=300.0, verify=self.ssl_verify) as client:
            async with client.stream(
                "POST",
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
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        if obj.get("type") == "content_block_delta":
                            text = obj.get("delta", {}).get("text", "")
                            if text:
                                yield text
                    except (json.JSONDecodeError, KeyError):
                        continue
