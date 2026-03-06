"""Structured information extraction from text.

Uses LangExtract for short texts (precise, example-based extraction)
and direct LLM prompting for long texts (handles long context natively).
"""
import json
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Structured extraction result."""
    entities: List[Dict]  # [{class, text, attributes}]
    source_title: str = ""
    raw_text: str = ""


# Pre-defined extraction profiles for common use cases
EXTRACTION_PROFILES = {
    "meeting": {
        "prompt": (
            "회의 내용에서 다음을 추출하세요:\n"
            "- agenda: 논의된 안건/주제\n"
            "- decision: 결정된 사항\n"
            "- action_item: 해야 할 일 (담당자, 기한 포함)\n"
            "- key_statement: 중요 발언\n"
            "원문 그대로 추출하고 순서대로 정리하세요."
        ),
        "examples": [
            {
                "text": "김부장: 다음 분기 마케팅 예산을 20% 증액하자. 이대리가 3월까지 계획서 작성해주세요.",
                "extractions": [
                    {"class": "agenda", "text": "다음 분기 마케팅 예산", "attributes": {"topic": "예산 증액"}},
                    {"class": "decision", "text": "20% 증액하자", "attributes": {"content": "마케팅 예산 20% 증액"}},
                    {"class": "action_item", "text": "이대리가 3월까지 계획서 작성", "attributes": {"assignee": "이대리", "deadline": "3월"}},
                ],
            }
        ],
    },
    "tech_review": {
        "prompt": (
            "기술 문서에서 다음을 추출하세요:\n"
            "- feature: 주요 기능/특징\n"
            "- architecture: 아키텍처/구조 관련 내용\n"
            "- requirement: 요구사항/의존성\n"
            "- example: 코드 예시/사용법\n"
            "- limitation: 제한사항/주의점\n"
            "원문 그대로 추출하세요."
        ),
        "examples": [
            {
                "text": "LangExtract supports local inference using Ollama. Install from ollama.com. Note: OpenAI models require fence_output=True.",
                "extractions": [
                    {"class": "feature", "text": "supports local inference using Ollama", "attributes": {"type": "LLM support"}},
                    {"class": "requirement", "text": "Install from ollama.com", "attributes": {"dependency": "Ollama"}},
                    {"class": "limitation", "text": "OpenAI models require fence_output=True", "attributes": {"scope": "OpenAI"}},
                ],
            }
        ],
    },
    "research": {
        "prompt": (
            "리서치 자료에서 다음을 추출하세요:\n"
            "- finding: 주요 발견/결론\n"
            "- data_point: 구체적 수치/통계\n"
            "- comparison: 비교 내용\n"
            "- recommendation: 제안/권고사항\n"
            "- reference: 출처/인용\n"
            "원문 그대로 추출하세요."
        ),
        "examples": [
            {
                "text": "실험 결과 A 모델이 95% 정확도로 B 모델(87%)보다 우수했다. 프로덕션에서는 A 모델 사용을 권장한다.",
                "extractions": [
                    {"class": "data_point", "text": "A 모델이 95% 정확도", "attributes": {"metric": "accuracy", "value": "95%"}},
                    {"class": "comparison", "text": "A 모델이 95% 정확도로 B 모델(87%)보다 우수", "attributes": {"winner": "A", "loser": "B"}},
                    {"class": "recommendation", "text": "프로덕션에서는 A 모델 사용을 권장", "attributes": {"context": "production"}},
                ],
            }
        ],
    },
    "ux_research": {
        "prompt": (
            "UX 리서치 자료에서 다음을 추출하세요:\n"
            "- user_need: 사용자 니즈/요구사항/불편사항\n"
            "- persona: 사용자 유형/페르소나 특성\n"
            "- insight: 핵심 인사이트/발견\n"
            "- pain_point: 사용자 페인포인트/허들\n"
            "- task_flow: 사용자 행동 흐름/태스크 시나리오\n"
            "- quote: 사용자 원문 발언/피드백\n"
            "- metric: UX 지표(완료율, 이탈률, SUS, NPS 등)\n"
            "- recommendation: 개선 제안/디자인 권고\n"
            "원문 그대로 추출하고 맥락을 보존하세요."
        ),
        "examples": [
            {
                "text": (
                    "인터뷰 참여자 P3(30대, 마케터): '검색 결과가 너무 많아서 원하는 걸 찾기가 어려워요. "
                    "필터를 눌러도 뭐가 뭔지 모르겠어요.' 태스크 완료율 42%, 평균 소요시간 3분 20초. "
                    "검색→필터→결과확인→재검색 루프가 반복됨. 필터 라벨을 사용자 언어로 변경하고, "
                    "인기 필터 조합을 추천하는 방안을 제안한다."
                ),
                "extractions": [
                    {"class": "persona", "text": "P3(30대, 마케터)", "attributes": {"age_group": "30대", "role": "마케터"}},
                    {"class": "quote", "text": "검색 결과가 너무 많아서 원하는 걸 찾기가 어려워요", "attributes": {"participant": "P3"}},
                    {"class": "pain_point", "text": "필터를 눌러도 뭐가 뭔지 모르겠어요", "attributes": {"area": "검색 필터"}},
                    {"class": "metric", "text": "태스크 완료율 42%, 평균 소요시간 3분 20초", "attributes": {"completion_rate": "42%", "avg_time": "3분 20초"}},
                    {"class": "task_flow", "text": "검색→필터→결과확인→재검색 루프가 반복됨", "attributes": {"pattern": "반복 루프"}},
                    {"class": "recommendation", "text": "필터 라벨을 사용자 언어로 변경하고, 인기 필터 조합을 추천", "attributes": {"type": "UI 개선"}},
                ],
            }
        ],
    },
    "general": {
        "prompt": (
            "텍스트에서 다음을 추출하세요:\n"
            "- key_point: 핵심 내용/요점\n"
            "- entity: 중요한 이름/용어/개념\n"
            "- relation: 관계/연결\n"
            "원문 그대로 추출하세요."
        ),
        "examples": [
            {
                "text": "Google이 LangExtract를 오픈소스로 공개했다. Gemini 모델을 기반으로 비정형 텍스트에서 구조화된 정보를 추출한다.",
                "extractions": [
                    {"class": "entity", "text": "Google", "attributes": {"type": "organization"}},
                    {"class": "entity", "text": "LangExtract", "attributes": {"type": "library"}},
                    {"class": "key_point", "text": "비정형 텍스트에서 구조화된 정보를 추출", "attributes": {"topic": "core function"}},
                    {"class": "relation", "text": "Gemini 모델을 기반으로", "attributes": {"type": "dependency"}},
                ],
            }
        ],
    },
}


class StructuredExtractor:
    """Extract structured information using LangExtract."""

    def __init__(
        self,
        model_id: str = "gemma2:2b",
        model_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model_id = model_id
        self.model_url = model_url
        self.api_key = api_key

    # LangExtract works well under this limit; above it, use direct LLM extraction
    LANGEXTRACT_MAX = 4000

    async def extract(
        self,
        text: str,
        profile: str = "general",
        custom_prompt: Optional[str] = None,
    ) -> ExtractionResult:
        """Run structured extraction on text.

        Short texts (<=4000 chars) use LangExtract for precise, example-based extraction.
        Long texts use the main LLM directly with a structured extraction prompt.
        """
        if len(text) <= self.LANGEXTRACT_MAX:
            entities = await self._extract_with_langextract(text, profile, custom_prompt)
        else:
            logger.info("Text too long for LangExtract (%d chars), using direct LLM extraction", len(text))
            entities = await self._extract_with_llm(text, profile, custom_prompt)

        return ExtractionResult(entities=entities, raw_text=text)

    async def _extract_with_langextract(
        self,
        text: str,
        profile: str = "general",
        custom_prompt: Optional[str] = None,
    ) -> List[Dict]:
        """Extract entities using LangExtract (best for short texts)."""
        import langextract as lx

        prof = EXTRACTION_PROFILES.get(profile, EXTRACTION_PROFILES["general"])
        prompt = custom_prompt or prof["prompt"]

        examples = []
        for ex in prof["examples"]:
            extractions = [
                lx.data.Extraction(
                    extraction_class=e["class"],
                    extraction_text=e["text"],
                    attributes=e.get("attributes", {}),
                )
                for e in ex["extractions"]
            ]
            examples.append(lx.data.ExampleData(text=ex["text"], extractions=extractions))

        kwargs = {
            "text_or_documents": text,
            "prompt_description": prompt,
            "examples": examples,
            "model_id": self.model_id,
            "fence_output": True,
            "use_schema_constraints": False,
        }

        if self.model_url and not self.api_key:
            kwargs["model_url"] = self.model_url
        elif self.api_key:
            kwargs["api_key"] = self.api_key

        try:
            result = lx.extract(**kwargs)
        except Exception as e:
            error_msg = str(e)
            if "JSON" in error_msg or "parse" in error_msg.lower() or "extractions" in error_msg.lower():
                try:
                    kwargs["fence_output"] = False
                    result = lx.extract(**kwargs)
                except Exception as e2:
                    raise RuntimeError(
                        f"LangExtract 추출 실패 (model: {self.model_id}, url: {self.model_url}):\n"
                        f"첫 시도: {error_msg}\n재시도: {str(e2)}"
                    ) from e2
            else:
                raise RuntimeError(
                    f"LangExtract 추출 실패 (model: {self.model_id}): {error_msg}"
                ) from e

        entities = []
        if hasattr(result, "extractions"):
            for ext in result.extractions:
                entities.append({
                    "class": ext.extraction_class,
                    "text": ext.extraction_text,
                    "attributes": ext.attributes if hasattr(ext, "attributes") else {},
                })
        return entities

    async def _extract_with_llm(
        self,
        text: str,
        profile: str = "general",
        custom_prompt: Optional[str] = None,
    ) -> List[Dict]:
        """Extract entities using direct LLM call (handles long texts natively)."""
        import httpx

        prof = EXTRACTION_PROFILES.get(profile, EXTRACTION_PROFILES["general"])
        prompt_desc = custom_prompt or prof["prompt"]

        # Build example JSON from profile
        example_json = json.dumps(prof["examples"][0]["extractions"], ensure_ascii=False, indent=2) if prof["examples"] else "[]"

        llm_prompt = f"""{prompt_desc}

반드시 아래 JSON 배열 형식으로만 출력하세요. 다른 텍스트 없이 JSON만 출력하세요.

출력 예시:
{example_json}

분석할 텍스트:
{text}"""

        # Call LLM directly
        try:
            if self.model_url and not self.api_key:
                # Ollama
                url = f"{self.model_url}/v1/chat/completions"
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(url, json={
                        "model": self.model_id,
                        "messages": [{"role": "user", "content": llm_prompt}],
                        "stream": False,
                        "temperature": 0.1,
                    })
                    resp.raise_for_status()
                    content = resp.json()["choices"][0]["message"]["content"]
            elif self.api_key:
                # Anthropic
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": self.model_id,
                            "max_tokens": 4096,
                            "messages": [{"role": "user", "content": llm_prompt}],
                        },
                    )
                    resp.raise_for_status()
                    content = resp.json()["content"][0]["text"]
            else:
                raise RuntimeError("LLM URL 또는 API 키가 설정되지 않았습니다")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM 추출 호출 실패: {e}") from e

        # Parse JSON from LLM response
        return self._parse_llm_json(content)

    @staticmethod
    def _parse_llm_json(content: str) -> List[Dict]:
        """Parse JSON array from LLM response, handling markdown fences."""
        content = content.strip()

        # Strip markdown code fences
        if content.startswith("```"):
            lines = content.split("\n")
            lines = lines[1:]  # remove opening ```json or ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                try:
                    data = json.loads(content[start:end + 1])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM extraction response")
                    return []
            else:
                logger.warning("No JSON array found in LLM extraction response")
                return []

        if not isinstance(data, list):
            data = [data]

        entities = []
        for item in data:
            if isinstance(item, dict) and "class" in item and "text" in item:
                entities.append({
                    "class": item["class"],
                    "text": item["text"],
                    "attributes": item.get("attributes", {}),
                })
        return entities

    async def extract_with_visualization(
        self,
        text: str,
        profile: str = "general",
        output_dir: str = ".",
    ) -> tuple:
        """Run extraction and generate interactive HTML visualization.

        Returns:
            (ExtractionResult, html_string)
        """
        import langextract as lx
        from pathlib import Path

        # LangExtract visualization needs a single result object; use truncated text
        viz_text = text[:self.LANGEXTRACT_MAX]

        prof = EXTRACTION_PROFILES.get(profile, EXTRACTION_PROFILES["general"])

        examples = []
        for ex in prof["examples"]:
            extractions = [
                lx.data.Extraction(
                    extraction_class=e["class"],
                    extraction_text=e["text"],
                    attributes=e.get("attributes", {}),
                )
                for e in ex["extractions"]
            ]
            examples.append(lx.data.ExampleData(text=ex["text"], extractions=extractions))

        kwargs = {
            "text_or_documents": viz_text,
            "prompt_description": prof["prompt"],
            "examples": examples,
            "model_id": self.model_id,
            "fence_output": True,
            "use_schema_constraints": False,
        }
        if self.model_url and not self.api_key:
            kwargs["model_url"] = self.model_url
        elif self.api_key:
            kwargs["api_key"] = self.api_key

        try:
            result = lx.extract(**kwargs)
        except Exception as e:
            error_msg = str(e)
            if "JSON" in error_msg or "parse" in error_msg.lower() or "extractions" in error_msg.lower():
                kwargs["fence_output"] = False
                result = lx.extract(**kwargs)
            else:
                raise

        # Save to JSONL for visualization
        jsonl_path = str(Path(output_dir) / "extraction_results.jsonl")
        lx.io.save_annotated_documents([result], output_name="extraction_results.jsonl", output_dir=output_dir)

        # Generate HTML visualization
        html_content = lx.visualize(jsonl_path)
        html_str = ""
        if hasattr(html_content, 'data'):
            html_str = html_content.data
        elif isinstance(html_content, str):
            html_str = html_content

        # Full extraction with chunking for complete entities
        full_result = await self.extract(text, profile)

        return full_result, html_str

    def format_entities_as_context(self, result: ExtractionResult) -> str:
        """Format extracted entities as structured context for LLM."""
        if not result.entities:
            return ""

        lines = []
        if result.source_title:
            lines.append(f"### 소스: {result.source_title}\n")

        by_class = {}
        for e in result.entities:
            by_class.setdefault(e["class"], []).append(e)

        for cls, items in by_class.items():
            lines.append(f"#### {cls}")
            for item in items:
                attrs = ", ".join(f"{k}: {v}" for k, v in item.get("attributes", {}).items())
                line = f"- {item['text']}"
                if attrs:
                    line += f" ({attrs})"
                lines.append(line)
            lines.append("")

        return "\n".join(lines)

    def format_multi_results_as_context(self, results: List[ExtractionResult]) -> str:
        """Format multiple extraction results as combined structured context for LLM."""
        sections = []
        for result in results:
            section = self.format_entities_as_context(result)
            if section:
                sections.append(section)

        if not sections:
            return ""

        return "## 구조화 추출 결과\n\n" + "\n---\n\n".join(sections)
