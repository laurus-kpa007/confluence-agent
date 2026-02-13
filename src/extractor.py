"""LangExtract integration - structured information extraction from text.

Uses google/langextract to extract structured entities (decisions, action items,
key points, etc.) from raw text before LLM processing.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field


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

    async def extract(
        self,
        text: str,
        profile: str = "general",
        custom_prompt: Optional[str] = None,
    ) -> ExtractionResult:
        """Run structured extraction on text.

        Args:
            text: Input text to extract from
            profile: Extraction profile (meeting, tech_review, research, general)
            custom_prompt: Override profile prompt with custom instructions
        """
        import langextract as lx

        # Get profile
        prof = EXTRACTION_PROFILES.get(profile, EXTRACTION_PROFILES["general"])
        prompt = custom_prompt or prof["prompt"]

        # Build examples
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

        # Run extraction
        # Limit text size more aggressively for stability
        max_chars = 10000  # Reduce from 50000 to avoid JSON parsing issues
        text_chunk = text[:max_chars]

        kwargs = {
            "text_or_documents": text_chunk,
            "prompt_description": prompt,
            "examples": examples,
            "model_id": self.model_id,
            "fence_output": True,  # Enable fence output for better JSON parsing
            "use_schema_constraints": False,
        }

        # Use Ollama if model_url provided, otherwise cloud
        if self.model_url and not self.api_key:
            kwargs["model_url"] = self.model_url
        elif self.api_key:
            kwargs["api_key"] = self.api_key

        try:
            result = lx.extract(**kwargs)
        except Exception as e:
            error_msg = str(e)

            # Try fallback with fence_output=False if it was a JSON parsing error
            if "JSON" in error_msg or "parse" in error_msg.lower():
                try:
                    print(f"⚠️  JSON 파싱 오류 발생, fence_output=False로 재시도...")
                    kwargs["fence_output"] = False
                    # Also try with even smaller chunk
                    kwargs["text_or_documents"] = text[:5000]
                    result = lx.extract(**kwargs)
                    print(f"✅ 재시도 성공!")
                except Exception as e2:
                    raise RuntimeError(
                        f"LangExtract 추출 실패 (model: {self.model_id}, url: {self.model_url}):\n"
                        f"첫 시도: {error_msg}\n"
                        f"재시도: {str(e2)}\n"
                        f"Ollama가 실행 중인지 확인하세요: {self.model_url or 'LLM_BASE_URL 환경변수를 설정하세요'}"
                    ) from e2
            else:
                raise RuntimeError(
                    f"LangExtract 추출 실패 (model: {self.model_id}, url: {self.model_url}): {error_msg}\n"
                    f"Ollama가 실행 중인지 확인하세요: {self.model_url or 'LLM_BASE_URL 환경변수를 설정하세요'}"
                ) from e

        # Parse results
        entities = []
        if hasattr(result, "extractions"):
            for ext in result.extractions:
                entities.append({
                    "class": ext.extraction_class,
                    "text": ext.extraction_text,
                    "attributes": ext.attributes if hasattr(ext, "attributes") else {},
                })

        return ExtractionResult(entities=entities, raw_text=text)

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
            "text_or_documents": text[:50000],
            "prompt_description": prof["prompt"],
            "examples": examples,
            "model_id": self.model_id,
            "fence_output": False,
            "use_schema_constraints": False,
        }
        if self.model_url and not self.api_key:
            kwargs["model_url"] = self.model_url
        elif self.api_key:
            kwargs["api_key"] = self.api_key

        result = lx.extract(**kwargs)

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

        # Parse entities
        entities = []
        if hasattr(result, "extractions"):
            for ext in result.extractions:
                entities.append({
                    "class": ext.extraction_class,
                    "text": ext.extraction_text,
                    "attributes": ext.attributes if hasattr(ext, "attributes") else {},
                })

        return ExtractionResult(entities=entities, raw_text=text), html_str

    def format_entities_as_context(self, result: ExtractionResult) -> str:
        """Format extracted entities as structured context for LLM."""
        if not result.entities:
            return ""

        lines = ["## 구조화 추출 결과\n"]
        by_class = {}
        for e in result.entities:
            by_class.setdefault(e["class"], []).append(e)

        for cls, items in by_class.items():
            lines.append(f"### {cls}")
            for item in items:
                attrs = ", ".join(f"{k}: {v}" for k, v in item.get("attributes", {}).items())
                line = f"- {item['text']}"
                if attrs:
                    line += f" ({attrs})"
                lines.append(line)
            lines.append("")

        return "\n".join(lines)
