# Confluence Knowledge Agent

멀티소스 자료를 수집 → 로컬 LLM으로 정리 → Confluence에 자동 삽입하는 경량 에이전트

**📖 문서:**
- **[⚡ QUICKSTART.md](QUICKSTART.md)** - 5분 안에 시작하기
- **[🔧 SETUP.md](SETUP.md)** - 상세 설정 가이드
- **[🩺 TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 문제 해결 가이드
- **[🔬 LANGEXTRACT_USAGE.md](LANGEXTRACT_USAGE.md)** - LangExtract 사용법 및 역할
- **[📦 ENTITY_VIEWER.md](ENTITY_VIEWER.md)** - 엔티티 뷰어 (구조화된 정보 시각화)
- **[📊 ANALYSIS.md](ANALYSIS.md)** - 기술 분석 보고서
- **[📝 CHANGELOG.md](CHANGELOG.md)** - 변경 이력

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Source Adapters (MCP)                  │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Web URL  │ │ YouTube  │ │ G-Drive  │ │ SharePoint │ │
│  │ Scraper  │ │ Subtitle │ │   MCP    │ │    MCP     │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘ │
│       │             │            │              │        │
│  ┌────┴─────┐ ┌────┴─────┐ ┌───┴──────┐ ┌────┴──────┐ │
│  │ Local FS │ │ Notion   │ │ Slack    │ │ Custom    │ │
│  │  Files   │ │   MCP    │ │   MCP    │ │   MCP     │ │
│  └────┬─────┘ └────┬─────┘ └───┬──────┘ └────┬──────┘ │
│       └──────┬──────┴───────┬───┘              │        │
└──────────────┼──────────────┼──────────────────┘        │
               ▼              ▼                            │
┌──────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│         Source Router               │
│  - URL 자동 감지 (web/youtube/file) │
│  - MCP 소스 라우팅                   │
│  - 텍스트 추출 & 정규화              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         LLM Processor               │
│  - 로컬: Ollama (qwen3:14b+)       │
│  - 클라우드: Claude/GPT (선택)      │
│  - 프롬프트: Confluence 포맷 정리    │
│  - 템플릿: 회의록/기술문서/리서치    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Output: Confluence MCP         │
│  - sooperset/mcp-atlassian          │
│  - 페이지 생성/수정                  │
│  - 스페이스/부모 페이지 지정         │
│  - 포맷: Confluence Storage Format   │
└─────────────────────────────────────┘
```

## 디렉토리 구조

```
confluence-agent/
├── README.md
├── pyproject.toml
├── config.yaml              # MCP 서버 설정, LLM 설정
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI 엔트리포인트
│   ├── router.py            # 소스 타입 감지 & 라우팅
│   ├── processor.py         # LLM 호출 & 포맷 변환
│   ├── publisher.py         # Confluence 출력
│   ├── adapters/            # 소스 어댑터 (플러그인 구조)
│   │   ├── __init__.py
│   │   ├── base.py          # BaseAdapter 인터페이스
│   │   ├── web.py           # 웹 URL 스크래핑
│   │   ├── youtube.py       # 유튜브 자막 추출
│   │   ├── local_file.py    # 로컬 파일 (PDF/Word/txt)
│   │   ├── gdrive.py        # Google Drive MCP
│   │   ├── sharepoint.py    # SharePoint/OneDrive MCP
│   │   └── notion.py        # Notion MCP (확장용)
│   └── templates/           # Confluence 페이지 템플릿
│       ├── meeting_notes.py
│       ├── tech_doc.py
│       ├── research.py
│       └── summary.py
└── tests/
```

## 핵심 MCP 서버 목록

| 소스 | MCP 서버 | GitHub |
|------|----------|--------|
| Confluence (출력) | sooperset/mcp-atlassian | github.com/sooperset/mcp-atlassian |
| Google Drive | piotr-agier/google-drive-mcp | github.com/piotr-agier/google-drive-mcp |
| SharePoint/OneDrive | ftaricano/mcp-onedrive-sharepoint | github.com/ftaricano/mcp-onedrive-sharepoint |
| Notion | makenotion/notion-mcp | github.com/makenotion/notion-mcp |
| Slack | anthropic/mcp-slack | 공식 MCP |
| 웹 스크래핑 | 내장 (trafilatura) | - |
| 유튜브 | 내장 (yt-dlp) | - |

## 사용 예시

```bash
# 웹 URL 정리 → Confluence
python -m confluence_agent "https://blog.example.com/article" --space DEV --title "기술 요약"

# 유튜브 영상 정리
python -m confluence_agent "https://youtube.com/watch?v=xxx" --template meeting_notes

# Google Drive 문서
python -m confluence_agent "gdrive://1234abcd" --space TEAM

# 여러 소스 한번에
python -m confluence_agent \
  "https://blog.example.com/article" \
  "https://youtube.com/watch?v=xxx" \
  "gdrive://meeting-doc-id" \
  --merge --title "종합 리서치 노트"
```

## 설정 (config.yaml)

```yaml
llm:
  provider: ollama
  model: qwen3:14b-128k
  base_url: http://localhost:11434
  # provider: anthropic  # 클라우드 옵션
  # model: claude-sonnet-4-20250514

confluence:
  url: https://your-domain.atlassian.net
  username: your-email@company.com
  api_token: ${CONFLUENCE_API_TOKEN}
  default_space: TEAM

mcp_servers:
  gdrive:
    enabled: false
    command: npx
    args: ["-y", "google-drive-mcp"]
  sharepoint:
    enabled: false
    command: npx
    args: ["-y", "mcp-onedrive-sharepoint"]
  notion:
    enabled: false
    command: npx
    args: ["-y", "@notionhq/notion-mcp-server"]

templates:
  default: summary
  available:
    - summary        # 일반 요약
    - meeting_notes  # 회의록
    - tech_doc       # 기술 문서
    - research       # 리서치 노트
```

## 빠른 시작

### 1. 설치
```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 패키지 설치
pip install -e ".[all]"
```

### 2. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 편집 - Confluence 정보 입력
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_api_token
```

### 3. Ollama 설치 (로컬 LLM)
```bash
# https://ollama.com 에서 다운로드 후
ollama pull qwen3:14b-128k
ollama pull gemma2:2b
```

### 4. 실행
```bash
# CLI 모드 - Dry run (Confluence에 발행하지 않음)
python -m src.main run "https://example.com" --dry-run

# Web UI 모드
python -m src.main ui
# 브라우저: http://127.0.0.1:8501
```

**자세한 설정 방법은 [SETUP.md](SETUP.md)를 참조하세요.**
