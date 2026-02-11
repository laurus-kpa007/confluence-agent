# 🚀 Confluence Knowledge Agent - 설정 가이드

## 1. 필수 요구사항

### Python 환경
- Python 3.10 이상
- 가상환경 사용 권장

### Ollama 설치 (로컬 LLM 사용 시)
```bash
# 1. Ollama 다운로드 및 설치
# https://ollama.com/download

# 2. 추천 모델 다운로드
ollama pull qwen3:14b-128k    # 메인 LLM (정리용)
ollama pull gemma2:2b         # 보조 LLM (빠른 추출용)

# 3. Ollama 실행 확인
ollama list
```

## 2. 프로젝트 설치

```bash
# 1. 저장소 클론 (또는 다운로드)
cd confluence-agent

# 2. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 기본 패키지 설치
pip install -e .

# 4. 선택적 기능 설치
pip install -e ".[all]"  # PDF, Word, Excel, YouTube 등 모두 설치
# 또는 필요한 것만:
# pip install -e ".[pdf]"      # PDF 지원
# pip install -e ".[youtube]"  # YouTube 자막
# pip install -e ".[docx]"     # Word 문서
```

## 3. 환경 변수 설정

### .env 파일 생성
```bash
cp .env.example .env
```

### .env 파일 편집
```bash
# 필수: Confluence 설정
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_api_token_here
```

**Confluence API 토큰 발급 방법:**
1. Atlassian 계정 설정: https://id.atlassian.com/manage-profile/security/api-tokens
2. "Create API token" 클릭
3. 토큰 이름 입력 (예: confluence-agent)
4. 생성된 토큰 복사하여 `.env` 파일에 붙여넣기

### 선택 사항

#### 웹 검색 기능 (search: 명령어)
```bash
# Option 1: Google Custom Search (추천)
GOOGLE_SEARCH_API_KEY=237c23d4505ce4625
GOOGLE_SEARCH_CX_ID=237c23d4505ce4625

# Option 2: Brave Search
BRAVE_API_KEY=your_brave_api_key

# Option 3: DuckDuckGo (API 키 불필요)
# config.yaml에서 provider: duckduckgo 설정
pip install duckduckgo-search
```

#### Claude API 사용 (Ollama 대신)
```bash
ANTHROPIC_API_KEY=sk-ant-api...
```

## 4. config.yaml 설정

### 기본 설정 확인
```yaml
llm:
  provider: ollama                    # 또는 anthropic
  model: qwen3:14b-128k
  base_url: http://localhost:11434

confluence:
  url: ${CONFLUENCE_URL}              # .env에서 자동 로드
  username: ${CONFLUENCE_USERNAME}
  api_token: ${CONFLUENCE_API_TOKEN}
  default_space: TEAM                 # 기본 Space 설정

search:
  provider: duckduckgo                # google, brave, duckduckgo
  # api_key: ${GOOGLE_SEARCH_API_KEY}  # Google/Brave 사용 시
  # cx_id: ${GOOGLE_SEARCH_CX_ID}      # Google 사용 시
  max_results: 3
```

### MCP 서버 설정 (고급)
Google Drive, SharePoint, Notion 등 연동 시 설정:
```yaml
mcp_servers:
  gdrive:
    enabled: true
    env:
      GOOGLE_APPLICATION_CREDENTIALS: "/path/to/credentials.json"
```

## 5. 동작 테스트

### CLI 모드
```bash
# 1. Dry-run 테스트 (Confluence에 발행하지 않음)
python -m src.main run "https://example.com" --dry-run

# 2. 웹 검색 테스트
python -m src.main run "search:Python asyncio tutorial" --dry-run

# 3. YouTube 자막 추출 테스트
python -m src.main run "https://youtube.com/watch?v=VIDEO_ID" --dry-run
```

### Web UI 모드
```bash
# Web UI 실행
python -m src.main ui

# 브라우저에서 열기: http://127.0.0.1:8501
```

### 실제 Confluence 발행 테스트
```bash
python -m src.main run \
  "https://example.com" \
  --space "DEV" \
  --title "테스트 페이지" \
  --template summary
```

## 6. 문제 해결

### Ollama 연결 오류
```bash
# Ollama 상태 확인
ollama list
curl http://localhost:11434/api/tags

# Ollama 재시작
# Windows: 작업 관리자에서 Ollama 프로세스 종료 후 재시작
# macOS/Linux: killall ollama && ollama serve
```

### Import 오류
```bash
# 누락된 패키지 설치
pip install trafilatura  # 웹 스크래핑
pip install langextract  # 구조화 추출
pip install yt-dlp       # YouTube
pip install pymupdf      # PDF
```

### Confluence 인증 오류
- API 토큰이 정확한지 확인
- Confluence URL에 `/wiki` 같은 경로가 포함되지 않았는지 확인
  - 올바른 예: `https://your-domain.atlassian.net`
  - 잘못된 예: `https://your-domain.atlassian.net/wiki`

### 웹 검색이 작동하지 않음
```bash
# DuckDuckGo 사용 시
pip install duckduckgo-search

# config.yaml 확인
# search:
#   provider: duckduckgo  # API 키 불필요
```

## 7. 다음 단계

### 템플릿 커스터마이징
`templates/` 폴더의 `.txt` 파일을 수정하여 출력 형식 변경:
- `summary.txt` - 일반 요약
- `meeting_notes.txt` - 회의록
- `tech_doc.txt` - 기술 문서
- `research.txt` - 리서치 노트

### Web UI에서 템플릿 편집
1. `python -m src.main ui`
2. 브라우저에서 템플릿 탭으로 이동
3. 실시간 수정 및 저장

### LangExtract 구조화 추출
Web UI에서 "구조화 추출 사용" 옵션 체크:
- 회의록: 안건, 결정사항, 액션아이템 자동 추출
- 기술문서: 기능, 요구사항, 제한사항 추출
- 리서치: 핵심 발견, 데이터, 권고사항 추출

## 8. 주요 기능

### 지원 소스
- 웹 URL: `https://example.com`
- 웹 검색: `search:검색어`
- YouTube: `https://youtube.com/watch?v=...`
- 로컬 파일: `/path/to/file.pdf` (PDF, Word, txt)
- (선택) Google Drive: `gdrive://file-id`
- (선택) SharePoint: MCP 설정 필요

### CLI 옵션
```bash
python -m src.main run [sources...] \
  --space SPACE_KEY \
  --title "페이지 제목" \
  --template summary|meeting_notes|tech_doc|research \
  --format markdown|confluence \
  --parent-id PAGE_ID \
  --dry-run
```

### 여러 소스 통합
```bash
python -m src.main run \
  "https://blog.example.com/article" \
  "search:AI agent frameworks" \
  "https://youtube.com/watch?v=xxx" \
  --title "AI 에이전트 종합 리서치"
```

## 완료!

이제 다양한 소스에서 자료를 수집하고 LLM으로 정리하여 Confluence에 자동으로 발행할 수 있습니다.

문제가 발생하면 이슈를 등록해주세요!
