"""Structured information extraction from text using LangExtract.

Uses LangExtract's native smart chunking, parallel processing, and multi-pass
extraction to handle both short and long texts efficiently.
"""
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

    async def extract(
        self,
        text: str,
        profile: str = "general",
        custom_prompt: Optional[str] = None,
    ) -> ExtractionResult:
        """Run structured extraction on text using LangExtract.

        Uses LangExtract's native smart chunking (max_char_buffer),
        parallel processing (max_workers), and multi-pass extraction
        (extraction_passes) to handle any text length.
        """
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

        # Adjust parameters based on text length
        text_len = len(text)
        if text_len <= 4000:
            max_char_buffer = text_len  # Short text: single chunk
            max_workers = 1
            extraction_passes = 1
        elif text_len <= 20000:
            max_char_buffer = 4000     # Medium: ~5 chunks, parallel
            max_workers = 4
            extraction_passes = 1
        else:
            max_char_buffer = 6000     # Long: larger chunks, parallel + multi-pass
            max_workers = 8
            extraction_passes = 2

        logger.info(
            "LangExtract: %d chars, buffer=%d, workers=%d, passes=%d",
            text_len, max_char_buffer, max_workers, extraction_passes,
        )

        kwargs = {
            "text_or_documents": text,
            "prompt_description": prompt,
            "examples": examples,
            "model_id": self.model_id,
            "max_char_buffer": max_char_buffer,
            "max_workers": max_workers,
            "extraction_passes": extraction_passes,
            "fence_output": True,
            "use_schema_constraints": False,
            "show_progress": False,  # We handle progress in the UI layer
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
                        f"LangExtract 추출 실패 (model: {self.model_id}):\n"
                        f"첫 시도: {error_msg}\n재시도: {str(e2)}"
                    ) from e2
            else:
                raise RuntimeError(
                    f"LangExtract 추출 실패 (model: {self.model_id}): {error_msg}"
                ) from e

        # Parse results — handle both single doc and list of docs
        entities = []
        results = result if isinstance(result, list) else [result]
        for doc in results:
            if hasattr(doc, "extractions"):
                for ext in doc.extractions:
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

        # Run full extraction
        full_result = await self.extract(text, profile)

        # For visualization, we need the raw lx result object
        # Re-run on a preview chunk for lx.visualize compatibility
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

        viz_kwargs = {
            "text_or_documents": text[:4000],
            "prompt_description": prof["prompt"],
            "examples": examples,
            "model_id": self.model_id,
            "max_char_buffer": 4000,
            "fence_output": True,
            "use_schema_constraints": False,
            "show_progress": False,
        }
        if self.model_url and not self.api_key:
            viz_kwargs["model_url"] = self.model_url
        elif self.api_key:
            viz_kwargs["api_key"] = self.api_key

        try:
            viz_result = lx.extract(**viz_kwargs)
        except Exception:
            viz_kwargs["fence_output"] = False
            viz_result = lx.extract(**viz_kwargs)

        # Generate visualization HTML
        jsonl_path = str(Path(output_dir) / "extraction_results.jsonl")
        viz_doc = viz_result if not isinstance(viz_result, list) else viz_result[0]
        lx.io.save_annotated_documents([viz_doc], output_name="extraction_results.jsonl", output_dir=output_dir)

        html_content = lx.visualize(jsonl_path)
        html_str = ""
        if hasattr(html_content, 'data'):
            html_str = html_content.data
        elif isinstance(html_content, str):
            html_str = html_content

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
