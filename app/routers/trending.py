"""
트렌딩 토픽 알림 및 분석 라우터
"""
import json
import httpx
import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/trending", tags=["트렌딩"])

try:
    from app.config import config
    GEMINI_KEY = config.GEMINI_API_KEY
except Exception:
    GEMINI_KEY = ""


class TrendingTopic(BaseModel):
    keyword: str
    search_volume: str
    trend_direction: str  # 상승, 유지, 하락
    related_news: List[str]


@router.get("/keywords")
async def get_trending_keywords(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """현재 트렌딩 키워드 조회 (Google Trends RSS 활용)"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = "https://trends.google.com/trending/rss?geo=KR"
            r = await client.get(url)
            # RSS 파싱 (간단히 title 추출)
            import re
            titles = re.findall(r'<title><!\[CDATA\[([^\]]+)\]\]>', r.text)
            titles = [t for t in titles if t != "Google Trends"][: 20]
    except Exception:
        titles = ["AI", "주식", "날씨", "스포츠", "부동산"]  # fallback

    return {
        "trending_keywords": titles,
        "source": "Google Trends Korea",
        "category": category,
    }


@router.post("/analyze")
async def analyze_trending_topic(
    keyword: str,
    current_user: User = Depends(get_current_user),
):
    """트렌딩 키워드 심층 분석"""
    if not GEMINI_KEY:
        raise HTTPException(500, "AI 서비스 설정이 필요합니다")

    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        f"현재 트렌딩 키워드 '{keyword}'에 대해 분석해줘.\n"
        "1. 왜 지금 이슈인지\n2. 주요 관련 내용 3가지\n3. 향후 전망\n"
        "한국어로 간결하게 작성해줘."
    )
    return {
        "keyword": keyword,
        "analysis": response.text,
    }
