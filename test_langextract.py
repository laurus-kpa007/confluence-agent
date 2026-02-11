"""
LangExtract 구조화 엔티티 추출 테스트
"""

import asyncio
from src.extractor import Extractor

async def main():
    # 샘플 텍스트
    text = """
    2026년 Q1 마케팅 전략 회의

    참석자: 김부장, 박과장, 이대리

    안건 1: 마케팅 예산 증액
    김부장: 다음 분기 마케팅 예산을 현재보다 20% 증액하고자 합니다.
    박과장: 증액 규모가 적절해 보입니다. 승인하겠습니다.

    김부장: 이대리님, 3월 15일까지 상세 예산 계획서를 작성해주시기 바랍니다.
    이대리: 네, 알겠습니다.

    결정 사항:
    - 마케팅 예산 20% 증액 승인
    """

    # Extractor 초기화
    extractor = Extractor()

    print("=" * 60)
    print("🔬 LangExtract 엔티티 추출 테스트")
    print("=" * 60)

    # 1. 회의록 프로필로 추출
    print("\n📋 프로필: meeting (회의록)")
    print("-" * 60)

    result = await extractor.extract(text, profile="meeting")

    # 추출된 엔티티 출력
    print(f"\n✅ 총 {len(result.entities)}개 엔티티 추출\n")

    for i, entity in enumerate(result.entities, 1):
        print(f"{i}. [{entity.type}]")
        print(f"   내용: {entity.content[:100]}...")

        # 필드 출력
        if entity.fields:
            for key, value in entity.fields.items():
                print(f"   {key}: {value}")

        # 원문 위치
        if entity.spans:
            span = entity.spans[0]
            print(f"   위치: {span.start}-{span.end} (신뢰도: {span.score:.2f})")

        print()

    # 2. 포맷팅된 컨텍스트 출력
    print("=" * 60)
    print("📝 LLM에 전달되는 구조화 컨텍스트:")
    print("=" * 60)

    context = extractor.format_entities_as_context(result)
    print(context)

    # 3. 다른 프로필 테스트 (기술 문서)
    tech_text = """
    FastAPI는 현대적이고 빠른 웹 프레임워크입니다.

    주요 기능:
    - 자동 API 문서 생성
    - 타입 힌트 기반 검증
    - 비동기 처리 지원

    요구사항:
    - Python 3.7+
    - Pydantic

    제한사항:
    - WSGI 서버 미지원
    """

    print("\n" + "=" * 60)
    print("📋 프로필: tech_review (기술 문서)")
    print("-" * 60)

    tech_result = await extractor.extract(tech_text, profile="tech_review")

    print(f"\n✅ 총 {len(tech_result.entities)}개 엔티티 추출\n")

    for i, entity in enumerate(tech_result.entities, 1):
        print(f"{i}. [{entity.type}] {entity.content[:80]}")
        if entity.fields:
            for key, value in entity.fields.items():
                print(f"   {key}: {value}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
