# 🔬 LangExtract 사용 위치 및 역할

## 📊 전체 흐름도

```
┌─────────────────────────────────────────────────────────┐
│ 1. 소스 추출 (Source Extraction)                         │
│    - 웹, YouTube, 파일 등에서 텍스트 추출                │
│    - Router → Adapters                                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. LangExtract (선택적) 🔬                               │
│    ┌──────────────────────────────────────────────┐    │
│    │ 비정형 텍스트에서 구조화된 정보 추출          │    │
│    │ - 회의: 안건, 결정사항, 액션아이템           │    │
│    │ - 기술: 기능, 요구사항, 제한사항             │    │
│    │ - 리서치: 발견, 데이터, 권고사항             │    │
│    └──────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 3. LLM 처리 (Main Processing)                            │
│    - 추출된 구조화 정보 + 원본 텍스트                   │
│    - Template 적용                                       │
│    - 최종 Confluence 문서 생성                           │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 LangExtract의 역할

### **위치: 2단계 (소스 추출과 LLM 처리 사이)**

LangExtract는 **전처리(preprocessing)** 역할을 합니다:

1. **원본 텍스트**: 비정형 자연어 텍스트
2. **LangExtract 처리**: 구조화된 엔티티 추출
3. **LLM 입력**: 구조화 정보 + 원본 텍스트

---

## 📝 코드 상세 분석

### processor.py의 처리 순서

```python
async def process(
    self,
    contents: List[SourceContent],
    template: str = "summary",
    output_format: str = "markdown",
    use_langextract: bool = False,        # 🔬 사용 여부
    extraction_profile: str = "general",   # 🔬 추출 프로필
    output_length: str = "normal",
) -> str:
    # ===== 1단계: 소스 결합 =====
    combined = self._combine_contents(contents)
    # 예: "회의 내용: 김부장이 마케팅 예산 20% 증액을 제안..."

    # ===== 2단계: LangExtract (선택적) =====
    if use_langextract:
        extractor = self._get_extractor()

        # 구조화 추출 실행
        result = await extractor.extract(
            combined[:20000],           # 최대 20000자
            profile=extraction_profile, # meeting, tech_review, research, general
        )

        # 추출된 엔티티를 포맷팅
        extraction_context = extractor.format_entities_as_context(result)
        # 예:
        # ## 구조화 추출 결과
        #
        # ### agenda
        # - 마케팅 예산 증액 (topic: 예산)
        #
        # ### decision
        # - 20% 증액하자 (content: 마케팅 예산 20% 증액)
        #
        # ### action_item
        # - 이대리가 3월까지 계획서 작성 (assignee: 이대리, deadline: 3월)

        # 원본 텍스트 앞에 구조화 정보 추가
        if extraction_context:
            combined = f"{extraction_context}\n\n---\n\n## 원본 자료\n{combined}"

    # ===== 3단계: Template 렌더링 =====
    prompt = self.templates.render(template, combined, output_format, output_length)

    # ===== 4단계: LLM 호출 =====
    response = await self._call_llm(prompt)
    return response
```

---

## 🔍 LangExtract 사용 전/후 비교

### **LangExtract 미사용 시**

#### LLM 입력
```
다음 자료를 회의록 형식으로 정리해주세요.

자료:
김부장: 다음 분기 마케팅 예산을 20% 증액하자.
       이대리가 3월까지 계획서 작성해주세요.
박과장: 좋습니다. 승인합니다.
```

#### LLM 출력 (구조 파악이 어려울 수 있음)
```markdown
## 회의록

회의에서 김부장이 마케팅 예산 증액을 제안했고,
박과장이 승인했습니다. 이대리가 계획서를 작성합니다.
```

---

### **LangExtract 사용 시** ✅

#### LLM 입력 (구조화된 정보 추가)
```
다음 자료를 회의록 형식으로 정리해주세요.

자료:
## 구조화 추출 결과

### agenda
- 다음 분기 마케팅 예산 (topic: 예산 증액)

### decision
- 20% 증액하자 (content: 마케팅 예산 20% 증액)

### action_item
- 이대리가 3월까지 계획서 작성 (assignee: 이대리, deadline: 3월)

---

## 원본 자료
김부장: 다음 분기 마케팅 예산을 20% 증액하자.
       이대리가 3월까지 계획서 작성해주세요.
박과장: 좋습니다. 승인합니다.
```

#### LLM 출력 (더 구조화되고 명확함)
```markdown
## 회의 개요
- 일시: [추출 불가]
- 참석자: 김부장, 이대리, 박과장
- 목적: 마케팅 예산 검토

## 논의 사항
### 마케팅 예산 증액
- 김부장: 다음 분기 마케팅 예산 20% 증액 제안

## 결정 사항
✅ 마케팅 예산 20% 증액 승인 (박과장 승인)

## 액션 아이템
| 담당자 | 내용 | 기한 |
|--------|------|------|
| 이대리 | 마케팅 예산 계획서 작성 | 3월 |
```

---

## 🎯 LangExtract의 장점

### 1. **구조 파악 향상**
- LLM이 텍스트 구조를 더 잘 이해
- 회의록, 기술문서 등에서 핵심 정보 누락 방지

### 2. **일관된 출력**
- 항상 같은 형식으로 정보 추출
- 예: 액션아이템은 항상 담당자, 내용, 기한 포함

### 3. **품질 향상**
- 중요 정보 강조
- LLM이 집중해야 할 부분 명확히 표시

---

## 🔬 LangExtract 프로필

### 1. meeting (회의록)
추출 항목:
- `agenda`: 논의된 안건/주제
- `decision`: 결정된 사항
- `action_item`: 해야 할 일 (담당자, 기한)
- `key_statement`: 중요 발언

### 2. tech_review (기술 문서)
추출 항목:
- `feature`: 주요 기능/특징
- `architecture`: 아키텍처/구조
- `requirement`: 요구사항/의존성
- `example`: 코드 예시/사용법
- `limitation`: 제한사항/주의점

### 3. research (리서치)
추출 항목:
- `finding`: 주요 발견/결론
- `data_point`: 구체적 수치/통계
- `comparison`: 비교 내용
- `recommendation`: 제안/권고사항
- `reference`: 출처/인용

### 4. general (일반)
추출 항목:
- `key_point`: 핵심 내용/요점
- `entity`: 중요한 이름/용어/개념
- `relation`: 관계/연결

---

## 🚀 사용 방법

### CLI
```bash
# LangExtract 사용 (회의록)
python -m src.main run "회의록.txt" \
  --template meeting_notes \
  --use-langextract \          # 🔬 활성화
  --extraction-profile meeting  # 🔬 프로필 선택
```

### Web UI
```
🔬 LangExtract 구조화 추출
☑️ [체크박스]  [프로필: 회의록 ▼]
                        ├─ 일반
                        ├─ 회의록  ⭐
                        ├─ 기술 리뷰
                        └─ 리서치
```

---

## ⚡ 성능 고려사항

### 1. 처리 시간
- LangExtract 없음: **5-10초**
- LangExtract 사용: **30-60초** (추가 LLM 호출)

### 2. 언제 사용할까?

#### ✅ 사용 권장
- **회의록**: 안건, 결정사항, 액션아이템 명확히 구분
- **기술 문서**: 기능, 요구사항, 제한사항 체계적 정리
- **리서치**: 데이터, 발견, 권고사항 구조화

#### ❌ 불필요한 경우
- **단순 요약**: 블로그 글, 뉴스 기사 등
- **이미 구조화된 문서**: 표, 목록이 명확한 문서
- **짧은 텍스트**: 200자 이하의 간단한 내용

---

## 📊 처리 흐름 다이어그램

```
일반 처리 (빠름)
┌──────┐    ┌─────┐    ┌──────────┐
│ 소스 │ -> │ LLM │ -> │ Confluence│
└──────┘    └─────┘    └──────────┘
           5-10초

LangExtract 사용 (느리지만 품질 향상)
┌──────┐    ┌────────────┐    ┌─────┐    ┌──────────┐
│ 소스 │ -> │ LangExtract│ -> │ LLM │ -> │ Confluence│
└──────┘    │  구조 추출  │    └─────┘    └──────────┘
            └────────────┘
               30-60초
```

---

## 🎯 실전 예시

### 시나리오: 회의록 작성

```bash
# 입력: 회의 녹취록 텍스트 파일
python -m src.main run "meeting.txt" \
  --template meeting_notes \
  --use-langextract \
  --extraction-profile meeting \
  --length detailed
```

**결과:**
1. LangExtract가 텍스트에서 자동 추출:
   - 안건 5개
   - 결정사항 3개
   - 액션아이템 8개 (담당자, 기한 포함)

2. 메인 LLM이 구조화된 정보 기반으로 회의록 생성:
   - 누락 없음
   - 표 형식 액션아이템
   - 명확한 결정사항

---

## 📝 요약

| 항목 | 설명 |
|------|------|
| **위치** | 소스 추출 후, 메인 LLM 처리 전 |
| **역할** | 비정형 텍스트 → 구조화된 정보 추출 |
| **사용 시** | 회의록, 기술문서, 리서치 등 구조가 중요한 경우 |
| **장점** | 품질 향상, 일관성, 핵심 정보 누락 방지 |
| **단점** | 처리 시간 증가 (30-60초) |
| **비활성화** | 기본값 (체크박스 해제 상태) |

LangExtract는 **선택적 전처리 도구**로, 더 나은 품질의 구조화된 문서가 필요할 때만 사용하면 됩니다! 🎯
