# 변경 이력

## [Unreleased]

### 🎉 주요 기능
- **출력 길이 조절**: 생성되는 콘텐츠 길이를 4단계로 선택 가능
  - compact: 50% (핵심만 간추림)
  - normal: 100% (기본값)
  - detailed: 200% (예시와 설명 추가)
  - comprehensive: 300% (모든 세부사항 포함)
  - CLI: `--length` / `-l` 옵션
  - Web UI: 📏 출력 길이 드롭다운

### 🎨 UI/UX 개선
- **상세 진행 상태 표시**: 프로그레스바와 단계별 진행 상황 표시
  - 시각적 프로그레스바 (0-100%, 그라데이션)
  - 단계별 아이콘 표시 (⏺ 대기 → ⏳ 진행 → ✅ 완료)
  - LLM 처리: 3단계 (소스 추출 → LLM 처리 → 포맷팅)
  - Confluence 발행: 3단계 (연결 → 페이지 생성 → 완료)
  - LangExtract 시각화: 3단계 (추출 → 분석 → 시각화)
  - 처리 시간 표시 (예: "5.2초 소요")
  - 상세한 통계 (소스 개수, 생성 길이, 엔티티 수)

---

## [0.1.1] - 2026-02-11

### 🎉 추가 기능
- **자동 검색 기능**: 일반 텍스트 입력 시 자동으로 웹 검색으로 변환
  - 예: `"Python asyncio"` → 자동으로 `"search:Python asyncio"`로 처리
  - Web UI와 CLI 모두 지원
  - 한글 검색어도 정상 작동

### 🔧 개선 사항
- **환경변수 지원**: `.env` 파일로 API 키 관리
  - `${VAR_NAME}` 및 `${VAR_NAME:default}` 형식 지원
  - config.yaml에서 환경변수 자동 확장
- **WebSearchAdapter 설정 개선**: config에서 검색 API 설정 주입
  - Google, Brave, DuckDuckGo 지원
  - DuckDuckGo를 기본값으로 설정 (API 키 불필요)
- **에러 처리 강화**:
  - Web UI: 서버 오류 시 명확한 메시지 표시
  - 서버: JSON 에러 응답 + traceback 포함
  - 더 이상 "Unexpected JSON" 오류 없음

### 📚 문서화
- **QUICKSTART.md**: 5분 빠른 시작 가이드 (신규)
- **SETUP.md**: 상세 설정 가이드 (신규)
- **TROUBLESHOOTING.md**: 문제 해결 가이드 (신규)
  - JSON 파싱 오류 해결
  - "No adapter found" 오류 해결
  - 일반적인 문제 및 해결책
- **ANALYSIS.md**: 기술 분석 보고서 (신규)
- README.md: 빠른 시작 섹션 추가

### 🐛 버그 수정
- JSON 파싱 오류 수정 (서버 에러 시)
- "No adapter found" 오류 개선 (자동 검색 fallback)

### 📦 의존성
- pyproject.toml: search, extract 그룹 추가
  - `duckduckgo-search>=6.0` (웹 검색)
  - `langextract>=1.1` (구조화 추출)

---

## [0.1.0] - 2026-02-11

### 초기 릴리스

#### 핵심 기능
- 멀티소스 자료 수집:
  - 웹 URL 스크래핑 (trafilatura)
  - YouTube 자막 추출 (yt-dlp)
  - 로컬 파일 (PDF, Word, txt)
  - 웹 검색 (Google, Brave, DuckDuckGo)
- LLM 처리:
  - Ollama (로컬 LLM) 지원
  - Anthropic Claude API 지원
  - 템플릿 기반 출력 포맷팅
- Confluence 출력:
  - REST API 기반 페이지 생성/수정
  - Space/Page 탐색 및 검색
  - 마크다운 및 Confluence Storage Format 지원
- LangExtract 통합:
  - 구조화된 정보 추출 (회의록, 기술문서, 리서치)
  - 대화형 HTML 시각화
- Web UI:
  - 시각적 인터페이스
  - 실시간 미리보기
  - 템플릿 편집

#### 아키텍처
- 어댑터 패턴 기반 소스 플러그인
- 비동기 처리 (asyncio)
- 모듈화된 구조

#### 지원 템플릿
- summary: 일반 요약
- meeting_notes: 회의록
- tech_doc: 기술 문서
- research: 리서치 노트
- weekly_report: 주간 보고서

---

## 향후 계획

### 단기 (1-2주)
- [ ] 단위 테스트 추가
- [ ] GitHub Actions CI/CD
- [ ] MCP 서버 통합 테스트 (Google Drive, SharePoint)

### 중기 (1개월)
- [ ] 캐싱 메커니즘 (중복 추출 방지)
- [ ] 로깅 시스템
- [ ] 오류 복구 메커니즘

### 장기 (3개월+)
- [ ] Docker 컨테이너화
- [ ] 스케줄링 기능 (주기적 업데이트)
- [ ] 웹 UI 개선 (React 마이그레이션)
- [ ] 멀티 언어 지원

---

## 기여

버그 리포트, 기능 제안, 풀 리퀘스트 환영합니다!

GitHub Issues: [프로젝트 저장소 URL]
