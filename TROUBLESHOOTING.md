# 🔧 문제 해결 가이드

## "No adapter found" 오류

### 증상
```
❌ 오류: 서버 오류 (500): {"error": "No adapter found for source: 제네시스 하이브리드...
```

### 원인
입력한 소스가 인식되지 않는 형식입니다.

### 해결 방법

**자동 검색 기능 활용 (v0.1.1+)**

이제 일반 텍스트를 입력하면 자동으로 웹 검색으로 처리됩니다!

```bash
# 이전 방식 (여전히 작동)
python -m src.main run "search:제네시스 하이브리드" --dry-run

# 새로운 방식 (자동 변환)
python -m src.main run "제네시스 하이브리드" --dry-run
```

**Web UI에서:**
- 그냥 "제네시스 하이브리드" 입력 → 자동으로 웹 검색 실행
- 💡 팁: 일반 텍스트는 자동으로 웹 검색됩니다

**지원하는 소스 형식:**
- ✅ **일반 텍스트**: `Python asyncio` → 자동으로 `search:Python asyncio`로 변환
- ✅ **웹 URL**: `https://example.com`
- ✅ **명시적 검색**: `search:검색어`
- ✅ **YouTube**: `https://youtube.com/watch?v=...`
- ✅ **로컬 파일**: `C:\path\to\file.pdf` 또는 `/path/to/file.pdf`
- ✅ **Google Drive**: `gdrive://file-id` (MCP 설정 필요)

---

## JSON 파싱 오류

### 증상
```
❌ 오류: Unexpected non-whitespace character after JSON at position 4 (line 1 column 5)
```

### 원인
서버에서 에러가 발생했을 때 JSON이 아닌 HTML이나 텍스트 응답이 반환되어 발생합니다.

### 해결 방법

#### 1. 서버 로그 확인
Web UI를 실행한 터미널에서 에러 메시지를 확인하세요:

```bash
python -m src.main ui

# 터미널에서 발생한 에러를 확인
```

#### 2. 일반적인 원인과 해결책

**A. Ollama가 실행되지 않음**
```bash
# Ollama 상태 확인
curl http://localhost:11434/api/tags

# 실행되지 않으면 Ollama 시작
# Windows: 시작 메뉴에서 Ollama 실행
# macOS/Linux: ollama serve
```

**B. 모델이 다운로드되지 않음**
```bash
# 모델 목록 확인
ollama list

# 필요한 모델 다운로드
ollama pull qwen3:14b-128k
ollama pull gemma2:2b
```

**C. config.yaml의 모델명이 잘못됨**
```yaml
# config.yaml 확인
llm:
  provider: ollama
  model: qwen3:14b-128k    # ollama list에 있는 정확한 이름 사용
```

**D. 웹 검색 실패 (DuckDuckGo)**
```bash
# duckduckgo-search 패키지 설치 확인
pip install duckduckgo-search

# 또는 Google/Brave API 사용
# .env에 API 키 설정
GOOGLE_SEARCH_API_KEY=your_key
GOOGLE_SEARCH_CX_ID=your_cx_id
```

**E. 네트워크 오류 (웹 스크래핑)**
- 일부 웹사이트는 봇 접근을 차단합니다
- 다른 URL로 테스트해보세요
- 예: `https://example.com` (항상 작동)

#### 3. 개선된 에러 메시지 활용

최신 버전에서는 더 자세한 에러 메시지를 제공합니다:

```
❌ 오류: 서버 오류 (500): ConnectionError: Ollama is not running
```

이제 정확한 문제를 파악할 수 있습니다.

#### 4. CLI로 테스트

Web UI 대신 CLI로 먼저 테스트하면 더 명확한 에러 메시지를 볼 수 있습니다:

```bash
# 간단한 테스트
python -m src.main run "https://example.com" --dry-run

# 검색 테스트
python -m src.main run "search:Python tutorial" --dry-run

# 에러 발생 시 전체 traceback 확인 가능
```

---

## 기타 일반적인 문제

### 1. Import 오류

**증상:**
```
ModuleNotFoundError: No module named 'trafilatura'
```

**해결:**
```bash
pip install -e ".[all]"
```

### 2. Confluence 인증 오류

**증상:**
```
❌ 게시 실패: 401 Unauthorized
```

**해결:**
1. `.env` 파일의 API 토큰 확인
2. Confluence URL 확인 (경로 제거)
   - ✅ `https://your-domain.atlassian.net`
   - ❌ `https://your-domain.atlassian.net/wiki`
3. API 토큰 재발급: https://id.atlassian.com/manage-profile/security/api-tokens

### 3. YouTube 자막 추출 실패

**증상:**
```
❌ No subtitles found
```

**해결:**
- 해당 영상에 자막이 있는지 확인
- 일부 영상은 자막을 제공하지 않습니다
- yt-dlp 업데이트: `pip install -U yt-dlp`

### 4. LangExtract 오류

**증상:**
```
❌ 추출 실패: LangExtract error
```

**해결:**
```bash
# langextract 설치 확인
pip install langextract

# gemma2:2b 모델 확인
ollama list | grep gemma2
ollama pull gemma2:2b
```

### 5. 메모리 부족 (대용량 모델)

**증상:**
- 시스템이 느려짐
- Ollama가 응답하지 않음

**해결:**
- 더 작은 모델 사용:
  ```yaml
  llm:
    model: qwen3:8b    # 14b 대신 8b
  ```
- RAM 여유 공간 확인 (최소 16GB 권장)

### 6. 웹 스크래핑 시간 초과

**증상:**
```
❌ Timeout error
```

**해결:**
- 일부 웹사이트는 로딩이 느립니다
- 다른 소스로 시도
- timeout 설정 증가 (고급 사용자)

---

## 디버깅 팁

### 1. Verbose 모드
```bash
# 상세 로그 출력 (개발 중)
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python -m src.main run "search:test" --dry-run
```

### 2. 단계별 테스트

```bash
# 1단계: Config 로딩
python -c "from src.config_loader import load_config; from pathlib import Path; print(load_config(Path('config.yaml')))"

# 2단계: Router
python -c "from src.main import build_router, load_config; r = build_router(load_config()); print([a.name for a in r._adapters])"

# 3단계: 웹 추출
python -c "
import asyncio
from src.adapters.web import WebAdapter
async def test():
    adapter = WebAdapter()
    content = await adapter.extract('https://example.com')
    print(f'Title: {content.title}')
asyncio.run(test())
"

# 4단계: 검색
python -m src.main run "search:test" --dry-run
```

### 3. Ollama 테스트

```bash
# API 직접 호출
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:14b-128k",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

---

## 여전히 문제가 해결되지 않나요?

### 이슈 제기 시 포함할 정보

1. **에러 메시지 전체**
   ```
   전체 traceback 또는 에러 메시지
   ```

2. **환경 정보**
   ```bash
   python --version
   ollama list
   pip list | grep -E "(trafilatura|langextract|yt-dlp)"
   ```

3. **사용한 명령어**
   ```bash
   python -m src.main run "your-source" --dry-run
   ```

4. **config.yaml 설정** (API 키 제외)

5. **재현 단계**

GitHub Issues: [프로젝트 저장소 URL]

---

## 빠른 체크리스트

문제가 발생하면 다음을 순서대로 확인하세요:

- [ ] Ollama가 실행 중인가? (`ollama list`)
- [ ] 모델이 다운로드되었나? (`ollama list | grep qwen3`)
- [ ] `.env` 파일이 존재하는가?
- [ ] Confluence API 토큰이 올바른가?
- [ ] 필요한 패키지가 설치되었나? (`pip list`)
- [ ] 인터넷 연결이 정상인가? (웹 스크래핑/검색 시)
- [ ] CLI로도 같은 오류가 발생하는가?

대부분의 문제는 Ollama 미실행 또는 모델 미다운로드입니다! 🚀
