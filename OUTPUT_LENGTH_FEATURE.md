# 📏 출력 길이 조절 기능

## 개요

사용자가 생성되는 콘텐츠의 길이를 선택할 수 있는 기능을 추가했습니다.

## 🎯 길이 옵션

| 옵션 | 설명 | 기본 대비 | 특징 |
|------|------|----------|------|
| **compact** | 간결 | **50%** | 핵심만 간추려서 요약 |
| **normal** | 보통 | **100%** | 기본값, 적당한 분량 |
| **detailed** | 상세 | **200%** | 더 많은 예시와 설명 포함 |
| **comprehensive** | 매우 상세 | **300%** | 모든 세부사항 포함 |

## 🚀 사용 방법

### CLI

```bash
# 간결한 요약 (50%)
python -m src.main run "Python asyncio" --length compact --dry-run

# 보통 (기본값, 100%)
python -m src.main run "Python asyncio" --dry-run

# 상세 (200%)
python -m src.main run "Python asyncio" --length detailed --dry-run

# 매우 상세 (300%)
python -m src.main run "Python asyncio" --length comprehensive --dry-run

# 단축 옵션 사용
python -m src.main run "Python asyncio" -l detailed --dry-run
```

### Web UI

1. Web UI 실행: `python -m src.main ui`
2. **📏 출력 길이** 드롭다운에서 선택:
   - 간결 (50% - 핵심만)
   - 보통 (100% - 기본) ⭐ 기본값
   - 상세 (200% - 예시 포함)
   - 매우 상세 (300% - 모든 세부사항)
3. **처리** 버튼 클릭

## 📝 구현 세부사항

### 1. Templates (src/templates.py)

```python
def render(self, name: str, content: str, output_format: str = "markdown",
           length: str = "normal") -> str:
    """Render template with length instructions."""

    length_instructions = {
        "compact": "간결하게 핵심만 요약 (현재 분량의 50%)",
        "normal": "적당한 분량으로 정리 (기본)",
        "detailed": "상세하게 정리 (현재 분량의 2배, 더 많은 예시와 설명 포함)",
        "comprehensive": "매우 상세하게 정리 (현재 분량의 3배, 모든 세부사항 포함)",
    }

    # LLM에 길이 지시사항 전달
    combined_instructions = f"{format_instructions}\n길이: {length_inst}"
```

### 2. Processor (src/processor.py)

```python
async def process(
    self,
    contents: List[SourceContent],
    template: str = "summary",
    output_format: str = "markdown",
    use_langextract: bool = False,
    extraction_profile: str = "general",
    output_length: str = "normal",  # 🆕 추가
) -> str:
    # Length instruction을 LLM prompt에 포함
    prompt = self.templates.render(template, combined, output_format, output_length)
```

### 3. Web UI (src/web_ui.py)

```python
async def _process(self, request):
    data = await request.json()
    output_length = data.get("output_length", "normal")  # 🆕 추가

    body = await self.processor.process(
        contents,
        template=template,
        output_format=output_format,
        output_length=output_length,
    )
```

### 4. CLI (src/main.py)

```python
cli.add_argument("--length", "-l",
                 choices=["compact", "normal", "detailed", "comprehensive"],
                 default="normal",
                 help="Output length")

# 사용 시
body = await processor.process(contents, template=template, output_length=output_length)
```

### 5. Web UI HTML (static/index.html)

```html
<div class="option-group">
  <label>📏 출력 길이</label>
  <select id="lengthSelect">
    <option value="compact">간결 (50% - 핵심만)</option>
    <option value="normal" selected>보통 (100% - 기본)</option>
    <option value="detailed">상세 (200% - 예시 포함)</option>
    <option value="comprehensive">매우 상세 (300% - 모든 세부사항)</option>
  </select>
</div>
```

## 📊 실제 예시

### 동일 소스, 다른 길이

**입력:** "Python asyncio tutorial"

#### compact (50%)
```markdown
## asyncio 개요
비동기 I/O 라이브러리. async/await로 병렬 처리.

## 주요 기능
- 네트워크 I/O
- 이벤트 루프
```
**→ 약 200자**

#### normal (100%) - 기본
```markdown
## asyncio 개요
asyncio는 Python의 비동기 I/O 라이브러리입니다.
async/await 구문으로 병렬 처리 코드 작성 가능.

## 주요 기능
- 네트워크 I/O 및 IPC 수행
- 이벤트 루프를 통한 작업 스케줄링
- 코루틴과 태스크 관리

## 사용 예시
```python
import asyncio
async def main():
    await asyncio.sleep(1)
```
```
**→ 약 400자**

#### detailed (200%)
```markdown
## asyncio란?
asyncio는 Python 3.4부터 도입된 표준 라이브러리로,
비동기 I/O, 이벤트 루프, 코루틴을 제공합니다.

async/await 구문을 사용하여 동시성 코드를 작성할 수 있으며,
CPU-bound가 아닌 I/O-bound 작업에 최적화되어 있습니다.

## 핵심 개념

### 코루틴 (Coroutine)
async def로 정의된 함수. await로 호출.

### 이벤트 루프
비동기 작업을 스케줄링하고 실행.

## 주요 기능
- 네트워크 I/O: TCP/UDP 서버/클라이언트
- IPC: 프로세스 간 통신
- 서브프로세스: 외부 프로그램 실행
- 동기화: Lock, Semaphore 등

## 실전 예시

### 간단한 비동기 함수
```python
import asyncio

async def fetch_data(url):
    # 비동기 HTTP 요청
    await asyncio.sleep(1)  # 시뮬레이션
    return f"Data from {url}"

async def main():
    result = await fetch_data("https://example.com")
    print(result)

asyncio.run(main())
```

### 여러 작업 동시 실행
```python
async def main():
    tasks = [
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    ]
    results = await asyncio.gather(*tasks)
```

## 성능 이점
동기 코드 대비 I/O-bound 작업에서 10-100배 향상.

## 제한사항
- CPU-bound 작업에는 부적합 (multiprocessing 사용)
- WASI 플랫폼 미지원
```
**→ 약 800자**

#### comprehensive (300%)
```markdown
# asyncio 완전 가이드

## 1. asyncio란?

### 1.1 개요
asyncio는 Python 3.4에서 도입된 표준 라이브러리로,
비동기 I/O, 이벤트 루프, 코루틴, 태스크를 제공하는
고수준 비동기 프로그래밍 프레임워크입니다.

### 1.2 등장 배경
- Node.js의 비동기 모델 영향
- I/O-bound 웹 애플리케이션 요구 증가
- 멀티스레딩의 복잡성 해소

### 1.3 사용 사례
- 고성능 웹 서버 (aiohttp, FastAPI)
- 웹 스크래핑 (aiohttp + BeautifulSoup)
- 채팅 서버
- IoT 디바이스 제어
- 마이크로서비스 간 통신

## 2. 핵심 개념

### 2.1 코루틴 (Coroutine)
`async def`로 정의된 특수한 함수입니다.

**특징:**
- 실행을 일시 중단하고 재개 가능
- await 키워드로 다른 코루틴 호출
- 일반 함수처럼 호출하면 코루틴 객체 반환

**예시:**
```python
async def greet(name):
    await asyncio.sleep(1)
    return f"Hello, {name}!"
```

### 2.2 이벤트 루프
모든 비동기 작업을 관리하는 중앙 메커니즘.

**역할:**
- 코루틴 스케줄링
- I/O 이벤트 감시
- 콜백 실행

... (더 많은 상세 내용)

## 3. 주요 API

### 3.1 고수준 API
...

### 3.2 저수준 API
...

(계속...)
```
**→ 약 1200자+**

## 🎯 장점

### 1. 사용자 맞춤형
- 빠른 요약이 필요한 경우: **compact**
- 일반적인 정리: **normal**
- 상세한 학습 자료: **detailed**
- 완전한 문서화: **comprehensive**

### 2. 시간 절약
- compact로 빠르게 핵심 파악
- 필요시 detailed로 재생성

### 3. Confluence 페이지 최적화
- 간단한 메모: compact
- 프로젝트 문서: detailed
- 기술 백서: comprehensive

## 📈 효과

| 상황 | 권장 길이 | 이유 |
|------|-----------|------|
| 슬랙 공유용 | compact | 빠른 전달 |
| 회의록 | normal | 핵심 + 맥락 |
| 기술 문서 | detailed | 예시 필요 |
| 온보딩 가이드 | comprehensive | 완전한 설명 |

## 🔮 향후 개선 가능 사항

1. **자동 길이 추천**: 소스 복잡도 분석
2. **커스텀 배율**: 사용자 정의 % 설정
3. **길이별 템플릿**: 각 길이에 최적화된 템플릿
4. **미리보기**: 각 길이의 예상 결과 미리보기

## 📝 변경된 파일

- ✅ [src/templates.py](d:\Python\confluence-agent\src\templates.py)
- ✅ [src/processor.py](d:\Python\confluence-agent\src\processor.py)
- ✅ [src/web_ui.py](d:\Python\confluence-agent\src\web_ui.py)
- ✅ [src/main.py](d:\Python\confluence-agent\src\main.py)
- ✅ [static/index.html](d:\Python\confluence-agent\static\index.html)

---

**버전:** v0.1.2 (Unreleased)
**작성일:** 2026-02-11
