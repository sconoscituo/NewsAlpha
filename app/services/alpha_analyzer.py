"""
알파 분석 서비스
Gemini AI를 사용해 뉴스에서 수혜주/피해주/섹터/영향도를 분석합니다.
"""
import json
import logging
import re
from typing import Optional

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.news import NewsItem
from app.models.alpha import AlphaSignal

logger = logging.getLogger(__name__)
settings = get_settings()

# Gemini 클라이언트 초기화
genai.configure(api_key=settings.gemini_api_key)


# Gemini에게 보낼 분석 프롬프트 템플릿
ANALYSIS_PROMPT = """
당신은 주식 시장 전문 애널리스트입니다. 다음 뉴스를 분석하여 주가에 미치는 영향을 JSON 형식으로 반환해주세요.

뉴스 제목: {title}
뉴스 내용: {content}

다음 JSON 형식으로만 응답하세요 (설명 없이 JSON만):
{{
  "beneficiary_stocks": [
    {{
      "code": "한국 종목코드 또는 티커",
      "name": "종목명",
      "reason": "수혜 이유 (30자 이내)"
    }}
  ],
  "victim_stocks": [
    {{
      "code": "한국 종목코드 또는 티커",
      "name": "종목명",
      "reason": "피해 이유 (30자 이내)"
    }}
  ],
  "impact_score": 0,
  "impact_reason": "전체 시장 영향 요약 (100자 이내)",
  "sector": "관련 섹터명"
}}

규칙:
- impact_score: -10(매우 부정) ~ +10(매우 긍정), 0은 중립
- 종목코드는 한국 6자리 코드 우선 (예: 005930), 해외는 티커 사용
- 관련 없으면 빈 배열 []
- sector: 반도체, 바이오, 에너지, 금융, 소비재, 자동차, 화학, 통신, 건설, 기타 중 선택
"""


async def analyze_pending_news() -> int:
    """
    미분석 뉴스를 조회해 Gemini로 분석하고 AlphaSignal을 저장합니다.
    반환값: 분석 완료된 뉴스 수
    """
    analyzed_count = 0

    async with AsyncSessionLocal() as db:
        # 미분석 뉴스 최대 20개 조회 (API 호출 비용 절감)
        result = await db.execute(
            select(NewsItem)
            .where(NewsItem.is_analyzed == 0)
            .order_by(NewsItem.collected_at.desc())
            .limit(20)
        )
        pending_news = result.scalars().all()

        for news_item in pending_news:
            try:
                signal_data = await _analyze_single_news(news_item)
                if signal_data:
                    alpha = AlphaSignal(news_id=news_item.id)
                    alpha.set_beneficiary_stocks(signal_data.get("beneficiary_stocks", []))
                    alpha.set_victim_stocks(signal_data.get("victim_stocks", []))
                    alpha.impact_score = float(signal_data.get("impact_score", 0))
                    alpha.impact_reason = signal_data.get("impact_reason", "")
                    alpha.sector = signal_data.get("sector", "기타")
                    db.add(alpha)

                    news_item.is_analyzed = 1
                    analyzed_count += 1
                    logger.info(f"분석 완료: [{news_item.source}] {news_item.title[:40]}")
                else:
                    news_item.is_analyzed = 2  # 분석 실패
            except Exception as e:
                logger.error(f"분석 실패 (news_id={news_item.id}): {e}")
                news_item.is_analyzed = 2

        await db.commit()

    logger.info(f"알파 분석 완료: {analyzed_count}개")
    return analyzed_count


async def _analyze_single_news(news_item: NewsItem) -> Optional[dict]:
    """
    단일 뉴스를 Gemini AI로 분석합니다.
    반환값: 분석 결과 딕셔너리 또는 None
    """
    prompt = ANALYSIS_PROMPT.format(
        title=news_item.title,
        content=news_item.content_summary or news_item.title,
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,          # 낮은 온도로 일관된 JSON 출력
                max_output_tokens=1024,
            ),
        )

        raw_text = response.text.strip()

        # JSON 블록 추출 (```json ... ``` 형식도 처리)
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not json_match:
            logger.warning(f"JSON 파싱 실패: {raw_text[:100]}")
            return None

        return json.loads(json_match.group())

    except json.JSONDecodeError as e:
        logger.error(f"JSON 디코드 실패: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API 오류: {e}")
        return None
