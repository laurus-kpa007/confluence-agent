"""Template manager - external template files that users can edit anytime."""
from pathlib import Path
from typing import Dict, List

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Default templates (created on first run)
DEFAULT_TEMPLATES = {
    "summary": """다음 자료들을 정리해주세요.

규칙:
- {format_instructions}
- 핵심 내용만 간결하게 정리
- 출처 링크 포함
- 표가 적절하면 사용
- 코드가 있으면 코드 블록 사용

자료:
{content}""",

    "meeting_notes": """다음 자료를 회의록 형식으로 정리해주세요.

형식:
## 회의 개요
- 일시, 참석자, 목적

## 논의 사항
- 안건별 정리

## 결정 사항
- 확정된 내용

## 액션 아이템
| 담당자 | 내용 | 기한 |
|--------|------|------|
| | | |

{format_instructions}

자료:
{content}""",

    "tech_doc": """다음 자료를 기술 문서 형식으로 정리해주세요.

형식:
## 개요
기술/도구 소개

## 주요 기능
핵심 기능 목록

## 아키텍처
구조 설명

## 사용 방법
코드 예시 포함

## 참고
링크, 레퍼런스

{format_instructions}

자료:
{content}""",

    "research": """다음 자료들을 리서치 노트로 종합 정리해주세요.

형식:
## 요약
핵심 인사이트 3-5줄

## 상세 내용
소스별 주요 내용

## 비교/분석
소스 간 공통점/차이점

## 결론 및 제언
시사점

## 출처
소스 목록

{format_instructions}

자료:
{content}""",

    "weekly_report": """다음 자료를 주간 보고서 형식으로 정리해주세요.

형식:
## 금주 실적
- 완료된 항목

## 이슈 및 리스크
- 문제점, 대응 방안

## 차주 계획
- 예정 업무

## 기타 특이사항

{format_instructions}

자료:
{content}""",
}

# Format instructions by output type
FORMAT_INSTRUCTIONS = {
    "confluence": """Confluence Storage Format (XHTML)으로 출력하세요.
반드시 먼저 <h1>으로 전체 문서의 제목을 작성하세요.
사용할 태그: <h1>, <h2>, <h3>, <p>, <ul>, <ol>, <li>, <table>, <tbody>, <tr>, <th>, <td>, <strong>, <em>, <a>, <code>, <hr />
코드 블록은 반드시 이 형식으로: <ac:structured-macro ac:name="code"><ac:parameter ac:name="language">언어</ac:parameter><ac:plain-text-body><![CDATA[코드]]></ac:plain-text-body></ac:structured-macro>
절대 사용 금지: {code}, {panel}, {note}, {info}, {warning}, {tip}, {toc}, {excerpt}, {noformat} 등 위키 마크업 매크로 문법""",
    "markdown": """마크다운 형식으로 출력하세요.
반드시 먼저 # 으로 전체 문서의 제목을 작성하세요.
사용할 문법: # 제목, ## 소제목, **굵게**, *기울임*, `인라인코드`, ```코드블록```, |테이블|, - 목록, 1. 번호목록
절대 사용 금지: {code}, {panel}, {note} 등 Confluence 위키 매크로 문법""",
}


class TemplateManager:
    """Manages editable template files."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.dir = templates_dir
        self._ensure_defaults()

    def _ensure_defaults(self):
        """Create default template files if they don't exist."""
        self.dir.mkdir(parents=True, exist_ok=True)
        for name, content in DEFAULT_TEMPLATES.items():
            path = self.dir / f"{name}.txt"
            if not path.exists():
                path.write_text(content, encoding="utf-8")

    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates."""
        templates = []
        for f in sorted(self.dir.glob("*.txt")):
            templates.append({
                "name": f.stem,
                "path": str(f),
                "size": f.stat().st_size,
            })
        return templates

    def get_template(self, name: str) -> str:
        """Get template content by name."""
        path = self.dir / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {name}")
        return path.read_text(encoding="utf-8")

    def save_template(self, name: str, content: str):
        """Save/update a template."""
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{name}.txt"
        path.write_text(content, encoding="utf-8")

    def delete_template(self, name: str):
        """Delete a template."""
        path = self.dir / f"{name}.txt"
        if path.exists():
            path.unlink()

    def render(self, name: str, content: str, output_format: str = "markdown", length: str = "normal", language: str = "ko") -> str:
        """Render template with content and format instructions.

        Args:
            name: Template name
            content: Source content
            output_format: markdown or confluence
            length: Output length - "compact", "normal", "detailed", "comprehensive"
            language: Output language code - "ko", "en", "ja", "zh"
        """
        template = self.get_template(name)
        fmt = FORMAT_INSTRUCTIONS.get(output_format, FORMAT_INSTRUCTIONS["markdown"])

        # Add length instructions with specific guidance
        length_instructions = {
            "compact": """
**출력 길이: 간결 (50%)**
- 핵심 요약만 3-5문단 이내
- 세부 설명 최소화
- 예시 1-2개만 포함
- 목표: 500-1000자""",
            "normal": """
**출력 길이: 보통 (100%)**
- 주요 내용을 적당히 정리
- 필요한 설명 포함
- 예시 2-3개 포함
- 목표: 1000-2000자""",
            "detailed": """
**출력 길이: 상세 (200%)**
- 모든 주요 내용 상세 설명
- 배경 정보와 컨텍스트 포함
- 예시 5개 이상 포함
- 각 섹션마다 충분한 설명
- 목표: 2000-4000자""",
            "comprehensive": """
**출력 길이: 매우 상세 (300%)**
- 모든 세부사항 완전히 설명
- 배경, 컨텍스트, 의미 모두 포함
- 가능한 모든 예시 포함
- 각 개념마다 심층 설명
- 관련 정보 모두 추가
- 목표: 4000-6000자 이상""",
        }
        length_inst = length_instructions.get(length, length_instructions["normal"])

        # Add language instructions
        language_instructions = {
            "ko": "**출력 언어: 한국어로 작성하세요.**",
            "en": "**Output Language: Write in English.**",
            "ja": "**出力言語: 日本語で書いてください。**",
            "zh": "**输出语言：请用中文写。**",
        }
        language_inst = language_instructions.get(language, language_instructions["ko"])

        # Combine format, length, and language instructions
        combined_instructions = f"{fmt}\n길이: {length_inst}\n{language_inst}"

        return template.format(content=content, format_instructions=combined_instructions)
