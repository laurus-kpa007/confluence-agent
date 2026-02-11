# ⚡ 빠른 시작 가이드

5분 안에 Confluence Knowledge Agent를 실행해보세요!

## 1️⃣ 사전 준비 (5분)

### Ollama 설치
```bash
# 1. https://ollama.com 에서 다운로드 & 설치

# 2. 모델 다운로드 (처음 한 번만)
ollama pull qwen3:14b-128k     # 메인 LLM (~8GB)
ollama pull gemma2:2b           # 보조 LLM (~1.6GB)

# 3. 실행 확인
ollama list
```

### Python 패키지 설치
```bash
cd confluence-agent

# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 패키지 설치
pip install -e ".[all]"
```

## 2️⃣ 환경 설정 (2분)

### .env 파일 생성
```bash
# 템플릿 복사
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

### .env 파일 편집
```bash
# 필수: Confluence 정보만 입력
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_api_token_here
```

**Confluence API 토큰 발급:**
1. https://id.atlassian.com/manage-profile/security/api-tokens 접속
2. "Create API token" 클릭
3. 이름 입력 (예: confluence-agent)
4. 생성된 토큰을 복사하여 `.env` 파일에 붙여넣기

## 3️⃣ 테스트 실행 (1분)

### Dry-run 테스트 (Confluence에 발행하지 않음)
```bash
# 웹 페이지 정리
python -m src.main run "https://example.com" --dry-run

# 성공하면 아래와 같은 출력:
# 📥 Extracting from 1 source(s)...
#   ✅ [web] Example Domain (112 chars)
# 🤖 Processing with qwen3:14b-128k...
#   ✅ Generated 500 chars
# ============================================================
# 📄 Generated Content (dry-run):
# ...
```

### Web UI 실행
```bash
python -m src.main ui

# 브라우저에서 열기: http://127.0.0.1:8501
```

## 4️⃣ 실전 사용 예제

### 예제 1: 웹 페이지 정리 → Confluence 발행
```bash
python -m src.main run \
  "https://docs.python.org/3/library/asyncio.html" \
  --space "DEV" \
  --title "Python asyncio 문서 요약" \
  --template tech_doc
```

### 예제 2: 웹 검색 + 정리
```bash
# DuckDuckGo 검색 사용 (API 키 불필요)
pip install duckduckgo-search

# 방법 1: 일반 텍스트 (자동으로 검색)
python -m src.main run \
  "Python FastAPI tutorial" \
  --template tech_doc \
  --dry-run

# 방법 2: 명시적 검색 (동일한 결과)
python -m src.main run \
  "search:Python FastAPI tutorial" \
  --template tech_doc \
  --dry-run
```

### 예제 3: YouTube 자막 정리
```bash
python -m src.main run \
  "https://youtube.com/watch?v=VIDEO_ID" \
  --space "TEAM" \
  --title "영상 요약" \
  --template summary
```

### 예제 4: 여러 소스 통합 리서치
```bash
python -m src.main run \
  "https://fastapi.tiangolo.com/" \
  "search:FastAPI vs Flask comparison" \
  "https://youtube.com/watch?v=..." \
  --space "DEV" \
  --title "FastAPI 프레임워크 리서치" \
  --template research
```

### 예제 5: 로컬 파일 정리
```bash
# PDF, Word, txt 지원
python -m src.main run \
  "C:\Documents\meeting-notes.pdf" \
  --space "TEAM" \
  --title "회의록 정리" \
  --template meeting_notes
```

## 5️⃣ Web UI 사용법

```bash
python -m src.main ui
```

1. **소스 입력**: URL, 검색어, 파일 경로 입력
2. **템플릿 선택**: summary, meeting_notes, tech_doc, research
3. **미리보기**: LLM 처리 결과 확인
4. **편집**: 필요시 내용 수정
5. **발행**: Confluence Space 선택하여 발행

### 고급 기능: 구조화 추출 (LangExtract)
- "구조화 추출 사용" 체크박스 활성화
- 회의록: 안건, 결정사항, 액션아이템 자동 추출
- 기술문서: 기능, 요구사항, 제한사항 추출
- 리서치: 핵심 발견, 데이터, 권고사항 추출

## 🔍 문제 해결

### Ollama 연결 오류
```bash
# Ollama 실행 확인
ollama list

# API 테스트
curl http://localhost:11434/api/tags
```

### Import 오류
```bash
# 누락 패키지 설치
pip install trafilatura yt-dlp langextract duckduckgo-search
```

### Confluence 인증 오류
- `.env` 파일의 API 토큰이 정확한지 확인
- Confluence URL에 `/wiki` 경로가 없는지 확인
  - ✅ 올바름: `https://your-domain.atlassian.net`
  - ❌ 틀림: `https://your-domain.atlassian.net/wiki`

## 📚 다음 단계

### 템플릿 커스터마이징
`templates/` 폴더의 `.txt` 파일을 편집하여 출력 형식 변경:
- `summary.txt` - 일반 요약
- `meeting_notes.txt` - 회의록
- `tech_doc.txt` - 기술 문서
- `research.txt` - 리서치 노트
- `weekly_report.txt` - 주간 보고서

### 웹 검색 API 설정 (선택)
무료 DuckDuckGo 대신 유료 API 사용:

**Google Custom Search:**
```bash
# .env에 추가
GOOGLE_SEARCH_API_KEY=your_api_key
GOOGLE_SEARCH_CX_ID=your_search_engine_id

# config.yaml 수정
search:
  provider: google
```

**Brave Search:**
```bash
# .env에 추가
BRAVE_API_KEY=your_brave_api_key

# config.yaml 수정
search:
  provider: brave
```

### Claude API 사용 (Ollama 대신)
```bash
# .env에 추가
ANTHROPIC_API_KEY=sk-ant-api...

# config.yaml 수정
llm:
  provider: anthropic
  model: claude-sonnet-4-20250514
```

## 🎓 자세한 문서

- **[SETUP.md](SETUP.md)**: 상세 설정 가이드
- **[README.md](README.md)**: 프로젝트 개요 및 아키텍처
- **[ANALYSIS.md](ANALYSIS.md)**: 기술 분석 보고서

## 🚀 이제 시작하세요!

```bash
# 간단한 테스트
python -m src.main run "https://example.com" --dry-run

# Web UI 실행
python -m src.main ui
```

즐거운 지식 정리 되세요! 🎉
