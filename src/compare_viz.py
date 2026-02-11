"""Side-by-side comparison visualization: Input (highlighted) vs Output (structured).

Shows the original text with entity highlights on the left,
and the structured extraction results on the right.
"""
import html
from typing import List, Dict


def generate_comparison_html(
    original_text: str,
    entities: List[Dict],
    structured_output: str = "",
    title: str = "LangExtract 추출 비교",
) -> str:
    """Generate side-by-side comparison HTML.
    
    Args:
        original_text: Raw input text
        entities: List of {class, text, attributes}
        structured_output: Formatted markdown/text output from LLM
        title: Page title
    """

    # Color map for entity classes
    COLORS = {
        "feature": {"bg": "#e8f5e9", "border": "#4caf50", "label": "🟢 기능"},
        "requirement": {"bg": "#e3f2fd", "border": "#2196f3", "label": "🔵 요구사항"},
        "limitation": {"bg": "#fce4ec", "border": "#f44336", "label": "🔴 제한사항"},
        "architecture": {"bg": "#f3e5f5", "border": "#9c27b0", "label": "🟣 아키텍처"},
        "example": {"bg": "#fff3e0", "border": "#ff9800", "label": "🟠 예시"},
        "agenda": {"bg": "#e8f5e9", "border": "#4caf50", "label": "🟢 안건"},
        "decision": {"bg": "#e3f2fd", "border": "#2196f3", "label": "🔵 결정"},
        "action_item": {"bg": "#fce4ec", "border": "#f44336", "label": "🔴 액션"},
        "key_statement": {"bg": "#fff3e0", "border": "#ff9800", "label": "🟠 발언"},
        "finding": {"bg": "#e8f5e9", "border": "#4caf50", "label": "🟢 발견"},
        "data_point": {"bg": "#e3f2fd", "border": "#2196f3", "label": "🔵 수치"},
        "comparison": {"bg": "#f3e5f5", "border": "#9c27b0", "label": "🟣 비교"},
        "recommendation": {"bg": "#fff3e0", "border": "#ff9800", "label": "🟠 권고"},
        "reference": {"bg": "#efebe9", "border": "#795548", "label": "🟤 출처"},
        "key_point": {"bg": "#e8f5e9", "border": "#4caf50", "label": "🟢 핵심"},
        "entity": {"bg": "#e3f2fd", "border": "#2196f3", "label": "🔵 엔티티"},
        "relation": {"bg": "#f3e5f5", "border": "#9c27b0", "label": "🟣 관계"},
    }
    DEFAULT_COLOR = {"bg": "#f5f5f5", "border": "#9e9e9e", "label": "⚪ 기타"}

    # Build highlighted text
    highlighted = _highlight_text(original_text, entities, COLORS, DEFAULT_COLOR)

    # Build entity cards
    entity_cards = _build_entity_cards(entities, COLORS, DEFAULT_COLOR)

    # Build legend
    used_classes = set(e["class"] for e in entities)
    legend_items = []
    for cls in used_classes:
        c = COLORS.get(cls, DEFAULT_COLOR)
        legend_items.append(
            f'<span class="legend-item" data-class="{cls}" onclick="toggleClass(\'{cls}\')">'
            f'<span class="legend-dot" style="background:{c["border"]}"></span>'
            f'{c["label"]} ({sum(1 for e in entities if e["class"]==cls)})'
            f'</span>'
        )
    legend_html = " ".join(legend_items)

    # Stats
    stats = f"{len(entities)}개 엔티티 · {len(used_classes)}개 클래스 · {len(original_text):,}자 원문"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{html.escape(title)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, 'Pretendard', 'Segoe UI', sans-serif; background: #f8f9fa; }}
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white; padding: 20px 32px;
}}
.header h1 {{ font-size: 1.4em; margin-bottom: 8px; }}
.header .stats {{ font-size: 0.85em; opacity: 0.8; }}
.legend {{
    padding: 12px 32px; background: white;
    border-bottom: 1px solid #e0e0e0;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
}}
.legend-item {{
    display: flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 16px; font-size: 0.8em;
    cursor: pointer; transition: all 0.2s;
    background: #f5f5f5;
}}
.legend-item:hover {{ background: #e0e0e0; }}
.legend-item.hidden {{ opacity: 0.3; text-decoration: line-through; }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
.main {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 0; height: calc(100vh - 130px);
}}
.panel {{
    overflow-y: auto; padding: 24px;
}}
.panel-header {{
    font-size: 0.9em; font-weight: 700; color: #666;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 16px; padding-bottom: 8px;
    border-bottom: 2px solid #e0e0e0;
}}
.panel-left {{ background: white; border-right: 1px solid #e0e0e0; }}
.panel-right {{ background: #fafafa; }}

/* Highlighted text */
.source-text {{
    line-height: 1.8; font-size: 0.95em; color: #333;
    white-space: pre-wrap; word-wrap: break-word;
}}
.highlight {{
    padding: 2px 4px; border-radius: 4px;
    border-bottom: 2px solid; cursor: pointer;
    transition: all 0.2s; position: relative;
}}
.highlight:hover {{
    filter: brightness(0.9);
}}
.highlight .tooltip {{
    display: none; position: absolute; bottom: 100%; left: 0;
    background: #333; color: white; padding: 6px 10px;
    border-radius: 6px; font-size: 0.75em; white-space: nowrap;
    z-index: 10;
}}
.highlight:hover .tooltip {{ display: block; }}

/* Entity cards */
.entity-card {{
    background: white; border-radius: 8px; padding: 12px 16px;
    margin-bottom: 8px; border-left: 4px solid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    transition: all 0.2s;
}}
.entity-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
.entity-card .class-label {{
    font-size: 0.7em; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 4px;
}}
.entity-card .text {{
    font-size: 0.9em; margin-bottom: 6px; color: #333;
}}
.entity-card .attrs {{
    font-size: 0.75em; color: #888;
}}
.entity-card .attrs span {{
    background: #f0f0f0; padding: 2px 8px; border-radius: 10px;
    margin-right: 4px;
}}

/* Hidden class */
.hidden-entity {{ display: none !important; }}

/* Responsive */
@media (max-width: 900px) {{
    .main {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
    <h1>🔬 {html.escape(title)}</h1>
    <div class="stats">{stats}</div>
</div>
<div class="legend">
    <span style="font-size:0.8em; color:#999; margin-right:8px;">필터:</span>
    {legend_html}
</div>
<div class="main">
    <div class="panel panel-left">
        <div class="panel-header">📄 Input — 원문 (하이라이트)</div>
        <div class="source-text">{highlighted}</div>
    </div>
    <div class="panel panel-right">
        <div class="panel-header">📊 Output — 추출된 엔티티 ({len(entities)})</div>
        <div id="entityList">{entity_cards}</div>
    </div>
</div>
<script>
const hiddenClasses = new Set();
function toggleClass(cls) {{
    const items = document.querySelectorAll('[data-class="'+cls+'"]');
    const legendItem = document.querySelector('.legend-item[data-class="'+cls+'"]');
    if (hiddenClasses.has(cls)) {{
        hiddenClasses.delete(cls);
        items.forEach(el => el.classList.remove('hidden-entity'));
        legendItem.classList.remove('hidden');
    }} else {{
        hiddenClasses.add(cls);
        items.forEach(el => el.classList.add('hidden-entity'));
        legendItem.classList.add('hidden');
    }}
}}
</script>
</body>
</html>"""


def _highlight_text(text: str, entities: List[Dict], colors: dict, default: dict) -> str:
    """Highlight entity mentions in the original text."""
    escaped = html.escape(text)

    # Sort entities by length (longest first) to avoid partial replacements
    sorted_entities = sorted(entities, key=lambda e: len(e["text"]), reverse=True)

    replaced = set()
    for e in sorted_entities:
        search = html.escape(e["text"])
        if search in replaced or search not in escaped:
            continue
        c = colors.get(e["class"], default)
        attrs_str = ", ".join(f"{k}: {v}" for k, v in e.get("attributes", {}).items())
        tooltip = f'{c["label"]}'
        if attrs_str:
            tooltip += f' — {attrs_str}'
        replacement = (
            f'<span class="highlight" data-class="{e["class"]}" '
            f'style="background:{c["bg"]}; border-color:{c["border"]}">'
            f'{search}'
            f'<span class="tooltip">{html.escape(tooltip)}</span>'
            f'</span>'
        )
        escaped = escaped.replace(search, replacement, 1)
        replaced.add(search)

    return escaped


def _build_entity_cards(entities: List[Dict], colors: dict, default: dict) -> str:
    """Build entity card HTML."""
    cards = []
    for i, e in enumerate(entities):
        c = colors.get(e["class"], default)
        attrs_html = ""
        if e.get("attributes"):
            spans = [f'<span>{html.escape(k)}: {html.escape(str(v))}</span>'
                     for k, v in e["attributes"].items()]
            attrs_html = f'<div class="attrs">{"".join(spans)}</div>'

        cards.append(
            f'<div class="entity-card" data-class="{e["class"]}" '
            f'style="border-color:{c["border"]}">'
            f'<div class="class-label" style="color:{c["border"]}">{c["label"]}</div>'
            f'<div class="text">{html.escape(e["text"][:200])}</div>'
            f'{attrs_html}'
            f'</div>'
        )
    return "\n".join(cards)
