# 🚀 성능 분석 및 최적화 가이드

## 📊 성능 프로파일링 결과

### 전체 처리 시간 분해

| 단계 | 소요 시간 | 비율 | 병목 여부 |
|------|-----------|------|----------|
| 1. 웹 검색 (Google API) | 1초 | 1% | ✅ |
| 2. 웹 스크래핑 (3개 URL) | 2-3초 | 2% | ✅ |
| 3. LangExtract (선택) | 55초 | 27% | ⚠️ |
| 4. 메인 LLM 처리 | 144초 | 70% | 🔴 |
| **총 소요 시간** | **147-202초** | **100%** | **2-3분** |

---

## 🔴 병목 #1: 메인 LLM 처리 (70% = 144초)

### 원인
- **모델 크기**: `qwen3:14b-128k` (14.8B 파라미터)
- **출력 길이**: comprehensive (300% = 3배)
- **CPU 추론**: GPU 미사용 시 매우 느림

### 🎯 최적화 방법

#### Option 1: 더 작은 모델 사용 ⭐ 추천
```yaml
# config.yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  model: qwen3:8b  # 14b → 8b (약 2배 빠름)
  # 또는
  model: gemma3:4b  # 약 3-4배 빠름
```

**예상 성능:**
- qwen3:14b → qwen3:8b: 144초 → **70초** (50% 단축)
- qwen3:14b → gemma3:4b: 144초 → **40초** (72% 단축)

#### Option 2: 출력 길이 조정
```javascript
// Web UI에서 선택
출력 길이: "매우 상세 (300%)" → "상세 (200%)" 또는 "보통 (100%)"
```

**예상 성능:**
- comprehensive (300%) → detailed (200%): 144초 → **95초** (34% 단축)
- comprehensive (300%) → normal (100%): 144초 → **48초** (67% 단축)

#### Option 3: GPU 가속 활성화
```bash
# NVIDIA GPU가 있다면
# Ollama는 자동으로 GPU 사용

# 확인 방법
nvidia-smi  # GPU 사용률 확인
```

**예상 성능:**
- CPU → GPU: 144초 → **10-20초** (85-90% 단축) 🚀

---

## ⚠️ 병목 #2: LangExtract 처리 (27% = 55초)

### 원인
- **텍스트 크기**: 3,186자
- **모델**: gemma2:2b
- **복잡도**: 구조화 추출은 일반 생성보다 느림

### 🎯 최적화 방법

#### Option 1: 텍스트 크기 제한 ⭐ 추천
```python
# src/processor.py (현재 5000자)
result = await extractor.extract(
    combined[:3000],  # 5000 → 3000자로 감소
    profile=extraction_profile,
)
```

**예상 성능:**
- 5000자 → 3000자: 55초 → **33초** (40% 단축)

#### Option 2: LangExtract 비활성화
```
Web UI에서: "🔬 LangExtract 구조화 추출" 체크박스 해제
```

**예상 성능:**
- LangExtract ON → OFF: 202초 → **147초** (27% 단축)

#### Option 3: 더 빠른 모델 사용
```python
# src/processor.py
self.extractor = StructuredExtractor(
    model_id="qwen3:8b",  # gemma2:2b → qwen3:8b
    # qwen3:8b는 더 크지만 병렬 처리가 더 효율적
)
```

---

## ✅ 병목 #3: 웹 스크래핑 (2% = 2-3초)

### 원인
- **순차 처리**: URL을 하나씩 처리
- **네트워크 지연**: 각 URL당 1초

### 🎯 최적화 방법

#### Option 1: 병렬 스크래핑 구현
```python
# src/adapters/web_search.py
import asyncio

# 현재 (순차)
for url in urls:
    content = await scrape(url)

# 최적화 (병렬)
contents = await asyncio.gather(*[scrape(url) for url in urls])
```

**예상 성능:**
- 순차 (3초) → 병렬 (1초): **67% 단축**

---

## 🎯 종합 최적화 시나리오

### 시나리오 A: 품질 유지 + 속도 향상
```yaml
모델: qwen3:8b (14b → 8b)
출력: detailed (300% → 200%)
LangExtract: 3000자 제한
```
**결과:** 202초 → **80초** (60% 단축, 1분 20초) ⭐

### 시나리오 B: 최대 속도
```yaml
모델: gemma3:4b
출력: normal (100%)
LangExtract: OFF
```
**결과:** 202초 → **40초** (80% 단축, 40초) 🚀

### 시나리오 C: GPU 활용 (최고 성능)
```yaml
모델: qwen3:14b (GPU 사용)
출력: comprehensive (300%)
LangExtract: ON (3000자)
```
**결과:** 202초 → **30초** (85% 단축, 30초) 🔥

---

## 📝 실전 설정 가이드

### 1. 빠른 처리가 필요한 경우
```yaml
# config.yaml
llm:
  model: gemma3:4b

# Web UI
출력 길이: 보통 (100%)
LangExtract: OFF
```
**예상 시간**: 40-50초

### 2. 균형잡힌 설정 (추천)
```yaml
# config.yaml
llm:
  model: qwen3:8b

# Web UI
출력 길이: 상세 (200%)
LangExtract: ON
```
**예상 시간**: 70-90초

### 3. 최고 품질 (시간 여유 있을 때)
```yaml
# config.yaml
llm:
  model: qwen3:14b-128k

# Web UI
출력 길이: 매우 상세 (300%)
LangExtract: ON
```
**예상 시간**: 2-3분 (GPU 사용 시 30-40초)

---

## 🔧 즉시 적용 가능한 최적화

### 1. src/processor.py 수정
```python
# Line 73: LangExtract 텍스트 제한
result = await extractor.extract(
    combined[:3000],  # 5000 → 3000
    profile=extraction_profile,
)
```

### 2. config.yaml 수정
```yaml
llm:
  provider: ollama
  base_url: http://localhost:11434
  model: qwen3:8b  # 또는 gemma3:4b
  ssl_verify: false
```

### 3. Web UI 기본값 변경
```html
<!-- static/index.html -->
<select id="lengthSelect">
  <option value="compact">간결 (50%)</option>
  <option value="normal" selected>보통 (100%)</option>  <!-- 기본값 -->
  <option value="detailed">상세 (200%)</option>
  <option value="comprehensive">매우 상세 (300%)</option>
</select>
```

---

## 📈 성능 측정 도구

### 타이밍 측정 추가
```python
# src/processor.py
import time

async def process(self, ...):
    start = time.time()

    # Extract
    extract_start = time.time()
    contents = await self.router.extract_many(sources)
    print(f"⏱️  Extract: {time.time() - extract_start:.1f}s")

    # LangExtract
    if use_langextract:
        le_start = time.time()
        result = await extractor.extract(...)
        print(f"⏱️  LangExtract: {time.time() - le_start:.1f}s")

    # LLM
    llm_start = time.time()
    body = await self._call_llm(prompt)
    print(f"⏱️  LLM: {time.time() - llm_start:.1f}s")

    print(f"⏱️  Total: {time.time() - start:.1f}s")
```

---

## 🎯 결론

**가장 큰 병목**: 메인 LLM 처리 (70%, 144초)

**추천 조치**:
1. ⭐ **즉시 적용**: 모델을 qwen3:8b로 변경 (50% 단축)
2. ⭐ **사용자 안내**: 출력 길이 기본값을 "보통"으로 설정
3. 🚀 **장기 목표**: GPU 활용 (85% 단축)

**예상 결과**: 2-3분 → **1분** 이내로 단축 가능! 🎉
