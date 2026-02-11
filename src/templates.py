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
    "confluence": "Confluence Storage Format (XHTML)으로 출력. <h2>, <table>, <ac:structured-macro> 등 사용",
    "markdown": "마크다운 형식으로 출력. ##, |테이블|, ```코드블록``` 등 사용",
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

    def render(self, name: str, content: str, output_format: str = "markdown", length: str = "normal") -> str:
        """Render template with content and format instructions.

        Args:
            name: Template name
            content: Source content
            output_format: markdown or confluence
            length: Output length - "compact", "normal", "detailed", "comprehensive"
        """
        template = self.get_template(name)
        fmt = FORMAT_INSTRUCTIONS.get(output_format, FORMAT_INSTRUCTIONS["markdown"])

        # Add length instructions
        length_instructions = {
            "compact": "간결하게 핵심만 요약 (현재 분량의 50%)",
            "normal": "적당한 분량으로 정리 (기본)",
            "detailed": "상세하게 정리 (현재 분량의 2배, 더 많은 예시와 설명 포함)",
            "comprehensive": "매우 상세하게 정리 (현재 분량의 3배, 모든 세부사항 포함)",
        }
        length_inst = length_instructions.get(length, length_instructions["normal"])

        # Combine format and length instructions
        combined_instructions = f"{fmt}\n길이: {length_inst}"

        return template.format(content=content, format_instructions=combined_instructions)
